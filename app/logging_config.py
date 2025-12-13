"""
Structured logging configuration for production.
Uses structlog for structured JSON logging.
"""

import logging
import sys
from typing import Any
import structlog
from app.config import config


def configure_logging():
    """
    Configure structured logging for the application.
    
    In production: JSON formatted logs
    In development: Pretty printed colored logs
    """
    
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, config.LOG_LEVEL),
    )

    # Reduce noise from HTTP client libraries (they log every request at INFO).
    for noisy_logger in [
        "httpx",
        "httpcore",
        "openai",
        "twilio",
        "urllib3",
    ]:
        logging.getLogger(noisy_logger).setLevel(logging.WARNING)
    
    # Common processors for all environments
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]
    
    if config.DEBUG:
        # Development: Pretty colored output
        processors.append(structlog.dev.ConsoleRenderer())
    else:
        # Production: JSON output for log aggregation
        processors.append(structlog.processors.JSONRenderer())
    
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


# Get logger instance
def get_logger(name: str = None) -> Any:
    """
    Get a structured logger instance.
    
    Usage:
        logger = get_logger(__name__)
        logger.info("user_login", user_id=123, ip="1.2.3.4")
        logger.error("payment_failed", amount=100, error="card_declined")
    """
    return structlog.get_logger(name)


# Configure on module import
configure_logging()

# Create default logger
logger = get_logger("agent_messiah")
