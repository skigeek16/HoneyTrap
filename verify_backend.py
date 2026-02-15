"""
Multi-turn conversation simulator for the HoneyTrap backend.
Simulates a realistic scammer conversation over multiple exchanges.
Each turn: POST message → wait for SCAM_STATUS_UPDATE → wait for STALL_MESSAGE → use that reply as context for next scammer message.
"""
import asyncio
import websockets
import httpx
import json

API_URL = "http://127.0.0.1:8000"
WS_URL = "ws://127.0.0.1:8000/ws/session"

# Simulated scammer messages — each one escalates the scam
SCAMMER_MESSAGES = [
    # Turn 1: Initial hook
    "Hello dear, I have a great job opportunity for you. You can earn ₹50,000 per week from home. Are you interested?",

    # Turn 2: Pressure + details
    "Yes it is 100% legitimate! This is a data entry job from a top MNC company. Many people are already earning. I just need your basic details to register you.",

    # Turn 3: Asks for personal info
    "Great! Please share your full name, Aadhaar number, and bank account details so I can register you immediately. The first payment will come within 24 hours.",

    # Turn 4: Provides fake UPI for "registration fee"
    "There is a small registration fee of ₹500 only. Please send to UPI ID: fastjobs@paytm. After payment I will activate your account and you start earning today itself.",

    # Turn 5: Urgency + threatens to close offer
    "Sir this offer is closing in 1 hour only. Already 50 people registered today. If you don't pay now you will lose this opportunity forever. Send ₹500 to 9876543210 or UPI fastjobs@paytm immediately.",

    # Turn 6: Tries alternative extraction
    "Ok no problem, if you can't pay now just share your bank account number and IFSC code. I will directly deposit ₹1000 as a bonus into your account to show you this is real.",
]


async def simulate_conversation():
    session_id = "sim-conv-001"
    
    print("=" * 70)
    print(f"  🍯 HoneyTrap Multi-Turn Conversation Simulator")
    print(f"  Session: {session_id}")
    print(f"  Turns:   {len(SCAMMER_MESSAGES)}")
    print("=" * 70)

    try:
        async with websockets.connect(f"{WS_URL}/{session_id}") as ws:
            # Receive ACK
            ack = json.loads(await ws.recv())
            print(f"\n✅ WebSocket connected: {ack['payload']['message']}\n")

            for turn, scammer_msg in enumerate(SCAMMER_MESSAGES, 1):
                print(f"{'─' * 70}")
                print(f"  TURN {turn}/{len(SCAMMER_MESSAGES)}")
                print(f"{'─' * 70}")
                print(f"\n📩 SCAMMER says:")
                print(f"   \"{scammer_msg}\"\n")

                # POST the message
                async with httpx.AsyncClient() as client:
                    resp = await client.post(
                        f"{API_URL}/v1/chat",
                        json={
                            "sessionId": session_id,
                            "message": {
                                "sender": "scammer",
                                "text": scammer_msg,
                            },
                            "metadata": {"channel": "SMS"},
                        },
                    )
                    ack_data = resp.json()
                    print(f"   HTTP ACK: {ack_data['status']}")

                # Wait for SCAM_STATUS_UPDATE
                event1 = json.loads(await asyncio.wait_for(ws.recv(), timeout=30))
                p = event1["payload"]
                severity_icon = {"red": "🔴", "yellow": "🟡", "green": "🟢"}.get(p["ui_color"], "⚪")
                print(f"\n{severity_icon} SCAM STATUS:")
                print(f"   Verdict:    {p['severity']} (confidence: {p['confidence']}%)")
                print(f"   Scam Type:  {p.get('scam_type', 'N/A')}")
                print(f"   UI Color:   {p['ui_color']}")

                # Wait for STALL_MESSAGE (only arrives if scam/suspicious)
                if p["ui_color"] != "green":
                    try:
                        event2 = json.loads(await asyncio.wait_for(ws.recv(), timeout=10.0))
                    except asyncio.TimeoutError:
                        # Timeout might mean Ghost Mode is active (no reply sent)
                        print(f"\n   ⚠️  Timeout waiting for reply. Checking for Ghost Mode...")
                        async with httpx.AsyncClient() as client:
                            chk = await client.get(f"{API_URL}/v1/session/{session_id}")
                            if chk.status_code == 200 and chk.json().get("ghost_mode"):
                                print(f"   👻 GHOST MODE CONFIRMED! The bot has stopped responding as intended.")
                                break
                            else:
                                print(f"   ❌ Timeout but Ghost Mode NOT active. Something is wrong.")
                                raise

                    print(f"   [DEBUG] Received Event 2: {event2}")
                    if event2.get("type") == "ERROR":
                        print(f"❌ BACKEND ERROR: {event2['payload'].get('message')}")
                        continue
                    
                    p2 = event2["payload"]
                    print(f"\n🤖 HONEYPOT REPLY (delay: {p2['suggested_delay']}s, phase: {p2['phase']}):")
                    print(f"   \"{p2['message_body']}\"")

                    # Simulate the delay between messages
                    if turn < len(SCAMMER_MESSAGES):
                        wait = min(p2["suggested_delay"], 3.0)  # Cap at 3s for testing
                        print(f"\n   ⏳ Waiting {wait:.1f}s before next scammer message...")
                        await asyncio.sleep(wait)
                else:
                    print(f"\n   ✋ SAFE — No reply sent (backend did not engage)")
                    if turn < len(SCAMMER_MESSAGES):
                        print(f"\n   ⏳ Waiting 1.0s before next scammer message...")
                        await asyncio.sleep(1.0)

            print(f"\n{'=' * 70}")
            print(f"  ✅ Conversation complete")
            print(f"{'=' * 70}")

            # Fetch final session state
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{API_URL}/v1/session/{session_id}")
                if resp.status_code == 200:
                    info = resp.json()
                    print(f"\n📊 FINAL SESSION STATE:")
                    print(f"   Messages:       {info['message_count']}")
                    print(f"   Phase:          {info['phase']}")
                    print(f"   Confidence:     {info['scam_confidence']}%")
                    print(f"   Intel Complete: {info['intelligence_completion']}%")
                    print(f"   Ghost Mode:     {info.get('ghost_mode', False)}")
                    print(f"   Entities Found: {info['entities_extracted']}")
                    print(f"   Persona:        {info.get('persona', 'None')}")
                    
                    if "intelligence_report" in info and info["intelligence_report"]:
                        print(f"\n🕵️  EXTRACTED INTELLIGENCE REPORT:")
                        print(f"   {'-'*40}")
                        for item in info["intelligence_report"]:
                            print(f"   • [{item['type']}] {item['value']} (conf: {item['confidence']})")
                        print(f"   {'-'*40}")

    except Exception as e:
        print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    asyncio.run(simulate_conversation())
