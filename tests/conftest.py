import pytest


@pytest.fixture(autouse=True)
def _safe_test_config(monkeypatch, request):
    """Force deterministic, offline-safe config for tests.

    The repo loads .env on import; these overrides prevent real network calls
    (OpenAI/Twilio) and reduce test flakiness.
    """
    from app.config import config, Config

    # LLM-only mode: provide a dummy OpenAI key so endpoints that require it are enabled,
    # but monkeypatch all networked functions (LLM + translation) to stay offline.
    monkeypatch.setattr(Config, "OPENAI_API_KEY", "test", raising=False)
    monkeypatch.setattr(Config, "ENABLE_TRANSLATION", True, raising=False)

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
    monkeypatch.setattr(config, "OPENAI_API_KEY", "test", raising=False)
    monkeypatch.setattr(config, "ENABLE_TRANSLATION", True, raising=False)
    monkeypatch.setattr(config, "TWILIO_ACCOUNT_SID", "", raising=False)
    monkeypatch.setattr(config, "TWILIO_AUTH_TOKEN", "", raising=False)
    monkeypatch.setattr(config, "TWILIO_CALLER_ID", "", raising=False)
    monkeypatch.setattr(config, "API_KEY", "", raising=False)
    monkeypatch.setattr(config, "DEBUG_CALL_EVENTS", False, raising=False)
    monkeypatch.setattr(config, "LOG_CALL_TRANSCRIPT", False, raising=False)

    # Offline deterministic LLM behavior for endpoint/integration tests.
    # IMPORTANT: do not patch `app.llm_agent` for `tests/test_llm_agent.py`, which
    # unit-tests the real implementation by mocking the OpenAI client.
    if "tests/test_llm_agent.py" not in request.node.nodeid:
        from app import llm_agent as llm_agent_module

        def _fake_get_initial_greeting(lead):
            name = None
            try:
                name = (lead.name.split()[0] if lead and getattr(lead, "name", None) else None)
            except Exception:
                name = None
            who = name or "there"
            return (
                f"Hi {who}! I'm the agent from Habari's Sales Copnamy. We help companies increase sales with AI agents. "
                "Is this a good time to talk? Please answer ONLY yes or no."
            )

        def _fake_decide_next_turn_llm(*, lead, history, last_user_utterance):
            text = (last_user_utterance or "").strip().lower()
            if "who are you" in text:
                return (
                    "I'm Messiah, an AI agent from Habari's Sales Copnamy. We help sales teams increase sales with AI agents.",
                    None,
                    None,
                )
            if "not interested" in text or text in {"no", "nope"}:
                return (
                    "No problem. If you change your mind, feel free to reach out. Goodbye.",
                    "end_call",
                    {"reason": "Not interested"},
                )
            if "yes" in text or "sounds interesting" in text:
                return (
                    "Great. I can offer a quick intro call. Does tomorrow 10:00 or Thursday 14:00 work?",
                    "offer_slots",
                    {
                        "slots": [
                            {"start": "2030-01-01T10:00:00", "display_text": "tomorrow 10:00", "duration_minutes": 30},
                            {"start": "2030-01-03T14:00:00", "display_text": "Thursday 14:00", "duration_minutes": 30},
                        ]
                    },
                )
            return ("Thanks. How do you handle inbound leads today?", None, None)

        monkeypatch.setattr(llm_agent_module, "get_initial_greeting", _fake_get_initial_greeting, raising=True)
        monkeypatch.setattr(llm_agent_module, "decide_next_turn_llm", _fake_decide_next_turn_llm, raising=True)

    # Offline deterministic translation.
    from app.language import translator as translator_module
    from app.language.caller_he import get_caller_text

    monkeypatch.setattr(
        translator_module,
        "translate_en_to_he",
        lambda _: get_caller_text("permission_ask"),
        raising=True,
    )
    monkeypatch.setattr(
        translator_module,
        "translate_he_to_en",
        lambda t: "yes" if "כן" in (t or "") else ("no" if "לא" in (t or "") else "hello"),
        raising=True,
    )

    return config
