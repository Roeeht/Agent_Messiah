from fastapi import APIRouter, HTTPException

from app import leads_store
from app.config import config

router = APIRouter(prefix="/outbound", tags=["Outbound"])


# POST /outbound/initiate-call?lead_id=1
# Gets: query param lead_id (int)
# Returns: JSON with call initiation status; if Twilio not configured, returns a dry-run response
# Example:
#   curl -X POST 'http://localhost:8000/outbound/initiate-call?lead_id=1'
@router.post("/initiate-call")
async def initiate_outbound_call(lead_id: int):
    """Initiate an outbound call to a lead using Twilio."""

    lead = leads_store.get_lead_by_id(lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail=f"Lead {lead_id} not found")

    if not config.has_twilio_config():
        return {
            "status": "error",
            "message": "Twilio not configured. Set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, and TWILIO_CALLER_ID in .env",
            "lead": lead.model_dump(),
            "would_call": lead.phone,
        }

    try:
        from twilio.rest import Client

        client = Client(config.TWILIO_ACCOUNT_SID, config.TWILIO_AUTH_TOKEN)

        call = client.calls.create(
            to=lead.phone,
            from_=config.TWILIO_CALLER_ID,
            url=f"{config.BASE_URL}/twilio/voice",
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
            "call_status": call.status,
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to initiate call: {str(e)}",
            "lead": lead.dict(),
        }


# POST /outbound/campaign
# Gets: nothing
# Returns: JSON with per-lead initiation results
# Example:
#   curl -X POST http://localhost:8000/outbound/campaign
@router.post("/campaign")
async def initiate_campaign():
    """Initiate an outbound calling campaign to all leads."""

    if not config.has_twilio_config():
        return {
            "status": "error",
            "message": "Twilio not configured",
            "leads_count": len(leads_store.list_leads()),
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
                method="POST",
            )

            results.append({
                "lead_id": lead.id,
                "lead_name": lead.name,
                "status": "initiated",
                "call_sid": call.sid,
            })

            import time

            time.sleep(2)

        except Exception as e:
            results.append({
                "lead_id": lead.id,
                "lead_name": lead.name,
                "status": "failed",
                "error": str(e),
            })

    return {
        "status": "campaign_initiated",
        "total_leads": len(leads),
        "results": results,
    }
