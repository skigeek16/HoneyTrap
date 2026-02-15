from typing import Dict, Any
from .rule_based import RuleBasedDetector
from .ml_ensemble import MLEnsembleDetector
from .llm_classifier import get_llm_classifier
from config import settings

class ScamDetectionEngine:
    def __init__(self):
        self.rule_detector = RuleBasedDetector()
        self.ml_detector = MLEnsembleDetector()
        self.llm_classifier = get_llm_classifier()
        
        # Scam intent labels from ML model
        self.scam_intents = {
            "requesting_payment", "threatening", "impersonating_authority",
            "offering_prize", "phishing_attempt", "job_offer",
            "investment_opportunity", "urgent_action_required", "identity_verification"
        }

    def evaluate(self, text: str) -> Dict[str, Any]:
        """Main pipeline: Triple-layer detection (Rule + ML + LLM)"""
        rule_res = self.rule_detector.analyze(text)
        ml_res = self.ml_detector.analyze(text)
        llm_res = self.llm_classifier.classify(text)
        final_score = self._calculate_ensemble_score(rule_res, ml_res, llm_res)
        
        # Lowered threshold for better recall
        threshold = 22
        decision = "ACTIVATE_AGENT" if final_score >= threshold else "POLITE_DECLINE"
        
        # Use LLM scam type if available and confident, else fall back to rule-based
        scam_type = self._classify_scam_type(rule_res)
        if llm_res.get('llm_enabled') and llm_res.get('llm_score', 0) > 60:
            scam_type = llm_res.get('llm_scam_type', scam_type)
        
        return {
            "is_scam": final_score >= threshold,
            "confidence_score": final_score,
            "decision": decision,
            "scam_type": scam_type,
            "details": {"rule_based": rule_res, "ml_ensemble": ml_res, "llm_classifier": llm_res}
        }

    def _calculate_ensemble_score(self, rule: Dict, ml: Dict, llm: Dict = None) -> float:
        """Triple-layer ensemble: Rule (50%) + ML (20%) + LLM (30%)"""
        
        # Get rule-based analysis
        rule_score = rule.get('rule_score', 0)
        scam_categories = rule.get('scam_categories', 0)
        legit_score = rule.get('legitimate_score', 0)
        flags = rule.get('flags', {})
        
        # Start with rule score
        score = rule_score * 0.5
        
        # ML signals
        phishing_prob = ml.get('phishing_prob', 0)
        intent = ml.get('intent', '')
        intent_conf = ml.get('intent_conf', 0)
        multi_prob = ml.get('multilingual_scam_prob', 0)
        
        # Phishing model boost
        if phishing_prob > 0.7:
            score += 15
        elif phishing_prob > 0.5:
            score += 10
        elif phishing_prob > 0.3:
            score += 4
        
        # Intent classification boost
        if intent in self.scam_intents and intent_conf > 0.5:
            score += 12
        elif intent in self.scam_intents and intent_conf > 0.3:
            score += 6
        elif intent == "innocent_conversation" and intent_conf > 0.5:
            score -= 12
        
        # Multilingual model boost
        if multi_prob > 0.6:
            score += 8
        elif multi_prob > 0.4:
            score += 4
        
        # === LLM Classifier Layer (30% weight) ===
        llm_score = 0
        llm_thinks_scam = False
        if llm and llm.get('llm_enabled'):
            llm_raw = llm.get('llm_score', 0)
            llm_score = llm_raw * 0.3  # 30% weight
            score += llm_score
            llm_thinks_scam = llm_raw >= 60
        
        # Cross-validation: if all 3 layers agree
        ml_thinks_scam = (phishing_prob > 0.5) or (intent in self.scam_intents and intent_conf > 0.4)
        rules_think_scam = scam_categories >= 1 and rule_score >= 25
        
        agreement_count = sum([ml_thinks_scam, rules_think_scam, llm_thinks_scam])
        
        if agreement_count >= 3:
            score += 20  # Triple agreement
        elif agreement_count >= 2:
            score += 12  # Double agreement
        elif agreement_count == 0:
            score -= 10  # All think innocent
        
        # Safety: If strong legitimate patterns and no scam patterns
        has_any_legit = any(k.startswith('legitimate_') and v for k, v in flags.items())
        has_any_scam = scam_categories > 0
        
        if has_any_legit and not has_any_scam and phishing_prob < 0.5 and not llm_thinks_scam:
            score = min(score, 20)  # Cap below threshold for pure legitimate
        
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