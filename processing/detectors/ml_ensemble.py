from transformers import pipeline
from backend.config import settings
import torch
from typing import Dict

class MLEnsembleDetector:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MLEnsembleDetector, cls).__new__(cls)
            cls._instance._load_models()
        return cls._instance

    def _load_models(self):
        print("⏳ Loading ML Models...")
        device = 0 if torch.cuda.is_available() and settings.DEVICE == "cuda" else -1
        
        # Only load essential models (reduced from 5 to 2)
        self.phishing_pipe = pipeline("text-classification", model=settings.MODEL_PHISHING, device=device)
        self.intent_pipe = pipeline("zero-shot-classification", model=settings.MODEL_INTENT, device=device)
        print("✅ Models Loaded.")

    def analyze(self, text: str, history: list = None) -> Dict:
        # Build context from conversation history (last N scammer messages)
        context_text = text
        if history:
            scammer_msgs = [
                m.get("content", m.get("text", ""))
                for m in history
                if m.get("role", m.get("sender", "")) == "scammer"
            ]
            # Use last 3 scammer messages for context (keep input short for models)
            recent = scammer_msgs[-3:] if len(scammer_msgs) > 3 else scammer_msgs
            if recent:
                context_text = " | ".join(recent) + " | " + text

        # Phishing detection (use context for better accuracy)
        phish_out = self.phishing_pipe(context_text[:512])[0]  # Truncate to model max
        phish_score = phish_out['score'] if phish_out['label'] == 'LABEL_1' else (1 - phish_out['score'])
        
        # Intent classification (use context for better accuracy)
        scam_labels = [
            "requesting_payment",
            "threatening",
            "impersonating_authority",
            "offering_prize",
            "phishing_attempt",
            "job_offer",
            "investment_opportunity",
            "urgent_action_required",
            "identity_verification",
            "innocent_conversation"
        ]
        
        intent_out = self.intent_pipe(context_text[:512], candidate_labels=scam_labels)
        top_intent = intent_out['labels'][0]
        top_confidence = intent_out['scores'][0]
        
        return {
            "phishing_prob": phish_score * 100,
            "intent": top_intent,
            "intent_conf": top_confidence,
            "multilingual_scam_prob": 0  # Removed heavy model, default to 0
        }

