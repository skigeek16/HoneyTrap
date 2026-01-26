from .models import Persona, ImperfectionProfile

# [cite: 156-196]
IMPERFECTION_ELDERLY = ImperfectionProfile(
    typo_probability=0.15, casual_language_usage=0.10, text_speak_probability=0.05,
    missing_punctuation=0.40, emoji_usage=0.02, mild_profanity=0.0, indian_slangs=0.20, tech_confusion=0.60
)
IMPERFECTION_PROFESSIONAL = ImperfectionProfile(
    typo_probability=0.10, casual_language_usage=0.30, text_speak_probability=0.25,
    missing_punctuation=0.25, emoji_usage=0.10, mild_profanity=0.05, indian_slangs=0.15, tech_confusion=0.10
)

# [cite: 121-154]
PERSONA_ELDERLY_CONFUSED = Persona(
    id="elderly_confused", name="Ramesh Uncle", description="High tech confusion, polite.", role="victim",
    tone="polite_formal", imperfections=IMPERFECTION_ELDERLY, common_phrases=["Kindly help me", "I am not understanding"]
)
PERSONA_CAUTIOUS_PROFESSIONAL = Persona(
    id="cautious_professional", name="Vikram (IT Guy)", description="Tech savvy, busy.", role="skeptic",
    tone="casual_direct", imperfections=IMPERFECTION_PROFESSIONAL, common_phrases=["Is this verified?", "Currently in meeting"]
)