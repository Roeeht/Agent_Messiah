"""Audio transcription helpers (Twilio Recording -> Hebrew text).

Used as a fallback when Twilio <Gather input="speech"> misrecognizes Hebrew.

Flow:
- Twilio <Record> posts RecordingUrl/RecordingSid to our webhook
- We download the audio from Twilio using HTTP basic auth
- We transcribe it using OpenAI audio transcription
"""

from __future__ import annotations

from typing import Tuple

import httpx

from app.config import config


def _normalize_twilio_recording_media_url(recording_url: str) -> str:
    url = (recording_url or "").strip()
    if not url:
        return ""

    # Twilio often sends RecordingUrl without extension.
    lowered = url.lower()
    if lowered.endswith(".wav") or lowered.endswith(".mp3") or lowered.endswith(".m4a"):
        return url

    return url + ".wav"


def _candidate_twilio_recording_media_urls(recording_url: str) -> list[str]:
    url = (recording_url or "").strip()
    if not url:
        return []

    lowered = url.lower()
    if lowered.endswith((".wav", ".mp3", ".m4a")):
        return [url]

    # Twilio often sends RecordingUrl without extension.
    return [url + ".wav", url + ".mp3", url + ".m4a"]


def _get_openai_client():
    from openai import OpenAI

    return OpenAI(api_key=config.OPENAI_API_KEY)


def transcribe_audio_to_hebrew(
    audio_bytes: bytes,
    *,
    filename: str = "recording.wav",
    mime_type: str = "audio/wav",
) -> str:
    """Transcribe audio bytes to Hebrew text using OpenAI.

    Returns empty string on failure.
    """
    if not audio_bytes:
        return ""

    if not config.has_openai_key():
        return ""

    try:
        client = _get_openai_client()
        # The OpenAI python client accepts a (filename, bytes, mime) tuple.
        result = client.audio.transcriptions.create(
            model=getattr(config, "OPENAI_TRANSCRIBE_MODEL", "gpt-4o-mini-transcribe"),
            file=(filename, audio_bytes, mime_type),
            language="he",
        )

        # The SDK returns an object with `.text`.
        text = getattr(result, "text", None)
        if isinstance(text, str):
            return text.strip()

        # Extra robustness: handle dict-like responses.
        if isinstance(result, dict) and isinstance(result.get("text"), str):
            return result["text"].strip()

        return ""
    except Exception:
        return ""


def fetch_twilio_recording_bytes(recording_url: str, timeout_s: float = 20.0) -> Tuple[bytes, str]:
    """Download recording audio from Twilio.

    Returns: (audio_bytes, resolved_media_url)
    """
    candidates = _candidate_twilio_recording_media_urls(recording_url)
    if not candidates:
        return b"", ""

    if not config.has_twilio_auth():
        return b"", candidates[0]

    try:
        with httpx.Client(timeout=timeout_s, follow_redirects=True) as client:
            last_url = candidates[0]
            for media_url in candidates:
                last_url = media_url
                resp = client.get(
                    media_url,
                    auth=(config.TWILIO_ACCOUNT_SID, config.TWILIO_AUTH_TOKEN),
                    headers={"Accept": "audio/*;q=0.9,*/*;q=0.1"},
                )
                if resp.status_code >= 400:
                    continue
                resp.raise_for_status()
                if resp.content:
                    return resp.content, media_url
            return b"", last_url
    except Exception:
        return b"", candidates[0]


def transcribe_twilio_recording_url_to_hebrew(recording_url: str) -> Tuple[str, str]:
    """Fetch a Twilio recording and transcribe it to Hebrew.

    Returns: (hebrew_text, resolved_media_url)
    """
    audio_bytes, media_url = fetch_twilio_recording_bytes(recording_url)
    if not audio_bytes:
        return "", media_url

    filename = "recording.wav"
    mime_type = "audio/wav"
    lowered = (media_url or "").lower()
    if lowered.endswith(".mp3"):
        filename = "recording.mp3"
        mime_type = "audio/mpeg"
    elif lowered.endswith(".m4a"):
        filename = "recording.m4a"
        mime_type = "audio/mp4"

    text = transcribe_audio_to_hebrew(audio_bytes, filename=filename, mime_type=mime_type)
    return text, media_url
