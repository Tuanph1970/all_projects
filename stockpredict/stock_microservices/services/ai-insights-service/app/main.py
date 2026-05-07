"""AI Insights Service - Main Application"""
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

settings = get_settings()

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

REQUEST_COUNT = Counter("ai_insights_requests_total", "Total requests", ["method", "endpoint", "status"])
REQUEST_LATENCY = Histogram("ai_insights_request_latency_seconds", "Request latency", ["method", "endpoint"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.SERVICE_NAME} v{settings.SERVICE_VERSION}")
    logger.info(f"OpenAI API configured: {bool(settings.OPENAI_API_KEY)}")
    yield
    logger.info(f"Shutting down {settings.SERVICE_NAME}")


app = FastAPI(
    title="AI Insights Service",
    description="LLM-powered Stock Analysis and Insights",
    version=settings.SERVICE_VERSION,
    docs_url=f"/{settings.API_PREFIX}/api/v2/ai/docs",
    redoc_url=f"/{settings.API_PREFIX}/api/v2/ai/redoc",
    openapi_url=f"/{settings.API_PREFIX}/api/v2/ai/openapi.json",
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


app.include_router(router, prefix=f"/{settings.API_PREFIX}/api/v2/ai", tags=["AI Insights"])


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": settings.SERVICE_NAME}


@app.get("/health/live")
async def liveness_check():
    return {"status": "alive"}


@app.get("/health/ready")
async def readiness_check():
    return {"status": "ready", "llm_configured": bool(settings.OPENAI_API_KEY or settings.ANTHROPIC_API_KEY)}


@app.get("/metrics")
async def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get(f"/{settings.API_PREFIX}/api/v2/ai/info")
async def service_info():
    return {
        "service": settings.SERVICE_NAME,
        "version": settings.SERVICE_VERSION,
        "llm_model": settings.LLM_MODEL,
        "endpoints": {
            "insight": f"/{settings.API_PREFIX}/api/v2/ai/insight",
            "compare": f"/{settings.API_PREFIX}/api/v2/ai/compare",
            "ask": f"/{settings.API_PREFIX}/api/v2/ai/ask",
            "market": f"/{settings.API_PREFIX}/api/v2/ai/market-overview"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
