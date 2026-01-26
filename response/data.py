TEMPLATES = [
    {
        "id": "confused_bank_1", "strategy": "show_concern_and_confusion", "phase": ["Initial Contact"],
        "text": "Hello? I received this message about {bank_name}... I don't understand what is happening. Is my money safe?"
    },
    {
        "id": "ask_upi_1", "strategy": "extract_payment_details", "phase": ["Active Extraction"],
        "text": "I am trying to send the money but the app is asking for a specific UPI ID. Which one should I use?"
    },
    {
        "id": "stall_tech_issue", "strategy": "stall_for_engagement", "phase": ["Active Extraction"],
        "text": "Wait wait, my internet is very slow. It is loading... please hold on one minute."
    }
]