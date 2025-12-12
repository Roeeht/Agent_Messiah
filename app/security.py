"""
Security utilities for production.
- API key authentication
- Twilio webhook signature validation
- Request validation
"""

from fastapi import HTTPException, Security, Header, Request
from fastapi.security import APIKeyHeader
from twilio.request_validator import RequestValidator
from typing import Optional
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


async def validate_twilio_signature(
    request: Request,
    x_twilio_signature: Optional[str] = Header(None)
) -> bool:
    """
    Validate Twilio webhook signature.
    
    Twilio signs all webhook requests with your auth token.
    This prevents unauthorized requests to your webhooks.
    
    Usage:
        @app.post("/twilio/voice")
        async def voice_webhook(
            request: Request,
            valid: bool = Depends(validate_twilio_signature)
        ):
            if not valid:
                raise HTTPException(403, "Invalid signature")
    """
    if not config.TWILIO_AUTH_TOKEN:
        logger.warning("twilio_auth_token_not_configured")
        return True  # Skip validation in development
    
    if not x_twilio_signature:
        logger.warning("twilio_signature_missing")
        return False
    
    # Get the full URL
    url = str(request.url)
    
    # Get form data
    form_data = await request.form()
    params = {key: value for key, value in form_data.items()}
    
    # Validate signature
    validator = RequestValidator(config.TWILIO_AUTH_TOKEN)
    is_valid = validator.validate(
        url,
        params,
        x_twilio_signature
    )
    
    if not is_valid:
        logger.warning(
            "twilio_signature_validation_failed",
            url=url,
            signature=x_twilio_signature[:16]
        )
    
    return is_valid


def sanitize_phone_number(phone: str) -> str:
    """
    Sanitize and format phone number.
    
    Args:
        phone: Phone number in any format
        
    Returns:
        E.164 formatted phone number
    """
    # Remove all non-digit characters
    digits = ''.join(c for c in phone if c.isdigit())
    
    # If doesn't start with +, add Israeli country code if appropriate
    if not phone.startswith('+'):
        # Israeli numbers start with 0, replace with +972
        if digits.startswith('0') and len(digits) == 10:
            digits = '972' + digits[1:]
        # Add + prefix
        return '+' + digits
    
    return phone


def mask_sensitive_data(data: dict, keys_to_mask: list = None) -> dict:
    """
    Mask sensitive data in dictionaries for logging.
    
    Args:
        data: Dictionary potentially containing sensitive data
        keys_to_mask: List of keys to mask (default: phone, api_key, token)
        
    Returns:
        Dictionary with masked values
    """
    if keys_to_mask is None:
        keys_to_mask = ['phone', 'api_key', 'token', 'password', 'secret']
    
    masked = data.copy()
    for key in keys_to_mask:
        if key in masked:
            value = str(masked[key])
            if len(value) > 4:
                masked[key] = value[:4] + '*' * (len(value) - 4)
            else:
                masked[key] = '*' * len(value)
    
    return masked
