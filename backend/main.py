"""
Agentic Honey-Pot API — Two-Way Responsive Backend.

POST  /v1/chat               → Accepts a message, returns ACK, processes in background.
WS    /ws/session/{id}        → Real-time stream of SCAM_STATUS_UPDATE & STALL_MESSAGE events.
GET   /v1/session/{id}        → Session info (debug / dashboard).
"""
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.concurrency import run_in_threadpool

import uvicorn
import traceback
import sys
import os

# Add project root to sys.path so we can import 'backend' and 'processing'
# even when running from inside the 'backend' directory
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.models import IncomingRequest, SimpleReply
from backend.session_manager import SessionManager
from backend.connection_manager import manager as ws_manager
from backend.config import settings

from processing.detectors.engine import ScamDetectionEngine
from processing.personas.manager import PersonaManager
from processing.intelligence.manager import IntelligenceManager
from processing.response.engine import ResponseEngine


# ─── App Setup ─────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Agentic Honey-Pot API",
    version="2.1",
    description="Two-way responsive AI honeypot (Open Access)",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Singleton Services ───────────────────────────────────────────────────────

session_manager = SessionManager()
detector = ScamDetectionEngine()
persona_manager = PersonaManager()
intel_manager = IntelligenceManager()
responder = ResponseEngine()

# ─── Health ────────────────────────────────────────────────────────────────────

@app.get("/")
async def health_check():
    return {"status": "ok", "message": "Agentic Honey-Pot API v2.1 (Open Access) is running"}


@app.get("/health")
async def health():
    return {"status": "healthy", "version": "2.1"}


# ─── WebSocket Endpoint ───────────────────────────────────────────────────────

@app.websocket("/ws/session/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """
    The app connects here to receive real-time updates for a session.

    Events pushed to the client:
      • SCAM_STATUS_UPDATE — scam detection result (for color dots)
      • STALL_MESSAGE      — the text reply to forward to the scammer
      • ACK                — connection confirmation
      • ERROR              — if something goes wrong server-side
    """
    await ws_manager.connect(session_id, websocket)

    # Send connection acknowledgement
    await ws_manager.broadcast(session_id, "ACK", {
        "session_id": session_id,
        "message": "Connected. You will receive SCAM_STATUS_UPDATE and STALL_MESSAGE events.",
    })

    try:
        while True:
            # Keep alive — the client can also send pings or data here
            data = await websocket.receive_text()
            # Optional: handle client-sent messages (e.g. "ping")
            if data.strip().lower() == "ping":
                await websocket.send_text('{"type":"PONG"}')
    except WebSocketDisconnect:
        ws_manager.disconnect(session_id, websocket)


# ─── Main Chat Endpoint ───────────────────────────────────────────────────────

@app.post("/v1/chat", response_model=SimpleReply)
async def chat_endpoint(
    request: IncomingRequest,
    background_tasks: BackgroundTasks,
):
    """
    Accepts a scammer message, returns an immediate ACK,
    then processes detection + response in the background
    and pushes results over WebSocket.
    """
    # 1. (API Key check removed)

    # 2. Get or create session
    session = session_manager.get_session(request.sessionId)
    if session is None:
        session = session_manager.create_session(request)

    # 3. Schedule background processing
    background_tasks.add_task(
        _process_message,
        session_id=request.sessionId,
        message_text=request.message.text,
    )

    # 4. Return immediate ACK
    return SimpleReply(
        status="processing",
        session_id=request.sessionId,
        message="Message received. Results will be pushed via WebSocket.",
    )


# ─── Background Processing Pipeline ───────────────────────────────────────────

async def _process_message(session_id: str, message_text: str):
    """
    Runs in the background after the HTTP response is sent.

    Pipeline:
      1. Scam Detection   → broadcast SCAM_STATUS_UPDATE
      2. Persona Selection (if first scam)
      3. Intelligence Extraction
      4. Response Generation → broadcast STALL_MESSAGE
      5. (GUVI Callback removed)
    """
    try:
        session = session_manager.get_session(session_id)
        if session is None:
            await ws_manager.broadcast(session_id, "ERROR", {
                "message": "Session not found",
            })
            return
        # ── Ghost Mode Check (Stop if already completed) ──────────────
        if hasattr(session, 'ghost_mode') and session.ghost_mode:
            print(f"👻 Session {session_id} is in GHOST MODE. Ignoring message.")
            return

        # ── Stage 1: Scam Detection (CPU-bound → threadpool) ──────────
        detect_res = await run_in_threadpool(
            detector.evaluate, message_text
        )
        should_engage = detect_res["is_scam"]
        session.scam_confidence = detect_res["confidence_score"]

        # ** IMMEDIATELY broadcast scam status to the app **
        await session_manager.broadcast_scam_status(
            session_id=session_id,
            is_scam=should_engage,
            confidence=detect_res["confidence_score"],
            scam_type=detect_res.get("scam_type", "Unknown"),
        )

        # ── If SAFE, stop here. No reply, no engagement. ─────────────
        if not should_engage:
            return

        # ── Stage 2: Persona Selection ────────────────────────────────
        if not session.persona:
            selected_persona = persona_manager.select_persona(detect_res["scam_type"])
            session.persona = selected_persona.model_dump()
            session.strategy = persona_manager.initialize_strategy(selected_persona).model_dump()

        # ── Stage 3: Intelligence Extraction (CPU-bound → threadpool) ─
        session.intelligence = await run_in_threadpool(
            intel_manager.process_turn,
            message_text,
            session.message_count,
            session.intelligence,
        )

        # ── Ghost Mode Trigger (Stop if we have enough info) ──────────
        # If we have gathered enough intelligence (e.g. > 90%), stop responding
        # effectively "ghosting" the scammer.
        if session.intelligence.completion_percentage >= 90:
            print(f"👻 Intelligence complete ({session.intelligence.completion_percentage}%). Activating GHOST MODE for {session_id}.")
            session.ghost_mode = True
            session_manager.save_session(session)
            return
            
        # ── Stage 4: Response Generation ──────────────────────────────
        intent = detect_res["details"]["ml_ensemble"]["intent"]
        resp_data = await run_in_threadpool(
            responder.generate_response, session, message_text, intent
        )
        agent_msg = resp_data["response_text"]
        delay = resp_data.get("suggested_delay", 2.0)

        # Update session history
        session_manager.update_session(session, message_text, agent_msg)

        # ** Broadcast the stall message to the app **
        await session_manager.broadcast_stall_message(
            session_id=session_id,
            message_body=agent_msg,
            delay=delay,
            phase=session.phase,
        )

    except Exception as e:
        traceback.print_exc()
        await ws_manager.broadcast(session_id, "ERROR", {
            "message": f"Processing failed: {str(e)}",
        })


# ─── Session Info (Debug / Dashboard) ─────────────────────────────────────────

@app.get("/v1/session/{session_id}")
async def get_session_info(session_id: str):
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return {
        "session_id": session.session_id,
        "message_count": session.message_count,
        "phase": session.phase,
        "scam_confidence": session.scam_confidence,
        "intelligence_completion": session.intelligence.completion_percentage,
        "entities_extracted": len(session.intelligence.entities),
        "ghost_mode": getattr(session, "ghost_mode", False),
        "intelligence_report": [
            {
                "type": e.type,
                "value": e.value,
                "confidence": e.confidence
            } for e in session.intelligence.entities
        ],
        "persona": session.persona.get("name") if session.persona else None,
    }


# ─── Entrypoint ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
