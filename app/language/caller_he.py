"""
Hebrew caller-facing messages.

THIS IS THE ONLY FILE ALLOWED TO CONTAIN HEBREW TEXT.

All text spoken to callers on the phone must be retrieved from this module.
"""

from typing import Dict

# Caller-facing messages in Hebrew
CALLER_MESSAGES: Dict[str, str] = {
    # Greetings
    "greeting_default": "שלום! אני הסוכן מאלטה. אנחנו עוזרים לחברות להגדיל מכירות עם סוכנים חכמים."
,
    "greeting_with_name": "שלום {name}! אני הסוכן מAlta. איך אתה?",

    # Generic short fallback
    "fallback_short": "שלום",
    
    # Prompts
    "ask_time": "איזה זמן מתאים לך?",
    
    # No response scenarios
    "no_response": "מצטערת, לא שמעתי תשובה. תודה ושיהיה יום נהדר!",
    "no_response_retry": "מצטערת, לא שמעתי תשובה. אם תרצה לדבר, תתקשר שוב. יום טוב!",

    # ASR fallback (when speech recognition is unreliable)
    "asr_retry_recording": "לא הצלחתי להבין. בבקשה תגיד שוב.",
    
    # Errors
    "technical_error": "מצטערים, ישנה בעיה טכנית. ננסה שוב מאוחר יותר. להתראות!",
    
    # Closings
    "goodbye": "תודה ושיהיה יום נהדר!",
    "meeting_confirmed": "תקבל אישור במייל עם פרטי הפגישה. מחכה לשיחה!",
    "contact_by_email": "נהיה בקשר במייל. תודה!",
    "disconnected": "נראה שהקו התנתק. נהיה בקשר. תודה!",
}


def get_not_interested_phrases() -> list[str]:
    """Hebrew phrases that indicate the lead is not interested.

    Kept here so Hebrew text stays in approved files.
    """
    return [
        "לא מעוניין",
        "לא רלוונטי",
        "לא מתאים",
        "תוריד",
        "תסיר",
        "אל תתקשר",
    ]


def get_caller_text(key: str, **variables) -> str:
    """
    Get Hebrew text for caller.
    This function must NEVER return an empty string.
    """

    template = CALLER_MESSAGES.get(key)

    if not isinstance(template, str) or not template.strip():
        template = CALLER_MESSAGES.get("greeting_default")

    if not isinstance(template, str) or not template.strip():
        # Absolute last resort, must never be empty
        return "שלום"

    try:
        text = template.format(**variables) if variables else template
    except Exception:
        text = template

    # Final guard
    if not text.strip():
        return "שלום"

    return text
