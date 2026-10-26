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

from app.api.broker_routes import router as broker_router
from app.api.routes import router
from app.api.tcb_routes import router as tcb_router
from app.config import get_settings
from app.deps import container
from app.repositories.news_repository import NewsRepository
from app.repositories.tcb_repository import TcbRepository
from app.services.watchlist_push import WatchlistPusher

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

        # Pasted-TCBS-mail tables share the engine and the Base with news_events, so
        # this only adds the three tcb_news* tables (FR-BM-MARKET/FR-BM-CALLS).
        tcb_repo = TcbRepository(engine)
        tcb_repo.ensure_schema()
        container.tcb_repo = tcb_repo
        container.watchlist_pusher = WatchlistPusher(
            settings.PORTFOLIO_SERVICE_URL,
            api_prefix=settings.API_PREFIX,
            timeout=settings.HTTP_TIMEOUT_SECONDS,
        )
        if settings.ENABLE_SCORING:
            _start_call_scorer(tcb_repo)

        # Broker mail intake, phase E1 (FR-BM-INTAKE). The table and the source are
        # always constructed so `POST /news/broker/poll` and the stats endpoint work on
        # demand; only the background loop is gated, and only when the mailbox is
        # actually configured — see _start_broker_mail.
        _start_broker_mail(engine)

        # Start the company poller outside test env (TestClient must not spawn pollers
        # or touch RabbitMQ/upstreams). N12 adds the macro poller behind ENABLE_MACRO.
        if settings.ENABLE_COMPANY and settings.ENVIRONMENT != "test":
            _start_company_poller(repo)
        if settings.ENABLE_MACRO and settings.ENVIRONMENT != "test":
            _start_macro_poller(repo)

        _READY = True
        logger.info("%s startup OK", settings.SERVICE_NAME)
    except Exception as exc:  # noqa: BLE001
        logger.error("startup wiring failed: %s", exc)
        _READY = False
    yield
    if container.scheduler is not None:
        await container.scheduler.stop()
    if container.macro_scheduler is not None:
        await container.macro_scheduler.stop()
    if container.scoring_scheduler is not None:
        await container.scoring_scheduler.stop()
    if container.broker_mail_scheduler is not None:
        await container.broker_mail_scheduler.stop()
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


def _start_call_scorer(tcb_repo: TcbRepository) -> None:
    """Wire the forward-return scorer (FR-BM-SCORE) and, outside tests, its schedule.

    The scorer itself is always constructed so `POST /news/tcb/score` works on demand;
    only the background loop is skipped under ENVIRONMENT=test, matching the pollers.
    A stock-data-service outage defers a tick, it never fails startup."""
    from app.ingest.price_history import PriceHistorySource
    from app.services.call_scorer import CallScorer
    from app.services.scheduler import PollerScheduler

    prices = PriceHistorySource(
        settings.STOCK_DATA_SERVICE_URL,
        api_prefix=settings.API_PREFIX,
        timeout=settings.HTTP_TIMEOUT_SECONDS,
    )
    scorer = CallScorer(tcb_repo, prices, index_symbol=settings.MARKET_INDEX_SYMBOL)
    container.call_scorer = scorer
    if settings.ENVIRONMENT != "test":
        sched = PollerScheduler(scorer, settings.SCORING_INTERVAL_SECONDS, name="call-scorer")
        sched.start()
        container.scoring_scheduler = sched


def _start_broker_mail(engine) -> None:
    """Wire broker-mail intake (E1: FR-BM-INTAKE, FR-BM-DEDUP, FR-BM-BACKFILL).

    Three states, kept distinguishable on purpose:
      * table + source always built, so the operator endpoints answer either way;
      * scheduler started only when ENABLE_EMAIL *and* the mailbox is configured;
      * configured-but-unreachable is reported per tick by the source, never at startup.

    A mailbox outage must not fail startup, so nothing here connects — the factory is
    called per tick (ImapMailbox deliberately does not hold a connection open).
    """
    from app.ingest.broker_mail_source import BrokerMailSource, ImapMailbox
    from app.repositories.broker_mail_repository import BrokerMailRepository
    from app.services.scheduler import PollerScheduler

    repo = BrokerMailRepository(engine)
    repo.ensure_schema()
    container.broker_mail_repo = repo

    def mailbox_factory():
        # The config check lives HERE rather than in the route or beside the scheduler,
        # so "is the mailbox usable?" is answered in exactly one place. With an empty
        # host imaplib would dial localhost and the operator would read "Connection
        # refused" — pointing at the network instead of at the three settings missing.
        if not settings.broker_mail_configured:
            raise RuntimeError(
                "ingestion mailbox not configured: set BROKER_MAIL_HOST, "
                "BROKER_MAIL_USER and BROKER_MAIL_PASSWORD (EC-B1: a dedicated "
                "mailbox, never a personal inbox)")
        return ImapMailbox(
            settings.BROKER_MAIL_HOST,
            settings.BROKER_MAIL_USER,
            settings.BROKER_MAIL_PASSWORD,
            port=settings.BROKER_MAIL_PORT,
            folder=settings.BROKER_MAIL_FOLDER,
            timeout=settings.HTTP_TIMEOUT_SECONDS * 3,   # IMAP login is slower than HTTP
        )

    source = BrokerMailSource(
        repo, mailbox_factory,
        allow_from=settings.broker_mail_allow_from,
        source_key=settings.BROKER_MAIL_SOURCE_KEY,
        lookback_days=settings.BROKER_MAIL_LOOKBACK_DAYS,
    )
    container.broker_mail_source = source

    if not settings.ENABLE_EMAIL:
        logger.info("broker mail intake off (ENABLE_EMAIL=0); endpoints still available")
        return
    if not settings.broker_mail_configured:
        # Loud, because this is the one state that looks enabled and captures nothing —
        # and every day it stays that way is a day of mail that may be unrecoverable.
        logger.warning(
            "ENABLE_EMAIL=1 but the ingestion mailbox is not configured "
            "(BROKER_MAIL_HOST/USER/PASSWORD); no mail will be captured")
        return
    if settings.ENVIRONMENT == "test":
        return
    sched = PollerScheduler(
        source, settings.BROKER_MAIL_POLL_INTERVAL_SECONDS, name="broker-mail")
    sched.start()
    container.broker_mail_scheduler = sched


def _load_macro_sources() -> list:
    """Feed registry from FEED_REGISTRY_PATH (JSON list) or the built-in defaults."""
    import json

    from app.ingest.macro_feeds import DEFAULT_SOURCES

    path = settings.FEED_REGISTRY_PATH
    if path:
        try:
            with open(path, "r", encoding="utf-8") as fh:
                return json.load(fh)
        except Exception as exc:  # noqa: BLE001
            logger.error("failed to load feed registry %s: %s; using defaults", path, exc)
    return DEFAULT_SOURCES


def _start_macro_poller(repo: NewsRepository) -> None:
    """Wire Stream A (macro) feeds + scheduler behind ENABLE_MACRO. The event-reaction
    bridge is attached only when ENABLE_BRIDGE is set (N13)."""
    from app.ingest.event_bridge import EventReactionBridge
    from app.ingest.macro_feeds import MacroFeedSource
    from app.services.macro_poller import MacroPoller
    from app.services.scheduler import PollerScheduler

    macro = MacroFeedSource(_load_macro_sources(), timeout=settings.HTTP_TIMEOUT_SECONDS)
    bridge = None
    if settings.ENABLE_BRIDGE:
        bridge = EventReactionBridge(
            settings.EVENT_REACTION_SERVICE_URL,
            api_prefix=settings.API_PREFIX, timeout=settings.HTTP_TIMEOUT_SECONDS,
        )
    poller = MacroPoller(macro_source=macro, repo=repo, bridge=bridge)
    sched = PollerScheduler(poller, settings.MACRO_POLL_INTERVAL_SECONDS, name="macro")
    sched.start()
    container.macro_poller = poller
    container.macro_scheduler = sched


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

app.include_router(
    tcb_router,
    prefix=f"/{settings.API_PREFIX}/api/v2/news",
    tags=["TCB News"],
)

app.include_router(
    broker_router,
    prefix=f"/{settings.API_PREFIX}/api/v2/news",
    tags=["Broker Mail"],
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
