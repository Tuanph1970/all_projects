"""Decision Helper Service — main FastAPI application.

F-010 bootstrap: health probes, /metrics, Traefik-routable prefix.
The decision engine (orchestrator + signal/risk pipeline) wires in from F-012.
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
from app.api.dependencies import engine
from app.models.domain import Base

settings = get_settings()

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

REQUEST_COUNT = Counter(
    "decision_helper_requests_total", "Total requests",
    ["method", "endpoint", "status"],
)
REQUEST_LATENCY = Histogram(
    "decision_helper_request_latency_seconds", "Request latency",
    ["method", "endpoint"],
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting %s v%s", settings.SERVICE_NAME, settings.SERVICE_VERSION)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created/verified")
    yield
    await engine.dispose()
    logger.info("Shutting down %s", settings.SERVICE_NAME)


app = FastAPI(
    title="Decision Helper Service",
    description="Per-bar trade recommendation engine (Schwager operationalised)",
    version=settings.SERVICE_VERSION,
    docs_url=f"/{settings.API_PREFIX}/api/v2/helper/docs",
    redoc_url=f"/{settings.API_PREFIX}/api/v2/helper/redoc",
    openapi_url=f"/{settings.API_PREFIX}/api/v2/helper/openapi.json",
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
        method=request.method, endpoint=request.url.path
    ).observe(time.time() - start)
    return response


app.include_router(
    router,
    prefix=f"/{settings.API_PREFIX}/api/v2/helper",
    tags=["Decision Helper"],
)


# ---------------------------------------------------------------------------
# Health probes (unauthenticated — relied on by docker-compose + run-tests.sh)
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    return {"status": "healthy", "service": settings.SERVICE_NAME}


@app.get("/health/live")
async def liveness():
    return {"status": "alive"}


@app.get("/health/ready")
async def readiness():
    try:
        async with engine.connect() as conn:
            from sqlalchemy import text
            await conn.execute(text("SELECT 1"))
        return {"status": "ready"}
    except Exception as exc:
        return JSONResponse(
            status_code=503,
            content={"status": "not ready", "error": str(exc)},
        )


@app.get("/metrics")
async def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
