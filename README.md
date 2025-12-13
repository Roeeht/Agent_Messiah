# Agent Messiah 🤖📞

**Hebrew AI Sales Agent (simple local dev workflow)**

Outbound calling system with a Hebrew caller experience, an English-only internal agent, and an HE↔EN translation pipeline.

This repo is intentionally set up to run locally with:

- `uvicorn app.main:app --reload`
- In-memory lead + meeting stores (no database)
- No Docker / Compose / Celery required

## Overview

Agent Messiah is an outbound calling solution that enables Alta to run Hebrew-speaking sales calls. The system features:

- **🧠 OpenAI GPT-4o-mini integration** for natural, context-aware agent conversations (English internally)
- **🌍 HE↔EN translation pipeline** so callers always hear Hebrew while internal logic stays English-only
- **📊 In-memory stores** for leads and meeting scheduling (simple local dev)
- **⚡ In-memory session management** for stateful voice conversations
- **🔐 API key protection** for debug endpoints (optional)
- **💬 Structured JSON logging** for production debugging

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env with your credentials

# Start application
uvicorn app.main:app --reload
```

## Project Structure

```
Agent_Messiah/
├── app/
│   ├── main.py              # FastAPI app composition (includes routers)
│   ├── routers/             # Route modules (core/agent/outbound/twilio)
│   ├── models.py            # Pydantic data models
│   ├── config.py            # Configuration with env vars
│   ├── redis_client.py      # In-memory call session store
│   ├── logging_config.py    # Structured logging setup
│   ├── security.py          # Authentication & validation
│   ├── health.py            # Health check endpoints
│   ├── llm_agent.py         # OpenAI GPT integration
│   ├── twiml_builder.py      # Twilio TwiML builders
│   ├── language/            # Hebrew caller messages + translation utilities
│   ├── leads_store.py       # Lead management
│   └── calendar_store.py    # Meeting scheduling
├── docs/                    # Documentation
├── tests/                   # Test suite
└── README.md               # This file
```

Entry-point docs live in `docs/`.

## Getting Started

### Prerequisites

- Python 3.10 or higher
- pip (Python package manager)

### Installation

1. **Clone the repository**

```bash
cd Agent_Messiah
```

2. **Create a virtual environment**

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**

```bash
pip install -r requirements.txt
```

4. **Set up environment variables**

```bash
cp .env.example .env
# Edit .env with your API keys (optional for basic testing)
```

### Running the Application

Start the FastAPI server:

```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`

Interactive API docs: `http://localhost:8000/docs`

## Voice Calling Setup (Twilio)

### 1. Get Twilio Credentials

1. Sign up at [twilio.com](https://www.twilio.com/try-twilio)
2. Get your Account SID and Auth Token from the console
3. Purchase a phone number with voice capabilities

### 2. Configure Environment Variables

```bash
cp .env.example .env
# Edit .env and add:
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_CALLER_ID=+1234567890  # Your Twilio phone number
BASE_URL=https://your-ngrok-url.ngrok.io  # For webhooks
```

### 3. Expose Webhooks with ngrok

```bash
# Install ngrok: https://ngrok.com/download
ngrok http 8000
```

Copy the HTTPS URL (e.g., `https://abc123.ngrok.io`) and update `BASE_URL` in `.env`

### 4. Make Outbound Calls

**Call a single lead**:

```bash
curl -X POST "http://localhost:8000/outbound/initiate-call?lead_id=1"
```

**Run a campaign (call all leads)**:

```bash
curl -X POST "http://localhost:8000/outbound/campaign"
```

The agent will:

1. Call the lead's phone number
2. Speak the greeting in Hebrew (via Twilio `<Say>` using a Hebrew-capable voice)
3. Record each caller response (`<Record>`) and transcribe it with OpenAI
4. Continue the conversation based on responses
5. Offer meeting slots if lead is interested
6. Book the meeting automatically

## API Usage

### Test the Agent (Text-Based HTTP)

**Endpoint**: `POST /agent/turn`

Note: this endpoint is a direct agent turn (no Twilio). The system is LLM-only and responds in English (by design). For the Hebrew caller experience, use the Twilio flow (HE↔EN translation around the LLM).

**Request**:

```bash
curl -X POST "http://localhost:8000/agent/turn" \
  -H "Content-Type: application/json" \
  -d '{
    "lead_id": 1,
      "user_utterance": "Hi",
    "history": []
  }'
```

**Response**:

```json
{
  "agent_reply": "Hi David! I'm the agent from Alta. We help companies increase sales with AI agents. Is this a good time to talk? Please answer yes or no.",
  "action": null,
  "action_payload": null
}
```

### Voice Endpoints

**Twilio Voice Webhook** (called by Twilio when call connects):

- `POST /twilio/voice` - Initiates conversation with Hebrew greeting
- Returns TwiML that records the caller (`<Record>`) and posts audio to the recording webhook

**Recording Processing** (called by Twilio after each recorded user response):

- `POST /twilio/process-recording` - Downloads the recording, transcribes it, and continues the conversation
- Returns TwiML with the agent response and the next `<Record>`

**Call Status** (called by Twilio for call events):

- `POST /twilio/call-status` - Logs call status changes

**Optional Debug (development only)**:

- `GET /twilio/debug/{call_sid}` - Returns recent per-call debug events (requires `DEBUG_CALL_EVENTS=True`)

### Example Conversation Flow

1. **Initial greeting**:

```bash
curl -X POST "http://localhost:8000/agent/turn" \
  -H "Content-Type: application/json" \
   -d '{"lead_id": 1, "user_utterance": "Hello", "history": []}'
```

2. **Ask "who are you"**:

```bash
curl -X POST "http://localhost:8000/agent/turn" \
  -H "Content-Type: application/json" \
   -d '{"lead_id": 1, "user_utterance": "Who are you?", "history": []}'
```

3. **Show interest**:

```bash
curl -X POST "http://localhost:8000/agent/turn" \
  -H "Content-Type: application/json" \
  -d '{
    "lead_id": 1,
      "user_utterance": "Yes, sounds interesting",
    "history": [
         {"user": "Hello", "agent": "Hi Roy!..."},
         {"user": "We have an SDR team", "agent": "Got it. ..."}
    ]
  }'
```

Response will include `"action": "offer_slots"` with available meeting times.

4. **Not interested**:

```bash
curl -X POST "http://localhost:8000/agent/turn" \
  -H "Content-Type: application/json" \
   -d '{"lead_id": 1, "user_utterance": "Not interested", "history": []}'
```

Response will include `"action": "end_call"`.

### Other Endpoints

**List all meetings**:

```bash
curl http://localhost:8000/meetings
```

**List all leads**:

```bash
curl http://localhost:8000/leads
```

## Running Tests

Run the test suite:

```bash
pytest
```

Run with coverage:

```bash
pytest --cov=app tests/
```

Run specific test file:

```bash
pytest tests/test_api_routes.py -v
```

## Implementation Details

### What's Implemented

1. **Data Layer**

   - Lead and Meeting models with Pydantic
   - In-memory storage (easily swappable for SQLite/PostgreSQL)
   - Helper functions for CRUD operations

2. **Agent Logic**

   - LLM-only conversation flow (English internal), translated for Hebrew callers in the Twilio flow
   - Context-aware responses based on conversation history
   - Qualification + meeting booking via OpenAI function calling

3. **API Endpoints**

   - `/agent/turn` - Main conversation endpoint
   - `/meetings` - List scheduled meetings
   - `/leads` - List all leads
   - `/twilio/voice` - Twilio webhook with basic TwiML

4. **Tests**
   - Agent/voice flow tests (offline-safe via mocks)
   - Calendar store tests (slots, booking)
   - API route tests (FastAPI TestClient)

### Agent Behavior

The agent follows this conversation pattern:

1. **Greeting**: Introduces Alta and asks about lead handling
2. **Qualifying**: 1-3 questions about SDRs and current processes
3. **Positive Response**: Offers 2 meeting slots
4. **Slot Selection**: Books meeting and confirms
5. **Not Interested**: Politely ends conversation

Caller-facing responses are in natural Israeli Hebrew with short, conversational sentences.

## Next Steps for Production

If this were a real production system, the next steps would be:

### Immediate Enhancements

1. **Database Integration**

   - Replace in-memory storage with PostgreSQL/MongoDB
   - Add proper schema migrations
   - Implement connection pooling

2. **LLM Integration**

   - Integrate OpenAI GPT-4 for more natural conversations
   - Add few-shot prompting with Hebrew examples
   - Implement streaming responses for lower latency

3. **Twilio Voice Implementation**

   - Improve the recording → transcription pipeline (latency, accuracy, retries)
   - Keep Hebrew TTS voice configuration stable (e.g., `TWILIO_TTS_VOICE=Google.he-IL-Standard-A`)
   - Add WebSocket support for real-time audio streaming
   - Handle interruptions and natural conversation flow

4. **Calendar Integration**
   - Connect to real calendar services (Google Calendar, Outlook)
   - Check actual availability
   - Send calendar invites
   - Handle timezone conversions

### Scalability & Reliability

5. **State Management**

   - Redis for session state
   - Conversation history persistence
   - Handle long-running conversations

6. **Monitoring & Observability**

   - Structured logging (JSON logs)
   - Metrics
   - Distributed tracing (OpenTelemetry)
   - Error tracking (Sentry)

7. **Security**

   - Twilio request signature verification
   - Rate limiting and DDoS protection
   - Input sanitization
   - Secrets management (AWS Secrets Manager/Vault)

8. **Performance**
   - Caching frequently accessed data
   - Async processing for non-blocking operations
   - Load balancing
   - CDN for static assets

### Advanced Features

9. **Agent Improvements**

   - Sentiment analysis
   - Intent classification
   - Multi-language support
   - Personalization based on lead data
   - A/B testing different conversation flows

10. **Analytics & Reporting**

    - Conversation analytics dashboard
    - Conversion rate tracking
    - Agent performance metrics
    - Lead scoring based on conversation

11. **CRM Integration**

    - Salesforce/HubSpot integration
    - Automatic lead updates
    - Activity logging
    - Reporting to sales team

12. **Compliance & Privacy**
    - GDPR compliance (data retention, right to deletion)
    - Call recording consent
    - Data encryption
    - Audit logs

## Configuration

### Environment Variables

Create a `.env` file based on `.env.example`:

```bash
# OpenAI Configuration (required for LLM-only agent)
OPENAI_API_KEY=sk-...

# Twilio Configuration (optional for telephony)
TWILIO_ACCOUNT_SID=AC...
TWILIO_AUTH_TOKEN=...
TWILIO_CALLER_ID=+1234567890

# Application Settings
DEBUG=True
```

## Technologies Used

- **FastAPI**: Modern web framework for building APIs
- **Pydantic**: Data validation using Python type annotations
- **pytest**: Testing framework
- **Twilio**: Telephony platform (basic integration)
- **python-dotenv**: Environment variable management

## Architecture Decisions

### Why LLM-Only?

- Higher conversational flexibility
- Clear single-path behavior (no mode switching)
- Meeting booking via function-calling actions

### Why In-Memory Storage?

- Simplifies initial development
- No database setup required
- Easy to test
- Simple migration path to persistent storage

### Why Hebrew-First?

- Target market in Israel
- Alta's primary audience
- Demonstrates localization capability

## License

This is a home assignment project for demonstration purposes.

## Author

Built as a home assignment for the AI Solution Engineer role at Alta.

---

**Questions or feedback?** Feel free to reach out!
