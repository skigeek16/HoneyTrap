from .models import IntelligenceState
from .extractor import ExtractionEngine

class IntelligenceManager:
    def __init__(self):
        self.engine = ExtractionEngine()

    def process_turn(self, text: str, turn_count: int, current_state: IntelligenceState) -> IntelligenceState:
        [cite_start]"""Main entry point for Stage 4 [cite: 206]"""
        # 1. Run all extractors
        new_entities = (
            self.engine.extract_regex(text, turn_count) +
            self.engine.extract_ner(text, turn_count) +
            self.engine.extract_keywords(text, turn_count)
        )
        # 2. Update State
        for entity in new_entities:
            current_state.add_entity(entity)
        # 3. Gap Analysis
        self._calculate_gap_analysis(current_state)
        return current_state

    def _calculate_gap_analysis(self, state: IntelligenceState):
        [cite_start]"""Step 4.2: Intelligence Gap Analysis [cite: 236-251]"""
        has_payment = any(e.type in ["UPI_ID", "BANK_ACC", "CRYPTO"] for e in state.entities)
        has_contact = any(e.type in ["PHONE_IN", "EMAIL", "URL"] for e in state.entities)
        has_tactical = any(e.category == "TACTICAL" for e in state.entities)
        
        score = 0.0
        if has_payment: score += 70.0
        if has_contact: score += 20.0
        if has_tactical: score += 10.0
        state.completion_percentage = score
        
        state.missing_priorities = []
        if not has_payment: state.missing_priorities.append("PAYMENT_DETAILS")
        if not has_contact: state.missing_priorities.append("CONTACT_INFO")