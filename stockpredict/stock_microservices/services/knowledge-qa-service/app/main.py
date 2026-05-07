"""Knowledge QA Service - Main Application."""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response
import time
import logging

from app.config import get_settings
from app.api.v1.knowledge_qa_router import router as qa_router
from app.api.error_handlers import knowledge_qa_error_handler, global_exception_handler
from app.domain.exceptions import KnowledgeQAError
from app.infrastructure.persistence.neo4j_connection import get_neo4j_driver, close_neo4j_driver
from app.infrastructure.external.ollama_adapter import OllamaLLMAdapter

settings = get_settings()

# Logging
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Prometheus metrics
REQUEST_COUNT = Counter(
    "knowledge_qa_service_requests_total",
    "Total requests",
    ["method", "endpoint", "status"],
)
REQUEST_LATENCY = Histogram(
    "knowledge_qa_service_request_latency_seconds",
    "Request latency",
    ["method", "endpoint"],
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info(f"Starting {settings.SERVICE_NAME} v{settings.SERVICE_VERSION}")

    # Initialize Neo4j driver
    try:
        driver = await get_neo4j_driver(
            settings.NEO4J_URI, settings.NEO4J_USER, settings.NEO4J_PASSWORD
        )
        logger.info(f"Neo4j driver initialized: {settings.NEO4J_URI}")
    except Exception as e:
        logger.warning(f"Neo4j connection failed at startup: {e}")

    yield

    # Cleanup
    await close_neo4j_driver()
    logger.info(f"Shutting down {settings.SERVICE_NAME}")


# Create FastAPI app
app = FastAPI(
    title="Knowledge QA Service",
    description="Graph RAG microservice for knowledge base Q&A using Neo4j + Ollama",
    version=settings.SERVICE_VERSION,
    docs_url=f"/{settings.API_PREFIX}/api/v2/knowledge-qa/docs",
    redoc_url=f"/{settings.API_PREFIX}/api/v2/knowledge-qa/redoc",
    openapi_url=f"/{settings.API_PREFIX}/api/v2/knowledge-qa/openapi.json",
    lifespan=lifespan,
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
        status=response.status_code,
    ).inc()
    REQUEST_LATENCY.labels(
        method=request.method,
        endpoint=endpoint,
    ).observe(duration)

    return response


# Exception handlers
app.add_exception_handler(KnowledgeQAError, knowledge_qa_error_handler)
app.add_exception_handler(Exception, global_exception_handler)

# Include API routes
app.include_router(
    qa_router,
    prefix=f"/{settings.API_PREFIX}/api/v2/knowledge-qa",
    tags=["Knowledge QA"],
)


# Health check endpoints
@app.get("/health")
async def health_check():
    """Comprehensive health check."""
    neo4j_ok = False
    ollama_ok = False

    try:
        driver = await get_neo4j_driver(
            settings.NEO4J_URI, settings.NEO4J_USER, settings.NEO4J_PASSWORD
        )
        async with driver.session() as session:
            result = await session.run("RETURN 1 AS ok")
            record = await result.single()
            neo4j_ok = record is not None
    except Exception:
        pass

    try:
        ollama = OllamaLLMAdapter(
            base_url=settings.OLLAMA_BASE_URL, model=settings.OLLAMA_MODEL
        )
        ollama_ok = await ollama.health_check()
    except Exception:
        pass

    status = "healthy" if neo4j_ok and ollama_ok else "degraded"
    return {
        "status": status,
        "service": settings.SERVICE_NAME,
        "neo4j": "connected" if neo4j_ok else "disconnected",
        "ollama": "connected" if ollama_ok else "disconnected",
    }


@app.get("/health/live")
async def liveness_check():
    """Kubernetes liveness probe."""
    return {"status": "alive"}


@app.get("/health/ready")
async def readiness_check():
    """Kubernetes readiness probe."""
    try:
        driver = await get_neo4j_driver(
            settings.NEO4J_URI, settings.NEO4J_USER, settings.NEO4J_PASSWORD
        )
        async with driver.session() as session:
            await session.run("RETURN 1")
        return {"status": "ready", "neo4j": "connected"}
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={"status": "not ready", "neo4j": str(e)},
        )


# Prometheus metrics endpoint
@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


# Service info endpoint
@app.get(f"/{settings.API_PREFIX}/api/v2/knowledge-qa/info")
async def service_info():
    """Service information."""
    return {
        "service": settings.SERVICE_NAME,
        "version": settings.SERVICE_VERSION,
        "environment": settings.ENVIRONMENT,
        "endpoints": {
            "chat": f"/{settings.API_PREFIX}/api/v2/knowledge-qa/chat",
            "history": f"/{settings.API_PREFIX}/api/v2/knowledge-qa/chat/history/{{session_id}}",
            "clear": f"/{settings.API_PREFIX}/api/v2/knowledge-qa/chat/clear/{{session_id}}",
            "search": f"/{settings.API_PREFIX}/api/v2/knowledge-qa/search",
            "stats": f"/{settings.API_PREFIX}/api/v2/knowledge-qa/stats",
            "health": "/health",
        },
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
