"""Tests for agent logic."""

import pytest
from app.agent_logic import decide_next_turn
from app.models import Lead


def test_who_are_you_question():
    """Test that agent responds to 'who are you' question with Alta explanation."""
    # Create a test lead
    lead = Lead(
        id=1,
        name="Test User",
        company="Test Corp",
        role="CEO",
        phone="+972501234567"
    )
    
    # Ask "who are you" in Hebrew
    agent_reply, action, action_payload = decide_next_turn(
        lead=lead,
        history=[],
        last_user_utterance="מי אתה?"
    )
    
    # Check that response mentions Alta
    assert "אלטה" in agent_reply or "Alta" in agent_reply
    assert "AI" in agent_reply or "סוכני" in agent_reply
    assert action is None  # No special action for explanation


def test_not_interested_response():
    """Test that agent handles 'not interested' and ends call."""
    lead = Lead(
        id=1,
        name="Test User",
        company="Test Corp",
        role="CEO",
        phone="+972501234567"
    )
    
    # Say "not interested" in Hebrew
    agent_reply, action, action_payload = decide_next_turn(
        lead=lead,
        history=[
            {"user": "שלום", "agent": "היי! אני מאלטה..."}
        ],
        last_user_utterance="לא מעוניין"
    )
    
    # Check that action is to end call
    assert action == "end_call"
    assert "תודה" in agent_reply or "אוקי" in agent_reply


def test_greeting_flow():
    """Test initial greeting includes Alta pitch."""
    lead = Lead(
        id=1,
        name="דוד כהן",
        company="Test Corp",
        role="CEO",
        phone="+972501234567"
    )
    
    # First interaction
    agent_reply, action, action_payload = decide_next_turn(
        lead=lead,
        history=[],
        last_user_utterance="שלום"
    )
    
    # Should greet and ask about lead handling
    assert "דוד" in agent_reply or "היי" in agent_reply
    assert "אלטה" in agent_reply
    assert action is None


def test_positive_flow_offers_slots():
    """Test that positive responses lead to slot offering."""
    lead = Lead(
        id=1,
        name="Test User",
        company="Test Corp",
        role="CEO",
        phone="+972501234567"
    )
    
    # Simulate a positive conversation
    history = [
        {"user": "שלום", "agent": "היי! אני מאלטה..."},
        {"user": "יש לנו SDR", "agent": "מעניין. יש לכם צוות SDR?"}
    ]
    
    agent_reply, action, action_payload = decide_next_turn(
        lead=lead,
        history=history,
        last_user_utterance="כן, נשמע מעניין"
    )
    
    # Should offer meeting slots
    assert action == "offer_slots"
    assert action_payload is not None
    assert "slots" in action_payload
    assert len(action_payload["slots"]) >= 1


def test_slot_selection_books_meeting():
    """Test that selecting a slot books a meeting."""
    lead = Lead(
        id=1,
        name="Test User",
        company="Test Corp",
        role="CEO",
        phone="+972501234567"
    )
    
    # Simulate conversation at slot offering stage
    history = [
        {"user": "שלום", "agent": "היי! אני מאלטה..."},
        {"user": "יש לנו SDR", "agent": "מעניין. יש לכם צוות SDR?"},
        {"user": "כן, נשמע מעניין", "agent": "נשמע מצוין! אשמח לקבוע שיחת היכרות..."}
    ]
    
    agent_reply, action, action_payload = decide_next_turn(
        lead=lead,
        history=history,
        last_user_utterance="מחר בשעה 10 מתאים"
    )
    
    # Should book the meeting
    assert action == "book_meeting"
    assert action_payload is not None
    assert "meeting_id" in action_payload
    assert "קבעתי" in agent_reply or "מעולה" in agent_reply
