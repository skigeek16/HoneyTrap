from typing import Dict, Any
from .rule_based import RuleBasedDetector
from .ml_ensemble import MLEnsembleDetector
from config import settings

class ScamDetectionEngine:
    def __init__(self):
        self.rule_detector = RuleBasedDetector()
        self.ml_detector = MLEnsembleDetector()
        
        # Scam intent labels from ML model
        self.scam_intents = {
            "requesting_payment", "threatening", "impersonating_authority",
            "offering_prize", "phishing_attempt", "job_offer",
            "investment_opportunity", "urgent_action_required", "identity_verification"
        }

    def evaluate(self, text: str) -> Dict[str, Any]:
        """Main pipeline with pattern-based classification"""
        rule_res = self.rule_detector.analyze(text)
        ml_res = self.ml_detector.analyze(text)
        final_score = self._calculate_ensemble_score(rule_res, ml_res)
        
        # Threshold for pattern-based classification
        threshold = 30
        decision = "ACTIVATE_AGENT" if final_score >= threshold else "POLITE_DECLINE"
        
        return {
            "is_scam": final_score >= threshold,
            "confidence_score": final_score,
            "decision": decision,
            "scam_type": self._classify_scam_type(rule_res),
            "details": {"rule_based": rule_res, "ml_ensemble": ml_res}
        }

    def _calculate_ensemble_score(self, rule: Dict, ml: Dict) -> float:
        """Ensemble scoring with pattern-based rules as primary signal"""
        
        # Get rule-based analysis
        rule_score = rule.get('rule_score', 0)
        scam_categories = rule.get('scam_categories', 0)
        legit_score = rule.get('legitimate_score', 0)
        flags = rule.get('flags', {})
        
        # Start with rule score (pattern-based is more reliable)
        score = rule_score * 0.7
        
        # ML signals as secondary validation
        phishing_prob = ml.get('phishing_prob', 0)
        intent = ml.get('intent', '')
        intent_conf = ml.get('intent_conf', 0)
        multi_prob = ml.get('multilingual_scam_prob', 0)
        
        # Phishing model boost
        if phishing_prob > 0.7:
            score += 20
        elif phishing_prob > 0.5:
            score += 12
        elif phishing_prob > 0.3:
            score += 5
        
        # Intent classification boost
        if intent in self.scam_intents and intent_conf > 0.5:
            score += 15
        elif intent in self.scam_intents and intent_conf > 0.3:
            score += 8
        elif intent == "innocent_conversation" and intent_conf > 0.5:
            score -= 15
        
        # Multilingual model boost
        if multi_prob > 0.6:
            score += 10
        elif multi_prob > 0.4:
            score += 5
        
        # Cross-validation: if both rule patterns and ML agree
        ml_thinks_scam = (phishing_prob > 0.5) or (intent in self.scam_intents and intent_conf > 0.4)
        rules_think_scam = scam_categories >= 1 and rule_score >= 25
        
        if ml_thinks_scam and rules_think_scam:
            score += 15  # Strong agreement
        elif not ml_thinks_scam and not rules_think_scam:
            score -= 10  # Both think innocent
        
        # Safety: If strong legitimate patterns and no scam patterns
        has_any_legit = any(k.startswith('legitimate_') and v for k, v in flags.items())
        has_any_scam = scam_categories > 0
        
        if has_any_legit and not has_any_scam and phishing_prob < 0.5:
            score = min(score, 25)  # Cap below threshold for pure legitimate
        
        return round(max(0.0, min(100.0, score)), 2)

    def _classify_scam_type(self, rule_res: Dict) -> str:
        """Classify based on detected patterns"""
        flags = rule_res.get('flags', {})
        
        if flags.get('sensitive_info_request'):
            return "Financial Data Theft"
        if flags.get('prize_claim'):
            return "Prize/Lottery Scam"
        if flags.get('threat_language'):
            return "Threat/Extortion"
        if flags.get('authority_impersonation'):
            return "Authority Impersonation"
        if flags.get('job_scam'):
            return "Job/Investment Scam"
        if flags.get('security_scam'):
            return "Security/Phishing Scam"
        if flags.get('payment_demand'):
            return "Payment Fraud"
        return "Suspicious Activity"