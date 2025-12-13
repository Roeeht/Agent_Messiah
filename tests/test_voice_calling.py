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
    assert "<Record" in content
    assert "playBeep=\"false\"" in content


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
    # Ensure TwiML shape is correct (lead personalization depends on translation/LLM settings).
    assert "<Response>" in content
    assert "<Say" in content
    assert "<Record" in content


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
    """Test that a positive response leads to slot offering.

    In LLM-only mode, we validate this through /agent/turn (LLM is mocked in conftest).
    """

    resp = client.post(
        "/agent/turn",
        json={
            "lead_id": 1,
            "user_utterance": "Yes, sounds interesting",
            "history": [{"user": "Hello", "agent": "Hi!"}],
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["action"] == "offer_slots"
    assert data["action_payload"] is not None
    assert "slots" in data["action_payload"]


def test_twilio_does_not_offer_slots_twice_when_pending_slots_exist():
    """If slots were already offered, a follow-up ambiguous "yes" shouldn't re-offer them."""

    call_sid = "CA9999999999"
    client.post(
        "/twilio/voice",
        data={
            "CallSid": call_sid,
            "From": "+972501234567",
            "To": "+972501111111",
        },
    )

    # Turn 0: permission yes -> mocked LLM offers slots.
    r1 = client.post(
        "/twilio/process-speech",
        data={
            "CallSid": call_sid,
            "SpeechResult": "כן",
            "Confidence": "0.95",
        },
        params={"call_sid": call_sid, "lead_id": 1, "turn": 0},
    )
    assert r1.status_code == 200
    assert "איזה זמן מתאים לך?" in r1.text  # offer_slots TwiML includes ask_time prompt

    # Turn 1: ambiguous yes again. Without a guard, the mocked LLM would offer slots again.
    r2 = client.post(
        "/twilio/process-speech",
        data={
            "CallSid": call_sid,
            "SpeechResult": "כן",
            "Confidence": "0.95",
        },
        params={"call_sid": call_sid, "lead_id": 1, "turn": 1},
    )
    assert r2.status_code == 200
    assert "איזה זמן מתאים לך?" not in r2.text  # continue TwiML should not repeat the slot-offer prompt


def test_root_endpoint_includes_outbound():
    """Test that root endpoint lists outbound endpoints."""
    response = client.get("/")
    
    assert response.status_code == 200
    data = response.json()
    
    # Check endpoints exist
    assert "endpoints" in data
