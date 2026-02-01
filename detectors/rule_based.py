import re
from typing import Dict

class RuleBasedDetector:
    """Enhanced pattern-based scam classifier with broader coverage"""
    
    def __init__(self):
        # Compile all patterns for faster matching
        
        # === SCAM PATTERNS ===
        
        # Pattern 1: Requesting sensitive information (BROADER)
        self.sensitive_info_patterns = [
            r'\b(share|give|provide|send|tell|confirm|verify|validate)\b.{0,40}\b(otp|cvv|pin|password)\b',
            r'\b(otp|cvv|pin|password)\b.{0,40}\b(share|give|provide|send)\b',
            r'\b(bank account|account number|card number|card details|credit card|debit card)\b',
            r'\b(login details|login credentials|personal details|personal information)\b',
            r'\bidentity (number|card|verification)\b',
            r'\b(aadhaar|aadhar|pan card|pan number|social security)\b',
            r'\bpin number\b',
            r'\byour (full name|complete name).{0,30}(identity|id)\b',
            r'\bverify your (details|information|particulars)\b',
            r'\bconfirm your.{0,30}(name|identity|details)\b',
        ]
        
        # Pattern 2: Prize/Lottery  
        self.prize_patterns = [
            r'\b(you have won|you won|you\'ve won|you are the winner)\b',
            r'\b(congratulations).{0,60}(won|prize|reward|gift|selected|winner|lottery)\b',
            r'\b(lottery|jackpot|lucky draw|sweepstake)\b',
            r'\b(claim your|claim the).{0,30}(prize|reward|gift|money|winnings)\b',
            r'\bwinner.{0,40}(selected|chosen|lucky)\b',
            r'\b(free|win).{0,20}(gift|iphone|laptop|car|vacation|trip|package)\b',
            r'\blucky one.{0,20}selected\b',
            r'\bsubstantial reward\b',
            r'\bexotic destination\b',
        ]
        
        # Pattern 3: Payment demands
        self.payment_demand_patterns = [
            r'\b(transfer|pay|send|deposit).{0,40}(bank account|account)\b',
            r'\btransfer.{0,20}(payment|money|funds|amount)\b',
            r'\b(processing fee|registration fee|advance payment|upfront fee|upfront payment)\b',
            r'\bpay.{0,20}(fee|immediately|now|first)\b',
            r'\bbank account \[?number\]?\b',
            r'\b(security|refundable) deposit\b',
            r'\bdeposit of \[?money\]?\b',
            r'\bwe (need|require).{0,30}payment\b',
            r'\bmake a (payment|transfer|deposit)\b',
            r'\bprovide.{0,20}payment\b',
        ]
        
        # Pattern 4: Threats/Urgency
        self.threat_patterns = [
            r'\b(account|card|service).{0,30}(blocked|suspended|terminated|frozen|seized|disconnected)\b',
            r'\b(arrested|arrest warrant|legal action|court case|police case)\b',
            r'\b(criminal|jail|imprisoned|prosecution|blacklisted|bankruptcy)\b',
            r'\bkidnapped\b',
            r'\b(unless you|or else|otherwise|fail to).{0,30}(pay|transfer)\b',
            r'\bsuspicious activity\b',
            r'\bsecurity (breach|issue|problem)\b',
            r'\bmoney laundering\b',
            r'\boverdue.{0,20}(payment|bill)\b',
            r'\bimmediate (payment|action)\b',
            r'\bavoid.{0,30}(arrest|disconnection|blacklist|being)\b',
        ]
        
        # Pattern 5: Authority impersonation
        self.authority_scam_patterns = [
            r'\b(calling from|this is).{0,40}(rbi|reserve bank|income tax|police|government)\b',
            r'\bpolice (department|headquarters|station|officer)\b',
            r'\bgovernment (grant|scheme|department|agency)\b',
            r'\b(enforcement directorate|cyber cell|crime branch|cbi)\b',
            r'\b(inspector|officer|commissioner|sergeant)\b.{0,20}(police|department)\b',
            r'\bon behalf of\b.{0,30}(government|police|bank|authority)\b',
            r'\bunder the \[?law\]?\b',
        ]
        
        # Pattern 6: Security/Verification scam
        self.security_scam_patterns = [
            r'\b(account|card|computer|system|device).{0,30}(compromised|hacked|breach|issue)\b',
            r'\bhas been (compromised|hacked|frozen|blocked)\b',
            r'\b(verify|validate).{0,30}(account|identity|information|details)\b',
            r'\bsecurity (purposes|protocol|measure|verification)\b',
            r'\breactivation\b',
            r'\bdownload.{0,30}(apk|file|app)\b',
            r'\baccess to your (device|computer|account)\b',
        ]
        
        # Pattern 7: Job/Investment/Recruitment scam (EXPANDED)
        self.job_scam_patterns = [
            r'\b(work from home|part time|online).{0,30}(job|earn|income|position)\b',
            r'\b(guaranteed returns|double your money|high returns|profit twice)\b',
            r'\b(invest|investment).{0,40}(opportunity|profit|returns)\b',
            r'\bjob (opportunity|abroad|offer).{0,50}(fee|payment|deposit)\b',
            r'\bvisa processing\b',
            r'\bapproved loan\b',
            r'\bonce.?in.?a.?lifetime\b',
            # Recruitment scams
            r'\bcame across your profile\b',
            r'\bfollowing your profile\b',
            r'\byour profile caught\b',
            r'\bwe are (looking for|hiring|on the lookout)\b',
            r'\b(earn|making|earning).{0,30}\[?money\]?\b',
            r'\b(earn up to|earning).{0,20}per (hour|week|month)\b',
            r'\bearn commissions?\b',
            r'\b(what is your|share your).{0,20}(age|occupation)\b',
            r'\bsend.{0,30}(resume|cv).{0,30}(phone|bank|account)\b',
            r'\b(resume|cv).{0,30}(phone number|bank account)\b',
            r'\bpurchasing products (upfront|in advance)\b',
            r'\baffiliate marketing\b.{0,40}(commission|earn)\b',
            r'\bboost(ing)? sales\b',
            r'\bassistant purchasers?\b',
            r'\bstock takers?\b',
            r'\bsystem trial\b',
            r'\bexciting opportunity\b',
            r'\bgame.?changer\b',
            r'\blife.?changing\b',
            r'\btoo good to be true\b',
            # MLM patterns
            r'\bI have been (doing this|in this|part of this|with this)\b',
            r'\bjoin me in this\b',
            r'\bI am (making|earning|pulling in)\b.{0,30}\[?money\]?\b',
        ]
        
        # Pattern 8: Generic scam signals
        self.generic_scam_patterns = [
            r'\bwe (need|require) your.{0,30}(details|information|cooperation)\b',
            r'\bsend.{0,20}(resume|cv).{0,30}(bank|account|payment)\b',
            r'\bcharitable (cause|organization|donation)\b.{0,40}(donate|transfer|bank)\b',
            r'\belectricity (bill|supply|disconnection)\b',
            r'\bemergency.{0,40}(money|send|transfer|help)\b',
            r'\bpackage.{0,40}(credit card|identity card|id card)\b',
            r'\bshipment.{0,30}(credit|identity)\b',
            r'\bexclusive (upgrade|offer|deal)\b.{0,40}(payment|account)\b',
        ]
        
        # === LEGITIMATE PATTERNS ===
        self.appointment_patterns = [
            r'\b(appointment|check-?up|session|meeting|visit).{0,40}(scheduled|confirmed|on|at|for)\b',
            r'\b(reminder|reminding).{0,40}(appointment|meeting|session)\b',
            r'\breschedule your\b',
        ]
        
        self.delivery_patterns = [
            r'\b(order|package|parcel|shipment).{0,40}(shipped|delivered|dispatched|arrived|ready)\b',
            r'\bout for delivery\b',
            r'\btracking (number|id|details)\b',
            r'\bpickup (ready|available)\b',
        ]
        
        self.professional_patterns = [
            r'\bthank you for (applying|your application|your order|your business)\b',
            r'\b(interview|onboarding).{0,30}(scheduled|on)\b',
            r'\brsvp\b',
            r'\bscheduled maintenance\b',
            r'\bsoftware update.{0,30}available\b',
        ]

    def _count_pattern_matches(self, text: str, patterns: list) -> int:
        count = 0
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                count += 1
        return count

    def analyze(self, text: str) -> Dict:
        """Classify message with broader scam detection"""
        
        # Count scam pattern matches
        sensitive_info = self._count_pattern_matches(text, self.sensitive_info_patterns)
        prize_claim = self._count_pattern_matches(text, self.prize_patterns)
        payment_demand = self._count_pattern_matches(text, self.payment_demand_patterns)
        threats = self._count_pattern_matches(text, self.threat_patterns)
        authority_scam = self._count_pattern_matches(text, self.authority_scam_patterns)
        security_scam = self._count_pattern_matches(text, self.security_scam_patterns)
        job_scam = self._count_pattern_matches(text, self.job_scam_patterns)
        generic_scam = self._count_pattern_matches(text, self.generic_scam_patterns)
        
        # Count legitimate pattern matches
        appointment = self._count_pattern_matches(text, self.appointment_patterns)
        delivery = self._count_pattern_matches(text, self.delivery_patterns)
        professional = self._count_pattern_matches(text, self.professional_patterns)
        
        # Calculate scam score
        scam_score = 0
        
        # Strong indicators
        if sensitive_info > 0:
            scam_score += 25 + (sensitive_info * 8)
        if prize_claim > 0:
            scam_score += 25 + (prize_claim * 8)
        if payment_demand > 0:
            scam_score += 25 + (payment_demand * 8)
        if threats > 0:
            scam_score += 20 + (threats * 6)
        if authority_scam > 0:
            scam_score += 20 + (authority_scam * 6)
        if security_scam > 0:
            scam_score += 18 + (security_scam * 5)
        if job_scam > 0:
            scam_score += 18 + (job_scam * 5)
        if generic_scam > 0:
            scam_score += 15 + (generic_scam * 5)
        
        # Combination bonus
        scam_categories = sum([
            1 if sensitive_info > 0 else 0,
            1 if prize_claim > 0 else 0,
            1 if payment_demand > 0 else 0,
            1 if threats > 0 else 0,
            1 if authority_scam > 0 else 0,
            1 if security_scam > 0 else 0,
            1 if job_scam > 0 else 0,
            1 if generic_scam > 0 else 0,
        ])
        
        if scam_categories >= 3:
            scam_score *= 1.3
        elif scam_categories >= 2:
            scam_score *= 1.15
        
        # Legitimate indicators
        legit_score = 0
        if appointment > 0:
            legit_score += 25 + (appointment * 10)
        if delivery > 0:
            legit_score += 25 + (delivery * 10)
        if professional > 0:
            legit_score += 20 + (professional * 8)
        
        # Apply legitimate penalty
        if legit_score > 0 and scam_categories == 0:
            scam_score -= legit_score * 2
        elif legit_score > 0:
            scam_score -= legit_score * 0.3
        
        flags = {
            "sensitive_info_request": sensitive_info > 0,
            "prize_claim": prize_claim > 0,
            "payment_demand": payment_demand > 0,
            "threat_language": threats > 0,
            "authority_impersonation": authority_scam > 0,
            "security_scam": security_scam > 0,
            "job_scam": job_scam > 0,
            "generic_scam": generic_scam > 0,
            "legitimate_appointment": appointment > 0,
            "legitimate_delivery": delivery > 0,
            "legitimate_professional": professional > 0,
        }
        
        return {
            "rule_score": max(0.0, min(100.0, scam_score)),
            "flags": flags,
            "scam_categories": scam_categories,
            "legitimate_score": legit_score,
            "flag_count": scam_categories
        }