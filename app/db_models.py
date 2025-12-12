"""
SQLAlchemy database models for production.
These replace the in-memory storage with persistent database tables.
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.database import Base


class LeadStatus(str, enum.Enum):
    """Lead status enum."""
    NEW = "new"
    CONTACTED = "contacted"
    QUALIFIED = "qualified"
    NOT_INTERESTED = "not_interested"
    MEETING_BOOKED = "meeting_booked"


class CallStatus(str, enum.Enum):
    """Call status enum."""
    INITIATED = "initiated"
    RINGING = "ringing"
    IN_PROGRESS = "in-progress"
    COMPLETED = "completed"
    BUSY = "busy"
    FAILED = "failed"
    NO_ANSWER = "no-answer"


class DBLead(Base):
    """Lead database model."""
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    phone = Column(String(50), unique=True, nullable=False, index=True)
    company = Column(String(255))
    role = Column(String(255))
    notes = Column(Text)
    status = Column(SQLEnum(LeadStatus), default=LeadStatus.NEW)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    meetings = relationship("DBMeeting", back_populates="lead", cascade="all, delete-orphan")
    call_sessions = relationship("DBCallSession", back_populates="lead", cascade="all, delete-orphan")


class DBMeeting(Base):
    """Meeting database model."""
    __tablename__ = "meetings"

    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=False)
    start = Column(DateTime, nullable=False)
    duration_minutes = Column(Integer, default=30)
    calendar_link = Column(String(500))
    
    # Meeting status
    is_confirmed = Column(Boolean, default=False)
    is_cancelled = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    lead = relationship("DBLead", back_populates="meetings")


class DBCallSession(Base):
    """
    Call session model - tracks voice call conversations.
    Stores conversation history and call metadata.
    """
    __tablename__ = "call_sessions"

    id = Column(Integer, primary_key=True, index=True)
    call_sid = Column(String(100), unique=True, nullable=False, index=True)  # Twilio Call SID
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=True)
    
    # Call metadata
    from_number = Column(String(50))
    to_number = Column(String(50))
    status = Column(SQLEnum(CallStatus), default=CallStatus.INITIATED)
    
    # Conversation data (stored as JSON in Redis for active calls, archived here after completion)
    conversation_history = Column(Text)  # JSON string of conversation turns
    
    # Timestamps
    started_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    
    # Outcome
    meeting_booked = Column(Boolean, default=False)
    meeting_id = Column(Integer, ForeignKey("meetings.id"), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    lead = relationship("DBLead", back_populates="call_sessions")
    meeting = relationship("DBMeeting")


class DBCampaign(Base):
    """
    Campaign model - tracks outbound calling campaigns.
    """
    __tablename__ = "campaigns"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    
    # Campaign stats
    total_leads = Column(Integer, default=0)
    calls_completed = Column(Integer, default=0)
    meetings_booked = Column(Integer, default=0)
    
    # Status
    is_active = Column(Boolean, default=True)
    is_paused = Column(Boolean, default=False)
    
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
