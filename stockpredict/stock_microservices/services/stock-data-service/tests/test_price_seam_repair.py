"""Backlog #119 — repairing a seam by re-pulling, not by adjusting.

The diagnosis these tests encode, because it is the whole reason the repair has
this shape: stored TCB fell -33.8% overnight, which no VN board permits, but
vnstock returns a CONTINUOUS series across that date. The provider restates a
symbol's entire history on a share-count event; `_top_up_prices` appends only
bars after the last stored date, so the restated rows never land and the two
scales meet at a seam.

Hence: re-fetch the full history and let the upsert restate every row. Never
compute a local adjustment factor -- that would be a second definition of
"adjusted" in the same database, and the next re-pull would overwrite it.
"""
from __future__ import annotations

from datetime import date, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.stock_service import StockService


def _rows(closes, start=date(2026, 1, 1)):
    return [SimpleNamespace(date=start + timedelta(days=i), close=c)
            for i, c in enumerate(closes)]


def _svc(stored, after=None, company=SimpleNamespace(id=7)):
    """A service whose repository returns `stored`, then `after` post-refetch."""
    svc = StockService(AsyncMock())
    repo = AsyncMock()
    repo.get_company_by_symbol = AsyncMock(return_value=company)
    seq = [stored] if after is None else [stored, after]
    repo.get_historical_prices = AsyncMock(side_effect=seq + [seq[-1]] * 6)
    # MagicMock, not AsyncMock: expire_all() is SYNCHRONOUS on AsyncSession,
    # and an AsyncMock would turn a bug (never calling it) into a passing test
    # that merely leaves a coroutine un-awaited.
    repo.session = MagicMock()
    repo.session.rollback = AsyncMock()
    svc.repository = repo
    svc.fetch_and_save_historical_data = AsyncMock(return_value=len(stored))
    return svc


CLEAN = [22.80, 22.53, 22.37, 22.33, 22.35, 21.60, 21.40]
SEAMED = [34.20, 33.80, 22.37, 22.33, 22.35, 21.60, 21.40]


@pytest.mark.asyncio
async def test_a_seamed_history_is_re_fetched_and_reported_repaired():
    svc = _svc(_rows(SEAMED), after=_rows(CLEAN))
    out = await svc.repair_price_seams("TCB")
    assert out["repaired"] is True
    assert out["seams"] == []
    assert len(out["seams_before"]) == 1
    assert out["seams_before"][0]["move_pct"] == pytest.approx(-33.81, abs=0.05)
    svc.fetch_and_save_historical_data.assert_awaited_once()


@pytest.mark.asyncio
async def test_a_clean_history_is_not_re_fetched_at_all():
    """The quota matters: vnstock allows 20 requests a minute. Re-pulling a
    symbol that is already continuous spends that budget for nothing."""
    svc = _svc(_rows(CLEAN))
    out = await svc.repair_price_seams("TCB")
    assert out["repaired"] is False
    assert out["reason"] == "no seams found"
    svc.fetch_and_save_historical_data.assert_not_awaited()


@pytest.mark.asyncio
async def test_a_refetch_that_does_not_close_the_seam_is_reported_as_failed():
    """THE MOST IMPORTANT TEST HERE.

    If the provider has NOT restated the history -- a real unadjusted feed, as
    opposed to our ingestion artifact -- the re-fetch changes nothing and the
    seam survives. Reporting that as "repaired" would hide a genuine data fault
    behind a successful-looking operation, and #118's narrator would then stop
    warning about it.
    """
    svc = _svc(_rows(SEAMED), after=_rows(SEAMED))
    out = await svc.repair_price_seams("TCB")
    assert out["repaired"] is False
    assert len(out["seams"]) == 1, "the surviving seam must stay visible"


@pytest.mark.asyncio
async def test_dry_run_detects_without_writing_anything():
    svc = _svc(_rows(SEAMED))
    out = await svc.repair_price_seams("TCB", dry_run=True)
    assert out["repaired"] is False
    assert out["reason"] == "dry run"
    assert len(out["seams"]) == 1
    svc.fetch_and_save_historical_data.assert_not_awaited()


@pytest.mark.asyncio
async def test_the_whole_stored_history_is_scanned_not_the_first_thousand_rows():
    """get_historical_prices defaults to limit=1000 and TCB holds 1345 bars.

    The 2021 HDB/TPB/VPB seams live in the OLDEST part of the history, so a
    default-limit call would scan past them and report a clean series. The limit
    must be passed explicitly and large.
    """
    svc = _svc(_rows(SEAMED))
    await svc.repair_price_seams("TCB", dry_run=True)
    _, kwargs = svc.repository.get_historical_prices.await_args
    assert kwargs.get("limit", 0) >= 10_000, (
        f"history scan is limited to {kwargs.get('limit')} rows, which can hide "
        f"a seam in older history")


@pytest.mark.asyncio
async def test_the_refetch_starts_at_the_oldest_stored_bar():
    """Re-fetching only recent bars would restate only recent rows and leave
    the seam exactly where it is."""
    rows = _rows(SEAMED)
    svc = _svc(rows, after=_rows(CLEAN))
    await svc.repair_price_seams("TCB")
    _, kwargs = svc.fetch_and_save_historical_data.await_args
    assert kwargs["start_date"] == rows[0].date


@pytest.mark.asyncio
async def test_an_unknown_symbol_is_an_error_not_a_crash():
    svc = _svc(_rows(CLEAN), company=None)
    out = await svc.repair_price_seams("NOPE")
    assert "error" in out
    svc.fetch_and_save_historical_data.assert_not_awaited()


@pytest.mark.asyncio
async def test_a_failed_refetch_rolls_back_and_reports_rather_than_raising():
    svc = _svc(_rows(SEAMED))
    svc.fetch_and_save_historical_data = AsyncMock(side_effect=RuntimeError("quota"))
    out = await svc.repair_price_seams("TCB")
    assert out["repaired"] is False
    assert "quota" in out["reason"]
    svc.repository.session.rollback.assert_awaited()


@pytest.mark.asyncio
async def test_too_little_history_is_handled():
    svc = _svc(_rows([22.0]))
    out = await svc.repair_price_seams("TCB")
    assert out["repaired"] is False
    svc.fetch_and_save_historical_data.assert_not_awaited()


@pytest.mark.asyncio
async def test_rows_are_sorted_before_scanning():
    """get_historical_prices returns DESC. Scanning in that order turns every
    ordinary two-day move into its own mirror image and a real seam into a
    +51% rise, so the sort is load-bearing rather than cosmetic."""
    rows = list(reversed(_rows(SEAMED)))      # newest first, as the repo returns
    svc = _svc(rows, after=_rows(CLEAN))
    out = await svc.repair_price_seams("TCB")
    assert len(out["seams_before"]) == 1
    assert out["seams_before"][0]["move_pct"] < 0, (
        "the seam was read backwards, so the rows were not sorted ascending")


@pytest.mark.asyncio
async def test_the_verification_read_cannot_see_stale_session_state():
    """The bug this repair shipped with, and it faked a seam rather than hiding one.

    The session factory sets expire_on_commit=False, so after the upsert the
    identity map still holds the pre-repair rows. The first live run therefore
    reported all four symbols UNREPAIRED while the database was already
    correct -- and worse, because the re-fetch also inserted bars older than
    anything stored, the second read mixed fresh rows at the new scale with
    cached rows at the old one and invented a +50.31% seam at 2021-06-14 that
    existed only in that session's memory.

    What saved it was the honest-reporting rule: `repaired` is computed from a
    RE-READ rather than assumed, so a broken read showed up as a failed repair
    instead of a silent success.
    """
    svc = _svc(_rows(SEAMED), after=_rows(CLEAN))
    await svc.repair_price_seams("TCB")
    svc.repository.session.expire_all.assert_called_once()


@pytest.mark.asyncio
async def test_nothing_is_expired_when_no_repair_was_attempted():
    """expire_all() is only meaningful after a write. Calling it on the clean
    path would mean the function writes nothing but still discards cached state
    for every other caller sharing the session."""
    svc = _svc(_rows(CLEAN))
    await svc.repair_price_seams("TCB")
    svc.repository.session.expire_all.assert_not_called()
