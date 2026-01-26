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
        
        # Update scammer patience based on conversation dynamics
        session.scammer_patience = self._calculate_patience_decay(session, agent_msg)
        
        self.save_session(session)

    def _calculate_patience_decay(self, session: SessionState, agent_msg: str) -> float:
        """Calculate scammer patience decay based on conversation dynamics"""
        patience = session.scammer_patience
        
        # Decay factors
        base_decay = 3.0  # Per turn decay
        stall_keywords = ["wait", "hold on", "minute", "loading", "slow", "checking", "error"]
        extract_keywords = ["upi", "account", "number", "transfer", "send money"]
        
        agent_lower = agent_msg.lower()
        
        # Stalling increases decay (scammer gets impatient)
        if any(kw in agent_lower for kw in stall_keywords):
            base_decay += 5.0
        
        # Showing willingness to pay decreases decay (keeps scammer engaged)
        if any(kw in agent_lower for kw in extract_keywords):
            base_decay -= 8.0  # Reward - scammer sees progress
        
        # Early messages don't decay much
        if session.message_count <= 3:
            base_decay *= 0.5
        
        # Apply decay with minimum of 0
        new_patience = max(0.0, patience - base_decay)
        
        return round(new_patience, 2)

    def format_response(self, session, agent_msg, scam_detected) -> APIResponse:
        intel = session.intelligence
        
        # Calculate session duration
        if session.conversation_history:
            try:
                first_msg_time = datetime.fromisoformat(session.conversation_history[0].get('timestamp', str(datetime.utcnow())))
                duration_seconds = (datetime.utcnow() - first_msg_time).total_seconds()
            except:
                duration_seconds = 0
        else:
            duration_seconds = 0
        
        # Build extracted intelligence
        extracted = ExtractedIntelligence(
            bankAccounts=[e.value for e in intel.entities if e.type == "BANK_ACC"],
            upiIds=[e.value for e in intel.entities if e.type == "UPI_ID"],
            phishingLinks=[e.value for e in intel.entities if e.type == "URL"],
            phoneNumbers=[e.value for e in intel.entities if e.type == "PHONE_IN"],
            suspiciousKeywords=[e.value for e in intel.entities if e.type == "KEYWORD"],
            organizationClaims=[e.value for e in intel.entities if e.type == "ORGANIZATION"],
            agentNotes=self._generate_agent_notes(session, intel)
        )
        
        return APIResponse(
            status="success",
            scamDetected=scam_detected,
            totalMessagesExchanged=session.message_count,
            engagementMetrics={
                "duration_seconds": round(duration_seconds, 2),
                "phase": session.phase,
                "scammer_patience": session.scammer_patience,
                "intelligence_completion": intel.completion_percentage,
                "persona_used": session.persona.get('name', 'Unknown') if session.persona else None,
                "entities_extracted": len(intel.entities)
            },
            extractedIntelligence=extracted
        )
    
    def _generate_agent_notes(self, session, intel) -> str:
        """Generate human-readable agent notes about the interaction"""
        notes = []
        
        # Summarize what was detected
        if intel.entities:
            entity_types = set(e.type for e in intel.entities)
            notes.append(f"Detected entities: {', '.join(entity_types)}")
        
        # Note primary extractions
        primary = [e for e in intel.entities if e.category == "PRIMARY"]
        if primary:
            notes.append(f"PRIMARY intel extracted: {len(primary)} items (UPI/Bank/Crypto)")
        
        # Phase and progress
        notes.append(f"Conversation phase: {session.phase}")
        notes.append(f"Intelligence completion: {intel.completion_percentage}%")
        
        # Missing data
        if intel.missing_priorities:
            notes.append(f"Still seeking: {', '.join(intel.missing_priorities)}")
        
        return " | ".join(notes) if notes else "Conversation initiated"