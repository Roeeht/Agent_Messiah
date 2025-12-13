"""In-memory storage for calendar and meetings."""

from datetime import datetime, timedelta
from typing import Optional
from app.models import Meeting, MeetingSlot

# In-memory storage
_meetings_db: dict[int, Meeting] = {}
_next_meeting_id = 1


def get_available_slots() -> list[MeetingSlot]:
    """
    Get available meeting slots.
    For now, returns 2-4 hardcoded future slots.
    In production, this would check real calendar availability.
    """
    now = datetime.now()
    
    # Generate slots for the next few days at 10:00 and 14:00
    slots = []
    
    # Tomorrow at 10:00
    tomorrow_10 = (now + timedelta(days=1)).replace(hour=10, minute=0, second=0, microsecond=0)
    slots.append(MeetingSlot(
        start=tomorrow_10,
        duration_minutes=30,
        display_text=f"Tomorrow at 10:00 ({tomorrow_10.strftime('%d/%m')})"
    ))
    
    # Tomorrow at 14:00
    tomorrow_14 = (now + timedelta(days=1)).replace(hour=14, minute=0, second=0, microsecond=0)
    slots.append(MeetingSlot(
        start=tomorrow_14,
        duration_minutes=30,
        display_text=f"Tomorrow at 14:00 ({tomorrow_14.strftime('%d/%m')})"
    ))
    
    # Day after tomorrow at 10:00
    day_after_10 = (now + timedelta(days=2)).replace(hour=10, minute=0, second=0, microsecond=0)
    slots.append(MeetingSlot(
        start=day_after_10,
        duration_minutes=30,
        display_text=f"Day after tomorrow at 10:00 ({day_after_10.strftime('%d/%m')})"
    ))
    
    return slots[:2]  # Return only first 2 slots as specified


def book_meeting(lead_id: int, start: datetime, duration_minutes: int = 30) -> Meeting:
    """
    Book a meeting for a lead.
    Creates a meeting record and returns it.
    """
    global _next_meeting_id
    
    # Generate a simple calendar link (in production, this would be a real calendar invite)
    calendar_link = f"https://calendar.example.com/meeting/{_next_meeting_id}"
    
    meeting = Meeting(
        id=_next_meeting_id,
        lead_id=lead_id,
        start=start,
        duration_minutes=duration_minutes,
        calendar_link=calendar_link
    )
    
    _meetings_db[_next_meeting_id] = meeting
    _next_meeting_id += 1
    
    return meeting


def list_meetings() -> list[Meeting]:
    """List all scheduled meetings."""
    return list(_meetings_db.values())


def get_meeting_by_id(meeting_id: int) -> Optional[Meeting]:
    """Get a meeting by ID."""
    return _meetings_db.get(meeting_id)
