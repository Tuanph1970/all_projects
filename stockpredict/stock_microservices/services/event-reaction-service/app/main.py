"""Event-Reaction Service — FastAPI application.

Stateful wrapper around the event_reaction library: owns a MySQL event store and
reaches stock-data-service over HTTP for prices. No stats computation happens here.
"""
from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from sqlalchemy import create_engine
from starlette.responses import Response

from event_reaction.ingest import HttpPriceSource

from app.api.routes import router
from app.config import get_settings
from app.deps import container
from app.repositories.event_repository import MySqlEventRepository
from app.services.event_reaction_service import EventReactionService

settings = get_settings()
logging.basicConfig(level=logging.DEBUG if settings.DEBUG else logging.INFO)
logger = logging.getLogger(__name__)

REQUEST_COUNT = Counter(
    "event_reaction_requests_total", "Total requests", ["method", "endpoint", "status"]
)
REQUEST_LATENCY = Histogram(
    "event_reaction_request_latency_seconds", "Request latency", ["method", "endpoint"]
)

_STORE_OK = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _STORE_OK
    logger.info("Starting %s v%s", settings.SERVICE_NAME, settings.SERVICE_VERSION)
    try:
        engine = create_engine(settings.DATABASE_URL)
        repo = MySqlEventRepository(engine)
        repo.ensure_schema()
        price_source = HttpPriceSource(
            settings.STOCK_DATA_SERVICE_URL, api_prefix=settings.API_PREFIX
        )
        container.service = EventReactionService(price_source, repo)
        _STORE_OK = True
        logger.info("event store + price source wired OK")
    except Exception as exc:  # noqa: BLE001
        logger.error("startup wiring failed: %s", exc)
        _STORE_OK = False
    yield
    logger.info("Shutting down %s", settings.SERVICE_NAME)


app = FastAPI(
    title="Event-Reaction Service",
    description="Measures how asset prices react to the surprise of discrete events.",
    version=settings.SERVICE_VERSION,
    docs_url=f"/{settings.API_PREFIX}/api/v2/event-reaction/docs",
    openapi_url=f"/{settings.API_PREFIX}/api/v2/event-reaction/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    REQUEST_COUNT.labels(request.method, request.url.path, response.status_code).inc()
    REQUEST_LATENCY.labels(request.method, request.url.path).observe(time.time() - start)
    return response


app.include_router(
    router,
    prefix=f"/{settings.API_PREFIX}/api/v2/event-reaction",
    tags=["Event Reaction"],
)


@app.get("/health")
async def health():
    return {"status": "healthy", "service": settings.SERVICE_NAME}


@app.get("/health/live")
async def liveness():
    return {"status": "alive"}


@app.get("/health/ready")
async def readiness():
    if _STORE_OK:
        return {"status": "ready"}
    return JSONResponse(status_code=503, content={"status": "not ready"})


@app.get("/metrics")
async def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
