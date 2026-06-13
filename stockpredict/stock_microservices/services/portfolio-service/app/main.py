"""Portfolio Service - Main Application"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from sqlalchemy import text
from starlette.responses import Response
import time
import logging

from app.config import get_settings
from app.api.routes import router
from app.api.notification_routes import router as notification_router
from app.api.push_routes import router as push_router
from app.api.dependencies import engine
from app.models.domain import Base
from app.services.alert_event_handler import start_alert_consumer, stop_alert_consumer
from app.services.notification_consumer import (
    start_notification_consumer,
    stop_notification_consumer,
)
from app.services.email_consumer import (
    start_email_consumer,
    stop_email_consumer,
)
from app.services.push_consumer import (
    start_push_consumer,
    stop_push_consumer,
)

settings = get_settings()

# Logging configuration
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Prometheus metrics
REQUEST_COUNT = Counter(
    "portfolio_service_requests_total",
    "Total requests",
    ["method", "endpoint", "status"]
)
REQUEST_LATENCY = Histogram(
    "portfolio_service_request_latency_seconds",
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

    # Subscribe to stock.price.updated events for event-driven alert evaluation.
    # Returns None silently if RabbitMQ is unavailable — service still serves CRUD.
    await start_alert_consumer(service_name=settings.SERVICE_NAME)

    # Subscribe to portfolio.alert.triggered (the alert handler emits this
    # after marking an alert) and persist as a Notification row.
    await start_notification_consumer(service_name=settings.SERVICE_NAME)

    # Second subscriber on the same event for the email channel — uses a
    # distinct queue name so RabbitMQ delivers a copy to each consumer.
    await start_email_consumer(service_name=settings.SERVICE_NAME)

    # Third subscriber: browser web-push delivery.
    await start_push_consumer(service_name=settings.SERVICE_NAME)

    yield

    # Cleanup
    await stop_alert_consumer()
    await stop_notification_consumer()
    await stop_email_consumer()
    await stop_push_consumer()
    await engine.dispose()
    logger.info(f"Shutting down {settings.SERVICE_NAME}")


# Create FastAPI app
app = FastAPI(
    title="Portfolio Service",
    description="Microservice for managing stock portfolios, holdings, transactions, and price alerts",
    version=settings.SERVICE_VERSION,
    docs_url=f"/{settings.API_PREFIX}/api/v2/portfolio/docs",
    redoc_url=f"/{settings.API_PREFIX}/api/v2/portfolio/redoc",
    openapi_url=f"/{settings.API_PREFIX}/api/v2/portfolio/openapi.json",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
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


# Notifications router included BEFORE the main portfolio router so its
# static `/notifications` paths aren't shadowed by the main router's
# trailing `/{portfolio_id}` catch-all.
app.include_router(
    notification_router,
    prefix=f"/{settings.API_PREFIX}/api/v2/portfolio",
    tags=["Notifications"]
)

# Same reasoning — static /push paths mount before /{portfolio_id}.
app.include_router(
    push_router,
    prefix=f"/{settings.API_PREFIX}/api/v2/portfolio",
    tags=["Push"]
)


# Service info endpoint — registered BEFORE the main router so the
# /{portfolio_id} catch-all on that router doesn't try to parse "info"
# as an int and return 422. Mirrors the rationale for the notification
# and push routers above.
@app.get(f"/{settings.API_PREFIX}/api/v2/portfolio/info")
async def service_info():
    """Service information"""
    return {
        "service": settings.SERVICE_NAME,
        "version": settings.SERVICE_VERSION,
        "environment": settings.ENVIRONMENT,
        "endpoints": {
            "portfolios": f"/{settings.API_PREFIX}/api/v2/portfolio/portfolios",
            "holdings": f"/{settings.API_PREFIX}/api/v2/portfolio/portfolios/{{id}}/holdings",
            "transactions": f"/{settings.API_PREFIX}/api/v2/portfolio/portfolios/{{id}}/transactions",
            "alerts": f"/{settings.API_PREFIX}/api/v2/portfolio/alerts",
            "watchlist": f"/{settings.API_PREFIX}/api/v2/portfolio/watchlist"
        }
    }


# Include API routes
app.include_router(
    router,
    prefix=f"/{settings.API_PREFIX}/api/v2/portfolio",
    tags=["Portfolio"]
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
            await conn.execute(text("SELECT 1"))
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
