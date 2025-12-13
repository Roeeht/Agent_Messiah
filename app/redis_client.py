"""In-memory session management.

This project intentionally runs without Redis.

We keep a per-call session store in memory so the Twilio webhooks can share
state across multiple HTTP requests during a call.

Notes:
- Sessions do not survive process restarts.
- This is ideal for simple local development (`uvicorn --reload`).
"""

from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, Optional

from app.config import config


# Compatibility exports: older code/health checks reference these.
redis_client = None
REDIS_AVAILABLE = False


# In-memory fallback for local/dev when Redis is unavailable.
# This keeps voice calls functional (basic history + idempotency) without requiring Redis.
_INMEM_SESSIONS: Dict[str, Dict[str, Any]] = {}


def _debug_dir() -> str:
    return os.path.join(os.getcwd(), "debug_calls")


def _debug_file_path(call_sid: str) -> str:
    safe = "".join(ch for ch in (call_sid or "") if ch.isalnum())
    return os.path.join(_debug_dir(), f"{safe}.jsonl")


def _append_debug_event_to_file(call_sid: str, event: Dict[str, Any]) -> None:
    if not call_sid:
        return
    try:
        os.makedirs(_debug_dir(), exist_ok=True)
        path = _debug_file_path(call_sid)
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
    except Exception:
        # Best-effort debug persistence only
        return


def _read_debug_events_from_file(call_sid: str, limit: Optional[int] = None) -> list[Dict[str, Any]]:
    path = _debug_file_path(call_sid)
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        if isinstance(limit, int) and limit > 0:
            lines = lines[-limit:]
        events: list[Dict[str, Any]] = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except Exception:
                continue
        return events
    except Exception:
        return []


class SessionManager:
    """
    Manages conversation sessions in Redis.
    Each voice call gets a session keyed by call_sid.
    """
    
    SESSION_PREFIX = "call_session:"
    
    @classmethod
    def get_session(cls, call_sid: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve session data for a call.
        
        Args:
            call_sid: Twilio Call SID
            
        Returns:
            Session data dict or None if not found
        """
        if not call_sid:
            return None

        return _INMEM_SESSIONS.get(call_sid)
    
    @classmethod
    def save_session(cls, call_sid: str, session_data: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """
        Save session data for a call.
        
        Args:
            call_sid: Twilio Call SID
            session_data: Dictionary of session data
            ttl: Ignored (sessions are in-memory)
            
        Returns:
            True if saved successfully
        """
        if not call_sid:
            return False

        # TTL is ignored in in-memory mode; sessions live until deleted or the
        # process restarts.
        _INMEM_SESSIONS[call_sid] = session_data
        return True
    
    @classmethod
    def update_session(cls, call_sid: str, updates: Dict[str, Any]) -> bool:
        """
        Update specific fields in a session.
        
        Args:
            call_sid: Twilio Call SID
            updates: Dictionary of fields to update
            
        Returns:
            True if updated successfully
        """
        session = cls.get_session(call_sid)
        if session is None:
            return False
        
        session.update(updates)
        return cls.save_session(call_sid, session)
    
    @classmethod
    def delete_session(cls, call_sid: str) -> bool:
        """
        Delete a session (e.g., after call ends).
        
        Args:
            call_sid: Twilio Call SID
            
        Returns:
            True if deleted successfully
        """
        if not call_sid:
            return False

        _INMEM_SESSIONS.pop(call_sid, None)
        return True
    
    @classmethod
    def add_conversation_turn(cls, call_sid: str, role: str, message: str) -> bool:
        """
        Add a conversation turn to the session history.
        
        Args:
            call_sid: Twilio Call SID
            role: "user" or "assistant"
            message: The message content
            
        Returns:
            True if added successfully
        """
        session = cls.get_session(call_sid)
        if session is None:
            # Create new session
            session = {
                "conversation_history": [],
                "lead_id": None,
                "call_start": None
            }
        
        if "conversation_history" not in session:
            session["conversation_history"] = []
        
        session["conversation_history"].append({
            "role": role,
            "content": message
        })
        
        return cls.save_session(call_sid, session)

    @classmethod
    def add_conversation_turn_he(cls, call_sid: str, role: str, message: str) -> bool:
        """Add a caller-facing Hebrew conversation turn to the session history."""
        session = cls.get_session(call_sid)
        if session is None:
            session = {
                "conversation_history": [],
                "conversation_history_he": [],
                "lead_id": None,
                "call_start": None,
                "idempotency": {},
                "debug_events": [],
            }

        if "conversation_history_he" not in session:
            session["conversation_history_he"] = []

        session["conversation_history_he"].append({"role": role, "content": message})
        return cls.save_session(call_sid, session)

    @classmethod
    def append_debug_event(
        cls,
        call_sid: str,
        event_type: str,
        payload: Dict[str, Any],
        max_events: Optional[int] = None,
    ) -> bool:
        """Append a debug event to a per-call session (if enabled).

        Events are stored under session key `debug_events` as a bounded list.
        """
        if not call_sid:
            return False

        if not config.DEBUG_CALL_EVENTS:
            return False

        session = cls.get_session(call_sid) or {}
        if not isinstance(session, dict):
            session = {}

        # Ensure expected session shape so /twilio/debug has meaningful summary even
        # if status callbacks arrive before /twilio/voice initializes the session.
        session.setdefault("lead_id", None)
        session.setdefault("conversation_history", [])
        session.setdefault("idempotency", {})

        events = session.get("debug_events")
        if not isinstance(events, list):
            events = []

        event = {"ts": time.time(), "type": event_type, "payload": payload}
        events.append(event)

        # Persist debug events to disk so they survive server restarts and work
        # even when Redis is unavailable.
        _append_debug_event_to_file(call_sid, event)

        limit = max_events if isinstance(max_events, int) and max_events > 0 else config.DEBUG_CALL_EVENTS_MAX
        if isinstance(limit, int) and limit > 0 and len(events) > limit:
            events = events[-limit:]

        session["debug_events"] = events
        return cls.save_session(call_sid, session)

    @classmethod
    def get_debug_events(cls, call_sid: str, limit: Optional[int] = None) -> list[Dict[str, Any]]:
        """Get recent debug events for a call session."""
        session = cls.get_session(call_sid) or {}
        if not isinstance(session, dict):
            return _read_debug_events_from_file(call_sid, limit=limit)

        events = session.get("debug_events")
        if not isinstance(events, list):
            return _read_debug_events_from_file(call_sid, limit=limit)

        if isinstance(limit, int) and limit > 0:
            return events[-limit:]
        return events
