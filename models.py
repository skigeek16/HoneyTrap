from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from intelligence.models import IntelligenceState

class Message(BaseModel):
    sender: str  # "scammer" or "user"
    text: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class Metadata(BaseModel):
    channel: str = "SMS"
    language: str = "en"
    locale: str = "IN"

class IncomingRequest(BaseModel):
    sessionId: str = Field(..., description="Unique session ID")
    message: Message
    conversationHistory: List[Message] = []
    metadata: Optional[Metadata] = None

class ExtractedIntelligence(BaseModel):
    bankAccounts: List[str] = []
    upiIds: List[str] = []
    phishingLinks: List[str] = []
    phoneNumbers: List[str] = []
    suspiciousKeywords: List[str] = []
    organizationClaims: List[str] = []
    agentNotes: str = ""

class APIResponse(BaseModel):
    status: str = "success"
    scamDetected: bool
    engagementMetrics: Dict[str, Any]
    totalMessagesExchanged: int
    extractedIntelligence: Optional[ExtractedIntelligence] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "success",
                "scamDetected": True,
                "totalMessagesExchanged": 3,
                "engagementMetrics": {
                    "duration_seconds": 45.2,
                    "phase": "Building Rapport",
                    "scammer_patience": 85.0,
                    "intelligence_completion": 30.0,
                    "persona_used": "Ramesh Uncle",
                    "entities_extracted": 2
                },
                "extractedIntelligence": {
                    "bankAccounts": [],
                    "upiIds": ["scammer@upi"],
                    "phishingLinks": [],
                    "phoneNumbers": ["+919876543210"],
                    "suspiciousKeywords": ["urgent", "payment"],
                    "organizationClaims": ["Income Tax Department"],
                    "agentNotes": "Detected entities: UPI_ID, PHONE_IN | PRIMARY intel extracted: 1 items"
                }
            }
        }

class SessionState(BaseModel):
    session_id: str
    metadata: Dict[str, Any] = {}
    conversation_history: List[Dict[str, Any]] = []
    intelligence: IntelligenceState = Field(default_factory=IntelligenceState)
    scam_confidence: float = 0.0
    persona: Optional[Dict[str, Any]] = None
    strategy: Optional[Dict[str, Any]] = None
    phase: str = "Initial Contact"
    message_count: int = 0
    scammer_patience: float = 100.0
    last_active: datetime = Field(default_factory=datetime.utcnow)