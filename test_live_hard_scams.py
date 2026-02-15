"""
Test 25 HARD-TO-DETECT scam messages against live Cloud Run endpoint.
These are designed to bypass regex — paraphrased, subtle, conversational.
"""
import requests
import json
import time

API_URL = "https://honeytrap-16395512998.asia-south1.run.app/v1/chat"
API_KEY = "secret-key-12345"

HARD_SCAMS = [
    # --- SOCIAL ENGINEERING (no keywords) ---
    ("Friend of friend", "Hey! Got your number from Priya. She said you might be interested in something I'm working on. Can we talk?"),
    ("Wrong number hook", "Hey Rahul! Long time! Oh wait, you're not Rahul? Sorry! But since we're chatting, what do you do? I run a fintech startup."),
    ("Fake mutual trust", "Hi, I'm Amit from your apartment complex. The RWA secretary asked me to collect the maintenance payment digitally this month."),
    
    # --- PARAPHRASED FINANCIAL SCAMS ---
    ("Subtle refund", "We found an overpayment on your recent purchase. A small amount needs to be returned to you. Please confirm your details so we can process it."),
    ("Vague account issue", "There seems to be a discrepancy in your account records. We'd appreciate if you could help us verify a few things at your convenience."),
    ("Fake cashback", "As a valued customer, you have an unclaimed cashback of Rs 2,340. It will expire in 48 hours. Tap here to redeem."),
    
    # --- JOB/INVESTMENT (no obvious keywords) ---
    ("Passive income pitch", "I used to work 12 hours a day. Now I make the same income in 2 hours using a simple system. Would you like to know how?"),
    ("Crypto without saying crypto", "Our automated trading system has been generating consistent returns for 6 months. No experience needed. Just set it up and watch."),
    ("Fake internship", "Hi! We're hiring part-time data operators. Work from your phone, flexible hours, weekly payouts. No interview needed, just register."),
    ("MLM disguised", "I started a side business 3 months ago and already replaced my salary. It's not what you think — it's completely legitimate. Want me to explain?"),
    
    # --- AUTHORITY IMPERSONATION (subtle) ---
    ("Soft govt notice", "This is regarding your recent filing. There appears to be a minor issue that needs your attention before the next deadline."),
    ("Fake compliance", "As per new regulatory guidelines, all users must re-verify their identity by end of this week. Failure to comply may result in temporary restrictions."),
    ("Telecom warning", "We've detected unusual activity on your mobile connection. To prevent service interruption, please verify your identity through our secure portal."),
    
    # --- EMOTIONAL MANIPULATION ---
    ("Sick child story", "Please help. My daughter has been diagnosed with a rare condition and we can't afford the treatment. Even Rs 100 will help. God bless you."),
    ("Stranded traveler", "I know this is random, but I'm stuck at the airport with no money. My wallet was stolen. Can you help me with cab fare? I'll pay you back immediately."),
    ("Fake charity", "We're distributing food packets to flood victims in Assam. Your contribution of any amount will directly feed a family for a day."),
    
    # --- TECH/PHISHING (no suspicious links) ---
    ("Storage warning", "Your cloud storage is 98% full. Some of your files may be deleted automatically. Upgrade now to keep your data safe."),
    ("Fake security alert", "Someone tried to access your account from an unrecognized device in Mumbai. If this wasn't you, please reset your credentials immediately."),
    ("Subscription trap", "Your premium subscription is expiring tomorrow. To avoid losing your saved data and preferences, renew before midnight."),
    
    # --- INDIA-SPECIFIC (subtle) ---
    ("Subtle FASTag", "Your vehicle toll account has a pending balance. Services may be affected if not resolved within 24 hours. Please update at your earliest."),
    ("Gas connection scam", "Your LPG subsidy transfer has been put on hold due to incomplete verification. Complete the process to resume your subsidized gas supply."),
    ("Ration card update", "Important: Your ration card needs to be linked with your Aadhaar by March 1st. Visit the link to update or you may lose your benefits."),
    
    # --- HINGLISH/MIXED LANGUAGE ---
    ("Hinglish investment", "Bhai ek scheme hai jisme daily 2-3 hazar milte hai. Maine khud try kiya hai. Tujhe sirf ek baar invest karna hai, baaki automatic hai."),
    ("Hinglish lottery", "Aapka number hamare lucky draw mein select hua hai. Bas ek chhoti si formality hai, phir aapko prize mil jayega. Jaldi reply karo."),
    ("Hinglish urgency", "Sir aapka account block hone wala hai. Kal tak verify nahi kiya toh paisa withdraw nahi kar paoge. Abhi details bhejo."),
]

def test_live():
    print("=" * 90)
    print("🔥 STRESS TEST: 25 Hard Scam Messages → Live Cloud Run Endpoint")
    print(f"🌐 URL: {API_URL}")
    print("=" * 90)
    
    results = []
    
    for i, (name, msg) in enumerate(HARD_SCAMS, 1):
        session_id = f"hard-scam-stress-{i:03d}"
        
        payload = {
            "sessionId": session_id,
            "message": {
                "sender": "scammer",
                "text": msg,
                "timestamp": "2026-02-15T16:00:00Z"
            },
            "metadata": {"channel": "SMS", "language": "en", "locale": "IN"}
        }
        
        start = time.time()
        try:
            resp = requests.post(API_URL, json=payload, headers={
                "Content-Type": "application/json",
                "x-api-key": API_KEY
            }, timeout=60)
            latency = round(time.time() - start, 1)
            
            if resp.status_code == 200:
                data = resp.json()
                detected = data.get("scamDetected", False)
                reply = data.get("reply", "")
                icon = "✅" if detected else "❌"
                
                print(f"\n{i:2d}. [{name}] {icon} scamDetected={detected} ({latency}s)")
                print(f"    📩 \"{msg[:75]}...\"")
                print(f"    💬 \"{reply[:80]}\"")
                
                results.append({"name": name, "detected": detected, "latency": latency, "reply": reply})
            else:
                print(f"\n{i:2d}. [{name}] ⚠️ HTTP {resp.status_code}: {resp.text[:100]} ({latency}s)")
                results.append({"name": name, "detected": False, "latency": latency, "reply": f"ERROR {resp.status_code}"})
        except Exception as e:
            latency = round(time.time() - start, 1)
            print(f"\n{i:2d}. [{name}] ❌ ERROR: {e} ({latency}s)")
            results.append({"name": name, "detected": False, "latency": latency, "reply": str(e)})
    
    # Summary
    print("\n" + "=" * 90)
    print("📊 RESULTS SUMMARY")
    print("=" * 90)
    
    caught = sum(1 for r in results if r["detected"])
    missed = sum(1 for r in results if not r["detected"])
    avg_latency = round(sum(r["latency"] for r in results) / len(results), 1)
    
    print(f"\n✅ Scams Detected:  {caught}/{len(HARD_SCAMS)} ({round(caught/len(HARD_SCAMS)*100)}%)")
    print(f"❌ Scams Missed:    {missed}/{len(HARD_SCAMS)}")
    print(f"⏱️  Avg Latency:     {avg_latency}s")
    print(f"⏱️  Total Time:      {round(sum(r['latency'] for r in results))}s")
    
    if missed > 0:
        print(f"\n--- MISSED SCAMS ---")
        for r in results:
            if not r["detected"]:
                print(f"  ❌ {r['name']}")
    
    print()
    if caught == len(HARD_SCAMS):
        print("🏆 PERFECT SCORE! All 25 hard scams detected!")
    elif caught >= 20:
        print(f"🎯 EXCELLENT! {caught}/25 detected — strong performance on hard scams")
    elif caught >= 15:
        print(f"👍 GOOD! {caught}/25 detected — room for improvement on edge cases")
    else:
        print(f"⚠️ NEEDS WORK: Only {caught}/25 detected")


if __name__ == "__main__":
    test_live()
