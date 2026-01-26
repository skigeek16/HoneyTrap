from typing import Dict
from .models import Persona, Strategy
from .library import PERSONA_ELDERLY_CONFUSED, PERSONA_CAUTIOUS_PROFESSIONAL

class PersonaManager:
    def __init__(self):
        self.scam_mapping = {
            "Bank Fraud / UPI Scam": "elderly_confused",
            "Phishing": "cautious_professional",
            "Tax/Gov Impersonation": "elderly_confused",
            "General Suspicion": "cautious_professional"
        }
        self.personas = {
            "elderly_confused": PERSONA_ELDERLY_CONFUSED,
            "cautious_professional": PERSONA_CAUTIOUS_PROFESSIONAL
        }

    def select_persona(self, scam_type: str) -> Persona:
        """Step 3.1: Persona Selection [cite: 118]"""
        key = self.scam_mapping.get(scam_type, "cautious_professional")
        return self.personas[key]

    def initialize_strategy(self, persona: Persona) -> Strategy:
        """Step 3.3: Strategy Init [cite: 198]"""
        return Strategy(
            phase="Initial Contact", primary_goal="Establish believability",
            extraction_priority=["Context"], emotional_state="confusion" if "elderly" in persona.id else "neutral",
            response_style="Reactive, asking clarification"
        )