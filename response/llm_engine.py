"""
LLM-Powered Response Generation Engine
Provides intelligent, context-aware responses using an LLM API
"""
import os
import json
import httpx
from typing import Dict, Any, Optional
from config import settings

class LLMEngine:
    """LLM-powered response generator for dynamic honeypot conversations"""
    
    def __init__(self):
        self.api_key = os.getenv("LLM_API_KEY", "")
        self.api_url = os.getenv("LLM_API_URL", "")  # User will provide this
        self.model = os.getenv("LLM_MODEL", "")  # User will provide this
        self.enabled = bool(self.api_key and self.api_url)
        
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
        if not self.enabled:
            return None
            
        system_prompt = self._build_system_prompt(persona, intelligence_gaps)
        conversation_context = self._build_conversation_context(session_context)
        
        try:
            response = self._call_llm_api(
                system_prompt=system_prompt,
                conversation=conversation_context,
                current_message=scammer_message,
                intent=detected_intent
            )
            return response
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
    
    def _build_conversation_context(self, session_context: Dict[str, Any]) -> list:
        """Build conversation history for LLM context"""
        messages = []
        history = session_context.get('conversation_history', [])
        
        # Include last 6 messages for context
        for msg in history[-6:]:
            role = "assistant" if msg.get('sender') == 'agent' else "user"
            messages.append({
                "role": role,
                "content": msg.get('text', '')
            })
        
        return messages
    
    def _call_llm_api(
        self, 
        system_prompt: str, 
        conversation: list, 
        current_message: str,
        intent: str
    ) -> str:
        """Make the actual API call to the LLM service"""
        
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(conversation)
        messages.append({
            "role": "user", 
            "content": f"[Scammer's message - detected intent: {intent}]\n{current_message}"
        })
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": 150,  # Keep responses short
            "temperature": 0.8,  # Some creativity for natural responses
        }
        
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                self.api_url,
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            
            result = response.json()
            # Handle both OpenAI and compatible API formats
            if "choices" in result:
                return result["choices"][0]["message"]["content"].strip()
            elif "response" in result:
                return result["response"].strip()
            elif "content" in result:
                return result["content"].strip()
            else:
                return result.get("text", "").strip()


# Singleton instance
_llm_engine_instance = None

def get_llm_engine() -> LLMEngine:
    """Get or create the singleton LLM engine instance"""
    global _llm_engine_instance
    if _llm_engine_instance is None:
        _llm_engine_instance = LLMEngine()
    return _llm_engine_instance
