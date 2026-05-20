"""Unit tests for app.services.journal_sync.

All HTTP traffic is mocked at the httpx.AsyncClient level so the tests
never need a live journal-service. Per the docstring, every helper must
catch exceptions and degrade quietly — these tests pin that contract.
"""
from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.services.journal_sync import (
    close_journal_trade,
    get_first_account_id,
    open_journal_trade,
)


class _FakeAsyncClient:
    """Async-context-manager stand-in for httpx.AsyncClient.

    Methods get/post/etc. are MagicMock async returning the canned response.
    """

    def __init__(self, response, *, raises: Exception | None = None,
                 method_name: str = "get"):
        self._response = response
        self._raises = raises
        self._method_name = method_name

    async def __aenter__(self):
        c = MagicMock()
        if self._raises is not None:
            setattr(c, self._method_name, AsyncMock(side_effect=self._raises))
            setattr(c, "post", AsyncMock(side_effect=self._raises))
            setattr(c, "get", AsyncMock(side_effect=self._raises))
        else:
            setattr(c, "get", AsyncMock(return_value=self._response))
            setattr(c, "post", AsyncMock(return_value=self._response))
        return c

    async def __aexit__(self, *_):
        return False


def _resp(status_code: int, json_body):
    r = MagicMock()
    r.status_code = status_code
    r.json.return_value = json_body
    if status_code >= 400:
        r.raise_for_status = MagicMock(
            side_effect=httpx.HTTPStatusError(
                "boom", request=MagicMock(), response=r,
            )
        )
    else:
        r.raise_for_status = MagicMock()
    return r


# ---------------------------------------------------------------------------
# get_first_account_id
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_first_account_id_returns_id_from_list():
    resp = _resp(200, [{"id": 7, "name": "Main"}, {"id": 8, "name": "IRA"}])
    with patch("app.services.journal_sync.httpx.AsyncClient",
               return_value=_FakeAsyncClient(resp)):
        assert await get_first_account_id("tok") == 7


@pytest.mark.asyncio
async def test_get_first_account_id_handles_dict_with_accounts_key():
    """journal-service may wrap the list in {'accounts': [...]} — supported."""
    resp = _resp(200, {"accounts": [{"id": 11}]})
    with patch("app.services.journal_sync.httpx.AsyncClient",
               return_value=_FakeAsyncClient(resp)):
        assert await get_first_account_id("tok") == 11


@pytest.mark.asyncio
async def test_get_first_account_id_handles_dict_with_items_key():
    resp = _resp(200, {"items": [{"id": 22}]})
    with patch("app.services.journal_sync.httpx.AsyncClient",
               return_value=_FakeAsyncClient(resp)):
        assert await get_first_account_id("tok") == 22


@pytest.mark.asyncio
async def test_get_first_account_id_returns_none_when_empty():
    resp = _resp(200, [])
    with patch("app.services.journal_sync.httpx.AsyncClient",
               return_value=_FakeAsyncClient(resp)):
        assert await get_first_account_id("tok") is None


@pytest.mark.asyncio
async def test_get_first_account_id_returns_none_on_http_error():
    """A 5xx must not propagate — the helper degrades quietly."""
    with patch("app.services.journal_sync.httpx.AsyncClient",
               return_value=_FakeAsyncClient(None, raises=httpx.ConnectError("down"))):
        assert await get_first_account_id("tok") is None


@pytest.mark.asyncio
async def test_get_first_account_id_returns_none_on_unexpected_shape():
    """Upstream sent a scalar instead of a list/dict — degrade to None."""
    resp = _resp(200, 42)
    with patch("app.services.journal_sync.httpx.AsyncClient",
               return_value=_FakeAsyncClient(resp)):
        assert await get_first_account_id("tok") is None


# ---------------------------------------------------------------------------
# open_journal_trade
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_open_journal_trade_returns_trade_id_for_long():
    resp = _resp(201, {"id": 555, "direction": "Long"})
    with patch("app.services.journal_sync.httpx.AsyncClient",
               return_value=_FakeAsyncClient(resp)):
        tid = await open_journal_trade(
            account_id=1, jwt_token="tok", ticker="VCB",
            direction="LONG", entry_date=date(2026, 5, 20),
            entry_price=82.5, initial_stop=80.0, position_size=100,
            signal_kind="ma_cross_up",
        )
    assert tid == 555


@pytest.mark.asyncio
async def test_open_journal_trade_returns_trade_id_for_short():
    resp = _resp(201, {"id": 556, "direction": "Short"})
    with patch("app.services.journal_sync.httpx.AsyncClient",
               return_value=_FakeAsyncClient(resp)):
        tid = await open_journal_trade(
            account_id=1, jwt_token="tok", ticker="VCB",
            direction="SHORT", entry_date=date(2026, 5, 20),
            entry_price=82.5, initial_stop=85.0, position_size=100,
        )
    assert tid == 556


@pytest.mark.asyncio
async def test_open_journal_trade_returns_none_on_error():
    """Upstream 500 → helper returns None (never raises)."""
    with patch("app.services.journal_sync.httpx.AsyncClient",
               return_value=_FakeAsyncClient(None, raises=httpx.ConnectError("down"))):
        tid = await open_journal_trade(
            account_id=1, jwt_token="tok", ticker="VCB",
            direction="LONG", entry_date=date(2026, 5, 20),
            entry_price=82.5, initial_stop=80.0, position_size=100,
        )
    assert tid is None


@pytest.mark.asyncio
async def test_open_journal_trade_returns_none_when_response_missing_id():
    resp = _resp(201, {})  # response payload missing 'id'
    with patch("app.services.journal_sync.httpx.AsyncClient",
               return_value=_FakeAsyncClient(resp)):
        tid = await open_journal_trade(
            account_id=1, jwt_token="tok", ticker="VCB",
            direction="LONG", entry_date=date(2026, 5, 20),
            entry_price=82.5, initial_stop=80.0, position_size=100,
        )
    assert tid is None


# ---------------------------------------------------------------------------
# close_journal_trade
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_close_journal_trade_returns_true_on_success():
    resp = _resp(200, {"closed": True})
    with patch("app.services.journal_sync.httpx.AsyncClient",
               return_value=_FakeAsyncClient(resp)):
        ok = await close_journal_trade(
            account_id=1, journal_trade_id=555, jwt_token="tok",
            exit_price=85.0, exit_date=date(2026, 5, 25),
            outcome="WIN",
        )
    assert ok is True


@pytest.mark.asyncio
async def test_close_journal_trade_no_outcome_still_succeeds():
    """outcome=None still emits a sensible reason and returns True."""
    resp = _resp(200, {"closed": True})
    with patch("app.services.journal_sync.httpx.AsyncClient",
               return_value=_FakeAsyncClient(resp)):
        ok = await close_journal_trade(
            account_id=1, journal_trade_id=555, jwt_token="tok",
            exit_price=85.0, exit_date=date(2026, 5, 25),
        )
    assert ok is True


@pytest.mark.asyncio
async def test_close_journal_trade_returns_false_on_error():
    with patch("app.services.journal_sync.httpx.AsyncClient",
               return_value=_FakeAsyncClient(None, raises=httpx.ConnectError("down"))):
        ok = await close_journal_trade(
            account_id=1, journal_trade_id=555, jwt_token="tok",
            exit_price=85.0, exit_date=date(2026, 5, 25),
        )
    assert ok is False
