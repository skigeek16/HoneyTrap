"""
LLM-Based Scam Classifier — Third Detection Layer
Uses Llama 3.3 70B via Nebius to classify messages that regex can't catch.
"""
import os
import json
import re
from typing import Dict, Any, Optional
from openai import OpenAI


class LLMScamClassifier:
    """Uses LLM to detect scams that bypass regex patterns"""
    
    def __init__(self):
        self.api_key = os.getenv("LLM_API_KEY", "")
        self.api_url = os.getenv("LLM_API_URL", "https://api.tokenfactory.nebius.com/v1/")
        self.model = os.getenv("LLM_MODEL", "meta-llama/Llama-3.3-70B-Instruct-fast")
        self.enabled = bool(self.api_key)
        
        if self.enabled:
            self.client = OpenAI(base_url=self.api_url, api_key=self.api_key)
        else:
            self.client = None
    
    def is_enabled(self) -> bool:
        return self.enabled
    
    def classify(self, text: str) -> Dict[str, Any]:
        """
        Classify a message using LLM.
        Returns scam score (0-100), scam type, and reasoning.
        """
        if not self.enabled or not self.client:
            return {"llm_score": 0, "llm_scam_type": "unknown", "llm_reasoning": "LLM disabled", "llm_enabled": False}
        
        prompt = f"""You are an expert Indian cybercrime analyst. Analyze this SMS/chat message and determine if it is a SCAM.

MESSAGE: "{text}"

SCAM CATEGORIES TO CHECK:
1. KYC/Banking fraud (fake bank KYC updates, account blocking threats)
2. Prize/Lottery scam (fake winnings, processing fees)
3. Job/Investment scam (work-from-home, guaranteed returns, MLM)
4. Authority impersonation (fake police, government, RBI)
5. Phishing (suspicious links, OTP requests, credential theft)
6. UPI/Payment fraud (fake payment requests, QR code scams)
7. Tech support scam (fake virus alerts, remote access)
8. Charity/Emergency scam (fake donations, urgent help)
9. Delivery/Package scam (fake courier, customs fee)
10. Loan/Insurance scam (pre-approved loans, fake insurance)
11. Romance/Social engineering (building trust to extract money)
12. Electricity/Utility scam (bill disconnection threats)
13. FASTag/Vehicle scam (fake toll charges, vehicle seizure)

ANALYSIS CRITERIA:
- Urgency language ("immediately", "within 24 hours", "last chance")
- Financial requests (fees, payments, OTP, bank details)
- Suspicious links or contact methods
- Impersonation of trusted entities
- Too-good-to-be-true offers
- Emotional manipulation (fear, greed, excitement)
- Subtle/paraphrased versions of common scams

Reply in EXACTLY this JSON format, nothing else:
{{"score": <0-100>, "type": "<scam category or legitimate>", "reason": "<one line explanation>"}}"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a scam detection expert. Reply ONLY with valid JSON, no markdown, no explanation."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=100,
                temperature=0.1,  # Low temp for consistent classification
            )
            
            raw = response.choices[0].message.content.strip()
            # Clean up potential markdown formatting
            raw = re.sub(r'^```(?:json)?\s*', '', raw)
            raw = re.sub(r'\s*```$', '', raw)
            
            result = json.loads(raw)
            
            return {
                "llm_score": min(100, max(0, float(result.get("score", 0)))),
                "llm_scam_type": result.get("type", "unknown"),
                "llm_reasoning": result.get("reason", ""),
                "llm_enabled": True
            }
        except json.JSONDecodeError as e:
            print(f"LLM Classifier JSON parse error: {e}, raw: {raw}")
            return {"llm_score": 0, "llm_scam_type": "parse_error", "llm_reasoning": str(e), "llm_enabled": True}
        except Exception as e:
            print(f"LLM Classifier error: {e}")
            return {"llm_score": 0, "llm_scam_type": "error", "llm_reasoning": str(e), "llm_enabled": True}


# Singleton
_classifier_instance = None

def get_llm_classifier() -> LLMScamClassifier:
    global _classifier_instance
    if _classifier_instance is None:
        _classifier_instance = LLMScamClassifier()
    return _classifier_instance

