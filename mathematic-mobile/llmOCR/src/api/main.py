"""
FastAPI main application for Mathematics LLM OCR Service.
"""
import os
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import make_asgi_app
from loguru import logger
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.loguru import LoguruIntegration

from ..config.settings import get_settings, validate_settings, apply_environment_overrides
from ..utils.logging import setup_logging


def _init_sentry(environment: str) -> None:
    """Initialise Sentry if SENTRY_DSN is configured. No-op otherwise."""
    dsn = os.getenv("SENTRY_DSN", "")
    if not dsn:
        logger.info("SENTRY_DSN not set — error tracking disabled")
        return

    sentry_sdk.init(
        dsn=dsn,
        environment=environment,
        traces_sample_rate=0.1 if environment == "production" else 1.0,
        integrations=[
            FastApiIntegration(),
            # Forward loguru ERROR+ messages to Sentry as breadcrumbs/events
            LoguruIntegration(level="WARNING", event_level="ERROR"),
        ],
        send_default_pii=False,   # Never send user PII to Sentry
        attach_stacktrace=True,
    )
    logger.info("Sentry error tracking initialised")
from .middleware import (
    APIKeyMiddleware,
    LoggingMiddleware,
    MetricsMiddleware,
    RateLimitMiddleware,
    RequestSizeLimitMiddleware,
)
from .routers import ocr, health, models, solution, tasks
from .exceptions import setup_exception_handlers
from ..services.model_manager import ModelManager
from ..infrastructure.tasks.in_memory_store import InMemoryTaskRepository


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager."""
    settings = get_settings()

    # Setup logging first so all subsequent messages are structured
    setup_logging(settings.logging)
    logger.info("Starting Mathematics LLM OCR Service")

    # Initialise Sentry before any other startup (captures startup errors too)
    _init_sentry(settings.logging.environment)

    # Validate settings and emit environment-specific warnings
    try:
        validate_settings()
    except ValueError as exc:
        logger.error(f"Configuration validation failed: {exc}")
        raise

    apply_environment_overrides(settings.logging.environment)

    # Initialize model manager and load default models
    model_manager = ModelManager(settings)
    await model_manager.initialize_default_models()

    # Store model manager in app state
    app.state.model_manager = model_manager

    # Initialise task repository
    app.state.task_repository = InMemoryTaskRepository()
    logger.info("Task repository initialised (InMemoryTaskRepository)")

    logger.info("Application startup complete")
    
    yield
    
    # Cleanup on shutdown
    logger.info("Shutting down application")
    
    # Unload all models via the registry owned by ModelManager
    app.state.model_manager.get_registry().unload_all_models()
    
    logger.info("Application shutdown complete")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()
    
    # Create FastAPI app
    app = FastAPI(
        title=settings.app_name,
        description=settings.app_description,
        version=settings.version,
        docs_url="/docs" if settings.enable_docs else None,
        redoc_url="/redoc" if settings.enable_docs else None,
        openapi_url="/openapi.json" if settings.enable_docs else None,
        lifespan=lifespan
    )
    
    # Setup exception handlers
    setup_exception_handlers(app)
    
    # Add middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.api.cors_origins,
        allow_credentials=settings.api.cors_allow_credentials,
        allow_methods=settings.api.cors_allow_methods,
        allow_headers=settings.api.cors_allow_headers,
    )
    
    # Add trusted host middleware for production
    if settings.logging.environment == "production":
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])
    
    # Request size guard (runs before body is consumed)
    app.add_middleware(
        RequestSizeLimitMiddleware,
        max_size_bytes=settings.api.max_file_size,
    )

    # API key authentication (only active when keys are configured)
    if settings.security.valid_api_keys:
        app.add_middleware(
            APIKeyMiddleware,
            valid_api_keys=settings.security.valid_api_keys,
        )
        logger.info(
            f"APIKeyMiddleware enabled ({len(settings.security.valid_api_keys)} key(s) configured)"
        )

    app.add_middleware(LoggingMiddleware)
    app.add_middleware(MetricsMiddleware)
    app.add_middleware(
        RateLimitMiddleware,
        requests_per_minute=settings.api.rate_limit_requests,
        window_seconds=settings.api.rate_limit_window,
    )
    
    # Include routers
    app.include_router(health.router, prefix="/health", tags=["health"])
    app.include_router(models.router, prefix="/models", tags=["models"])
    app.include_router(ocr.router, prefix="/ocr", tags=["ocr"])
    app.include_router(solution.router, prefix="/solution", tags=["solution"])
    app.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
    
    # Add metrics endpoint if enabled
    if settings.monitoring.enable_metrics:
        metrics_app = make_asgi_app()
        app.mount("/metrics", metrics_app)

    # Add debug endpoints if enabled
    if settings.enable_debug_endpoints:
        from .routers import debug
        app.include_router(debug.router, prefix="/debug", tags=["debug"])

    # Wire OpenTelemetry tracing if enabled
    _setup_tracing(app, settings)

    return app


def _setup_tracing(app: FastAPI, settings) -> None:
    """
    Instrument the FastAPI app with OpenTelemetry tracing.

    Activated only when ``ENABLE_TRACING=true``.  Exports spans to the
    OTLP HTTP endpoint defined by ``JAEGER_ENDPOINT`` (e.g.
    ``http://jaeger:4318/v1/traces``).  Falls back to a no-op (console)
    tracer when the OTLP exporter package is unavailable so the service
    still starts cleanly without the optional dependency.
    """
    if not settings.monitoring.enable_tracing:
        return

    try:
        from opentelemetry import trace
        from opentelemetry.sdk.resources import Resource, SERVICE_NAME
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

        resource = Resource.create({SERVICE_NAME: settings.logging.service_name})
        provider = TracerProvider(resource=resource)

        if settings.monitoring.jaeger_endpoint:
            try:
                from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
                    OTLPSpanExporter,
                )
                exporter = OTLPSpanExporter(endpoint=settings.monitoring.jaeger_endpoint)
                logger.info(
                    f"OpenTelemetry tracing → OTLP endpoint: {settings.monitoring.jaeger_endpoint}"
                )
            except ImportError:
                logger.warning(
                    "opentelemetry-exporter-otlp-proto-http not installed — "
                    "falling back to ConsoleSpanExporter.  "
                    "Run: pip install opentelemetry-exporter-otlp-proto-http"
                )
                exporter = ConsoleSpanExporter()
        else:
            logger.info(
                "JAEGER_ENDPOINT not set — using ConsoleSpanExporter for tracing"
            )
            exporter = ConsoleSpanExporter()

        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)
        FastAPIInstrumentor.instrument_app(app, tracer_provider=provider)
        logger.info("OpenTelemetry FastAPI instrumentation enabled")

    except ImportError as exc:
        logger.warning(
            f"OpenTelemetry packages not available ({exc}) — "
            "tracing disabled.  Install opentelemetry-sdk and "
            "opentelemetry-instrumentation-fastapi to enable."
        )


# Create the app instance
app = create_app()


@app.get("/", include_in_schema=False)
async def root():
    """Root endpoint providing service information."""
    settings = get_settings()
    return {
        "service": settings.app_name,
        "version": settings.version,
        "description": settings.app_description,
        "status": "running",
        "timestamp": time.time(),
        "docs_url": "/docs" if settings.enable_docs else None,
        "health_check": "/health",
        "metrics": "/metrics" if settings.monitoring.enable_metrics else None
    }


@app.get("/info", include_in_schema=False)
async def info(request: Request):
    """Service information endpoint."""
    settings = get_settings()
    model_registry = request.app.state.model_manager.get_registry()
    
    return {
        "service_info": {
            "name": settings.app_name,
            "version": settings.version,
            "environment": settings.logging.environment,
        },
        "model_info": {
            "registry_status": model_registry.get_registry_status(),
            "total_models": len(model_registry.list_models()),
        },
        "api_info": {
            "cors_origins": settings.api.cors_origins,
            "rate_limit": {
                "requests_per_minute": settings.api.rate_limit_requests,
                "window_seconds": settings.api.rate_limit_window
            }
        }
    }


if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    
    uvicorn.run(
        "src.api.main:app",
        host=settings.api.host,
        port=settings.api.port,
        reload=settings.api.reload,
        workers=settings.api.workers if not settings.api.reload else 1,
        log_config=None  # We handle logging ourselves
    )