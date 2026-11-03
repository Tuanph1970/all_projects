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


# ---------------------------------------------------------------------------
# The nightly sweep — #119's cause, not its symptom
# ---------------------------------------------------------------------------

def _sweep_svc(symbols, *, total=None, repair=None):
    """A service whose universe is `symbols` -> {symbol: closes}."""
    svc = StockService(AsyncMock())
    repo = AsyncMock()
    companies = [SimpleNamespace(id=i, symbol=s) for i, s in enumerate(symbols, 1)]
    repo.get_all_companies = AsyncMock(
        return_value=(companies, total if total is not None else len(companies)))

    def _hist(company_id, *a, **kw):
        sym = symbols[company_id - 1]
        return _rows(symbols[sym] if isinstance(symbols, dict) else CLEAN)

    by_id = {c.id: symbols[c.symbol] for c in companies} if isinstance(symbols, dict) else {}

    async def hist(company_id, start=None, end=None, limit=None):
        return _rows(by_id.get(company_id, CLEAN))

    repo.get_historical_prices = AsyncMock(side_effect=hist)
    repo.session = MagicMock()
    repo.session.rollback = AsyncMock()
    svc.repository = repo
    svc.repair_price_seams = AsyncMock(
        return_value=repair if repair is not None
        else {"repaired": True, "bars_restated": 1408, "seams": []})
    return svc


def _recent_rows(closes):
    """Rows ending TODAY, so a seam in them falls inside the recency window."""
    from datetime import date as _d, timedelta as _td
    start = _d.today() - _td(days=len(closes) - 1)
    return [SimpleNamespace(date=start + _td(days=i), close=c)
            for i, c in enumerate(closes)]


@pytest.mark.asyncio
async def test_a_clean_universe_spends_no_vendor_call():
    """The property that makes a nightly sweep affordable.

    Detection reads stored closes only. Historically there were four seams in
    five years, so almost every night finds nothing and must therefore cost
    nothing — otherwise the sweep competes with the price refresh for quota.
    """
    svc = _sweep_svc({"AAA": CLEAN, "BBB": CLEAN, "CCC": CLEAN})
    rep = await svc.scan_and_repair_seams()
    assert rep["scanned"] == 3
    assert rep["with_seams"] == 0
    svc.repair_price_seams.assert_not_awaited()


@pytest.mark.asyncio
async def test_a_fresh_seam_is_repaired():
    svc = _sweep_svc({"AAA": CLEAN, "TCB": SEAMED})
    svc.repository.get_historical_prices = AsyncMock(
        side_effect=lambda cid, *a, **k: _recent_rows(SEAMED if cid == 2 else CLEAN))
    rep = await svc.scan_and_repair_seams()
    assert rep["with_seams"] == 1
    assert [e["symbol"] for e in rep["repaired"]] == ["TCB"]
    svc.repair_price_seams.assert_awaited_once_with("TCB")


@pytest.mark.asyncio
async def test_an_old_seam_is_left_alone_so_the_sweep_cannot_loop():
    """THE LOOP GUARD, and the reason the sweep is safe unattended.

    A GENUINE seam — one the provider itself never adjusted — survives a
    re-pull. With no memory and no date bound, the sweep would re-pull that
    symbol's whole history every single night for ever, burning ~1,400 bars of
    quota nightly to achieve nothing.
    """
    svc = _sweep_svc({"TCB": SEAMED})          # _rows() dates start 2026-01-01
    rep = await svc.scan_and_repair_seams(recent_days=30)
    assert rep["with_seams"] == 1
    assert rep["repaired"] == []
    assert [e["symbol"] for e in rep["skipped_old"]] == ["TCB"]
    svc.repair_price_seams.assert_not_awaited()


@pytest.mark.asyncio
async def test_the_recency_window_is_read_and_not_baked_in():
    """Non-vacuity for the test above: the same seam IS repaired when the
    window is wide enough to include it, so the skip is the window and not a
    broken scan."""
    svc = _sweep_svc({"TCB": SEAMED})
    rep = await svc.scan_and_repair_seams(recent_days=100_000)
    assert [e["symbol"] for e in rep["repaired"]] == ["TCB"]


@pytest.mark.asyncio
async def test_repairs_are_capped_per_run():
    """One repair re-pulls ~1,400 bars. Without a cap, a bad night across many
    symbols would eat the quota the price refresh needs."""
    svc = _sweep_svc({s: SEAMED for s in ("AAA", "BBB", "CCC", "DDD", "EEE")})
    svc.repository.get_historical_prices = AsyncMock(
        side_effect=lambda cid, *a, **k: _recent_rows(SEAMED))
    rep = await svc.scan_and_repair_seams(max_repairs=2)
    assert len(rep["repaired"]) == 2
    assert len(rep["skipped_cap"]) == 3
    assert svc.repair_price_seams.await_count == 2


@pytest.mark.asyncio
async def test_a_failed_repair_is_recorded_as_failed_not_repaired():
    svc = _sweep_svc(
        {"TCB": SEAMED},
        repair={"repaired": False, "reason": "re-fetch failed: quota", "seams": [{}]})
    svc.repository.get_historical_prices = AsyncMock(
        side_effect=lambda cid, *a, **k: _recent_rows(SEAMED))
    rep = await svc.scan_and_repair_seams()
    assert rep["repaired"] == []
    assert [e["symbol"] for e in rep["failed"]] == ["TCB"]
    assert "quota" in rep["failed"][0]["reason"]


@pytest.mark.asyncio
async def test_a_failed_repair_still_counts_against_the_cap():
    """Otherwise a symbol that cannot be fixed would be retried until the cap
    was reached by successes alone, spending calls on a known-hopeless case."""
    svc = _sweep_svc(
        {s: SEAMED for s in ("AAA", "BBB", "CCC")},
        repair={"repaired": False, "reason": "nope", "seams": [{}]})
    svc.repository.get_historical_prices = AsyncMock(
        side_effect=lambda cid, *a, **k: _recent_rows(SEAMED))
    rep = await svc.scan_and_repair_seams(max_repairs=1)
    assert len(rep["failed"]) == 1
    assert svc.repair_price_seams.await_count == 1


@pytest.mark.asyncio
async def test_the_whole_universe_is_listed_not_the_first_hundred():
    """get_all_companies defaults to limit=100 and returns a TUPLE.

    Both are silent: iterating the bare result walks [list, int] and treats the
    list as one company, and the default limit truncates the universe without a
    word once it grows past 100 — the same shape as get_historical_prices'
    1000-row default, which would have hidden the 2021 seams.
    """
    svc = _sweep_svc({"AAA": CLEAN})
    await svc.scan_and_repair_seams()
    _, kwargs = svc.repository.get_all_companies.await_args
    assert kwargs.get("limit", 0) >= 10_000


@pytest.mark.asyncio
async def test_a_truncated_universe_is_reported_rather_than_hidden():
    svc = _sweep_svc({"AAA": CLEAN}, total=5000)
    rep = await svc.scan_and_repair_seams()
    assert rep["universe"] == 5000


@pytest.mark.asyncio
async def test_dry_run_scans_without_repairing():
    svc = _sweep_svc({"TCB": SEAMED})
    svc.repository.get_historical_prices = AsyncMock(
        side_effect=lambda cid, *a, **k: _recent_rows(SEAMED))
    rep = await svc.scan_and_repair_seams(dry_run=True)
    assert rep["with_seams"] == 1
    assert rep["repaired"] == []
    svc.repair_price_seams.assert_not_awaited()


@pytest.mark.asyncio
async def test_one_bad_symbol_does_not_stop_the_sweep():
    svc = _sweep_svc({"AAA": CLEAN, "BAD": CLEAN, "CCC": CLEAN})
    calls = {"n": 0}

    async def flaky(cid, start=None, end=None, limit=None):
        calls["n"] += 1
        if cid == 2:
            raise RuntimeError("table locked")
        return _rows(CLEAN)

    svc.repository.get_historical_prices = AsyncMock(side_effect=flaky)
    rep = await svc.scan_and_repair_seams()
    assert rep["errors"] == 1
    assert rep["scanned"] == 2, "the sweep stopped at the first failure"


@pytest.mark.asyncio
async def test_an_unlistable_universe_returns_a_report_not_an_exception():
    svc = _sweep_svc({"AAA": CLEAN})
    svc.repository.get_all_companies = AsyncMock(side_effect=RuntimeError("db down"))
    rep = await svc.scan_and_repair_seams()
    assert rep["scanned"] == 0 and rep["repaired"] == []


@pytest.mark.asyncio
async def test_symbols_with_too_little_history_are_skipped_silently():
    svc = _sweep_svc({"NEW": CLEAN})
    svc.repository.get_historical_prices = AsyncMock(
        side_effect=lambda cid, *a, **k: _rows([22.0]))
    rep = await svc.scan_and_repair_seams()
    assert rep["scanned"] == 0 and rep["errors"] == 0


# ---------------------------------------------------------------------------
# The wiring: a sweep nothing calls protects nothing
# ---------------------------------------------------------------------------

def test_the_nightly_cycle_actually_calls_the_sweep():
    """#117 shipped an EventBus binding that never delivered a message because
    both halves existed and disagreed. A flag-gated step that is never invoked
    is the same class of bug, so the call site is asserted directly."""
    import inspect
    import app.main as main
    src = inspect.getsource(main._run_sync)
    assert "scan_and_repair_seams" in src
    assert "ENABLE_NIGHTLY_SEAM_SCAN" in src


def test_the_sweep_runs_after_the_price_refresh_that_creates_seams():
    """ORDER IS THE POINT, not a detail.

    `refresh_all_prices` is what APPENDS new bars, so it is also what opens a
    seam when the provider has restated history in the meantime. Sweeping
    before it would find yesterday's state and miss the seam the refresh just
    introduced, delaying the repair by a full day.
    """
    import inspect
    import app.main as main
    src = inspect.getsource(main._run_sync)
    assert src.index("refresh_all_prices") < src.index("scan_and_repair_seams")


def test_the_flags_have_safe_defaults():
    from app.config import get_settings
    s = get_settings()
    assert s.ENABLE_NIGHTLY_SEAM_SCAN is True
    # Bounded: a repair re-pulls a whole history, so the cap must be small.
    assert 1 <= s.SEAM_SCAN_MAX_REPAIRS <= 10
    # And the loop guard must be a real window, not "forever".
    assert 1 <= s.SEAM_SCAN_RECENT_DAYS <= 365
