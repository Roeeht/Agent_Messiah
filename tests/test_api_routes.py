"""Tests for API routes."""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_root_endpoint():
    """Test root endpoint returns API info."""
    response = client.get("/")
    assert response.status_code == 200
    
    data = response.json()
    assert "message" in data
    assert "endpoints" in data


def test_agent_turn_basic_request():
    """Test /agent/turn endpoint with basic request."""
    response = client.post(
        "/agent/turn",
        json={
            "lead_id": 1,
            "user_utterance": "שלום",
            "history": []
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert "agent_reply" in data
    assert isinstance(data["agent_reply"], str)
    assert len(data["agent_reply"]) > 0
    
    # Optional fields
    assert "action" in data
    assert "action_payload" in data


def test_agent_turn_who_are_you():
    """Test agent responds to 'who are you' question."""
    response = client.post(
        "/agent/turn",
        json={
            "lead_id": 1,
            "user_utterance": "מי אתה?",
            "history": []
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Should mention Alta
    assert "אלטה" in data["agent_reply"] or "Alta" in data["agent_reply"]
    assert data["action"] is None


def test_agent_turn_not_interested():
    """Test agent handles 'not interested' correctly."""
    response = client.post(
        "/agent/turn",
        json={
            "lead_id": 1,
            "user_utterance": "לא מעוניין",
            "history": [
                {"user": "שלום", "agent": "היי!"}
            ]
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Should end call
    assert data["action"] == "end_call"


def test_agent_turn_without_lead():
    """Test /agent/turn works without lead_id."""
    response = client.post(
        "/agent/turn",
        json={
            "user_utterance": "שלום",
            "history": []
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "agent_reply" in data


def test_agent_turn_invalid_lead():
    """Test /agent/turn with invalid lead_id."""
    response = client.post(
        "/agent/turn",
        json={
            "lead_id": 99999,
            "user_utterance": "שלום",
            "history": []
        }
    )
    
    assert response.status_code == 404


def test_list_meetings_endpoint():
    """Test /meetings endpoint."""
    response = client.get("/meetings")
    
    assert response.status_code == 200
    data = response.json()
    
    # Should return a list (might be empty initially)
    assert isinstance(data, list)


def test_list_leads_endpoint():
    """Test /leads endpoint."""
    response = client.get("/leads")
    
    assert response.status_code == 200
    data = response.json()
    
    # Should return a list with sample leads
    assert isinstance(data, list)
    assert len(data) >= 1  # We initialize with sample leads


def test_twilio_voice_endpoint():
    """Test /twilio/voice endpoint returns TwiML."""
    response = client.post("/twilio/voice")
    
    assert response.status_code == 200
    
    # Should return XML
    assert "xml" in response.headers.get("content-type", "").lower()
    
    # Check for TwiML structure
    content = response.text
    assert "<Response>" in content
    assert "<Say" in content
    assert "he-IL" in content  # Hebrew language


def test_agent_turn_positive_flow():
    """Test a positive conversation flow leading to slot offer."""
    # Initial greeting
    response1 = client.post(
        "/agent/turn",
        json={
            "lead_id": 1,
            "user_utterance": "שלום",
            "history": []
        }
    )
    assert response1.status_code == 200
    
    # Build history
    history = [
        {"user": "שלום", "agent": response1.json()["agent_reply"]}
    ]
    
    # Positive response - this triggers slot offering
    response2 = client.post(
        "/agent/turn",
        json={
            "lead_id": 1,
            "user_utterance": "כן, נשמע מעניין מאוד",
            "history": history
        }
    )
    assert response2.status_code == 200
    
    # Should offer slots at this point
    data = response2.json()
    assert data["action"] == "offer_slots"
    assert "slots" in data["action_payload"]
