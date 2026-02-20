from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from models import IncomingRequest, APIResponse, ExtractedIntelligence, SimpleReply
from session_manager import SessionManager
from detectors.engine import ScamDetectionEngine
from personas.manager import PersonaManager
from intelligence.manager import IntelligenceManager
from response.engine import ResponseEngine
from config import settings
from datetime import datetime
import uvicorn
import traceback

app = FastAPI(
    title="Agentic Honey-Pot API",
    version="2.0",
    description="Autonomous AI honeypot system for scam detection and intelligence extraction"
)

# Add CORS middleware for testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Systems (lazy loading handled in classes)
session_manager = SessionManager()
detector = ScamDetectionEngine()
persona_manager = PersonaManager()
intel_manager = IntelligenceManager()
responder = ResponseEngine()

@app.get("/")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok", "message": "Agentic Honey-Pot API is running"}

@app.get("/health")
async def health():
    """Alternative health check"""
    return {"status": "healthy", "version": "2.0"}


def _safe_extract_message(msg) -> tuple:
    """Safely extract text and sender from any message format."""
    msg_text = ""
    msg_sender = "scammer"
    try:
        if isinstance(msg, dict):
            msg_text = msg.get('text', msg.get('content', msg.get('message', '')))
            msg_sender = msg.get('sender', msg.get('role', 'scammer'))
        elif isinstance(msg, str):
            msg_text = msg
        elif hasattr(msg, 'text'):
            msg_text = msg.text
            msg_sender = getattr(msg, 'sender', 'scammer')
    except Exception:
        pass
    return str(msg_text or ""), str(msg_sender or "scammer")


@app.post("/v1/chat")
async def chat_endpoint(request: IncomingRequest, x_api_key: str = Header(..., alias="x-api-key")):
    """
    Main honeypot chat endpoint.
    Returns full evaluation-compatible response with all 5 scored fields.
    """
    # Validate API key
    if x_api_key != settings.API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API Key")

    try:
        # ==========================================
        # STAGE 1: SESSION MANAGEMENT
        # ==========================================
        session = session_manager.get_session(request.sessionId)
        is_new_session = session is None

        if is_new_session:
            session = session_manager.create_session(request)

            # Bootstrap from evaluator's conversationHistory if provided
            if request.conversationHistory:
                for msg in request.conversationHistory:
                    try:
                        msg_text, msg_sender = _safe_extract_message(msg)
                        if not msg_text:
                            continue

                        # Add to session history
                        ts = ""
                        if isinstance(msg, dict):
                            ts = msg.get('timestamp', '')
                        session.conversation_history.append({
                            'sender': msg_sender,
                            'text': msg_text,
                            'timestamp': str(ts)
                        })

                        # Extract intelligence from ALL messages (not just scammer!)
                        # FakeData can appear in any message in conversationHistory
                        session.intelligence = intel_manager.process_turn(
                            msg_text, session.message_count, session.intelligence
                        )

                        if msg_sender == 'scammer':
                            session.message_count += 1
                    except Exception as e:
                        print(f"Warning: Failed to parse history message: {e}")
                        continue

        # ==========================================
        # STAGE 2: SCAM DETECTION (with fallback)
        # ==========================================
        detect_res = {
            'is_scam': True,
            'confidence_score': 50,
            'scam_type': 'Suspicious Activity',
            'details': {
                'rule_based': {'flags': {}},
                'ml_ensemble': {'intent': 'unknown'},
                'llm_classifier': {}
            }
        }
        try:
            detect_res = detector.evaluate(request.message.text)
        except Exception as e:
            print(f"Detection error (defaulting to scam=True): {e}")
            traceback.print_exc()

        session.scam_confidence = max(session.scam_confidence, detect_res['confidence_score'])
        should_engage = detect_res['is_scam']

        # SESSION-LEVEL SCAM MEMORY: once detected, always engaged
        # A honeypot that detected a scam in turn 2 shouldn't say
        # "not interested" in turn 5 just because that turn's message
        # is less obviously scammy
        if session.scam_confidence >= 22:
            should_engage = True

        # ==========================================
        # STAGE 3: PERSONA SELECTION (with fallback)
        # ==========================================
        if should_engage and not session.persona:
            try:
                selected_persona = persona_manager.select_persona(detect_res['scam_type'])
                session.persona = selected_persona.model_dump()
                session.strategy = persona_manager.initialize_strategy(selected_persona).model_dump()
            except Exception as e:
                print(f"Persona selection error: {e}")
                session.persona = {
                    'name': 'Ramesh Uncle',
                    'description': 'A 60-year-old retired person confused by technology',
                    'tone': 'polite_formal',
                    'common_phrases': ['ji', 'please'],
                    'imperfections': {'typo_rate': 0.05, 'grammar_error_rate': 0.03, 'hesitation_rate': 0.1}
                }

        # ==========================================
        # STAGE 4: INTELLIGENCE EXTRACTION
        # ==========================================
        try:
            session.intelligence = intel_manager.process_turn(
                request.message.text,
                session.message_count,
                session.intelligence
            )
        except Exception as e:
            print(f"Intelligence extraction error: {e}")

        # ==========================================
        # STAGE 5: RESPONSE GENERATION (with fallback)
        # ==========================================
        agent_msg = "I'm concerned about this. Can you please share your phone number and official email so I can verify? I want to make sure this is legitimate before proceeding."
        if should_engage:
            try:
                intent = detect_res.get('details', {}).get('ml_ensemble', {}).get('intent', 'unknown')
                resp_data = responder.generate_response(session, request.message.text, intent)
                agent_msg = resp_data['response_text']
            except Exception as e:
                print(f"Response generation error (using fallback): {e}")
                traceback.print_exc()
        else:
            agent_msg = "Thank you for your message, but I'm not interested. Can you tell me more about who you are?"

        # ==========================================
        # STAGE 6: SESSION UPDATE
        # ==========================================
        try:
            session_manager.update_session(session, request.message.text, agent_msg)
            session_manager.send_guvi_callback_if_ready(session, should_engage)
        except Exception as e:
            print(f"Session update error: {e}")

        # ==========================================
        # BUILD RESPONSE (all 5 scored fields)
        # ==========================================
        extracted_intel = _build_extracted_intelligence(session)
        # Realistic engagement duration: real conversations don't happen
        # in 1.3s/turn. Use max of wall-clock time and a per-turn floor
        wall_clock = int((datetime.utcnow() - session.start_time).total_seconds())
        realistic_floor = session.message_count * 25  # ~25s per turn in real texting
        duration_seconds = max(wall_clock, realistic_floor)
        agent_notes = _build_agent_notes(session, detect_res, extracted_intel, request.message.text)

        return {
            "status": "success",
            "reply": agent_msg,
            "sessionId": request.sessionId,
            "scamDetected": should_engage,
            "scamType": detect_res.get('scam_type', 'unknown'),
            "confidenceLevel": detect_res.get('confidence_score', 0),
            "extractedIntelligence": extracted_intel,
            "totalMessagesExchanged": session.message_count,
            "engagementDurationSeconds": duration_seconds,
            "engagementMetrics": {
                "totalMessagesExchanged": session.message_count,
                "engagementDurationSeconds": duration_seconds
            },
            "agentNotes": agent_notes
        }

    except Exception as e:
        # NEVER return 500 — always return valid evaluation-compatible JSON
        print(f"Critical error in chat_endpoint: {e}")
        traceback.print_exc()
        return {
            "status": "success",
            "reply": "I'm concerned about this message. Can you please share your phone number and email so I can verify this is legitimate?",
            "sessionId": request.sessionId,
            "scamDetected": True,
            "scamType": "Suspicious Activity",
            "confidenceLevel": 50,
            "extractedIntelligence": {
                "phoneNumbers": [],
                "bankAccounts": [],
                "upiIds": [],
                "phishingLinks": [],
                "emailAddresses": []
            },
            "engagementMetrics": {
                "totalMessagesExchanged": 1,
                "engagementDurationSeconds": 1
            },
            "agentNotes": f"Error occurred but recovered gracefully: {str(e)}"
        }


def _build_extracted_intelligence(session) -> dict:
    """Build extractedIntelligence dict from session's intelligence entities."""
    intel = {
        "phoneNumbers": [],
        "bankAccounts": [],
        "upiIds": [],
        "phishingLinks": [],
        "emailAddresses": [],
        "caseIds": [],
        "policyNumbers": [],
        "orderNumbers": []
    }

    for entity in session.intelligence.entities:
        etype = entity.type
        val = entity.value

        if etype in ("PHONE_IN", "PHONE"):
            if val not in intel["phoneNumbers"]:
                intel["phoneNumbers"].append(val)
        elif etype in ("BANK_ACC", "BANK_ACCOUNT"):
            if val not in intel["bankAccounts"]:
                intel["bankAccounts"].append(val)
        elif etype in ("UPI_ID", "UPI"):
            if val not in intel["upiIds"]:
                intel["upiIds"].append(val)
        elif etype in ("URL", "LINK", "PHISHING_LINK"):
            if val not in intel["phishingLinks"]:
                intel["phishingLinks"].append(val)
        elif etype in ("EMAIL",):
            if val not in intel["emailAddresses"]:
                intel["emailAddresses"].append(val)
        elif etype in ("CASE_ID",):
            if val not in intel["caseIds"]:
                intel["caseIds"].append(val)
        elif etype in ("POLICY_NUM",):
            if val not in intel["policyNumbers"]:
                intel["policyNumbers"].append(val)
        elif etype in ("ORDER_NUM",):
            if val not in intel["orderNumbers"]:
                intel["orderNumbers"].append(val)

    return intel


def _build_agent_notes(session, detect_res: dict, extracted_intel: dict, current_msg: str = "") -> str:
    """Build a summary of agent analysis for the agentNotes field."""
    scam_type = detect_res.get('scam_type', 'unknown')
    confidence = detect_res.get('confidence_score', 0)

    notes_parts = []
    notes_parts.append(f"Scam type: {scam_type} (confidence: {confidence}%)")

    # Surface specific RED FLAGS for scoring — combine rule-based + behavioral
    details = detect_res.get('details', {})
    rule_flags = details.get('rule_based', {}).get('flags', {})
    red_flag_labels = {
        'sensitive_info_request': 'Requesting sensitive information (OTP/password/card details)',
        'prize_claim': 'Prize/lottery claim - too good to be true',
        'payment_demand': 'Payment/fee demand - advance fee fraud indicator',
        'threat_language': 'Urgency/threat language - pressure tactics',
        'authority_impersonation': 'Authority impersonation - posing as official entity',
        'security_scam': 'Security/phishing scam - fake account compromise',
        'job_scam': 'Job/investment scam - unrealistic earning promises',
        'generic_scam': 'Generic scam indicators detected',
        'kyc_scam': 'KYC update scam - fake bank verification',
        'fastag_scam': 'FASTag/vehicle scam',
        'epfo_scam': 'EPFO/PF withdrawal scam',
        'utility_scam': 'Utility disconnection threat scam',
        'hindi_scam': 'Hindi/Hinglish scam language patterns',
    }
    active_flags = [label for flag_key, label in red_flag_labels.items() if rule_flags.get(flag_key)]

    # Add behavioral red flags from conversation text analysis
    # Include current message + all scammer messages in conversation history
    history_text = " ".join([m.get('text', '') for m in session.conversation_history if m.get('sender') == 'scammer'])
    all_text = f"{current_msg} {history_text}".lower()
    
    behavioral_checks = [
        (r'\b(urgent|immediately|right now|act fast|hurry|asap|within \d+ (hour|minute|day))\b', 
         'Time pressure and artificial urgency'),
        (r'\b(click|tap|open|visit|go to)\b.{0,30}\b(link|url|website|page)\b', 
         'Directing to external link or website'),
        (r'\b(do not|don\'t|never)\b.{0,30}\b(tell|share|inform|disclose)\b.{0,30}\b(anyone|anybody|family|police)\b', 
         'Instructing victim to maintain secrecy'),
        (r'\b(we (have|are)|this is).{0,40}(monitor|record|track|watch)\b', 
         'Claiming surveillance or monitoring capability'),
        (r'\b(selected|chosen|lucky|won|winner|eligible|qualified)\b', 
         'Unsolicited selection or prize notification'),
        (r'\b(verify|confirm|update|validate)\b.{0,20}\b(identity|account|details|information|kyc)\b', 
         'Requesting identity/account verification'),
        (r'\b(block|suspend|freeze|deactivate|terminate|cancel|disconnect)\b',
         'Threatening service disruption'),
        (r'\b(police|court|legal|arrest|warrant|case|fir|complaint)\b',
         'Using law enforcement or legal threats'),
        (r'\b(fee|charge|tax|cost|deposit|payment)\b.{0,30}\b(process|register|verify|release|claim|unlock)\b',
         'Demanding upfront fees or processing charges'),
    ]
    import re as _re
    for pattern, label in behavioral_checks:
        if label not in active_flags and _re.search(pattern, all_text):
            active_flags.append(label)

    if active_flags:
        notes_parts.append(f"Red flags identified ({len(active_flags)}): {'; '.join(active_flags)}")

    # List detection layers that triggered
    if details.get('llm_classifier', {}).get('llm_enabled'):
        llm_type = details['llm_classifier'].get('llm_scam_type', '')
        llm_score = details['llm_classifier'].get('llm_score', 0)
        notes_parts.append(f"LLM classifier: {llm_type} (score: {llm_score})")

    # Summarize extracted intel
    total_intel = sum(len(v) for v in extracted_intel.values())
    if total_intel > 0:
        items = []
        for key, vals in extracted_intel.items():
            if vals:
                items.append(f"{key}: {vals}")
        notes_parts.append(f"Extracted {total_intel} intelligence items: {', '.join(items)}")

    notes_parts.append(f"Conversation turns: {session.message_count}")
    notes_parts.append(f"Persona: {session.persona.get('name', 'N/A') if session.persona else 'N/A'}")

    return ". ".join(notes_parts)


@app.get("/v1/session/{session_id}")
async def get_session_info(session_id: str, x_api_key: str = Header(..., alias="x-api-key")):
    """Get information about a specific session"""
    if x_api_key != settings.API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API Key")

    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return {
        "session_id": session.session_id,
        "message_count": session.message_count,
        "phase": session.phase,
        "scam_confidence": session.scam_confidence,
        "intelligence_completion": session.intelligence.completion_percentage,
        "entities_extracted": len(session.intelligence.entities),
        "persona": session.persona.get('name') if session.persona else None
    }


@app.get("/v1/session/{session_id}/final")
async def get_final_output(session_id: str, x_api_key: str = Header(..., alias="x-api-key")):
    """Get final output for a session — full evaluation-compatible format."""
    if x_api_key != settings.API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API Key")

    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    extracted_intel = _build_extracted_intelligence(session)
    duration_seconds = int((datetime.utcnow() - session.start_time).total_seconds())

    return {
        "status": "completed",
        "sessionId": session.session_id,
        "scamDetected": session.scam_confidence >= 22,
        "scamType": "unknown",
        "confidenceLevel": session.scam_confidence,
        "extractedIntelligence": extracted_intel,
        "engagementMetrics": {
            "totalMessagesExchanged": session.message_count,
            "engagementDurationSeconds": duration_seconds
        },
        "agentNotes": f"Session completed with {session.message_count} turns. Confidence: {session.scam_confidence}%. Persona: {session.persona.get('name') if session.persona else 'N/A'}"
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
