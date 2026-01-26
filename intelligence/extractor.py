import re
from typing import List
from transformers import pipeline
from keybert import KeyBERT
from .models import Entity

class ExtractionEngine:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ExtractionEngine, cls).__new__(cls)
            cls._instance._load_resources()
        return cls._instance

    def _load_resources(self):
        print("🕵️ Loading Intelligence Extraction Models...")
        self.ner_pipe = pipeline("ner", model="dslim/bert-base-NER", aggregation_strategy="simple")
        self.kw_model = KeyBERT('distilbert-base-nli-mean-tokens')
        self.patterns = {
            "UPI_ID": re.compile(r'[a-zA-Z0-9.\-_]{3,}@[a-zA-Z]{3,}'), 
            "PHONE_IN": re.compile(r'(?:\+91[\-\s]?)?[6-9]\d{9}'),
            "BANK_ACC": re.compile(r'\b\d{9,18}\b'),
            "IFSC": re.compile(r'^[A-Z]{4}0[A-Z0-9]{6}$'), 
            "URL": re.compile(r'(https?://\S+|www\.\S+|bit\.ly/\S+)'),
            "EMAIL": re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'),
            "PAN": re.compile(r'[A-Z]{5}[0-9]{4}[A-Z]{1}'),
            "AADHAAR": re.compile(r'\b\d{4}\s?\d{4}\s?\d{4}\b'),
            "AMOUNT": re.compile(r'(?:Rs\.?|INR|₹)\s?[\d,]+'),
            "CRYPTO": re.compile(r'\b(bc1|[13])[a-zA-Z0-9]{25,39}\b')
        }
        print("✅ Extraction Engine Ready.")

    def extract_regex(self, text: str, turn: int) -> List[Entity]:
        entities = []
        for type_name, pattern in self.patterns.items():
            matches = pattern.findall(text)
            for match in matches:
                clean_val = match.strip() if isinstance(match, str) else match[0].strip()
                category = "TACTICAL"
                if type_name in ["UPI_ID", "BANK_ACC", "CRYPTO"]: category = "PRIMARY"
                elif type_name in ["PHONE_IN", "EMAIL", "URL"]: category = "SECONDARY"
                
                entities.append(Entity(
                    value=clean_val, type=type_name, category=category,
                    confidence=1.0, source_turn=turn, is_validated=self._validate_entity(type_name, clean_val)
                ))
        return entities

    def extract_ner(self, text: str, turn: int) -> List[Entity]:
        entities = []
        ner_results = self.ner_pipe(text)
        for res in ner_results:
            mapped_type = {"ORG": "ORGANIZATION", "PER": "PERSON_NAME", "LOC": "LOCATION"}.get(res['entity_group'], "UNKNOWN")
            if mapped_type != "UNKNOWN":
                entities.append(Entity(
                    value=res['word'], type=mapped_type, category="TACTICAL",
                    confidence=float(res['score']), source_turn=turn
                ))
        return entities

    def extract_keywords(self, text: str, turn: int) -> List[Entity]:
        keywords = self.kw_model.extract_keywords(text, keyphrase_ngram_range=(1, 2), stop_words='english', top_n=3)
        return [Entity(value=kw, type="KEYWORD", category="TACTICAL", confidence=score, source_turn=turn) for kw, score in keywords]

    def _validate_entity(self, type_name: str, value: str) -> bool:
        if type_name == "UPI_ID": return "@" in value
        if type_name == "PHONE_IN":
            clean = re.sub(r'\D', '', value)
            if len(clean) > 10: clean = clean[-10:]
            return clean and clean[0] in ['6', '7', '8', '9']
        if type_name == "IFSC": return len(value) == 11 and value[4] == '0'
        return True