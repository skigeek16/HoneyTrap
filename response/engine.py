from sentence_transformers import SentenceTransformer, util
from .data import TEMPLATES
from .imperfection import ImperfectionEngine

class ResponseEngine:
    def __init__(self):
        self.imperfection_engine = ImperfectionEngine()
        self.semantic_model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
        self.template_embeddings = {t['id']: self.semantic_model.encode(t['text'], convert_to_tensor=True) for t in TEMPLATES}

    def generate_response(self, session, scammer_text: str, intent: str):
        # Strategy Update
        if session.message_count > 3 and session.phase == "Initial Contact": session.phase = "Building Rapport"
        
        # Template Selection
        best_template = self._select_best_template(scammer_text)
        
        # Imperfection Application
        final_text = best_template['text']
        delay = 2.0
        if session.persona:
            from personas.models import ImperfectionProfile
            profile = ImperfectionProfile(**session.persona['imperfections'])
            final_text = self.imperfection_engine.apply_imperfections(final_text, profile, "neutral")
            delay = self.imperfection_engine.calculate_delay(final_text)

        return {"response_text": final_text, "suggested_delay": delay}

    def _select_best_template(self, text):
        input_emb = self.semantic_model.encode(text, convert_to_tensor=True)
        best_score, best_t = -1, TEMPLATES[0]
        for t in TEMPLATES:
            score = util.cos_sim(input_emb, self.template_embeddings[t['id']])
            if score > best_score: best_score, best_t = score, t
        return best_t