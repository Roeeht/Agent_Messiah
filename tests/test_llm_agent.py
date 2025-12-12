"""
Tests for LLM-based agent conversations.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from app import llm_agent
from app.models import Lead


@pytest.fixture
def sample_lead():
    """Create a sample lead for testing."""
    return Lead(
        id=1,
        name="דוד כהן",
        phone="+972501234567",
        company="TechCorp",
        role="מנכ\"ל",
        notes="Interested in AI solutions"
    )


def test_llm_agent_imports():
    """Test that LLM agent module imports correctly."""
    assert hasattr(llm_agent, 'decide_next_turn_llm')
    assert hasattr(llm_agent, 'get_initial_greeting')
    assert hasattr(llm_agent, 'SYSTEM_PROMPT')
    assert hasattr(llm_agent, 'FUNCTIONS')


def test_system_prompt_contains_key_info():
    """Test that system prompt contains essential information."""
    prompt = llm_agent.SYSTEM_PROMPT
    
    # Check for key elements
    assert "Alta" in prompt
    assert "AI" in prompt or "סוכן" in prompt
    assert "עברית" in prompt or "ישראלית" in prompt
    assert "פגישה" in prompt
    

def test_functions_defined():
    """Test that all required functions are defined."""
    function_names = [f["name"] for f in llm_agent.FUNCTIONS]
    
    assert "offer_meeting_slots" in function_names
    assert "book_meeting" in function_names
    assert "end_call" in function_names


@patch('app.llm_agent.client')
def test_decide_next_turn_llm_basic_conversation(mock_client, sample_lead):
    """Test basic conversation flow with LLM."""
    # Mock OpenAI response
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "שלום! איך אפשר לעזור לך?"
    mock_response.choices[0].message.function_call = None
    
    mock_client.chat.completions.create.return_value = mock_response
    
    # Test conversation
    history = []
    user_input = "שלום"
    
    agent_reply, action, payload = llm_agent.decide_next_turn_llm(
        lead=sample_lead,
        history=history,
        last_user_utterance=user_input
    )
    
    # Verify response
    assert isinstance(agent_reply, str)
    assert len(agent_reply) > 0
    assert action is None  # No function call in this response


@patch('app.llm_agent.client')
def test_decide_next_turn_llm_offer_slots(mock_client, sample_lead):
    """Test LLM offering meeting slots."""
    # Mock OpenAI response with function call
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = None
    mock_response.choices[0].message.function_call = MagicMock()
    mock_response.choices[0].message.function_call.name = "offer_meeting_slots"
    mock_response.choices[0].message.function_call.arguments = '{"reason": "Lead showed strong interest"}'
    
    mock_client.chat.completions.create.return_value = mock_response
    
    # Test with positive history
    history = [
        {"role": "assistant", "content": "היי דוד! אני מאלטה..."},
        {"role": "user", "content": "כן, נשמע מעניין מאוד"}
    ]
    
    agent_reply, action, payload = llm_agent.decide_next_turn_llm(
        lead=sample_lead,
        history=history,
        last_user_utterance="אשמח לשמוע יותר"
    )
    
    # Verify slot offering
    assert action == "offer_slots"
    assert payload is not None
    assert "slots" in payload
    assert len(payload["slots"]) > 0
    assert "10:00" in agent_reply or "14:00" in agent_reply


@patch('app.llm_agent.client')
def test_decide_next_turn_llm_book_meeting(mock_client, sample_lead):
    """Test LLM booking a meeting."""
    # Mock OpenAI response with book_meeting function call
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = None
    mock_response.choices[0].message.function_call = MagicMock()
    mock_response.choices[0].message.function_call.name = "book_meeting"
    mock_response.choices[0].message.function_call.arguments = '{"slot_index": 0, "confirmation": "מחר בעשר"}'
    
    mock_client.chat.completions.create.return_value = mock_response
    
    history = [
        {"role": "assistant", "content": "יש לי זמינות מחר ב-10:00 או ביום חמישי ב-14:00"},
        {"role": "user", "content": "מחר בעשר"}
    ]
    
    agent_reply, action, payload = llm_agent.decide_next_turn_llm(
        lead=sample_lead,
        history=history,
        last_user_utterance="מחר בעשר"
    )
    
    # Verify meeting booking
    assert action == "book_meeting"
    assert payload is not None
    assert "meeting_id" in payload
    assert "calendar_link" in payload
    assert "קבעתי" in agent_reply or "פגישה" in agent_reply


@patch('app.llm_agent.client')
def test_decide_next_turn_llm_end_call(mock_client, sample_lead):
    """Test LLM ending call gracefully."""
    # Mock OpenAI response with end_call function
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = None
    mock_response.choices[0].message.function_call = MagicMock()
    mock_response.choices[0].message.function_call.name = "end_call"
    mock_response.choices[0].message.function_call.arguments = '{"reason": "Not interested"}'
    
    mock_client.chat.completions.create.return_value = mock_response
    
    history = []
    
    agent_reply, action, payload = llm_agent.decide_next_turn_llm(
        lead=sample_lead,
        history=history,
        last_user_utterance="לא מעוניין"
    )
    
    # Verify call ending
    assert action == "end_call"
    assert payload is not None
    assert "reason" in payload
    assert "מבין" in agent_reply or "טוב" in agent_reply


@patch('app.llm_agent.client')
def test_get_initial_greeting_with_lead(mock_client, sample_lead):
    """Test generating personalized greeting."""
    # Mock OpenAI response
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "שלום דוד! אני הסוכן מAlta. איך אפשר לעזור?"
    
    mock_client.chat.completions.create.return_value = mock_response
    
    greeting = llm_agent.get_initial_greeting(sample_lead)
    
    # Verify greeting
    assert isinstance(greeting, str)
    assert len(greeting) > 0
    # Should be personalized
    assert "דוד" in greeting or "Alta" in greeting.lower()


def test_get_initial_greeting_without_lead():
    """Test generic greeting when no lead provided."""
    greeting = llm_agent.get_initial_greeting(None)
    
    # Verify generic greeting
    assert isinstance(greeting, str)
    assert len(greeting) > 0
    assert "Alta" in greeting or "אלטה" in greeting


@patch('app.llm_agent.client')
def test_decide_next_turn_llm_error_handling(mock_client, sample_lead):
    """Test error handling when OpenAI API fails."""
    # Mock API error
    mock_client.chat.completions.create.side_effect = Exception("API Error")
    
    history = []
    
    agent_reply, action, payload = llm_agent.decide_next_turn_llm(
        lead=sample_lead,
        history=history,
        last_user_utterance="שלום"
    )
    
    # Verify fallback response
    assert isinstance(agent_reply, str)
    assert len(agent_reply) > 0
    assert action is None
    # Should contain error recovery message
    assert "בעיה" in agent_reply or "מצטער" in agent_reply


@patch('app.llm_agent.client')
def test_conversation_context_passed_to_openai(mock_client, sample_lead):
    """Test that conversation history is properly passed to OpenAI."""
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "כמובן!"
    mock_response.choices[0].message.function_call = None
    
    mock_client.chat.completions.create.return_value = mock_response
    
    # Provide conversation history
    history = [
        {"role": "assistant", "content": "היי! אני מאלטה"},
        {"role": "user", "content": "מה אתם מציעים?"},
        {"role": "assistant", "content": "אנחנו מציעים פתרונות AI"}
    ]
    
    llm_agent.decide_next_turn_llm(
        lead=sample_lead,
        history=history,
        last_user_utterance="נשמע מעניין"
    )
    
    # Verify OpenAI was called with history
    call_args = mock_client.chat.completions.create.call_args
    messages = call_args.kwargs['messages']
    
    # Should have system prompt + context + history + current message
    assert len(messages) >= len(history) + 2  # system + lead context + history + current
    
    # Verify lead context was added
    lead_context_found = any("דוד כהן" in str(msg) for msg in messages)
    assert lead_context_found
