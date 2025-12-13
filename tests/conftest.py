import pytest


@pytest.fixture(autouse=True)
def _safe_test_config(monkeypatch):
    """Force deterministic, offline-safe config for tests.

    The repo loads .env on import; these overrides prevent real network calls
    (OpenAI/Twilio) and reduce test flakiness.
    """
    from app.config import config, Config

    # Disable OpenAI usage in API endpoints by default.
    monkeypatch.setattr(Config, "OPENAI_API_KEY", "", raising=False)
    monkeypatch.setattr(Config, "AGENT_MODE", "rule", raising=False)
    monkeypatch.setattr(Config, "ENABLE_TRANSLATION", False, raising=False)

    # Disable Twilio credentials so outbound endpoints follow the "not configured" path
    # unless a test explicitly overrides.
    monkeypatch.setattr(Config, "TWILIO_ACCOUNT_SID", "", raising=False)
    monkeypatch.setattr(Config, "TWILIO_AUTH_TOKEN", "", raising=False)
    monkeypatch.setattr(Config, "TWILIO_CALLER_ID", "", raising=False)

    # Keep debug endpoints accessible in tests unless a test opts out.
    monkeypatch.setattr(Config, "API_KEY", "", raising=False)

    # Keep debug events disabled by default (tests that need it will enable).
    monkeypatch.setattr(Config, "DEBUG_CALL_EVENTS", False, raising=False)

    # Avoid transcript spam in test output.
    monkeypatch.setattr(Config, "LOG_CALL_TRANSCRIPT", False, raising=False)

    # Keep the instance in sync for any code that reads instance attributes directly.
    monkeypatch.setattr(config, "OPENAI_API_KEY", "", raising=False)
    monkeypatch.setattr(config, "AGENT_MODE", "rule", raising=False)
    monkeypatch.setattr(config, "ENABLE_TRANSLATION", False, raising=False)
    monkeypatch.setattr(config, "TWILIO_ACCOUNT_SID", "", raising=False)
    monkeypatch.setattr(config, "TWILIO_AUTH_TOKEN", "", raising=False)
    monkeypatch.setattr(config, "TWILIO_CALLER_ID", "", raising=False)
    monkeypatch.setattr(config, "API_KEY", "", raising=False)
    monkeypatch.setattr(config, "DEBUG_CALL_EVENTS", False, raising=False)
    monkeypatch.setattr(config, "LOG_CALL_TRANSCRIPT", False, raising=False)

    return config
