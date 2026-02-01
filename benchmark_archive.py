#!/usr/bin/env python3
"""
Honeypot Benchmark using Archive Test Files
Tests scam detection accuracy using provided labeled datasets
Calculates: TP, FP, TN, FN, Precision, Recall, F1, Accuracy
"""

import requests
import json
import re
import sys
from pathlib import Path
# No external dependencies needed

API_URL = "http://localhost:8000/v1/chat"
API_KEY = "secret-key-12345"

# Limit messages to test (set to None for all)
MAX_MESSAGES = 200  # Testing 200 per category

def is_phone_call(msg):
    """Detect if message is a phone call script (not SMS)"""
    call_indicators = [
        r'\bpress \d\b',  # "Press 1", "Press 2"
        r'\bthis call\b',
        r'\bcourtesy call\b',
        r'\bwe are calling\b',
        r'\bi am calling\b',
        r'\bnotification bot\b',
        r'\bautomated (message|call)\b',
        r'\bhear this message again\b',
        r'\bto be connected\b',
        r'\bspeak with (a|our)\b',
    ]
    msg_lower = msg.lower()
    for pattern in call_indicators:
        if re.search(pattern, msg_lower):
            return True
    # Phone calls tend to be much longer than SMS
    if len(msg) > 600:
        return True
    return False

def load_messages(file_path, sms_only=True):
    """Load messages from archive file"""
    messages = []
    with open(file_path, 'r', encoding='utf-8') as f:
        text = f.read()
        lines = text.strip().split('\n')
        current_msg = []
        for line in lines:
            line = line.strip()
            if not line:
                if current_msg:
                    messages.append(' '.join(current_msg))
                    current_msg = []
            else:
                cleaned = re.sub(r'^\d+\.\s*', '', line)
                if cleaned:
                    current_msg.append(cleaned)
        if current_msg:
            messages.append(' '.join(current_msg))
    
    messages = [m for m in messages if len(m) > 10]
    
    if sms_only:
        original_count = len(messages)
        messages = [m for m in messages if not is_phone_call(m)]
        print(f"Filtered {original_count - len(messages)} phone calls, kept {len(messages)} SMS")
    
    return messages

def test_message(msg, idx):
    """Test a single message and return scam_detected flag"""
    try:
        payload = {
            "sessionId": f"benchmark-{idx}",
            "message": {"sender": "scammer", "text": msg},
            "conversationHistory": [],
            "metadata": {"channel": "SMS", "language": "English", "locale": "IN"}
        }
        response = requests.post(
            API_URL,
            json=payload,
            headers={"x-api-key": API_KEY},
            timeout=30
        )
        if response.status_code == 200:
            return response.json().get("scamDetected", False)
        return None
    except Exception as e:
        print(f"Error: {e}")
        return None

def main():
    archive_dir = Path(__file__).parent / "archive"
    scam_file = archive_dir / "English_Scam.txt"
    nonscam_file = archive_dir / "English_NonScam.txt"
    
    print("=" * 70)
    print("🔬 HONEYPOT SCAM DETECTION BENCHMARK (Archive Dataset)")
    print("=" * 70)
    
    # Load messages
    scam_msgs = load_messages(scam_file)
    nonscam_msgs = load_messages(nonscam_file)
    
    if MAX_MESSAGES:
        scam_msgs = scam_msgs[:MAX_MESSAGES]
        nonscam_msgs = nonscam_msgs[:MAX_MESSAGES]
    
    print(f"Scam messages loaded: {len(scam_msgs)}")
    print(f"Non-scam messages loaded: {len(nonscam_msgs)}")
    print("=" * 70)
    
    # Metrics counters
    TP = FP = TN = FN = 0
    errors = 0
    
    # Test scam messages (should be detected as scam)
    print("\n📧 Testing SCAM messages (expected: scamDetected=True)...")
    for i, msg in enumerate(scam_msgs, 1):
        result = test_message(msg, f"scam-{i}")
        preview = msg[:50] + "..." if len(msg) > 50 else msg
        if result is None:
            errors += 1
            status = "⚠️ ERR"
        elif result:
            TP += 1
            status = "✅ TP "
        else:
            FN += 1
            status = "❌ FN "
        print(f"[{i:03}] {status} | {preview}")
        sys.stdout.flush()
    
    # Test non-scam messages (should NOT be detected as scam)
    print("\n📧 Testing NON-SCAM messages (expected: scamDetected=False)...")
    for i, msg in enumerate(nonscam_msgs, 1):
        result = test_message(msg, f"nonscam-{i}")
        preview = msg[:50] + "..." if len(msg) > 50 else msg
        if result is None:
            errors += 1
            status = "⚠️ ERR"
        elif result:
            FP += 1
            status = "❌ FP "
        else:
            TN += 1
            status = "✅ TN "
        print(f"[{i:03}] {status} | {preview}")
        sys.stdout.flush()
    
    # Calculate metrics
    print("\n" + "=" * 70)
    print("📊 CONFUSION MATRIX")
    print("=" * 70)
    
    print(f"""
                    Predicted
                SCAM    |  NON-SCAM
           +-----------+-----------+
    Actual |           |           |
      SCAM |  TP: {TP:4} |  FN: {FN:4} |
           +-----------+-----------+
  NON-SCAM |  FP: {FP:4} |  TN: {TN:4} |
           +-----------+-----------+
""")
    
    total = TP + TN + FP + FN
    accuracy = (TP + TN) / total * 100 if total > 0 else 0
    precision = TP / (TP + FP) * 100 if (TP + FP) > 0 else 0
    recall = TP / (TP + FN) * 100 if (TP + FN) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
    
    print("=" * 70)
    print("📈 PERFORMANCE METRICS")
    print("=" * 70)
    
    metrics = [
        ["Accuracy", f"{accuracy:.1f}%", "(TP+TN)/(TP+TN+FP+FN)"],
        ["Precision", f"{precision:.1f}%", "TP/(TP+FP) - How many detected scams are real"],
        ["Recall", f"{recall:.1f}%", "TP/(TP+FN) - How many real scams were caught"],
        ["F1 Score", f"{f1:.1f}%", "Harmonic mean of Precision & Recall"],
    ]
    
    for m in metrics:
        print(f"  {m[0]:<12}: {m[1]:<8} - {m[2]}")
    
    print("\n" + "=" * 70)
    print("📋 SUMMARY")
    print("=" * 70)
    summary = [
        ["Total Tests", total],
        ["True Positives (TP)", TP],
        ["True Negatives (TN)", TN],
        ["False Positives (FP)", FP],
        ["False Negatives (FN)", FN],
        ["Errors", errors],
    ]
    for s in summary:
        print(f"  {s[0]:<25}: {s[1]}")
    
    # Rating
    print("\n")
    if f1 >= 90:
        print("🏆 EXCELLENT! F1 Score >= 90%")
    elif f1 >= 80:
        print("✅ GOOD! F1 Score >= 80%")
    elif f1 >= 70:
        print("⚠️ FAIR - F1 Score >= 70%")
    else:
        print("❌ NEEDS IMPROVEMENT - F1 Score < 70%")
    
    return {"TP": TP, "TN": TN, "FP": FP, "FN": FN, "accuracy": accuracy, "precision": precision, "recall": recall, "f1": f1}

if __name__ == "__main__":
    main()
