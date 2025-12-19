from fastapi import APIRouter

from app.models import Meeting
from app import leads_store, calendar_store

router = APIRouter(tags=["Core"])


# GET /
# Gets: nothing
# Returns: basic API metadata and a map of key endpoints
# Example:
#   curl http://localhost:8000/
@router.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Agent Messiah API - Hebrew Speaking AI Sales Agent",
        "version": "1.0.0",
        "description": "Outbound calling campaign agent for Habari's Sales Copnamy - pitches value proposition and books meetings",
        "endpoints": {
            "agent_turn": "/agent/turn",
            "meetings": "/meetings",
            "leads": "/leads",
            "outbound_call": "/outbound/initiate-call",
            "outbound_campaign": "/outbound/campaign",
            "twilio_voice": "/twilio/voice",
            "twilio_process_recording": "/twilio/process-recording",
            "twilio_call_status": "/twilio/call-status",
        },
        "features": [
            "Hebrew speaking AI agent",
            "Outbound calling campaigns",
            "Value proposition pitch",
            "Meeting booking",
            "Twilio voice integration",
        ],
    }


# GET /meetings
# Gets: nothing
# Returns: JSON array of Meeting objects
# Example:
#   curl http://localhost:8000/meetings
@router.get("/meetings", response_model=list[Meeting])
async def list_meetings():
    """List all scheduled meetings."""
    return calendar_store.list_meetings()


# GET /leads
# Gets: nothing
# Returns: JSON array of leads
# Example:
#   curl http://localhost:8000/leads
@router.get("/leads")
async def list_leads():
    """List all leads."""
    return leads_store.list_leads()
