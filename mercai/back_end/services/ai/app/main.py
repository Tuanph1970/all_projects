# AI Service - LLM-backed seller assistance
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from sqlalchemy import text
from shared.database import engine, Base
from shared.config import settings
from shared.cache import cache

from app.routers import listing

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting AI Service...")

    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created/verified")

    if cache.client:
        logger.info("Redis cache connection established")
    else:
        logger.warning("Redis cache not available - running without cache")

    logger.info(
        "Model config: %s at %s", settings.OLLAMA_MODEL, settings.OLLAMA_BASE_URL
    )
    logger.info(
        "Feature flags: listing_optimizer=%s chat_copilot=%s review_intelligence=%s",
        settings.AI_LISTING_OPTIMIZER_ENABLED,
        settings.AI_CHAT_COPILOT_ENABLED,
        settings.AI_REVIEW_INTELLIGENCE_ENABLED,
    )

    yield

    logger.info("Shutting down AI Service...")


app = FastAPI(
    title="AI Service",
    description="Seller-facing AI assistance for Mercai",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(listing.router, prefix="/api/v1/ai", tags=["ai-listing"])


# Two paths, one handler, on purpose:
#   /health            -> container healthcheck, reached inside the network
#   /api/v1/ai/health  -> the client, which only reaches this service through
#                         Traefik's PathPrefix(`/api/v1/ai`) rule
@app.get("/health")
@app.get("/api/v1/ai/health")
def health_check():
    """
    Health for orchestration AND for the client.

    The client uses `features` to decide whether to render AI affordances at
    all, so a model outage hides the buttons instead of showing a control that
    fails when tapped.
    """
    from app.services.ollama_client import ollama_client

    health_status = {
        "status": "healthy",
        "service": "ai-service",
        "version": "1.0.0",
        "model": settings.OLLAMA_MODEL,
    }

    try:
        from shared.database import SessionLocal
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        health_status["database"] = "connected"
    except Exception as e:
        health_status["database"] = f"error: {str(e)}"
        health_status["status"] = "degraded"

    try:
        if cache.client and cache.client.ping():
            health_status["cache"] = "connected"
        else:
            health_status["cache"] = "not available"
    except Exception as e:
        health_status["cache"] = f"error: {str(e)}"

    model_reachable = ollama_client.is_available()
    health_status["ollama"] = "reachable" if model_reachable else "unreachable"
    if not model_reachable:
        health_status["status"] = "degraded"

    health_status["features"] = {
        "listing_optimizer": settings.AI_LISTING_OPTIMIZER_ENABLED and model_reachable,
        "chat_copilot": settings.AI_CHAT_COPILOT_ENABLED and model_reachable,
        "review_intelligence": settings.AI_REVIEW_INTELLIGENCE_ENABLED and model_reachable,
    }

    return health_status


@app.get("/")
def root():
    return {
        "service": "AI Service",
        "status": "running",
        "endpoints": {"listing": "/api/v1/ai/listing", "health": "/health"},
    }
