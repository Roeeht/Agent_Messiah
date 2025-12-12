"""
Hebrew caller-facing messages.

THIS IS THE ONLY FILE ALLOWED TO CONTAIN HEBREW TEXT.

All text spoken to callers on the phone must be retrieved from this module.
"""

from typing import Dict

# Caller-facing messages in Hebrew
CALLER_MESSAGES: Dict[str, str] = {
    # Greetings
    "greeting_default": "שלום! אני הסוכן מAlta. אנחנו עוזרים לחברות להגדיל מכירות עם סוכני AI.",
    "greeting_with_name": "שלום {name}! אני הסוכן מAlta. איך אתה?",
    
    # Prompts
    "listening": "אני מקשיבה",
    "ask_time": "איזה זמן מתאים לך?",
    
    # No response scenarios
    "no_response": "מצטערת, לא שמעתי תשובה. תודה ושיהיה יום נהדר!",
    "no_response_retry": "מצטערת, לא שמעתי תשובה. אם תרצה לדבר, תתקשר שוב. יום טוב!",
    
    # Errors
    "technical_error": "מצטערים, ישנה בעיה טכנית. ננסה שוב מאוחר יותר. להתראות!",
    
    # Closings
    "goodbye": "תודה ושיהיה יום נהדר!",
    "meeting_confirmed": "תקבל אישור במייל עם פרטי הפגישה. מחכה לשיחה!",
    "contact_by_email": "נהיה בקשר במייל. תודה!",
    "disconnected": "נראה שהקו התנתק. נהיה בקשר. תודה!",
}


def get_caller_text(key: str, **variables) -> str:
    """
    Get Hebrew text for caller.
    
    This is the ONLY function that returns Hebrew text.
    
    Args:
        key: Message key from CALLER_MESSAGES
        **variables: Template variables to format into the message
    
    Returns:
        Hebrew text to speak to the caller
    
    Examples:
        >>> get_caller_text("greeting_default")
        'שלום! אני הסוכן מAlta...'
        
        >>> get_caller_text("greeting_with_name", name="רועי")
        'שלום רועי! אני הסוכן מAlta...'
    """
    template = CALLER_MESSAGES.get(key, "")
    
    if not template:
        # Fallback to default greeting if key not found
        template = CALLER_MESSAGES.get("greeting_default", "")
    
    try:
        return template.format(**variables) if variables else template
    except KeyError as e:
        # Missing template variable, return template as-is
        return template
