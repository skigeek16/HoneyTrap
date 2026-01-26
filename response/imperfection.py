import random
import re
from personas.models import ImperfectionProfile

class ImperfectionEngine:
    def __init__(self):
        self.adj_keys = {'a': 'qsxz', 'b': 'vghn', 'e': 'wsdr'} # Partial list for brevity

    def apply_imperfections(self, text: str, profile: ImperfectionProfile, emotion: str) -> str:
        if random.random() < profile.text_speak_probability: # Layer 1
            text = " ".join([random.choice(self.text_speak_map.get(w.lower(), [w])) for w in text.split()])
        
        if random.random() < profile.indian_slangs: # Layer 5
            text += " na" if random.random() < 0.5 else ""
            
        if not re.search(r'\d', text) and random.random() < profile.typo_probability: # Layer 3
            idx = random.randint(0, len(text)-1)
            text = text[:idx] + text[idx] + text[idx:] # Simple double letter typo

        if random.random() < profile.missing_punctuation: # Layer 2
            text = text.rstrip(".")

        return text

    def calculate_delay(self, text: str) -> float:
        return round(len(text) * 0.2 + random.uniform(2.0, 5.0), 2)