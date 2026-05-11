"""Tests for app.api.dependencies — JWT helpers.

`get_current_user_optional` returns None on missing/invalid tokens
(used by /trending, /sectors, /capabilities); `get_current_user`
raises 401 on the same conditions (used everywhere else).
"""
import jwt
import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.api import dependencies
from app.config import get_settings


def _make_token(payload: dict) -> str:
    s = get_settings()
    return jwt.encode(payload, s.JWT_SECRET_KEY, algorithm=s.JWT_ALGORITHM)


def _creds(token: str) -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


@pytest.mark.asyncio
async def test_get_current_user_optional_returns_none_without_credentials():
    user = await dependencies.get_current_user_optional(credentials=None)
    assert user is None


@pytest.mark.asyncio
async def test_get_current_user_optional_returns_none_on_invalid_token():
    user = await dependencies.get_current_user_optional(credentials=_creds("not.a.jwt"))
    assert user is None


@pytest.mark.asyncio
async def test_get_current_user_optional_returns_user_on_valid_token():
    token = _make_token({"sub": "42", "email": "alice@example.com"})
    user = await dependencies.get_current_user_optional(credentials=_creds(token))
    assert user == {"user_id": 42, "email": "alice@example.com"}


@pytest.mark.asyncio
async def test_get_current_user_raises_401_on_invalid_token():
    with pytest.raises(HTTPException) as exc:
        await dependencies.get_current_user(credentials=_creds("not.a.jwt"))
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_raises_401_when_sub_missing():
    # Token decodes, but missing 'sub' claim → 401 not silently passed through.
    token = _make_token({"email": "no-subject@example.com"})
    with pytest.raises(HTTPException) as exc:
        await dependencies.get_current_user(credentials=_creds(token))
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_returns_dict_on_valid_token():
    token = _make_token({"sub": "7", "email": "bob@example.com"})
    user = await dependencies.get_current_user(credentials=_creds(token))
    assert user == {"user_id": 7, "email": "bob@example.com"}
