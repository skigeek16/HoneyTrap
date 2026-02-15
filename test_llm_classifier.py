"""
Test LLM Classifier on Hard-to-Detect Scam Messages
Compares Regex vs LLM on messages that would BYPASS regex.
"""
import os
import sys
import time

# Set env vars
os.environ["LLM_API_KEY"] = "v1.CmQKHHN0YXRpY2tleS1lMDBycTJlczg3YnhxNzV0eDQSIXNlcnZpY2VhY2NvdW50LWUwMGhkZHg3enI3MG1qc2pwcDIMCPa33ssGEJTW8_YCOgwI9br2lgcQgPjOowNAAloDZTAw.AAAAAAAAAAHDHmpqjy3eiyvZ947LNHi8lxjQNWLzWKefCO2O0U90GmdvoVvUjrGNX3BnJ7tUy8ncV31DD_uWSy07p3J_9oIM"
os.environ["LLM_API_URL"] = "https://api.tokenfactory.nebius.com/v1/"
os.environ["LLM_MODEL"] = "meta-llama/Llama-3.3-70B-Instruct-fast"

from detectors.llm_classifier import LLMScamClassifier
from detectors.rule_based import RuleBasedDetector

# ============ TEST MESSAGES ============

# HARD SCAMS: Bypass regex but LLM should catch
HARD_SCAMS = [
    ("Paraphrased KYC", "Your banking service needs attention. Please review your profile at your earliest convenience to avoid any disruption."),
    ("Subtle Prize", "Hi! You've been selected as part of our loyalty program. A small formality is needed to process your reward. Reach out to us at wa.me/919999888877"),
    ("Vague Threat", "We noticed some irregularities on your profile. Please get back to us within today to resolve this matter, or further steps will be taken."),
    ("Social Engineering", "Hey, I found your number from a mutual friend. I have an amazing business opportunity that can change your life. Are you interested?"),
    ("Emotional Manipulation", "I'm a student and my mother is in the hospital. I need Rs 2000 urgently for medicine. I'll return it tomorrow. Please help me. UPI: help4mom@paytm"),
    ("Professional Scam", "Our records show a pending refund of Rs 15,000 in your name. To process it, we need to verify your identity. Reply with your full name and date of birth."),
    ("Crypto Scam", "Join our exclusive trading group. Our AI bot generates 15% weekly returns. Start with just Rs 5000. DM me for the invite link."),
    ("Hinglish Subtle", "Bhai tere number pe ek offer aaya hai. Mujhe bas thoda sa help chahiye process karne ke liye. Kal tak paise double ho jayenge."),
]

# LEGITIMATE: Should NOT be flagged
LEGITIMATE = [
    ("Doctor Appointment", "Reminder: Your appointment with Dr. Sharma is scheduled for tomorrow at 10 AM. Please arrive 15 minutes early."),
    ("Delivery Update", "Your Amazon order #1234 has been shipped and will arrive by Feb 16. Track at amazon.in/track"),
    ("Friend Message", "Hey! Are we still meeting for coffee at 5pm today? Let me know if you need to reschedule."),
    ("Work Email", "Please review the Q3 report and share your feedback by end of day. The team meeting is at 3 PM."),
    ("Bank Genuine", "Your SBI account **4532 has been credited with Rs 25,000. Available balance: Rs 1,42,350. - SBI"),
]

# EASY SCAMS: Sanity check — both should catch
EASY_SCAMS = [
    ("KYC Direct", "Dear Customer, your SBI account KYC is expiring. Click http://sbi-kyc.in to update immediately or account will be blocked."),
    ("Lottery Direct", "Congratulations! You won Rs 25 lakh in KBC Lucky Draw! Pay Rs 4500 processing fee to claim."),
]


def run_tests():
    print("=" * 80)
    print("🔍 HoneyTrap LLM Classifier Test — Hard-to-Detect Messages")
    print("=" * 80)
    
    llm = LLMScamClassifier()
    rule = RuleBasedDetector()
    
    if not llm.is_enabled():
        print("❌ LLM not enabled! Check LLM_API_KEY")
        return
    
    print(f"✅ LLM enabled — Model: {llm.model}\n")
    
    results = {"hard_scam": [], "legit": [], "easy_scam": []}
    
    # Test hard scams
    print("\n" + "=" * 80)
    print("🎯 HARD SCAMS (should bypass regex but LLM should catch)")
    print("=" * 80)
    for name, msg in HARD_SCAMS:
        rule_res = rule.analyze(msg)
        rule_score = rule_res['rule_score']
        
        start = time.time()
        llm_res = llm.classify(msg)
        latency = round(time.time() - start, 1)
        
        llm_score = llm_res['llm_score']
        caught_by_regex = "✅" if rule_score >= 22 else "❌"
        caught_by_llm = "✅" if llm_score >= 60 else "❌"
        
        print(f"\n📩 [{name}]: \"{msg[:70]}...\"")
        print(f"   Regex: {caught_by_regex} (score: {rule_score:.0f})")
        print(f"   LLM:   {caught_by_llm} (score: {llm_score:.0f}) — {llm_res['llm_scam_type']} ({latency}s)")
        print(f"   Reason: {llm_res['llm_reasoning']}")
        
        results["hard_scam"].append({"name": name, "regex": rule_score, "llm": llm_score})
    
    # Test legitimate messages
    print("\n" + "=" * 80)
    print("✅ LEGITIMATE (should NOT be flagged)")
    print("=" * 80)
    for name, msg in LEGITIMATE:
        rule_res = rule.analyze(msg)
        rule_score = rule_res['rule_score']
        
        start = time.time()
        llm_res = llm.classify(msg)
        latency = round(time.time() - start, 1)
        
        llm_score = llm_res['llm_score']
        false_positive_regex = "⚠️ FP!" if rule_score >= 22 else "✅ OK"
        false_positive_llm = "⚠️ FP!" if llm_score >= 60 else "✅ OK"
        
        print(f"\n📩 [{name}]: \"{msg[:70]}...\"")
        print(f"   Regex: {false_positive_regex} (score: {rule_score:.0f})")
        print(f"   LLM:   {false_positive_llm} (score: {llm_score:.0f}) — {llm_res['llm_scam_type']} ({latency}s)")
        
        results["legit"].append({"name": name, "regex": rule_score, "llm": llm_score})
    
    # Test easy scams
    print("\n" + "=" * 80)
    print("🎯 EASY SCAMS (sanity check — both should catch)")
    print("=" * 80)
    for name, msg in EASY_SCAMS:
        rule_res = rule.analyze(msg)
        rule_score = rule_res['rule_score']
        
        start = time.time()
        llm_res = llm.classify(msg)
        latency = round(time.time() - start, 1)
        
        llm_score = llm_res['llm_score']
        print(f"\n📩 [{name}]: \"{msg[:70]}...\"")
        print(f"   Regex: {'✅' if rule_score >= 22 else '❌'} (score: {rule_score:.0f})")
        print(f"   LLM:   {'✅' if llm_score >= 60 else '❌'} (score: {llm_score:.0f}) — {llm_res['llm_scam_type']} ({latency}s)")
        
        results["easy_scam"].append({"name": name, "regex": rule_score, "llm": llm_score})
    
    # Summary
    print("\n" + "=" * 80)
    print("📊 SUMMARY")
    print("=" * 80)
    
    hard_regex_caught = sum(1 for r in results["hard_scam"] if r["regex"] >= 22)
    hard_llm_caught = sum(1 for r in results["hard_scam"] if r["llm"] >= 60)
    legit_regex_fp = sum(1 for r in results["legit"] if r["regex"] >= 22)
    legit_llm_fp = sum(1 for r in results["legit"] if r["llm"] >= 60)
    easy_regex = sum(1 for r in results["easy_scam"] if r["regex"] >= 22)
    easy_llm = sum(1 for r in results["easy_scam"] if r["llm"] >= 60)
    
    print(f"\n{'Category':<25} {'Regex':<20} {'LLM Classifier':<20}")
    print(f"{'-'*25} {'-'*20} {'-'*20}")
    print(f"{'Hard Scams Caught':<25} {hard_regex_caught}/{len(HARD_SCAMS):<19} {hard_llm_caught}/{len(HARD_SCAMS):<19}")
    print(f"{'False Positives':<25} {legit_regex_fp}/{len(LEGITIMATE):<19} {legit_llm_fp}/{len(LEGITIMATE):<19}")
    print(f"{'Easy Scams (sanity)':<25} {easy_regex}/{len(EASY_SCAMS):<19} {easy_llm}/{len(EASY_SCAMS):<19}")
    
    print(f"\n🏆 LLM caught {hard_llm_caught - hard_regex_caught} MORE hard scams than regex alone!")
    if legit_llm_fp == 0:
        print("✅ LLM had ZERO false positives on legitimate messages!")
    else:
        print(f"⚠️ LLM had {legit_llm_fp} false positive(s) on legitimate messages")


if __name__ == "__main__":
    run_tests()
