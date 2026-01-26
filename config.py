import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load .env file
load_dotenv()

class Settings(BaseSettings):
    # API Security
    API_KEY: str = os.getenv("API_KEY", "secret-key-12345")
    
    # Redis Configuration
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_DB: int = int(os.getenv("REDIS_DB", "0"))
    USE_REDIS: bool = os.getenv("USE_REDIS", "False").lower() == "true"

    # LLM Configuration - Nebius Token Factory
    LLM_API_KEY: str = os.getenv("LLM_API_KEY", "")
    LLM_API_URL: str = os.getenv("LLM_API_URL", "https://api.tokenfactory.nebius.com/v1/")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "meta-llama/Llama-3.3-70B-Instruct-fast")

    # ML Model Configuration
    MODEL_PHISHING: str = "ealvaradob/bert-finetuned-phishing"
    MODEL_SENTIMENT: str = "cardiffnlp/twitter-roberta-base-sentiment"
    MODEL_EMOTION: str = "j-hartmann/emotion-english-distilroberta-base"
    MODEL_INTENT: str = "facebook/bart-large-mnli"
    MODEL_LANG: str = "papluca/xlm-roberta-base-language-detection"
    MODEL_MULTILINGUAL: str = "joeddav/xlm-roberta-large-xnli" 

    # Scoring Thresholds
    SCORE_LOW: int = 20
    SCORE_MEDIUM: int = 35
    SCORE_HIGH: int = 60
    
    # Ensemble Weights
    WEIGHT_PHISHING: float = 0.30
    WEIGHT_RULE_BASED: float = 0.25
    WEIGHT_EMOTION: float = 0.15
    WEIGHT_SENTIMENT: float = 0.10
    WEIGHT_INTENT: float = 0.10
    WEIGHT_MULTILINGUAL: float = 0.10

    # Device configuration
    DEVICE: str = os.getenv("DEVICE", "cpu")

    class Config:
        env_file = ".env"

settings = Settings()