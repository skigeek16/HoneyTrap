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
        print("⏳ Loading ML Ensemble Models...")
        device = 0 if torch.cuda.is_available() and settings.DEVICE == "cuda" else -1
        self.phishing_pipe = pipeline("text-classification", model=settings.MODEL_PHISHING, device=device)
        self.sentiment_pipe = pipeline("text-classification", model=settings.MODEL_SENTIMENT, device=device)
        self.emotion_pipe = pipeline("text-classification", model=settings.MODEL_EMOTION, top_k=None, device=device)
        self.intent_pipe = pipeline("zero-shot-classification", model=settings.MODEL_INTENT, device=device)
        self.multilingual_pipe = pipeline("zero-shot-classification", model=settings.MODEL_MULTILINGUAL, device=device)
        print("✅ Models Loaded.")

    def analyze(self, text: str) -> Dict:
        # Phishing detection
        phish_out = self.phishing_pipe(text)[0]
        phish_score = phish_out['score'] if phish_out['label'] == 'LABEL_1' else (1 - phish_out['score'])
        
        # More granular intent classification for scam detection
        scam_labels = [
            "requesting_payment",      # UPI/Bank fraud
            "threatening",             # Arrest/Legal threats
            "impersonating_authority", # Govt/Police/Bank impersonation
            "offering_prize",          # Lottery/Prize scams
            "phishing_attempt",        # Data/Credential theft
            "job_offer",               # Job/MLM scams
            "investment_opportunity",  # Crypto/Stock scams
            "urgent_action_required",  # Urgency manipulation
            "identity_verification",   # KYC/OTP scams
            "innocent_conversation"    # Normal message
        ]
        
        intent_out = self.intent_pipe(text, candidate_labels=scam_labels)
        top_intent = intent_out['labels'][0]
        top_confidence = intent_out['scores'][0]
        
        # Get top 3 intents for multi-signal analysis
        top_3_intents = list(zip(intent_out['labels'][:3], intent_out['scores'][:3]))
        
        # Check if any scam intent is in top 3 with reasonable confidence
        scam_intents_set = set(scam_labels) - {"innocent_conversation"}
        scam_signals = [(intent, conf) for intent, conf in top_3_intents if intent in scam_intents_set]
        
        # Multilingual scam detection
        multi_out = self.multilingual_pipe(text, candidate_labels=["scam", "fraud", "legitimate", "safe"])
        scam_fraud_score = sum(
            multi_out['scores'][i] for i, label in enumerate(multi_out['labels']) 
            if label in ["scam", "fraud"]
        )
        
        # Emotion analysis
        emotions = {e['label']: e['score'] for e in self.emotion_pipe(text)[0]}
        
        return {
            "phishing_prob": phish_score * 100,
            "emotions": emotions,
            "sentiment": self.sentiment_pipe(text)[0],
            "intent": top_intent,
            "intent_conf": top_confidence,
            "top_3_intents": top_3_intents,
            "scam_signals": scam_signals,
            "multilingual_scam_prob": scam_fraud_score * 100
        }