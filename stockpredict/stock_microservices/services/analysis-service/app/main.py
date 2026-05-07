"""Analysis Service - Main Application"""
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

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

REQUEST_COUNT = Counter("analysis_service_requests_total", "Total requests", ["method", "endpoint", "status"])
REQUEST_LATENCY = Histogram("analysis_service_request_latency_seconds", "Request latency", ["method", "endpoint"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.SERVICE_NAME} v{settings.SERVICE_VERSION}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created")
    yield
    await engine.dispose()
    logger.info(f"Shutting down {settings.SERVICE_NAME}")


app = FastAPI(
    title="Analysis Service",
    description="Technical and Fundamental Analysis Microservice",
    version=settings.SERVICE_VERSION,
    docs_url=f"/{settings.API_PREFIX}/api/v2/analysis/docs",
    redoc_url=f"/{settings.API_PREFIX}/api/v2/analysis/redoc",
    openapi_url=f"/{settings.API_PREFIX}/api/v2/analysis/openapi.json",
    lifespan=lifespan
)

app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    REQUEST_COUNT.labels(method=request.method, endpoint=request.url.path, status=response.status_code).inc()
    REQUEST_LATENCY.labels(method=request.method, endpoint=request.url.path).observe(time.time() - start_time)
    return response


app.include_router(router, prefix=f"/{settings.API_PREFIX}/api/v2/analysis", tags=["Analysis"])


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": settings.SERVICE_NAME}


@app.get("/health/live")
async def liveness_check():
    return {"status": "alive"}


@app.get("/health/ready")
async def readiness_check():
    try:
        async with engine.connect() as conn:
            await conn.execute("SELECT 1")
        return {"status": "ready"}
    except Exception as e:
        return JSONResponse(status_code=503, content={"status": "not ready", "error": str(e)})


@app.get("/metrics")
async def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get(f"/{settings.API_PREFIX}/api/v2/analysis/info")
async def service_info():
    return {
        "service": settings.SERVICE_NAME,
        "version": settings.SERVICE_VERSION,
        "endpoints": {
            "technical": f"/{settings.API_PREFIX}/api/v2/analysis/technical/{{symbol}}",
            "fundamental": f"/{settings.API_PREFIX}/api/v2/analysis/fundamental/{{symbol}}",
            "screener": f"/{settings.API_PREFIX}/api/v2/analysis/screener"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
