from __future__ import annotations

import hashlib

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response

from app import calendar_store, leads_store, llm_agent
from app.config import config
from app.logging_config import logger
from app.redis_client import SessionManager, REDIS_AVAILABLE
from app.security import verify_api_key

router = APIRouter(prefix="/twilio", tags=["Twilio"])


# POST /twilio/call-status
# Gets: Twilio form fields (CallSid, CallStatus, From, To, ...)
# Returns: {"status": "received"}
# Example:
#   curl -X POST http://localhost:8000/twilio/call-status -d 'CallSid=CAxxx&CallStatus=completed'
@router.post("/call-status")
async def twilio_call_status(request: Request):
    """Receive call status updates from Twilio."""

    form_data = await request.form()

    call_sid = form_data.get("CallSid", "")
    call_status = form_data.get("CallStatus", "")
    from_number = form_data.get("From", "")
    to_number = form_data.get("To", "")
    error_code = form_data.get("ErrorCode", "")
    call_duration = form_data.get("CallDuration", "")
    timestamp = form_data.get("Timestamp", "")

    logger.info("call_status", call_sid=call_sid, call_status=call_status)

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


# GET /twilio/debug/{call_sid}?limit=100
# Gets: path param call_sid (str), query param limit (int), and optional X-API-Key header
# Returns: per-call debug events and a reconstructed transcript
# Example:
#   curl -H 'X-API-Key: <key>' http://localhost:8000/twilio/debug/CAxxx?limit=50
@router.get("/debug/{call_sid}")
async def twilio_debug_call(call_sid: str, limit: int = 100, api_key: str = Depends(verify_api_key)):
    """Return recent per-call debug events (development / controlled environments only)."""

    if not config.DEBUG_CALL_EVENTS:
        raise HTTPException(status_code=404, detail="Call debug is disabled")

    session = SessionManager.get_session(call_sid)
    events = SessionManager.get_debug_events(call_sid, limit=limit)

    history_en = session.get("conversation_history") if isinstance(session, dict) else None
    history_he = session.get("conversation_history_he") if isinstance(session, dict) else None
    idem = session.get("idempotency") if isinstance(session, dict) else None

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


# POST /twilio/voice
# Gets: Twilio form fields (CallSid, From, To, ...)
# Returns: TwiML (application/xml)
# Example:
#   curl -X POST http://localhost:8000/twilio/voice -d 'CallSid=CAxxx&From=%2B1555&To=%2B1666'
@router.post("/voice")
async def twilio_voice(request: Request):
    """Twilio webhook for incoming/outgoing calls."""

    import traceback
    import re

    from app.language.caller_he import get_caller_text
    from app.twiml_builder import build_voice_twiml, build_error_twiml

    try:
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

        lead = None
        leads = leads_store.list_leads()
        for l in leads:
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

        SessionManager.save_session(
            call_sid,
            {
                "lead_id": lead.id if lead else 0,
                "conversation_history": [],
                "conversation_history_he": [],
                "idempotency": {},
                "debug_events": [],
                "call_stage": "permission",
            },
        )

        if not config.has_openai_key():
            # LLM-only mode: if OpenAI isn't configured, tell the caller and hang up.
            error_msg_he = get_caller_text("technical_error")
            error_twiml = build_error_twiml(error_msg_he)
            return Response(content=error_twiml, media_type="application/xml")

        # Fast start: do not call the LLM or translation for the initial greeting.
        # We always start with the deterministic permission gate prompt.
        english_greeting = llm_agent.get_permission_gate_greeting(lead)

        SessionManager.append_debug_event(
            call_sid,
            "greeting_generated_en",
            {
                "greeting_en": english_greeting,
            },
        )

        # Caller-facing Hebrew is always the fixed permission prompt (stored in approved Hebrew module).
        hebrew_greeting = get_caller_text("permission_ask")

        SessionManager.add_conversation_turn(call_sid, role="assistant", message=english_greeting)
        SessionManager.add_conversation_turn_he(call_sid, role="assistant", message=hebrew_greeting)

        if getattr(config, "LOG_CALL_TRANSCRIPT", False):
            max_chars = int(getattr(config, "LOG_CALL_TRANSCRIPT_MAX_CHARS", 500) or 500)
            he = (hebrew_greeting or "").strip()
            en = (english_greeting or "").strip()
            if max_chars > 0:
                if len(he) > max_chars:
                    he = he[:max_chars] + "…"
                if len(en) > max_chars:
                    en = en[:max_chars] + "…"
            logger.info("call_transcript_turn", call_sid=call_sid, turn=0, role="assistant", he=he, en=en)

        SessionManager.append_debug_event(
            call_sid,
            "transcript_turn",
            {"turn": 0, "role": "assistant", "content": hebrew_greeting},
        )

        lead_id = lead.id if lead else 0
        SessionManager.update_session(call_sid, {"lead_id": lead_id})
        twiml = build_voice_twiml(hebrew_greeting, call_sid, lead_id)

        SessionManager.append_debug_event(
            call_sid,
            "twiml_voice_generated",
            {
                "twiml": twiml,
                "lead_id": lead_id,
            },
        )

        return Response(content=twiml, media_type="application/xml")

    except Exception as e:
        logger.error("voice_webhook_error", error=str(e), traceback=traceback.format_exc())

        error_msg_hebrew = get_caller_text("technical_error")
        error_twiml = build_error_twiml(error_msg_hebrew)
        return Response(content=error_twiml, media_type="application/xml")


async def _process_hebrew_turn(
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
    import re
    from datetime import datetime

    from app.language.translator import translate_he_to_en, translate_en_to_he
    from app.language.caller_he import (
        get_caller_text,
        get_not_interested_phrases,
        get_permission_yes_phrases,
        get_permission_no_phrases,
        is_goodbye_message,
    )
    from app.twiml_builder import (
        build_hangup_twiml,
        build_continue_twiml,
        build_offer_slots_twiml,
        build_meeting_confirmed_twiml,
        build_record_fallback_twiml,
    )

    HEBREW_RE = re.compile(r"[\u0590-\u05FF]")

    def _log_transcript_turn(*, role: str, he: str | None = None, en: str | None = None) -> None:
        if not getattr(config, "LOG_CALL_TRANSCRIPT", False):
            return
        max_chars = int(getattr(config, "LOG_CALL_TRANSCRIPT_MAX_CHARS", 500) or 500)
        he_txt = (he or "").strip() if he is not None else None
        en_txt = (en or "").strip() if en is not None else None
        if max_chars > 0:
            if he_txt is not None and len(he_txt) > max_chars:
                he_txt = he_txt[:max_chars] + "…"
            if en_txt is not None and len(en_txt) > max_chars:
                en_txt = en_txt[:max_chars] + "…"
        logger.info(
            "call_transcript_turn",
            call_sid=call_sid,
            turn=turn,
            role=role,
            he=he_txt,
            en=en_txt,
        )

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
        return is_goodbye_message(reply_he)

    def _parse_iso_datetime(value: str | None) -> datetime | None:
        if not value:
            return None
        s = value.strip()
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        try:
            return datetime.fromisoformat(s)
        except Exception:
            return None

    def _infer_selected_slot_index(*, speech_he: str, text_en: str, slots: list[dict]) -> int | None:
        """Best-effort mapping of user's response to one of the offered slots.

        Returns 0/1 for a confident match, otherwise None.
        """
        if not slots:
            return None

        # Collect slot hours from the offered slots.
        slot_hours: list[int | None] = []
        for slot in slots:
            if not isinstance(slot, dict):
                slot_hours.append(None)
                continue
            dt = _parse_iso_datetime(slot.get("start"))
            if dt is not None:
                slot_hours.append(dt.hour)
                continue
            display = (slot.get("display_text") or "")
            m = re.search(r"\b(\d{1,2}):(\d{2})\b", display)
            slot_hours.append(int(m.group(1)) if m else None)

        en = (text_en or "").strip().lower()
        he = (speech_he or "").strip().lower()
        combined = f"{en} {he}".strip()

        # Ordinal / option selection.
        if re.search(r"\b(1st|first)\b", en):
            return 0
        if re.search(r"\b(2nd|second)\b", en):
            return 1

        target_hour: int | None = None

        # Explicit hour selection (English).
        if re.search(r"\b10(:00)?\b", en) or re.search(r"\bten\b", en):
            target_hour = 10
        elif re.search(r"\b14(:00)?\b", en):
            target_hour = 14
        elif re.search(r"\b2(:00)?\b", en) and ("pm" in en or "afternoon" in en):
            target_hour = 14

        # Explicit hour selection via numeric tokens in the raw transcript.
        if target_hour is None:
            if re.search(r"\b10(:00)?\b", he):
                target_hour = 10
            elif re.search(r"\b14(:00)?\b", he):
                target_hour = 14

        # Morning/afternoon cues if we have identifiable hours.
        if target_hour is None and any(h is not None for h in slot_hours):
            known_hours = [h for h in slot_hours if h is not None]
            if "morning" in combined:
                target_hour = min(known_hours)
            elif "afternoon" in combined:
                target_hour = max(known_hours)

        if target_hour is None:
            return None

        for idx, hour in enumerate(slot_hours):
            if hour == target_hour:
                return idx
        return None

    speech_norm = (speech_he or "").strip()
    speech_sig = hashlib.sha256(speech_norm.encode("utf-8")).hexdigest() if speech_norm else ""

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

    session = SessionManager.get_session(call_sid) or {"conversation_history": [], "idempotency": {}, "lead_id": lead_id}
    idem = session.get("idempotency") if isinstance(session, dict) else None

    stable_id = (source_id or "").strip() or (speech_sig or "empty")
    idem_key = f"turn:{turn}:{source}:{stable_id}"

    if isinstance(idem, dict) and idem_key in idem:
        return Response(content=idem[idem_key], media_type="application/xml")

    if not speech_norm:
        no_response_msg = get_caller_text("no_response_retry")
        _log_transcript_turn(role="assistant", he=no_response_msg, en=None)
        twiml = build_hangup_twiml(no_response_msg)
        if isinstance(idem, dict):
            idem[idem_key] = twiml
            SessionManager.update_session(call_sid, {"idempotency": idem})
        return Response(content=twiml, media_type="application/xml")

    session_lead_id = session.get("lead_id") if isinstance(session, dict) else None
    effective_lead_id = lead_id if lead_id > 0 else (session_lead_id or 0)
    lead = leads_store.get_lead_by_id(effective_lead_id) if effective_lead_id else None

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
        return Response(content=twiml, media_type="application/xml")

    # Gate the conversation: first answer must be yes/no to permission question.
    stage = session.get("call_stage") if isinstance(session, dict) else None
    if stage == "permission":
        yes_phrases = get_permission_yes_phrases()
        no_phrases = get_permission_no_phrases()
        if any(p in speech_norm for p in no_phrases):
            _log_transcript_turn(role="user", he=speech_he, en=None)
            goodbye = get_caller_text("not_interested_goodbye")
            _log_transcript_turn(role="assistant", he=goodbye, en=None)
            twiml = build_hangup_twiml(goodbye)
            if isinstance(idem, dict):
                idem[idem_key] = twiml
                SessionManager.update_session(call_sid, {"idempotency": idem})
            SessionManager.delete_session(call_sid)
            return Response(content=twiml, media_type="application/xml")

        if any(p in speech_norm for p in yes_phrases):
            SessionManager.update_session(call_sid, {"call_stage": "conversation"})
        else:
            _log_transcript_turn(role="user", he=speech_he, en=None)
            prompt = get_caller_text("permission_clarify")
            _log_transcript_turn(role="assistant", he=prompt, en=None)
            twiml = build_continue_twiml(prompt, call_sid, effective_lead_id, turn)
            if isinstance(idem, dict):
                idem[idem_key] = twiml
                SessionManager.update_session(call_sid, {"idempotency": idem})
            return Response(content=twiml, media_type="application/xml")

    # Fast-path: caller not interested (Hebrew)
    not_interested_phrases = get_not_interested_phrases()
    if any(kw in speech_norm for kw in not_interested_phrases):
        goodbye = get_caller_text("not_interested_goodbye")
        _log_transcript_turn(role="user", he=speech_he, en=None)
        _log_transcript_turn(role="assistant", he=goodbye, en=None)
        twiml = build_hangup_twiml(goodbye)
        if isinstance(idem, dict):
            idem[idem_key] = twiml
            SessionManager.update_session(call_sid, {"idempotency": idem})
        SessionManager.delete_session(call_sid)
        return Response(content=twiml, media_type="application/xml")

    if not config.has_openai_key():
        error_msg = get_caller_text("technical_error")
        _log_transcript_turn(role="assistant", he=error_msg, en=None)
        twiml = build_hangup_twiml(error_msg)
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
        },
    )

    SessionManager.add_conversation_turn_he(call_sid, role="user", message=speech_he)
    SessionManager.append_debug_event(call_sid, "transcript_turn", {"turn": turn, "role": "user", "content": speech_he})
    _log_transcript_turn(role="user", he=speech_he, en=english_user_input)

    history = []
    if isinstance(session, dict) and isinstance(session.get("conversation_history"), list):
        history = session.get("conversation_history")

    SessionManager.add_conversation_turn(call_sid, role="user", message=english_user_input)

    english_reply: str
    action: str | None
    action_payload: dict | None
    decision_source = "llm"

    pending_slots = session.get("pending_slots") if isinstance(session, dict) else None
    has_pending_slots = isinstance(pending_slots, list) and bool(pending_slots)
    if isinstance(pending_slots, list) and pending_slots and lead is not None:
        inferred_index = _infer_selected_slot_index(
            speech_he=speech_he,
            text_en=english_user_input,
            slots=pending_slots,
        )
        if inferred_index is not None and 0 <= inferred_index < len(pending_slots):
            selected = pending_slots[inferred_index] if isinstance(pending_slots[inferred_index], dict) else {}
            selected_start = _parse_iso_datetime(selected.get("start"))
            selected_duration = int(selected.get("duration_minutes", 30) or 30)
            selected_display = (selected.get("display_text") or "").strip() or "the selected time"

            if selected_start is not None:
                meeting = calendar_store.book_meeting(
                    lead_id=lead.id,
                    start=selected_start,
                    duration_minutes=selected_duration,
                )
                english_reply = (
                    f"Excellent! I've scheduled a meeting for you on {selected_display}. "
                    "I'll send you a calendar invitation. Looking forward to the call!"
                )
                action = "book_meeting"
                action_payload = {
                    "meeting_id": meeting.id,
                    "start": meeting.start.isoformat(),
                    "calendar_link": meeting.calendar_link,
                    "slot_index": inferred_index,
                }
                decision_source = "deterministic_slot_match"
                # Clear pending slots to avoid reusing them.
                SessionManager.update_session(call_sid, {"pending_slots": None})
            else:
                inferred_index = None

    if decision_source == "llm":
        english_reply, action, action_payload = llm_agent.decide_next_turn_llm(
            lead=lead,
            history=history,
            last_user_utterance=english_user_input,
        )

    # Guard against duplicate slot offers.
    # If we already offered slots earlier in the call (pending_slots is set) and the
    # model tries to offer again, keep the conversation moving by asking the lead to
    # choose between the existing options.
    if action == "offer_slots" and has_pending_slots:
        opt_text: list[str] = []
        for idx, slot in enumerate(pending_slots[:2]):
            if not isinstance(slot, dict):
                continue
            display = (slot.get("display_text") or "").strip()
            if display:
                opt_text.append(f"Option {idx + 1}: {display}")

        if len(opt_text) >= 2:
            options = f"{opt_text[0]} or {opt_text[1]}"
        elif len(opt_text) == 1:
            options = opt_text[0]
        else:
            options = "the times I just mentioned"

        english_reply = (
            f"Just to confirm, which time works for you: {options}? "
            "You can say 'first' or 'second'. If neither works, tell me what day/time you prefer."
        )
        action = None
        action_payload = None
        decision_source = "guard_repeat_offer_slots"

    SessionManager.append_debug_event(
        call_sid,
        "agent_decision",
        {"turn": turn, "action": action, "action_payload": action_payload, "reply_en": english_reply, "source": decision_source},
    )

    # Persist last action/payload so we can deterministically handle slot selection next turn.
    if action == "offer_slots" and isinstance(action_payload, dict) and isinstance(action_payload.get("slots"), list):
        SessionManager.update_session(
            call_sid,
            {
                "last_action": action,
                "last_action_payload": action_payload,
                "pending_slots": action_payload.get("slots"),
            },
        )
    else:
        SessionManager.update_session(
            call_sid,
            {
                "last_action": action,
                "last_action_payload": action_payload,
            },
        )

    SessionManager.add_conversation_turn(call_sid, role="assistant", message=english_reply)

    hebrew_reply = translate_en_to_he(english_reply)
    SessionManager.add_conversation_turn_he(call_sid, role="assistant", message=hebrew_reply)
    SessionManager.append_debug_event(call_sid, "transcript_turn", {"turn": turn, "role": "assistant", "content": hebrew_reply})
    _log_transcript_turn(role="assistant", he=hebrew_reply, en=english_reply)

    if not action and _looks_like_goodbye(reply_en=english_reply, reply_he=hebrew_reply):
        action = "end_call"

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


# POST /twilio/process-speech?call_sid=CAxxx&lead_id=1&turn=0
# Gets: Twilio form fields including SpeechResult (Hebrew), plus query params call_sid/lead_id/turn
# Returns: TwiML (application/xml)
# Example:
#   curl -X POST 'http://localhost:8000/twilio/process-speech?call_sid=CAxxx&lead_id=1&turn=0' -d 'SpeechResult=<hebrew_yes_or_no>'
@router.post("/process-speech")
async def twilio_process_speech(request: Request, call_sid: str = "", lead_id: int = 0, turn: int = 0):
    """Process speech input from Twilio <Gather input=\"speech\">."""

    form_data = await request.form()
    if not call_sid:
        call_sid = form_data.get("CallSid", "")

    speech_he = form_data.get("SpeechResult", "")
    confidence = form_data.get("Confidence", "0")

    return await _process_hebrew_turn(
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


# POST /twilio/process-recording?call_sid=CAxxx&lead_id=1&turn=0
# Gets: Twilio form fields including RecordingUrl/RecordingSid, plus query params call_sid/lead_id/turn
# Returns: TwiML (application/xml)
# Example:
#   curl -X POST 'http://localhost:8000/twilio/process-recording?call_sid=CAxxx&lead_id=1&turn=0' -d 'RecordingUrl=https://...&RecordingSid=RE...'
@router.post("/process-recording")
async def twilio_process_recording(request: Request, call_sid: str = "", lead_id: int = 0, turn: int = 0):
    """Process Twilio <Record> callback: download recording, transcribe to Hebrew, then process."""

    from app.language.audio_transcriber import transcribe_twilio_recording_url_to_hebrew
    from app.language.caller_he import is_transcription_instructions_echo

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

    transcript_norm = (transcript_he or "").strip()
    if is_transcription_instructions_echo(transcript_norm):
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

    return await _process_hebrew_turn(
        call_sid=call_sid,
        lead_id=lead_id,
        turn=turn,
        speech_he=(transcript_he or ""),
        confidence="recording",
        raw={k: str(v) for k, v in form_data.items()},
        source="recording",
        source_id=recording_sid or "",
        allow_record_fallback=False,
    )
