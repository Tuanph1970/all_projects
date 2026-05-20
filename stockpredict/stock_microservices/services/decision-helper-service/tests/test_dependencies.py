"""Unit tests for app.api.dependencies — JWT helpers."""
from __future__ import annotations

import datetime as _dt

import jwt
import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.api.dependencies import (
    get_current_user,
    get_current_user_from_token,
    get_current_user_optional,
    settings,
)


def _token(payload: dict) -> str:
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


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
    out = await get_current_user_optional(
        credentials=_creds(_token({"sub": "42", "email": "u@x.io"}))
    )
    assert out == {"user_id": 42, "email": "u@x.io"}


@pytest.mark.asyncio
async def test_optional_returns_none_on_invalid_token():
    out = await get_current_user_optional(credentials=_creds("not-a-jwt"))
    assert out is None


@pytest.mark.asyncio
async def test_optional_returns_none_on_expired_token():
    """Expired token = InvalidTokenError subclass; helper still returns None."""
    past = _dt.datetime.now(_dt.timezone.utc) - _dt.timedelta(hours=1)
    out = await get_current_user_optional(
        credentials=_creds(_token({"sub": "1", "exp": int(past.timestamp())}))
    )
    assert out is None


# ---------------------------------------------------------------------------
# get_current_user (required)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_required_returns_user_for_valid_token():
    out = await get_current_user(
        credentials=_creds(_token({"sub": "9", "email": "a@b.io"}))
    )
    assert out == {"user_id": 9, "email": "a@b.io"}


@pytest.mark.asyncio
async def test_required_rejects_when_sub_missing():
    with pytest.raises(HTTPException) as ei:
        await get_current_user(credentials=_creds(_token({"email": "no-sub@x.io"})))
    assert ei.value.status_code == 401


@pytest.mark.asyncio
async def test_required_rejects_invalid_token():
    with pytest.raises(HTTPException) as ei:
        await get_current_user(credentials=_creds("bogus"))
    assert ei.value.status_code == 401


@pytest.mark.asyncio
async def test_required_rejects_expired_token():
    past = _dt.datetime.now(_dt.timezone.utc) - _dt.timedelta(hours=1)
    with pytest.raises(HTTPException) as ei:
        await get_current_user(
            credentials=_creds(_token({"sub": "1", "exp": int(past.timestamp())}))
        )
    assert ei.value.status_code == 401


# ---------------------------------------------------------------------------
# get_current_user_from_token — used by the /alerts/stream SSE endpoint
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_from_token_returns_user_for_valid_token():
    out = await get_current_user_from_token(_token({"sub": "5", "email": "s@x.io"}))
    assert out == {"user_id": 5, "email": "s@x.io"}


@pytest.mark.asyncio
async def test_from_token_rejects_missing_sub():
    with pytest.raises(HTTPException) as ei:
        await get_current_user_from_token(_token({"email": "no-sub@x.io"}))
    assert ei.value.status_code == 401


@pytest.mark.asyncio
async def test_from_token_rejects_invalid():
    with pytest.raises(HTTPException) as ei:
        await get_current_user_from_token("not-a-jwt")
    assert ei.value.status_code == 401
