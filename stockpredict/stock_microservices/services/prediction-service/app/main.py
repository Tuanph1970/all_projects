"""Prediction Service - Main Application"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response
import time
import logging

from app.config import get_settings
from app.api.routes import router
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
    "prediction_service_requests_total",
    "Total requests",
    ["method", "endpoint", "status"]
)
REQUEST_LATENCY = Histogram(
    "prediction_service_request_latency_seconds",
    "Request latency",
    ["method", "endpoint"]
)
PREDICTION_COUNT = Counter(
    "prediction_service_predictions_total",
    "Total predictions generated",
    ["symbol", "model_type"]
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    logger.info(f"Starting {settings.SERVICE_NAME} v{settings.SERVICE_VERSION}")

    # Create database tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created")

    # Create model directory
    import os
    os.makedirs(settings.MODEL_PATH, exist_ok=True)
    logger.info(f"Model directory ready: {settings.MODEL_PATH}")

    yield

    # Cleanup
    await engine.dispose()
    logger.info(f"Shutting down {settings.SERVICE_NAME}")


# Create FastAPI app
app = FastAPI(
    title="Prediction Service",
    description="Microservice for ML-based stock price predictions",
    version=settings.SERVICE_VERSION,
    docs_url=f"/{settings.API_PREFIX}/api/v2/predict/docs",
    redoc_url=f"/{settings.API_PREFIX}/api/v2/predict/redoc",
    openapi_url=f"/{settings.API_PREFIX}/api/v2/predict/openapi.json",
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


# Include API routes for /predict path
app.include_router(
    router,
    prefix=f"/{settings.API_PREFIX}/api/v2/predict",
    tags=["Predictions"]
)

# Also include routes for /models path (for model management endpoints)
app.include_router(
    router,
    prefix=f"/{settings.API_PREFIX}/api/v2/models",
    tags=["Models"]
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
@app.get(f"/{settings.API_PREFIX}/api/v2/predict/info")
async def service_info():
    """Service information"""
    return {
        "service": settings.SERVICE_NAME,
        "version": settings.SERVICE_VERSION,
        "environment": settings.ENVIRONMENT,
        "ml_config": {
            "model_path": settings.MODEL_PATH,
            "default_prediction_days": settings.DEFAULT_PREDICTION_DAYS,
            "max_prediction_days": settings.MAX_PREDICTION_DAYS,
            "lookback_period": settings.LOOKBACK_PERIOD
        },
        "endpoints": {
            "predict": f"/{settings.API_PREFIX}/api/v2/predict/predict",
            "models": f"/{settings.API_PREFIX}/api/v2/predict/models",
            "train": f"/{settings.API_PREFIX}/api/v2/predict/models/train",
            "backtest": f"/{settings.API_PREFIX}/api/v2/predict/backtest",
            "compare": f"/{settings.API_PREFIX}/api/v2/predict/compare"
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
