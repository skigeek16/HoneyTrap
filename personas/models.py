from pydantic import BaseModel
from typing import List

class ImperfectionProfile(BaseModel):
    """Configuration for Human Imperfection Application [cite: 156-196]"""
    typo_probability: float
    casual_language_usage: float
    text_speak_probability: float
    missing_punctuation: float
    emoji_usage: float
    mild_profanity: float
    indian_slangs: float
    tech_confusion: float

class Persona(BaseModel):
    """Agent character profile [cite: 121-154]"""
    id: str
    name: str
    description: str
    role: str
    tone: str
    imperfections: ImperfectionProfile
    common_phrases: List[str] = []

class Strategy(BaseModel):
    """Current conversation strategy state [cite: 198-203]"""
    phase: str
    primary_goal: str
    extraction_priority: List[str]
    emotional_state: str
    response_style: str
