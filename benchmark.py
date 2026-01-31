#!/usr/bin/env python3
"""
Honeypot Benchmark Evaluation Script
Tests scam detection accuracy with mixed messages (scam + normal)
Calculates: TP, FP, TN, FN, Precision, Recall, F1, Accuracy
"""

import requests
import json
from dataclasses import dataclass
from typing import List

API_URL = "http://localhost:8000/v1/chat"
API_KEY = "secret-key-12345"

# Test dataset with ground truth labels
# label: True = SCAM, False = NORMAL
TEST_MESSAGES = [
    # === SCAM MESSAGES ===
    {"text": "Your bank account will be blocked today. Verify immediately.", "label": True, "type": "Bank Fraud"},
    {"text": "Congratulations! You won ₹50 lakh in lottery. Pay ₹5000 to claim.", "label": True, "type": "Lottery Scam"},
    {"text": "This is Income Tax Department. Pay pending tax of ₹25000 or face arrest.", "label": True, "type": "Tax Scam"},
    {"text": "Your UPI account is suspended. Share OTP to reactivate.", "label": True, "type": "UPI Fraud"},
    {"text": "URGENT: Transfer ₹10000 to avoid account suspension. Call now.", "label": True, "type": "Urgency Scam"},
    {"text": "I am calling from SBI. Your ATM card will be blocked. Share CVV.", "label": True, "type": "Bank Impersonation"},
    {"text": "You have won iPhone 15! Click http://bit.ly/freeiphone to claim.", "label": True, "type": "Prize Scam"},
    {"text": "Your son is in police custody. Send ₹50000 immediately for bail.", "label": True, "type": "Emergency Scam"},
    {"text": "Work from home job! Earn ₹5000 daily. Just invest ₹1000 to start.", "label": True, "type": "Job Scam"},
    {"text": "Your Aadhaar is linked to illegal activities. Pay fine now.", "label": True, "type": "Aadhaar Scam"},
    {"text": "RBI alert: Your account is frozen. Share account details to unfreeze.", "label": True, "type": "RBI Impersonation"},
    {"text": "Crypto investment opportunity! 500% returns guaranteed in 7 days.", "label": True, "type": "Investment Scam"},
    
    # === NORMAL MESSAGES ===
    {"text": "Hi, how are you doing today?", "label": False, "type": "Greeting"},
    {"text": "Can you tell me the weather forecast for tomorrow?", "label": False, "type": "Weather Query"},
    {"text": "What time does the movie start?", "label": False, "type": "General Query"},
    {"text": "Happy birthday! Wishing you a wonderful year ahead.", "label": False, "type": "Wishes"},
    {"text": "The meeting is scheduled for 3 PM tomorrow.", "label": False, "type": "Meeting Info"},
    {"text": "Please find the attached document for your review.", "label": False, "type": "Work Email"},
    {"text": "Thanks for helping me with the project yesterday.", "label": False, "type": "Gratitude"},
    {"text": "Let me know when you're free to discuss the proposal.", "label": False, "type": "Work Query"},
    {"text": "I'll pick you up from the airport at 6 PM.", "label": False, "type": "Travel Info"},
    {"text": "The restaurant is fully booked for Saturday.", "label": False, "type": "Reservation Info"},
    {"text": "Don't forget to bring the documents for the interview.", "label": False, "type": "Reminder"},
    {"text": "The parcel has been delivered to your address.", "label": False, "type": "Delivery Update"},
]

@dataclass
class Metrics:
    tp: int = 0  # True Positive (correctly detected scams)
    fp: int = 0  # False Positive (normal flagged as scam)
    tn: int = 0  # True Negative (normal correctly ignored)
    fn: int = 0  # False Negative (missed scams)
    
    @property
    def accuracy(self) -> float:
        total = self.tp + self.fp + self.tn + self.fn
        return (self.tp + self.tn) / total if total > 0 else 0
    
    @property
    def precision(self) -> float:
        return self.tp / (self.tp + self.fp) if (self.tp + self.fp) > 0 else 0
    
    @property
    def recall(self) -> float:
        return self.tp / (self.tp + self.fn) if (self.tp + self.fn) > 0 else 0
    
    @property
    def f1_score(self) -> float:
        p, r = self.precision, self.recall
        return 2 * (p * r) / (p + r) if (p + r) > 0 else 0

def test_message(text: str, session_id: str) -> dict:
    """Send a message to the API and get response"""
    payload = {
        "sessionId": session_id,
        "message": {"sender": "scammer", "text": text},
        "conversationHistory": [],
        "metadata": {"channel": "SMS", "language": "English", "locale": "IN"}
    }
    
    try:
        response = requests.post(
            API_URL, 
            json=payload, 
            headers={"x-api-key": API_KEY, "Content-Type": "application/json"},
            timeout=30
        )
        return response.json()
    except Exception as e:
        print(f"Error: {e}")
        return {"status": "error", "reply": ""}

def run_benchmark():
    """Run the benchmark evaluation"""
    print("=" * 70)
    print("🔬 HONEYPOT SCAM DETECTION BENCHMARK")
    print("=" * 70)
    print(f"Total test cases: {len(TEST_MESSAGES)}")
    print(f"Scam messages: {sum(1 for m in TEST_MESSAGES if m['label'])}")
    print(f"Normal messages: {sum(1 for m in TEST_MESSAGES if not m['label'])}")
    print("=" * 70)
    
    metrics = Metrics()
    results = []
    
    for i, test in enumerate(TEST_MESSAGES):
        session_id = f"benchmark-{i}"
        text = test["text"]
        is_scam = test["label"]
        msg_type = test["type"]
        
        response = test_message(text, session_id)
        reply = response.get("reply", "")
        
        # Determine if API detected it as scam based on reply content
        # Non-scam responses are typically: "Thank you for your message, but I'm not interested."
        detected_as_scam = "not interested" not in reply.lower()
        
        # Calculate metrics
        if is_scam and detected_as_scam:
            metrics.tp += 1
            status = "✅ TP"
        elif not is_scam and detected_as_scam:
            metrics.fp += 1
            status = "❌ FP"
        elif not is_scam and not detected_as_scam:
            metrics.tn += 1
            status = "✅ TN"
        else:  # is_scam and not detected_as_scam
            metrics.fn += 1
            status = "❌ FN"
        
        results.append({
            "message": text[:50] + "..." if len(text) > 50 else text,
            "type": msg_type,
            "actual": "SCAM" if is_scam else "NORMAL",
            "detected": "SCAM" if detected_as_scam else "NORMAL",
            "status": status,
            "reply": reply[:60] + "..." if len(reply) > 60 else reply
        })
        
        print(f"[{i+1:02d}] {status} | {msg_type:20s} | {text[:40]}...")
    
    # Print results summary
    print("\n" + "=" * 70)
    print("📊 CONFUSION MATRIX")
    print("=" * 70)
    print(f"""
                    Predicted
                 SCAM    NORMAL
    Actual  SCAM   {metrics.tp:3d}      {metrics.fn:3d}
           NORMAL  {metrics.fp:3d}      {metrics.tn:3d}
    """)
    
    print("=" * 70)
    print("📈 METRICS SUMMARY")
    print("=" * 70)
    print(f"  True Positives (TP):  {metrics.tp}")
    print(f"  False Positives (FP): {metrics.fp}")
    print(f"  True Negatives (TN):  {metrics.tn}")
    print(f"  False Negatives (FN): {metrics.fn}")
    print("-" * 70)
    print(f"  Accuracy:   {metrics.accuracy:.2%}")
    print(f"  Precision:  {metrics.precision:.2%}")
    print(f"  Recall:     {metrics.recall:.2%}")
    print(f"  F1 Score:   {metrics.f1_score:.2%}")
    print("=" * 70)
    
    # Save detailed results to JSON
    output = {
        "metrics": {
            "tp": metrics.tp, "fp": metrics.fp, 
            "tn": metrics.tn, "fn": metrics.fn,
            "accuracy": metrics.accuracy,
            "precision": metrics.precision,
            "recall": metrics.recall,
            "f1_score": metrics.f1_score
        },
        "results": results
    }
    
    with open("benchmark_results.json", "w") as f:
        json.dump(output, f, indent=2)
    
    print(f"\n💾 Detailed results saved to: benchmark_results.json")

if __name__ == "__main__":
    run_benchmark()
