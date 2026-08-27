# Intel Service - seller price & market intelligence
#
# Formerly ai-service. The Ollama client and the three LLM features it carried
# were removed on 2026-08-27 because the deploy target cannot run a model; see
# docs/ai-features/05-price-intelligence.md section 2.
#
# What is left is deliberately small: the flag/quota machinery, the Pillow-based
# image checks, and a health endpoint whose shape the mobile client already
# depends on. Phase 1 mounts the price-position router here.
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from sqlalchemy import text
from shared.database import engine, Base
from shared.config import settings
from shared.cache import cache

from app.routers import comparables, images, position

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Intel Service...")

    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created/verified")

    if cache.client:
        logger.info("Redis cache connection established")
    else:
        logger.warning("Redis cache not available - running without cache")

    logger.info("Feature flags: price_intel=%s", settings.INTEL_PRICE_ENABLED)

    yield

    logger.info("Shutting down Intel Service...")


app = FastAPI(
    title="Intel Service",
    description="Seller price and market intelligence for Mercai",
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

app.include_router(position.router, prefix="/api/v1/intel", tags=["intel-position"])
app.include_router(images.router, prefix="/api/v1/intel", tags=["intel-images"])
app.include_router(comparables.router, prefix="/api/v1/intel", tags=["intel-comparables"])


# Two paths, one handler, on purpose:
#   /health              -> container healthcheck, reached inside the network
#   /api/v1/intel/health -> the client, which only reaches this service through
#                           Traefik's PathPrefix(`/api/v1/intel`) rule
@app.get("/health")
@app.get("/api/v1/intel/health")
def health_check():
    """
    Health for orchestration AND for the client.

    The client uses `features` to decide whether to render intel affordances at
    all, so a disabled feature hides its controls instead of showing something
    that fails when tapped. The contract is unchanged from the ai-service
    version except that nothing here can be "degraded by an unreachable model"
    any more -- there is no model. A feature is on or off, and that is a
    deployment decision rather than a runtime accident.
    """
    health_status = {
        "status": "healthy",
        "service": "intel-service",
        "version": "2.0.0",
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

    health_status["features"] = {
        "price_intel": settings.INTEL_PRICE_ENABLED,
    }

    return health_status


@app.get("/")
def root():
    return {
        "service": "Intel Service",
        "status": "running",
        "endpoints": {
            "price_position": "/api/v1/intel/products/{id}/price-position",
            "image_report": "/api/v1/intel/products/{id}/image-report",
            "comparables": "/api/v1/intel/comparables",
            "health": "/health",
        },
    }
