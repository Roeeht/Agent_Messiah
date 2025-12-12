"""Data models for Agent Messiah application."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class Lead(BaseModel):
    """Lead model representing a potential customer."""
    id: int
    name: str
    company: str
    role: str
    phone: str
    notes: Optional[str] = None


class Meeting(BaseModel):
    """Meeting model representing a scheduled meeting."""
    id: int
    lead_id: int
    start: datetime
    duration_minutes: int
    calendar_link: str


class MeetingSlot(BaseModel):
    """Available meeting slot."""
    start: datetime
    duration_minutes: int
    display_text: str  # Hebrew text to show to user


class AgentTurnRequest(BaseModel):
    """Request model for /agent/turn endpoint."""
    lead_id: Optional[int] = None
    user_utterance: str
    history: Optional[list[dict]] = None


class AgentTurnResponse(BaseModel):
    """Response model for /agent/turn endpoint."""
    agent_reply: str
    action: Optional[str] = None  # "offer_slots", "book_meeting", "end_call", or None
    action_payload: Optional[dict] = None
