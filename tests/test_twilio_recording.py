from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_twilio_process_recording_hangup_on_end_call(monkeypatch):
    """Recording webhook should return hangup TwiML when agent ends call."""
    # Make transcription deterministic and offline.
    # Returning a not-interested phrase triggers the fast-path hangup.
    monkeypatch.setattr(
        "app.language.audio_transcriber.transcribe_twilio_recording_url_to_hebrew",
        lambda url: ("לא מעוניין", url),
    )

    resp = client.post(
        "/twilio/process-recording",
        params={"call_sid": "CA_TEST", "lead_id": 1, "turn": 0},
        data={
            "CallSid": "CA_TEST",
            "RecordingUrl": "https://example.twilio.com/recordings/RE123",
            "RecordingSid": "RE123",
            "RecordingDuration": "2",
        },
    )

    assert resp.status_code == 200
    assert "application/xml" in resp.headers.get("content-type", "")
    assert "<Response>" in resp.text
    assert "<Hangup" in resp.text


def test_twilio_debug_disabled_by_default():
    resp = client.get("/twilio/debug/CA_TEST")
    assert resp.status_code in (404, 403)


def test_twilio_debug_enabled(monkeypatch):
    from app.config import config

    monkeypatch.setattr(config, "DEBUG_CALL_EVENTS", True, raising=False)

    # Seed a couple of events.
    from app.redis_client import SessionManager

    call_sid = "CA_DEBUG"
    SessionManager.save_session(call_sid, {"lead_id": 1, "conversation_history": [], "idempotency": {}, "debug_events": []})
    SessionManager.append_debug_event(call_sid, "transcript_turn", {"turn": 0, "role": "assistant", "content": "שלום"})
    SessionManager.append_debug_event(call_sid, "transcript_turn", {"turn": 0, "role": "user", "content": "היי"})

    resp = client.get(f"/twilio/debug/{call_sid}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["call_sid"] == call_sid
    assert "transcript" in data
    assert data["transcript"]["lead_said"] == ["היי"]
    assert data["transcript"]["agent_said"] == ["שלום"]
