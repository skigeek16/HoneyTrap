from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from models import IncomingRequest, APIResponse, ExtractedIntelligence, SimpleReply
from session_manager import SessionManager
from detectors.engine import ScamDetectionEngine
from personas.manager import PersonaManager
from intelligence.manager import IntelligenceManager
from response.engine import ResponseEngine
from config import settings
import uvicorn

app = FastAPI(
    title="Agentic Honey-Pot API",
    version="1.0",
    description="Autonomous AI honeypot system for scam detection and intelligence extraction"
)

# Add CORS middleware for testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Systems (lazy loading handled in classes)
session_manager = SessionManager()
detector = ScamDetectionEngine()
persona_manager = PersonaManager()
intel_manager = IntelligenceManager()
responder = ResponseEngine()

@app.get("/")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok", "message": "Agentic Honey-Pot API is running"}

@app.get("/health")
async def health():
    """Alternative health check"""
    return {"status": "healthy", "version": "1.0"}

@app.post("/v1/chat", response_model=SimpleReply)
async def chat_endpoint(request: IncomingRequest, x_api_key: str = Header(..., alias="x-api-key")):
    """
    Main honeypot chat endpoint.
    
    - Receives scammer messages
    - Detects if message is a scam
    - Engages using believable personas
    - Extracts intelligence (UPI IDs, bank accounts, phishing links)
    - Returns simple JSON response: {"status": "success", "reply": "..."}
    """
    # Validate API key
    if x_api_key != settings.API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    
    try:
        # Get or create session
        session = session_manager.get_session(request.sessionId)
        if session is None:
            session = session_manager.create_session(request)

        # Stage 2: Scam Detection
        detect_res = detector.evaluate(request.message.text)
        session.scam_confidence = detect_res['confidence_score']
        should_engage = detect_res['is_scam']

        # Stage 3: Persona Selection (only on first scam detection)
        if should_engage and not session.persona:
            selected_persona = persona_manager.select_persona(detect_res['scam_type'])
            session.persona = selected_persona.model_dump()
            session.strategy = persona_manager.initialize_strategy(selected_persona).model_dump()

        # Stage 4: Intelligence Extraction
        session.intelligence = intel_manager.process_turn(
            request.message.text,
            session.message_count,
            session.intelligence
        )

        # Stage 5: Response Generation
        if should_engage:
            intent = detect_res['details']['ml_ensemble']['intent']
            resp_data = responder.generate_response(session, request.message.text, intent)
            agent_msg = resp_data['response_text']
        else:
            # Polite decline for non-scam messages
            agent_msg = "Thank you for your message, but I'm not interested."

        # Update session with new messages
        session_manager.update_session(session, request.message.text, agent_msg)
        
        # Send GUVI callback if scam detected
        session_manager.send_guvi_callback_if_ready(session, should_engage)
        
        # Return simple reply format as per Section 8
        return SimpleReply(status="success", reply=agent_msg, scamDetected=should_engage)
    
    except Exception as e:
        # Log error and return graceful response
        print(f"Error processing request: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/v1/session/{session_id}")
async def get_session_info(session_id: str, x_api_key: str = Header(..., alias="x-api-key")):
    """Get information about a specific session"""
    if x_api_key != settings.API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    
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
        "persona": session.persona.get('name') if session.persona else None
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)