"""
Authentication module for JWT-based authentication.

Provides:
- JWT token creation and validation
- FastAPI authentication middleware
- User context management
- Password hashing utilities
"""

from stock_common.auth.jwt import (
    create_access_token,
    create_refresh_token,
    decode_token,
    TokenData,
    TokenPayload,
)
from stock_common.auth.middleware import (
    JWTAuthMiddleware,
    get_current_user,
    require_auth,
    CurrentUser,
)
from stock_common.auth.password import (
    hash_password,
    verify_password,
)

__all__ = [
    # JWT
    "create_access_token",
    "create_refresh_token",
    "decode_token",
    "TokenData",
    "TokenPayload",
    # Middleware
    "JWTAuthMiddleware",
    "get_current_user",
    "require_auth",
    "CurrentUser",
    # Password
    "hash_password",
    "verify_password",
]
