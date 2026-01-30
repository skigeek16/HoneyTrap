from typing import Dict, Any
from .rule_based import RuleBasedDetector
from .ml_ensemble import MLEnsembleDetector
from config import settings

class ScamDetectionEngine:
    def __init__(self):
        self.rule_detector = RuleBasedDetector()
        self.ml_detector = MLEnsembleDetector()

    def evaluate(self, text: str) -> Dict[str, Any]:
        """Main pipeline for Stage 2 [cite: 85-97]"""
        rule_res = self.rule_detector.analyze(text)
        ml_res = self.ml_detector.analyze(text)
        final_score = self._calculate_ensemble_score(rule_res, ml_res)
        decision = "ACTIVATE_AGENT" if final_score >= settings.SCORE_MEDIUM else "POLITE_DECLINE"
        
        return {
            "is_scam": final_score >= settings.SCORE_MEDIUM,
            "confidence_score": final_score,
            "decision": decision,
            "scam_type": self._classify_scam_type(ml_res['intent'], rule_res['flags']),
            "details": {"rule_based": rule_res, "ml_ensemble": ml_res}
        }

    def _calculate_ensemble_score(self, rule: Dict, ml: Dict) -> float:
        """Weighted formula implementation [cite: 87-93]"""
        # Base score from ML models
        score = (
            (ml['phishing_prob'] * 100 * settings.WEIGHT_PHISHING) +
            (rule['rule_score'] * settings.WEIGHT_RULE_BASED) +
            (ml['multilingual_scam_prob'] * 100 * settings.WEIGHT_MULTILINGUAL)
        )
        
        # Emotion boosts
        if ml['emotions'].get('fear', 0) > 0.3 or ml['emotions'].get('joy', 0) > 0.7: 
            score += 15.0
        
        # Intent boosts - significant for scam intents
        scam_intents = ["requesting_payment", "phishing_attempt", "offering_prize", 
                        "impersonating_authority", "job_offer", "threatening"]
        if ml['intent'] in scam_intents:
            score += 25.0 + (ml['intent_conf'] * 20)
        elif ml['intent'] not in ["innocent_conversation"]: 
            score += (ml['intent_conf'] * 100 * settings.WEIGHT_INTENT)
        
        # Rule-based boost for multi-flag matches
        flags = rule.get('flags', {})
        flag_count = sum(1 for v in flags.values() if v)
        if flag_count >= 3:
            score += 20.0  # Multi-indicator boost
        
        return round(min(100.0, score), 2)

    def _classify_scam_type(self, intent: str, flags: Dict) -> str:
        """Step 2.4: Scam Type Classification [cite: 102-111]"""
        if intent == "requesting_payment" or flags["financial"]: return "Bank Fraud / UPI Scam"
        if intent == "phishing_attempt" or flags["url"]: return "Phishing"
        if intent == "offering_prize" or flags["offer"]: return "Prize/Lottery Scam"
        if intent == "job_offer": return "Job/Investment Scam"
        if intent == "impersonating_authority": return "Tax/Gov Impersonation"
        return "General Suspicion"