from fastapi import FastAPI, HTTPException, Header
from models import IncomingRequest, APIResponse
from session_manager import SessionManager
from detectors.engine import ScamDetectionEngine
from personas.manager import PersonaManager
from intelligence.manager import IntelligenceManager
from response.engine import ResponseEngine
from config import settings
import uvicorn

app = FastAPI(title="Agentic Honey-Pot API", version="1.0")

# Initialize Systems
session_manager = SessionManager()
detector = ScamDetectionEngine()
persona_manager = PersonaManager()
intel_manager = IntelligenceManager()
responder = ResponseEngine()

@app.post("/v1/chat", response_model=APIResponse)
async def chat_endpoint(request: IncomingRequest, x_api_key: str = Header(...)):
    if x_api_key != settings.API_KEY: raise HTTPException(status_code=401, detail="Invalid API Key")
    session = session_manager.get_session(request.sessionId) or session_manager.create_session(request)

    detect_res = detector.evaluate(request.message.text)
    session.scam_confidence = detect_res['confidence_score']
    should_engage = detect_res['is_scam']

    if should_engage and not session.persona:
        p = persona_manager.select_persona(detect_res['scam_type'])
        session.persona = p.model_dump()
        session.strategy = persona_manager.initialize_strategy(p).model_dump()

    session.intelligence = intel_manager.process_turn(request.message.text, session.message_count, session.intelligence)

    if should_engage:
        resp_data = responder.generate_response(session, request.message.text, detect_res['details']['ml_ensemble']['intent'])
        agent_msg = resp_data['response_text']
    else:
        agent_msg = "Not interested."

    session_manager.update_session(session, request.message.text, agent_msg)
    return session_manager.format_response(session, agent_msg, should_engage)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)