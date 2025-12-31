"""
Security Middleware for FastAPI Services

Provides security middleware components for production deployment.
"""
import re
import time
import logging
import hashlib
from typing import Callable, Dict, Any, Optional
from datetime import datetime
from collections import defaultdict

from fastapi import Request, Response, HTTPException
from fastapi.middleware.base import BaseHTTPMiddleware
from starlette.middleware.base import RequestResponseEndpoint

from .security_config import get_security_config, mask_sensitive_data

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses"""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        response = await call_next(request)

        security_config = get_security_config()

        for header, value in security_config.headers.headers.items():
            response.headers[header] = value

        # Add HSTS header if enabled
        if security_config.tls.hsts_enabled:
            hsts_value = f"max-age={security_config.tls.hsts_max_age}"
            if security_config.tls.hsts_include_subdomains:
                hsts_value += "; includeSubDomains"
            if security_config.tls.hsts_preload:
                hsts_value += "; preload"
            response.headers["Strict-Transport-Security"] = hsts_value

        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware with sliding window"""

    def __init__(self, app, redis_client=None):
        super().__init__(app)
        self.redis = redis_client
        self.local_cache: Dict[str, list] = defaultdict(list)
        self.config = get_security_config().rate_limit

    def _get_client_id(self, request: Request) -> str:
        """Get unique client identifier"""
        # Try to get user ID from auth token
        user_id = getattr(request.state, "user_id", None)
        if user_id:
            return f"user:{user_id}"

        # Fall back to IP address
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return f"ip:{forwarded.split(',')[0].strip()}"

        return f"ip:{request.client.host}"

    def _is_auth_endpoint(self, path: str) -> bool:
        """Check if path is an auth endpoint"""
        auth_paths = ["/auth/login", "/auth/register", "/auth/token"]
        return any(auth_path in path for auth_path in auth_paths)

    async def _check_rate_limit(
        self,
        client_id: str,
        is_auth: bool
    ) -> tuple[bool, int]:
        """Check if request is within rate limits"""
        current_time = time.time()
        window = 60  # 1 minute window

        if is_auth:
            max_requests = self.config.auth_requests_per_minute
        else:
            max_requests = self.config.default_requests_per_minute

        if self.redis:
            # Use Redis for distributed rate limiting
            key = f"ratelimit:{client_id}:{int(current_time // window)}"
            count = await self.redis.incr(key)
            if count == 1:
                await self.redis.expire(key, window)
            remaining = max(0, max_requests - count)
            return count <= max_requests, remaining
        else:
            # Local cache fallback
            requests = self.local_cache[client_id]
            # Remove old requests
            cutoff = current_time - window
            requests = [r for r in requests if r > cutoff]
            requests.append(current_time)
            self.local_cache[client_id] = requests

            remaining = max(0, max_requests - len(requests))
            return len(requests) <= max_requests, remaining

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        client_id = self._get_client_id(request)
        is_auth = self._is_auth_endpoint(request.url.path)

        allowed, remaining = await self._check_rate_limit(client_id, is_auth)

        if not allowed:
            logger.warning(f"Rate limit exceeded for {client_id}")
            raise HTTPException(
                status_code=429,
                detail="Too many requests. Please try again later.",
                headers={
                    "Retry-After": "60",
                    "X-RateLimit-Remaining": "0"
                }
            )

        response = await call_next(request)

        # Add rate limit headers
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(time.time()) + 60)

        return response


class InputValidationMiddleware(BaseHTTPMiddleware):
    """Validate and sanitize input data"""

    def __init__(self, app):
        super().__init__(app)
        self.config = get_security_config().input_validation

    def _check_sql_injection(self, value: str) -> bool:
        """Check for SQL injection patterns"""
        for pattern in self.config.sql_injection_patterns:
            if re.search(pattern, value, re.IGNORECASE):
                return True
        return False

    def _check_xss(self, value: str) -> bool:
        """Check for XSS patterns"""
        for pattern in self.config.xss_patterns:
            if re.search(pattern, value, re.IGNORECASE):
                return True
        return False

    def _validate_value(self, value: Any, depth: int = 0) -> bool:
        """Recursively validate values"""
        if depth > self.config.max_json_depth:
            return False

        if isinstance(value, str):
            if len(value) > self.config.max_string_length:
                return False
            if self._check_sql_injection(value) or self._check_xss(value):
                return False

        elif isinstance(value, list):
            if len(value) > self.config.max_array_length:
                return False
            for item in value:
                if not self._validate_value(item, depth + 1):
                    return False

        elif isinstance(value, dict):
            for v in value.values():
                if not self._validate_value(v, depth + 1):
                    return False

        return True

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Check content type
        content_type = request.headers.get("content-type", "")
        if request.method in ["POST", "PUT", "PATCH"]:
            if not any(ct in content_type for ct in self.config.allowed_content_types):
                if content_type:  # Only reject if content-type is provided
                    raise HTTPException(
                        status_code=415,
                        detail=f"Unsupported content type: {content_type}"
                    )

        # Check request size
        content_length = request.headers.get("content-length")
        if content_length:
            max_bytes = self.config.max_request_size_mb * 1024 * 1024
            if int(content_length) > max_bytes:
                raise HTTPException(
                    status_code=413,
                    detail=f"Request too large. Max size: {self.config.max_request_size_mb}MB"
                )

        # Validate query parameters
        for key, value in request.query_params.items():
            if not self._validate_value(value):
                logger.warning(f"Suspicious query parameter: {key}")
                raise HTTPException(
                    status_code=400,
                    detail="Invalid request parameters"
                )

        return await call_next(request)


class AuditLogMiddleware(BaseHTTPMiddleware):
    """Audit logging middleware for security events"""

    def __init__(self, app, redis_client=None):
        super().__init__(app)
        self.redis = redis_client
        self.config = get_security_config().audit

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        start_time = time.time()
        request_id = request.headers.get("X-Request-ID", "")

        # Get user info if available
        user_id = getattr(request.state, "user_id", None)

        # Process request
        response = await call_next(request)

        # Calculate duration
        duration_ms = (time.time() - start_time) * 1000

        # Determine if this is an auditable event
        should_audit = self._should_audit(request, response)

        if should_audit:
            audit_entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "request_id": request_id,
                "user_id": user_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": round(duration_ms, 2),
                "ip_address": request.client.host if request.client else None,
                "user_agent": request.headers.get("user-agent"),
            }

            # Mask sensitive data
            audit_entry = mask_sensitive_data(audit_entry, self.config)

            # Log the audit entry
            logger.info(f"AUDIT: {audit_entry}")

            # Store in Redis if available
            if self.redis:
                await self._store_audit_entry(audit_entry)

        return response

    def _should_audit(self, request: Request, response: Response) -> bool:
        """Determine if request should be audited"""
        # Always audit auth endpoints
        if "/auth/" in request.url.path:
            return True

        # Audit write operations
        if request.method in ["POST", "PUT", "PATCH", "DELETE"]:
            return True

        # Audit errors
        if response.status_code >= 400:
            return True

        # Audit admin endpoints
        if "/admin/" in request.url.path:
            return True

        return False

    async def _store_audit_entry(self, entry: Dict[str, Any]):
        """Store audit entry in Redis"""
        try:
            import json
            key = f"audit:{datetime.utcnow().strftime('%Y%m%d')}"
            await self.redis.lpush(key, json.dumps(entry))
            await self.redis.ltrim(key, 0, 99999)  # Keep last 100K entries per day
            await self.redis.expire(key, self.config.log_retention_days * 86400)
        except Exception as e:
            logger.error(f"Failed to store audit entry: {e}")


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Add unique request ID to all requests"""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Get or generate request ID
        request_id = request.headers.get("X-Request-ID")
        if not request_id:
            request_id = hashlib.sha256(
                f"{time.time()}{request.client.host}".encode()
            ).hexdigest()[:16]

        # Store in request state
        request.state.request_id = request_id

        response = await call_next(request)

        # Add to response headers
        response.headers["X-Request-ID"] = request_id

        return response


def setup_security_middleware(app, redis_client=None):
    """Setup all security middleware for a FastAPI app"""
    # Order matters - add from last to first
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(AuditLogMiddleware, redis_client=redis_client)
    app.add_middleware(InputValidationMiddleware)
    app.add_middleware(RateLimitMiddleware, redis_client=redis_client)
    app.add_middleware(RequestIDMiddleware)

    logger.info("Security middleware configured")
