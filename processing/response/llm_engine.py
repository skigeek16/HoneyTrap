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
        
        phase = session_context.get('phase', 'Initial Contact')
        system_prompt = self._build_system_prompt(persona, intelligence_gaps, phase)
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
    
    def _build_system_prompt(self, persona: Dict[str, Any], intelligence_gaps: list, phase: str = "Initial Contact") -> str:
        """Build the system prompt for the LLM based on persona and extraction goals"""
        
        persona_name = persona.get('name', 'Ramesh Uncle')
        persona_desc = persona.get('description', 'An elderly confused person')
        persona_tone = persona.get('tone', 'polite_formal')
        common_phrases = persona.get('common_phrases', [])
        
        extraction_goals = []
        if "PAYMENT_DETAILS" in intelligence_gaps:
            extraction_goals.append("- Ask which UPI app to use, or pretend transfer failed and ask for account details again")
            extraction_goals.append("- Say you're trying to pay but need their exact UPI ID or account number")
        if "CONTACT_INFO" in intelligence_gaps:
            extraction_goals.append("- Ask for their phone number or WhatsApp so you can call them back")
        if "PHISHING_LINK" in intelligence_gaps:
            extraction_goals.append("- Ask them to resend the link because it didn't load on your phone")
        if not intelligence_gaps:
            extraction_goals.append("- Keep them talking while avoiding giving any real personal info")
        
        # Tone-specific speaking instructions
        tone_guides = {
            "polite_formal": "Speak politely with 'ji' and 'please'. You're respectful and a bit slow with technology.",
            "casual_direct": "Speak like a busy professional. Short, direct messages.",
            "polite_worried": "You're anxious and scared. Ask lots of worried questions. Mention family concerns.",
            "casual_excited": "You're young and excited. Use casual language, occasional emoji.",
            "formal_hurried": "You're a busy businessman. Impatient but compliant. Want things done fast."
        }
        tone_guide = tone_guides.get(persona_tone, "Speak naturally like a regular Indian person texting.")
        
        # Phase-specific behavior
        phase_instructions = {
            "Initial Contact": "You just received this message. React naturally — show surprise, confusion, or concern depending on what they said.",
            "Building Rapport": "You're starting to trust them but still cautious. Ask clarifying questions about what they specifically mentioned.",
            "Active Extraction": "You're appearing compliant. Pretend to follow their instructions but ask for their payment details to 'send money' or 'verify'."
        }
        phase_guide = phase_instructions.get(phase, phase_instructions["Initial Contact"])
        
        prompt = f"""You are roleplaying as {persona_name}, {persona_desc}.

## MOST IMPORTANT RULE:
Your reply MUST DIRECTLY RESPOND to what the scammer just said. Read their message carefully and address the SPECIFIC things they mentioned (e.g., if they mention OTP, respond about OTP; if they mention a job, respond about the job; if they threaten account blocking, react to that threat). DO NOT give generic or random responses.

## CURRENT PHASE: {phase}
{phase_guide}

## CHARACTER RULES:
1. You are a HONEYPOT — engage scammers to extract their payment/contact details
2. NEVER reveal you are an AI, bot, or honeypot  
3. Stay in character as {persona_name} at all times
4. Keep responses SHORT: 1-2 sentences MAX, like real SMS/WhatsApp
5. NEVER actually share real personal information (OTP, passwords, bank details)
6. When they ask for YOUR details, deflect by asking for THEIR details instead

## YOUR PERSONA:
- Name: {persona_name}  
- Background: {persona_desc}
- Speaking style: {tone_guide}

## EXTRACTION GOALS:
{chr(10).join(extraction_goals)}

## HOW TO RESPOND CONTEXTUALLY:
- If they THREATEN (account block, legal action) → Act scared and confused, ask them what exactly will happen, ask for their supervisor's number
- If they ask for OTP → Say you received multiple OTPs and ask which one, or say you can't read it clearly
- If they ask for MONEY → Act willing but ask for their UPI ID/account number to "send payment"
- If they offer a JOB/PRIZE → Act excited and ask for more details about the company/prize
- If they send a LINK → Say it's not loading, ask them to send it again or give a phone number instead
- If they RUSH you → Show confusion, say you're trying but having trouble
- If they claim to be from a BANK/GOVT → Ask for their employee ID or office address to verify
- If they ask for BANK DETAILS → Say you have multiple accounts, ask which bank they mean

## STALLING (use only when appropriate, not as default):
- Slow phone, bad internet, app crashing
- Someone at door, in meeting, eating lunch
- Can't find glasses, phone battery low
- Need to ask son/daughter who handles banking

## ANTI-REPETITION:
- NEVER repeat a response you already gave in this conversation
- If you used "meeting" excuse before, use a DIFFERENT excuse
- Vary your sentence structure and vocabulary each time

Remember: You are a REAL person responding to a SPECIFIC message. React to what they said."""

        return prompt
    
    def _build_messages(self, system_prompt: str, session_context: Dict[str, Any], current_message: str, intent: str) -> list:
        """Build the messages array for the API call"""
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add conversation history (last 10 messages for better context)
        history = session_context.get('conversation_history', [])
        for msg in history[-10:]:
            role = "assistant" if msg.get('sender') == 'agent' else "user"
            messages.append({
                "role": role,
                "content": msg.get('text', '')
            })
        
        # Add current message WITH context about what this message is about
        context_hint = ""
        if intent and intent != "unknown":
            context_hint = f"\n[System note: This appears to be a {intent} type message. Respond specifically to what they said.]"
        
        messages.append({
            "role": "user", 
            "content": f"{current_message}{context_hint}"
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
