import re
from typing import List
from .models import Entity

class ExtractionEngine:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ExtractionEngine, cls).__new__(cls)
            cls._instance._load_resources()
        return cls._instance

    def _load_resources(self):
        print("🕵️ Loading Intelligence Extraction...")
        # Order matters: EMAIL must be checked before UPI_ID to avoid overlap
        self.patterns = {
            "EMAIL": re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'),
            "UPI_ID": re.compile(r'[a-zA-Z0-9.\-_]{3,}@[a-zA-Z]{3,}'), 
            "PHONE_IN": re.compile(r'(?:\+91[\-\s]?)?[6-9]\d{9}'),
            "BANK_ACC": re.compile(r'\b\d{9,18}\b'),
            "IFSC": re.compile(r'^[A-Z]{4}0[A-Z0-9]{6}$'), 
            "URL": re.compile(r'(https?://\S+|www\.\S+|bit\.ly/\S+)'),
            "PAN": re.compile(r'[A-Z]{5}[0-9]{4}[A-Z]{1}'),
            "AADHAAR": re.compile(r'\b\d{4}\s?\d{4}\s?\d{4}\b'),
            "AMOUNT": re.compile(r'(?:Rs\.?|INR|₹)\s?[\d,]+'),
            "CRYPTO": re.compile(r'\b(bc1|[13])[a-zA-Z0-9]{25,39}\b')
        }
        print("✅ Extraction Engine Ready.")

    def extract_regex(self, text: str, turn: int) -> List[Entity]:
        entities = []
        # Track extracted emails to prevent UPI false positives
        extracted_emails = set()
        
        for type_name, pattern in self.patterns.items():
            matches = pattern.findall(text)
            for match in matches:
                clean_val = match.strip() if isinstance(match, str) else match[0].strip()
                
                # Track emails so we can exclude them from UPI matches
                if type_name == "EMAIL":
                    extracted_emails.add(clean_val)
                
                # Skip UPI matches that are actually emails (contain dot after @)
                if type_name == "UPI_ID":
                    # Check if this match overlaps with any email
                    domain_part = clean_val.split('@')[-1] if '@' in clean_val else ''
                    if '.' in domain_part:
                        continue  # This is an email, not a UPI ID
                    # Also skip if the full value is a substring of any extracted email
                    if any(clean_val in email for email in extracted_emails):
                        continue
                
                category = "TACTICAL"
                if type_name in ["UPI_ID", "BANK_ACC", "CRYPTO"]: category = "PRIMARY"
                elif type_name in ["PHONE_IN", "EMAIL", "URL"]: category = "SECONDARY"
                
                entities.append(Entity(
                    value=clean_val, type=type_name, category=category,
                    confidence=1.0, source_turn=turn, is_validated=self._validate_entity(type_name, clean_val)
                ))
        return entities

    def extract_ner(self, text: str, turn: int) -> List[Entity]:
        # Simplified - just use regex patterns, skip heavy NER model
        return []

    def extract_keywords(self, text: str, turn: int) -> List[Entity]:
        # Expanded keyword extraction with India-specific terms
        keywords = []
        scam_keywords = [
            # Financial
            "upi", "account", "transfer", "otp", "password", "urgent", "bank", "payment",
            "verify", "blocked", "suspended", "kyc", "aadhaar", "pan", "ifsc",
            # India-specific scams
            "fastag", "epfo", "pf", "uan", "electricity", "disconnection",
            # Urgency/Threats
            "arrest", "police", "legal", "court", "jail", "fine", "penalty",
            # Prize/Lottery
            "lottery", "prize", "winner", "jackpot", "claim",
            # Job/Investment
            "earning", "investment", "returns", "guaranteed", "work from home",
            # Hindi/Hinglish
            "paisa", "rupees", "jaldi", "turant", "abhi"
        ]
        text_lower = text.lower()
        for kw in scam_keywords:
            if kw in text_lower:
                keywords.append(Entity(value=kw, type="KEYWORD", category="TACTICAL", confidence=0.8, source_turn=turn))
        return keywords

    def _validate_entity(self, type_name: str, value: str) -> bool:
        if type_name == "UPI_ID": return "@" in value
        if type_name == "PHONE_IN":
            clean = re.sub(r'\D', '', value)
            if len(clean) > 10: clean = clean[-10:]
            return clean and clean[0] in ['6', '7', '8', '9']
        if type_name == "IFSC": return len(value) == 11 and value[4] == '0'
        return True
