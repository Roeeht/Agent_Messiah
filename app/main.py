"""Main FastAPI application.

This module intentionally stays small: it wires routers + middleware together.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import config
from app.logging_config import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - startup and shutdown."""

    logger.info("application_starting", version="2.0.0")
    logger.info("openai_configured", configured=config.has_openai_key())

    yield

    logger.info("application_shutting_down")


app = FastAPI(
    title="Agent Messiah API",
    description="Production-Ready AI Sales Agent for Alta",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.health import router as health_router
from app.routers.agent import router as agent_router
from app.routers.core import router as core_router
from app.routers.outbound import router as outbound_router
from app.routers.twilio import router as twilio_router

app.include_router(health_router)
app.include_router(core_router)
app.include_router(agent_router)
app.include_router(outbound_router)
app.include_router(twilio_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
