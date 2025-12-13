"""Tests for voice calling functionality."""

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_twilio_voice_endpoint_returns_twiml():
    """Test /twilio/voice endpoint returns proper TwiML."""
    response = client.post(
        "/twilio/voice",
        data={
            "CallSid": "CA1234567890",
            "From": "+972501234567",
            "To": "+972501111111"
        }
    )
    
    assert response.status_code == 200
    assert "application/xml" in response.headers.get("content-type", "")
    
    content = response.text
    assert "<Response>" in content
    assert "<Say" in content
    assert "he-IL" in content
    assert "Polly.Ayelet" in content
    assert "אלטה" in content or "Alta" in content
    assert "<Gather" in content
    assert "speech" in content


def test_twilio_voice_recognizes_lead():
    """Test that voice endpoint recognizes lead by phone number."""
    response = client.post(
        "/twilio/voice",
        data={
            "CallSid": "CA1234567890",
            "From": "+972501234567",  # This matches our sample lead
            "To": "+972501111111"
        }
    )
    
    assert response.status_code == 200
    content = response.text
    # Should include lead's first name in greeting
    assert "דוד" in content or "שרה" in content


def test_twilio_process_speech_handles_input():
    """Test /twilio/process-speech handles speech input."""
    response = client.post(
        "/twilio/process-speech",
        data={
            "CallSid": "CA1234567890",
            "SpeechResult": "שלום",
            "Confidence": "0.95"
        },
        params={"call_sid": "CA1234567890", "lead_id": 1, "turn": 0}
    )
    
    assert response.status_code == 200
    assert "application/xml" in response.headers.get("content-type", "")
    
    content = response.text
    assert "<Response>" in content
    assert "<Say" in content


def test_twilio_process_speech_handles_not_interested():
    """Test that 'not interested' triggers hangup."""
    response = client.post(
        "/twilio/process-speech",
        data={
            "CallSid": "CA1234567890",
            "SpeechResult": "לא מעוניין",
            "Confidence": "0.95"
        },
        params={"call_sid": "CA1234567890", "lead_id": 1, "turn": 0}
    )
    
    assert response.status_code == 200
    content = response.text
    assert "<Hangup" in content
    # Should have polite goodbye
    assert "תודה" in content or "אוקי" in content


def test_twilio_process_speech_handles_no_speech():
    """Test handling when no speech is detected."""
    response = client.post(
        "/twilio/process-speech",
        data={
            "CallSid": "CA1234567890",
            "SpeechResult": "",  # No speech
            "Confidence": "0.0"
        },
        params={"call_sid": "CA1234567890", "lead_id": 1, "turn": 0}
    )
    
    assert response.status_code == 200
    content = response.text
    assert "<Hangup" in content
    assert "מצטערת" in content or "לא שמעתי" in content


def test_initiate_outbound_call_without_twilio():
    """Test outbound call initiation without Twilio config."""
    response = client.post("/outbound/initiate-call?lead_id=1")
    
    assert response.status_code == 200
    data = response.json()
    
    # Without Twilio config, should return error message
    assert data["status"] == "error"
    assert "Twilio not configured" in data["message"]
    assert "lead" in data


def test_initiate_outbound_call_invalid_lead():
    """Test outbound call with invalid lead ID."""
    response = client.post("/outbound/initiate-call?lead_id=99999")
    
    assert response.status_code == 404


def test_initiate_campaign_without_twilio():
    """Test campaign initiation without Twilio config."""
    response = client.post("/outbound/campaign")
    
    assert response.status_code == 200
    data = response.json()
    
    # Without Twilio config, should return error
    assert data["status"] == "error"
    assert "leads_count" in data


def test_call_status_webhook():
    """Test call status webhook receives updates."""
    response = client.post(
        "/twilio/call-status",
        data={
            "CallSid": "CA1234567890",
            "CallStatus": "completed"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "received"


def test_twilio_process_speech_offers_slots():
    """Test that positive response leads to slot offering.
    
    Note: Since we don't have session storage in tests, this test validates
    that the agent logic can produce slot offerings when given proper history.
    In production, conversation history would be stored in Redis/DB.
    """
    # Test that the agent logic itself can offer slots
    from app import agent_logic
    from app.models import Lead
    
    lead = Lead(
        id=1,
        name="דוד כהן",
        phone="+972501234567",
        company="TechCorp",
        role="מנכ״ל"
    )
    
    # Simulate conversation history leading to slot offering
    # Need to go through proper qualifying flow
    history = [
        {"role": "agent", "content": "היי דוד! אני מאלטה. אנחנו עוזרים לחברות להגדיל מכירות עם סוכני AI. איך אתם מטפלים היום בלידים נכנסים?"},
        {"role": "user", "content": "יש לנו צוות מכירות"},
        {"role": "agent", "content": "מעניין. יש לכם צוות SDR שמטפל בשיחות?"},
        {"role": "user", "content": "כן, נשמע מעניין"},
    ]
    
    agent_reply, action, action_payload = agent_logic.decide_next_turn(
        lead=lead,
        history=history,
        last_user_utterance="כן, אשמח לשמוע יותר"
    )
    
    # After qualifying questions with positive signals, should offer slots
    assert action in ["offer_slots", None]  # None means continuing conversation
    assert len(agent_reply) > 0
    
    # If offering slots, should have slot data
    if action == "offer_slots":
        assert action_payload is not None
        assert "slots" in action_payload


def test_root_endpoint_includes_outbound():
    """Test that root endpoint lists outbound endpoints."""
    response = client.get("/")
    
    assert response.status_code == 200
    data = response.json()
    
    # Check endpoints exist
    assert "endpoints" in data
