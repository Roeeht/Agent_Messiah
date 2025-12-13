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
    
    # Ask "who are you" in English (rule-based agent is English-only)
    agent_reply, action, action_payload = decide_next_turn(
        lead=lead,
        history=[],
        last_user_utterance="Who are you?"
    )
    
    # Check that response mentions Alta
    assert "Alta" in agent_reply
    assert "AI" in agent_reply
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
    
    # Say "not interested" in English
    agent_reply, action, action_payload = decide_next_turn(
        lead=lead,
        history=[
            {"user": "Hello", "agent": "Hi! I'm from Alta..."}
        ],
        last_user_utterance="Not interested"
    )
    
    # Check that action is to end call
    assert action == "end_call"
    assert "thanks" in agent_reply.lower() or "understand" in agent_reply.lower()


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
        last_user_utterance="Hello"
    )
    
    # Should greet and ask about lead handling
    assert "דוד" in agent_reply or "hi" in agent_reply.lower()
    assert "Alta" in agent_reply
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
        {"user": "Hello", "agent": "Hi! I'm from Alta..."},
        {"user": "We have SDR", "agent": "Interesting. Do you have an SDR team that handles calls?"}
    ]
    
    agent_reply, action, action_payload = decide_next_turn(
        lead=lead,
        history=history,
        last_user_utterance="Yes, sounds interesting"
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
        {"user": "Hello", "agent": "Hi! I'm from Alta..."},
        {"user": "We have SDR", "agent": "Interesting. Do you have an SDR team that handles calls?"},
        {"user": "Yes", "agent": "Sounds great! I'd be happy to schedule a brief introduction call. I have availability tomorrow 10:00 or Thursday 14:00. What works for you?"}
    ]
    
    agent_reply, action, action_payload = decide_next_turn(
        lead=lead,
        history=history,
        last_user_utterance="Tomorrow at 10 works"
    )
    
    # Should book the meeting
    assert action == "book_meeting"
    assert action_payload is not None
    assert "meeting_id" in action_payload
    assert "scheduled" in agent_reply.lower() or "meeting" in agent_reply.lower()
