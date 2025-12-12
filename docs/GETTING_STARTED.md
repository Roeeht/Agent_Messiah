# Getting Started with Agent Messiah

## Quick Start Guide

### Step 1: Start the Application

You have **two options** - Simple (local) or Full (Docker with all features):

#### Option A: Simple Local Start (Recommended for Testing)

```bash
cd /Users/roeehabari-tamir/Documents/repos/Agent_Messiah

# Activate virtual environment
source venv/bin/activate

# Run database migrations (first time only)
alembic upgrade head

# Start the server
uvicorn app.main:app --reload
```

The server will start on **http://localhost:8000**

**Note**: This uses SQLite (no PostgreSQL needed) and works without Redis. Perfect for testing!

#### Option B: Full Production Start (with all features)

```bash
# Start all services (PostgreSQL, Redis, App, Celery)
docker-compose up -d

# Check status
docker-compose logs -f app
```

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

### Step 3: Test with a New Lead

#### Method 1: Add Lead via API

```bash
# Add a new lead
curl -X POST http://localhost:8000/leads \
  -H "Content-Type: application/json" \
  -d '{
    "name": "יוסי כהן",
    "phone": "+972501234567",
    "company": "Tech Corp",
    "role": "CTO",
    "notes": "Met at conference"
  }'

# Response will include the lead_id
```

#### Method 2: Use Built-in Test Leads

The system comes with 3 pre-loaded test leads:

```bash
# List all leads
curl http://localhost:8000/leads

# Returns:
# [
#   {"id": 1, "name": "דוד כהן", "phone": "+972501234567", ...},
#   {"id": 2, "name": "שרה לוי", "phone": "+972509876543", ...},
#   {"id": 3, "name": "מיכאל אברהם", "phone": "+972502223333", ...}
# ]
```

### Step 4: Test the Agent (3 Ways)

#### Way 1: Text Conversation (API Test)

```bash
# Have a conversation with the agent
curl -X POST http://localhost:8000/agent/turn \
  -H "Content-Type: application/json" \
  -d '{
    "lead_id": 1,
    "user_utterance": "שלום",
    "history": []
  }'

# The agent will respond in Hebrew!
# Response:
# {
#   "agent_reply": "שלום דוד! אני הסוכן מAlta...",
#   "action": null,
#   "action_payload": null
# }
```

#### Way 2: Interactive Demo Script

```bash
# Run the interactive demo
python demo_llm.py --interactive

# This starts a chat where you can type Hebrew messages
# Type messages in Hebrew and press Enter
# Type 'quit' to exit
```

#### Way 3: Actual Phone Call (Real Test!)

**Important**: Make sure ngrok is running first:

```bash
# In a separate terminal
ngrok http 8000

# Update BASE_URL in .env with the ngrok URL
# Example: BASE_URL=https://abc123.ngrok-free.app
```

Then initiate a call:

```bash
# Call lead #1 (דוד כהן)
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
AGENT_MODE=llm                  # Use LLM conversations ✓

TWILIO_ACCOUNT_SID=AC...        # Your Twilio SID ✓
TWILIO_AUTH_TOKEN=e696...       # Your Twilio token ✓
TWILIO_CALLER_ID=+97233769901   # Your Israeli number ✓

BASE_URL=https://...ngrok...    # Your ngrok URL ✓
```

### ✅ Optional Keys (Added - Can Stay Empty)

```bash
DATABASE_URL=sqlite:///./agent_messiah.db  # Uses SQLite by default
REDIS_URL=redis://localhost:6379/0         # Only needed if Redis installed
LOG_LEVEL=INFO                              # Logging verbosity
API_KEY=                                    # Leave empty (optional security)
WEBHOOK_SECRET=                             # Leave empty (optional security)
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
    "user_utterance": "שלום",
    "history": []
  }'

# Agent: "שלום דוד! אני הסוכן מAlta..."

# 3. Show interest
curl -X POST http://localhost:8000/agent/turn \
  -H "Content-Type: application/json" \
  -d '{
    "lead_id": 1,
    "user_utterance": "כן, נשמע מעניין",
    "history": [
      {"role": "user", "content": "שלום"},
      {"role": "assistant", "content": "שלום דוד! אני הסוכן מAlta..."}
    ]
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

### Issue: "Connection refused" or "Redis not available"

**Solution**: Redis is optional! The system works without it.

If you want Redis features:

```bash
brew install redis
brew services start redis
```

### Issue: "Database error"

**Solution**: Run migrations:

```bash
alembic upgrade head
```

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
1. ✓ Database initialized (SQLite: agent_messiah.db)
2. ✓ Redis checked (optional - skips if not available)
3. ✓ OpenAI client configured
4. ✓ Twilio client ready
5. ✓ Server listening on http://localhost:8000
6. ✓ Health checks available at /health
```

## Next Steps

1. **Test the API**: Use the curl commands above
2. **Try a phone call**: Make sure ngrok is running, then call a lead
3. **Interactive demo**: Run `python demo_llm.py --interactive`
4. **View logs**: Check the console for structured logs
5. **Monitor health**: Visit http://localhost:8000/health/info

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
- [ ] Interactive demo works
- [ ] Phone call initiates (with ngrok)
- [ ] Meetings can be booked
- [ ] Metrics endpoint works (`/metrics`)

You're all set! 🚀
