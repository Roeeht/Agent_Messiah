"""Configuration management for Agent Messiah."""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Application configuration."""
    
    # OpenAI Configuration
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")  
    # Agent Messiah runs in LLM-only mode.
    # If OpenAI is not configured, LLM-dependent endpoints will return an error.
    
    # Twilio Configuration
    TWILIO_ACCOUNT_SID: str = os.getenv("TWILIO_ACCOUNT_SID", "")
    TWILIO_AUTH_TOKEN: str = os.getenv("TWILIO_AUTH_TOKEN", "")
    TWILIO_CALLER_ID: str = os.getenv("TWILIO_CALLER_ID", "")
    
    # Application Settings
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    BASE_URL: str = os.getenv("BASE_URL", "http://localhost:8000")  # For webhooks - use ngrok URL in production
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # Optional: log caller/agent transcript to console.
    # Defaults to enabled in development (DEBUG=True) and disabled in production.
    # May include sensitive content.
    LOG_CALL_TRANSCRIPT: bool = os.getenv(
        "LOG_CALL_TRANSCRIPT",
        "True" if DEBUG else "False",
    ).lower() == "true"
    LOG_CALL_TRANSCRIPT_MAX_CHARS: int = int(os.getenv("LOG_CALL_TRANSCRIPT_MAX_CHARS", "500"))

    # Voice Debugging (development / controlled environments only)
    # When enabled, Twilio webhooks will store per-call debug events in the session store.
    # This can include raw caller speech and agent replies.
    DEBUG_CALL_EVENTS: bool = os.getenv("DEBUG_CALL_EVENTS", "False").lower() == "true"
    DEBUG_CALL_EVENTS_MAX: int = int(os.getenv("DEBUG_CALL_EVENTS_MAX", "200"))

    # ASR / Speech input behavior
    # Hebrew voice input: we use Twilio <Record> + OpenAI transcription as the default path.
    # (Twilio <Gather input="speech"> can misrecognize Hebrew as English-like gibberish.)
    HEBREW_ASR_FALLBACK_TO_RECORDING: bool = os.getenv("HEBREW_ASR_FALLBACK_TO_RECORDING", "True").lower() == "true"
    RECORD_MAX_LENGTH_SECONDS: int = int(os.getenv("RECORD_MAX_LENGTH_SECONDS", "15"))
    # Twilio <Record timeout>: seconds of silence before Twilio ends the recording and hits the action URL.
    # Lower values reduce latency but can clip trailing words; 2 is a reasonable default.
    RECORD_SILENCE_TIMEOUT_SECONDS: int = int(os.getenv("RECORD_SILENCE_TIMEOUT_SECONDS", "2"))

    # OpenAI transcription model for recorded audio
    OPENAI_TRANSCRIBE_MODEL: str = os.getenv("OPENAI_TRANSCRIBE_MODEL", "gpt-4o-mini-transcribe")
    
    # Language Configuration
    CALLER_LANGUAGE: str = os.getenv("CALLER_LANGUAGE", "he-IL")  # Language spoken to caller
    ENABLE_TRANSLATION: bool = os.getenv("ENABLE_TRANSLATION", "True").lower() == "true"  # Use OpenAI for translation

    # Twilio TTS voice (important for Hebrew):
    # If no voice is specified, Twilio may use a default voice that doesn't support Hebrew well.
    TWILIO_TTS_VOICE: str = os.getenv(
        "TWILIO_TTS_VOICE",
        "Google.he-IL-Wavenet-A" if CALLER_LANGUAGE.startswith("he") else "",
    )
    
    # Security
    API_KEY: str = os.getenv("API_KEY", "")  # For API authentication
    
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

    @classmethod
    def has_twilio_auth(cls) -> bool:
        """Check if Twilio auth is available (for fetching recordings, etc.)."""
        return bool(cls.TWILIO_ACCOUNT_SID and cls.TWILIO_AUTH_TOKEN)


# Create a global config instance
config = Config()
