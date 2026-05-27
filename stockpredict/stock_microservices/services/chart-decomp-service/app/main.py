"""Chart Decomposition Service — FastAPI application.

Stateless computation wrapper around the chart_decomp library (CD-1).
No database; health/ready simply confirms the library imported cleanly.
"""
from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response

from app.config import get_settings
from app.api.routes import router

settings = get_settings()

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

REQUEST_COUNT = Counter(
    "chart_decomp_requests_total", "Total requests",
    ["method", "endpoint", "status"],
)
REQUEST_LATENCY = Histogram(
    "chart_decomp_request_latency_seconds", "Request latency in seconds",
    ["method", "endpoint"],
)

_LIBRARY_OK: bool = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _LIBRARY_OK
    logger.info("Starting %s v%s", settings.SERVICE_NAME, settings.SERVICE_VERSION)
    try:
        import chart_decomp as cd  # noqa: F401 — verify importable
        import numpy as np
        # Smoke-test: tiny MODWT round-trip to confirm pywt + numpy wired up
        _test = cd.modwt(np.sin(np.linspace(0, 4 * np.pi, 128)))
        assert _test.approximation is not None
        _LIBRARY_OK = True
        logger.info("chart_decomp library verified OK")
    except Exception as exc:
        logger.error("chart_decomp smoke-test failed: %s", exc)
        _LIBRARY_OK = False

    yield

    logger.info("Shutting down %s", settings.SERVICE_NAME)


app = FastAPI(
    title="Chart Decomposition Service",
    description=(
        "Multi-scale chart decomposition & volatility forecasting API. "
        "Implements MODWT, EMD/EEMD, VMD, CWT, HHT, Hurst, Wavelet Coherence, "
        "HAR/VMD-HAR forecasting, and vol-targeting backtest."
    ),
    version=settings.SERVICE_VERSION,
    docs_url=f"/{settings.API_PREFIX}/api/v2/chart-decomp/docs",
    redoc_url=f"/{settings.API_PREFIX}/api/v2/chart-decomp/redoc",
    openapi_url=f"/{settings.API_PREFIX}/api/v2/chart-decomp/openapi.json",
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
    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code,
    ).inc()
    REQUEST_LATENCY.labels(
        method=request.method,
        endpoint=request.url.path,
    ).observe(time.time() - start)
    return response


app.include_router(
    router,
    prefix=f"/{settings.API_PREFIX}/api/v2/chart-decomp",
    tags=["Chart Decomposition"],
)


# ---------------------------------------------------------------------------
# Health probes — unauthenticated, relied on by docker-compose + run-tests.sh
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    return {"status": "healthy", "service": settings.SERVICE_NAME}


@app.get("/health/live")
async def liveness():
    return {"status": "alive"}


@app.get("/health/ready")
async def readiness():
    if _LIBRARY_OK:
        return {"status": "ready"}
    return JSONResponse(
        status_code=503,
        content={"status": "not ready", "error": "chart_decomp library failed smoke-test"},
    )


@app.get("/metrics")
async def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
