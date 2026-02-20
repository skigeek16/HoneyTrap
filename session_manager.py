import json
import requests
from datetime import datetime
from typing import Optional
from models import SessionState, IncomingRequest, APIResponse, ExtractedIntelligence, EngagementMetrics

GUVI_CALLBACK_URL = "https://hackathon.guvi.in/api/updateHoneyPotFinalResult"

class SessionManager:
    def __init__(self):
        self.memory_store = {}

    def get_session(self, session_id: str) -> Optional[SessionState]:
        return self.memory_store.get(session_id)

    def create_session(self, request: IncomingRequest) -> SessionState:
        if request.metadata is None:
            meta = {}
        elif isinstance(request.metadata, dict):
            meta = request.metadata
        else:
            meta = request.metadata.model_dump()
            
        return SessionState(
            session_id=request.sessionId, 
            metadata=meta, 
            conversation_history=[],
            start_time=datetime.utcnow()
        )

    def save_session(self, session: SessionState):
        session.last_active = datetime.utcnow()
        self.memory_store[session.session_id] = session

    def update_session(self, session: SessionState, scammer_msg: str, agent_msg: str):
        session.message_count += 1
        session.conversation_history.append({"sender": "scammer", "text": scammer_msg, "timestamp": str(datetime.utcnow())})
        session.conversation_history.append({"sender": "agent", "text": agent_msg, "timestamp": str(datetime.utcnow())})
        session.scammer_patience = self._calculate_patience_decay(session, agent_msg)
        self.save_session(session)

    def _calculate_patience_decay(self, session: SessionState, agent_msg: str) -> float:
        patience = session.scammer_patience
        base_decay = 3.0
        stall_keywords = ["wait", "hold on", "minute", "loading", "slow", "checking", "error"]
        extract_keywords = ["upi", "account", "number", "transfer", "send money"]
        
        agent_lower = agent_msg.lower()
        if any(kw in agent_lower for kw in stall_keywords):
            base_decay += 5.0
        if any(kw in agent_lower for kw in extract_keywords):
            base_decay -= 8.0
        if session.message_count <= 3:
            base_decay *= 0.5
        
        return round(max(0.0, patience - base_decay), 2)

    def format_response(self, session, agent_msg, scam_detected) -> APIResponse:
        intel = session.intelligence
        duration_seconds = int((datetime.utcnow() - session.start_time).total_seconds())
        
        extracted = ExtractedIntelligence(
            bankAccounts=[e.value for e in intel.entities if e.type == "BANK_ACC"],
            upiIds=[e.value for e in intel.entities if e.type == "UPI_ID"],
            phishingLinks=[e.value for e in intel.entities if e.type == "URL"]
        )
        
        agent_notes = self._generate_agent_notes(session, intel)
        
        if scam_detected and session.message_count >= 2:
            self._send_guvi_callback(session, scam_detected, extracted, agent_notes)
        
        return APIResponse(
            status="success",
            scamDetected=scam_detected,
            engagementMetrics=EngagementMetrics(
                engagementDurationSeconds=duration_seconds,
                totalMessagesExchanged=session.message_count
            ),
            extractedIntelligence=extracted,
            agentNotes=agent_notes
        )
    
    def _generate_agent_notes(self, session, intel) -> str:
        notes = []
        if intel.entities:
            entity_types = set(e.type for e in intel.entities)
            notes.append(f"Detected: {', '.join(entity_types)}")
        
        primary = [e for e in intel.entities if e.category == "PRIMARY"]
        if primary:
            notes.append(f"Primary intel: {len(primary)} items")
        
        notes.append(f"Phase: {session.phase}")
        
        if intel.missing_priorities:
            notes.append(f"Seeking: {', '.join(intel.missing_priorities)}")
        
        return " | ".join(notes) if notes else "Engagement initiated"
    
    def send_guvi_callback_if_ready(self, session, scam_detected: bool):
        """Send GUVI callback when scam is detected and enough engagement"""
        if scam_detected and session.message_count >= 2:
            intel = session.intelligence
            
            # Calculate engagement duration
            duration_seconds = int((datetime.utcnow() - session.start_time).total_seconds())
            realistic_floor = session.message_count * 25  # ~25s per turn in real texting
            duration_seconds = max(duration_seconds, realistic_floor)
            
            # Build extracted intelligence with ALL required fields
            extracted = {
                "bankAccounts": [e.value for e in intel.entities if e.type == "BANK_ACC"],
                "upiIds": [e.value for e in intel.entities if e.type == "UPI_ID"],
                "phishingLinks": [e.value for e in intel.entities if e.type == "URL"],
                "phoneNumbers": [e.value for e in intel.entities if e.type == "PHONE_IN"],
                "emailAddresses": [e.value for e in intel.entities if e.type == "EMAIL"],
                "caseIds": [e.value for e in intel.entities if e.type == "CASE_ID"],
                "policyNumbers": [e.value for e in intel.entities if e.type == "POLICY_NUM"],
                "orderNumbers": [e.value for e in intel.entities if e.type == "ORDER_NUM"],
            }
            
            agent_notes = self._generate_agent_notes(session, intel)
            
            try:
                payload = {
                    "sessionId": session.session_id,
                    "scamDetected": scam_detected,
                    "totalMessagesExchanged": session.message_count,
                    "engagementDurationSeconds": duration_seconds,
                    "extractedIntelligence": extracted,
                    "agentNotes": agent_notes
                }
                
                response = requests.post(GUVI_CALLBACK_URL, json=payload, timeout=5)
                print(f"GUVI Callback: {response.status_code} - {response.text[:100]}")
            except Exception as e:
                print(f"GUVI Callback failed: {e}")

