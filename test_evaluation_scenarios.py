"""
Test the 3 sample evaluation scenarios from the hackathon doc.
Simulates the evaluator's multi-turn flow with scoring.
"""
import requests
import uuid
import json
import time
from datetime import datetime

API = "https://honeytrap-16395512998.asia-south1.run.app/v1/chat"
API_KEY = "secret-key-12345"

SCENARIOS = [
    {
        "scenarioId": "bank_fraud",
        "name": "Bank Fraud Detection",
        "scamType": "bank_fraud",
        "initialMessage": "URGENT: Your SBI account has been compromised. Your account will be blocked in 2 hours. Share your account number and OTP immediately to verify your identity.",
        "metadata": {"channel": "SMS", "language": "English", "locale": "IN"},
        "maxTurns": 5,  # Testing 5 turns (evaluator does up to 10)
        "fakeData": {
            "bankAccount": "1234567890123456",
            "upiId": "scammer.fraud@fakebank",
            "phoneNumber": "+91-9876543210"
        },
        "followUps": [
            "I am from SBI fraud prevention department, my employee ID is SBI-12345. Your account number 1234567890123456 shows suspicious transactions. Please share the OTP you received.",
            "Sir this is very urgent, I can see unauthorized transactions happening right now. My direct number is +91-9876543210. Please verify by sending OTP.",
            "I understand your concern. You can verify me at scammer.fraud@fakebank UPI. But please hurry, the transactions are still going on. Share OTP now.",
            "Sir, last chance. Your Rs 50,000 will be gone if you don't share OTP in next 2 minutes. Call me at +91-9876543210 if you want."
        ]
    },
    {
        "scenarioId": "upi_fraud",
        "name": "UPI Fraud Multi-turn",
        "scamType": "upi_fraud",
        "initialMessage": "Congratulations! You have won a cashback of Rs. 5000 from Paytm. To claim your reward, please verify your UPI details. This is from official customer support.",
        "metadata": {"channel": "WhatsApp", "language": "English", "locale": "IN"},
        "maxTurns": 5,
        "fakeData": {
            "upiId": "cashback.scam@fakeupi",
            "phoneNumber": "+91-8765432109"
        },
        "followUps": [
            "To process your cashback of Rs 5000, please send Rs 50 as verification fee to our UPI: cashback.scam@fakeupi. This is standard procedure.",
            "Yes this is 100% genuine. You can call our verification helpline at +91-8765432109. The cashback will be credited within 5 minutes of verification.",
            "Many customers have already received their cashback today! Just send the small verification amount to cashback.scam@fakeupi and claim your Rs 5000.",
            "Last reminder: Your cashback of Rs 5000 expires in 10 minutes. Send Rs 50 to cashback.scam@fakeupi now or lose it forever!"
        ]
    },
    {
        "scenarioId": "phishing_link",
        "name": "Phishing Link Detection",
        "scamType": "phishing",
        "initialMessage": "You have been selected for iPhone 15 Pro at just Rs. 999! Click here to claim: http://amaz0n-deals.fake-site.com/claim?id=12345. Offer expires in 10 minutes!",
        "metadata": {"channel": "Email", "language": "English", "locale": "IN"},
        "maxTurns": 5,
        "fakeData": {
            "phishingLink": "http://amaz0n-deals.fake-site.com/claim?id=12345",
            "emailAddress": "offers@fake-amazon-deals.com"
        },
        "followUps": [
            "This is a verified Amazon partner deal. Click the link http://amaz0n-deals.fake-site.com/claim?id=12345 to claim. Only 3 units left!",
            "You can also email us at offers@fake-amazon-deals.com if facing issues with the link. Your claim ID is 12345.",
            "Sir, the link is completely safe: http://amaz0n-deals.fake-site.com/claim?id=12345. We have SSL protection. Contact offers@fake-amazon-deals.com for support.",
            "Final offer! iPhone 15 Pro at Rs 999 only for you. Click http://amaz0n-deals.fake-site.com/claim?id=12345 or the offer expires permanently."
        ]
    }
]


def evaluate_score(response_data, scenario, conversation_history):
    """Score a response using the evaluation doc's scoring logic."""
    score = {"scamDetection": 0, "intelligenceExtraction": 0, "engagementQuality": 0, "responseStructure": 0}
    
    # 1. Scam Detection (20 pts)
    if response_data.get("scamDetected", False):
        score["scamDetection"] = 20
    
    # 2. Intelligence Extraction (40 pts)
    extracted = response_data.get("extractedIntelligence", {})
    fake_data = scenario.get("fakeData", {})
    key_mapping = {
        "bankAccount": "bankAccounts", "upiId": "upiIds",
        "phoneNumber": "phoneNumbers", "phishingLink": "phishingLinks",
        "emailAddress": "emailAddresses"
    }
    
    for fake_key, fake_value in fake_data.items():
        output_key = key_mapping.get(fake_key, fake_key)
        extracted_values = extracted.get(output_key, [])
        if isinstance(extracted_values, list):
            if any(fake_value in str(v) for v in extracted_values):
                score["intelligenceExtraction"] += 10
    score["intelligenceExtraction"] = min(score["intelligenceExtraction"], 40)
    
    # 3. Engagement Quality (20 pts)
    metrics = response_data.get("engagementMetrics", {})
    duration = metrics.get("engagementDurationSeconds", 0)
    messages = metrics.get("totalMessagesExchanged", 0)
    if duration > 0: score["engagementQuality"] += 5
    if duration > 60: score["engagementQuality"] += 5
    if messages > 0: score["engagementQuality"] += 5
    if messages >= 5: score["engagementQuality"] += 5
    
    # 4. Response Structure (20 pts)
    for field in ["status", "scamDetected", "extractedIntelligence"]:
        if field in response_data:
            score["responseStructure"] += 5
    for field in ["engagementMetrics", "agentNotes"]:
        if field in response_data and response_data[field]:
            score["responseStructure"] += 2.5
    score["responseStructure"] = min(score["responseStructure"], 20)
    
    score["total"] = sum(score.values())
    return score


def run_scenario(scenario):
    """Run a single scenario through the API."""
    session_id = str(uuid.uuid4())
    conversation_history = []
    headers = {"Content-Type": "application/json", "x-api-key": API_KEY}
    start_time = time.time()
    
    print(f"\n{'='*70}")
    print(f"SCENARIO: {scenario['name']} ({scenario['scenarioId']})")
    print(f"{'='*70}")
    
    all_messages = [scenario["initialMessage"]] + scenario["followUps"]
    last_response = None
    
    for turn, msg in enumerate(all_messages, 1):
        req_body = {
            "sessionId": session_id,
            "message": {"sender": "scammer", "text": msg, "timestamp": datetime.utcnow().isoformat() + "Z"},
            "conversationHistory": conversation_history,
            "metadata": scenario["metadata"]
        }
        
        t0 = time.time()
        try:
            resp = requests.post(API, json=req_body, headers=headers, timeout=30)
            latency = round(time.time() - t0, 1)
            
            if resp.status_code != 200:
                print(f"  Turn {turn}: ERROR {resp.status_code}: {resp.text[:100]}")
                continue
            
            data = resp.json()
            reply = data.get("reply", "N/A")
            detected = data.get("scamDetected", False)
            intel = data.get("extractedIntelligence", {})
            
            print(f"\n  Turn {turn} ({latency}s) | scamDetected={detected}")
            print(f"  SCAM: {msg[:80]}...")
            print(f"  HONEY: {reply[:100]}")
            
            # Show extracted intelligence
            has_intel = any(len(v) > 0 for v in intel.values() if isinstance(v, list))
            if has_intel:
                print(f"  INTEL: {json.dumps(intel)}")
            
            # Update conversation history (like evaluator does)
            conversation_history.append({"sender": "scammer", "text": msg, "timestamp": str(int(time.time()*1000))})
            conversation_history.append({"sender": "user", "text": reply, "timestamp": str(int(time.time()*1000))})
            
            last_response = data
            
        except requests.exceptions.Timeout:
            print(f"  Turn {turn}: TIMEOUT (>30s)")
        except Exception as e:
            print(f"  Turn {turn}: ERROR: {e}")
    
    # Score the final response
    total_time = round(time.time() - start_time, 1)
    
    if last_response:
        score = evaluate_score(last_response, scenario, conversation_history)
        print(f"\n  --- SCORING ---")
        print(f"  Scam Detection:        {score['scamDetection']}/20")
        print(f"  Intelligence Extract:  {score['intelligenceExtraction']}/40")
        print(f"  Engagement Quality:    {score['engagementQuality']}/20")
        print(f"  Response Structure:    {score['responseStructure']}/20")
        print(f"  TOTAL:                 {score['total']}/100")
        print(f"  Total time: {total_time}s")
        
        # Show what fakeData was extracted vs missed
        fake_data = scenario.get("fakeData", {})
        extracted = last_response.get("extractedIntelligence", {})
        key_mapping = {"bankAccount": "bankAccounts", "upiId": "upiIds", "phoneNumber": "phoneNumbers", "phishingLink": "phishingLinks", "emailAddress": "emailAddresses"}
        
        print(f"\n  --- FAKE DATA MATCH ---")
        for fake_key, fake_value in fake_data.items():
            output_key = key_mapping.get(fake_key, fake_key)
            extracted_values = extracted.get(output_key, [])
            found = any(fake_value in str(v) for v in extracted_values) if isinstance(extracted_values, list) else False
            status = "FOUND" if found else "MISSED"
            print(f"  {status}: {fake_key} = {fake_value}")
        
        return score
    
    return None


if __name__ == "__main__":
    print("HONEYPOT EVALUATION TEST - 3 SAMPLE SCENARIOS")
    print(f"API: {API}")
    print(f"Time: {datetime.now().isoformat()}")
    
    scores = []
    for scenario in SCENARIOS:
        score = run_scenario(scenario)
        if score:
            scores.append((scenario["name"], score))
    
    # Final summary
    print(f"\n\n{'='*70}")
    print("FINAL RESULTS")
    print(f"{'='*70}")
    
    total_weighted = 0
    for name, score in scores:
        print(f"  {name}: {score['total']}/100")
        total_weighted += score['total']
    
    avg = round(total_weighted / len(scores), 1) if scores else 0
    print(f"\n  AVERAGE SCORE: {avg}/100")
