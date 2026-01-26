import json
import redis
from datetime import datetime
from typing import Optional
from models import SessionState, IncomingRequest, APIResponse, ExtractedIntelligence
from config import settings

class SessionManager:
    def __init__(self):
        if settings.USE_REDIS:
            self.redis_client = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=settings.REDIS_DB, decode_responses=True)
        else:
            self.memory_store = {}

    def get_session(self, session_id: str) -> Optional[SessionState]:
        if settings.USE_REDIS:
            data = self.redis_client.get(f"session:{session_id}")
            return SessionState(**json.loads(data)) if data else None
        return self.memory_store.get(session_id)

    def create_session(self, request: IncomingRequest) -> SessionState:
        return SessionState(session_id=request.sessionId, metadata=request.metadata.model_dump() if request.metadata else {}, conversation_history=[])

    def save_session(self, session: SessionState):
        session.last_active = datetime.utcnow()
        if settings.USE_REDIS:
            self.redis_client.setex(f"session:{session.session_id}", 86400, session.model_dump_json())
        else:
            self.memory_store[session.session_id] = session

    def update_session(self, session: SessionState, scammer_msg: str, agent_msg: str):
        session.message_count += 1
        session.conversation_history.append({"sender": "scammer", "text": scammer_msg, "timestamp": str(datetime.utcnow())})
        session.conversation_history.append({"sender": "agent", "text": agent_msg, "timestamp": str(datetime.utcnow())})
        self.save_session(session)

    def format_response(self, session, agent_msg, scam_detected) -> APIResponse:
        intel = session.intelligence
        return APIResponse(
            status="success", scamDetected=scam_detected, totalMessagesExchanged=session.message_count,
            engagementMetrics={"duration": 0, "phase": session.phase},
            extractedIntelligence=ExtractedIntelligence(
                bankAccounts=[e.value for e in intel.entities if e.type == "BANK_ACC"],
                upiIds=[e.value for e in intel.entities if e.type == "UPI_ID"],
                phishingLinks=[e.value for e in intel.entities if e.type == "URL"],
                phoneNumbers=[e.value for e in intel.entities if e.type == "PHONE_IN"],
                agentNotes=f"Detected: {session.intelligence.entities[-1].type if intel.entities else 'None'}"
            )
        )