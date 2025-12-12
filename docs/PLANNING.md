# Project goal

Build a small demo of a **Hebrew speaking AI outbound calling agent** for Alta's "AI Solution Engineer" home assignment.

The agent's purpose:

- Call B2B leads in Israel (prototype can work with simulated calls or Twilio test calls).
- Speak in natural Israeli Hebrew.
- Pitch Alta's value proposition in 1 to 3 short sentences.
- Ask a few qualifying questions.
- Try to book a short intro meeting with a sales rep.
- Log the outcome of the call and any booked meeting.

It is totally fine if the telephony part is minimal or partially mocked, but the **agent logic and API design must be clear and working**.

---

## Non goals

- No need for a production ready system.
- No need for advanced frontends or dashboards. A simple HTML page or just API endpoints plus README is enough.
- No need for real CRM integration. We can simulate leads in a local database or in memory.

---

## Tech stack

Use these technologies unless there is a strong reason not to:

- Backend: **Python + FastAPI**
- Data: in memory lists or SQLite, with a simple repository layer so it is easy to swap later
- LLM usage: design as if we use an OpenAI compatible client, but keep the call in a separate module so it can be stubbed or mocked
- Optional telephony: **Twilio Programmable Voice** integration for outbound calls. If time is short, build a minimal version that hits our backend and uses static TwiML, and clearly mark missing pieces in comments.

---

## High level architecture

Please implement this structure:

```text
.
├── app/
│   ├── main.py                 # FastAPI app and routes
│   ├── models.py               # Pydantic models and DB models (if using SQLite)
│   ├── agent_logic.py          # Conversation logic and LLM integration
│   ├── calendar_store.py       # Simple "calendar" abstraction for meeting slots and bookings
│   ├── leads_store.py          # Simple lead store with fake data
│   ├── telemetry.py            # Logging helpers (call outcome, transcripts, etc)
│   ├── twilio_webhooks.py      # Optional Twilio webhooks and helpers for voice calls
│   └── config.py               # Settings, env vars (API keys, Twilio config, etc)
├── tests/
│   ├── test_agent_logic.py
│   ├── test_calendar_store.py
│   └── test_api_routes.py
├── requirements.txt
└── README.md
```
