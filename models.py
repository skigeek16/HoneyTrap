from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from intelligence.models import IntelligenceState

class Message(BaseModel):
    sender: str = "scammer"  # Default to scammer
    text: str
    timestamp: Optional[Any] = None  # Accept any timestamp format
    
    @field_validator('timestamp', mode='before')
    @classmethod
    def parse_timestamp(cls, v):
        if v is None:
            return datetime.utcnow().isoformat()
        return v  # Keep as string or whatever format

class Metadata(BaseModel):
    channel: str = "SMS"
    language: str = "en"
    locale: str = "IN"
    
    class Config:
        extra = "allow"  # Allow extra fields

class IncomingRequest(BaseModel):
    sessionId: str = Field(..., description="Unique session ID")
    message: Union[str, Dict[str, Any], Message]  # Accept string, dict, or Message
    conversationHistory: Optional[List[Any]] = []
    metadata: Optional[Union[Dict[str, Any], Metadata]] = None
    
    class Config:
        extra = "allow"  # Allow extra fields
    
    @field_validator('message', mode='before')
    @classmethod
    def parse_message(cls, v):
        if isinstance(v, str):
            return Message(sender="scammer", text=v)
        if isinstance(v, dict):
            # Handle dict with 'text' field
            text = v.get('text', v.get('content', ''))
            sender = v.get('sender', 'scammer')
            timestamp = v.get('timestamp')
            return Message(sender=sender, text=text, timestamp=timestamp)
        return v

class ExtractedIntelligence(BaseModel):
    bankAccounts: List[str] = []
    upiIds: List[str] = []
    phishingLinks: List[str] = []
    phoneNumbers: List[str] = []
    suspiciousKeywords: List[str] = []
    
    class Config:
        extra = "ignore"

class SimpleReply(BaseModel):
    """Simple response format as per Section 8 of problem statement"""
    status: str = "success"
    reply: str
    scamDetected: bool = False

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
        # Ensure exact JSON output
        json_encoders = {}

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
    start_time: datetime = Field(default_factory=datetime.utcnow)

