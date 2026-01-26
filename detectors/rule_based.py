import re
from typing import Dict, Tuple

class RuleBasedDetector:
    def __init__(self):
        self.keywords = {
            "financial": {"upi", "bank", "payment", "account", "transfer", "rs.", "inr"},
            "urgency": {"immediately", "now", "urgent", "today", "within 24 hours"},
            "authority": {"government", "police", "tax", "rbi", "it department", "court"},
            "threat": {"blocked", "suspended", "arrested", "penalty", "legal action"},
            "offer": {"won", "lottery", "prize", "reward", "free", "gift"}
        }
        self.url_pattern = re.compile(r'(https?://\S+|www\.\S+|bit\.ly/\S+)') # [cite: 39]

    def analyze(self, text: str) -> Dict:
        """Execute scans and apply multipliers [cite: 41-44]"""
        text_lower = text.lower()
        score = 0.0
        flags = {k: any(w in text_lower for w in v) for k, v in self.keywords.items()}
        flags["url"] = bool(self.url_pattern.search(text_lower))

        if flags["financial"]: score += 10
        if flags["urgency"]: score += 10
        if flags["authority"]: score += 10
        if flags["threat"]: score += 10
        if flags["offer"]: score += 10
        if flags["url"]: score += 15
        if flags["financial"] and flags["urgency"]: score *= 1.5
        if flags["authority"] and flags["threat"]: score *= 2.0

        return {"rule_score": min(100.0, score), "flags": flags}