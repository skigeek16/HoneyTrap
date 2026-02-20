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
        # Order matters: BANK_ACC before PHONE_IN so phone-substring check works
        # EMAIL before UPI_ID to detect email vs UPI overlap
        self.patterns = {
            "EMAIL": re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'),
            "BANK_ACC": re.compile(r'\b\d{11,18}\b'),
            "PHONE_IN": re.compile(r'(?:\+91[\-\s]?)?[6-9]\d{9}'),
            "UPI_ID": re.compile(r'[a-zA-Z0-9.\-_]{3,}@[a-zA-Z]{3,}'),
            "IFSC": re.compile(r'^[A-Z]{4}0[A-Z0-9]{6}$'), 
            "URL": re.compile(r'(https?://\S+|www\.\S+|bit\.ly/\S+)'),
            "PAN": re.compile(r'[A-Z]{5}[0-9]{4}[A-Z]{1}'),
            "AADHAAR": re.compile(r'\b\d{4}\s?\d{4}\s?\d{4}\b'),
            "AMOUNT": re.compile(r'(?:Rs\.?|INR|₹)\s?[\d,]+'),
            "CRYPTO": re.compile(r'\b(bc1|[13])[a-zA-Z0-9]{25,39}\b'),
            # Case/Reference IDs (e.g., CASE-12345, REF-ABC123, FIR-2025-001)
            # Require separator after prefix to avoid matching bare words like "Reference"
            "CASE_ID": re.compile(r'\b(?:CASE|REF|FIR|COMPLAINT|REFERENCE|TICKET|CR|SR|INC)[\-#:_]\s*[A-Z0-9][A-Z0-9\-]{3,20}\b', re.IGNORECASE),
            # Policy Numbers (e.g., POL-123456, LIC-12345678, POLICY-ABC123)
            "POLICY_NUM": re.compile(r'\b(?:POL|POLICY|LIC|INSURANCE|PLAN)[\-#:_]\s*[A-Z0-9][A-Z0-9\-]{4,20}\b', re.IGNORECASE),
            # Order Numbers (e.g., ORD-12345, ORDER-ABC123, OD-123456789)
            "ORDER_NUM": re.compile(r'\b(?:ORD|ORDER|OD|ORDERID|ORDER_ID|INVOICE|INV)[\-#:_]\s*[A-Z0-9][A-Z0-9\-]{4,20}\b', re.IGNORECASE),
        }
        print("✅ Extraction Engine Ready.")

    def extract_regex(self, text: str, turn: int) -> List[Entity]:
        entities = []
        # Track extracted values to prevent cross-type false positives
        extracted_emails = set()
        extracted_phone_digits = set()
        extracted_bank_accs = set()
        
        for type_name, pattern in self.patterns.items():
            matches = pattern.findall(text)
            for match in matches:
                clean_val = match.strip() if isinstance(match, str) else match[0].strip()
                
                # Clean URLs: strip trailing punctuation
                if type_name == "URL":
                    clean_val = clean_val.rstrip('.,;:!?)\"\'')
                
                # Track emails to exclude from UPI matches
                if type_name == "EMAIL":
                    extracted_emails.add(clean_val)
                
                # Track phone digits for exact-match dedup
                if type_name == "PHONE_IN":
                    digits_only = re.sub(r'\D', '', clean_val)
                    if len(digits_only) > 10:
                        digits_only = digits_only[-10:]
                    extracted_phone_digits.add(digits_only)
                
                # Skip UPI matches that are actually emails
                if type_name == "UPI_ID":
                    domain_part = clean_val.split('@')[-1] if '@' in clean_val else ''
                    if '.' in domain_part:
                        continue
                    if any(clean_val in email for email in extracted_emails):
                        continue
                
                # Skip BANK_ACC matches that are exactly 10-digit phone numbers
                # But KEEP longer bank account numbers even if they contain phone digits
                if type_name == "BANK_ACC":
                    if len(clean_val) == 10 and clean_val in extracted_phone_digits:
                        continue
                    extracted_bank_accs.add(clean_val)
                
                category = "TACTICAL"
                if type_name in ["UPI_ID", "BANK_ACC", "CRYPTO"]: category = "PRIMARY"
                elif type_name in ["PHONE_IN", "EMAIL", "URL"]: category = "SECONDARY"
                elif type_name in ["CASE_ID", "POLICY_NUM", "ORDER_NUM"]: category = "SECONDARY"
                
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
