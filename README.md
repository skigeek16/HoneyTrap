---
title: HoneyTrap API
emoji: 🍯
colorFrom: yellow
colorTo: red
sdk: docker
app_port: 7860
pinned: false
---

# 🍯 HoneyTrap — Agentic AI Honeypot for Scam Detection & Intelligence Extraction

An autonomous AI-powered honeypot system that detects scam messages, engages scammers using believable personas, and extracts actionable intelligence (phone numbers, bank accounts, UPI IDs, phishing links, emails) — all in real-time.

## Description

HoneyTrap is an agentic honeypot API built for the GUVI Hackathon. When a scammer sends a message, HoneyTrap:

1. **Detects the scam** using a triple-layer detection engine
2. **Selects a believable persona** to impersonate a potential victim
3. **Extracts intelligence** (UPI IDs, phone numbers, bank accounts, links, emails)
4. **Generates contextual responses** that stall the scammer while extracting more information
5. **Reports findings** in a structured evaluation-compatible format

## Tech Stack

- **Framework:** FastAPI + Uvicorn
- **Language:** Python 3.11
- **LLM:** Llama 3.3 70B Instruct (via Nebius Token Factory API)
- **ML Models:** HuggingFace Transformers (phishing detection + zero-shot classification)
- **Regex Engine:** 300+ India-specific scam patterns (KYC, UPI, bank, threat, prize, etc.)
- **Deployment:** Docker on Google Cloud Run (asia-south1)

## Architecture

```
Incoming Message
       ↓
┌──────────────────────────────────────────────┐
│  Stage 1: Triple-Layer Scam Detection        │
│  ├── Rule-Based Detector (50% weight)        │
│  │   └── 300+ regex patterns, 13 categories  │
│  ├── ML Ensemble (20% weight)                │
│  │   ├── Phishing classifier                 │
│  │   └── Zero-shot intent recognition        │
│  └── LLM Classifier (30% weight)             │
│      └── Llama 3.3 70B structured analysis   │
├──────────────────────────────────────────────┤
│  Stage 2: Persona Selection                  │
│  └── 5 victim personas matched to scam type  │
├──────────────────────────────────────────────┤
│  Stage 3: Intelligence Extraction            │
│  └── Regex: Phone, UPI, Bank, URL, Email,    │
│      PAN, Aadhaar, IFSC, Crypto              │
├──────────────────────────────────────────────┤
│  Stage 4: Response Generation                │
│  └── LLM contextual response with            │
│      extraction-focused prompting            │
└──────────────────────────────────────────────┘
       ↓
  Structured JSON Response
```

## Setup Instructions

### 1. Clone the Repository
```bash
git clone https://github.com/YOUR_USERNAME/Honeypot.git
cd Honeypot/HoneyTrap
```

### 2. Install Dependencies
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Set Environment Variables
```bash
cp .env.example .env
# Edit .env with your API keys:
# API_KEY=your-api-key
# LLM_API_KEY=your-nebius-api-key
# LLM_API_URL=https://api.tokenfactory.nebius.com/v1/
# LLM_MODEL=meta-llama/Llama-3.3-70B-Instruct-fast
# DEVICE=cpu
```

### 4. Run the Application
```bash
uvicorn main:app --host 0.0.0.0 --port 7860
```

### 5. Docker
```bash
docker build -t honeytrap .
docker run -p 7860:7860 --env-file .env honeytrap
```

## API Endpoint

- **URL:** `https://honeytrap-16395512998.asia-south1.run.app/v1/chat`
- **Method:** POST
- **Authentication:** `x-api-key` header

### Request Format
```json
{
  "sessionId": "unique-session-id",
  "message": {
    "sender": "scammer",
    "text": "URGENT: Your account has been compromised...",
    "timestamp": "2025-02-11T10:30:00Z"
  },
  "conversationHistory": [],
  "metadata": {
    "channel": "SMS",
    "language": "English",
    "locale": "IN"
  }
}
```

### Response Format
```json
{
  "status": "success",
  "reply": "I'm scared, can you give me your phone number so I can verify?",
  "scamDetected": true,
  "scamType": "bank_fraud",
  "extractedIntelligence": {
    "phoneNumbers": ["+91-9876543210"],
    "bankAccounts": ["1234567890123456"],
    "upiIds": ["scammer@fakebank"],
    "phishingLinks": [],
    "emailAddresses": []
  },
  "engagementMetrics": {
    "totalMessagesExchanged": 5,
    "engagementDurationSeconds": 120
  },
  "agentNotes": "Scam type: bank_fraud (confidence: 92%)..."
}
```

## Approach

### How We Detect Scams
- **Rule-Based (50%):** 300+ regex patterns covering 13 scam categories — KYC fraud, prize scams, UPI fraud, authority impersonation, threats, phishing, job scams, and more
- **ML Ensemble (20%):** HuggingFace phishing classifier + zero-shot intent recognition for detecting 8 intent categories
- **LLM Classifier (30%):** Llama 3.3 70B analyzes message content with structured JSON output for score, type, and reasoning

### How We Extract Intelligence
- Regex extraction engine identifies phone numbers, UPI IDs, bank accounts, URLs, emails, PAN, Aadhaar, IFSC codes, and crypto addresses
- Extraction runs on every message (including conversation history from the evaluator)
- Intelligence is accumulated across the entire conversation session

### How We Maintain Engagement
- 5 distinct victim personas (Ramesh Uncle, Priya Sharma, Arun Ji, Tech-Savvy Student, Retired Teacher) selected based on scam type
- Phase-aware responses: Initial Contact → Building Rapport → Active Extraction
- Every response naturally requests scammer details (phone, UPI, bank, email)
- Anti-repetition rules ensure varied, realistic conversation flow
- Contextual stalling tactics (slow phone, app crashing, can't find glasses)

## Project Structure
```
HoneyTrap/
├── main.py                    # FastAPI app & endpoints
├── config.py                  # Environment configuration
├── models.py                  # Pydantic request/response models
├── session_manager.py         # Session state management
├── detectors/
│   ├── engine.py              # Ensemble detection orchestrator
│   ├── rule_based.py          # 300+ regex scam patterns
│   ├── ml_ensemble.py         # HuggingFace ML classifiers
│   └── llm_classifier.py      # Llama 70B scam classifier
├── intelligence/
│   ├── manager.py             # Intelligence extraction orchestrator
│   ├── extractor.py           # Regex entity extraction
│   └── models.py              # Entity & state models
├── response/
│   ├── engine.py              # Response generation orchestrator
│   ├── llm_engine.py          # LLM response generator
│   ├── data.py                # Template responses & strategies
│   └── imperfection.py        # Human-like typo injection
├── personas/
│   ├── manager.py             # Persona selection logic
│   └── profiles.py            # 5 victim persona definitions
├── requirements.txt           # Python dependencies
├── Dockerfile                 # Container configuration
└── .env.example               # Environment variables template
```

## Test Results

Tested against 3 sample evaluation scenarios:

| Scenario | Score | Detection | Intelligence | Engagement | Structure |
|---|---|---|---|---|---|
| Bank Fraud | 90/100 | 20/20 | 30/40 | 20/20 | 20/20 |
| UPI Fraud | 80/100 | 20/20 | 20/40 | 20/20 | 20/20 |
| Phishing | 80/100 | 20/20 | 20/40 | 20/20 | 20/20 |
| **Average** | **83.3/100** | | | | |

- 100% scam detection rate across all scenarios
- 100% fake data extraction (all planted intelligence recovered)
- Average latency: ~16s per turn (within 30s limit)

## License

MIT
