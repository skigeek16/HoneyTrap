"""
Stress Test: Simulates all 15 evaluation scenarios × 10 turns each = 150 API calls.
Matches the exact evaluation flow described in Participants Queries doc.
"""
import requests
import time
import json
import sys

API_URL = "http://localhost:7860/v1/chat"
API_KEY = "secret-key-12345"
HEADERS = {"Content-Type": "application/json", "x-api-key": API_KEY}

# All 15 scenarios from evaluation (Participants Queries doc)
SCENARIOS = [
    {
        "name": "Bank Fraud",
        "turns": [
            "URGENT: Your SBI account has been compromised. Your account will be blocked in 2 hours unless you verify immediately.",
            "Sir this is from RBI fraud cell. Your account number 1234567890123 has unauthorized transactions of Rs 50,000.",
            "You need to transfer security deposit of Rs 5,000 to verify. Send to UPI: rbi.verify@oksbi",
            "Sir please hurry, your account will be permanently blocked. Call me at 9876543210 for immediate assistance.",
            "I am sending you verification link: http://sbi-verify-secure.com/auth. Click and enter your details.",
            "Sir your card ending 4567 has been used. Share OTP to block the card immediately.",
            "Transfer Rs 2,000 to bank account 9876543210987654 IFSC SBIN0001234 for insurance claim.",
            "Send the amount to fraudhelp@sbi-secure.com via email transfer. This is very urgent.",
            "Sir I can see your account is about to be frozen. Last chance to save your money.",
            "Final warning. Transfer now or face legal action. Contact helpdesk@rbi-fraud.org"
        ],
        "expected_intel": {"phones": ["9876543210"], "banks": ["1234567890123", "9876543210987654"], "upis": ["rbi.verify@oksbi"], "links": ["http://sbi-verify-secure.com/auth"], "emails": ["fraudhelp@sbi-secure.com", "helpdesk@rbi-fraud.org"]}
    },
    {
        "name": "UPI Fraud",
        "turns": [
            "Congratulations! You've won Rs 10 lakh cashback on PhonePe. Claim now!",
            "To claim your prize, send Rs 500 processing fee to UPI: cashback.claim@ybl",
            "Sir I am PhonePe executive. My ID is PP-45678. Call me at 8765432109.",
            "Send the fee to our verified account 5678901234567890 HDFC Bank.",
            "You can also pay via Google Pay to gpay.prize@okaxis. Very easy sir.",
            "Hurry! Offer expires in 30 minutes. Visit http://phonepe-cashback-claim.in/verify",
            "Let me send you confirmation email. What's your email? Mine is support@phonepe-rewards.com",
            "Sir your cashback of Rs 10,00,000 is ready. Just Rs 500 more for GST.",
            "Send to alternate UPI winner.verify@paytm if other one doesn't work.",
            "Last chance sir. After this your prize will be given to someone else."
        ],
        "expected_intel": {"phones": ["8765432109"], "banks": ["5678901234567890"], "upis": ["cashback.claim@ybl", "gpay.prize@okaxis", "winner.verify@paytm"], "links": ["http://phonepe-cashback-claim.in/verify"], "emails": ["support@phonepe-rewards.com"]}
    },
    {
        "name": "Phishing Link",
        "turns": [
            "Dear Customer, your PAN card is linked to multiple accounts. Update KYC immediately.",
            "Click this link to update: http://pan-kyc-update.in/verify?ref=urgent",
            "Sir I am from Income Tax department. Your PAN ABCDE1234F has been flagged.",
            "Call our helpline 7654321098 or email kyc.update@incometax-verify.org",
            "If you don't update within 24 hours, your accounts will be frozen under Section 139.",
            "Visit http://kyc-aadhaar-link.com/update to complete verification.",
            "Send your Aadhaar copy to verify. My UPI for processing fee: itdept@oksbi",
            "Your bank account 3456789012345678 has been flagged for IT scrutiny.",
            "This is your final notice. Contact officer.sharma@it-department.org immediately.",
            "Pay penalty of Rs 1,000 via UPI to penalty.collection@ybl to avoid arrest."
        ],
        "expected_intel": {"phones": ["7654321098"], "banks": ["3456789012345678"], "upis": ["itdept@oksbi", "penalty.collection@ybl"], "links": ["http://pan-kyc-update.in/verify?ref=urgent", "http://kyc-aadhaar-link.com/update"], "emails": ["kyc.update@incometax-verify.org", "officer.sharma@it-department.org"]}
    },
    {
        "name": "KYC Fraud",
        "turns": [
            "Your bank KYC is expired. Update immediately to avoid account suspension.",
            "Visit http://kyc-bank-update.com/renew or your account will be deactivated.",
            "I am bank manager Rajesh Kumar. Contact me at 6543210987.",
            "Share your Aadhaar and PAN for verification. UPI: kyc.renewal@okicici",
            "Your fixed deposit of Rs 5,00,000 is at risk. Act now.",
            "Transfer KYC fee Rs 299 to account 2345678901234567 ICICI Bank.",
            "Email your documents to kyc.support@icici-bankverify.com for faster processing.",
            "Visit our portal: http://icici-kyc-portal.in/upload to submit documents.",
            "Sir this is last reminder. Your account 2345678901234567 will be closed tomorrow.",
            "Call our senior manager at 6543210987 or pay via UPI: manager.rajesh@okicici"
        ],
        "expected_intel": {"phones": ["6543210987"], "banks": ["2345678901234567"], "upis": ["kyc.renewal@okicici", "manager.rajesh@okicici"], "links": ["http://kyc-bank-update.com/renew", "http://icici-kyc-portal.in/upload"], "emails": ["kyc.support@icici-bankverify.com"]}
    },
    {
        "name": "Job Scam",
        "turns": [
            "Exciting WFH opportunity! Earn Rs 50,000/month doing simple data entry tasks.",
            "Apply now at http://jobs-wfh-india.com/apply. Limited positions available!",
            "I am HR manager Priya Sharma. Call me at 9988776655 for interview details.",
            "Pay registration fee Rs 1,500 via UPI: hr.recruitment@ybl to confirm your slot.",
            "Our company email is careers@wfh-jobs-india.com. Send your resume there.",
            "After payment, your employee ID and login will be emailed within 1 hour.",
            "You can also transfer to bank account 6789012345678901 Axis Bank.",
            "Visit http://wfh-training-portal.com/register for training materials.",
            "First month salary Rs 50,000 guaranteed. Just Rs 1,500 to start. Very small amount.",
            "Hurry! Only 3 positions left. Pay via UPI: jobs.hiring@okaxis today."
        ],
        "expected_intel": {"phones": ["9988776655"], "banks": ["6789012345678901"], "upis": ["hr.recruitment@ybl", "jobs.hiring@okaxis"], "links": ["http://jobs-wfh-india.com/apply", "http://wfh-training-portal.com/register"], "emails": ["careers@wfh-jobs-india.com"]}
    },
    {
        "name": "Lottery Scam",
        "turns": [
            "CONGRATULATIONS! You have won Rs 25,00,000 in the National Digital Lottery!",
            "To claim, pay processing fee Rs 5,000. UPI: lottery.claim@ybl",
            "I am lottery officer Amit Verma. My number is 8877665544.",
            "Visit http://national-lottery-india.com/claim to register your win.",
            "Send processing fee to account 7890123456789012 PNB Bank.",
            "Email your ID proof to winner@national-lottery.org to verify identity.",
            "Sir your winning ticket number is NL-789456. This is 100% genuine.",
            "Pay GST of Rs 2,000 via UPI: lottery.gst@oksbi to release winnings.",
            "Your Rs 25 lakh will be transferred within 24 hours of payment.",
            "Final deadline is today. Call 8877665544 or lose your prize forever."
        ],
        "expected_intel": {"phones": ["8877665544"], "banks": ["7890123456789012"], "upis": ["lottery.claim@ybl", "lottery.gst@oksbi"], "links": ["http://national-lottery-india.com/claim"], "emails": ["winner@national-lottery.org"]}
    },
    {
        "name": "Electricity Bill",
        "turns": [
            "ALERT: Your electricity connection will be disconnected today due to unpaid bill of Rs 8,456.",
            "Pay immediately via UPI: electricity.bill@ybl to avoid disconnection.",
            "I am BSES officer. Contact 7766554433 for bill details.",
            "Visit http://bses-bill-payment.com/pay to clear your dues online.",
            "Transfer Rs 8,456 to account 8901234567890123 SBI for bill clearance.",
            "Email your consumer number to billing@bses-payment.org for receipt.",
            "Your meter number MR-456789 shows outstanding dues. Pay now.",
            "After payment, send screenshot to billing.verify@bses-payment.org",
            "Alternate UPI: bses.urgent@okicici if first one doesn't work.",
            "Your power will be cut in 2 hours. This is final notice. Call 7766554433."
        ],
        "expected_intel": {"phones": ["7766554433"], "banks": ["8901234567890123"], "upis": ["electricity.bill@ybl", "bses.urgent@okicici"], "links": ["http://bses-bill-payment.com/pay"], "emails": ["billing@bses-payment.org", "billing.verify@bses-payment.org"]}
    },
    {
        "name": "Govt Scheme",
        "turns": [
            "You are eligible for PM Kisan Samman Nidhi. Rs 12,000 direct to your account!",
            "Register at http://pm-kisan-yojana.gov.in.com/register to claim.",
            "I am from Agriculture Ministry. Call 6655443322 for registration help.",
            "Pay Rs 250 registration via UPI: pmkisan.register@ybl",
            "Email your Aadhaar to register@pmkisan-scheme.org for verification.",
            "Your subsidy will be sent to your bank. Share account for verification.",
            "Transfer registration fee to 9012345678901234 Bank of Baroda.",
            "Visit http://pmkisan-verify.com/aadhaar to link Aadhaar.",
            "Alternate payment UPI: govt.scheme@oksbi. Very easy process.",
            "Hurry, registration closes tomorrow. Call 6655443322 now."
        ],
        "expected_intel": {"phones": ["6655443322"], "banks": ["9012345678901234"], "upis": ["pmkisan.register@ybl", "govt.scheme@oksbi"], "links": ["http://pm-kisan-yojana.gov.in.com/register", "http://pmkisan-verify.com/aadhaar"], "emails": ["register@pmkisan-scheme.org"]}
    },
    {
        "name": "Crypto Investment",
        "turns": [
            "Triple your money in 30 days! Invest in our exclusive crypto fund. Guaranteed 300% returns!",
            "Visit http://crypto-fund-india.com/invest to see our track record.",
            "I am fund manager Vikram Mehta. WhatsApp me at 9544332211.",
            "Minimum investment Rs 10,000 via UPI: crypto.invest@ybl",
            "Email invest@crypto-fund-india.com for detailed portfolio report.",
            "Transfer to our trading account 1234509876543210 HDFC Bank.",
            "We accept crypto too. Our Bitcoin wallet: bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh",
            "Visit http://crypto-returns-tracker.com/dashboard to see live returns.",
            "Alt UPI: fund.manager@okaxis. Invest today, withdraw anytime.",
            "Last chance for guaranteed 300% returns. Act now or miss out forever."
        ],
        "expected_intel": {"phones": ["9544332211"], "banks": ["1234509876543210"], "upis": ["crypto.invest@ybl", "fund.manager@okaxis"], "links": ["http://crypto-fund-india.com/invest", "http://crypto-returns-tracker.com/dashboard"], "emails": ["invest@crypto-fund-india.com"]}
    },
    {
        "name": "Customs Parcel",
        "turns": [
            "Your international parcel has been seized by Indian Customs. Pay clearance fee immediately.",
            "Visit http://customs-clearance-india.com/pay to release your parcel.",
            "I am customs officer Inspector Sharma. Call 8433221100 for case details.",
            "Pay customs duty Rs 15,000 via UPI: customs.duty@ybl",
            "Email your passport copy to clearance@customs-india.org for verification.",
            "Transfer duty to account 5432109876543210 PNB Bank.",
            "Your parcel tracking number is CU-987654. It contains suspicious items.",
            "Visit http://india-customs-portal.com/verify to check parcel status.",
            "Alt UPI: inspector.sharma@oksbi if payment pending.",
            "If not cleared in 24 hours, parcel will be destroyed and FIR filed against you."
        ],
        "expected_intel": {"phones": ["8433221100"], "banks": ["5432109876543210"], "upis": ["customs.duty@ybl", "inspector.sharma@oksbi"], "links": ["http://customs-clearance-india.com/pay", "http://india-customs-portal.com/verify"], "emails": ["clearance@customs-india.org"]}
    },
    {
        "name": "Tech Support",
        "turns": [
            "Microsoft Security Alert: Your computer has been infected with a critical virus. Call immediately.",
            "Visit http://microsoft-support-india.com/fix to download security patch.",
            "I am Microsoft engineer Rahul. Call me at 7322110099 for remote access.",
            "Pay Rs 3,000 for premium antivirus via UPI: microsoft.support@ybl",
            "Email your system details to techsupport@microsoft-help.org for diagnosis.",
            "Transfer payment to account 6543210987654321 Kotak Bank.",
            "I need TeamViewer access. Your PC ID shows virus infection.",
            "Visit http://ms-security-update.com/install for urgent patch.",
            "Alt UPI: tech.repair@okicici. Virus will spread to your phone too.",
            "If you don't fix now your data will be stolen. This is very serious."
        ],
        "expected_intel": {"phones": ["7322110099"], "banks": ["6543210987654321"], "upis": ["microsoft.support@ybl", "tech.repair@okicici"], "links": ["http://microsoft-support-india.com/fix", "http://ms-security-update.com/install"], "emails": ["techsupport@microsoft-help.org"]}
    },
    {
        "name": "Loan Approval",
        "turns": [
            "Pre-approved personal loan of Rs 5,00,000 at just 2% interest! No documents needed.",
            "Apply at http://instant-loan-india.com/apply. Approval in 5 minutes!",
            "I am loan officer Neha Singh. Call 6211009988 for instant approval.",
            "Pay processing fee Rs 2,000 via UPI: loan.approval@ybl",
            "Email income proof to loans@instant-finance.com for higher limit.",
            "Transfer fee to account 7654321098765432 IDBI Bank.",
            "Your loan reference number is LN-456789. Amount sanctioned!",
            "Visit http://loan-disbursement.in/status to track disbursement.",
            "Alt UPI: neha.loans@okaxis. Pay now, get money in 1 hour.",
            "Offer valid today only. After today interest rate will be 12%."
        ],
        "expected_intel": {"phones": ["6211009988"], "banks": ["7654321098765432"], "upis": ["loan.approval@ybl", "neha.loans@okaxis"], "links": ["http://instant-loan-india.com/apply", "http://loan-disbursement.in/status"], "emails": ["loans@instant-finance.com"]}
    },
    {
        "name": "Income Tax",
        "turns": [
            "NOTICE: Income Tax refund of Rs 45,000 is pending. Claim before it expires.",
            "Visit http://incometax-refund.gov.in.org/claim to process your refund.",
            "I am IT officer from CPC Bangalore. Call 9100887766 for case number.",
            "Pay verification fee Rs 500 via UPI: itrefund.verify@ybl",
            "Email your Form 16 to refund@incometax-portal.org for processing.",
            "Your PAN FGHIJ5678K has refund. Transfer fee to 8765432109876543 SBI.",
            "Refund will be credited within 48 hours of verification.",
            "Visit http://it-refund-status.com/track for status update.",
            "Alt UPI: tax.refund@oksbi. Processing is almost complete.",
            "Last date for refund claim is today. After that amount will lapse."
        ],
        "expected_intel": {"phones": ["9100887766"], "banks": ["8765432109876543"], "upis": ["itrefund.verify@ybl", "tax.refund@oksbi"], "links": ["http://incometax-refund.gov.in.org/claim", "http://it-refund-status.com/track"], "emails": ["refund@incometax-portal.org"]}
    },
    {
        "name": "Refund Scam",
        "turns": [
            "Your Amazon order refund of Rs 12,000 failed. Contact support to reprocess.",
            "Visit http://amazon-refund-help.com/process to initiate refund.",
            "I am Amazon customer care. Call 8099776655 for order details.",
            "Account verification needed. Share UPI for direct refund. Our UPI: amazon.refund@ybl",
            "Email order details to support@amazon-refund-help.org to expedite.",
            "We accidentally sent Rs 1,20,000 instead of Rs 12,000. Please return Rs 1,08,000.",
            "Transfer excess to account 9876543210123456 Yes Bank immediately.",
            "Visit http://amazon-return-verify.com/excess to see the transaction.",
            "Alt UPI: refund.return@okicici. Return the extra amount please.",
            "Sir this is urgent. Our system shows extra credit. Legal team will contact you if not returned."
        ],
        "expected_intel": {"phones": ["8099776655"], "banks": ["9876543210123456"], "upis": ["amazon.refund@ybl", "refund.return@okicici"], "links": ["http://amazon-refund-help.com/process", "http://amazon-return-verify.com/excess"], "emails": ["support@amazon-refund-help.org"]}
    },
    {
        "name": "Insurance",
        "turns": [
            "Your LIC policy has matured! Claim Rs 8,00,000 bonus amount immediately.",
            "Visit http://lic-policy-claim.com/bonus to submit claim.",
            "I am LIC agent Suresh. My number is 7088665544.",
            "Pay claim processing fee Rs 3,000 via UPI: lic.claim@ybl",
            "Email policy documents to claims@lic-bonus-payout.org for verification.",
            "Transfer fee to account 1098765432109876 LIC Housing Finance.",
            "Your policy number LI-789012 shows bonus accumulated over 20 years.",
            "Visit http://lic-bonus-calculator.in/check to see your exact amount.",
            "Alt UPI: agent.suresh@oksbi. Pay today and get bonus this week.",
            "Policy bonus expires end of month. After that it will be forfeited."
        ],
        "expected_intel": {"phones": ["7088665544"], "banks": ["1098765432109876"], "upis": ["lic.claim@ybl", "agent.suresh@oksbi"], "links": ["http://lic-policy-claim.com/bonus", "http://lic-bonus-calculator.in/check"], "emails": ["claims@lic-bonus-payout.org"]}
    }
]


def run_stress_test():
    print("=" * 80)
    print(f"HONEYTRAP STRESS TEST — {len(SCENARIOS)} scenarios × 10 turns = {len(SCENARIOS)*10} API calls")
    print("=" * 80)
    
    total_calls = 0
    total_time = 0
    total_errors = 0
    total_timeouts = 0
    scenario_results = []
    
    for i, scenario in enumerate(SCENARIOS):
        print(f"\n{'─'*70}")
        print(f"📋 Scenario {i+1}/15: {scenario['name']}")
        print(f"{'─'*70}")
        
        session_id = f"stress-test-{scenario['name'].lower().replace(' ', '-')}"
        history = []
        turn_times = []
        last_response = None
        errors = 0
        
        for turn_num, scammer_msg in enumerate(scenario['turns']):
            t0 = time.time()
            
            payload = {
                "sessionId": session_id,
                "message": {"sender": "scammer", "text": scammer_msg},
                "conversationHistory": history,
                "metadata": {"channel": "SMS", "language": "English", "locale": "IN"}
            }
            
            try:
                resp = requests.post(API_URL, json=payload, headers=HEADERS, timeout=30)
                elapsed = time.time() - t0
                turn_times.append(elapsed)
                total_time += elapsed
                total_calls += 1
                
                if resp.status_code != 200:
                    print(f"  Turn {turn_num+1}: ❌ HTTP {resp.status_code} ({elapsed:.1f}s)")
                    errors += 1
                    total_errors += 1
                    continue
                
                data = resp.json()
                last_response = data
                
                # Add to history for next turn
                history.append({"sender": "scammer", "text": scammer_msg})
                agent_reply = data.get('reply', '')
                history.append({"sender": "agent", "text": agent_reply})
                
                # Quick status
                detected = "✅" if data.get('scamDetected') else "❌"
                intel_count = sum(len(v) for v in data.get('extractedIntelligence', {}).values())
                print(f"  Turn {turn_num+1}: {detected} det | {intel_count} intel | {elapsed:.1f}s | {agent_reply[:60]}...")
                
            except requests.exceptions.Timeout:
                elapsed = time.time() - t0
                print(f"  Turn {turn_num+1}: ⏱️ TIMEOUT ({elapsed:.1f}s)")
                total_timeouts += 1
                total_calls += 1
                errors += 1
            except Exception as e:
                elapsed = time.time() - t0
                print(f"  Turn {turn_num+1}: 💥 ERROR: {e} ({elapsed:.1f}s)")
                errors += 1
                total_errors += 1
                total_calls += 1
        
        # Scenario summary
        avg_time = sum(turn_times) / len(turn_times) if turn_times else 0
        max_time = max(turn_times) if turn_times else 0
        
        # Check intelligence extraction
        intel_result = {"phones": 0, "banks": 0, "upis": 0, "links": 0, "emails": 0}
        if last_response:
            ei = last_response.get('extractedIntelligence', {})
            intel_result = {
                "phones": len(ei.get('phoneNumbers', [])),
                "banks": len(ei.get('bankAccounts', [])),
                "upis": len(ei.get('upiIds', [])),
                "links": len(ei.get('phishingLinks', [])),
                "emails": len(ei.get('emailAddresses', []))
            }
        
        expected = scenario['expected_intel']
        
        # Score calculation
        fields_present = 0
        if last_response:
            for f in ['status', 'scamDetected', 'extractedIntelligence', 'engagementMetrics', 'agentNotes']:
                if f in last_response:
                    fields_present += 1
        
        result = {
            "name": scenario['name'],
            "avg_time": avg_time,
            "max_time": max_time,
            "errors": errors,
            "detected": last_response.get('scamDetected', False) if last_response else False,
            "intel": intel_result,
            "expected": {k: len(v) for k, v in expected.items()},
            "fields": fields_present,
            "messages": last_response.get('engagementMetrics', {}).get('totalMessagesExchanged', 0) if last_response else 0,
            "duration": last_response.get('engagementMetrics', {}).get('engagementDurationSeconds', 0) if last_response else 0
        }
        scenario_results.append(result)
        
        print(f"\n  📊 Summary: avg={avg_time:.1f}s, max={max_time:.1f}s, errors={errors}")
        print(f"  📱 Intel: phones={intel_result['phones']}/{len(expected['phones'])}, banks={intel_result['banks']}/{len(expected['banks'])}, upis={intel_result['upis']}/{len(expected['upis'])}, links={intel_result['links']}/{len(expected['links'])}, emails={intel_result['emails']}/{len(expected['emails'])}")
        print(f"  📋 Fields: {fields_present}/5, Messages: {result['messages']}, Duration: {result['duration']}s")
    
    # Final report
    print("\n" + "=" * 80)
    print("FINAL STRESS TEST REPORT")
    print("=" * 80)
    
    print(f"\n📊 Overall Stats:")
    print(f"  Total API calls: {total_calls}")
    print(f"  Total time: {total_time:.1f}s ({total_time/60:.1f} min)")
    print(f"  Avg per turn: {total_time/total_calls:.1f}s" if total_calls > 0 else "  No successful calls")
    print(f"  Errors: {total_errors}")
    print(f"  Timeouts: {total_timeouts}")
    
    print(f"\n{'Scenario':<20} {'Det':>4} {'Time':>6} {'Ph':>4} {'Bk':>4} {'UPI':>4} {'Lnk':>4} {'Em':>4} {'Flds':>5} {'Msgs':>5}")
    print("─" * 75)
    
    total_detection = 0
    total_intel_score = 0
    total_structure = 0
    total_engagement = 0
    
    for r in scenario_results:
        det_emoji = "✅" if r['detected'] else "❌"
        total_detection += 20 if r['detected'] else 0
        
        # Intel score (out of 40)
        intel_score = 0
        for cat, expected_count in r['expected'].items():
            actual = r['intel'].get(cat, 0)
            if expected_count > 0:
                intel_score += min(1.0, actual / expected_count) * 8  # 8 pts per category (5 categories × 8 = 40)
        total_intel_score += intel_score
        
        # Engagement (out of 20)
        eng_score = 0
        if r['duration'] > 0: eng_score += 5
        if r['duration'] > 60: eng_score += 5
        if r['messages'] > 0: eng_score += 5
        if r['messages'] >= 5: eng_score += 5
        total_engagement += eng_score
        
        # Structure (out of 20)
        struct_score = r['fields'] * 4
        total_structure += struct_score
        
        print(f"  {r['name']:<18} {det_emoji:>4} {r['avg_time']:>5.1f}s {r['intel']['phones']:>3}/{r['expected']['phones']} {r['intel']['banks']:>3}/{r['expected']['banks']} {r['intel']['upis']:>3}/{r['expected']['upis']} {r['intel']['links']:>3}/{r['expected']['links']} {r['intel']['emails']:>3}/{r['expected']['emails']} {r['fields']:>4}/5 {r['messages']:>5}")
    
    n = len(scenario_results)
    print(f"\n📈 Estimated Score (out of 100):")
    print(f"  Scam Detection:       {total_detection/n:.0f}/20")
    print(f"  Intelligence Extract: {total_intel_score/n:.1f}/40")
    print(f"  Engagement Quality:   {total_engagement/n:.0f}/20")
    print(f"  Response Structure:   {total_structure/n:.0f}/20")
    print(f"  ─────────────────────────")
    estimated = (total_detection + total_intel_score + total_engagement + total_structure) / n
    print(f"  ESTIMATED TOTAL:      {estimated:.1f}/100")
    
    # Check under 30s requirement
    over_30 = sum(1 for r in scenario_results if r['max_time'] > 30)
    print(f"\n⏱️ Latency Check: {over_30} scenarios had turns exceeding 30s timeout")


if __name__ == "__main__":
    run_stress_test()
