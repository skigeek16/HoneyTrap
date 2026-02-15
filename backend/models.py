from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict, Any, Union
from datetime import datetime, timezone
from processing.intelligence.models import IntelligenceState


# ─── Incoming Request Models ───────────────────────────────────────────────────

class Message(BaseModel):
    sender: str = "scammer"
    text: str
    timestamp: Optional[Any] = None

    @field_validator('timestamp', mode='before')
    @classmethod
    def parse_timestamp(cls, v):
        if v is None:
            return datetime.now(timezone.utc).isoformat()
        return v


class Metadata(BaseModel):
    channel: str = "SMS"
    language: str = "en"
    locale: str = "IN"

    class Config:
        extra = "allow"


class IncomingRequest(BaseModel):
    sessionId: str = Field(..., description="Unique session ID")
    message: Union[str, Dict[str, Any], Message]
    conversationHistory: Optional[List[Any]] = []
    metadata: Optional[Union[Dict[str, Any], Metadata]] = None

    class Config:
        extra = "allow"

    @field_validator('message', mode='before')
    @classmethod
    def parse_message(cls, v):
        if isinstance(v, str):
            return Message(sender="scammer", text=v)
        if isinstance(v, dict):
            text = v.get('text', v.get('content', ''))
            sender = v.get('sender', 'scammer')
            timestamp = v.get('timestamp')
            return Message(sender=sender, text=text, timestamp=timestamp)
        return v


# ─── WebSocket Event Payloads ──────────────────────────────────────────────────

class ScamStatusPayload(BaseModel):
    """
    Response Type 1 — Scam Confirmation.
    Sent to the app so it can update its status indicator (color dots).
    """
    is_scam: bool
    confidence: float = Field(..., ge=0.0, le=100.0, description="Confidence 0-100")
    severity: str = Field(..., description="SAFE | SUSPICIOUS | SCAM")
    scam_type: Optional[str] = None
    ui_color: str = Field(..., description="green | yellow | red")


class StallMessagePayload(BaseModel):
    """
    Response Type 2 — Simple Reply.
    Contains the text the app should send to the scammer to stall them.
    """
    message_body: str
    suggested_delay: float = 2.0
    phase: str = "Initial Contact"


class WebSocketEvent(BaseModel):
    """Wrapper envelope sent over the WebSocket."""
    type: str = Field(..., description="SCAM_STATUS_UPDATE | STALL_MESSAGE | ACK | ERROR")
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    payload: Dict[str, Any]


# ─── Legacy / Existing Response Models ─────────────────────────────────────────

class ExtractedIntelligence(BaseModel):
    bankAccounts: List[str] = []
    upiIds: List[str] = []
    phishingLinks: List[str] = []
    phoneNumbers: List[str] = []
    suspiciousKeywords: List[str] = []

    class Config:
        extra = "ignore"


class SimpleReply(BaseModel):
    """HTTP response returned from POST /v1/chat (acknowledgement)."""
    status: str = "processing"
    session_id: str = ""
    message: str = "Message received. Updates will arrive over WebSocket."


class EngagementMetrics(BaseModel):
    engagementDurationSeconds: int = 0
    totalMessagesExchanged: int = 0


class APIResponse(BaseModel):
    status: str = "success"
    scamDetected: bool
    engagementMetrics: EngagementMetrics
    extractedIntelligence: ExtractedIntelligence
    agentNotes: str = ""

    class Config:
        json_encoders = {}


# ─── Session State (in-memory, persisted to SQLite via session_manager) ────────

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
    last_active: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    start_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    ghost_mode: bool = False
