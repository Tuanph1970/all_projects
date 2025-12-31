"""
JWT token creation and validation.

Provides:
- Access token creation
- Refresh token creation
- Token decoding and validation
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from jose import JWTError, jwt
from pydantic import BaseModel, Field

from stock_common.config import JWTConfig

logger = logging.getLogger(__name__)


class TokenPayload(BaseModel):
    """JWT token payload structure."""

    sub: str = Field(..., description="Subject (user ID)")
    exp: datetime = Field(..., description="Expiration time")
    iat: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Issued at")
    type: str = Field(default="access", description="Token type (access/refresh)")
    # Additional claims
    email: Optional[str] = Field(default=None, description="User email")
    username: Optional[str] = Field(default=None, description="Username")
    roles: list[str] = Field(default_factory=list, description="User roles")


class TokenData(BaseModel):
    """Decoded token data."""

    user_id: str
    email: Optional[str] = None
    username: Optional[str] = None
    roles: list[str] = Field(default_factory=list)
    token_type: str = "access"
    expires_at: datetime


class InvalidTokenError(Exception):
    """Exception raised for invalid tokens."""

    def __init__(self, message: str = "Invalid token"):
        self.message = message
        super().__init__(message)


class TokenExpiredError(InvalidTokenError):
    """Exception raised for expired tokens."""

    def __init__(self):
        super().__init__("Token has expired")


def create_access_token(
    user_id: str,
    config: JWTConfig,
    email: Optional[str] = None,
    username: Optional[str] = None,
    roles: Optional[list[str]] = None,
    additional_claims: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Create a JWT access token.

    Args:
        user_id: User identifier
        config: JWT configuration
        email: Optional user email
        username: Optional username
        roles: Optional list of user roles
        additional_claims: Optional additional claims to include

    Returns:
        Encoded JWT token string
    """
    now = datetime.now(timezone.utc)
    expires = now + timedelta(minutes=config.access_token_expire_minutes)

    payload = {
        "sub": str(user_id),
        "exp": expires,
        "iat": now,
        "type": "access",
    }

    if email:
        payload["email"] = email
    if username:
        payload["username"] = username
    if roles:
        payload["roles"] = roles
    if additional_claims:
        payload.update(additional_claims)

    token = jwt.encode(payload, config.secret_key, algorithm=config.algorithm)
    logger.debug(f"Created access token for user {user_id}, expires at {expires}")

    return token


def create_refresh_token(
    user_id: str,
    config: JWTConfig,
    additional_claims: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Create a JWT refresh token.

    Args:
        user_id: User identifier
        config: JWT configuration
        additional_claims: Optional additional claims

    Returns:
        Encoded JWT refresh token string
    """
    now = datetime.now(timezone.utc)
    expires = now + timedelta(days=config.refresh_token_expire_days)

    payload = {
        "sub": str(user_id),
        "exp": expires,
        "iat": now,
        "type": "refresh",
    }

    if additional_claims:
        payload.update(additional_claims)

    token = jwt.encode(payload, config.secret_key, algorithm=config.algorithm)
    logger.debug(f"Created refresh token for user {user_id}, expires at {expires}")

    return token


def decode_token(
    token: str,
    config: JWTConfig,
    token_type: str = "access",
    verify_exp: bool = True,
) -> TokenData:
    """
    Decode and validate a JWT token.

    Args:
        token: JWT token string
        config: JWT configuration
        token_type: Expected token type (access/refresh)
        verify_exp: Whether to verify expiration

    Returns:
        Decoded token data

    Raises:
        InvalidTokenError: If token is invalid
        TokenExpiredError: If token has expired
    """
    try:
        payload = jwt.decode(
            token,
            config.secret_key,
            algorithms=[config.algorithm],
            options={"verify_exp": verify_exp},
        )
    except jwt.ExpiredSignatureError:
        raise TokenExpiredError()
    except JWTError as e:
        logger.warning(f"JWT decode error: {e}")
        raise InvalidTokenError(f"Invalid token: {e}")

    # Validate token type
    if payload.get("type") != token_type:
        raise InvalidTokenError(
            f"Invalid token type. Expected {token_type}, got {payload.get('type')}"
        )

    # Extract user data
    user_id = payload.get("sub")
    if not user_id:
        raise InvalidTokenError("Token missing subject claim")

    return TokenData(
        user_id=user_id,
        email=payload.get("email"),
        username=payload.get("username"),
        roles=payload.get("roles", []),
        token_type=payload.get("type", "access"),
        expires_at=datetime.fromtimestamp(payload["exp"], tz=timezone.utc),
    )


def get_token_from_header(authorization: str) -> str:
    """
    Extract token from Authorization header.

    Args:
        authorization: Authorization header value (e.g., "Bearer <token>")

    Returns:
        Token string

    Raises:
        InvalidTokenError: If header format is invalid
    """
    if not authorization:
        raise InvalidTokenError("Missing authorization header")

    parts = authorization.split()

    if len(parts) != 2:
        raise InvalidTokenError("Invalid authorization header format")

    scheme, token = parts

    if scheme.lower() != "bearer":
        raise InvalidTokenError(f"Invalid authentication scheme: {scheme}")

    return token
