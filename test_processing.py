import sys
import os
import asyncio

# Ensure project root is in path
sys.path.append(os.getcwd())

from processing.detectors.engine import ScamDetectionEngine

def test_engine():
    print("Initializing ScamDetectionEngine...")
    engine = ScamDetectionEngine()
    
    test_message = "Dear customer, your SBI account is blocked. Please click here to update KYC immediately: http://bit.ly/fake"
    print(f"\nTesting with message: '{test_message}'")
    
    try:
        result = engine.evaluate(test_message)
        print("\nEvaluation Result:")
        print(f"Is Scam: {result['is_scam']}")
        print(f"Score: {result['confidence_score']}")
        print(f"Type: {result['scam_type']}")
        print(f"Decision: {result['decision']}")
        print("\nDetails:")
        print(f"Rule Score: {result['details']['rule_based'].get('rule_score')}")
        print(f"ML Phishing Prob: {result['details']['ml_ensemble'].get('phishing_prob')}")
        print(f"LLM Enabled: {result['details']['llm_classifier'].get('llm_enabled')}")
        
    except Exception as e:
        print(f"Error during evaluation: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_engine()
