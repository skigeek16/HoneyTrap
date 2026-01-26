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
        print("⏳ Loading ML Ensemble Models... [cite: 52-84]")
        device = 0 if torch.cuda.is_available() and settings.DEVICE == "cuda" else -1
        self.phishing_pipe = pipeline("text-classification", model=settings.MODEL_PHISHING, device=device)
        self.sentiment_pipe = pipeline("text-classification", model=settings.MODEL_SENTIMENT, device=device)
        self.emotion_pipe = pipeline("text-classification", model=settings.MODEL_EMOTION, top_k=None, device=device)
        self.intent_pipe = pipeline("zero-shot-classification", model=settings.MODEL_INTENT, device=device)
        self.multilingual_pipe = pipeline("zero-shot-classification", model=settings.MODEL_MULTILINGUAL, device=device)
        print("✅ Models Loaded.")

    def analyze(self, text: str) -> Dict:
        phish_out = self.phishing_pipe(text)[0]
        phish_score = phish_out['score'] if phish_out['label'] == 'LABEL_1' else (1 - phish_out['score'])
        
        intent_out = self.intent_pipe(text, candidate_labels=[
            "requesting_payment", "threatening", "impersonating_authority", 
            "offering_prize", "phishing_attempt", "job_offer", "innocent_conversation"
        ])
        
        multi_out = self.multilingual_pipe(text, candidate_labels=["scam", "safe"])
        
        return {
            "phishing_prob": phish_score * 100,
            "emotions": {e['label']: e['score'] for e in self.emotion_pipe(text)[0]},
            "sentiment": self.sentiment_pipe(text)[0],
            "intent": intent_out['labels'][0],
            "intent_conf": intent_out['scores'][0],
            "multilingual_scam_prob": multi_out['scores'][multi_out['labels'].index("scam")] * 100
        }