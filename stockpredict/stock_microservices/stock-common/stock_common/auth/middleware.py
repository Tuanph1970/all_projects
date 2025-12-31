"""
FastAPI authentication middleware and dependencies.

Provides:
- JWT authentication middleware
- Current user dependency
- Role-based authorization
"""

import logging
from contextvars import ContextVar
from functools import wraps
from typing import Annotated, Callable, List, Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from stock_common.config import JWTConfig, get_config
from stock_common.auth.jwt import (
    TokenData,
    decode_token,
    get_token_from_header,
    InvalidTokenError,
    TokenExpiredError,
)

logger = logging.getLogger(__name__)

# Context variable for current user
_current_user: ContextVar[Optional[TokenData]] = ContextVar("current_user", default=None)

# Security scheme
security = HTTPBearer(auto_error=False)


class CurrentUser:
    """
    Current authenticated user context.

    Provides access to the current user's data from JWT token.
    """

    @staticmethod
    def get() -> Optional[TokenData]:
        """Get current user data."""
        return _current_user.get()

    @staticmethod
    def set(user: Optional[TokenData]) -> None:
        """Set current user data."""
        _current_user.set(user)

    @staticmethod
    def get_id() -> Optional[str]:
        """Get current user ID."""
        user = _current_user.get()
        return user.user_id if user else None

    @staticmethod
    def get_roles() -> List[str]:
        """Get current user roles."""
        user = _current_user.get()
        return user.roles if user else []

    @staticmethod
    def has_role(role: str) -> bool:
        """Check if current user has a specific role."""
        return role in CurrentUser.get_roles()

    @staticmethod
    def require_role(role: str) -> None:
        """Require current user to have a specific role."""
        if not CurrentUser.has_role(role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{role}' required",
            )


class JWTAuthMiddleware:
    """
    ASGI middleware for JWT authentication.

    Extracts JWT token from Authorization header and sets current user context.
    Does not block requests without tokens (use dependencies for that).
    """

    def __init__(self, app, config: Optional[JWTConfig] = None):
        self.app = app
        self.config = config or get_config().jwt

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            headers = dict(scope.get("headers", []))
            auth_header = headers.get(b"authorization", b"").decode()

            if auth_header:
                try:
                    token = get_token_from_header(auth_header)
                    user_data = decode_token(token, self.config)
                    CurrentUser.set(user_data)
                    logger.debug(f"Authenticated user: {user_data.user_id}")
                except (InvalidTokenError, TokenExpiredError) as e:
                    logger.debug(f"Authentication failed: {e}")
                    CurrentUser.set(None)
            else:
                CurrentUser.set(None)

        await self.app(scope, receive, send)


async def get_current_user(
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(security)],
    config: JWTConfig = Depends(lambda: get_config().jwt),
) -> TokenData:
    """
    FastAPI dependency for getting the current authenticated user.

    Raises HTTPException 401 if not authenticated.

    Usage:
        @app.get("/protected")
        async def protected_route(user: TokenData = Depends(get_current_user)):
            return {"user_id": user.user_id}
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        token_data = decode_token(credentials.credentials, config)
        return token_data
    except TokenExpiredError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_optional_user(
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(security)],
    config: JWTConfig = Depends(lambda: get_config().jwt),
) -> Optional[TokenData]:
    """
    FastAPI dependency for optionally getting the current user.

    Returns None if not authenticated (does not raise exception).

    Usage:
        @app.get("/public-with-user-context")
        async def public_route(user: Optional[TokenData] = Depends(get_optional_user)):
            if user:
                return {"message": f"Hello, {user.username}"}
            return {"message": "Hello, guest"}
    """
    if not credentials:
        return None

    try:
        return decode_token(credentials.credentials, config)
    except (InvalidTokenError, TokenExpiredError):
        return None


def require_auth(func: Callable) -> Callable:
    """
    Decorator for requiring authentication on a route.

    Usage:
        @app.get("/protected")
        @require_auth
        async def protected_route(request: Request):
            user = CurrentUser.get()
            return {"user_id": user.user_id}
    """

    @wraps(func)
    async def wrapper(*args, **kwargs):
        user = CurrentUser.get()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return await func(*args, **kwargs)

    return wrapper


def require_roles(*roles: str) -> Callable:
    """
    Decorator for requiring specific roles.

    Usage:
        @app.get("/admin")
        @require_roles("admin")
        async def admin_route():
            return {"message": "Admin only"}

        @app.get("/staff")
        @require_roles("admin", "staff")
        async def staff_route():
            return {"message": "Admin or staff"}
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            user = CurrentUser.get()
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Not authenticated",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            if not any(role in user.roles for role in roles):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Required roles: {', '.join(roles)}",
                )

            return await func(*args, **kwargs)

        return wrapper

    return decorator


class RoleChecker:
    """
    Dependency for checking user roles.

    Usage:
        @app.get("/admin", dependencies=[Depends(RoleChecker(["admin"]))])
        async def admin_route():
            return {"message": "Admin only"}
    """

    def __init__(self, required_roles: List[str]):
        self.required_roles = required_roles

    async def __call__(
        self, user: TokenData = Depends(get_current_user)
    ) -> TokenData:
        if not any(role in user.roles for role in self.required_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Required roles: {', '.join(self.required_roles)}",
            )
        return user
