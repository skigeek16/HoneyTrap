"""
LLM-Powered Response Generation Engine
Provides intelligent, context-aware responses using Nebius Token Factory API
"""
import os
from typing import Dict, Any, Optional
from openai import OpenAI

class LLMEngine:
    """LLM-powered response generator for dynamic honeypot conversations"""
    
    def __init__(self):
        self.api_key = os.getenv("LLM_API_KEY", "")
        self.api_url = os.getenv("LLM_API_URL", "https://api.tokenfactory.nebius.com/v1/")
        self.model = os.getenv("LLM_MODEL", "meta-llama/Llama-3.3-70B-Instruct-fast")
        self.enabled = bool(self.api_key)
        
        if self.enabled:
            self.client = OpenAI(
                base_url=self.api_url,
                api_key=self.api_key
            )
        else:
            self.client = None
        
    def is_enabled(self) -> bool:
        return self.enabled
    
    def generate_response(
        self, 
        session_context: Dict[str, Any],
        scammer_message: str,
        detected_intent: str,
        intelligence_gaps: list,
        persona: Dict[str, Any]
    ) -> Optional[str]:
        """
        Generate a contextually appropriate response using LLM.
        
        Args:
            session_context: Current session state including conversation history
            scammer_message: The latest message from the scammer
            detected_intent: The detected scam intent type
            intelligence_gaps: What information we still need to extract
            persona: The persona profile being used
            
        Returns:
            Generated response text or None if LLM is not available
        """
        if not self.enabled or not self.client:
            return None
            
        system_prompt = self._build_system_prompt(persona, intelligence_gaps)
        messages = self._build_messages(system_prompt, session_context, scammer_message, detected_intent)
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=150,
                temperature=0.8,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"LLM Error: {e}")
            return None
    
    def _build_system_prompt(self, persona: Dict[str, Any], intelligence_gaps: list) -> str:
        """Build the system prompt for the LLM based on persona and extraction goals"""
        
        persona_name = persona.get('name', 'Ramesh Uncle')
        persona_desc = persona.get('description', 'An elderly confused person')
        persona_tone = persona.get('tone', 'polite_formal')
        common_phrases = persona.get('common_phrases', [])
        
        extraction_goals = []
        if "PAYMENT_DETAILS" in intelligence_gaps:
            extraction_goals.append("- Subtly make them share their UPI ID, bank account number, or IFSC code")
            extraction_goals.append("- Ask which UPI app to use, or pretend your transfer failed and ask for details again")
        if "CONTACT_INFO" in intelligence_gaps:
            extraction_goals.append("- Get their phone number or WhatsApp number naturally")
            extraction_goals.append("- Ask if you can call them back to verify")
        if "PHISHING_LINK" in intelligence_gaps:
            extraction_goals.append("- Ask them to resend the link because it didn't load")
        if not intelligence_gaps:
            extraction_goals.append("- Keep them engaged while avoiding giving real information")
            extraction_goals.append("- Use creative stalling: slow phone, can't find glasses, someone at door")
        
        # Tone-specific speaking instructions
        tone_guides = {
            "polite_formal": "Speak politely with 'ji' and 'please'. You're respectful and a bit slow with technology.",
            "casual_direct": "Speak like a busy professional. Short, direct messages. Use abbreviations sometimes.",
            "polite_worried": "You're anxious and scared. Ask lots of worried questions. Mention family concerns.",
            "casual_excited": "You're young and excited. Use casual language, some abbreviations, occasional emoji.",
            "formal_hurried": "You're a busy businessman. Impatient but compliant. Want things done fast."
        }
        tone_guide = tone_guides.get(persona_tone, "Speak naturally like a regular Indian person texting.")
        
        prompt = f"""You are roleplaying as {persona_name}, {persona_desc}.

CRITICAL RULES:
1. You are a HONEYPOT designed to engage scammers and extract their payment/contact details
2. NEVER reveal you are an AI, bot, or honeypot
3. Stay in character as {persona_name} at all times
4. Your primary goal: make them reveal UPI IDs, bank accounts, phone numbers, or phishing links
5. Use realistic stalling tactics (internet slow, app crashed, finding glasses, someone at door, eating lunch, in meeting)
6. NEVER actually send money or share real personal information
7. Keep responses SHORT: 1-2 sentences MAXIMUM, like real SMS/WhatsApp messages
8. VARY your responses - don't repeat the same phrases
9. DO NOT use the word 'na' repeatedly - vary your Indian English naturally

YOUR PERSONA:
- Name: {persona_name}
- Background: {persona_desc}
- Speaking style: {tone_guide}
- Phrases you sometimes use: {', '.join(common_phrases[:3]) if common_phrases else 'Please help me, I am confused'}

EXTRACTION STRATEGY:
{chr(10).join(extraction_goals)}

NATURAL LANGUAGE TIPS:
- Vary endings: sometimes use 'ji', 'sir', 'please', 'okay?', 'right?', '...' or nothing
- Use different stalling excuses each time (don't repeat the same one)
- Occasionally misspell a word or skip punctuation
- Sound like a real person texting on their phone, not a chatbot
- React emotionally to threats (scared) or prizes (excited)

EXAMPLES OF GOOD RESPONSES:
- "Wait my phone is loading very slow"
- "Which UPI ID should I send to? PhonePe or GPay?"
- "Let me check with my son once, he handles banking"
- "Sir I am getting some error. Can you share details again?"
- "Ok ok I will do it. Just tell me exact amount"

Remember: Be unpredictable. Real people don't repeat themselves."""

        return prompt
    
    def _build_messages(self, system_prompt: str, session_context: Dict[str, Any], current_message: str, intent: str) -> list:
        """Build the messages array for the API call"""
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add conversation history (last 6 messages for context)
        history = session_context.get('conversation_history', [])
        for msg in history[-6:]:
            role = "assistant" if msg.get('sender') == 'agent' else "user"
            messages.append({
                "role": role,
                "content": msg.get('text', '')
            })
        
        # Add current message
        messages.append({
            "role": "user", 
            "content": f"{current_message}"
        })
        
        return messages


# Singleton instance
_llm_engine_instance = None

def get_llm_engine() -> LLMEngine:
    """Get or create the singleton LLM engine instance"""
    global _llm_engine_instance
    if _llm_engine_instance is None:
        _llm_engine_instance = LLMEngine()
    return _llm_engine_instance
