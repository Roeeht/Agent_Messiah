"""Main FastAPI application."""

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, JSONResponse
import hashlib
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
from app.security import verify_api_key

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
            "twilio_process_recording": "/twilio/process-recording",
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
            status_callback_method="POST",
            status_callback_event=["initiated", "ringing", "answered", "completed"],
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
    from_number = form_data.get("From", "")
    to_number = form_data.get("To", "")
    error_code = form_data.get("ErrorCode", "")
    call_duration = form_data.get("CallDuration", "")
    timestamp = form_data.get("Timestamp", "")
    
    logger.info("call_status", call_sid=call_sid, call_status=call_status)

    # Optional debug feed
    SessionManager.append_debug_event(
        call_sid,
        "call_status",
        {
            "call_status": call_status,
            "from_number": from_number,
            "to_number": to_number,
            "error_code": error_code,
            "call_duration": call_duration,
            "timestamp": timestamp,
            "raw": {k: str(v) for k, v in form_data.items()},
        },
    )
    
    return {"status": "received"}


@app.get("/twilio/debug/{call_sid}")
async def twilio_debug_call(call_sid: str, limit: int = 100, api_key: str = Depends(verify_api_key)):
    """Return recent per-call debug events (development / controlled environments only).

    Enable with DEBUG_CALL_EVENTS=True. Protected by X-API-Key if API_KEY is set.
    """
    if not config.DEBUG_CALL_EVENTS:
        raise HTTPException(status_code=404, detail="Call debug is disabled")

    session = SessionManager.get_session(call_sid)
    events = SessionManager.get_debug_events(call_sid, limit=limit)

    history_en = session.get("conversation_history") if isinstance(session, dict) else None
    history_he = session.get("conversation_history_he") if isinstance(session, dict) else None
    idem = session.get("idempotency") if isinstance(session, dict) else None

    # Prefer a transcript derived from debug events because sessions may be deleted on call end.
    transcript_he: list[dict] = []
    if isinstance(events, list):
        for event in events:
            if not isinstance(event, dict):
                continue
            if event.get("type") != "transcript_turn":
                continue
            payload = event.get("payload")
            if not isinstance(payload, dict):
                continue
            role = (payload.get("role") or "").strip()
            content = (payload.get("content") or "").strip()
            if role not in ("user", "assistant"):
                continue
            if not content:
                continue
            entry = {"role": role, "content": content}
            if "turn" in payload:
                entry["turn"] = payload.get("turn")
            transcript_he.append(entry)

    # Fallback: session history (only available while session exists)
    if not transcript_he and isinstance(history_he, list):
        for t in history_he:
            if not isinstance(t, dict):
                continue
            role = (t.get("role") or "").strip()
            content = (t.get("content") or "").strip()
            if role in ("user", "assistant") and content:
                transcript_he.append({"role": role, "content": content})

    lead_said = [t["content"] for t in transcript_he if t.get("role") == "user"]
    agent_said = [t["content"] for t in transcript_he if t.get("role") == "assistant"]

    summary = {
        "lead_id": session.get("lead_id") if isinstance(session, dict) else None,
        "history_turns_en": len(history_en) if isinstance(history_en, list) else 0,
        "history_turns_he": len(history_he) if isinstance(history_he, list) else 0,
        "idempotency_keys": len(idem) if isinstance(idem, dict) else 0,
        "redis_available": REDIS_AVAILABLE,
        "session_found": bool(session),
    }

    if not session and not events:
        raise HTTPException(status_code=404, detail="Call session not found")

    return {
        "call_sid": call_sid,
        "summary": summary,
        "events": events,
        "transcript": {
            "he": transcript_he,
            "lead_said": lead_said,
            "agent_said": agent_said,
        },
    }


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

        SessionManager.append_debug_event(
            call_sid,
            "voice_webhook_called",
            {
                "from_number": from_number,
                "to_number": to_number,
            },
        )
        
        # Find lead (internal logic - English)
        lead = None
        leads = leads_store.list_leads()
        for l in leads:
            # Check both to_number and from_number to handle inbound and outbound
            if (to_number and to_number in l.phone) or (from_number and from_number in l.phone):
                lead = l
                break
        
        logger.info("lead_identified", lead_id=lead.id if lead else None, lead_name=lead.name if lead else None)

        SessionManager.append_debug_event(
            call_sid,
            "lead_identified",
            {
                "lead_id": lead.id if lead else None,
                "lead_name": lead.name if lead else None,
            },
        )

        # Initialize / reset per-call session state (history + idempotency)
        SessionManager.save_session(
            call_sid,
            {
                "lead_id": lead.id if lead else 0,
                "conversation_history": [],
                "idempotency": {},
                "debug_events": [],
            },
        )
        
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

        SessionManager.append_debug_event(
            call_sid,
            "greeting_generated_en",
            {
                "greeting_en": english_greeting,
                "agent_mode": config.AGENT_MODE,
            },
        )

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

        SessionManager.append_debug_event(
            call_sid,
            "greeting_translated_he",
            {
                "greeting_he": hebrew_greeting,
            },
        )

        # Persist the English greeting as the first assistant message so subsequent turns have context.
        SessionManager.add_conversation_turn(call_sid, role="assistant", message=english_greeting)

        # Persist caller-facing Hebrew for debugging
        SessionManager.add_conversation_turn_he(call_sid, role="assistant", message=hebrew_greeting)

        # Human-friendly transcript stream (Hebrew)
        SessionManager.append_debug_event(
            call_sid,
            "transcript_turn",
            {"turn": 0, "role": "assistant", "content": hebrew_greeting},
        )
        if getattr(config, "LOG_CALL_TRANSCRIPT", False):
            max_chars = int(getattr(config, "LOG_CALL_TRANSCRIPT_MAX_CHARS", 500) or 500)
            text = (hebrew_greeting or "").strip()
            if len(text) > max_chars:
                text = text[:max_chars] + "…"
            logger.info("call_transcript_turn", call_sid=call_sid, turn=0, role="assistant", content=text)
        
        # Build TwiML with proper escaping
        lead_id = lead.id if lead else 0
        SessionManager.update_session(call_sid, {"lead_id": lead_id})
        twiml = build_voice_twiml(hebrew_greeting, call_sid, lead_id)

        SessionManager.append_debug_event(
            call_sid,
            "gather_language_effective",
            {
                "caller_language": config.CALLER_LANGUAGE,
            },
        )

        SessionManager.append_debug_event(
            call_sid,
            "twiml_voice_generated",
            {
                "twiml": twiml,
                "lead_id": lead_id,
            },
        )
        
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

        SessionManager.append_debug_event(
            call_sid,
            "voice_webhook_error",
            {
                "error": str(e),
            },
        )
        
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
    """Process speech input from Twilio <Gather input="speech">.

    Pipeline: Hebrew speech → English translation → English processing → Hebrew translation → Hebrew TwiML
    """

    async def _handle_turn(
        *,
        call_sid: str,
        lead_id: int,
        turn: int,
        speech_he: str,
        confidence: str,
        raw: dict,
        source: str,
        source_id: str,
        allow_record_fallback: bool,
    ) -> Response:
        from app.language.translator import translate_he_to_en, translate_en_to_he
        from app.language.caller_he import get_caller_text
        from app.twiml_builder import (
            build_hangup_twiml,
            build_continue_twiml,
            build_offer_slots_twiml,
            build_meeting_confirmed_twiml,
            build_record_fallback_twiml,
        )
        import re

        HEBREW_RE = re.compile(r"[\u0590-\u05FF]")

        def _log_transcript_turn(*, role: str, content: str) -> None:
            if not getattr(config, "LOG_CALL_TRANSCRIPT", False):
                return
            max_chars = int(getattr(config, "LOG_CALL_TRANSCRIPT_MAX_CHARS", 500) or 500)
            if max_chars <= 0:
                max_chars = 500
            text = (content or "").strip()
            if len(text) > max_chars:
                text = text[:max_chars] + "…"
            logger.info("call_transcript_turn", call_sid=call_sid, turn=turn, role=role, content=text)

        def _looks_like_goodbye(*, reply_en: str, reply_he: str) -> bool:
            en = (reply_en or "").strip().lower()
            if any(p in en for p in [
                "have a good day",
                "have a nice day",
                "have a great day",
                "have a wonderful day",
                "have a great one",
                "goodbye",
                "bye",
                "take care",
                "thanks for your time",
            ]):
                return True
            goodbye_he = (get_caller_text("goodbye") or "").strip()
            if goodbye_he and goodbye_he in (reply_he or ""):
                return True
            # Avoid false-positives on polite mid-call "תודה".
            he = (reply_he or "")
            if any(kw in he for kw in ["להתראות", "ביי", "נתראה", "לילה טוב", "ערב טוב", "שבת שלום"]):
                return True
            # Day-wishes like "שיהיה לך יום נפלא/נהדר/מקסים/טוב".
            if re.search(r"שיהיה(?: לך)? יום (?:טוב|נפלא|נהדר|מקסים|מעולה)", he):
                return True
            if re.search(r"יום (?:טוב|נפלא|נהדר|מקסים|מעולה)", he):
                return True
            return False

        speech_norm = (speech_he or "").strip()
        speech_sig = hashlib.sha256(speech_norm.encode("utf-8")).hexdigest() if speech_norm else ""

        logger.info(
            "speech_received",
            call_sid=call_sid,
            turn=turn,
            confidence=confidence,
            speech_length=len(speech_he or ""),
            source=source,
        )

        SessionManager.append_debug_event(
            call_sid,
            "speech_received",
            {
                "turn": turn,
                "confidence": confidence,
                "source": source,
                "source_id": source_id,
                "speech_he": speech_he,
                "speech_sha256": speech_sig,
                "raw": raw,
            },
        )

        # Load per-call session (history + idempotency cache)
        session = SessionManager.get_session(call_sid) or {"conversation_history": [], "idempotency": {}, "lead_id": lead_id}
        idem = session.get("idempotency") if isinstance(session, dict) else None

        stable_id = (source_id or "").strip() or (speech_sig or "empty")
        idem_key = f"turn:{turn}:{source}:{stable_id}"

        # Idempotency: Twilio may retry webhooks; return cached TwiML if same request repeats
        if isinstance(idem, dict) and idem_key in idem:
            logger.warning("twilio_retry_deduped", call_sid=call_sid, turn=turn, source=source)
            SessionManager.append_debug_event(
                call_sid,
                "twilio_retry_deduped",
                {
                    "turn": turn,
                    "source": source,
                    "idem_key": idem_key,
                },
            )
            return Response(content=idem[idem_key], media_type="application/xml")

        # If no speech detected, end call politely
        if not speech_norm:
            logger.info("no_speech_detected", call_sid=call_sid, turn=turn, source=source)
            no_response_msg = get_caller_text("no_response_retry")
            twiml = build_hangup_twiml(no_response_msg)
            if isinstance(idem, dict):
                idem[idem_key] = twiml
                SessionManager.update_session(call_sid, {"idempotency": idem})

            SessionManager.append_debug_event(
                call_sid,
                "no_speech_hangup",
                {
                    "turn": turn,
                    "source": source,
                    "twiml": twiml,
                },
            )
            return Response(content=twiml, media_type="application/xml")

        # Resolve lead_id from params or session
        session_lead_id = session.get("lead_id") if isinstance(session, dict) else None
        effective_lead_id = lead_id if lead_id > 0 else (session_lead_id or 0)
        lead = leads_store.get_lead_by_id(effective_lead_id) if effective_lead_id else None

        # ASR fallback: if we're expecting Hebrew but Twilio gave non-Hebrew transcript, record + transcribe.
        caller_is_hebrew = ((config.CALLER_LANGUAGE or "").strip().lower().startswith("he"))
        transcript_has_hebrew = bool(HEBREW_RE.search(speech_norm))
        if (
            allow_record_fallback
            and caller_is_hebrew
            and getattr(config, "HEBREW_ASR_FALLBACK_TO_RECORDING", False)
            and not transcript_has_hebrew
            and config.has_openai_key()
            and config.has_twilio_auth()
        ):
            prompt = get_caller_text("asr_retry_recording")
            twiml = build_record_fallback_twiml(prompt, call_sid, effective_lead_id, turn)

            if isinstance(idem, dict):
                idem[idem_key] = twiml
                SessionManager.update_session(call_sid, {"idempotency": idem})

            SessionManager.append_debug_event(
                call_sid,
                "asr_fallback_to_recording",
                {
                    "turn": turn,
                    "source": source,
                    "speech_he": speech_he,
                    "twiml": twiml,
                },
            )
            return Response(content=twiml, media_type="application/xml")

        # Fast-path: caller not interested (handle Hebrew directly)
        from app.language.caller_he import get_not_interested_phrases
        not_interested_phrases = get_not_interested_phrases()
        if any(kw in speech_norm for kw in not_interested_phrases):
            logger.info("caller_not_interested_detected", call_sid=call_sid, turn=turn)
            goodbye = get_caller_text("goodbye")
            twiml = build_hangup_twiml(goodbye)
            if isinstance(idem, dict):
                idem[idem_key] = twiml
                SessionManager.update_session(call_sid, {"idempotency": idem})

            SessionManager.append_debug_event(
                call_sid,
                "not_interested_hangup",
                {
                    "turn": turn,
                    "speech_he": speech_he,
                    "twiml": twiml,
                },
            )
            SessionManager.delete_session(call_sid)
            return Response(content=twiml, media_type="application/xml")

        # Always treat the caller utterance as Hebrew and translate HE→EN for internal processing.
        english_user_input = translate_he_to_en(speech_he)
        translation_ok = bool((english_user_input or "").strip()) and not HEBREW_RE.search(english_user_input)
        translation_mode = "he_to_en" if translation_ok else "he_to_en_fallback_he"

        logger.info(
            "speech_translated_to_english",
            call_sid=call_sid,
            translation_mode=translation_mode,
            speech_he=speech_he,
            user_input_en=english_user_input,
        )

        SessionManager.append_debug_event(
            call_sid,
            "input_normalized_to_en",
            {
                "turn": turn,
                "translation_mode": translation_mode,
                "speech_he": speech_he,
                "speech_en": english_user_input,
            },
        )

        # Persist user turn in Hebrew and English
        SessionManager.add_conversation_turn_he(call_sid, role="user", message=speech_he)
        SessionManager.append_debug_event(
            call_sid,
            "transcript_turn",
            {"turn": turn, "role": "user", "content": speech_he},
        )
        _log_transcript_turn(role="user", content=speech_he)

        # Pull English conversation history
        history = []
        if isinstance(session, dict) and isinstance(session.get("conversation_history"), list):
            history = session.get("conversation_history")

        # Persist user turn in English so the agent has context
        SessionManager.add_conversation_turn(call_sid, role="user", message=english_user_input)

        # Process with agent logic in ENGLISH
        if config.AGENT_MODE == "llm" and config.has_openai_key():
            english_reply, action, action_payload = llm_agent.decide_next_turn_llm(
                lead=lead,
                history=history,
                last_user_utterance=english_user_input,
            )
        else:
            english_reply, action, action_payload = agent_logic.decide_next_turn(
                lead=lead,
                history=history,
                last_user_utterance=english_user_input,
            )

        logger.info("agent_responded_english", call_sid=call_sid, action=action, reply=english_reply[:100])

        SessionManager.append_debug_event(
            call_sid,
            "agent_decision",
            {
                "turn": turn,
                "action": action,
                "action_payload": action_payload,
                "reply_en": english_reply,
            },
        )

        # Persist assistant response in English
        SessionManager.add_conversation_turn(call_sid, role="assistant", message=english_reply)

        # TRANSLATE: English → Hebrew
        hebrew_reply = translate_en_to_he(english_reply)
        logger.info("reply_translated_to_hebrew", call_sid=call_sid, length=len(hebrew_reply))

        # Persist assistant response in Hebrew for debugging
        SessionManager.add_conversation_turn_he(call_sid, role="assistant", message=hebrew_reply)
        SessionManager.append_debug_event(
            call_sid,
            "transcript_turn",
            {"turn": turn, "role": "assistant", "content": hebrew_reply},
        )
        _log_transcript_turn(role="assistant", content=hebrew_reply)

        # Safety: if the model says goodbye but didn't set end_call, force a hangup.
        if not action and _looks_like_goodbye(reply_en=english_reply, reply_he=hebrew_reply):
            SessionManager.append_debug_event(
                call_sid,
                "end_call_forced",
                {"turn": turn, "reason": "goodbye_heuristic", "reply_en": english_reply, "reply_he": hebrew_reply},
            )
            action = "end_call"

        SessionManager.append_debug_event(
            call_sid,
            "translated_en_to_he",
            {
                "turn": turn,
                "reply_en": english_reply,
                "reply_he": hebrew_reply,
            },
        )

        # Safety logging for TwiML content
        logger.info(
            "twiml_reply_lengths",
            call_sid=call_sid,
            reply_english_len=len(english_reply),
            reply_hebrew_len=len(hebrew_reply),
        )

        # Build TwiML based on action
        if action == "end_call":
            logger.info("ending_call", call_sid=call_sid)
            twiml = build_hangup_twiml(hebrew_reply)
            if isinstance(idem, dict):
                idem[idem_key] = twiml
                SessionManager.update_session(call_sid, {"idempotency": idem})
            SessionManager.delete_session(call_sid)
            return Response(content=twiml, media_type="application/xml")

        if action == "offer_slots":
            logger.info("offering_meeting_slots", call_sid=call_sid)
            twiml = build_offer_slots_twiml(hebrew_reply, call_sid, effective_lead_id, turn)
            if isinstance(idem, dict):
                idem[idem_key] = twiml
                SessionManager.update_session(call_sid, {"idempotency": idem})
            return Response(content=twiml, media_type="application/xml")

        if action == "book_meeting":
            logger.info("meeting_booked", call_sid=call_sid)
            twiml = build_meeting_confirmed_twiml(hebrew_reply)
            if isinstance(idem, dict):
                idem[idem_key] = twiml
                SessionManager.update_session(call_sid, {"idempotency": idem})
            SessionManager.delete_session(call_sid)
            return Response(content=twiml, media_type="application/xml")

        # Continue conversation
        logger.info("continuing_conversation", call_sid=call_sid, turn=turn + 1)
        twiml = build_continue_twiml(hebrew_reply, call_sid, effective_lead_id, turn)
        if isinstance(idem, dict):
            idem[idem_key] = twiml
            SessionManager.update_session(call_sid, {"idempotency": idem})
        return Response(content=twiml, media_type="application/xml")

    # Get form data from Twilio
    form_data = await request.form()
    if not call_sid:
        call_sid = form_data.get("CallSid", "")

    speech_he = form_data.get("SpeechResult", "")
    confidence = form_data.get("Confidence", "0")

    return await _handle_turn(
        call_sid=call_sid,
        lead_id=lead_id,
        turn=turn,
        speech_he=speech_he,
        confidence=confidence,
        raw={k: str(v) for k, v in form_data.items()},
        source="gather",
        source_id="",
        allow_record_fallback=True,
    )


@app.post("/twilio/process-recording")
async def twilio_process_recording(
    request: Request,
    call_sid: str = "",
    lead_id: int = 0,
    turn: int = 0,
):
    """Process Twilio <Record> callback.

    Downloads the recording from Twilio and transcribes it to Hebrew using OpenAI,
    then continues the same pipeline as speech gather.
    """
    from app.language.audio_transcriber import transcribe_twilio_recording_url_to_hebrew

    # Get form data from Twilio
    form_data = await request.form()
    if not call_sid:
        call_sid = form_data.get("CallSid", "")

    recording_url = form_data.get("RecordingUrl", "")
    recording_sid = form_data.get("RecordingSid", "")
    recording_duration = form_data.get("RecordingDuration", "")

    SessionManager.append_debug_event(
        call_sid,
        "recording_received",
        {
            "turn": turn,
            "recording_sid": recording_sid,
            "recording_url": recording_url,
            "recording_duration": recording_duration,
            "raw": {k: str(v) for k, v in form_data.items()},
        },
    )

    transcript_he, media_url = transcribe_twilio_recording_url_to_hebrew(recording_url)

    # Defensive: some transcription backends may echo prompt/instructions.
    # If we detect that, treat it as an empty/invalid transcript.
    transcript_norm = (transcript_he or "").strip()
    if transcript_norm and (
        "תמלול של שיחת טלפון" in transcript_norm
        or "תמלל רק את מה שהדובר" in transcript_norm
        or "החזר טקסט ריק" in transcript_norm
    ):
        SessionManager.append_debug_event(
            call_sid,
            "transcription_filtered",
            {"turn": turn, "reason": "echoed_instructions", "transcript_he": transcript_norm},
        )
        transcript_he = ""

    SessionManager.append_debug_event(
        call_sid,
        "recording_transcribed",
        {
            "turn": turn,
            "recording_sid": recording_sid,
            "media_url": media_url,
            "transcript_he": transcript_he,
        },
    )

    # Now run the same pipeline as Gather.
    # We call the /twilio/process-speech handler logic by duplicating its implementation here.
    # To avoid large duplication, we re-import and inline a small helper.
    from app.language.translator import translate_he_to_en, translate_en_to_he
    from app.language.caller_he import get_caller_text
    from app.twiml_builder import (
        build_hangup_twiml,
        build_record_fallback_twiml,
        build_continue_twiml,
        build_offer_slots_twiml,
        build_meeting_confirmed_twiml,
    )
    import re

    HEBREW_RE = re.compile(r"[\u0590-\u05FF]")

    def _log_transcript_turn(*, role: str, content: str) -> None:
        if not getattr(config, "LOG_CALL_TRANSCRIPT", False):
            return
        max_chars = int(getattr(config, "LOG_CALL_TRANSCRIPT_MAX_CHARS", 500) or 500)
        if max_chars <= 0:
            max_chars = 500
        text = (content or "").strip()
        if len(text) > max_chars:
            text = text[:max_chars] + "…"
        logger.info("call_transcript_turn", call_sid=call_sid, turn=turn, role=role, content=text)

    def _looks_like_goodbye(*, reply_en: str, reply_he: str) -> bool:
        en = (reply_en or "").strip().lower()
        if any(p in en for p in [
            "have a good day",
            "have a nice day",
            "have a great day",
            "have a wonderful day",
            "have a great one",
            "goodbye",
            "bye",
            "take care",
            "thanks for your time",
        ]):
            return True
        goodbye_he = (get_caller_text("goodbye") or "").strip()
        if goodbye_he and goodbye_he in (reply_he or ""):
            return True
        # Extra safety: common Hebrew closings (avoid treating plain "תודה" as a hangup).
        he = (reply_he or "")
        if any(kw in he for kw in ["להתראות", "ביי", "נתראה", "לילה טוב", "ערב טוב", "שבת שלום"]):
            return True
        if re.search(r"שיהיה(?: לך)? יום (?:טוב|נפלא|נהדר|מקסים|מעולה)", he):
            return True
        if re.search(r"יום (?:טוב|נפלא|נהדר|מקסים|מעולה)", he):
            return True
        return False
    speech_he = (transcript_he or "").strip()
    speech_sig = hashlib.sha256(speech_he.encode("utf-8")).hexdigest() if speech_he else ""

    SessionManager.append_debug_event(
        call_sid,
        "speech_received",
        {
            "turn": turn,
            "confidence": "recording",
            "source": "recording",
            "source_id": recording_sid or "",
            "speech_he": speech_he,
            "speech_sha256": speech_sig,
        },
    )

    session = SessionManager.get_session(call_sid) or {"conversation_history": [], "idempotency": {}, "lead_id": lead_id}
    idem = session.get("idempotency") if isinstance(session, dict) else None
    stable_id = (recording_sid or "").strip() or (speech_sig or "empty")
    idem_key = f"turn:{turn}:recording:{stable_id}"

    if isinstance(idem, dict) and idem_key in idem:
        return Response(content=idem[idem_key], media_type="application/xml")

    if not speech_he:
        # One retry: ask to repeat and record again, then hang up if still empty.
        retried_turns = session.get("recording_empty_retry_turns") if isinstance(session, dict) else None
        if not isinstance(retried_turns, list):
            retried_turns = []
        if turn not in retried_turns:
            retried_turns.append(turn)
            if isinstance(session, dict):
                SessionManager.update_session(call_sid, {"recording_empty_retry_turns": retried_turns})
            prompt = get_caller_text("asr_retry_recording")
            twiml = build_record_fallback_twiml(prompt, call_sid, lead_id, turn)
            if isinstance(idem, dict):
                idem[idem_key] = twiml
                SessionManager.update_session(call_sid, {"idempotency": idem})
            return Response(content=twiml, media_type="application/xml")

        no_response_msg = get_caller_text("no_response_retry")
        twiml = build_hangup_twiml(no_response_msg)
        if isinstance(idem, dict):
            idem[idem_key] = twiml
            SessionManager.update_session(call_sid, {"idempotency": idem})
        return Response(content=twiml, media_type="application/xml")

    # Resolve lead_id from params or session
    session_lead_id = session.get("lead_id") if isinstance(session, dict) else None
    effective_lead_id = lead_id if lead_id > 0 else (session_lead_id or 0)
    lead = leads_store.get_lead_by_id(effective_lead_id) if effective_lead_id else None

    # Fast-path: caller not interested (handle Hebrew directly)
    from app.language.caller_he import get_not_interested_phrases
    not_interested_phrases = get_not_interested_phrases()
    if any(kw in speech_he for kw in not_interested_phrases):
        goodbye = get_caller_text("goodbye")
        twiml = build_hangup_twiml(goodbye)
        if isinstance(idem, dict):
            idem[idem_key] = twiml
            SessionManager.update_session(call_sid, {"idempotency": idem})
        SessionManager.delete_session(call_sid)
        return Response(content=twiml, media_type="application/xml")

    english_user_input = translate_he_to_en(speech_he)
    translation_ok = bool((english_user_input or "").strip()) and not HEBREW_RE.search(english_user_input)
    translation_mode = "he_to_en" if translation_ok else "he_to_en_fallback_he"

    SessionManager.append_debug_event(
        call_sid,
        "input_normalized_to_en",
        {
            "turn": turn,
            "translation_mode": translation_mode,
            "speech_he": speech_he,
            "speech_en": english_user_input,
            "source": "recording",
        },
    )

    SessionManager.add_conversation_turn_he(call_sid, role="user", message=speech_he)
    SessionManager.append_debug_event(
        call_sid,
        "transcript_turn",
        {"turn": turn, "role": "user", "content": speech_he},
    )
    _log_transcript_turn(role="user", content=speech_he)
    SessionManager.add_conversation_turn(call_sid, role="user", message=english_user_input)

    history = []
    if isinstance(session, dict) and isinstance(session.get("conversation_history"), list):
        history = session.get("conversation_history")

    if config.AGENT_MODE == "llm" and config.has_openai_key():
        english_reply, action, action_payload = llm_agent.decide_next_turn_llm(
            lead=lead,
            history=history,
            last_user_utterance=english_user_input,
        )
    else:
        english_reply, action, action_payload = agent_logic.decide_next_turn(
            lead=lead,
            history=history,
            last_user_utterance=english_user_input,
        )

    SessionManager.add_conversation_turn(call_sid, role="assistant", message=english_reply)
    hebrew_reply = translate_en_to_he(english_reply)
    SessionManager.add_conversation_turn_he(call_sid, role="assistant", message=hebrew_reply)
    SessionManager.append_debug_event(
        call_sid,
        "transcript_turn",
        {"turn": turn, "role": "assistant", "content": hebrew_reply},
    )
    _log_transcript_turn(role="assistant", content=hebrew_reply)

    # Safety: if the model says goodbye but didn't set end_call, force a hangup.
    if not action and _looks_like_goodbye(reply_en=english_reply, reply_he=hebrew_reply):
        SessionManager.append_debug_event(
            call_sid,
            "end_call_forced",
            {"turn": turn, "reason": "goodbye_heuristic", "reply_en": english_reply, "reply_he": hebrew_reply},
        )
        action = "end_call"

    SessionManager.append_debug_event(
        call_sid,
        "translated_en_to_he",
        {
            "turn": turn,
            "reply_en": english_reply,
            "reply_he": hebrew_reply,
            "source": "recording",
        },
    )

    if action == "end_call":
        twiml = build_hangup_twiml(hebrew_reply)
        if isinstance(idem, dict):
            idem[idem_key] = twiml
            SessionManager.update_session(call_sid, {"idempotency": idem})
        SessionManager.delete_session(call_sid)
        return Response(content=twiml, media_type="application/xml")

    if action == "offer_slots":
        twiml = build_offer_slots_twiml(hebrew_reply, call_sid, effective_lead_id, turn)
        if isinstance(idem, dict):
            idem[idem_key] = twiml
            SessionManager.update_session(call_sid, {"idempotency": idem})
        return Response(content=twiml, media_type="application/xml")

    if action == "book_meeting":
        twiml = build_meeting_confirmed_twiml(hebrew_reply)
        if isinstance(idem, dict):
            idem[idem_key] = twiml
            SessionManager.update_session(call_sid, {"idempotency": idem})
        SessionManager.delete_session(call_sid)
        return Response(content=twiml, media_type="application/xml")

    twiml = build_continue_twiml(hebrew_reply, call_sid, effective_lead_id, turn)
    if isinstance(idem, dict):
        idem[idem_key] = twiml
        SessionManager.update_session(call_sid, {"idempotency": idem})
    return Response(content=twiml, media_type="application/xml")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
