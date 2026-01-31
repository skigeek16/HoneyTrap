import re
from typing import Dict, Tuple

class RuleBasedDetector:
    """Pattern-based scam classifier focusing on scam behavior patterns, not just keywords"""
    
    def __init__(self):
        # === SCAM PATTERNS (what scammers DO) ===
        
        # Pattern 1: Requesting sensitive information
        self.sensitive_info_patterns = [
            r'\b(share|give|provide|send|tell)\b.{0,30}\b(otp|cvv|pin|password)\b',
            r'\b(otp|cvv|pin|password)\b.{0,30}\b(share|give|provide|send)\b',
            r'\b(bank account|account number|card number|card details|credit card|debit card)\b',
            r'\b(login details|login credentials|personal details|identity number)\b',
            r'\b(aadhaar|aadhar|pan card|pan number)\b',
            r'\bpin number\b',
        ]
        
        # Pattern 2: Unsolicited prize/lottery claims  
        self.prize_patterns = [
            r'\b(you have won|you won|you\'ve won)\b',
            r'\b(congratulations).{0,50}(won|prize|reward|gift|selected)\b',
            r'\b(lottery|jackpot|lucky draw|sweepstake)\b',
            r'\b(claim your|claim the).{0,20}(prize|reward|gift|money)\b',
            r'\bwinner\b.{0,30}\b(selected|chosen|lucky)\b',
            r'\bfree\s+(gift|iphone|laptop|car|vacation)\b',
        ]
        
        # Pattern 3: Payment demands with urgency/threats
        self.payment_demand_patterns = [
            r'\b(transfer|pay|send|deposit).{0,30}(immediately|urgent|now|today|asap)\b',
            r'\b(immediately|urgent|now).{0,30}(transfer|pay|send|deposit)\b',
            r'\b(processing fee|registration fee|advance payment|upfront payment)\b',
            r'\btransfer the payment to\b',
            r'\bpay a (small |)fee\b',
            r'\b(taxes upfront|customs fee|visa processing|transportation fee)\b',
        ]
        
        # Pattern 4: Threat/Scare tactics
        self.threat_patterns = [
            r'\b(account|card).{0,20}(blocked|suspended|terminated|frozen|seized)\b',
            r'\b(arrested|arrest warrant|legal action|court case|fir|police case)\b',
            r'\b(criminal|jail|imprisoned|prosecution)\b',
            r'\bkidnapped\b',
            r'\b(unless you pay|or else|otherwise)\b',
            r'\bfail to.{0,30}(pay|transfer)\b',
        ]
        
        # Pattern 5: Authority impersonation with demands
        self.authority_scam_patterns = [
            r'\b(calling from|this is).{0,30}(rbi|reserve bank|income tax|cbi|police|government)\b',
            r'\bgovernment (grant|scheme|lottery)\b',
            r'\b(enforcement directorate|cyber cell|crime branch)\b',
        ]
        
        # Pattern 6: Compromise/Security scam
        self.security_scam_patterns = [
            r'\b(account|card|computer|system).{0,20}(compromised|hacked|breach)\b',
            r'\bhas been compromised\b',
            r'\bsocial security.{0,20}(compromised|suspended|blocked)\b',
        ]
        
        # Pattern 7: Job/Investment scam
        self.job_scam_patterns = [
            r'\b(work from home|part time|data entry).{0,30}(job|earn|income)\b',
            r'\b(guaranteed returns|double your money|high returns)\b',
            r'\b(invest|investment).{0,30}(opportunity|profit|returns)\b',
            r'\bjob (opportunity|abroad)\b.{0,50}\b(fee|payment|deposit)\b',
        ]
        
        # === LEGITIMATE PATTERNS (what real businesses say) ===
        
        # Appointment/Scheduling
        self.appointment_patterns = [
            r'\b(appointment|check-?up|session|meeting|visit).{0,30}(scheduled|confirmed|on|at)\b',
            r'\b(reminder|reminding).{0,30}(appointment|meeting|session)\b',
            r'\breschedule your\b',
        ]
        
        # Order/Delivery
        self.delivery_patterns = [
            r'\b(order|package|parcel|shipment).{0,30}(shipped|delivered|dispatched|arrived)\b',
            r'\bout for delivery\b',
            r'\btracking (number|id|details)\b',
            r'\bpickup (ready|available)\b',
        ]
        
        # Professional/Business
        self.professional_patterns = [
            r'\bthank you for (applying|your application|your order)\b',
            r'\b(interview|onboarding).{0,20}(scheduled|on)\b',
            r'\brsvp\b',
            r'\bpre-?order.{0,20}(ready|available)\b',
            r'\b(renewal|subscription|membership).{0,20}(due|reminder)\b',
            r'\bscheduled maintenance\b',
        ]
        
        # Service notifications (without demands)
        self.service_patterns = [
            r'\blab (results|test|report)\b',
            r'\bprescription.{0,20}(refill|ready|due)\b',
            r'\bsoftware update\b.{0,20}\b(available|pending)\b',
        ]

    def _count_pattern_matches(self, text: str, patterns: list) -> int:
        """Count how many patterns match in text"""
        count = 0
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                count += 1
        return count

    def _has_pattern_match(self, text: str, patterns: list) -> bool:
        """Check if any pattern matches"""
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False

    def analyze(self, text: str) -> Dict:
        """Classify message based on scam vs legitimate patterns"""
        text_lower = text.lower()
        
        # Count scam pattern matches
        sensitive_info = self._count_pattern_matches(text, self.sensitive_info_patterns)
        prize_claim = self._count_pattern_matches(text, self.prize_patterns)
        payment_demand = self._count_pattern_matches(text, self.payment_demand_patterns)
        threats = self._count_pattern_matches(text, self.threat_patterns)
        authority_scam = self._count_pattern_matches(text, self.authority_scam_patterns)
        security_scam = self._count_pattern_matches(text, self.security_scam_patterns)
        job_scam = self._count_pattern_matches(text, self.job_scam_patterns)
        
        # Count legitimate pattern matches
        appointment = self._count_pattern_matches(text, self.appointment_patterns)
        delivery = self._count_pattern_matches(text, self.delivery_patterns)
        professional = self._count_pattern_matches(text, self.professional_patterns)
        service = self._count_pattern_matches(text, self.service_patterns)
        
        # Calculate scam score based on pattern combinations
        scam_score = 0
        
        # Strong scam indicators (high points)
        if sensitive_info > 0:
            scam_score += 35 + (sensitive_info * 10)
        if prize_claim > 0:
            scam_score += 30 + (prize_claim * 8)
        if payment_demand > 0:
            scam_score += 30 + (payment_demand * 8)
        if threats > 0:
            scam_score += 25 + (threats * 8)
        if authority_scam > 0:
            scam_score += 25 + (authority_scam * 8)
        if security_scam > 0:
            scam_score += 25 + (security_scam * 8)
        if job_scam > 0:
            scam_score += 25 + (job_scam * 8)
        
        # Combination bonuses (multiple scam patterns = very likely scam)
        scam_categories = sum([
            1 if sensitive_info > 0 else 0,
            1 if prize_claim > 0 else 0,
            1 if payment_demand > 0 else 0,
            1 if threats > 0 else 0,
            1 if authority_scam > 0 else 0,
            1 if security_scam > 0 else 0,
            1 if job_scam > 0 else 0,
        ])
        
        if scam_categories >= 3:
            scam_score *= 1.4
        elif scam_categories >= 2:
            scam_score *= 1.2
        
        # Legitimate score
        legit_score = 0
        if appointment > 0:
            legit_score += 25 + (appointment * 10)
        if delivery > 0:
            legit_score += 25 + (delivery * 10)
        if professional > 0:
            legit_score += 20 + (professional * 8)
        if service > 0:
            legit_score += 20 + (service * 8)
        
        # If message has legitimate patterns but NO scam patterns, heavily reduce score
        if legit_score > 0 and scam_categories == 0:
            scam_score -= legit_score * 2
        # If message has both, reduce score moderately
        elif legit_score > 0 and scam_categories > 0:
            scam_score -= legit_score * 0.5
        
        # Build flags for debugging
        flags = {
            "sensitive_info_request": sensitive_info > 0,
            "prize_claim": prize_claim > 0,
            "payment_demand": payment_demand > 0,
            "threat_language": threats > 0,
            "authority_impersonation": authority_scam > 0,
            "security_scam": security_scam > 0,
            "job_scam": job_scam > 0,
            "legitimate_appointment": appointment > 0,
            "legitimate_delivery": delivery > 0,
            "legitimate_professional": professional > 0,
            "legitimate_service": service > 0,
        }
        
        return {
            "rule_score": max(0.0, min(100.0, scam_score)),
            "flags": flags,
            "scam_categories": scam_categories,
            "legitimate_score": legit_score,
            "flag_count": scam_categories
        }