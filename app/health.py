"""
Health check and monitoring endpoints for production.
"""

from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from app.database import get_db
from app.redis_client import redis_client, REDIS_AVAILABLE
from app.config import config
from app.logging_config import logger

router = APIRouter(tags=["Health & Monitoring"])


@router.get("/health")
async def health_check():
    """
    Basic health check - returns 200 if service is running.
    Use this for basic liveness probes.
    """
    return {
        "status": "healthy",
        "service": "agent-messiah",
        "version": "2.0.0"
    }


@router.get("/health/ready")
async def readiness_check(db: Session = Depends(get_db)):
    """
    Readiness check - verifies all dependencies are available.
    Use this for Kubernetes readiness probes.
    
    Checks:
    - Database connectivity
    - Redis availability (if configured)
    - OpenAI configuration (if configured)
    """
    checks = {
        "database": False,
        "redis": False,
        "openai": False,
        "ready": False
    }
    
    # Check database
    try:
        db.execute(text("SELECT 1"))
        checks["database"] = True
        logger.debug("readiness_check_database", status="ok")
    except Exception as e:
        logger.error("readiness_check_database", status="error", error=str(e))
    
    # Check Redis
    if REDIS_AVAILABLE:
        try:
            redis_client.ping()
            checks["redis"] = True
            logger.debug("readiness_check_redis", status="ok")
        except Exception as e:
            logger.warning("readiness_check_redis", status="error", error=str(e))
    else:
        checks["redis"] = "not_configured"
    
    # Check OpenAI
    if config.has_openai_key():
        checks["openai"] = True
    else:
        checks["openai"] = "not_configured"
    
    # Service is ready if database is available
    # (Redis and OpenAI are optional for basic functionality)
    checks["ready"] = checks["database"]
    
    status_code = 200 if checks["ready"] else 503
    
    return checks, status_code


@router.get("/metrics")
async def metrics():
    """
    Prometheus metrics endpoint.
    Exposes application metrics in Prometheus format.
    
    Metrics include:
    - API request counts and durations
    - Call counts
    - Meeting booking counts
    """
    metrics_data = generate_latest()
    return PlainTextResponse(
        content=metrics_data.decode('utf-8'),
        media_type=CONTENT_TYPE_LATEST
    )


@router.get("/health/info")
async def system_info():
    """
    System information and configuration status.
    """
    return {
        "service": "agent-messiah",
        "version": "2.0.0",
        "configuration": {
            "agent_mode": config.AGENT_MODE,
            "openai_configured": config.has_openai_key(),
            "openai_model": config.OPENAI_MODEL if config.has_openai_key() else None,
            "redis_configured": REDIS_AVAILABLE,
            "database_type": "sqlite" if "sqlite" in config.DATABASE_URL else "postgresql",
            "debug_mode": config.DEBUG
        },
        "features": {
            "llm_conversations": config.has_openai_key(),
            "session_persistence": REDIS_AVAILABLE,
            "database_persistence": True,
            "twilio_integration": bool(config.TWILIO_ACCOUNT_SID),
        }
    }
