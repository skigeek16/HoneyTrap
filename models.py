from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from intelligence.models import IntelligenceState

class Message(BaseModel):
    sender: str  # "scammer" or "user"
    text: str
    timestamp: datetime

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
    status: str
    scamDetected: bool
    engagementMetrics: Dict[str, Any]
    totalMessagesExchanged: int
    extractedIntelligence: Optional[ExtractedIntelligence] = None

class SessionState(BaseModel):
    session_id: str
    metadata: Dict[str, Any]
    conversation_history: List[Dict[str, Any]]
    intelligence: IntelligenceState = Field(default_factory=IntelligenceState)
    scam_confidence: float = 0.0
    persona: Optional[Dict[str, Any]] = None
    strategy: Optional[Dict[str, Any]] = None
    phase: str = "initial"
    message_count: int = 0
    scammer_patience: float = 100.0
    last_active: datetime = Field(default_factory=datetime.utcnow)