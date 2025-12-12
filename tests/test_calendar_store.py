"""Tests for calendar store."""

import pytest
from datetime import datetime
from app.calendar_store import get_available_slots, book_meeting, list_meetings


def test_get_available_slots_returns_slots():
    """Test that get_available_slots returns at least 1 slot."""
    slots = get_available_slots()
    
    assert len(slots) >= 1
    assert len(slots) <= 4  # Should return 2-4 slots as per spec
    
    # Check slot structure
    for slot in slots:
        assert slot.start is not None
        assert isinstance(slot.start, datetime)
        assert slot.duration_minutes > 0
        assert slot.display_text != ""
        assert isinstance(slot.display_text, str)


def test_get_available_slots_returns_future_times():
    """Test that slots are in the future."""
    slots = get_available_slots()
    now = datetime.now()
    
    for slot in slots:
        assert slot.start > now, "Slot should be in the future"


def test_book_meeting_creates_meeting():
    """Test that book_meeting adds a meeting and returns it."""
    initial_meetings = list_meetings()
    initial_count = len(initial_meetings)
    
    # Book a meeting
    start_time = datetime(2025, 12, 15, 10, 0)
    meeting = book_meeting(
        lead_id=1,
        start=start_time,
        duration_minutes=30
    )
    
    # Verify meeting was created
    assert meeting is not None
    assert meeting.id is not None
    assert meeting.lead_id == 1
    assert meeting.start == start_time
    assert meeting.duration_minutes == 30
    assert meeting.calendar_link != ""
    
    # Verify meeting was added to storage
    all_meetings = list_meetings()
    assert len(all_meetings) == initial_count + 1
    assert meeting in all_meetings


def test_book_meeting_returns_calendar_link():
    """Test that booked meetings have calendar links."""
    start_time = datetime(2025, 12, 16, 14, 0)
    meeting = book_meeting(
        lead_id=2,
        start=start_time,
        duration_minutes=30
    )
    
    assert meeting.calendar_link is not None
    assert len(meeting.calendar_link) > 0
    assert "http" in meeting.calendar_link.lower()


def test_list_meetings_returns_all_meetings():
    """Test that list_meetings returns all booked meetings."""
    # Clear and book some meetings
    meetings_list = list_meetings()
    initial_count = len(meetings_list)
    
    # Book two meetings
    meeting1 = book_meeting(lead_id=1, start=datetime(2025, 12, 17, 10, 0))
    meeting2 = book_meeting(lead_id=2, start=datetime(2025, 12, 17, 14, 0))
    
    # Get all meetings
    all_meetings = list_meetings()
    
    assert len(all_meetings) == initial_count + 2
    assert meeting1 in all_meetings
    assert meeting2 in all_meetings
