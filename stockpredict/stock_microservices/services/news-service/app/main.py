"""News-service — FastAPI application.

Stateful, schedule-driven ingestion service with two streams:
  - Stream B (company): watched-ticker good/bad news -> classify -> notify.
  - Stream A (macro): global-event feeds -> news_events corpus + event-reaction bridge.

N1 scaffold: app boot, health/metrics, versioned router mount. The news_events store
(N2), pollers/scheduler (N6/N12), and read endpoints (N8) are wired in later tasks —
this lifespan reserves the hooks for them.
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

from app.api.routes import router
from app.config import get_settings
from app.deps import container
from app.repositories.news_repository import NewsRepository

settings = get_settings()
logging.basicConfig(level=logging.DEBUG if settings.DEBUG else logging.INFO)
logger = logging.getLogger(__name__)

REQUEST_COUNT = Counter(
    "news_requests_total", "Total requests", ["method", "endpoint", "status"]
)
REQUEST_LATENCY = Histogram(
    "news_request_latency_seconds", "Request latency", ["method", "endpoint"]
)

# Readiness flips true once startup wiring succeeds. N1 has no store/scheduler to
# initialise yet, so the service is ready as soon as it boots; N2/N6 add real checks.
_READY = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _READY
    logger.info("Starting %s v%s", settings.SERVICE_NAME, settings.SERVICE_VERSION)
    try:
        engine = create_engine(settings.DATABASE_URL)
        repo = NewsRepository(engine)
        repo.ensure_schema()
        container.repo = repo

        # Start the company poller outside test env (TestClient must not spawn pollers
        # or touch RabbitMQ/upstreams). N12 adds the macro poller behind ENABLE_MACRO.
        if settings.ENABLE_COMPANY and settings.ENVIRONMENT != "test":
            _start_company_poller(repo)

        _READY = True
        logger.info("%s startup OK", settings.SERVICE_NAME)
    except Exception as exc:  # noqa: BLE001
        logger.error("startup wiring failed: %s", exc)
        _READY = False
    yield
    if container.scheduler is not None:
        await container.scheduler.stop()
    if container.bus is not None:
        try:
            await container.bus.disconnect()
        except Exception:  # noqa: BLE001
            pass
    logger.info("Shutting down %s", settings.SERVICE_NAME)


def _start_company_poller(repo: NewsRepository) -> None:
    """Wire Stream B (company) adapters + scheduler. Bus publish auto-connects lazily,
    so a RabbitMQ outage does not block startup — a failed emit is logged per tick."""
    from stock_common.config import RabbitMQConfig
    from stock_common.events.bus import EventBus

    from app.ingest.classifier import NewsClassifier
    from app.ingest.company_source import CompanyNewsSource
    from app.ingest.watch_source import WatchSource
    from app.services.company_poller import CompanyPoller
    from app.services.notifier import Notifier
    from app.services.scheduler import PollerScheduler

    t = settings.HTTP_TIMEOUT_SECONDS
    watch = WatchSource(
        settings.PORTFOLIO_SERVICE_URL, settings.DECISION_HELPER_SERVICE_URL,
        api_prefix=settings.API_PREFIX, timeout=t,
    )
    company = CompanyNewsSource(settings.STOCK_DATA_SERVICE_URL, api_prefix=settings.API_PREFIX, timeout=t)
    classifier = NewsClassifier(settings.AI_INSIGHTS_SERVICE_URL, api_prefix=settings.API_PREFIX, timeout=t)
    bus = EventBus(RabbitMQConfig(), service_name=settings.SERVICE_NAME)
    notifier = Notifier(bus, source_service=settings.SERVICE_NAME)
    poller = CompanyPoller(
        watch_source=watch, company_source=company, classifier=classifier,
        repo=repo, notifier=notifier, notify_sentiments=settings.notify_sentiments,
    )
    sched = PollerScheduler(poller, settings.COMPANY_POLL_INTERVAL_SECONDS, name="company")
    sched.start()
    container.bus = bus
    container.company_poller = poller
    container.scheduler = sched


app = FastAPI(
    title="News Service",
    description="Ingests company & macro news/events; notifies users of good/bad company news.",
    version=settings.SERVICE_VERSION,
    docs_url=f"/{settings.API_PREFIX}/api/v2/news/docs",
    openapi_url=f"/{settings.API_PREFIX}/api/v2/news/openapi.json",
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
    prefix=f"/{settings.API_PREFIX}/api/v2/news",
    tags=["News"],
)


@app.get("/health")
async def health():
    return {"status": "healthy", "service": settings.SERVICE_NAME}


@app.get("/health/live")
async def liveness():
    return {"status": "alive"}


@app.get("/health/ready")
async def readiness():
    if _READY:
        return {"status": "ready"}
    return JSONResponse(status_code=503, content={"status": "not ready"})


@app.get("/metrics")
async def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
