"""
Stock Data Service - FastAPI Application Entry Point
"""
import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response

from app.config import get_settings
from app.api.routes import router as stock_router
from app.api.dependencies import engine
from app.models.domain import Base


# Configuration
settings = get_settings()

# Logging
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(settings.SERVICE_NAME)

# Prometheus Metrics
REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)
REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency",
    ["method", "endpoint"],
)


async def _run_sync():
    """Run one sync cycle if data is stale."""
    from app.api.dependencies import async_session_factory
    from app.repositories.stock_repository import StockRepository
    from app.services.stock_service import StockService

    async with async_session_factory() as session:
        repo = StockRepository(session)
        service = StockService(repo)
        if await service.is_company_data_stale():
            logger.info("Company data is stale or empty, starting full sync...")
            results = await service.sync_all_company_data()
            logger.info(f"Sync complete: {results}")
        else:
            logger.info("Company data is fresh, skipping sync")

        # Always refresh price board for VN30 on each sync cycle
        try:
            count = await service.refresh_price_board("VN30")
            logger.info(f"Price board refreshed: {count} records")
        except Exception as e:
            logger.error(f"Price board refresh failed: {e}", exc_info=True)


async def _background_company_sync():
    """Background task: sync on startup if stale, then daily at 1:00 AM."""
    from datetime import datetime as dt, timedelta

    # Initial sync after 5s startup delay
    await asyncio.sleep(5)
    logger.info("Background company sync: initial check...")
    try:
        await _run_sync()
    except Exception as e:
        logger.error(f"Initial company sync failed: {e}", exc_info=True)

    # Daily loop: sleep until 1:00 AM, then sync
    while True:
        now = dt.now()
        next_run = now.replace(hour=1, minute=0, second=0, microsecond=0)
        if next_run <= now:
            next_run += timedelta(days=1)
        wait_seconds = (next_run - now).total_seconds()
        logger.info(f"Next scheduled sync at {next_run.strftime('%Y-%m-%d %H:%M')}, sleeping {wait_seconds/3600:.1f}h")
        await asyncio.sleep(wait_seconds)

        logger.info("Scheduled daily sync starting...")
        try:
            await _run_sync()
        except Exception as e:
            logger.error(f"Scheduled company sync failed: {e}", exc_info=True)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """Application lifespan handler"""
    # Startup
    logger.info(f"Starting {settings.SERVICE_NAME} v{settings.SERVICE_VERSION}")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"VNStock Data Source: {settings.VNSTOCK_DATA_SOURCE}")

    # Create database tables if not exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables initialized")

    # Spawn non-blocking background sync for VN30 company data
    sync_task = asyncio.create_task(_background_company_sync())

    yield

    # Shutdown
    sync_task.cancel()
    logger.info(f"Shutting down {settings.SERVICE_NAME}")
    await engine.dispose()


# Create FastAPI app
app = FastAPI(
    title="Stock Data Service",
    description="Stock data microservice for Stock Helper - provides company info, historical prices, and market data",
    version=settings.SERVICE_VERSION,
    docs_url=f"/{settings.API_PREFIX}/api/v2/stocks/docs",
    redoc_url=f"/{settings.API_PREFIX}/api/v2/stocks/redoc",
    openapi_url=f"/{settings.API_PREFIX}/api/v2/stocks/openapi.json",
    lifespan=lifespan,
)

# CORS Middleware - origins from environment or defaults
import os
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000,http://localhost:3004,http://127.0.0.1:3004").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Metrics Middleware
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    """Middleware to collect metrics"""
    import time

    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time

    # Record metrics (skip health and metrics endpoints)
    if not request.url.path.startswith("/health") and request.url.path != "/metrics":
        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=request.url.path,
            status=response.status_code,
        ).inc()
        REQUEST_LATENCY.labels(
            method=request.method,
            endpoint=request.url.path,
        ).observe(duration)

    return response


# Exception Handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal server error",
            "detail": str(exc) if settings.DEBUG else None,
        },
    )


# Health Check Endpoints
@app.get("/health/live", tags=["Health"])
async def liveness():
    """Kubernetes liveness probe - is the service alive?"""
    return {"status": "alive", "service": settings.SERVICE_NAME}


@app.get("/health/ready", tags=["Health"])
async def readiness():
    """Kubernetes readiness probe - is the service ready to accept traffic?"""
    # Check database connection
    try:
        async with engine.connect() as conn:
            await conn.execute("SELECT 1")
        db_status = "connected"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "not_ready",
                "service": settings.SERVICE_NAME,
                "database": "disconnected",
            },
        )

    return {
        "status": "ready",
        "service": settings.SERVICE_NAME,
        "database": db_status,
    }


@app.get("/health", tags=["Health"])
async def health():
    """Combined health check"""
    return {
        "status": "healthy",
        "service": settings.SERVICE_NAME,
        "version": settings.SERVICE_VERSION,
        "environment": settings.ENVIRONMENT,
    }


# Metrics Endpoint
@app.get("/metrics", tags=["Observability"])
async def metrics():
    """Prometheus metrics endpoint"""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )


# Include API routers
app.include_router(
    stock_router,
    prefix=f"/{settings.API_PREFIX}/api/v2",
)


# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with service information"""
    return {
        "service": settings.SERVICE_NAME,
        "version": settings.SERVICE_VERSION,
        "status": "running",
        "docs": f"/{settings.API_PREFIX}/api/v2/stocks/docs",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
