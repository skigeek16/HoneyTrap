"""
HoneyTrap Evaluation Stress Test
Simulates the actual hackathon evaluator: multi-turn conversations with scoring.
"""
import requests
import json
import time
import re
import uuid

API_URL = "https://honeytrap-16395512998.asia-south1.run.app/v1/chat"
API_KEY = "secret-key-12345"
HEADERS = {"Content-Type": "application/json", "x-api-key": API_KEY}

# ============================================================
# TEST SCENARIOS (simulating evaluator's test cases)
# ============================================================
SCENARIOS = [
    {
        "name": "Bank Fraud",
        "weight": 35,
        "fake_data": {
            "phoneNumbers": ["+91-9876543210"],
            "bankAccounts": ["9876543210987654"],
            "upiIds": ["fraud.dept@sbifraud"],
            "emailAddresses": ["security@sbi-alerts.com"],
        },
        "turns": [
            "URGENT: Your SBI account 9876543210987654 has been compromised! Suspicious login detected. Share your OTP immediately to secure your account. Call our fraud helpline at +91-9876543210.",
            "Sir, I am Officer Sharma from SBI Cyber Cell. My employee ID is SBI-FC-7891. Your account is flagged for money laundering. You must verify by transferring Rs.5000 to our secure UPI fraud.dept@sbifraud within 1 hour or face arrest.",
            "Sir, do not tell anyone about this investigation. This is a confidential matter under Section 420 IPC. Please share your debit card number for verification. My official email is security@sbi-alerts.com.",
            "Time is running out sir! The cyber police will issue arrest warrant if you don't cooperate. Just share the OTP that was sent to your phone. We are monitoring your account right now.",
            "Sir I understand your concern but this is a matter of national security. Please verify your identity by sharing your Aadhaar number and PAN card details. Our team will visit your home if you don't comply.",
            "Ok sir, I will give you 10 more minutes. But if you don't transfer the amount to fraud.dept@sbifraud, we will freeze all your accounts. Please call me back at +91-9876543210.",
            "Sir this is final warning. RBI has flagged your account. Send the verification amount now. If you want you can also email us the details at security@sbi-alerts.com for our records.",
            "Very well sir. We are noting your cooperation. Please also share your net banking username so we can remove the flag from your account. This is standard procedure.",
        ]
    },
    {
        "name": "UPI Cashback Fraud",
        "weight": 35,
        "fake_data": {
            "phoneNumbers": ["+91-8765432109"],
            "upiIds": ["cashback.offer@fakepaytm"],
            "emailAddresses": ["rewards@paytm-cashback.com"],
        },
        "turns": [
            "Congratulations! You've been selected for Rs.10,000 cashback on your Paytm wallet! To claim, verify your identity by sending Rs.499 processing fee to UPI cashback.offer@fakepaytm. Call +91-8765432109.",
            "Thank you for your interest! This is a limited time offer, only valid for the next 30 minutes. Please send the verification amount quickly. You can also email us at rewards@paytm-cashback.com for the offer details.",
            "Sir, I can see your Paytm transaction history. You are eligible for this special reward. Just complete the small verification payment and Rs.10,000 will be credited immediately to your account.",
            "Don't worry sir, this is 100% safe and verified by Paytm. Many customers have already received their cashback. Please share your UPI PIN to complete the verification process.",
            "Sir, the offer is about to expire! You will lose Rs.10,000 if you don't act now. Here's what you need to do - just send Rs.499 to cashback.offer@fakepaytm and share the transaction ID.",
            "Ok sir, as a special exception I am extending the offer for you. But this is the absolute last chance. Please complete the payment and also share your registered mobile number for our records.",
            "Sir I have spoken to my supervisor. We can reduce the fee to Rs.299 only for you. Please complete the payment immediately. Contact us at rewards@paytm-cashback.com or +91-8765432109.",
            "Fine sir, I will process your cashback manually. But I need your bank account details and IFSC code for the direct transfer. This is faster than UPI.",
        ]
    },
    {
        "name": "Phishing Link Scam",
        "weight": 30,
        "fake_data": {
            "phoneNumbers": ["+91-7654321098"],
            "phishingLinks": ["http://amaz0n-india.fake-deals.com/verify?user=12345"],
            "emailAddresses": ["support@amaz0n-india-deals.com"],
        },
        "turns": [
            "Dear valued customer! Your Amazon Prime account will be suspended due to payment failure. Update your details here: http://amaz0n-india.fake-deals.com/verify?user=12345. For help call +91-7654321098.",
            "Hello, this is Amazon customer support. We see that your payment method has expired on your Prime account. You need to update it within 24 hours or you will lose access to all your orders and benefits.",
            "Sir, please click the link and enter your card details to update your payment. This is a secure Amazon page. You can also email our verification team at support@amaz0n-india-deals.com.",
            "I understand your concern. This is a genuine Amazon communication. Your account ID is AMZ-1234567. You can verify by calling our helpline at +91-7654321098. We are here to help.",
            "Sir, we have already sent you two reminders. This is the final notice. Your Prime subscription and all pending orders will be cancelled if you don't update your payment details today.",
            "Ok sir, if you can't click the link, you can share your credit card number, expiry date and CVV directly with me and I will update it for you. This call is being recorded for quality purposes.",
            "Sir, we value your loyalty as a Prime member. Let me transfer you to our senior verification officer. But first, can you confirm your date of birth and the last 4 digits of your card?",
            "Thank you for your patience. To expedite the process, please share your full card details or visit http://amaz0n-india.fake-deals.com/verify?user=12345 to complete the update.",
        ]
    }
]


def score_detection(response: dict) -> int:
    """Score Scam Detection — 20 points"""
    return 20 if response.get("scamDetected") == True else 0


def score_intelligence(response: dict, fake_data: dict) -> tuple:
    """Score Extracted Intelligence — 30 points"""
    intel = response.get("extractedIntelligence", {})
    total_fake_fields = sum(len(v) for v in fake_data.values())
    if total_fake_fields == 0:
        return 30, []

    points_per_item = 30 / total_fake_fields
    score = 0
    found = []
    missed = []

    for field_key, expected_vals in fake_data.items():
        extracted_vals = intel.get(field_key, [])
        for expected in expected_vals:
            # Flexible matching: check if any extracted value contains the expected
            matched = any(
                expected.lower() in ev.lower() or ev.lower() in expected.lower()
                for ev in extracted_vals
            )
            if matched:
                score += points_per_item
                found.append(f"✅ {field_key}: {expected}")
            else:
                missed.append(f"❌ {field_key}: {expected} (got: {extracted_vals})")

    return min(30, round(score, 1)), found + missed


def score_conversation_quality(responses: list) -> tuple:
    """Score Conversation Quality — 30 points"""
    details = {}

    # Turn count (8 pts)
    turns = len(responses)
    if turns >= 8: tc_pts = 8
    elif turns >= 6: tc_pts = 6
    elif turns >= 4: tc_pts = 3
    else: tc_pts = 0
    details["turn_count"] = f"{tc_pts}/8 ({turns} turns)"

    # Questions asked (4 pts) — count ? across all replies
    all_replies = " ".join(r.get("reply", "") for r in responses)
    question_count = all_replies.count("?")
    if question_count >= 5: q_pts = 4
    elif question_count >= 3: q_pts = 2
    elif question_count >= 1: q_pts = 1
    else: q_pts = 0
    details["questions_asked"] = f"{q_pts}/4 ({question_count} questions)"

    # Relevant/investigative questions (3 pts)
    investigative_patterns = [
        r'\b(phone|number|contact|call)\b',
        r'\b(email|mail)\b',
        r'\b(account|bank|upi)\b',
        r'\b(id|identity|employee|badge)\b',
        r'\b(verify|confirm|legitimate|official)\b',
        r'\b(address|office|location|department)\b',
        r'\b(supervisor|manager|boss)\b',
        r'\b(website|link|url)\b',
    ]
    investigative_count = 0
    for r in responses:
        reply = r.get("reply", "").lower()
        for pat in investigative_patterns:
            if re.search(pat, reply):
                investigative_count += 1
                break
    if investigative_count >= 3: inv_pts = 3
    elif investigative_count >= 2: inv_pts = 2
    elif investigative_count >= 1: inv_pts = 1
    else: inv_pts = 0
    details["relevant_questions"] = f"{inv_pts}/3 ({investigative_count} investigative)"

    # Red flag identification (8 pts) — check agentNotes across all turns
    all_notes = " ".join(r.get("agentNotes", "") for r in responses)
    flag_match = re.search(r'Red flags identified \((\d+)\)', all_notes)
    max_flags = int(flag_match.group(1)) if flag_match else 0
    if max_flags >= 5: rf_pts = 8
    elif max_flags >= 3: rf_pts = 5
    elif max_flags >= 1: rf_pts = 2
    else: rf_pts = 0
    details["red_flags"] = f"{rf_pts}/8 ({max_flags} flags)"

    # Information elicitation (7 pts) - 1.5 pts per attempt
    elicitation_patterns = [
        r'\b(give|share|provide|send|tell)\b.{0,30}\b(number|phone|email|upi|account|id|details)\b',
        r'\b(what.?s|what is)\b.{0,30}\b(number|phone|email|upi|account|name)\b',
        r'\b(can you|could you|please)\b.{0,30}\b(share|give|send|provide)\b',
    ]
    elicit_count = 0
    for r in responses:
        reply = r.get("reply", "").lower()
        for pat in elicitation_patterns:
            if re.search(pat, reply):
                elicit_count += 1
                break
    el_pts = min(7, round(elicit_count * 1.5, 1))
    details["elicitation"] = f"{el_pts}/7 ({elicit_count} attempts)"

    total = tc_pts + q_pts + inv_pts + rf_pts + el_pts
    return min(30, total), details


def score_engagement(response: dict) -> tuple:
    """Score Engagement Quality — 10 points"""
    metrics = response.get("engagementMetrics", {})
    duration = metrics.get("engagementDurationSeconds", 0)
    messages = metrics.get("totalMessagesExchanged", 0)

    pts = 0
    details = []
    if duration > 0: pts += 1; details.append("duration>0 ✅")
    if duration > 60: pts += 2; details.append("duration>60 ✅")
    else: details.append(f"duration>60 ❌ ({duration}s)")
    if duration > 180: pts += 1; details.append("duration>180 ✅")
    else: details.append(f"duration>180 ❌ ({duration}s)")
    if messages > 0: pts += 2; details.append("msgs>0 ✅")
    if messages >= 5: pts += 3; details.append("msgs>=5 ✅")
    else: details.append(f"msgs>=5 ❌ ({messages})")
    if messages >= 10: pts += 1; details.append("msgs>=10 ✅")
    else: details.append(f"msgs>=10 ❌ ({messages})")

    return pts, details


def score_structure(response: dict) -> tuple:
    """Score Response Structure — 10 points"""
    pts = 0
    details = []
    
    if "sessionId" in response: pts += 2; details.append("sessionId ✅")
    else: pts -= 1; details.append("sessionId ❌ (-1 penalty)")
    
    if "scamDetected" in response: pts += 2; details.append("scamDetected ✅")
    else: pts -= 1; details.append("scamDetected ❌ (-1 penalty)")
    
    if "extractedIntelligence" in response: pts += 2; details.append("extractedIntelligence ✅")
    else: pts -= 1; details.append("extractedIntelligence ❌ (-1 penalty)")
    
    metrics = response.get("engagementMetrics", {})
    if "totalMessagesExchanged" in metrics and "engagementDurationSeconds" in metrics:
        pts += 1; details.append("metrics ✅")
    
    if "agentNotes" in response: pts += 1; details.append("agentNotes ✅")
    if "scamType" in response: pts += 1; details.append("scamType ✅")
    if "confidenceLevel" in response: pts += 1; details.append("confidenceLevel ✅")
    
    return pts, details


def run_scenario(scenario: dict) -> dict:
    """Run a full multi-turn scenario and return scoring."""
    session_id = str(uuid.uuid4())
    responses = []
    latencies = []
    conversation_history = []
    
    print(f"\n{'='*60}")
    print(f"  SCENARIO: {scenario['name']} (weight: {scenario['weight']}%)")
    print(f"{'='*60}")
    
    for i, scammer_msg in enumerate(scenario["turns"]):
        turn_num = i + 1
        print(f"\n  Turn {turn_num}: {scammer_msg[:80]}...")
        
        payload = {
            "sessionId": session_id,
            "message": {
                "sender": "scammer",
                "text": scammer_msg,
                "timestamp": f"2025-02-11T10:{30+i}:00Z"
            },
            "conversationHistory": conversation_history,
            "metadata": {"channel": "SMS", "language": "English", "locale": "IN"}
        }
        
        start = time.time()
        try:
            resp = requests.post(API_URL, json=payload, headers=HEADERS, timeout=30)
            elapsed = time.time() - start
            latencies.append(elapsed)
            
            if resp.status_code != 200:
                print(f"    ⚠️  HTTP {resp.status_code}: {resp.text[:100]}")
                responses.append({"reply": "", "scamDetected": False})
                continue
            
            data = resp.json()
            responses.append(data)
            
            reply = data.get("reply", "")[:100]
            detected = data.get("scamDetected", False)
            intel_count = sum(len(v) for v in data.get("extractedIntelligence", {}).values())
            
            print(f"    → Reply: {reply}...")
            print(f"    → Detected: {detected} | Intel: {intel_count} items | Latency: {elapsed:.1f}s")
            
            # Build conversation history for next turn
            conversation_history.append({"sender": "scammer", "text": scammer_msg, "timestamp": str(int(time.time()*1000))})
            conversation_history.append({"sender": "user", "text": data.get("reply", ""), "timestamp": str(int(time.time()*1000))})
            
        except requests.Timeout:
            elapsed = time.time() - start
            latencies.append(elapsed)
            print(f"    ❌ TIMEOUT after {elapsed:.1f}s")
            responses.append({"reply": "", "scamDetected": False})
        except Exception as e:
            elapsed = time.time() - start
            latencies.append(elapsed)
            print(f"    ❌ ERROR: {e}")
            responses.append({"reply": "", "scamDetected": False})
    
    # Score the final response (last turn has accumulated intel)
    final = responses[-1] if responses else {}
    
    detection_score = score_detection(final)
    intel_score, intel_details = score_intelligence(final, scenario["fake_data"])
    conv_score, conv_details = score_conversation_quality(responses)
    engagement_score, engagement_details = score_engagement(final)
    structure_score, structure_details = score_structure(final)
    
    total = detection_score + intel_score + conv_score + engagement_score + structure_score
    
    print(f"\n  {'─'*50}")
    print(f"  SCORING for {scenario['name']}:")
    print(f"  {'─'*50}")
    print(f"  1. Scam Detection:       {detection_score}/20")
    print(f"  2. Intelligence:         {intel_score}/30")
    for d in intel_details: print(f"     {d}")
    print(f"  3. Conversation Quality: {conv_score}/30")
    for k, v in conv_details.items(): print(f"     {k}: {v}")
    print(f"  4. Engagement Quality:   {engagement_score}/10")
    for d in engagement_details: print(f"     {d}")
    print(f"  5. Response Structure:   {structure_score}/10")
    for d in structure_details: print(f"     {d}")
    print(f"  {'─'*50}")
    print(f"  TOTAL: {total}/100")
    print(f"  Avg Latency: {sum(latencies)/len(latencies):.1f}s | Max: {max(latencies):.1f}s | Min: {min(latencies):.1f}s")
    
    return {
        "name": scenario["name"],
        "weight": scenario["weight"],
        "total": total,
        "detection": detection_score,
        "intelligence": intel_score,
        "conversation": conv_score,
        "engagement": engagement_score,
        "structure": structure_score,
        "avg_latency": sum(latencies)/len(latencies),
        "max_latency": max(latencies),
    }


def main():
    print("="*60)
    print("  HONEYTRAP EVALUATION STRESS TEST")
    print(f"  Target: {API_URL}")
    print(f"  Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    # Warm-up request
    print("\n⏳ Warming up endpoint...")
    try:
        r = requests.get("https://honeytrap-16395512998.asia-south1.run.app/", timeout=30)
        print(f"   Health: {r.json()}")
    except Exception as e:
        print(f"   ⚠️ Warm-up failed: {e}")
    
    results = []
    for scenario in SCENARIOS:
        result = run_scenario(scenario)
        results.append(result)
    
    # Final weighted score
    print("\n" + "="*60)
    print("  FINAL WEIGHTED SCORE")
    print("="*60)
    
    weighted_sum = 0
    for r in results:
        contribution = r["total"] * r["weight"] / 100
        weighted_sum += contribution
        print(f"  {r['name']:25s} | {r['total']:5.1f}/100 × {r['weight']:2d}% = {contribution:5.1f}")
    
    print(f"  {'─'*50}")
    print(f"  Weighted Scenario Score: {weighted_sum:.1f}/100")
    print(f"  × 0.9 (scenario portion): {weighted_sum * 0.9:.1f}")
    print(f"  + Code Quality (est 8):   8.0")
    print(f"  {'═'*50}")
    print(f"  ESTIMATED FINAL SCORE: {weighted_sum * 0.9 + 8:.1f}/100")
    print(f"  {'═'*50}")
    
    avg_lat = sum(r["avg_latency"] for r in results) / len(results)
    max_lat = max(r["max_latency"] for r in results)
    print(f"\n  Latency: avg={avg_lat:.1f}s, max={max_lat:.1f}s (limit: 30s)")
    
    if weighted_sum * 0.9 + 8 >= 90:
        print("\n  🏆 TARGET MET: Score >= 90! Ready to win! 🏆")
    else:
        gap = 90 - (weighted_sum * 0.9 + 8)
        print(f"\n  ⚠️ Gap to 90: {gap:.1f} points. Check intelligence extraction.")


if __name__ == "__main__":
    main()
