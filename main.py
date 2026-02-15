from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from models import IncomingRequest, APIResponse, ExtractedIntelligence, SimpleReply
from session_manager import SessionManager
from detectors.engine import ScamDetectionEngine
from personas.manager import PersonaManager
from intelligence.manager import IntelligenceManager
from response.engine import ResponseEngine
from config import settings
from datetime import datetime
import uvicorn

app = FastAPI(
    title="Agentic Honey-Pot API",
    version="2.0",
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
    return {"status": "healthy", "version": "2.0"}

@app.post("/v1/chat")
async def chat_endpoint(request: IncomingRequest, x_api_key: str = Header(..., alias="x-api-key")):
    """
    Main honeypot chat endpoint.
    
    Returns full evaluation-compatible response with:
    - reply: honeypot response text
    - scamDetected: boolean
    - extractedIntelligence: phone numbers, bank accounts, UPI IDs, links, emails
    - engagementMetrics: messages exchanged, duration
    - agentNotes: analysis summary
    """
    # Validate API key
    if x_api_key != settings.API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    
    try:
        # Get or create session
        session = session_manager.get_session(request.sessionId)
        is_new_session = session is None
        
        if is_new_session:
            session = session_manager.create_session(request)
            
            # Bootstrap from evaluator's conversationHistory if provided
            if request.conversationHistory:
                for msg in request.conversationHistory:
                    msg_text = ""
                    msg_sender = "scammer"
                    if isinstance(msg, dict):
                        msg_text = msg.get('text', msg.get('content', ''))
                        msg_sender = msg.get('sender', 'scammer')
                    elif isinstance(msg, str):
                        msg_text = msg
                    
                    if msg_text:
                        # Add to session history
                        session.conversation_history.append({
                            'sender': msg_sender,
                            'text': msg_text,
                            'timestamp': msg.get('timestamp', '') if isinstance(msg, dict) else ''
                        })
                        
                        # Extract intelligence from all prior scammer messages
                        if msg_sender == 'scammer':
                            session.intelligence = intel_manager.process_turn(
                                msg_text, session.message_count, session.intelligence
                            )
                            session.message_count += 1

        # Stage 2: Scam Detection
        detect_res = detector.evaluate(request.message.text)
        session.scam_confidence = detect_res['confidence_score']
        should_engage = detect_res['is_scam']

        # Stage 3: Persona Selection (only on first scam detection)
        if should_engage and not session.persona:
            selected_persona = persona_manager.select_persona(detect_res['scam_type'])
            session.persona = selected_persona.model_dump()
            session.strategy = persona_manager.initialize_strategy(selected_persona).model_dump()

        # Stage 4: Intelligence Extraction (current message)
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
        
        # Build extracted intelligence from session entities
        extracted_intel = _build_extracted_intelligence(session)
        
        # Calculate engagement metrics
        duration_seconds = int((datetime.utcnow() - session.start_time).total_seconds())
        
        # Build agent notes
        scam_type = detect_res.get('scam_type', 'unknown')
        agent_notes = _build_agent_notes(session, detect_res, extracted_intel)
        
        # Return full evaluation-compatible response
        return {
            "status": "success",
            "reply": agent_msg,
            "scamDetected": should_engage,
            "scamType": scam_type,
            "extractedIntelligence": extracted_intel,
            "engagementMetrics": {
                "totalMessagesExchanged": session.message_count,
                "engagementDurationSeconds": duration_seconds
            },
            "agentNotes": agent_notes
        }
    
    except Exception as e:
        # Log error and return graceful response
        print(f"Error processing request: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


def _build_extracted_intelligence(session) -> dict:
    """Build extractedIntelligence dict from session's intelligence entities."""
    intel = {
        "phoneNumbers": [],
        "bankAccounts": [],
        "upiIds": [],
        "phishingLinks": [],
        "emailAddresses": []
    }
    
    for entity in session.intelligence.entities:
        etype = entity.type
        val = entity.value
        
        if etype in ("PHONE_IN", "PHONE"):
            if val not in intel["phoneNumbers"]:
                intel["phoneNumbers"].append(val)
        elif etype in ("BANK_ACC", "BANK_ACCOUNT"):
            if val not in intel["bankAccounts"]:
                intel["bankAccounts"].append(val)
        elif etype in ("UPI_ID", "UPI"):
            if val not in intel["upiIds"]:
                intel["upiIds"].append(val)
        elif etype in ("URL", "LINK", "PHISHING_LINK"):
            if val not in intel["phishingLinks"]:
                intel["phishingLinks"].append(val)
        elif etype in ("EMAIL",):
            if val not in intel["emailAddresses"]:
                intel["emailAddresses"].append(val)
    
    return intel


def _build_agent_notes(session, detect_res: dict, extracted_intel: dict) -> str:
    """Build a summary of agent analysis for the agentNotes field."""
    scam_type = detect_res.get('scam_type', 'unknown')
    confidence = detect_res.get('confidence_score', 0)
    
    notes_parts = []
    notes_parts.append(f"Scam type: {scam_type} (confidence: {confidence}%)")
    
    # List detection layers that triggered
    details = detect_res.get('details', {})
    if details.get('llm_classifier', {}).get('llm_enabled'):
        llm_type = details['llm_classifier'].get('llm_scam_type', '')
        llm_score = details['llm_classifier'].get('llm_score', 0)
        notes_parts.append(f"LLM classifier: {llm_type} (score: {llm_score})")
    
    # Summarize extracted intel
    total_intel = sum(len(v) for v in extracted_intel.values())
    if total_intel > 0:
        items = []
        for key, vals in extracted_intel.items():
            if vals:
                items.append(f"{key}: {vals}")
        notes_parts.append(f"Extracted {total_intel} intelligence items: {', '.join(items)}")
    
    notes_parts.append(f"Conversation turns: {session.message_count}")
    notes_parts.append(f"Persona: {session.persona.get('name', 'N/A') if session.persona else 'N/A'}")
    
    return ". ".join(notes_parts)


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


@app.get("/v1/session/{session_id}/final")
async def get_final_output(session_id: str, x_api_key: str = Header(..., alias="x-api-key")):
    """Get final output for a session — full evaluation-compatible format."""
    if x_api_key != settings.API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    extracted_intel = _build_extracted_intelligence(session)
    duration_seconds = int((datetime.utcnow() - session.start_time).total_seconds())
    
    return {
        "status": "completed",
        "scamDetected": session.scam_confidence >= 40,
        "scamType": "unknown",
        "extractedIntelligence": extracted_intel,
        "engagementMetrics": {
            "totalMessagesExchanged": session.message_count,
            "engagementDurationSeconds": duration_seconds
        },
        "agentNotes": f"Session completed with {session.message_count} turns. Confidence: {session.scam_confidence}%. Persona: {session.persona.get('name') if session.persona else 'N/A'}"
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)