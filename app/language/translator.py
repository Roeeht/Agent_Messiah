"""Translation utilities for Hebrew ↔ English conversion.

Handles:
- Hebrew speech input → English internal representation
- English agent response → Hebrew caller output
"""

from typing import Optional
from app.config import config
import re
from app.language.caller_he import get_caller_text

# Lazy import to avoid circular dependencies
_openai_client = None

HEBREW_RE = re.compile(r"[\u0590-\u05FF]")

def _ensure_hebrew(text: str, fallback_key: str) -> str:
    t = (text or "").strip()
    if not t:
        return get_caller_text(fallback_key)
    if not HEBREW_RE.search(t):
        return get_caller_text(fallback_key)
    return t


def _get_openai_client():
    """Lazy initialization of OpenAI client."""
    global _openai_client
    if _openai_client is None and config.has_openai_key():
        from openai import OpenAI
        _openai_client = OpenAI(api_key=config.OPENAI_API_KEY)
    return _openai_client


def translate_he_to_en(hebrew_text: str) -> str:
    """
    Convert Hebrew speech to English internal message.
    
    This is used to translate what the caller says (in Hebrew) into English
    for internal processing, logging, and LLM context.
    
    Args:
        hebrew_text: Hebrew speech from Twilio transcription
    
    Returns:
        English translation for internal use
    
    Examples:
        >>> translate_he_to_en("כן, מעניין אותי")
        "Yes, I'm interested"
        
        >>> translate_he_to_en("אני רוצה לקבוע פגישה")
        "I want to schedule a meeting"
    """
    if not hebrew_text or not hebrew_text.strip():
        return "[empty speech]"
    
    # Check if translation is enabled and OpenAI is configured
    if not config.ENABLE_TRANSLATION:
        return f"[Hebrew speech not translated: {hebrew_text[:50]}...]"
    
    client = _get_openai_client()
    if not client:
        return f"[Hebrew speech - translation unavailable: {hebrew_text[:50]}...]"
    
    try:
        response = client.chat.completions.create(
            model=config.OPENAI_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "Translate Hebrew to English concisely. Preserve meaning and tone. Return only the English translation."
                },
                {
                    "role": "user",
                    "content": hebrew_text
                }
            ],
            temperature=0.3,
            max_tokens=200
        )
        
        return response.choices[0].message.content or "[translation failed]"
        
    except Exception as e:
        # Log error but don't crash
        print(f"Translation error (HE→EN): {e}")
        return f"[Hebrew speech - translation error: {hebrew_text[:50]}...]"


def translate_en_to_he(english_text: str) -> str:
    """
    Convert English agent response to Hebrew for caller.
    
    This is used to translate the agent's internal English response into
    Hebrew that will be spoken to the caller.
    
    Args:
        english_text: English response from agent logic/LLM
    
    Returns:
        Hebrew text to speak to caller
    
    Examples:
        >>> translate_en_to_he("Yes, I can help you with that.")
        "כן, אני יכול לעזור לך עם זה."
        
        >>> translate_en_to_he("Let me check our available times.")
        "אני בודק את הזמנים הפנויים שלנו."
    """
    if not english_text or not english_text.strip():
        return get_caller_text("technical_error")

    if not config.ENABLE_TRANSLATION:
        return get_caller_text("technical_error")

    client = _get_openai_client()
    if not client:
        return get_caller_text("technical_error")

    
    try:
        response = client.chat.completions.create(
            model=config.OPENAI_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "Translate to Hebrew for speaking on a phone call. Output Hebrew text only. No English. No quotes. No extra words."
                },
                {
                    "role": "user",
                    "content": english_text
                }
            ],
            temperature=0.7,
            max_tokens=200
        )
        
        hebrew_result = response.choices[0].message.content
        return _ensure_hebrew(hebrew_result, "technical_error")

        
    except Exception as e:
        # Log error but don't crash
        print(f"Translation error (EN→HE): {e}")
        return get_caller_text("technical_error")
