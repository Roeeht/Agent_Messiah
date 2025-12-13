"""
Security utilities for production.
- API key authentication
- Request validation
"""

from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader
from app.config import config
from app.logging_config import get_logger

logger = get_logger(__name__)

# API Key authentication scheme
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(api_key: str = Security(api_key_header)) -> str:
    """
    Verify API key for protected endpoints.
    
    Usage:
        @app.get("/protected")
        async def protected_route(api_key: str = Depends(verify_api_key)):
            return {"message": "Access granted"}
    """
    if not config.API_KEY:
        # If no API key is configured, allow access (development mode)
        return "development"
    
    if api_key != config.API_KEY:
        logger.warning("api_key_authentication_failed", provided_key=api_key[:8] if api_key else None)
        raise HTTPException(
            status_code=403,
            detail="Invalid or missing API key"
        )
    
    return api_key
