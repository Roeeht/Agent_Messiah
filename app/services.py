"""
Service layer for database operations.
Replaces in-memory storage with database persistence.
"""

from typing import List, Optional
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import json

from app.db_models import DBLead, DBMeeting, DBCallSession, LeadStatus, CallStatus
from app.models import Lead, MeetingSlot
from app.logging_config import get_logger

logger = get_logger(__name__)


class LeadService:
    """Service for managing leads."""
    
    @staticmethod
    def create_lead(db: Session, name: str, phone: str, company: Optional[str] = None, role: Optional[str] = None) -> DBLead:
        """Create a new lead."""
        lead = DBLead(
            name=name,
            phone=phone,
            company=company,
            role=role,
            status=LeadStatus.NEW
        )
        db.add(lead)
        db.commit()
        db.refresh(lead)
        
        logger.info("lead_created", lead_id=lead.id, phone=phone)
        return lead
    
    @staticmethod
    def get_lead(db: Session, lead_id: int) -> Optional[DBLead]:
        """Get lead by ID."""
        return db.query(DBLead).filter(DBLead.id == lead_id).first()
    
    @staticmethod
    def get_lead_by_phone(db: Session, phone: str) -> Optional[DBLead]:
        """Get lead by phone number."""
        return db.query(DBLead).filter(DBLead.phone == phone).first()
    
    @staticmethod
    def list_leads(db: Session, skip: int = 0, limit: int = 100, status: Optional[LeadStatus] = None) -> List[DBLead]:
        """List leads with optional filtering."""
        query = db.query(DBLead)
        
        if status:
            query = query.filter(DBLead.status == status)
        
        return query.offset(skip).limit(limit).all()
    
    @staticmethod
    def update_lead_status(db: Session, lead_id: int, status: LeadStatus) -> Optional[DBLead]:
        """Update lead status."""
        lead = db.query(DBLead).filter(DBLead.id == lead_id).first()
        if lead:
            lead.status = status
            lead.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(lead)
            
            logger.info("lead_status_updated", lead_id=lead_id, status=status.value)
        
        return lead
    
    @staticmethod
    def delete_lead(db: Session, lead_id: int) -> bool:
        """Delete a lead."""
        lead = db.query(DBLead).filter(DBLead.id == lead_id).first()
        if lead:
            db.delete(lead)
            db.commit()
            logger.info("lead_deleted", lead_id=lead_id)
            return True
        return False


class MeetingService:
    """Service for managing meetings."""
    
    @staticmethod
    def create_meeting(db: Session, lead_id: int, start_time: datetime, duration_minutes: int = 30) -> DBMeeting:
        """Create a new meeting."""
        meeting = DBMeeting(
            lead_id=lead_id,
            start=start_time,
            duration_minutes=duration_minutes,
            is_confirmed=True
        )
        db.add(meeting)
        
        # Update lead status
        lead = db.query(DBLead).filter(DBLead.id == lead_id).first()
        if lead:
            lead.status = LeadStatus.MEETING_BOOKED
            lead.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(meeting)
        
        logger.info("meeting_created", meeting_id=meeting.id, lead_id=lead_id, start_time=start_time.isoformat())
        return meeting
    
    @staticmethod
    def get_meeting(db: Session, meeting_id: int) -> Optional[DBMeeting]:
        """Get meeting by ID."""
        return db.query(DBMeeting).filter(DBMeeting.id == meeting_id).first()
    
    @staticmethod
    def list_meetings(db: Session, lead_id: Optional[int] = None, include_cancelled: bool = False) -> List[DBMeeting]:
        """List meetings with optional filtering."""
        query = db.query(DBMeeting)
        
        if lead_id:
            query = query.filter(DBMeeting.lead_id == lead_id)
        
        if not include_cancelled:
            query = query.filter(DBMeeting.is_cancelled == False)
        
        return query.order_by(DBMeeting.start).all()
    
    @staticmethod
    def cancel_meeting(db: Session, meeting_id: int) -> Optional[DBMeeting]:
        """Cancel a meeting."""
        meeting = db.query(DBMeeting).filter(DBMeeting.id == meeting_id).first()
        if meeting:
            meeting.is_cancelled = True
            meeting.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(meeting)
            
            logger.info("meeting_cancelled", meeting_id=meeting_id)
        
        return meeting


class CallSessionService:
    """Service for managing call sessions."""
    
    @staticmethod
    def create_session(db: Session, call_sid: str, lead_id: Optional[int] = None, 
                      from_number: Optional[str] = None, to_number: Optional[str] = None) -> DBCallSession:
        """Create a new call session."""
        session = DBCallSession(
            call_sid=call_sid,
            lead_id=lead_id,
            from_number=from_number,
            to_number=to_number,
            status=CallStatus.INITIATED,
            conversation_history="[]"
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        
        logger.info("call_session_created", call_sid=call_sid, lead_id=lead_id)
        return session
    
    @staticmethod
    def get_session(db: Session, call_sid: str) -> Optional[DBCallSession]:
        """Get call session by call SID."""
        return db.query(DBCallSession).filter(DBCallSession.call_sid == call_sid).first()
    
    @staticmethod
    def update_session_status(db: Session, call_sid: str, status: CallStatus) -> Optional[DBCallSession]:
        """Update call session status."""
        session = db.query(DBCallSession).filter(DBCallSession.call_sid == call_sid).first()
        if session:
            session.status = status
            session.updated_at = datetime.utcnow()
            
            if status == CallStatus.COMPLETED and not session.ended_at:
                session.ended_at = datetime.utcnow()
                if session.started_at:
                    duration = (session.ended_at - session.started_at).total_seconds()
                    session.duration_seconds = int(duration)
            
            db.commit()
            db.refresh(session)
            
            logger.info("call_session_status_updated", call_sid=call_sid, status=status.value)
        
        return session
    
    @staticmethod
    def save_conversation_history(db: Session, call_sid: str, conversation_history: list) -> Optional[DBCallSession]:
        """Save conversation history to database."""
        session = db.query(DBCallSession).filter(DBCallSession.call_sid == call_sid).first()
        if session:
            session.conversation_history = json.dumps(conversation_history)
            session.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(session)
            
            logger.info("conversation_history_saved", call_sid=call_sid, turns=len(conversation_history))
        
        return session
    
    @staticmethod
    def mark_meeting_booked(db: Session, call_sid: str, meeting_id: int) -> Optional[DBCallSession]:
        """Mark that a meeting was booked during this call."""
        session = db.query(DBCallSession).filter(DBCallSession.call_sid == call_sid).first()
        if session:
            session.meeting_booked = True
            session.meeting_id = meeting_id
            session.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(session)
            
            logger.info("call_session_meeting_booked", call_sid=call_sid, meeting_id=meeting_id)
        
        return session
