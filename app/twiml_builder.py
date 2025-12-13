"""TwiML generation utilities.

Handles:
- XML escaping for all dynamic content
- Proper URL encoding for action attributes
- Consistent voice and language settings
- Unicode normalization and control character removal
"""

import re
import unicodedata
import xml.sax.saxutils as saxutils
from app.config import config
from app.language.caller_he import get_caller_text


def _say_attrs() -> str:
    language = (config.CALLER_LANGUAGE or "he-IL").strip()
    voice = (getattr(config, "TWILIO_TTS_VOICE", "") or "").strip()

    attrs = f'language="{saxutils.escape(language)}"'
    if voice:
        attrs += f' voice="{saxutils.escape(voice)}"'
    return attrs


def _record_timeout_seconds() -> int:
    timeout_s = int(getattr(config, "RECORD_SILENCE_TIMEOUT_SECONDS", 1) or 1)
    # Keep a sane range; too low can clip speech, too high adds latency.
    # if timeout_s < 1:
    #     timeout_s = 1
    # # Cap slightly lower to reduce perceived latency.
    # if timeout_s > 5:
    #     timeout_s = 5
    return timeout_s


def sanitize_say_text(text: str, fallback: str | None = None) -> str:
    """
    Sanitize text for Twilio <Say> tags.
    
    - Normalizes Unicode (NFKC)
    - Removes control characters (keeps basic whitespace)
    - Collapses whitespace
    - Escapes for XML
    - Returns fallback if empty
    
    Args:
        text: Text to sanitize
        fallback: Fallback text if input is empty
    
    Returns:
        Sanitized and XML-escaped text
    """
    if not text:
        text = fallback or get_caller_text("fallback_short")
    
    # Normalize Unicode (NFKC = compatibility decomposition + canonical composition)
    t = unicodedata.normalize("NFKC", text)
    
    # Remove control chars (keep basic whitespace: newline, tab, space)
    t = "".join(ch for ch in t if ch in ["\n", "\t"] or ord(ch) >= 32)
    
    # Collapse whitespace
    t = re.sub(r"\s+", " ", t).strip()
    
    if not t:
        t = fallback or get_caller_text("fallback_short")
    
    # Escape for XML
    return saxutils.escape(t)


def build_voice_twiml(greeting_hebrew: str, call_sid: str, lead_id: int) -> str:
    """
    Build initial voice call TwiML with proper escaping.
    
    Args:
        greeting_hebrew: Hebrew greeting text (already translated)
        call_sid: Twilio call SID
        lead_id: Lead identifier
    
    Returns:
        Complete TwiML XML string
    """
    # Default Hebrew input method: record (no beep), then transcribe.
    greeting_escaped = sanitize_say_text(greeting_hebrew)

    action_url = f"{config.BASE_URL}/twilio/process-recording?call_sid={call_sid}&lead_id={lead_id}&turn=0"
    action_url_escaped = saxutils.escape(action_url)

    say_attrs = _say_attrs()
    max_len = int(getattr(config, "RECORD_MAX_LENGTH_SECONDS", 10) or 10)
    if max_len <= 0:
        max_len = 10
    timeout_s = _record_timeout_seconds()

    return f"""<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<Response>
    <Say {say_attrs}>{greeting_escaped}</Say>
    <Record playBeep=\"false\" maxLength=\"{max_len}\" timeout=\"{timeout_s}\" action=\"{action_url_escaped}\" method=\"POST\" />
</Response>"""


def build_error_twiml(error_message_hebrew: str) -> str:
    """
    Build error TwiML.
    
    Args:
        error_message_hebrew: Hebrew error message
    
    Returns:
        TwiML XML string
    """
    msg_escaped = sanitize_say_text(error_message_hebrew)

    say_attrs = _say_attrs()
    
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say {say_attrs}>{msg_escaped}</Say>
    <Hangup/>
</Response>"""


def build_hangup_twiml(final_message_hebrew: str) -> str:
    """
    Build TwiML that says a message and hangs up.
    
    Args:
        final_message_hebrew: Hebrew message before hanging up
    
    Returns:
        TwiML XML string
    """
    msg_escaped = sanitize_say_text(final_message_hebrew)

    say_attrs = _say_attrs()
    
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say {say_attrs}>{msg_escaped}</Say>
    <Hangup/>
</Response>"""


def build_record_fallback_twiml(prompt_hebrew: str, call_sid: str, lead_id: int, turn: int) -> str:
    """Ask caller to repeat and record audio."""
    prompt_escaped = sanitize_say_text(prompt_hebrew)

    action_url = f"{config.BASE_URL}/twilio/process-recording?call_sid={call_sid}&lead_id={lead_id}&turn={turn}"
    action_url_escaped = saxutils.escape(action_url)

    say_attrs = _say_attrs()
    max_len = int(getattr(config, "RECORD_MAX_LENGTH_SECONDS", 10) or 10)
    if max_len <= 0:
        max_len = 10
    timeout_s = _record_timeout_seconds()

    return f"""<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<Response>
    <Say {say_attrs}>{prompt_escaped}</Say>
    <Record playBeep=\"false\" maxLength=\"{max_len}\" timeout=\"{timeout_s}\" action=\"{action_url_escaped}\" method=\"POST\" />
</Response>"""


def build_continue_twiml(agent_reply_hebrew: str, call_sid: str, lead_id: int, turn: int) -> str:
    """
    Build TwiML to continue conversation with recording.
    
    Args:
        agent_reply_hebrew: Hebrew agent response (already translated)
        call_sid: Twilio call SID
        lead_id: Lead identifier
        turn: Current turn number
    
    Returns:
        TwiML XML string
    """
    reply_escaped = sanitize_say_text(agent_reply_hebrew)

    next_url = f"{config.BASE_URL}/twilio/process-recording?call_sid={call_sid}&lead_id={lead_id}&turn={turn+1}"
    next_url_escaped = saxutils.escape(next_url)

    say_attrs = _say_attrs()
    max_len = int(getattr(config, "RECORD_MAX_LENGTH_SECONDS", 10) or 10)
    if max_len <= 0:
        max_len = 10
    timeout_s = _record_timeout_seconds()

    return f"""<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<Response>
    <Say {say_attrs}>{reply_escaped}</Say>
    <Record playBeep=\"false\" maxLength=\"{max_len}\" timeout=\"{timeout_s}\" action=\"{next_url_escaped}\" method=\"POST\" />
</Response>"""


def build_offer_slots_twiml(slots_message_hebrew: str, call_sid: str, lead_id: int, turn: int) -> str:
    """
    Build TwiML to offer meeting slots.
    
    Args:
        slots_message_hebrew: Hebrew message with slot options
        call_sid: Twilio call SID
        lead_id: Lead identifier
        turn: Current turn number
    
    Returns:
        TwiML XML string
    """
    slots_escaped = sanitize_say_text(slots_message_hebrew)
    ask_time = sanitize_say_text(get_caller_text("ask_time"))

    next_url = f"{config.BASE_URL}/twilio/process-recording?call_sid={call_sid}&lead_id={lead_id}&turn={turn+1}"
    next_url_escaped = saxutils.escape(next_url)

    say_attrs = _say_attrs()
    max_len = int(getattr(config, "RECORD_MAX_LENGTH_SECONDS", 10) or 10)
    if max_len <= 0:
        max_len = 10
    timeout_s = _record_timeout_seconds()

    return f"""<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<Response>
    <Say {say_attrs}>{slots_escaped}</Say>
    <Say {say_attrs}>{ask_time}</Say>
    <Record playBeep=\"false\" maxLength=\"{max_len}\" timeout=\"{timeout_s}\" action=\"{next_url_escaped}\" method=\"POST\" />
</Response>"""


def build_meeting_confirmed_twiml(confirmation_message_hebrew: str) -> str:
    """
    Build TwiML for meeting confirmation.
    
    Args:
        confirmation_message_hebrew: Hebrew confirmation message
    
    Returns:
        TwiML XML string
    """
    msg_escaped = sanitize_say_text(confirmation_message_hebrew)
    follow_up = sanitize_say_text(get_caller_text("meeting_confirmed"))

    say_attrs = _say_attrs()
    
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say {say_attrs}>{msg_escaped}</Say>
    <Pause length="1"/>
    <Say {say_attrs}>{follow_up}</Say>
    <Hangup/>
</Response>"""
