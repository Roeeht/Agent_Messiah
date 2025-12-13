# 📞 Voice Calling Guide

Complete guide for setting up and using Agent Messiah's outbound calling capabilities.

## Prerequisites

- Twilio account (free trial works)
- ngrok installed (for webhook tunneling)
- Phone number to test with

## Setup Steps

### 1. Get Twilio Credentials

1. Sign up at [twilio.com/try-twilio](https://www.twilio.com/try-twilio)
2. Navigate to Console Dashboard
3. Copy your **Account SID** and **Auth Token**
4. Go to Phone Numbers → Buy a Number
5. Select a number with **Voice** capabilities
6. Note your purchased phone number (e.g., +1234567890)

### 2. Configure Environment

```bash
# Copy the example environment file
cp .env.example .env
```

Edit `.env` and add your credentials:

```env
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token_here
TWILIO_CALLER_ID=+1234567890
BASE_URL=https://your-ngrok-url.ngrok.io  # Set this after step 3

# Language / voice (recommended defaults)
CALLER_LANGUAGE=he-IL
ENABLE_TRANSLATION=True

# Hebrew-capable Twilio TTS voice (optional; defaults to a Hebrew Google voice when CALLER_LANGUAGE starts with "he")
TWILIO_TTS_VOICE=Google.he-IL-Standard-A
```

### 3. Start the Server

```bash
# Activate virtual environment
source venv/bin/activate

# Start FastAPI server
uvicorn app.main:app --reload
```

Server will run on `http://localhost:8000`

### 4. Expose Webhooks with ngrok

In a new terminal:

```bash
# Download and install ngrok from https://ngrok.com/download
# Then start the tunnel
ngrok http 8000
```

You'll see output like:

```
Forwarding   https://abc123.ngrok.io -> http://localhost:8000
```

Copy the HTTPS URL (e.g., `https://abc123.ngrok.io`) and update `BASE_URL` in your `.env` file.

**Restart the server** after updating `.env`:

```bash
# Ctrl+C to stop, then restart
uvicorn app.main:app --reload
```

### 5. Add a Test Lead

The project comes with sample leads. If you want to call your own phone number, add a lead by editing `app/leads_store.py`.

Example (add inside `_init_sample_leads()`):

```python
create_lead(
   name="Your Name",
   company="Test Corp",
   role="Tester",
   phone="+1234567890",  # Your actual phone number
   notes="Local test lead",
)
```

Restart the server.

## Making Calls

### Option 1: Call a Single Lead

```bash
curl -X POST "http://localhost:8000/outbound/initiate-call?lead_id=3"
```

Expected response:

```json
{
  "status": "success",
  "message": "Call initiated to Your Name",
  "call_sid": "CAxxxxxxxxxxxxxxxx",
  "call_status": "queued"
}
```

Your phone will ring within seconds!

### Option 2: Run a Campaign (All Leads)

```bash
curl -X POST "http://localhost:8000/outbound/campaign"
```

Expected response:

```json
{
  "status": "campaign_initiated",
  "total_leads": 2,
  "results": [
    {
      "lead_id": 1,
      "lead_name": "Roy Habari Tamir",
      "status": "initiated",
      "call_sid": "CAxxxxxxxx"
    },
    {
      "lead_id": 2,
      "lead_name": "Gal Miles",
      "status": "initiated",
      "call_sid": "CAyyyyyyyy"
    }
  ]
}
```

All leads will receive calls!

## What Happens During a Call

1. **Phone Rings**: Lead receives call from your Twilio number

2. **Agent Greeting** (Hebrew)

   The greeting is generated in English (internally), translated to Hebrew, and spoken via Twilio `<Say>`.
   The TTS voice is controlled by `TWILIO_TTS_VOICE` (default: `Google.he-IL-Standard-A` for Hebrew).

   ```
   "היי [Name]! אני מאלטה. אנחנו עוזרים לחברות להגדיל מכירות עם סוכני AI.
   איך אתם מטפלים היום בלידים נכנסים?"
   ```

3. **Recording + Transcription**: Twilio records the caller response (`<Record>`), then the server transcribes the audio with OpenAI

4. **Language Pipeline**:

   - Caller speech (Hebrew) → HE→EN translation
   - Agent logic/LLM runs in English
   - EN→HE translation → spoken back to the caller

5. **Conversation Flow**:

   - If interested → Qualifying questions
   - If very interested → Offer time slots
   - If selects slot → Book meeting
   - If not interested → Polite goodbye

6. **Meeting Confirmation** (if booked):
   ```
   "מעולה! קבעתי לך פגישה ל[date] בשעה [time].
   שלחתי לך הזמנה ליומן. מצפה לשיחה!"
   ```

## Call Flow Endpoints

The system uses these webhook endpoints (called by Twilio):

1. **`POST /twilio/voice`**

   - Triggered when call connects
   - Returns TwiML with Hebrew greeting
   - Starts recording (`<Record>`) and posts audio to the recording webhook

2. **`POST /twilio/process-recording`**

   - Triggered after each recorded caller response
   - Downloads the recording from Twilio, transcribes it, and continues the conversation
   - Returns next agent response as TwiML (and the next `<Record>`)

3. **`POST /twilio/call-status`**

   - Triggered for call events (ringing, answered, completed)
   - Logs status changes
   - Used for monitoring

4. **Optional debug**: **`GET /twilio/debug/{call_sid}`**

   - Disabled by default
   - Enable with `DEBUG_CALL_EVENTS=True`

## Testing the Conversation

Example conversation flow:

**Agent**: היי דוד! אני מאלטה. אנחנו עוזרים לחברות להגדיל מכירות עם סוכני AI. איך אתם מטפלים היום בלידים נכנסים?

**You**: יש לנו צוות מכירות

**Agent**: מעניין. יש לכם צוות SDR שמטפל בשיחות?

**You**: כן, נשמע מעניין

**Agent**: נשמע מצוין! אשמח לקבוע שיחת היכרות קצרה. יש לי זמינות מחר ב-10:00 או ביום חמישי ב-14:00. מה מתאים לך?

**You**: מחר בעשר

**Agent**: מעולה! קבעתי לך פגישה למחר בשעה 10:00. שלחתי לך הזמנה ליומן. מצפה לשיחה!

[Call ends]

## Troubleshooting

### "Twilio not configured" Error

Check that:

- All environment variables are set in `.env`
- You restarted the server after updating `.env`
- No typos in Account SID or Auth Token

### Call Not Connecting

1. Check ngrok is running and URL is correct in `.env`
2. Verify `BASE_URL` in `.env` matches ngrok HTTPS URL
3. Check Twilio console for error logs
4. Ensure phone number has voice capabilities

### No Voice Heard

- Check Twilio console → Debugger for TwiML errors
- Verify TwiML is being generated (check server logs)
- If you set `TWILIO_TTS_VOICE`, verify it matches the caller language (e.g. Hebrew voice for `he-IL`)
- Confirm your webhook response is valid TwiML XML and served as `application/xml`

### Speech Not Recognized

- If the caller response isn't understood, check server logs for transcription errors
- Verify OpenAI is configured (`OPENAI_API_KEY`) and reachable
- Increase `RECORD_MAX_LENGTH_SECONDS` if callers speak longer sentences

### ngrok Session Expired

Free ngrok sessions expire. Just restart:

```bash
# Kill old ngrok
pkill ngrok

# Start new session
ngrok http 8000

# Update BASE_URL in .env with new URL
# Restart server
```

## Monitoring Calls

### View in Twilio Console

1. Go to [console.twilio.com](https://console.twilio.com)
2. Click "Monitor" → "Logs" → "Calls"
3. See all calls, durations, and status

### View Booked Meetings

```bash
curl http://localhost:8000/meetings
```

### Check Server Logs

Watch the terminal running `uvicorn` for real-time webhook calls and TwiML generation.

## Cost Considerations

**Twilio Free Trial**:

- $15.50 credit
- ~$0.02 per minute for calls
- ~750 minutes of calling available

**Production Costs** (approximate):

- Outbound calls: $0.013 - $0.02/minute
- Phone number: $1/month
- Text-to-Speech + call minutes: billed by Twilio (see your Twilio voice pricing for exact rates)
- Transcription + translation: billed by OpenAI (based on your configured models)

## Production Deployment

For production use:

1. **Deploy server** to cloud (Railway, Render, Heroku, AWS)
2. **Use production domain** instead of ngrok for `BASE_URL`
3. **Add Redis** for conversation state storage
4. **Implement queue** for campaign processing
5. **Add monitoring** (Sentry, DataDog)
6. **Set up logging** for all calls
7. **Implement retry logic** for failed calls
8. **Add rate limiting** to respect Twilio limits

## Next Steps

- [ ] Test with your own phone number
- [ ] Customize the initial permission-gate greeting in `app/llm_agent.py` (and the Hebrew fallback text in `app/language/caller_he.py`)
- [ ] Add more leads to `app/leads_store.py`
- [ ] Run a small campaign
- [ ] Review booked meetings
- [ ] Check call logs in Twilio console

## Support

For issues or questions:

- Check Twilio docs: [twilio.com/docs/voice](https://www.twilio.com/docs/voice)
- Review TwiML reference: [twilio.com/docs/voice/twiml](https://www.twilio.com/docs/voice/twiml)
- Check server logs for errors
- Inspect Twilio debugger in console

Happy calling! 📞🎉
