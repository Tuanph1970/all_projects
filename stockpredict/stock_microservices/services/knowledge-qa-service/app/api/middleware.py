"""API middleware - request logging, error handling."""
import time
import logging
from fastapi import Request

logger = logging.getLogger(__name__)


async def log_request_middleware(request: Request, call_next):
    """Log request details and timing."""
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time

    logger.info(
        f"{request.method} {request.url.path} -> {response.status_code} "
        f"({duration:.3f}s)"
    )
    return response
