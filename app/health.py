"""
Health check and monitoring endpoints for production.
"""

from fastapi import APIRouter

from app.redis_client import redis_client, REDIS_AVAILABLE
from app.config import config
from app.logging_config import logger

router = APIRouter(tags=["Health & Monitoring"])


# GET /health
# Gets: nothing
# Returns: {status, service, version}
# Example:
#   curl http://localhost:8000/health
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


# GET /health/ready
# Gets: nothing
# Returns: dependency readiness checks + an HTTP status code (as a tuple)
# Example:
#   curl http://localhost:8000/health/ready
@router.get("/health/ready")
async def readiness_check():
    """
    Readiness check - verifies all dependencies are available.
    Use this for Kubernetes readiness probes.
    
    Checks:
    - Redis availability (if configured)
    - OpenAI configuration (if configured)
    """
    checks = {
        "database": "not_used",
        "redis": False,
        "openai": False,
        "ready": False
    }
    
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
    
    # Service is ready without external dependencies in local dev.
    # (Redis and OpenAI are optional for basic functionality)
    checks["ready"] = True
    
    status_code = 200 if checks["ready"] else 503
    
    return checks, status_code


# GET /health/info
# Gets: nothing
# Returns: service configuration summary
# Example:
#   curl http://localhost:8000/health/info
@router.get("/health/info")
async def system_info():
    """
    System information and configuration status.
    """
    return {
        "service": "agent-messiah",
        "version": "2.0.0",
        "configuration": {
            "openai_configured": config.has_openai_key(),
            "openai_model": config.OPENAI_MODEL if config.has_openai_key() else None,
            "redis_configured": REDIS_AVAILABLE,
            "debug_mode": config.DEBUG
        },
        "features": {
            "llm_conversations": config.has_openai_key(),
            "session_persistence": REDIS_AVAILABLE,
            "database_persistence": False,
            "twilio_integration": bool(config.TWILIO_ACCOUNT_SID),
        }
    }
