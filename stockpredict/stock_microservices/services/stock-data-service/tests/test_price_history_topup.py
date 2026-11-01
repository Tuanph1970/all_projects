"""Backlog #114 — historical-data must not serve a frozen tail.

get_historical_data served the DB whenever ANY row fell in the range, and
only the VN30 is re-synced in the background (weekly), so a symbol like DPG
stayed at the day it was first added: a request for Aug-Oct returned bars
only to 09-29 while the vendor had them to 10-30. These tests pin the tail
top-up: when it fires, how far it fetches, and that it never makes a read
worse than before.

All times are naive UTC, as _utcnow() returns them; ICT = UTC+7.
"""
from datetime import date, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest

from app.models.domain import Company, StockPrice
from app.services import stock_service as svc_mod
from app.services.stock_service import (
    StockService,
    last_completed_session,
    price_history_target,
)

# Thu 2026-10-29 is a weekday; 2026-10-31 is a Saturday.
THU_AFTER_CLOSE = datetime(2026, 10, 29, 9, 0)   # 16:00 ICT
THU_IN_SESSION = datetime(2026, 10, 29, 3, 0)    # 10:00 ICT
MON_MORNING = datetime(2026, 11, 2, 1, 0)        # 08:00 ICT Mon
SATURDAY = datetime(2026, 10, 31, 5, 0)


@pytest.fixture(autouse=True)
def _clear_topup_throttle():
    svc_mod._price_topup_attempted.clear()
    yield
    svc_mod._price_topup_attempted.clear()


def _company(symbol="DPG") -> Company:
    return Company(id=7, symbol=symbol, name=symbol, exchange="HOSE", is_active=True, is_tradeable=True)


def _price(d: date) -> StockPrice:
    return StockPrice(id=1, company_id=7, date=d, open=1.0, high=1.0, low=1.0, close=1.0, volume=1)


def _bars(start: date, end: date) -> list:
    days = (end - start).days
    return [_price(start + timedelta(days=i)) for i in range(days + 1)
            if (start + timedelta(days=i)).weekday() < 5]


def _service(stored, refreshed=None) -> StockService:
    repo = MagicMock()
    repo.get_company_by_symbol = AsyncMock(return_value=_company())
    # Newest first, as the repository returns them.
    reads = [sorted(stored, key=lambda p: p.date, reverse=True)]
    if refreshed is not None:
        reads.append(sorted(refreshed, key=lambda p: p.date, reverse=True))
    repo.get_historical_prices = AsyncMock(side_effect=reads)
    repo.session.rollback = AsyncMock()
    return StockService(repo)


# ---------------------------------------------------------------------------
# The market clock
# ---------------------------------------------------------------------------

def test_last_completed_session_is_today_after_close():
    assert last_completed_session(THU_AFTER_CLOSE) == date(2026, 10, 29)


def test_last_completed_session_is_yesterday_while_trading():
    assert last_completed_session(THU_IN_SESSION) == date(2026, 10, 28)


def test_last_completed_session_skips_the_weekend():
    assert last_completed_session(MON_MORNING) == date(2026, 10, 30)
    assert last_completed_session(SATURDAY) == date(2026, 10, 30)


def test_target_never_passes_the_requested_end():
    assert price_history_target(date(2026, 9, 30), THU_AFTER_CLOSE) == date(2026, 9, 30)


def test_target_on_a_weekend_end_is_the_friday_before():
    # A range ending Sunday is complete with Friday's bar.
    assert price_history_target(date(2026, 10, 25), THU_AFTER_CLOSE) == date(2026, 10, 23)


# ---------------------------------------------------------------------------
# get_historical_data — the top-up
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_stale_tail_is_fetched_and_served():
    stored = _bars(date(2026, 8, 3), date(2026, 9, 29))
    refreshed = _bars(date(2026, 8, 3), date(2026, 10, 30))
    svc = _service(stored, refreshed)

    with patch.object(svc_mod, "_utcnow", return_value=SATURDAY), \
         patch.object(svc, "fetch_and_save_historical_data", AsyncMock(return_value=23)) as fetch:
        out = await svc.get_historical_data("DPG", date(2026, 8, 1), date(2026, 10, 31))

    fetch.assert_awaited_once_with(symbol="DPG", start_date=date(2026, 9, 30), end_date=date(2026, 10, 30))
    assert out.data[-1].date == date(2026, 10, 30)
    assert out.count == len(refreshed)


@pytest.mark.asyncio
async def test_current_tail_does_not_call_the_vendor():
    svc = _service(_bars(date(2026, 8, 3), date(2026, 10, 30)))

    with patch.object(svc_mod, "_utcnow", return_value=SATURDAY), \
         patch.object(svc, "fetch_and_save_historical_data", AsyncMock()) as fetch:
        out = await svc.get_historical_data("DPG", date(2026, 8, 1), date(2026, 10, 31))

    fetch.assert_not_awaited()
    assert out.data[-1].date == date(2026, 10, 30)


@pytest.mark.asyncio
async def test_top_up_stops_at_the_last_closed_session():
    """In session, today's bar is still forming and must not be stored as a close."""
    svc = _service(_bars(date(2026, 10, 1), date(2026, 10, 27)), _bars(date(2026, 10, 1), date(2026, 10, 28)))

    with patch.object(svc_mod, "_utcnow", return_value=THU_IN_SESSION), \
         patch.object(svc, "fetch_and_save_historical_data", AsyncMock(return_value=1)) as fetch:
        await svc.get_historical_data("DPG", date(2026, 10, 1), date(2026, 10, 29))

    assert fetch.await_args.kwargs["end_date"] == date(2026, 10, 28)


@pytest.mark.asyncio
async def test_failed_top_up_serves_the_stored_rows():
    stored = _bars(date(2026, 8, 3), date(2026, 9, 29))
    svc = _service(stored)

    with patch.object(svc_mod, "_utcnow", return_value=SATURDAY), \
         patch.object(svc, "fetch_and_save_historical_data", AsyncMock(side_effect=RuntimeError("quota"))):
        out = await svc.get_historical_data("DPG", date(2026, 8, 1), date(2026, 10, 31))

    assert out.count == len(stored)
    assert out.data[-1].date == date(2026, 9, 29)
    svc.repository.session.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_empty_top_up_does_not_reread():
    """Nothing new (a holiday, a suspension): serve what is stored, one DB read."""
    stored = _bars(date(2026, 8, 3), date(2026, 9, 29))
    svc = _service(stored)

    with patch.object(svc_mod, "_utcnow", return_value=SATURDAY), \
         patch.object(svc, "fetch_and_save_historical_data", AsyncMock(return_value=0)):
        out = await svc.get_historical_data("DPG", date(2026, 8, 1), date(2026, 10, 31))

    assert svc.repository.get_historical_prices.await_count == 1
    assert out.count == len(stored)


@pytest.mark.asyncio
async def test_repeat_reads_within_the_interval_try_once():
    stored = _bars(date(2026, 8, 3), date(2026, 9, 29))
    fetch = AsyncMock(return_value=0)

    with patch.object(svc_mod, "_utcnow", return_value=SATURDAY):
        for _ in range(3):
            svc = _service(stored)
            with patch.object(svc, "fetch_and_save_historical_data", fetch):
                await svc.get_historical_data("DPG", date(2026, 8, 1), date(2026, 10, 31))
    assert fetch.await_count == 1

    later = SATURDAY + svc_mod.PRICE_TOPUP_MIN_INTERVAL + timedelta(seconds=1)
    with patch.object(svc_mod, "_utcnow", return_value=later):
        svc = _service(stored)
        with patch.object(svc, "fetch_and_save_historical_data", fetch):
            await svc.get_historical_data("DPG", date(2026, 8, 1), date(2026, 10, 31))
    assert fetch.await_count == 2


# ---------------------------------------------------------------------------
# Every stored write stops at the last closed session
# ---------------------------------------------------------------------------

def _recording_vnstock(svc: StockService):
    """Patch svc.vnstock with a fake whose history() records its window."""
    calls = []

    def history(start, end, **_):
        calls.append((start, end))
        return pd.DataFrame()

    fake = MagicMock()
    fake.stock.return_value.quote.history = history
    patcher = patch.object(type(svc), "vnstock", new_callable=lambda: property(lambda self: fake))
    return patcher, calls


def _fetch_service() -> StockService:
    repo = MagicMock()
    repo.get_company_by_symbol = AsyncMock(return_value=_company())
    repo.save_prices = AsyncMock()
    repo.update_company = AsyncMock()
    return StockService(repo)


@pytest.mark.asyncio
async def test_fetch_in_session_does_not_request_the_forming_bar():
    """Thu 10:00 ICT, asked for 'up to today': the stored window ends Wednesday."""
    svc = _fetch_service()
    patcher, calls = _recording_vnstock(svc)

    with patcher, patch.object(svc_mod, "_utcnow", return_value=THU_IN_SESSION):
        await svc.fetch_and_save_historical_data("DPG", date(2026, 10, 1), date(2026, 10, 29))

    assert calls == [("2026-10-01", "2026-10-28")]


@pytest.mark.asyncio
async def test_fetch_after_close_includes_today():
    svc = _fetch_service()
    patcher, calls = _recording_vnstock(svc)

    with patcher, patch.object(svc_mod, "_utcnow", return_value=THU_AFTER_CLOSE):
        await svc.fetch_and_save_historical_data("DPG", date(2026, 10, 1), date(2026, 10, 29))

    assert calls == [("2026-10-01", "2026-10-29")]


@pytest.mark.asyncio
async def test_fetch_with_nothing_closed_yet_skips_the_vendor():
    """Asked only for today, in session: there is no closed bar to store."""
    svc = _fetch_service()
    patcher, calls = _recording_vnstock(svc)

    with patcher, patch.object(svc_mod, "_utcnow", return_value=THU_IN_SESSION):
        n = await svc.fetch_and_save_historical_data("DPG", date(2026, 10, 29), date(2026, 10, 29))

    assert n == 0
    assert calls == []
    svc.repository.save_prices.assert_not_awaited()


@pytest.mark.asyncio
async def test_index_sync_in_session_stops_at_yesterday():
    svc = StockService(MagicMock())
    patcher, calls = _recording_vnstock(svc)

    with patcher, patch.object(svc_mod, "_utcnow", return_value=THU_IN_SESSION):
        await svc.sync_market_indices(days=7)

    assert calls and all(end == "2026-10-28" for _, end in calls)
