import random
import re
from personas.models import ImperfectionProfile

class ImperfectionEngine:
    def __init__(self):
        # Adjacent keyboard keys for realistic typos
        self.adj_keys = {
            'a': 'qwsz', 'b': 'vghn', 'c': 'xdfv', 'd': 'erfcxs', 'e': 'wsdr',
            'f': 'rtgvcd', 'g': 'tyhbvf', 'h': 'yujnbg', 'i': 'ujko', 'j': 'uikmnh',
            'k': 'iolmj', 'l': 'opk', 'm': 'njk', 'n': 'bhjm', 'o': 'iklp',
            'p': 'ol', 'q': 'wa', 'r': 'edft', 's': 'wedxza', 't': 'rfgy',
            'u': 'yhji', 'v': 'cfgb', 'w': 'qase', 'x': 'zsdc', 'y': 'tghu', 'z': 'asx'
        }
        
        # Text speak conversions
        self.text_speak_map = {
            "you": ["u", "you"], "your": ["ur", "your"], "are": ["r", "are"],
            "okay": ["ok", "okay", "k"], "please": ["pls", "plz", "please"],
            "thanks": ["thx", "thnks", "thanks"], "thank": ["thk", "thank"],
            "because": ["coz", "bcz", "because"], "before": ["b4", "before"],
            "tomorrow": ["tmrw", "2moro", "tomorrow"], "today": ["2day", "today"],
            "what": ["wat", "wht", "what"], "with": ["wid", "with"],
            "the": ["d", "the"], "this": ["dis", "this"], "that": ["dat", "that"],
            "going": ["goin", "going"], "doing": ["doin", "doing"],
            "something": ["smth", "something"], "someone": ["sm1", "someone"],
            "message": ["msg", "message"], "money": ["$", "money"],
            "minutes": ["mins", "minutes"], "seconds": ["secs", "seconds"],
            "problem": ["prob", "problem"], "information": ["info", "information"],
            "account": ["acc", "acct", "account"], "number": ["no.", "num", "number"],
            "understand": ["undrstnd", "understand"], "know": ["kno", "know"]
        }
        
        # Indian slang phrases to append
        self.indian_slangs = [
            " na", " ji", " yaar", " bhai", " sir", " madam",
            " only", " actually", " basically", " kindly"
        ]
        
        # Emotion-based modifiers
        self.emotion_prefixes = {
            "confusion": ["Hmm...", "Wait...", "I don't...", "Sorry but...", "Uh..."],
            "fear": ["Oh no...", "What?!", "Is this real?", "Please..."],
            "trust": ["Okay okay", "Yes yes", "Sure sure", "Right right"],
            "neutral": [""]
        }
        
        # Common elderly typing patterns
        self.elderly_patterns = {
            "ellipsis_overuse": "...",
            "caps_confusion": True,
            "space_before_punctuation": True
        }

    def apply_imperfections(self, text: str, profile: ImperfectionProfile, emotion: str) -> str:
        # Layer 1: Text speak conversion
        if random.random() < profile.text_speak_probability:
            words = text.split()
            new_words = []
            for w in words:
                lower_w = w.lower().strip('.,!?')
                if lower_w in self.text_speak_map and random.random() < 0.5:
                    replacement = random.choice(self.text_speak_map[lower_w])
                    new_words.append(replacement)
                else:
                    new_words.append(w)
            text = " ".join(new_words)
        
        # Layer 2: Missing punctuation
        if random.random() < profile.missing_punctuation:
            text = text.rstrip(".!?")
        
        # Layer 3: Typos (avoid in numbers)
        if random.random() < profile.typo_probability and len(text) > 10:
            words = text.split()
            if len(words) > 2:
                idx = random.randint(0, len(words) - 1)
                word = words[idx]
                if len(word) > 3 and not any(c.isdigit() for c in word):
                    char_idx = random.randint(1, len(word) - 2)
                    char = word[char_idx].lower()
                    if char in self.adj_keys:
                        typo_char = random.choice(self.adj_keys[char])
                        word = word[:char_idx] + typo_char + word[char_idx + 1:]
                        words[idx] = word
                text = " ".join(words)
        
        # Layer 4: Double letters (common typing mistake)
        if random.random() < profile.typo_probability * 0.5:
            if len(text) > 5:
                idx = random.randint(2, len(text) - 3)
                if text[idx].isalpha():
                    text = text[:idx] + text[idx] + text[idx:]
        
        # Layer 5: Indian slangs
        if random.random() < profile.indian_slangs:
            slang = random.choice(self.indian_slangs)
            # Append at end or after first sentence
            if "." in text and random.random() < 0.5:
                parts = text.split(".", 1)
                text = parts[0] + slang + "." + (parts[1] if len(parts) > 1 else "")
            else:
                text = text.rstrip(".!?") + slang
        
        # Layer 6: Tech confusion for elderly personas
        if random.random() < profile.tech_confusion:
            confusion_phrases = [
                " I am not understanding this app properly.",
                " My phone is very slow.",
                " How to do this?",
                " My grandson usually helps me with this.",
                " The screen is showing something else."
            ]
            if random.random() < 0.3:
                text += random.choice(confusion_phrases)
        
        # Layer 7: Casual language
        if random.random() < profile.casual_language_usage:
            casual_starters = ["See ", "Look ", "Actually ", "Basically ", "Like "]
            if random.random() < 0.3 and not text.startswith(tuple(casual_starters)):
                text = random.choice(casual_starters) + text[0].lower() + text[1:]
        
        # Layer 8: Emoji usage
        if random.random() < profile.emoji_usage:
            emojis = ["🙏", "😊", "😅", "🤔", "👍", "✅", "❓"]
            text += " " + random.choice(emojis)
        
        return text.strip()

    def calculate_delay(self, text: str) -> float:
        """Calculate realistic typing delay based on text length"""
        base_delay = len(text) * 0.08  # ~12 chars per second
        thinking_delay = random.uniform(1.0, 3.0)
        hesitation = random.uniform(0, 2.0) if random.random() < 0.3 else 0
        return round(base_delay + thinking_delay + hesitation, 2)