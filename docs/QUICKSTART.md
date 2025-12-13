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
    "user_utterance": "שלום",
    "history": []
  }'
```

**Response:**

```json
{
  "agent_reply": "היי דוד! אני מאלטה. אנחנו עוזרים לחברות להגדיל מכירות עם סוכני AI. איך אתם מטפלים היום בלידים נכנסים?",
  "action": null,
  "action_payload": null
}
```

Note: In `AGENT_MODE=llm`, the agent reply is English-only by design. For the Hebrew caller experience, use the Twilio voice flow (the server translates HE↔EN around the LLM).

### Example 2: "Who are you?"

```bash
curl -X POST "http://127.0.0.1:8000/agent/turn" \
  -H "Content-Type: application/json" \
  -d '{
    "user_utterance": "מי אתה?",
    "history": []
  }'
```

### Example 3: "Not interested"

```bash
curl -X POST "http://127.0.0.1:8000/agent/turn" \
  -H "Content-Type: application/json" \
  -d '{
    "user_utterance": "לא מעוניין",
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
    "user_utterance": "כן, נשמע מעניין",
    "history": [
      {"user": "שלום", "agent": "היי דוד!..."}
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
        "start": "2025-12-12T10:00:00",
        "display_text": "מחר בשעה 10:00 (12/12)",
        "duration_minutes": 30
      },
      ...
    ]
  }
}
```

### Example 5: Book a Meeting

```bash
curl -X POST "http://127.0.0.1:8000/agent/turn" \
  -H "Content-Type: application/json" \
  -d '{
    "lead_id": 1,
    "user_utterance": "מחר בשעה 10 מתאים",
    "history": [
      {"user": "שלום", "agent": "היי!"},
      {"user": "כן נשמע מעניין", "agent": "נשמח לקבוע פגישה..."}
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

## Manual Testing Script

For interactive testing (requires server to be running):

```bash
python scripts/manual_test_api.py
```

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

The app works without these for basic testing!

## Project Structure

```
Agent_Messiah/
├── app/                    # Application code
│   ├── main.py            # FastAPI routes
│   ├── agent_logic.py     # Conversation logic
│   ├── models.py          # Data models
│   ├── leads_store.py     # Lead management
│   ├── calendar_store.py  # Meeting scheduling
│   └── config.py          # Configuration
├── tests/                 # Test suite (20 tests)
└── README.md             # Full documentation
```

## Next Steps

- See [README.md](../README.md) for complete documentation
- See [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) for what's been built
- See [PLANNING.md](PLANNING.md) for project planning details

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
