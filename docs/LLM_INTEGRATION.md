# LLM Integration Guide

Agent Messiah runs in **LLM-only mode** using OpenAI's GPT models.

## What's New

Instead of rule-based responses, the agent can now:

- 🧠 **Understand context** from the entire conversation
- 💬 **Respond naturally** to any question or comment
- 🎯 **Adapt dynamically** to lead responses
- 🤖 **Make smart decisions** about when to offer meetings
- 🌍 **Keep the agent English-only internally** and translate to Hebrew for callers

## Quick Start

### 1. Get an OpenAI API Key

1. Sign up at [platform.openai.com](https://platform.openai.com)
2. Create an API key in your dashboard
3. Copy the key (starts with `sk-proj-...`)

### 2. Configure Environment

```bash
# Edit your .env file
nano .env
```

Add your OpenAI configuration:

```env
# OpenAI API configuration
OPENAI_API_KEY=sk-proj-your-actual-key-here
OPENAI_MODEL=gpt-4o-mini  # Recommended for cost efficiency
```

### 3. Test the Agent

```bash
# Start the server
uvicorn app.main:app --reload

# In another terminal, test a conversation
curl -X POST "http://localhost:8000/agent/turn" \
  -H "Content-Type: application/json" \
  -d '{
    "lead_id": 1,
    "user_utterance": "Hi, who is this?",
    "history": []
  }'
```

You should get an intelligent response from GPT!

## Model Options

Choose the right model for your needs:

| Model           | Cost          | Speed            | Quality              | Recommended For              |
| --------------- | ------------- | ---------------- | -------------------- | ---------------------------- |
| `gpt-4o-mini`   | 💰 Lowest     | ⚡ Fastest       | ⭐⭐⭐ Good          | **Production** (recommended) |
| `gpt-4o`        | 💰💰 Medium   | ⚡⚡ Fast        | ⭐⭐⭐⭐⭐ Excellent | High-value leads             |
| `gpt-4-turbo`   | 💰💰💰 Higher | ⚡⚡ Fast        | ⭐⭐⭐⭐⭐ Excellent | Complex conversations        |
| `gpt-3.5-turbo` | 💰 Very Low   | ⚡⚡⚡ Very Fast | ⭐⭐ OK              | Testing only                 |

**Our recommendation**: Use `gpt-4o-mini` for production. It's cost-effective (~15x cheaper than GPT-4) and performs excellently for sales conversations.

## How It Works

### System Prompt

The agent is defined with a comprehensive system prompt that includes:

- **Persona**: AI sales agent (English internally) working for Habari's Sales Company
- **Company info**: Habari's Sales Company provides AI solutions for SDR teams
- **Conversation guidelines**: Short, professional, friendly
- **Critical language rule**: The model output must be English-only (caller Hebrew is produced by translation)
- **Conversation flow**: Greeting → Pitch → Qualify → Offer Meeting → Book

### Function Calling

The agent can call these functions automatically:

1. **`offer_meeting_slots`** - When lead shows strong interest
2. **`book_meeting`** - When lead selects a time
3. **`end_call`** - When lead is not interested or conversation is complete

### Conversation Memory

The agent maintains context by:

- Receiving full conversation history with each turn
- Understanding what was discussed earlier
- Making coherent decisions based on the entire conversation
- Adapting responses to the lead's tone and interest level

## Example Conversations

Note: The LLM outputs English-only. In the Twilio voice flow, user speech is translated HE→EN before the LLM, and replies are translated EN→HE for the caller.

### Conversation 1: Successful Booking

```bash
# Turn 1
User: "Hello"
Agent: "Hi! I'm the agent from Habari's Sales Company. We help companies increase sales with AI agents. Is this a good time to talk? Please answer yes or no."

# Turn 2
User: "Yes"
Agent: "Great. How do you handle inbound leads today?"

# Turn 2
User: "We have an SDR team but they're overloaded"
Agent: "Got it. That's exactly what we help with — our AI agents handle the initial lead response so your team can focus on the best opportunities. Want to see a quick demo?"

# Turn 3
User: "Yes, sounds interesting"
Agent: "Great. I'd be happy to schedule a short intro call. I have availability tomorrow at 10:00 or Thursday at 14:00. What works for you?"
[Function called: offer_meeting_slots]

# Turn 4
User: "Tomorrow at 10 works"
Agent: "Excellent! I've scheduled a meeting for tomorrow at 10:00. I'll send you a calendar invitation. Looking forward to the call!"
[Function called: book_meeting]
```

### Conversation 2: Handling Objections

```bash
# Turn 1
User: "How much does it cost?"
Agent: "It depends on your needs. I'd be happy to do a quick 15-minute intro to understand your process and share options. Do you have time tomorrow?"

# Turn 2
User: "We don't have budget right now"
Agent: "Totally understand. Many teams see ROI quickly because the agents free up sales to focus on larger deals. Want to hear how it typically works?"
```

### Conversation 3: Not Interested

```bash
User: "Not interested, thanks"
Agent: "Understood. If it makes sense to revisit in the future, I'd be happy to chat. Have a great day."
[Function called: end_call]
```

## Voice Calling with LLM

The LLM integration works seamlessly with voice calls:

```bash
# Initiate outbound call (uses LLM automatically)
curl -X POST "http://localhost:8000/outbound/initiate-call?lead_id=1"
```

The agent will:

1. Call the lead
2. Generate the greeting in English, translate it to Hebrew, and speak it via Twilio `<Say>`
3. Record each response (`<Record>`) and transcribe it with OpenAI
4. Use GPT to understand and respond naturally
5. Continue until meeting is booked or call ends

## LLM-Only Mode

The project no longer supports switching between LLM and rule-based modes.

- If you need offline/deterministic behavior (for CI/tests), mock `app.llm_agent.decide_next_turn_llm` and translation helpers.
- For production, configure `OPENAI_API_KEY`.

## Cost Estimation

With `gpt-4o-mini`:

- Costs vary by prompt size, token usage, and translation settings.
- Measure actual usage in your logs and OpenAI usage dashboard before scaling campaigns.
- **1,000 calls/day**: $1.50/day = **$45/month**

Compare to:

- Twilio voice minutes: ~$0.02/minute
- Human SDR: $30-50/hour

The AI conversation cost is negligible compared to call costs!

## Monitoring and Debugging

### View Conversations

All conversations are logged automatically. Check the server logs to see:

- Full conversation history
- Function calls made by the agent
- Lead information
- Response times

### Common Issues

**"OpenAI API error"**

- Check your API key is correct
- Verify you have credits in your OpenAI account
- Check internet connection

**"OpenAI not configured"**

- Verify `OPENAI_API_KEY` is set
- Restart the server after changing `.env`

**"Conversations not coherent"**

- Ensure you're passing conversation history
- Check token limits (max 150 tokens per response)
- Try using a more powerful model (gpt-4o)

## Advanced Configuration

### Custom System Prompt

Edit `app/llm_agent.py` to customize the agent's behavior:

```python
SYSTEM_PROMPT = """You are an AI sales agent working for Habari's Sales Company.

[Your custom instructions here]
"""
```

### Adjust Temperature

Control creativity vs consistency:

```python
# In llm_agent.py decide_next_turn_llm()
temperature=0.7,  # Lower = more consistent, Higher = more creative
```

### Change Token Limits

Control response length:

```python
max_tokens=150,  # Increase for longer responses
```

## Testing

Run the LLM tests:

```bash
pytest tests/test_llm_agent.py -v
```

All tests use mocked OpenAI responses, so they run without API costs.

## Next Steps

1. ✅ Configure your OpenAI API key
2. ✅ Test with a few conversations
3. ✅ Review conversation quality
4. ✅ Adjust system prompt if needed
5. ✅ Run a small campaign (10-20 calls)
6. ✅ Monitor costs and results
7. ✅ Scale up!

## Support

For issues or questions:

- Check the [README.md](../README.md) for general setup
- Review [QUICKSTART.md](QUICKSTART.md) for basic usage
- See [VOICE_CALLING_GUIDE.md](VOICE_CALLING_GUIDE.md) for Twilio integration

Happy calling with AI! 🤖📞
