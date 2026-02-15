import random
from typing import Dict
from .models import Persona, Strategy
from .library import (
    PERSONA_ELDERLY_CONFUSED, 
    PERSONA_CAUTIOUS_PROFESSIONAL,
    PERSONA_HOUSEWIFE,
    PERSONA_STUDENT,
    PERSONA_BUSINESSMAN
)

class PersonaManager:
    def __init__(self):
        # Map scam types to most vulnerable persona types
        self.scam_mapping = {
            "Bank Fraud / UPI Scam": ["elderly_confused", "worried_housewife", "busy_businessman"],
            "Phishing": ["cautious_professional", "naive_student", "elderly_confused"],
            "Prize/Lottery Scam": ["elderly_confused", "naive_student", "worried_housewife"],
            "Job/Investment Scam": ["naive_student", "worried_housewife", "busy_businessman"],
            "Tax/Gov Impersonation": ["elderly_confused", "busy_businessman", "worried_housewife"],
            "General Suspicion": ["cautious_professional", "elderly_confused"]
        }
        
        self.personas = {
            "elderly_confused": PERSONA_ELDERLY_CONFUSED,
            "cautious_professional": PERSONA_CAUTIOUS_PROFESSIONAL,
            "worried_housewife": PERSONA_HOUSEWIFE,
            "naive_student": PERSONA_STUDENT,
            "busy_businessman": PERSONA_BUSINESSMAN
        }
        
        # Strategy templates for different phases
        self.strategy_templates = {
            "Initial Contact": {
                "primary_goal": "Establish believability and show initial interest",
                "extraction_priority": ["Context", "Organization"],
                "response_style": "Reactive, asking clarification questions"
            },
            "Building Rapport": {
                "primary_goal": "Build trust and prepare for extraction",
                "extraction_priority": ["Contact", "Context"],
                "response_style": "Cooperative but slightly confused"
            },
            "Active Extraction": {
                "primary_goal": "Extract payment details and contact information",
                "extraction_priority": ["UPI_ID", "BANK_ACC", "PHONE"],
                "response_style": "Eager to comply, asking for specific details"
            }
        }

    def select_persona(self, scam_type: str) -> Persona:
        """Select an appropriate persona based on scam type with some randomness"""
        persona_options = self.scam_mapping.get(scam_type, ["cautious_professional"])
        
        # Weighted random selection (first option has higher probability)
        weights = [0.5, 0.3, 0.2][:len(persona_options)]
        selected_key = random.choices(persona_options, weights=weights[:len(persona_options)])[0]
        
        return self.personas[selected_key]

    def initialize_strategy(self, persona: Persona) -> Strategy:
        """Initialize conversation strategy based on persona"""
        
        # Determine initial emotional state based on persona role
        emotional_states = {
            "victim": "confusion",
            "skeptic": "caution",
            "eager_victim": "excitement",
            "impatient_victim": "impatience"
        }
        
        initial_emotion = emotional_states.get(persona.role, "neutral")
        template = self.strategy_templates["Initial Contact"]
        
        return Strategy(
            phase="Initial Contact",
            primary_goal=template["primary_goal"],
            extraction_priority=template["extraction_priority"],
            emotional_state=initial_emotion,
            response_style=template["response_style"]
        )
    
    def update_strategy(self, current_strategy: Dict, new_phase: str, intelligence_completion: float) -> Strategy:
        """Update strategy based on conversation progress"""
        
        template = self.strategy_templates.get(new_phase, self.strategy_templates["Building Rapport"])
        
        # Adjust emotional state based on phase
        if new_phase == "Active Extraction":
            emotional_state = "eagerness"
        elif intelligence_completion > 50:
            emotional_state = "trust"
        else:
            emotional_state = current_strategy.get("emotional_state", "confusion")
        
        return Strategy(
            phase=new_phase,
            primary_goal=template["primary_goal"],
            extraction_priority=template["extraction_priority"],
            emotional_state=emotional_state,
            response_style=template["response_style"]
        )
