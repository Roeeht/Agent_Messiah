"""
Async job processing with Celery.
For background tasks like outbound campaign calling.
"""

from celery import Celery
from app.config import config

# Initialize Celery with Redis broker
celery_app = Celery(
    'agent_messiah',
    broker=config.REDIS_URL,
    backend=config.REDIS_URL
)

# Celery configuration
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 minutes
    worker_prefetch_multiplier=1,
)


@celery_app.task(name='make_outbound_call')
def make_outbound_call_task(lead_id: int):
    """
    Background task to make an outbound call to a lead.
    
    Args:
        lead_id: ID of the lead to call
        
    Returns:
        dict: Call result with status and call_sid
    """
    from sqlalchemy.orm import Session
    from app.database import SessionLocal
    from app.services import LeadService, CallSessionService
    from app.db_models import LeadStatus, CallStatus
    from app.logging_config import logger
    from twilio.rest import Client
    
    db = SessionLocal()
    try:
        # Get lead from database
        lead = LeadService.get_lead(db, lead_id)
        if not lead:
            logger.error("lead_not_found", lead_id=lead_id)
            return {"status": "error", "message": "Lead not found"}
        
        # Initialize Twilio client
        client = Client(config.TWILIO_ACCOUNT_SID, config.TWILIO_AUTH_TOKEN)
        
        # Make the call
        call = client.calls.create(
            to=lead.phone,
            from_=config.TWILIO_CALLER_ID,
            url=f"{config.BASE_URL}/twilio/voice?lead_id={lead_id}",
            status_callback=f"{config.BASE_URL}/twilio/call-status",
            status_callback_event=['initiated', 'ringing', 'answered', 'completed']
        )
        
        # Create call session in database
        CallSessionService.create_session(
            db,
            call_sid=call.sid,
            lead_id=lead_id,
            from_number=config.TWILIO_CALLER_ID,
            to_number=lead.phone
        )
        
        # Update lead status
        LeadService.update_lead_status(db, lead_id, LeadStatus.CONTACTED)
        
        logger.info("outbound_call_initiated", lead_id=lead_id, call_sid=call.sid)
        
        return {
            "status": "success",
            "call_sid": call.sid,
            "lead_id": lead_id
        }
        
    except Exception as e:
        logger.error("outbound_call_failed", lead_id=lead_id, error=str(e))
        return {"status": "error", "message": str(e)}
    finally:
        db.close()


@celery_app.task(name='run_outbound_campaign')
def run_outbound_campaign_task(campaign_id: int, lead_ids: list[int], delay_seconds: int = 30):
    """
    Background task to run an outbound calling campaign.
    Calls each lead with a delay between calls.
    
    Args:
        campaign_id: ID of the campaign
        lead_ids: List of lead IDs to call
        delay_seconds: Delay between calls (default: 30 seconds)
        
    Returns:
        dict: Campaign results
    """
    from app.logging_config import logger
    import time
    
    results = {
        "campaign_id": campaign_id,
        "total_leads": len(lead_ids),
        "successful_calls": 0,
        "failed_calls": 0,
        "call_results": []
    }
    
    logger.info("campaign_started", campaign_id=campaign_id, total_leads=len(lead_ids))
    
    for i, lead_id in enumerate(lead_ids):
        # Make the call
        result = make_outbound_call_task(lead_id)
        results["call_results"].append(result)
        
        if result["status"] == "success":
            results["successful_calls"] += 1
        else:
            results["failed_calls"] += 1
        
        # Delay before next call (except for the last one)
        if i < len(lead_ids) - 1:
            time.sleep(delay_seconds)
    
    logger.info("campaign_completed", **results)
    
    return results
