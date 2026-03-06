"""
Custom middleware for the Mathematics LLM OCR Service.
"""
import time
import uuid
from typing import Callable, Dict, Any, Optional
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.status import HTTP_429_TOO_MANY_REQUESTS, HTTP_503_SERVICE_UNAVAILABLE
from loguru import logger
from collections import defaultdict
import asyncio


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for logging HTTP requests and responses.
    
    Logs request details including method, path, headers, and processing time.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and log details."""
        # Generate request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Extract request information
        method = request.method
        path = request.url.path
        client_host = request.client.host if request.client else "unknown"
        query_params = str(request.url.query) if request.url.query else ""
        
        # Log request
        start_time = time.time()
        logger.info(
            f"Request started: {method} {path}",
            extra={
                "request_id": request_id,
                "method": method,
                "path": path,
                "query_params": query_params,
                "client_host": client_host,
            }
        )
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate processing time
            process_time = time.time() - start_time
            
            # Log response
            logger.info(
                f"Request completed: {method} {path} - {response.status_code}",
                extra={
                    "request_id": request_id,
                    "status_code": response.status_code,
                    "process_time": f"{process_time:.4f}s",
                }
            )
            
            # Add timing header
            response.headers["X-Process-Time"] = str(process_time)
            response.headers["X-Request-ID"] = request_id
            
            return response
            
        except Exception as e:
            process_time = time.time() - start_time
            logger.error(
                f"Request failed: {method} {path} - {str(e)}",
                extra={
                    "request_id": request_id,
                    "method": method,
                    "path": path,
                    "process_time": f"{process_time:.4f}s",
                    "error": str(e),
                },
                exc_info=True
            )
            raise


class MetricsMiddleware(BaseHTTPMiddleware):
    """
    Middleware for collecting request metrics.
    
    Tracks request counts, response times, and error rates.
    """

    def __init__(self, app, *args, **kwargs):
        super().__init__(app, *args, **kwargs)
        self.request_counts: Dict[str, int] = defaultdict(int)
        self.response_times: Dict[str, list] = defaultdict(list)
        self.error_counts: Dict[str, int] = defaultdict(int)
        self.max_history = 1000  # Keep last 1000 response times per endpoint

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and collect metrics."""
        method = request.method
        path = request.url.path
        endpoint_key = f"{method}:{path}"
        
        # Increment request count
        self.request_counts[endpoint_key] += 1
        
        # Track response time
        start_time = time.time()
        
        try:
            response = await call_next(request)
            
            process_time = time.time() - start_time
            self.response_times[endpoint_key].append(process_time)
            
            # Trim history if too long
            if len(self.response_times[endpoint_key]) > self.max_history:
                self.response_times[endpoint_key] = self.response_times[endpoint_key][-self.max_history:]
            
            # Track errors
            if response.status_code >= 400:
                self.error_counts[endpoint_key] += 1
            
            return response
            
        except Exception as e:
            process_time = time.time() - start_time
            self.response_times[endpoint_key].append(process_time)
            self.error_counts[endpoint_key] += 1
            raise

    def get_metrics(self) -> Dict[str, Any]:
        """Get collected metrics."""
        metrics = {}
        
        for endpoint_key in self.request_counts:
            times = self.response_times.get(endpoint_key, [])
            
            if times:
                metrics[endpoint_key] = {
                    "request_count": self.request_counts[endpoint_key],
                    "error_count": self.error_counts[endpoint_key],
                    "avg_response_time": sum(times) / len(times),
                    "min_response_time": min(times),
                    "max_response_time": max(times),
                    "p95_response_time": sorted(times)[int(len(times) * 0.95)] if len(times) >= 20 else max(times),
                }
            else:
                metrics[endpoint_key] = {
                    "request_count": self.request_counts[endpoint_key],
                    "error_count": self.error_counts[endpoint_key],
                }
        
        return metrics


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware for rate limiting API requests.
    
    Implements a sliding window rate limiting algorithm.
    """

    def __init__(
        self,
        app,
        requests_per_minute: int = 100,
        window_seconds: int = 60,
        *args,
        **kwargs
    ):
        super().__init__(app, *args, **kwargs)
        self.requests_per_minute = requests_per_minute
        self.window_seconds = window_seconds
        self.request_history: Dict[str, list] = defaultdict(list)
        self._cleanup_task: Optional[asyncio.Task] = None
        
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with rate limiting."""
        # Get client identifier (IP address or API key)
        client_id = self._get_client_identifier(request)
        current_time = time.time()
        
        # Clean old requests outside the window
        self._clean_old_requests(client_id, current_time)
        
        # Check rate limit
        if len(self.request_history[client_id]) >= self.requests_per_minute:
            logger.warning(
                f"Rate limit exceeded for client {client_id}",
                extra={"client_id": client_id, "limit": self.requests_per_minute}
            )
            
            return JSONResponse(
                status_code=HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "success": False,
                    "error": "Rate limit exceeded",
                    "message": f"Too many requests. Limit: {self.requests_per_minute} per {self.window_seconds} seconds",
                    "retry_after": int(self._get_retry_after(client_id, current_time))
                },
                headers={
                    "Retry-After": str(int(self._get_retry_after(client_id, current_time))),
                    "X-RateLimit-Limit": str(self.requests_per_minute),
                    "X-RateLimit-Remaining": "0"
                }
            )
        
        # Record this request
        self.request_history[client_id].append(current_time)
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        remaining = self.requests_per_minute - len(self.request_history[client_id])
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(current_time + self.window_seconds))
        
        return response

    def _get_client_identifier(self, request: Request) -> str:
        """Get unique client identifier."""
        # Try API key first
        api_key = request.headers.get("X-API-Key")
        if api_key:
            return f"api_key:{api_key}"
        
        # Fall back to IP address
        client_host = request.client.host if request.client else "unknown"
        return f"ip:{client_host}"

    def _clean_old_requests(self, client_id: str, current_time: float) -> None:
        """Remove requests outside the current time window."""
        window_start = current_time - self.window_seconds
        self.request_history[client_id] = [
            timestamp for timestamp in self.request_history[client_id]
            if timestamp > window_start
        ]

    def _get_retry_after(self, client_id: str, current_time: float) -> float:
        """Calculate time until rate limit resets."""
        if not self.request_history[client_id]:
            return 0.0
        
        oldest_request = min(self.request_history[client_id])
        retry_after = (oldest_request + self.window_seconds) - current_time
        return max(0.0, retry_after)


class APIKeyMiddleware(BaseHTTPMiddleware):
    """
    Middleware for API key authentication.
    
    Validates API keys for protected endpoints.
    """

    def __init__(self, app, valid_api_keys: list = None, *args, **kwargs):
        super().__init__(app, *args, **kwargs)
        self.valid_api_keys = set(valid_api_keys or [])
        # Public endpoints that don't require authentication
        self.public_endpoints = {
            "/health",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/metrics",
            "/",
        }

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with API key validation."""
        path = request.url.path
        
        # Skip authentication for public endpoints
        if self._is_public_endpoint(path):
            return await call_next(request)
        
        # Validate API key
        api_key = request.headers.get("X-API-Key")
        
        if not api_key:
            logger.warning(f"Missing API key for {path}")
            return JSONResponse(
                status_code=401,
                content={
                    "success": False,
                    "error": "Unauthorized",
                    "message": "API key required. Please provide X-API-Key header."
                },
                headers={"WWW-Authenticate": "ApiKey"}
            )
        
        if api_key not in self.valid_api_keys:
            logger.warning(f"Invalid API key attempt for {path}")
            return JSONResponse(
                status_code=401,
                content={
                    "success": False,
                    "error": "Unauthorized",
                    "message": "Invalid API key"
                }
            )
        
        return await call_next(request)

    def _is_public_endpoint(self, path: str) -> bool:
        """Check if endpoint is publicly accessible."""
        return any(path.startswith(public) for public in self.public_endpoints)


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware for limiting request body size.
    
    Prevents large payload attacks by limiting request size.
    """

    def __init__(self, app, max_size_bytes: int = 10 * 1024 * 1024, *args, **kwargs):
        """
        Initialize middleware.
        
        Args:
            app: FastAPI application
            max_size_bytes: Maximum request size in bytes (default: 10MB)
        """
        super().__init__(app, *args, **kwargs)
        self.max_size_bytes = max_size_bytes

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with size limit check."""
        # Check content length header
        content_length = request.headers.get("content-length")
        
        if content_length:
            try:
                size = int(content_length)
                if size > self.max_size_bytes:
                    logger.warning(
                        f"Request size {size} exceeds limit {self.max_size_bytes}",
                        extra={"path": request.url.path}
                    )
                    return JSONResponse(
                        status_code=413,
                        content={
                            "success": False,
                            "error": "Payload too large",
                            "message": f"Request size exceeds maximum allowed size of {self.max_size_bytes / (1024*1024):.1f}MB"
                        }
                    )
            except (ValueError, TypeError):
                pass
        
        return await call_next(request)


class CORSPreflightMiddleware(BaseHTTPMiddleware):
    """
    Middleware for handling CORS preflight requests.
    
    Provides additional CORS support beyond FastAPI's built-in CORS middleware.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with CORS headers."""
        # Handle OPTIONS preflight requests
        if request.method == "OPTIONS":
            response = Response(status_code=200)
            self._add_cors_headers(response)
            return response
        
        # Process normal request
        response = await call_next(request)
        self._add_cors_headers(response)
        return response

    def _add_cors_headers(self, response: Response) -> None:
        """Add CORS headers to response."""
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-API-Key, X-Request-ID"
        response.headers["Access-Control-Max-Age"] = "86400"  # 24 hours
