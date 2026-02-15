from transformers import pipeline
from config import settings
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

    def analyze(self, text: str) -> Dict:
        # Phishing detection
        phish_out = self.phishing_pipe(text)[0]
        phish_score = phish_out['score'] if phish_out['label'] == 'LABEL_1' else (1 - phish_out['score'])
        
        # Intent classification
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
        
        intent_out = self.intent_pipe(text, candidate_labels=scam_labels)
        top_intent = intent_out['labels'][0]
        top_confidence = intent_out['scores'][0]
        
        return {
            "phishing_prob": phish_score * 100,
            "intent": top_intent,
            "intent_conf": top_confidence,
            "multilingual_scam_prob": 0  # Removed heavy model, default to 0
        }
