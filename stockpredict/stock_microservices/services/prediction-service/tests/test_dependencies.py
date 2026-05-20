"""Unit tests for app.api.dependencies — JWT helpers.

The auth helpers branch on:
- credentials present vs missing (optional flavor)
- valid JWT vs ExpiredSignatureError vs InvalidTokenError
- payload "sub" present vs None
- admin role enforcement

We test them as plain callables (no FastAPI request lifecycle needed)
because they're already DI-friendly.
"""
from __future__ import annotations

import jwt
import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.api.dependencies import (
    get_current_user,
    get_current_user_optional,
    require_admin,
    settings,
)


def _make_token(payload: dict, *, secret: str | None = None,
                algorithm: str | None = None) -> str:
    return jwt.encode(
        payload,
        secret or settings.JWT_SECRET_KEY,
        algorithm=algorithm or settings.JWT_ALGORITHM,
    )


def _creds(token: str) -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


# ---------------------------------------------------------------------------
# get_current_user_optional
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_optional_returns_none_when_no_credentials():
    assert await get_current_user_optional(credentials=None) is None


@pytest.mark.asyncio
async def test_optional_returns_user_dict_for_valid_token():
    token = _make_token({"sub": "42", "email": "user@example.com", "role": "user"})
    out = await get_current_user_optional(credentials=_creds(token))
    assert out == {"user_id": 42, "email": "user@example.com", "role": "user"}


@pytest.mark.asyncio
async def test_optional_returns_none_on_invalid_token():
    """A bogus token must not raise; just yield None."""
    out = await get_current_user_optional(credentials=_creds("not-a-jwt"))
    assert out is None


@pytest.mark.asyncio
async def test_optional_defaults_role_to_user_when_missing():
    token = _make_token({"sub": "7", "email": "u@x.io"})
    out = await get_current_user_optional(credentials=_creds(token))
    assert out is not None
    assert out["role"] == "user"


# ---------------------------------------------------------------------------
# get_current_user (required)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_required_returns_user_for_valid_token():
    token = _make_token({"sub": "9", "email": "x@y.io", "role": "admin"})
    out = await get_current_user(credentials=_creds(token))
    assert out["user_id"] == 9
    assert out["role"] == "admin"


@pytest.mark.asyncio
async def test_required_rejects_when_sub_is_missing():
    token = _make_token({"email": "no-sub@x.io"})  # no `sub`
    with pytest.raises(HTTPException) as ei:
        await get_current_user(credentials=_creds(token))
    assert ei.value.status_code == 401


@pytest.mark.asyncio
async def test_required_rejects_expired_token():
    # Build a token whose exp is in the past — jwt.decode raises
    # ExpiredSignatureError, which the helper maps to a 401.
    import datetime
    past = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=1)
    token = _make_token({"sub": "1", "exp": int(past.timestamp())})
    with pytest.raises(HTTPException) as ei:
        await get_current_user(credentials=_creds(token))
    assert ei.value.status_code == 401
    assert "expired" in ei.value.detail.lower()


@pytest.mark.asyncio
async def test_required_rejects_invalid_token():
    with pytest.raises(HTTPException) as ei:
        await get_current_user(credentials=_creds("not-a-jwt"))
    assert ei.value.status_code == 401
    assert "invalid token" in ei.value.detail.lower()


# ---------------------------------------------------------------------------
# require_admin
# ---------------------------------------------------------------------------


def test_require_admin_accepts_admin_role():
    user = {"user_id": 1, "role": "admin", "email": "a@x.io"}
    assert require_admin(current_user=user) is user


def test_require_admin_rejects_non_admin():
    user = {"user_id": 1, "role": "user", "email": "u@x.io"}
    with pytest.raises(HTTPException) as ei:
        require_admin(current_user=user)
    assert ei.value.status_code == 403


def test_require_admin_rejects_missing_role():
    """When the JWT payload had no `role` at all, the helper defaults to
    'user' upstream — but if some callsite hands us a dict without one,
    treat it as non-admin."""
    with pytest.raises(HTTPException) as ei:
        require_admin(current_user={"user_id": 1, "email": "u@x.io"})
    assert ei.value.status_code == 403
