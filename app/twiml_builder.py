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


def sanitize_say_text(text: str, fallback: str = "שלום") -> str:
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
        text = fallback
    
    # Normalize Unicode (NFKC = compatibility decomposition + canonical composition)
    t = unicodedata.normalize("NFKC", text)
    
    # Remove control chars (keep basic whitespace: newline, tab, space)
    t = "".join(ch for ch in t if ch in ["\n", "\t"] or ord(ch) >= 32)
    
    # Collapse whitespace
    t = re.sub(r"\s+", " ", t).strip()
    
    if not t:
        t = fallback
    
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
    # Sanitize and escape Hebrew text for XML
    greeting_escaped = sanitize_say_text(greeting_hebrew)
    listening_prompt = sanitize_say_text(get_caller_text("listening"))
    no_response = sanitize_say_text(get_caller_text("no_response"))
    
    # Build action URL (will be escaped when inserted into XML)
    action_url = f"{config.BASE_URL}/twilio/process-speech?call_sid={call_sid}&lead_id={lead_id}&turn=0"
    action_url_escaped = saxutils.escape(action_url)
    
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say language="he-IL">{greeting_escaped}</Say>
    <Gather input="speech" language="he-IL" speechTimeout="auto" timeout="10" action="{action_url_escaped}" method="POST">
        <Say language="he-IL">{listening_prompt}</Say>
    </Gather>
    <Say language="he-IL">{no_response}</Say>
    <Hangup/>
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
    
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say language="he-IL">{msg_escaped}</Say>
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
    
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say language="he-IL">{msg_escaped}</Say>
    <Hangup/>
</Response>"""


def build_continue_twiml(agent_reply_hebrew: str, call_sid: str, lead_id: int, turn: int) -> str:
    """
    Build TwiML to continue conversation with speech gathering.
    
    Args:
        agent_reply_hebrew: Hebrew agent response (already translated)
        call_sid: Twilio call SID
        lead_id: Lead identifier
        turn: Current turn number
    
    Returns:
        TwiML XML string
    """
    reply_escaped = sanitize_say_text(agent_reply_hebrew)
    listening = sanitize_say_text(get_caller_text("listening"))
    disconnected = sanitize_say_text(get_caller_text("disconnected"))
    
    # Build next action URL
    next_url = f"{config.BASE_URL}/twilio/process-speech?call_sid={call_sid}&lead_id={lead_id}&turn={turn+1}"
    next_url_escaped = saxutils.escape(next_url)
    
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say language="he-IL">{reply_escaped}</Say>
    <Gather input="speech" language="he-IL" speechTimeout="auto" timeout="10" action="{next_url_escaped}" method="POST">
        <Say language="he-IL">{listening}</Say>
    </Gather>
    <Say language="he-IL">{disconnected}</Say>
    <Hangup/>
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
    contact_email = sanitize_say_text(get_caller_text("contact_by_email"))
    
    next_url = f"{config.BASE_URL}/twilio/process-speech?call_sid={call_sid}&lead_id={lead_id}&turn={turn+1}"
    next_url_escaped = saxutils.escape(next_url)
    
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say language="he-IL">{slots_escaped}</Say>
    <Gather input="speech" language="he-IL" speechTimeout="auto" timeout="10" action="{next_url_escaped}" method="POST">
        <Say language="he-IL">{ask_time}</Say>
    </Gather>
    <Say language="he-IL">{contact_email}</Say>
    <Hangup/>
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
    
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say language="he-IL">{msg_escaped}</Say>
    <Pause length="1"/>
    <Say language="he-IL">{follow_up}</Say>
    <Hangup/>
</Response>"""
