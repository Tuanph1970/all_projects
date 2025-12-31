"""
Feature Flag Service
Manages feature flags for gradual traffic cutover during migration

Provides:
- Service-level traffic splitting percentages
- User/group targeting for canary releases
- Real-time flag updates without restart
- Audit logging for all changes
"""
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import flags, health, admin
from app.services.flag_store import FlagStore
from app.services.metrics import MetricsCollector

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """Application lifespan manager"""
    # Startup
    logger.info("Starting Feature Flag Service...")

    # Initialize flag store
    app.state.flag_store = FlagStore()
    await app.state.flag_store.initialize()

    # Initialize metrics
    app.state.metrics = MetricsCollector()

    # Load initial flags from config
    await app.state.flag_store.load_defaults()

    logger.info("Feature Flag Service started successfully")

    yield

    # Shutdown
    logger.info("Shutting down Feature Flag Service...")
    await app.state.flag_store.close()
    logger.info("Feature Flag Service stopped")


# Create FastAPI app
app = FastAPI(
    title="Feature Flag Service",
    description="Manages feature flags for gradual microservices migration",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, prefix="/health", tags=["Health"])
app.include_router(flags.router, prefix="/api/flags", tags=["Flags"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])


@app.get("/")
async def root():
    """Root endpoint with service info"""
    return {
        "service": "feature-flags",
        "version": "1.0.0",
        "status": "running"
    }
