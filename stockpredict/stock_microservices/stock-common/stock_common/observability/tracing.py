"""
Distributed tracing using OpenTelemetry with Jaeger exporter.

Provides:
- Automatic trace propagation
- Custom span creation
- Context injection/extraction for inter-service calls
"""

import logging
from contextvars import ContextVar
from functools import wraps
from typing import Any, Callable, Dict, Optional

from opentelemetry import trace
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.propagate import inject, extract
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import Status, StatusCode, Span
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

from stock_common.config import TracingConfig

logger = logging.getLogger(__name__)

# Current span context variable
_current_span: ContextVar[Optional[Span]] = ContextVar("current_span", default=None)

# Global tracer
_tracer: Optional[trace.Tracer] = None


def setup_tracing(
    service_name: str,
    config: TracingConfig,
    service_version: str = "0.1.0",
) -> trace.Tracer:
    """
    Set up distributed tracing with OpenTelemetry and Jaeger.

    Args:
        service_name: Name of the service
        config: Tracing configuration
        service_version: Version of the service

    Returns:
        Configured tracer instance
    """
    global _tracer

    if not config.enabled:
        logger.info("Tracing is disabled")
        _tracer = trace.get_tracer(service_name)
        return _tracer

    # Create resource with service information
    resource = Resource.create({
        "service.name": service_name,
        "service.version": service_version,
    })

    # Create tracer provider
    provider = TracerProvider(resource=resource)

    # Configure Jaeger exporter
    jaeger_exporter = JaegerExporter(
        agent_host_name=config.jaeger_host,
        agent_port=config.jaeger_port,
    )

    # Add batch span processor for efficient export
    provider.add_span_processor(
        BatchSpanProcessor(jaeger_exporter)
    )

    # Set as global tracer provider
    trace.set_tracer_provider(provider)

    # Get tracer
    _tracer = trace.get_tracer(service_name, service_version)

    logger.info(
        f"Tracing configured: Jaeger at {config.jaeger_host}:{config.jaeger_port}"
    )

    return _tracer


def instrument_fastapi(app) -> None:
    """
    Instrument a FastAPI application for automatic tracing.

    Args:
        app: FastAPI application instance
    """
    FastAPIInstrumentor.instrument_app(app)
    logger.debug("FastAPI instrumented for tracing")


def instrument_httpx() -> None:
    """Instrument HTTPX client for automatic tracing."""
    HTTPXClientInstrumentor().instrument()
    logger.debug("HTTPX instrumented for tracing")


def get_tracer() -> trace.Tracer:
    """Get the global tracer instance."""
    global _tracer
    if _tracer is None:
        _tracer = trace.get_tracer("stock-common")
    return _tracer


def trace_span(
    name: str,
    attributes: Optional[Dict[str, Any]] = None,
    record_exception: bool = True,
):
    """
    Decorator for creating a traced span around a function.

    Example:
        @trace_span("process-order", attributes={"order.type": "buy"})
        async def process_order(order_id: str):
            # ... processing logic
            pass
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            tracer = get_tracer()

            with tracer.start_as_current_span(name) as span:
                _current_span.set(span)

                # Add attributes
                if attributes:
                    for key, value in attributes.items():
                        span.set_attribute(key, value)

                try:
                    result = await func(*args, **kwargs)
                    span.set_status(Status(StatusCode.OK))
                    return result
                except Exception as e:
                    if record_exception:
                        span.record_exception(e)
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    raise
                finally:
                    _current_span.set(None)

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            tracer = get_tracer()

            with tracer.start_as_current_span(name) as span:
                _current_span.set(span)

                if attributes:
                    for key, value in attributes.items():
                        span.set_attribute(key, value)

                try:
                    result = func(*args, **kwargs)
                    span.set_status(Status(StatusCode.OK))
                    return result
                except Exception as e:
                    if record_exception:
                        span.record_exception(e)
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    raise
                finally:
                    _current_span.set(None)

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


def inject_trace_context(headers: Dict[str, str]) -> Dict[str, str]:
    """
    Inject trace context into HTTP headers for propagation.

    Args:
        headers: Existing headers dictionary

    Returns:
        Headers with trace context added
    """
    inject(headers)
    return headers


def extract_trace_context(headers: Dict[str, str]) -> trace.Context:
    """
    Extract trace context from HTTP headers.

    Args:
        headers: Request headers

    Returns:
        Extracted trace context
    """
    return extract(headers)


def add_span_attribute(key: str, value: Any) -> None:
    """Add an attribute to the current span."""
    span = _current_span.get()
    if span:
        span.set_attribute(key, value)


def add_span_event(name: str, attributes: Optional[Dict[str, Any]] = None) -> None:
    """Add an event to the current span."""
    span = _current_span.get()
    if span:
        span.add_event(name, attributes=attributes or {})


def set_span_status(code: StatusCode, description: Optional[str] = None) -> None:
    """Set the status of the current span."""
    span = _current_span.get()
    if span:
        span.set_status(Status(code, description))


class SpanContext:
    """
    Context manager for creating spans.

    Example:
        async with SpanContext("database-query", {"db.statement": query}):
            result = await db.execute(query)
    """

    def __init__(
        self,
        name: str,
        attributes: Optional[Dict[str, Any]] = None,
        record_exception: bool = True,
    ):
        self.name = name
        self.attributes = attributes or {}
        self.record_exception = record_exception
        self.span: Optional[Span] = None

    async def __aenter__(self) -> Span:
        tracer = get_tracer()
        self.span = tracer.start_span(self.name)
        _current_span.set(self.span)

        for key, value in self.attributes.items():
            self.span.set_attribute(key, value)

        return self.span

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if self.span:
            if exc_val:
                if self.record_exception:
                    self.span.record_exception(exc_val)
                self.span.set_status(Status(StatusCode.ERROR, str(exc_val)))
            else:
                self.span.set_status(Status(StatusCode.OK))

            self.span.end()
            _current_span.set(None)

    def __enter__(self) -> Span:
        tracer = get_tracer()
        self.span = tracer.start_span(self.name)
        _current_span.set(self.span)

        for key, value in self.attributes.items():
            self.span.set_attribute(key, value)

        return self.span

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self.span:
            if exc_val:
                if self.record_exception:
                    self.span.record_exception(exc_val)
                self.span.set_status(Status(StatusCode.ERROR, str(exc_val)))
            else:
                self.span.set_status(Status(StatusCode.OK))

            self.span.end()
            _current_span.set(None)
