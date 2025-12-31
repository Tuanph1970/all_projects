"""
Structured logging for microservices.

Provides:
- JSON-formatted logs
- Context-aware logging
- Correlation ID propagation
"""

import logging
import sys
from contextvars import ContextVar
from typing import Any, Dict, Optional

import structlog
from structlog.types import Processor

# Context variables for log context
_log_context: ContextVar[Dict[str, Any]] = ContextVar("log_context", default={})


class LogContext:
    """
    Context manager for adding context to logs.

    Example:
        async with LogContext(user_id="123", request_id="abc"):
            logger.info("Processing request")  # Includes user_id and request_id
    """

    def __init__(self, **kwargs):
        self.context = kwargs
        self._token = None

    def __enter__(self) -> "LogContext":
        current = _log_context.get().copy()
        current.update(self.context)
        self._token = _log_context.set(current)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._token:
            _log_context.reset(self._token)

    async def __aenter__(self) -> "LogContext":
        return self.__enter__()

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        self.__exit__(exc_type, exc_val, exc_tb)

    @staticmethod
    def set(**kwargs) -> None:
        """Set context variables without context manager."""
        current = _log_context.get().copy()
        current.update(kwargs)
        _log_context.set(current)

    @staticmethod
    def get() -> Dict[str, Any]:
        """Get current log context."""
        return _log_context.get().copy()

    @staticmethod
    def clear() -> None:
        """Clear log context."""
        _log_context.set({})


def add_log_context(
    logger: structlog.types.WrappedLogger,
    method_name: str,
    event_dict: Dict[str, Any],
) -> Dict[str, Any]:
    """Add context variables to log event."""
    context = _log_context.get()
    event_dict.update(context)
    return event_dict


def setup_logging(
    service_name: str,
    level: str = "INFO",
    json_format: bool = True,
    add_timestamp: bool = True,
) -> None:
    """
    Set up structured logging for the service.

    Args:
        service_name: Name of the service
        level: Log level (DEBUG, INFO, WARNING, ERROR)
        json_format: Use JSON format (True for production)
        add_timestamp: Add timestamp to logs
    """
    # Common processors
    processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        add_log_context,
    ]

    if add_timestamp:
        processors.append(structlog.processors.TimeStamper(fmt="iso"))

    processors.extend([
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ])

    # Add service name
    processors.insert(0, lambda _, __, event_dict: {
        "service": service_name,
        **event_dict,
    })

    if json_format:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, level.upper())
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Also configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, level.upper()),
    )

    # Silence noisy loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


def get_logger(name: Optional[str] = None) -> structlog.BoundLogger:
    """
    Get a structured logger.

    Args:
        name: Logger name (optional)

    Returns:
        Bound logger instance
    """
    return structlog.get_logger(name)


class LoggerAdapter:
    """
    Adapter to make structlog work like standard logging.

    Useful for compatibility with libraries expecting standard loggers.
    """

    def __init__(self, logger: structlog.BoundLogger):
        self._logger = logger

    def debug(self, msg: str, *args, **kwargs) -> None:
        self._logger.debug(msg, *args, **kwargs)

    def info(self, msg: str, *args, **kwargs) -> None:
        self._logger.info(msg, *args, **kwargs)

    def warning(self, msg: str, *args, **kwargs) -> None:
        self._logger.warning(msg, *args, **kwargs)

    def error(self, msg: str, *args, **kwargs) -> None:
        self._logger.error(msg, *args, **kwargs)

    def exception(self, msg: str, *args, **kwargs) -> None:
        self._logger.exception(msg, *args, **kwargs)

    def critical(self, msg: str, *args, **kwargs) -> None:
        self._logger.critical(msg, *args, **kwargs)


def request_id_middleware(app):
    """
    Middleware to add request ID to log context.

    Usage:
        app = FastAPI()
        app.middleware("http")(request_id_middleware(app))
    """
    import uuid
    from fastapi import Request

    async def middleware(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))

        with LogContext(request_id=request_id):
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            return response

    return middleware
