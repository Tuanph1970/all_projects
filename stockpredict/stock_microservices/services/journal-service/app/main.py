"""Journal Service - Main Application"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response
import time
import logging
import os

from app.config import get_settings
from app.api.account_routes import router as account_router
from app.api.trade_routes import router as trade_router
from app.api.diary_routes import router as diary_router
from app.api.dashboard_routes import router as dashboard_router
from app.api.planning_routes import router as planning_router
from app.api.dependencies import engine
from app.models.domain import Base

settings = get_settings()

# Logging configuration
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Prometheus metrics
REQUEST_COUNT = Counter(
    "journal_service_requests_total",
    "Total requests",
    ["method", "endpoint", "status"]
)
REQUEST_LATENCY = Histogram(
    "journal_service_request_latency_seconds",
    "Request latency",
    ["method", "endpoint"]
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    logger.info(f"Starting {settings.SERVICE_NAME} v{settings.SERVICE_VERSION}")

    # Create database tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created")

    # Create upload directory for diary charts
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    logger.info(f"Upload directory ready: {settings.UPLOAD_DIR}")

    yield

    # Cleanup
    await engine.dispose()
    logger.info(f"Shutting down {settings.SERVICE_NAME}")


# Create FastAPI app
app = FastAPI(
    title="Journal Service",
    description="Microservice for Trader Journal — implementing Schwager's Planned Trading Approach",
    version=settings.SERVICE_VERSION,
    docs_url=f"/{settings.API_PREFIX}/api/v2/journal/docs",
    redoc_url=f"/{settings.API_PREFIX}/api/v2/journal/redoc",
    openapi_url=f"/{settings.API_PREFIX}/api/v2/journal/openapi.json",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Metrics middleware
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time

    endpoint = request.url.path
    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=endpoint,
        status=response.status_code
    ).inc()
    REQUEST_LATENCY.labels(
        method=request.method,
        endpoint=endpoint
    ).observe(duration)

    return response


# Include API routes
app.include_router(
    account_router,
    prefix=f"/{settings.API_PREFIX}/api/v2/journal",
    tags=["Journal Accounts"]
)
app.include_router(
    trade_router,
    prefix=f"/{settings.API_PREFIX}/api/v2/journal",
    tags=["Journal Trades"]
)
app.include_router(
    diary_router,
    prefix=f"/{settings.API_PREFIX}/api/v2/journal",
    tags=["Journal Diary"]
)
app.include_router(
    dashboard_router,
    prefix=f"/{settings.API_PREFIX}/api/v2/journal",
    tags=["Journal Dashboard"]
)
app.include_router(
    planning_router,
    prefix=f"/{settings.API_PREFIX}/api/v2/journal",
    tags=["Journal Planning"]
)


# Health check endpoints
@app.get("/health")
async def health_check():
    """Basic health check"""
    return {"status": "healthy", "service": settings.SERVICE_NAME}


@app.get("/health/live")
async def liveness_check():
    """Kubernetes liveness probe"""
    return {"status": "alive"}


@app.get("/health/ready")
async def readiness_check():
    """Kubernetes readiness probe"""
    try:
        async with engine.connect() as conn:
            await conn.execute("SELECT 1")
        return {"status": "ready", "database": "connected"}
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={"status": "not ready", "database": str(e)}
        )


# Prometheus metrics endpoint
@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )


# Service info endpoint
@app.get(f"/{settings.API_PREFIX}/api/v2/journal/info")
async def service_info():
    """Service information"""
    return {
        "service": settings.SERVICE_NAME,
        "version": settings.SERVICE_VERSION,
        "environment": settings.ENVIRONMENT,
        "endpoints": {
            "accounts": f"/{settings.API_PREFIX}/api/v2/journal/accounts",
            "rules": f"/{settings.API_PREFIX}/api/v2/journal/accounts/{{id}}/rules",
            "trades": f"/{settings.API_PREFIX}/api/v2/journal/accounts/{{id}}/trades",
            "diary": f"/{settings.API_PREFIX}/api/v2/journal/trades/{{id}}/diary",
            "charts": f"/{settings.API_PREFIX}/api/v2/journal/diary/{{id}}/charts",
            "dashboard": f"/{settings.API_PREFIX}/api/v2/journal/accounts/{{id}}/dashboard",
            "equity": f"/{settings.API_PREFIX}/api/v2/journal/accounts/{{id}}/equity",
            "daily_plans": f"/{settings.API_PREFIX}/api/v2/journal/accounts/{{id}}/plans",
            "weekly_reviews": f"/{settings.API_PREFIX}/api/v2/journal/accounts/{{id}}/reviews"
        }
    }


# Error handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "type": type(exc).__name__}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
