"""Chatbot Service - Main Application"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
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

REQUEST_COUNT = Counter("chatbot_requests_total", "Total requests", ["method", "endpoint", "status"])
REQUEST_LATENCY = Histogram("chatbot_request_latency_seconds", "Request latency", ["method", "endpoint"])
CHAT_MESSAGES = Counter("chatbot_messages_total", "Total chat messages", ["intent"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.SERVICE_NAME} v{settings.SERVICE_VERSION}")
    yield
    logger.info(f"Shutting down {settings.SERVICE_NAME}")


app = FastAPI(
    title="Chatbot Service",
    description="Conversational AI for Stock Queries",
    version=settings.SERVICE_VERSION,
    docs_url=f"/{settings.API_PREFIX}/api/v2/chat/docs",
    redoc_url=f"/{settings.API_PREFIX}/api/v2/chat/redoc",
    openapi_url=f"/{settings.API_PREFIX}/api/v2/chat/openapi.json",
    lifespan=lifespan
)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    REQUEST_COUNT.labels(method=request.method, endpoint=request.url.path, status=response.status_code).inc()
    REQUEST_LATENCY.labels(method=request.method, endpoint=request.url.path).observe(time.time() - start_time)
    return response


app.include_router(router, prefix=f"/{settings.API_PREFIX}/api/v2/chat", tags=["Chatbot"])


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": settings.SERVICE_NAME}


@app.get("/health/live")
async def liveness_check():
    return {"status": "alive"}


@app.get("/health/ready")
async def readiness_check():
    return {"status": "ready"}


@app.get("/metrics")
async def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get(f"/{settings.API_PREFIX}/api/v2/chat/info")
async def service_info():
    return {
        "service": settings.SERVICE_NAME,
        "version": settings.SERVICE_VERSION,
        "features": ["text_chat", "websocket", "session_management", "intent_detection"],
        "endpoints": {
            "chat": f"/{settings.API_PREFIX}/api/v2/chat/chat",
            "websocket": f"/{settings.API_PREFIX}/api/v2/chat/ws/{{session_id}}",
            "history": f"/{settings.API_PREFIX}/api/v2/chat/history/{{session_id}}"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
