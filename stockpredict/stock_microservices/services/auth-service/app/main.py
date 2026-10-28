"""
Auth Service - FastAPI Application Entry Point
"""
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from sqlalchemy import text
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.responses import Response

from app.config import get_settings
from app.api.rate_limit import check_proxy_trust, limiter
from app.api.routes import router as auth_router
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


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """Application lifespan handler"""
    # Startup
    logger.info(f"Starting {settings.SERVICE_NAME} v{settings.SERVICE_VERSION}")
    logger.info(f"Environment: {settings.ENVIRONMENT}")

    # Backlog #24. The per-IP rate limit silently degrades to a GLOBAL one when
    # uvicorn is not told to trust the proxy, because `get_remote_address` then
    # keys every request to Traefik's own address. That was the live state until
    # 2026-10-28 and nothing announced it, so it announces itself now.
    proxy_warning = check_proxy_trust()
    if proxy_warning:
        logger.warning("RATE LIMIT MISCONFIGURED: %s", proxy_warning)
    else:
        logger.info("Rate limiting keys on the real client "
                    "(FORWARDED_ALLOW_IPS is set to a proxy network)")

    # Create database tables if not exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables initialized")

    yield

    # Shutdown
    logger.info(f"Shutting down {settings.SERVICE_NAME}")
    await engine.dispose()


# Create FastAPI app
app = FastAPI(
    title="Auth Service",
    description="Authentication and authorization microservice for Stock Helper",
    version=settings.SERVICE_VERSION,
    docs_url=f"/{settings.API_PREFIX}/api/v2/auth/docs",
    redoc_url=f"/{settings.API_PREFIX}/api/v2/auth/redoc",
    openapi_url=f"/{settings.API_PREFIX}/api/v2/auth/openapi.json",
    lifespan=lifespan,
)

# Rate limiting — per-IP buckets on the brute-force-prone routes.
# SECURITY_AUDIT.md MEDIUM #7. The limiter is registered as middleware so
# it runs before CORS; the 429 handler emits a JSON body matching our
# standard error shape.
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

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
            await conn.execute(text("SELECT 1"))
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
    auth_router,
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
        "docs": f"/{settings.API_PREFIX}/api/v2/auth/docs",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
