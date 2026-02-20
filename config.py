import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load .env file
load_dotenv()

class Settings(BaseSettings):
    # API Security
    API_KEY: str = os.getenv("API_KEY", "secret-key-12345")

    # LLM Configuration - Nebius Token Factory
    LLM_API_KEY: str = os.getenv("LLM_API_KEY", "")
    LLM_API_URL: str = os.getenv("LLM_API_URL", "https://api.tokenfactory.nebius.com/v1/")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "meta-llama/Llama-3.3-70B-Instruct-fast")

    # ML Model Configuration (lightweight models only)
    MODEL_PHISHING: str = "ealvaradob/bert-finetuned-phishing"
    MODEL_INTENT: str = "facebook/bart-large-mnli"

    # Scoring Thresholds
    SCORE_THRESHOLD: int = 22

    # Device configuration
    DEVICE: str = os.getenv("DEVICE", "cpu")

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
