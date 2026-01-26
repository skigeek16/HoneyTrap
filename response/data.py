TEMPLATES = [
    # ==================== INITIAL CONTACT PHASE ====================
    {
        "id": "confused_bank_1", "strategy": "show_concern_and_confusion", "phase": ["Initial Contact"],
        "intent": ["requesting_payment", "threatening"],
        "text": "Hello? I received this message about my bank... I don't understand what is happening. Is my money safe?"
    },
    {
        "id": "confused_general_1", "strategy": "show_concern_and_confusion", "phase": ["Initial Contact"],
        "intent": ["threatening", "impersonating_authority"],
        "text": "What is this? Who is this? I am getting very worried now. Please explain properly."
    },
    {
        "id": "curious_prize_1", "strategy": "show_interest", "phase": ["Initial Contact"],
        "intent": ["offering_prize"],
        "text": "Really? I won something? But I don't remember entering any contest. How is this possible?"
    },
    {
        "id": "cautious_verify_1", "strategy": "verify_legitimacy", "phase": ["Initial Contact"],
        "intent": ["job_offer", "offering_prize"],
        "text": "This sounds interesting but how do I know this is real? Can you provide some verification?"
    },
    {
        "id": "elderly_confused_1", "strategy": "show_tech_confusion", "phase": ["Initial Contact"],
        "intent": ["phishing_attempt", "requesting_payment"],
        "text": "I don't understand these technical things. My son usually helps me. Can you explain simply?"
    },
    {
        "id": "authority_fear_1", "strategy": "show_fear", "phase": ["Initial Contact"],
        "intent": ["impersonating_authority", "threatening"],
        "text": "Oh my god! Is this really from the government? I have always paid my taxes properly. What happened?"
    },
    
    # ==================== BUILDING RAPPORT PHASE ====================
    {
        "id": "trust_building_1", "strategy": "build_trust", "phase": ["Building Rapport"],
        "intent": ["requesting_payment", "threatening"],
        "text": "Okay okay, I believe you. Just tell me what I need to do. I don't want any problem."
    },
    {
        "id": "personal_share_1", "strategy": "share_personal_info", "phase": ["Building Rapport"],
        "intent": ["job_offer", "offering_prize"],
        "text": "Actually I am retired now. My pension is my only income. This prize would really help me."
    },
    {
        "id": "concern_family_1", "strategy": "show_family_concern", "phase": ["Building Rapport"],
        "intent": ["threatening", "impersonating_authority"],
        "text": "Please don't tell my family about this. They will get very worried. I will do whatever you say."
    },
    {
        "id": "eager_help_1", "strategy": "show_eagerness", "phase": ["Building Rapport"],
        "intent": ["requesting_payment", "offering_prize"],
        "text": "Yes yes, I want to complete this quickly. What details do you need from me?"
    },
    {
        "id": "cooperative_1", "strategy": "show_cooperation", "phase": ["Building Rapport"],
        "intent": ["job_offer", "phishing_attempt"],
        "text": "I am ready to cooperate fully. Just guide me step by step please."
    },
    
    # ==================== ACTIVE EXTRACTION PHASE ====================
    {
        "id": "ask_upi_1", "strategy": "extract_payment_details", "phase": ["Active Extraction"],
        "intent": ["requesting_payment"],
        "text": "I am trying to send the money but the app is asking for a specific UPI ID. Which one should I use?"
    },
    {
        "id": "ask_account_1", "strategy": "extract_bank_details", "phase": ["Active Extraction"],
        "intent": ["requesting_payment", "threatening"],
        "text": "Should I transfer to your bank account directly? Please share the account number and IFSC code."
    },
    {
        "id": "ask_link_1", "strategy": "extract_phishing_link", "phase": ["Active Extraction"],
        "intent": ["phishing_attempt"],
        "text": "Okay I will click the link. Can you send it again? My phone didn't show it properly."
    },
    {
        "id": "confirm_details_1", "strategy": "confirm_extraction", "phase": ["Active Extraction"],
        "intent": ["requesting_payment"],
        "text": "Let me confirm - I should send money to this UPI ID you mentioned? Please share it once more clearly."
    },
    {
        "id": "ask_amount_1", "strategy": "clarify_amount", "phase": ["Active Extraction"],
        "intent": ["requesting_payment", "offering_prize"],
        "text": "How much exactly do I need to pay? I want to make sure I send the correct amount."
    },
    {
        "id": "payment_method_1", "strategy": "ask_payment_method", "phase": ["Active Extraction"],
        "intent": ["requesting_payment"],
        "text": "I can pay through UPI or bank transfer. Which one is better? Share the details please."
    },
    {
        "id": "ask_phone_1", "strategy": "extract_contact", "phase": ["Active Extraction"],
        "intent": ["job_offer", "offering_prize"],
        "text": "Can I call you to discuss this? Please share your phone number for my records."
    },
    
    # ==================== STALLING TACTICS ====================
    {
        "id": "stall_tech_issue", "strategy": "stall_for_engagement", "phase": ["Active Extraction", "Building Rapport"],
        "intent": ["requesting_payment", "threatening"],
        "text": "Wait wait, my internet is very slow. It is loading... please hold on one minute."
    },
    {
        "id": "stall_otp_1", "strategy": "stall_otp_issue", "phase": ["Active Extraction"],
        "intent": ["phishing_attempt", "requesting_payment"],
        "text": "OTP is not coming on my phone. Network issue maybe. Can you wait 2-3 minutes?"
    },
    {
        "id": "stall_bank_1", "strategy": "stall_bank_issue", "phase": ["Active Extraction"],
        "intent": ["requesting_payment"],
        "text": "My banking app is showing some error. Let me try again. Please don't disconnect."
    },
    {
        "id": "stall_family_1", "strategy": "stall_family_excuse", "phase": ["Active Extraction", "Building Rapport"],
        "intent": ["requesting_payment", "threatening"],
        "text": "Someone is at the door. Give me 5 minutes, I will come back and complete this."
    },
    {
        "id": "stall_money_1", "strategy": "stall_insufficient_funds", "phase": ["Active Extraction"],
        "intent": ["requesting_payment"],
        "text": "I don't have this much money in this account. Can I transfer in two parts? First part now?"
    },
    {
        "id": "stall_glasses_1", "strategy": "stall_vision_issue", "phase": ["Active Extraction"],
        "intent": ["phishing_attempt", "requesting_payment"],
        "text": "Let me find my reading glasses. I cannot see the small text clearly on phone."
    },
    
    # ==================== VERIFICATION REQUESTS ====================
    {
        "id": "verify_org_1", "strategy": "verify_organization", "phase": ["Building Rapport", "Active Extraction"],
        "intent": ["impersonating_authority", "job_offer"],
        "text": "Which organization are you calling from exactly? I want to note it down for my records."
    },
    {
        "id": "verify_id_1", "strategy": "verify_identity", "phase": ["Building Rapport"],
        "intent": ["impersonating_authority", "threatening"],
        "text": "Can you share your employee ID or badge number? I need to verify before proceeding."
    },
    {
        "id": "verify_case_1", "strategy": "verify_case_number", "phase": ["Building Rapport", "Active Extraction"],
        "intent": ["threatening", "impersonating_authority"],
        "text": "What is the case number or reference number for this? I should have it for documentation."
    },
    
    # ==================== EMOTIONAL RESPONSES ====================
    {
        "id": "scared_comply_1", "strategy": "show_fear_compliance", "phase": ["Building Rapport", "Active Extraction"],
        "intent": ["threatening", "impersonating_authority"],
        "text": "Please don't arrest me! I will pay immediately. Just tell me where to send the money."
    },
    {
        "id": "grateful_1", "strategy": "show_gratitude", "phase": ["Building Rapport"],
        "intent": ["offering_prize", "job_offer"],
        "text": "Thank you so much for choosing me! This will really help my family. What do I do next?"
    },
    {
        "id": "apologetic_1", "strategy": "show_apology", "phase": ["Building Rapport", "Active Extraction"],
        "intent": ["threatening", "impersonating_authority"],
        "text": "I am so sorry if I did anything wrong. I am old and don't understand these things. Please help me."
    },
    
    # ==================== FALLBACK / GENERIC ====================
    {
        "id": "generic_continue_1", "strategy": "generic_engagement", "phase": ["Initial Contact", "Building Rapport", "Active Extraction"],
        "intent": ["innocent_conversation"],
        "text": "I see. Please tell me more about this. I want to understand completely."
    },
    {
        "id": "generic_clarify_1", "strategy": "generic_clarification", "phase": ["Initial Contact", "Building Rapport"],
        "intent": ["innocent_conversation", "phishing_attempt"],
        "text": "Can you explain this again? I didn't fully understand what you are saying."
    },
    {
        "id": "generic_agree_1", "strategy": "generic_agreement", "phase": ["Building Rapport", "Active Extraction"],
        "intent": ["requesting_payment", "job_offer", "offering_prize"],
        "text": "Okay, I understand now. Please proceed and tell me what to do next."
    }
]

# Strategy mappings for intelligent template selection
STRATEGY_BY_PHASE = {
    "Initial Contact": ["show_concern_and_confusion", "show_interest", "verify_legitimacy", "show_tech_confusion", "show_fear"],
    "Building Rapport": ["build_trust", "share_personal_info", "show_family_concern", "show_eagerness", "show_cooperation", "verify_organization"],
    "Active Extraction": ["extract_payment_details", "extract_bank_details", "extract_phishing_link", "confirm_extraction", "stall_for_engagement"]
}

# Intelligence gap to strategy mapping
EXTRACTION_STRATEGIES = {
    "PAYMENT_DETAILS": ["extract_payment_details", "extract_bank_details", "ask_payment_method", "clarify_amount"],
    "CONTACT_INFO": ["extract_contact", "verify_organization", "verify_identity"],
    "PHISHING_LINK": ["extract_phishing_link", "generic_clarification"]
}