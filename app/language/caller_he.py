"""
Hebrew caller-facing messages.

THIS IS THE ONLY FILE ALLOWED TO CONTAIN HEBREW TEXT.

All text spoken to callers on the phone must be retrieved from this module.
"""

from typing import Dict
import re

# Caller-facing messages in Hebrew
CALLER_MESSAGES: Dict[str, str] = {
    # Greetings
    "greeting_default": "שלום! אני הסוכן משיח מאלטה. אנחנו עוזרים לחברות להגדיל מכירות עם סוכנים חכמים."
,
    "greeting_with_name": "שלום {name}! אני משיח הסוכן מHabari's Sales Copnamy. איך אתה? ",

    # Permission gate (first question)
    "permission_ask": "שלום! אני הסוכן משיח מאלטה. אנחנו עוזרים לחברות להגדיל מכירות עם סוכנים חכמים. האם זה זמן טוב לדבר? בבקשה ענה רק כן או לא.",
    "permission_clarify": "רק כדי לוודא, האם זה זמן טוב לדבר? בבקשה ענה כן או לא.",

    # Generic short fallback
    "fallback_short": "שלום",
    
    # Prompts
    "ask_time": "איזה זמן מתאים לך?",
    
    # No response scenarios
    "no_response": "מצטער, לא שמעתי תשובה. תודה ושיהיה יום נהדר!",
    "no_response_retry": "מצטער, לא שמעתי תשובה. אם תרצה לדבר, תתקשר שוב. יום טוב!",

    # ASR fallback (when speech recognition is unreliable)
    "asr_retry_recording": "לא הצלחתי להבין. בבקשה תגיד שוב.",
    
    # Errors
    "technical_error": "מצטער, ישנה בעיה טכנית. ננסה שוב מאוחר יותר. להתראות!",
    
    # Closings
    "goodbye": "תודה ושיהיה יום נהדר!",
    "not_interested_goodbye": "אין בעיה. אם תשנה את דעתך, אתה מוזמן להתקשר אלינו. להתראות!",
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


def get_permission_yes_phrases() -> list[str]:
    """Hebrew phrases that indicate consent to continue the call (yes).

    Kept here so Hebrew text stays in approved files.
    """
    return [
        "כן",
        "בטח",
        "כן בטח",
        "כן אפשר",
        "כן, אפשר",
        "אפשר",
        "בסדר",
        "אוקיי",
        "אוקי",
    ]


def get_permission_no_phrases() -> list[str]:
    """Hebrew phrases that indicate the lead is not available / not interested right now (no).

    Kept here so Hebrew text stays in approved files.
    """
    return [
        "לא",
        "לא תודה",
        "לא, תודה",
        "לא עכשיו",
        "לא מתאים",
        "לא זמן טוב",
        "לא בזמן",
        "עזוב",
        "עזבי",
        *get_not_interested_phrases(),
    ]


def is_goodbye_message(text: str) -> bool:
    """Heuristic: does the given Hebrew text look like a closing/goodbye?

    Kept here so Hebrew markers stay in approved files.
    """
    t = (text or "").strip()
    if not t:
        return False

    goodbye = get_caller_text("goodbye")
    if goodbye and goodbye in t:
        return True

    # Common closings.
    if any(kw in t for kw in [
        "להתראות",
        "ביי",
        "נתראה",
        "לילה טוב",
        "ערב טוב",
        "שבת שלום",
    ]):
        return True

    # Day-wishes like: "שיהיה (לך) יום טוב/נהדר/נפלא/...".
    if re.search(r"שיהיה(?: לך)? יום (?:טוב|נפלא|נהדר|מקסים|מעולה)", t):
        return True
    if re.search(r"יום (?:טוב|נפלא|נהדר|מקסים|מעולה)", t):
        return True

    return False


def is_transcription_instructions_echo(text: str) -> bool:
    """Detect when a transcript is actually echoed instructions/prompt.

    Some transcription backends may incorrectly return the instruction text.
    Kept here so Hebrew markers stay in approved files.
    """
    t = (text or "").strip()
    if not t:
        return False

    # Known fragments that have shown up when prompts were echoed back.
    return any(fragment in t for fragment in [
        "תמלול של שיחת טלפון",
        "תמלל רק את מה שהדובר",
        "החזר טקסט ריק",
    ])


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
