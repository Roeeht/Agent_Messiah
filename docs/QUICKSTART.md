# 🚀 Quick Start Guide - Agent Messiah

## Installation (1 minute)

```bash
# 1. Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt
```

## Run Tests (10 seconds)

```bash
pytest -v
# ✅ Test suite should pass
```

## Start Server (5 seconds)

```bash
uvicorn app.main:app --reload
```

Server will start at: `http://127.0.0.1:8000`

- API Docs: `http://127.0.0.1:8000/docs`
- Alternative Docs: `http://127.0.0.1:8000/redoc`

## Test the API

### Example 1: Basic Greeting

```bash
curl -X POST "http://127.0.0.1:8000/agent/turn" \
  -H "Content-Type: application/json" \
  -d '{
    "lead_id": 1,
    "user_utterance": "Hello",
    "history": []
  }'
```

**Response:**

```json
{
  "agent_reply": "Hi Roy! I'm the agent from Alta. We help companies increase sales with AI agents. Is this a good time to talk? Please answer ONLY yes or no.",
  "action": null,
  "action_payload": null
}
```

Note: `/agent/turn` is English-only by design. For the Hebrew caller experience, use the Twilio voice flow (the server translates HE↔EN around the LLM).

### Example 2: "Who are you?"

```bash
curl -X POST "http://127.0.0.1:8000/agent/turn" \
  -H "Content-Type: application/json" \
  -d '{
    "user_utterance": "Who are you?",
    "history": []
  }'
```

### Example 3: "Not interested"

```bash
curl -X POST "http://127.0.0.1:8000/agent/turn" \
  -H "Content-Type: application/json" \
  -d '{
    "user_utterance": "Not interested",
    "history": []
  }'
```

**Response includes:** `"action": "end_call"`

### Example 4: Positive Flow (Get Meeting Slots)

```bash
curl -X POST "http://127.0.0.1:8000/agent/turn" \
  -H "Content-Type: application/json" \
  -d '{
    "lead_id": 1,
    "user_utterance": "Yes, sounds interesting",
    "history": [
      {"user": "Hello", "agent": "Hi Roy!..."}
    ]
  }'
```

**Response includes:**

```json
{
  "action": "offer_slots",
  "action_payload": {
    "slots": [
      {
        "start": "2030-01-01T10:00:00",
        "display_text": "... (caller-facing display text)",
        "duration_minutes": 30
      },
      ...
    ]
  }
}
```

Note: slot `display_text` is caller-facing and may be Hebrew.

### Example 5: Book a Meeting

```bash
curl -X POST "http://127.0.0.1:8000/agent/turn" \
  -H "Content-Type: application/json" \
  -d '{
    "lead_id": 1,
    "user_utterance": "Tomorrow at 10 works",
    "history": [
      {"user": "Hello", "agent": "Hi!"},
      {"user": "Yes, sounds interesting", "agent": "Great. ..."}
    ]
  }'
```

**Response includes:** `"action": "book_meeting"`

## Other Endpoints

### List all leads

```bash
curl http://127.0.0.1:8000/leads
```

### List all meetings

```bash
curl http://127.0.0.1:8000/meetings
```

### Twilio webhook (returns TwiML)

```bash
curl -X POST http://127.0.0.1:8000/twilio/voice
```

Note: this curl test hits your local server directly. For a real phone call via Twilio, your server must be reachable from the public internet (use ngrok and set `BASE_URL`). See `docs/VOICE_CALLING_GUIDE.md`.

## Using the Interactive API Docs

1. Start the server: `uvicorn app.main:app --reload`
2. Open browser: `http://127.0.0.1:8000/docs`
3. Click "Try it out" on any endpoint
4. Fill in the request body
5. Click "Execute"

## Environment Variables (Optional)

For LLM or Twilio integration:

```bash
# Copy the example file
cp .env.example .env

# Edit .env with your keys
OPENAI_API_KEY=sk-...
TWILIO_ACCOUNT_SID=AC...
TWILIO_AUTH_TOKEN=...
TWILIO_CALLER_ID=+1234567890
```

The server can start without these, but health endpoints are the only thing that will work without OpenAI.

Note: `/agent/turn` and the Twilio voice flow require OpenAI.

## Project Structure

```
Agent_Messiah/
├── app/                    # Application code
│   ├── main.py            # FastAPI routes
│   ├── routers/           # Route modules (core/agent/outbound/twilio)
│   ├── models.py          # Data models
│   ├── leads_store.py     # Lead management
│   ├── calendar_store.py  # Meeting scheduling
│   └── config.py          # Configuration
├── tests/                 # Test suite (20 tests)
└── README.md             # Full documentation
```

## Next Steps

- See [README.md](../README.md) for complete documentation

- For real outbound phone calls with Twilio (requires ngrok): see [VOICE_CALLING_GUIDE.md](VOICE_CALLING_GUIDE.md)

## Troubleshooting

**Import errors in tests?**

- Make sure you're in the virtual environment: `source venv/bin/activate`
- pytest is installed: `pip install pytest`

**Server won't start?**

- Check if port 8000 is available
- Try a different port: `uvicorn app.main:app --port 8001`

**Tests fail?**

- Make sure you're in the project root directory
- Run: `pytest -v` to see detailed output

---

**Ready to demo!** 🎉
