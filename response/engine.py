import random
from sentence_transformers import SentenceTransformer, util
from .data import TEMPLATES, STRATEGY_BY_PHASE, EXTRACTION_STRATEGIES
from .imperfection import ImperfectionEngine
from .llm_engine import get_llm_engine

class ResponseEngine:
    def __init__(self):
        self.imperfection_engine = ImperfectionEngine()
        self.semantic_model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
        self.template_embeddings = {t['id']: self.semantic_model.encode(t['text'], convert_to_tensor=True) for t in TEMPLATES}
        self.llm_engine = get_llm_engine()

    def generate_response(self, session, scammer_text: str, intent: str):
        """Main response generation with strategy-driven selection"""
        
        # Step 1: Update conversation phase based on progress
        self._update_phase(session)
        
        # Step 2: Get intelligence gaps to guide extraction strategy
        intelligence_gaps = session.intelligence.missing_priorities if session.intelligence else []
        
        # Step 3: Try LLM-powered response first if available
        if self.llm_engine.is_enabled() and session.persona:
            llm_response = self.llm_engine.generate_response(
                session_context={
                    'conversation_history': session.conversation_history,
                    'phase': session.phase,
                    'message_count': session.message_count
                },
                scammer_message=scammer_text,
                detected_intent=intent,
                intelligence_gaps=intelligence_gaps,
                persona=session.persona
            )
            if llm_response:
                delay = self.imperfection_engine.calculate_delay(llm_response)
                return {"response_text": llm_response, "suggested_delay": delay}
        
        # Step 4: Fall back to template-based response
        best_template = self._select_strategic_template(
            scammer_text=scammer_text,
            intent=intent,
            phase=session.phase,
            intelligence_gaps=intelligence_gaps
        )
        
        # Step 5: Apply imperfections based on persona
        final_text = best_template['text']
        delay = 2.0
        emotional_state = "neutral"
        
        if session.persona:
            from personas.models import ImperfectionProfile
            profile = ImperfectionProfile(**session.persona['imperfections'])
            if session.strategy:
                emotional_state = session.strategy.get('emotional_state', 'neutral')
            final_text = self.imperfection_engine.apply_imperfections(final_text, profile, emotional_state)
            delay = self.imperfection_engine.calculate_delay(final_text)

        return {"response_text": final_text, "suggested_delay": delay}

    def _update_phase(self, session):
        """Update conversation phase based on message count and intelligence gathered"""
        msg_count = session.message_count
        intel_completion = session.intelligence.completion_percentage if session.intelligence else 0
        
        if msg_count <= 2:
            session.phase = "Initial Contact"
        elif msg_count <= 5 or intel_completion < 30:
            session.phase = "Building Rapport"
        else:
            session.phase = "Active Extraction"
    
    def _select_strategic_template(self, scammer_text: str, intent: str, phase: str, intelligence_gaps: list):
        """Select template based on strategy, phase, intent, and intelligence gaps"""
        
        # Filter templates by phase
        phase_templates = [t for t in TEMPLATES if phase in t.get('phase', [])]
        
        # Further filter by intent if available
        intent_templates = [t for t in phase_templates if intent in t.get('intent', [])]
        
        # If we have specific intelligence gaps, prioritize extraction templates
        if intelligence_gaps and phase == "Active Extraction":
            extraction_templates = []
            for gap in intelligence_gaps:
                strategies = EXTRACTION_STRATEGIES.get(gap, [])
                for t in intent_templates or phase_templates:
                    if t.get('strategy') in strategies:
                        extraction_templates.append(t)
            if extraction_templates:
                # Randomly select from extraction-focused templates
                return random.choice(extraction_templates)
        
        # Use semantic similarity to pick the best template from filtered set
        candidates = intent_templates if intent_templates else (phase_templates if phase_templates else TEMPLATES)
        
        if len(candidates) == 1:
            return candidates[0]
        
        input_emb = self.semantic_model.encode(scammer_text, convert_to_tensor=True)
        best_score, best_t = -1, candidates[0]
        
        for t in candidates:
            if t['id'] in self.template_embeddings:
                score = util.cos_sim(input_emb, self.template_embeddings[t['id']]).item()
                # Add randomness to avoid always picking the same template
                score += random.uniform(-0.1, 0.1)
                if score > best_score:
                    best_score, best_t = score, t
        
        return best_t

    def _select_best_template(self, text):
        """Legacy method for backward compatibility - uses semantic similarity"""
        input_emb = self.semantic_model.encode(text, convert_to_tensor=True)
        best_score, best_t = -1, TEMPLATES[0]
        for t in TEMPLATES:
            score = util.cos_sim(input_emb, self.template_embeddings[t['id']])
            if score > best_score: best_score, best_t = score, t
        return best_t
