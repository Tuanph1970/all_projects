"""Global exception to HTTP response mapping."""
import logging
from fastapi import Request
from fastapi.responses import JSONResponse

from app.domain.exceptions import (
    KnowledgeQAError,
    GraphConnectionError,
    LLMConnectionError,
    SessionNotFoundError,
    EmptyQueryError,
    GraphQueryError,
)

logger = logging.getLogger(__name__)


async def knowledge_qa_error_handler(request: Request, exc: KnowledgeQAError):
    """Handle domain-specific exceptions."""
    if isinstance(exc, EmptyQueryError):
        return JSONResponse(status_code=400, content={"detail": str(exc)})
    if isinstance(exc, SessionNotFoundError):
        return JSONResponse(status_code=404, content={"detail": str(exc)})
    if isinstance(exc, GraphConnectionError):
        return JSONResponse(status_code=503, content={"detail": "Knowledge graph unavailable"})
    if isinstance(exc, LLMConnectionError):
        return JSONResponse(status_code=503, content={"detail": "LLM service unavailable"})
    if isinstance(exc, GraphQueryError):
        return JSONResponse(status_code=500, content={"detail": "Graph query failed"})
    return JSONResponse(status_code=500, content={"detail": "Internal error"})


async def global_exception_handler(request: Request, exc: Exception):
    """Handle all unhandled exceptions."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "type": type(exc).__name__},
    )
