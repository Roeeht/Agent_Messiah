"""Main FastAPI application."""

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, JSONResponse
from sqlalchemy.orm import Session
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
import time

from app.models import AgentTurnRequest, AgentTurnResponse, Meeting
from app import leads_store, calendar_store, agent_logic, llm_agent
from app.config import config
from app.database import get_db, init_db
from app.services import LeadService, MeetingService, CallSessionService
from app.db_models import LeadStatus, CallStatus
from app.logging_config import logger
from app.redis_client import SessionManager, REDIS_AVAILABLE

# Prometheus metrics
api_requests_total = Counter('api_requests_total', 'Total API requests', ['method', 'endpoint', 'status'])
api_request_duration = Histogram('api_request_duration_seconds', 'API request duration')
calls_initiated = Counter('calls_initiated_total', 'Total calls initiated')
meetings_booked = Counter('meetings_booked_total', 'Total meetings booked')


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - startup and shutdown."""
    # Startup
    logger.info("application_starting", version="2.0.0")
    init_db()  # Initialize database
    logger.info("database_initialized")
    logger.info("redis_available", available=REDIS_AVAILABLE)
    logger.info("openai_configured", configured=config.has_openai_key())
    logger.info("agent_mode", mode=config.AGENT_MODE)
    
    yield
    
    # Shutdown
    logger.info("application_shutting_down")


app = FastAPI(
    title="Agent Messiah API",
    description="Production-Ready AI Sales Agent for Alta",
    version="2.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include health & monitoring router
from app.health import router as health_router
app.include_router(health_router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Agent Messiah API - Hebrew Speaking AI Sales Agent",
        "version": "1.0.0",
        "description": "Outbound calling campaign agent for Alta - pitches value proposition and books meetings",
        "endpoints": {
            "agent_turn": "/agent/turn",
            "meetings": "/meetings",
            "leads": "/leads",
            "outbound_call": "/outbound/initiate-call",
            "outbound_campaign": "/outbound/campaign",
            "twilio_voice": "/twilio/voice",
            "twilio_process_speech": "/twilio/process-speech",
            "twilio_call_status": "/twilio/call-status"
        },
        "features": [
            "Hebrew speaking AI agent",
            "Outbound calling campaigns",
            "Value proposition pitch",
            "Meeting booking",
            "Twilio voice integration"
        ]
    }


@app.post("/agent/turn", response_model=AgentTurnResponse)
async def agent_turn(request: AgentTurnRequest):
    """
    Process a conversation turn with the AI agent.
    
    This endpoint simulates a conversation with the agent without telephony.
    """
    # Get lead if provided
    lead = None
    if request.lead_id:
        lead = leads_store.get_lead_by_id(request.lead_id)
        if not lead:
            raise HTTPException(status_code=404, detail=f"Lead {request.lead_id} not found")
    
    # Prepare history
    history = request.history or []
    
    # Get agent's response - use LLM if configured, otherwise rule-based
    if config.AGENT_MODE == "llm" and config.has_openai_key():
        agent_reply, action, action_payload = llm_agent.decide_next_turn_llm(
            lead=lead,
            history=history,
            last_user_utterance=request.user_utterance
        )
    else:
        # Fall back to rule-based agent
        agent_reply, action, action_payload = agent_logic.decide_next_turn(
            lead=lead,
            history=history,
            last_user_utterance=request.user_utterance
        )
    
    return AgentTurnResponse(
        agent_reply=agent_reply,
        action=action,
        action_payload=action_payload
    )


@app.get("/meetings", response_model=list[Meeting])
async def list_meetings():
    """List all scheduled meetings."""
    return calendar_store.list_meetings()


@app.get("/leads")
async def list_leads():
    """List all leads."""
    return leads_store.list_leads()


@app.post("/outbound/initiate-call")
async def initiate_outbound_call(lead_id: int):
    """
    Initiate an outbound call to a lead.
    
    This endpoint triggers a call to the specified lead using Twilio.
    The agent will pitch Alta's value proposition and attempt to book a meeting.
    """
    # Validate lead exists
    lead = leads_store.get_lead_by_id(lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail=f"Lead {lead_id} not found")
    
    # Check if Twilio is configured
    if not config.has_twilio_config():
        return {
            "status": "error",
            "message": "Twilio not configured. Set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, and TWILIO_CALLER_ID in .env",
            "lead": lead.model_dump(),
            "would_call": lead.phone
        }
    
    try:
        from twilio.rest import Client
        
        # Initialize Twilio client
        client = Client(config.TWILIO_ACCOUNT_SID, config.TWILIO_AUTH_TOKEN)
        
        # Initiate outbound call
        # The voice webhook URL should be publicly accessible (use ngrok for local testing)
        call = client.calls.create(
            to=lead.phone,
            from_=config.TWILIO_CALLER_ID,
            url=f"{config.BASE_URL}/twilio/voice",  # This must be a public URL
            method="POST",
            status_callback=f"{config.BASE_URL}/twilio/call-status",
            status_callback_method="POST"
        )
        
        return {
            "status": "success",
            "message": f"Call initiated to {lead.name}",
            "lead": lead.model_dump(),
            "call_sid": call.sid,
            "call_status": call.status
        }
    
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to initiate call: {str(e)}",
            "lead": lead.dict()
        }


@app.post("/outbound/campaign")
async def initiate_campaign():
    """
    Initiate an outbound calling campaign to all leads.
    
    This will call all leads in the database sequentially with a delay between calls.
    """
    if not config.has_twilio_config():
        return {
            "status": "error",
            "message": "Twilio not configured",
            "leads_count": len(leads_store.list_leads())
        }
    
    leads = leads_store.list_leads()
    results = []
    
    for lead in leads:
        try:
            from twilio.rest import Client
            
            client = Client(config.TWILIO_ACCOUNT_SID, config.TWILIO_AUTH_TOKEN)
            
            call = client.calls.create(
                to=lead.phone,
                from_=config.TWILIO_CALLER_ID,
                url=f"{config.BASE_URL}/twilio/voice",
                method="POST"
            )
            
            results.append({
                "lead_id": lead.id,
                "lead_name": lead.name,
                "status": "initiated",
                "call_sid": call.sid
            })
            
            # Small delay between calls to avoid overwhelming
            import time
            time.sleep(2)
            
        except Exception as e:
            results.append({
                "lead_id": lead.id,
                "lead_name": lead.name,
                "status": "failed",
                "error": str(e)
            })
    
    return {
        "status": "campaign_initiated",
        "total_leads": len(leads),
        "results": results
    }


@app.post("/twilio/call-status")
async def twilio_call_status(request: Request):
    """
    Receive call status updates from Twilio.
    
    Twilio sends updates about call progress (ringing, answered, completed, etc.)
    """
    form_data = await request.form()
    
    call_sid = form_data.get("CallSid", "")
    call_status = form_data.get("CallStatus", "")
    
    # In production, log this to database/analytics
    print(f"Call {call_sid} status: {call_status}")
    
    return {"status": "received"}


@app.post("/twilio/voice")
async def twilio_voice(request: Request):
    """
    Twilio webhook for incoming/outgoing calls.
    
    Returns Hebrew TwiML for caller. All internal processing in English.
    """
    import traceback
    from app.language.caller_he import get_caller_text
    from app.language.translator import translate_en_to_he
    from app.twiml_builder import build_voice_twiml, build_error_twiml
    
    try:
        # Get call parameters
        form_data = await request.form()
        call_sid = form_data.get("CallSid", "")
        from_number = form_data.get("From", "")
        to_number = form_data.get("To", "")
        
        logger.info("voice_webhook_called", call_sid=call_sid, from_number=from_number, to_number=to_number)
        
        # Find lead (internal logic - English)
        lead = None
        leads = leads_store.list_leads()
        for l in leads:
            # Check both to_number and from_number to handle inbound and outbound
            if (to_number and to_number in l.phone) or (from_number and from_number in l.phone):
                lead = l
                break
        
        logger.info("lead_identified", lead_id=lead.id if lead else None, lead_name=lead.name if lead else None)
        
        # Generate initial greeting in ENGLISH
        if config.AGENT_MODE == "llm" and config.has_openai_key():
            logger.info("generating_greeting_with_llm")
            # LLM will return English greeting (to be updated in llm_agent.py)
            english_greeting = llm_agent.get_initial_greeting(lead)
        else:
            # Fallback: simple English greeting
            if lead:
                first_name = lead.name.split()[0]
                english_greeting = f"Hi {first_name}! I'm the agent from Alta. We help companies increase sales with AI agents. How do you handle inbound leads today?"
            else:
                english_greeting = "Hello! I'm the agent from Alta. We help companies increase sales with AI agents. Who am I speaking with?"
        
        logger.info("greeting_generated_english", greeting=english_greeting[:100])

        # Guardrail: if the LLM returns an unhelpful one-word greeting, fall back
        # to a deterministic greeting that includes value prop + a question.
        greeting_words = [w for w in (english_greeting or "").strip().split() if w]
        if len((english_greeting or "").strip()) < 20 or len(greeting_words) < 4:
            logger.warning(
                "greeting_too_short_fallback",
                greeting_repr=repr(english_greeting),
                greeting_len=len(english_greeting or ""),
                greeting_words=len(greeting_words),
            )
            if lead:
                first_name = lead.name.split()[0]
                english_greeting = (
                    f"Hi {first_name}! I'm the agent from Alta. We help companies increase sales with AI agents. "
                    "How do you handle inbound leads today?"
                )
            else:
                english_greeting = (
                    "Hello! I'm the agent from Alta. We help companies increase sales with AI agents. "
                    "How do you handle inbound leads today?"
                )
            logger.info("greeting_fallback_applied", greeting=english_greeting[:100])
        
        # Translate to Hebrew for caller
        hebrew_greeting = translate_en_to_he(english_greeting)
        import re
        HEBREW_RE = re.compile(r"[\u0590-\u05FF]")

        if not hebrew_greeting or not HEBREW_RE.search(hebrew_greeting):
            logger.warning("hebrew_translation_invalid_fallback", value=repr(hebrew_greeting))
            hebrew_greeting = get_caller_text("greeting_default")

        logger.info("greeting_translated_to_hebrew", length=len(hebrew_greeting))
        
        # Build TwiML with proper escaping
        lead_id = lead.id if lead else 0
        twiml = build_voice_twiml(hebrew_greeting, call_sid, lead_id)
        
        # Safety logging for TwiML content lengths
        logger.info(
            "twiml_say_lengths",
            greeting_english_len=len(english_greeting or ""),
            greeting_hebrew_len=len(hebrew_greeting or ""),
            greeting_hebrew_preview=hebrew_greeting[:80] if hebrew_greeting else ""
        )

        
        logger.info("twiml_generated_successfully")
        return Response(content=twiml, media_type="application/xml")
    
    except Exception as e:
        logger.error("voice_webhook_error", error=str(e), traceback=traceback.format_exc())
        
        # Error message to caller in Hebrew
        error_msg_hebrew = get_caller_text("technical_error")
        error_twiml = build_error_twiml(error_msg_hebrew)
        return Response(content=error_twiml, media_type="application/xml")


@app.post("/twilio/process-speech")
async def twilio_process_speech(
    request: Request,
    call_sid: str = "",
    lead_id: int = 0,
    turn: int = 0
):
    """
    Process speech input from Twilio Gather.
    
    Pipeline: Hebrew speech → English translation → English processing → Hebrew translation → Hebrew TwiML
    """
    from app.language.translator import translate_he_to_en, translate_en_to_he
    from app.language.caller_he import get_caller_text
    from app.twiml_builder import (
        build_hangup_twiml,
        build_continue_twiml,
        build_offer_slots_twiml,
        build_meeting_confirmed_twiml
    )
    
    # Get form data from Twilio
    form_data = await request.form()
    hebrew_speech = form_data.get("SpeechResult", "")
    confidence = form_data.get("Confidence", "0")
    
    logger.info("speech_received", call_sid=call_sid, confidence=confidence, speech_length=len(hebrew_speech))
    
    # If no speech detected, end call politely
    if not hebrew_speech:
        logger.info("no_speech_detected")
        no_response_msg = get_caller_text("no_response_retry")
        return Response(content=build_hangup_twiml(no_response_msg), media_type="application/xml")
    
    # TRANSLATE: Hebrew → English
    english_user_input = translate_he_to_en(hebrew_speech)
    logger.info("speech_translated_to_english", user_input=english_user_input)
    
    # Get lead
    lead = leads_store.get_lead_by_id(lead_id) if lead_id > 0 else None
    
    # Retrieve conversation history (TODO: implement Redis/DB storage)
    history = []
    
    # Process with agent logic in ENGLISH
    if config.AGENT_MODE == "llm" and config.has_openai_key():
        english_reply, action, action_payload = llm_agent.decide_next_turn_llm(
            lead=lead,
            history=history,
            last_user_utterance=english_user_input
        )
    else:
        english_reply, action, action_payload = agent_logic.decide_next_turn(
            lead=lead,
            history=history,
            last_user_utterance=english_user_input
        )
    
    logger.info("agent_responded_english", action=action, reply=english_reply[:100])
    
    # TRANSLATE: English → Hebrew
    hebrew_reply = translate_en_to_he(english_reply)
    logger.info("reply_translated_to_hebrew", length=len(hebrew_reply))
    
    # Safety logging for TwiML content
    logger.info("twiml_reply_lengths", 
               reply_english_len=len(english_reply),
               reply_hebrew_len=len(hebrew_reply))
    
    # Build TwiML based on action
    if action == "end_call":
        logger.info("ending_call")
        return Response(content=build_hangup_twiml(hebrew_reply), media_type="application/xml")
    
    elif action == "offer_slots":
        logger.info("offering_meeting_slots")
        twiml = build_offer_slots_twiml(hebrew_reply, call_sid, lead_id, turn)
        return Response(content=twiml, media_type="application/xml")
    
    elif action == "book_meeting":
        logger.info("meeting_booked")
        twiml = build_meeting_confirmed_twiml(hebrew_reply)
        return Response(content=twiml, media_type="application/xml")
    
    else:
        # Continue conversation
        logger.info("continuing_conversation", turn=turn+1)
        twiml = build_continue_twiml(hebrew_reply, call_sid, lead_id, turn)
        return Response(content=twiml, media_type="application/xml")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
