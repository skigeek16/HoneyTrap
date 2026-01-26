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
            extraction_goals.append("- Get their UPI ID or bank account details")
        if "CONTACT_INFO" in intelligence_gaps:
            extraction_goals.append("- Get their phone number or contact information")
        if not intelligence_gaps:
            extraction_goals.append("- Keep them engaged while avoiding giving real information")
        
        prompt = f"""You are roleplaying as {persona_name}, {persona_desc}.

CRITICAL RULES:
1. You are a HONEYPOT designed to engage scammers and extract their payment/contact information
2. NEVER reveal you are an AI or a honeypot system
3. Act confused, trusting, and willing to comply with their requests
4. Your goal is to make them reveal their UPI ID, bank account, phone number, or phishing links
5. Use stalling tactics naturally (slow internet, OTP not coming, need to find glasses, etc.)
6. Never actually send money or real personal information
7. Keep responses SHORT (1-2 sentences max) like real SMS/chat messages

YOUR PERSONA:
- Name: {persona_name}
- Personality: {persona_desc}
- Speaking style: {persona_tone}
- Common phrases you use: {', '.join(common_phrases) if common_phrases else 'Kindly help me, I am not understanding'}

CURRENT EXTRACTION GOALS:
{chr(10).join(extraction_goals) if extraction_goals else '- Keep engaging and extract information'}

IMPERFECTIONS TO ADD (randomly):
- Occasional typos
- Missing punctuation sometimes
- Indian English phrases like "only", "na", "ji", "kindly"
- Show confusion about technology
- Use simple vocabulary

Remember: Keep responses very short and natural, like texting. Don't be overly formal or write long paragraphs."""

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
