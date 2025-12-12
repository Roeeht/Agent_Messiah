# Agent Messiah 🤖📞

**Production-Ready Hebrew AI Sales Agent**

A production-grade, Hebrew-speaking AI sales agent system for outbound calling campaigns with OpenAI GPT-4o-mini integration, complete database persistence, and enterprise monitoring.

> 🚀 **Quick Start**: Docker: `docker-compose up -d` | See [PRODUCTION.md](PRODUCTION.md) for deployment  
> 📞 **Voice Calling**: See [VOICE_CALLING_GUIDE.md](VOICE_CALLING_GUIDE.md) for Twilio setup  
> 🤖 **LLM Integration**: See [LLM_INTEGRATION.md](LLM_INTEGRATION.md) for OpenAI configuration  
> 🔄 **Migration**: Upgrading from MVP? See [MIGRATION.md](MIGRATION.md)

## Overview

Agent Messiah is a **production-ready** outbound calling solution that enables Alta to run Hebrew-speaking sales campaigns at scale with intelligent AI conversations. The system features:

- **🧠 OpenAI GPT-4o-mini integration** for natural, context-aware Hebrew conversations
- **📊 PostgreSQL database** for persistent lead and meeting storage
- **⚡ Redis session management** for stateful voice conversations
- **🔐 Enterprise security** with API authentication and webhook validation
- **📈 Prometheus metrics** for monitoring and observability
- **🐳 Docker deployment** with full containerization
- **🔄 Async job processing** with Celery for campaigns
- **💬 Structured JSON logging** for production debugging

## Production Features

| Feature                 | Status | Description                               |
| ----------------------- | ------ | ----------------------------------------- |
| 🗄️ Database Persistence | ✅     | PostgreSQL with SQLAlchemy ORM            |
| 🎯 Redis Sessions       | ✅     | Conversation state management             |
| 🧠 OpenAI Integration   | ✅     | GPT-4o-mini for intelligent conversations |
| 📞 Twilio Voice         | ✅     | Hebrew voice calling with AWS Polly       |
| 🔐 Security             | ✅     | API auth + webhook validation             |
| 📊 Monitoring           | ✅     | Health checks + Prometheus metrics        |
| 📝 Structured Logging   | ✅     | JSON logs with structlog                  |
| ⚙️ Async Tasks          | ✅     | Celery workers for campaigns              |
| 🐳 Docker               | ✅     | Full containerization with compose        |
| ✅ Tests                | ✅     | 42 comprehensive tests                    |

## Quick Start

### Option 1: Docker (Recommended)

```bash
# Clone and configure
git clone <repo>
cd Agent_Messiah
cp .env.docker.example .env.docker
# Edit .env.docker with your API keys

# Start all services
docker-compose up -d

# Check health
curl http://localhost:8000/health/ready
```

### Option 2: Manual Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Set up PostgreSQL and Redis
createdb agent_messiah
brew install redis && brew services start redis

# Configure
cp .env.example .env
# Edit .env with your credentials

# Run migrations
alembic upgrade head

# Start application
uvicorn app.main:app --reload

# Start Celery worker (separate terminal)
celery -A app.celery_tasks worker --loglevel=info
```

## Project Structure

```
Agent_Messiah/
├── app/
│   ├── main.py              # FastAPI app with production middleware
│   ├── models.py            # Pydantic data models
│   ├── config.py            # Configuration with env vars
│   ├── database.py          # SQLAlchemy database setup
│   ├── db_models.py         # Database models (Lead, Meeting, CallSession)
│   ├── services.py          # Business logic layer
│   ├── redis_client.py      # Redis session management
│   ├── logging_config.py    # Structured logging setup
│   ├── security.py          # Authentication & validation
│   ├── health.py            # Health check endpoints
│   ├── llm_agent.py         # OpenAI GPT integration
│   ├── agent_logic.py       # Rule-based fallback logic
│   ├── celery_tasks.py      # Async job processing
│   ├── leads_store.py       # Lead management
│   └── calendar_store.py    # Meeting scheduling
├── alembic/                 # Database migrations
├── tests/                   # 42 comprehensive tests
├── docker-compose.yml       # Multi-container setup
├── Dockerfile              # Production container
├── PRODUCTION.md           # Production deployment guide
├── MIGRATION.md            # Migration from MVP guide
├── LLM_INTEGRATION.md      # OpenAI integration docs
└── README.md               # This file
```

├── .env.example
├── .gitignore
├── PLANNING.md
├── QUICKSTART.md
├── IMPLEMENTATION_SUMMARY.md
└── README.md

````

## Getting Started

### Prerequisites

- Python 3.10 or higher
- pip (Python package manager)

### Installation

1. **Clone the repository**

```bash
cd Agent_Messiah
````

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
2. Speak the greeting in Hebrew (AWS Polly - Ayelet voice)
3. Listen for responses using speech-to-text
4. Continue the conversation based on responses
5. Offer meeting slots if lead is interested
6. Book the meeting automatically

## API Usage

### Test the Agent (Text-Based HTTP)

**Endpoint**: `POST /agent/turn`

**Request**:

```bash
curl -X POST "http://localhost:8000/agent/turn" \
  -H "Content-Type: application/json" \
  -d '{
    "lead_id": 1,
    "user_utterance": "שלום",
    "history": []
  }'
```

**Response**:

```json
{
  "agent_reply": "היי דוד! אני מאלטה. אנחנו עוזרים לחברות להגדיל מכירות עם סוכני AI. איך אתם מטפלים היום בלידים נכנסים?",
  "action": null,
  "action_payload": null
}
```

### Voice Endpoints

**Twilio Voice Webhook** (called by Twilio when call connects):

- `POST /twilio/voice` - Initiates conversation with Hebrew greeting
- Returns TwiML with speech gathering

**Speech Processing** (called by Twilio after each user response):

- `POST /twilio/process-speech` - Processes speech input and continues conversation
- Returns TwiML with agent response and next speech gather

**Call Status** (called by Twilio for call events):

- `POST /twilio/call-status` - Logs call status changes

### Example Conversation Flow

1. **Initial greeting**:

```bash
curl -X POST "http://localhost:8000/agent/turn" \
  -H "Content-Type: application/json" \
  -d '{"lead_id": 1, "user_utterance": "שלום", "history": []}'
```

2. **Ask "who are you"**:

```bash
curl -X POST "http://localhost:8000/agent/turn" \
  -H "Content-Type: application/json" \
  -d '{"lead_id": 1, "user_utterance": "מי אתה?", "history": []}'
```

3. **Show interest**:

```bash
curl -X POST "http://localhost:8000/agent/turn" \
  -H "Content-Type: application/json" \
  -d '{
    "lead_id": 1,
    "user_utterance": "כן, נשמע מעניין",
    "history": [
      {"user": "שלום", "agent": "היי דוד!..."},
      {"user": "יש לנו SDR", "agent": "מעניין. יש לכם צוות SDR?"}
    ]
  }'
```

Response will include `"action": "offer_slots"` with available meeting times.

4. **Not interested**:

```bash
curl -X POST "http://localhost:8000/agent/turn" \
  -H "Content-Type: application/json" \
  -d '{"lead_id": 1, "user_utterance": "לא מעוניין", "history": []}'
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
pytest tests/test_agent_logic.py -v
```

## Implementation Details

### What's Implemented

1. **Data Layer**

   - Lead and Meeting models with Pydantic
   - In-memory storage (easily swappable for SQLite/PostgreSQL)
   - Helper functions for CRUD operations

2. **Agent Logic**

   - Rule-based conversation flow in natural Israeli Hebrew
   - Context-aware responses based on conversation history
   - Qualifying questions about lead handling and SDR teams
   - Meeting booking flow with slot selection

3. **API Endpoints**

   - `/agent/turn` - Main conversation endpoint
   - `/meetings` - List scheduled meetings
   - `/leads` - List all leads
   - `/twilio/voice` - Twilio webhook with basic TwiML

4. **Tests**
   - Agent logic tests (Hebrew responses, flow control)
   - Calendar store tests (slots, booking)
   - API route tests (FastAPI TestClient)

### Agent Behavior

The agent follows this conversation pattern:

1. **Greeting**: Introduces Alta and asks about lead handling
2. **Qualifying**: 1-3 questions about SDRs and current processes
3. **Positive Response**: Offers 2 meeting slots
4. **Slot Selection**: Books meeting and confirms
5. **Not Interested**: Politely ends conversation

All responses are in natural Israeli Hebrew with short, conversational sentences.

## Next Steps for Production

If this were a real production system, the next steps would be:

### Immediate Enhancements

1. **Database Integration**

   - Replace in-memory storage with PostgreSQL/MongoDB
   - Add proper schema migrations (Alembic)
   - Implement connection pooling

2. **LLM Integration**

   - Integrate OpenAI GPT-4 for more natural conversations
   - Add few-shot prompting with Hebrew examples
   - Implement streaming responses for lower latency

3. **Twilio Voice Implementation**

   - Complete speech-to-text integration (Twilio/Deepgram)
   - Implement text-to-speech with Hebrew voice (Polly.Ayelet)
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
   - Metrics (Prometheus/Datadog)
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
# OpenAI Configuration (optional for rule-based version)
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

### Why Rule-Based for v1?

- Faster development and testing
- Predictable responses
- Lower cost (no LLM API calls)
- Easier to debug conversation flows
- Foundation for LLM enhancement

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
