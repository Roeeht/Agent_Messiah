# Getting Started with Agent Messiah

## Quick Start Guide

### Step 1: Start the Application

This project is designed to run locally with a simple FastAPI + in-memory setup (no database).

#### Local Start (Recommended)

```bash
cd Agent_Messiah

# Activate virtual environment
source venv/bin/activate

# Start the server
uvicorn app.main:app --reload
```

The server will start on **http://localhost:8000**

### Step 2: Verify It's Running

Open your browser or use curl:

```bash
# Health check
curl http://localhost:8000/health

# Should return:
# {"status":"healthy","service":"agent-messiah","version":"2.0.0"}

# System info
curl http://localhost:8000/health/info
```

### Step 3: Use Built-in Test Leads

The system comes with 2 pre-loaded test leads:

```bash
# List all leads
curl http://localhost:8000/leads

# Returns a JSON list of leads.
# (See `app/leads_store.py` for the seeded sample data.)
```

### Step 4: Test the Agent (3 Ways)

#### Way 1: Text Conversation (API Test)

If you want an interactive text chat (no manual history copying), use:

```bash
venv/bin/python scripts/text_chat.py --lead-id 1
```

Or, if your server is not on localhost:

```bash
venv/bin/python scripts/text_chat.py --base-url http://localhost:8000 --lead-id 1
```

Type `/exit` to quit.

If you see an immediate exit with no prompt, double-check you ran the exact command above (sometimes terminals accidentally paste a markdown link like `[...] (http://...)` which will fail).

```bash
# Have a conversation with the agent
curl -X POST http://localhost:8000/agent/turn \
  -H "Content-Type: application/json" \
  -d '{
    "lead_id": 1,
    "user_utterance": "Hello",
    "history": []
  }'

# The agent runs in LLM-only mode and responds in English.
# In the Twilio voice flow, caller Hebrew is handled via HE↔EN translation around the LLM.
```

#### Way 2: Actual Phone Call (Real Test!)

**Important**: Make sure ngrok is running first:

```bash
# In a separate terminal
ngrok http 8000

# Update BASE_URL in .env with the ngrok URL
# Example: BASE_URL=https://abc123.ngrok-free.app
```

Then initiate a call:

```bash
# Call lead #1
curl -X POST "http://localhost:8000/outbound/initiate-call?lead_id=1"

# Response:
# {
#   "status": "success",
#   "call_sid": "CA1234...",
#   "message": "Call initiated to +972501234567"
# }

# The agent will call the phone number and speak in Hebrew!
```

## Environment Variables Explained

Your `.env` file now has all required keys:

### ✅ Required Keys (You Have These)

```bash
OPENAI_API_KEY=sk-proj-...      # Your OpenAI key ✓
OPENAI_MODEL=gpt-4o-mini        # Model to use ✓
# LLM-only mode (no AGENT_MODE setting)

TWILIO_ACCOUNT_SID=AC...        # Your Twilio SID ✓
TWILIO_AUTH_TOKEN=e696...       # Your Twilio token ✓
TWILIO_CALLER_ID=+97233769901   # Your Israeli number ✓

BASE_URL=https://...ngrok...    # Your ngrok URL ✓
```

### ✅ Optional Keys (Added - Can Stay Empty)

```bash
LOG_LEVEL=INFO                              # Logging verbosity
API_KEY=                                    # Leave empty (optional security)
```

## Testing a Complete Flow

Here's a full example conversation:

```bash
# 1. Start the agent
uvicorn app.main:app --reload

# 2. Initial greeting
curl -X POST http://localhost:8000/agent/turn \
  -H "Content-Type: application/json" \
  -d '{
    "lead_id": 1,
    "user_utterance": "Hello",
    "history": []
  }'

# 3. Show interest
curl -X POST http://localhost:8000/agent/turn \
  -H "Content-Type: application/json" \
  -d '{
    "lead_id": 1,
    "user_utterance": "Yes, sounds interesting",
    "history": []
  }'

# Agent will offer meeting slots!

# 4. Book a meeting
curl -X POST http://localhost:8000/agent/turn \
  -H "Content-Type: application/json" \
  -d '{
    "lead_id": 1,
    "user_utterance": "האופציה הראשונה מתאימה לי",
    "history": [...]
  }'

# Agent will confirm the meeting!
```

## Common Issues & Solutions

### Issue: "ngrok command not found"

**Solution**:

```bash
brew install ngrok
ngrok config add-authtoken YOUR_TOKEN
ngrok http 8000
```

### Issue: "OpenAI API error"

**Solution**: Check your API key is valid and has credits:

- Visit https://platform.openai.com/api-keys
- Verify your key starts with `sk-proj-`
- Check billing at https://platform.openai.com/account/billing

## What Happens When You Start?

```
1. ✓ OpenAI client configured (if OPENAI_API_KEY is set)
2. ✓ Twilio client ready (if Twilio env vars are set)
3. ✓ Server listening on http://localhost:8000
4. ✓ Health checks available at /health
```

## Next Steps

1. **Test the API**: Use the curl commands above
2. **Try a phone call**: Make sure ngrok is running, then call a lead
3. **View logs**: Check the console for structured logs
4. **Monitor health**: Visit http://localhost:8000/health/info

## Need Help?

- **Check logs**: Look at the terminal where uvicorn is running
- **Health status**: `curl http://localhost:8000/health/ready`
- **List leads**: `curl http://localhost:8000/leads`
- **View meetings**: `curl http://localhost:8000/meetings`

## Full Feature Test Checklist

- [ ] Server starts successfully
- [ ] Health check returns 200
- [ ] Can create a new lead
- [ ] Can list all leads
- [ ] Agent responds to text messages
- [ ] Phone call initiates (with ngrok)
- [ ] Meetings can be booked

You're all set!
