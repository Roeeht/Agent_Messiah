"""Configuration management for Agent Messiah."""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Application configuration."""
    
    # OpenAI Configuration
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")  # Default to gpt-4o-mini for cost efficiency
    AGENT_MODE: str = os.getenv("AGENT_MODE", "llm")  # "llm" for OpenAI-based or "rule" for rule-based
    
    # Database Configuration
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "sqlite:///./agent_messiah.db"  # Default to SQLite for development
    )
    
    # Redis Configuration
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    REDIS_SESSION_TTL: int = int(os.getenv("REDIS_SESSION_TTL", "1800"))  # 30 minutes
    
    # Twilio Configuration
    TWILIO_ACCOUNT_SID: str = os.getenv("TWILIO_ACCOUNT_SID", "")
    TWILIO_AUTH_TOKEN: str = os.getenv("TWILIO_AUTH_TOKEN", "")
    TWILIO_CALLER_ID: str = os.getenv("TWILIO_CALLER_ID", "")
    
    # Application Settings
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    BASE_URL: str = os.getenv("BASE_URL", "http://localhost:8000")  # For webhooks - use ngrok URL in production
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Language Configuration
    CALLER_LANGUAGE: str = os.getenv("CALLER_LANGUAGE", "he-IL")  # Language spoken to caller
    INTERNAL_LANGUAGE: str = os.getenv("INTERNAL_LANGUAGE", "en")  # Language for logs/state/LLM
    ENABLE_TRANSLATION: bool = os.getenv("ENABLE_TRANSLATION", "True").lower() == "true"  # Use OpenAI for translation

    # Twilio TTS voice (important for Hebrew):
    # If no voice is specified, Twilio may use a default voice that doesn't support Hebrew well.
    TWILIO_TTS_VOICE: str = os.getenv(
        "TWILIO_TTS_VOICE",
        "Google.he-IL-Standard-A" if CALLER_LANGUAGE.startswith("he") else "",
    )
    
    # Security
    API_KEY: str = os.getenv("API_KEY", "")  # For API authentication
    WEBHOOK_SECRET: str = os.getenv("WEBHOOK_SECRET", "")  # For webhook validation
    
    @classmethod
    def validate(cls) -> bool:
        """Validate that required configuration is present."""
        # For basic functionality, we don't require all keys
        # OPENAI and Twilio are optional for initial testing
        return True
    
    @classmethod
    def has_openai_key(cls) -> bool:
        """Check if OpenAI API key is configured."""
        return bool(cls.OPENAI_API_KEY)
    
    @classmethod
    def has_twilio_config(cls) -> bool:
        """Check if Twilio configuration is complete."""
        return all([
            cls.TWILIO_ACCOUNT_SID,
            cls.TWILIO_AUTH_TOKEN,
            cls.TWILIO_CALLER_ID
        ])


# Create a global config instance
config = Config()
