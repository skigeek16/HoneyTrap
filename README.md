# 🍯 Agentic Honey-Pot (HoneyTrap)

**Autonomous AI Honeypot System for Scam Detection & Intelligence Extraction**

This system is designed to engage with potential scammers, detect malicious intent, and autonomous extract actionable intelligence (UPI IDs, Bank Accounts, Phone Numbers) using adaptive personas. It employs a multi-agent architecture combining Rule-based logic, ML ensembles, and LLMs to create realistic, "imperfect" human responses.

---

## 🚀 System Architecture & Workflow

The system operates as a pipeline of specialized agents:

1.  **Incoming Request (`/v1/chat`)**: The entry point receives a message.
2.  **Session Management**: Loads previous context from Redis/Memory.
3.  **🛡️ Stage 2: Scam Detection**:
    *   **Rule-Based**: Checks for specific regex patterns (OTP requests, lottery claims).
    *   **ML Ensemble**: Uses Transformer models (BERT/RoBERTa) for intent classification and phishing detection.
    *   **Decision**: If both agree on "Safe", it declines politely. If "Scam" is detected, it activates the Agent.
4.  **🎭 Stage 3: Persona & Strategy**:
    *   Selects a persona vulnerable to the specific scam type (e.g., "Elderly Confused" for Tech Support scams).
    *   Sets a strategy (Initial Contact -> Building Rapport -> Active Extraction).
5.  **🕵️ Stage 4: Intelligence Extraction**:
    *   Scans message for entities using NER and Regex.
    *   Identifies gaps (e.g., "I have the bank account, but need the IFSC").
6.  **💬 Stage 5: Response Generation**:
    *   **LLM Engine**: Generates context-aware, strategic replies.
    *   **Fallback**: Uses semantic search to find the best template if LLM fails.
    *   **Imperfection Engine**: Injests typos, "Indianisms", and delays to mimic human typing based on the Persona.

---

## 📂 Codebase Structure & File Descriptions

### **Root Directory**

*   **`main.py`**: The FastAPI application entry point. Defines API endpoints (`/v1/chat`, `/v1/session`) and initializes the system managers.
*   **`models.py`**: Pydantic models defining the data schemas for Requests, Responses, Session State, and Intelligence.
*   **`session_manager.py`**: Handles session persistence (Redis/Memory), state updates, and sends callbacks to the external GUVI dashboard.
*   **`config.py`**: Integration configuration using `pydantic-settings`. Loads environment variables for API keys, Redis, and Model paths.
*   **`requirements.txt`**: List of Python dependencies.

### **1. Detectors (`/detectors`)**
Responsible for classifying if a user is a scammer.
*   **`engine.py`**: The orchestrator. Runs both Rule and ML detectors and calculates a final "Confidence Score".
*   **`rule_based.py`**: High-speed detector using Regex patterns for known scam scripts (Job scams, sextortion, etc.).
*   **`ml_ensemble.py`**: (Inferred) Wraps HuggingFace transformers for "Intent", "Sentiment", and "Phishing" classification.

### **2. Personas (`/personas`)**
Manages the "fake victims" the system plays.
*   **`manager.py`**: Selects the best persona based on the detected scam type (e.g., assigns `PERSONA_ELDERLY_CONFUSED` to `Bank Fraud`).
*   **`library.py`**: Contains the static definitions of personas, including their backstory, vocabulary, and vulnerability levels.
*   **`models.py`**: Pydantic models for `Persona` and `Strategy` objects.

### **3. Intelligence (`/intelligence`)**
The "Spy" module that extracts data from scammer messages.
*   **`manager.py`**: Coordinates extraction and performs "Gap Analysis" (determining what info is still missing).
*   **`extractor.py`**: The heavy lifter. Uses `KeyBERT` for keywords, `bert-base-NER` for entities, and complex Regex for Indian-specific formats (UPI, IFSC, Aadhaar).
*   **`models.py`**: Defines `IntelligenceState` and `Entity` classes.

### **4. Response (`/response`)**
Generates the text sent back to the scammer.
*   **`engine.py`**: Decides *how* to reply. It prioritizes LLM generation, but falls back to Semantic Search (Template Matching) if needed.
*   **`llm_engine.py`**: Connects to the LLM provider (Nebius/Llama-70B) to generate dynamic, improvised responses.
*   **`imperfection.py`**: A unique module that "humanizes" text by adding:
    *   Typos (based on keyboard proximity).
    *   Text-speak ("u", "plz", "tmrw").
    *   Indian English mannerisms ("kindly", "do the needful").
    *   Typing delays.
*   **`data.py`**: Stores fallback response templates.

---

## 🛠️ Installation & Setup

1.  **Clone the Repository**
    ```bash
    git clone <repo-url>
    cd HoneyTrap
    ```

2.  **Install Dependencies**
    It is recommended to use a virtual environment.
    ```bash
    pip install -r requirements.txt
    ```

3.  **Environment Configuration**
    Create a `.env` file in the root directory:
    ```env
    API_KEY=your_secret_api_key
    USE_REDIS=False
    LLM_API_KEY=your_nebius_key
    ```

4.  **Run the Server**
    ```bash
    python main.py
    # OR using uvicorn directly
    uvicorn main:app --reload --host 0.0.0.0 --port 8000
    ```

---

## 🔌 API Usage

### **1. Chat Endpoint**
**POST** `/v1/chat`
*   **Headers**: `x-api-key: <your_key>`
*   **Body**:
    ```json
    {
        "sessionId": "test-session-001",
        "message": "Hello sir, your account is blocked. Update KYC immediately."
    }
    ```

### **2. Session Info**
**GET** `/v1/session/{session_id}`
*   Returns the current state, including detected scam confidence, active persona, and extracted intelligence.
