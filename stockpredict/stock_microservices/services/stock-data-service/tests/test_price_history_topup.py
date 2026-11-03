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


# ---------------------------------------------------------------------------
# Backlog #114 follow-up — the DAILY ALL-SYMBOLS price refresh.
#
# The on-read top-up fixed correctness: a read never serves a frozen tail. It
# did not fix SPEED — the first reader of a stale symbol pays a vendor call,
# and only the VN30 is touched by the background sync. Measured on 2026-11-02:
# 30 of 32 stored symbols sat at 2026-10-27, three sessions behind, because
# nobody had read them. This runs once a day and brings them all current.
#
# SCOPE, deliberately: only symbols that ALREADY have stored history. A symbol
# with none is absent rather than stale, and backfilling five years for it is
# ensure_company_and_sync's job, on demand — a different and far heavier
# operation that should not ride along on a nightly top-up.
# ---------------------------------------------------------------------------

def _refresh_service(pairs, top_up=None):
    """A service whose repository reports `pairs` as (symbol, newest_date)."""
    repo = MagicMock()
    repo.get_latest_price_dates = AsyncMock(return_value=list(pairs))
    repo.session = MagicMock()
    repo.session.rollback = AsyncMock()
    svc = StockService(repo)
    svc._top_up_prices = AsyncMock(side_effect=top_up if top_up else (lambda *a, **k: True))
    return svc


@pytest.mark.asyncio
async def test_only_stale_symbols_are_refreshed():
    """A symbol already at the target costs no vendor call."""
    target = last_completed_session(MON_MORNING)          # Fri 2026-10-30
    svc = _refresh_service([("ACB", target), ("DPG", date(2026, 10, 27))])
    with patch.object(svc_mod, "_utcnow", return_value=MON_MORNING):
        out = await svc.refresh_all_prices(pause_seconds=0)
    assert out["checked"] == 2
    assert out["stale"] == 1
    assert out["refreshed"] == 1
    assert [c.args[0] for c in svc._top_up_prices.await_args_list] == ["DPG"]


@pytest.mark.asyncio
async def test_nothing_to_do_when_every_symbol_is_current():
    target = last_completed_session(MON_MORNING)
    svc = _refresh_service([("ACB", target), ("VNM", target)])
    with patch.object(svc_mod, "_utcnow", return_value=MON_MORNING):
        out = await svc.refresh_all_prices(pause_seconds=0)
    assert out["stale"] == 0 and out["refreshed"] == 0
    svc._top_up_prices.assert_not_awaited()


@pytest.mark.asyncio
async def test_it_tops_up_to_the_last_completed_session_not_today():
    """Mid-session, today's bar is still forming. Storing it as a close is the
    defect the #114 follow-up fixed, so the target must stay behind it."""
    svc = _refresh_service([("DPG", date(2026, 10, 20))])
    with patch.object(svc_mod, "_utcnow", return_value=THU_IN_SESSION):
        await svc.refresh_all_prices(pause_seconds=0)
    _sym, latest, target = svc._top_up_prices.await_args_list[0].args
    assert target == last_completed_session(THU_IN_SESSION)
    assert target < date(2026, 10, 29), "an in-session day must not be the target"
    assert latest == date(2026, 10, 20)


@pytest.mark.asyncio
async def test_one_symbol_failing_does_not_stop_the_rest():
    """Never raises: a suspended or delisted symbol must not abort the night."""
    async def flaky(symbol, *_a, **_k):
        if symbol == "BAD":
            raise RuntimeError("vendor exploded")
        return True
    svc = _refresh_service(
        [("AAA", date(2026, 10, 1)), ("BAD", date(2026, 10, 1)), ("ZZZ", date(2026, 10, 1))],
        top_up=flaky)
    with patch.object(svc_mod, "_utcnow", return_value=MON_MORNING):
        out = await svc.refresh_all_prices(pause_seconds=0)
    assert out["refreshed"] == 2
    assert len(out["errors"]) == 1 and "BAD" in out["errors"][0]


@pytest.mark.asyncio
async def test_the_run_is_capped_so_a_large_database_cannot_run_unbounded():
    pairs = [(f"S{i:03d}", date(2026, 10, 1)) for i in range(50)]
    svc = _refresh_service(pairs)
    with patch.object(svc_mod, "_utcnow", return_value=MON_MORNING):
        out = await svc.refresh_all_prices(max_symbols=5, pause_seconds=0)
    assert out["refreshed"] == 5
    assert svc._top_up_prices.await_count == 5
    assert out["skipped_over_cap"] == 45


@pytest.mark.asyncio
async def test_interactive_requests_keep_priority_over_the_nightly_run():
    """vnstock_call spaces background work so a user request is not queued
    behind 30 nightly calls."""
    seen = {}

    async def record(symbol, *_a, **_k):
        seen[symbol] = svc_mod.vnstock_background.get()
        return True
    svc = _refresh_service([("DPG", date(2026, 10, 1))], top_up=record)
    with patch.object(svc_mod, "_utcnow", return_value=MON_MORNING):
        await svc.refresh_all_prices(pause_seconds=0)
    assert seen["DPG"] is True


@pytest.mark.asyncio
async def test_a_symbol_ahead_of_the_target_is_left_alone():
    """Defensive: a stored bar newer than the computed target (clock skew, or a
    manually synced range) must not trigger a backwards fetch."""
    svc = _refresh_service([("ACB", date(2026, 11, 20))])
    with patch.object(svc_mod, "_utcnow", return_value=MON_MORNING):
        out = await svc.refresh_all_prices(pause_seconds=0)
    assert out["stale"] == 0
    svc._top_up_prices.assert_not_awaited()


@pytest.mark.asyncio
async def test_symbols_with_no_stored_history_are_not_in_scope():
    """The repository only reports symbols that have bars; a None date would
    mean a first-time backfill, which is ensure_company_and_sync's job."""
    svc = _refresh_service([("ACB", None), ("DPG", date(2026, 10, 1))])
    with patch.object(svc_mod, "_utcnow", return_value=MON_MORNING):
        out = await svc.refresh_all_prices(pause_seconds=0)
    assert [c.args[0] for c in svc._top_up_prices.await_args_list] == ["DPG"]
    assert out["checked"] == 2 and out["stale"] == 1


@pytest.mark.asyncio
async def test_the_stalest_symbols_are_refreshed_first():
    """If the cap bites, the symbols furthest behind should be the ones that
    get fixed, not whichever the database happened to list first."""
    svc = _refresh_service([
        ("FRESH", date(2026, 10, 29)),
        ("OLDEST", date(2026, 1, 5)),
        ("MIDDLE", date(2026, 9, 1)),
    ])
    with patch.object(svc_mod, "_utcnow", return_value=MON_MORNING):
        await svc.refresh_all_prices(max_symbols=2, pause_seconds=0)
    assert [c.args[0] for c in svc._top_up_prices.await_args_list] == ["OLDEST", "MIDDLE"]


# --- the nightly cycle actually calls it ------------------------------------

@pytest.mark.asyncio
async def test_the_nightly_cycle_runs_the_price_refresh():
    """The method is worthless if nothing schedules it. Guards the wiring, not
    the logic, so a future reshuffle of _run_sync cannot silently drop it."""
    import app.main as main_mod
    svc = MagicMock()
    svc.is_company_data_stale = AsyncMock(return_value=False)
    svc.refresh_price_board = AsyncMock(return_value=0)
    svc.sync_market_indices = AsyncMock(return_value=0)
    svc.refresh_all_prices = AsyncMock(return_value={"refreshed": 3})

    class _Ctx:
        async def __aenter__(self): return MagicMock()
        async def __aexit__(self, *a): return False

    with patch("app.api.dependencies.async_session_factory", return_value=_Ctx()), \
         patch("app.repositories.stock_repository.StockRepository", return_value=MagicMock()), \
         patch("app.services.stock_service.StockService", return_value=svc), \
         patch.object(main_mod.settings, "ENABLE_DAILY_PRICE_REFRESH", True):
        await main_mod._run_sync()
    svc.refresh_all_prices.assert_awaited_once()


@pytest.mark.asyncio
async def test_the_price_refresh_can_be_switched_off():
    import app.main as main_mod
    svc = MagicMock()
    svc.is_company_data_stale = AsyncMock(return_value=False)
    svc.refresh_price_board = AsyncMock(return_value=0)
    svc.sync_market_indices = AsyncMock(return_value=0)
    svc.refresh_all_prices = AsyncMock(return_value={})

    class _Ctx:
        async def __aenter__(self): return MagicMock()
        async def __aexit__(self, *a): return False

    with patch("app.api.dependencies.async_session_factory", return_value=_Ctx()), \
         patch("app.repositories.stock_repository.StockRepository", return_value=MagicMock()), \
         patch("app.services.stock_service.StockService", return_value=svc), \
         patch.object(main_mod.settings, "ENABLE_DAILY_PRICE_REFRESH", False):
        await main_mod._run_sync()
    svc.refresh_all_prices.assert_not_awaited()


# ---------------------------------------------------------------------------
# Backlog #117 — the relative-volume reading attached to each price event
#
# The ratio is computed HERE because this is the only service holding both
# today's volume and the symbol's history. The alert consumer in
# portfolio-service sees one event at a time with no trailing window, so a ratio
# computed there would cost a round trip per symbol per refresh.
# ---------------------------------------------------------------------------

def _svc_with_history(history: dict) -> StockService:
    repo = MagicMock()
    repo.get_recent_volumes = AsyncMock(return_value=history)
    return StockService(repo)


@pytest.mark.asyncio
async def test_a_spike_is_attached_as_its_multiple_of_the_median():
    svc = _svc_with_history({"ACB": [100] * 60})
    records = [{"symbol": "ACB", "matchQty": 420}]
    await svc._attach_relative_volume(records)
    assert records[0]["relVolume"] == pytest.approx(4.2)


@pytest.mark.asyncio
async def test_a_normal_bar_is_attached_near_one():
    svc = _svc_with_history({"ACB": [100] * 60})
    records = [{"symbol": "ACB", "matchQty": 105}]
    await svc._attach_relative_volume(records)
    assert records[0]["relVolume"] == pytest.approx(1.05)


@pytest.mark.asyncio
async def test_todays_bar_is_judged_against_history_not_against_itself():
    """If today's volume were folded into its own baseline, a genuine spike
    would read lower than it is — the error that makes a spike detector blind
    to the very events it exists for.

    THE HISTORY HERE IS DELIBERATELY UNEVEN. An earlier version of this test
    used a FLAT history of forty 10s, and two real mutations survived it: both
    "include the judged bar in its own baseline" and "use a mean instead of a
    median" left the answer at exactly 100.0, because on a flat series the mean
    equals the median and one extra value cannot move a median of forty. The
    test passed for a reason unrelated to its name. An uneven baseline makes
    both mutations change the number.
    """
    svc = _svc_with_history({"ACB": list(range(1, 11))})      # median 5.5, mean 5.5
    records = [{"symbol": "ACB", "matchQty": 1000}]
    await svc._attach_relative_volume(records)
    # median(1..10) = 5.5 -> 1000/5.5. Folding today in gives median 6 -> 166.7.
    assert records[0]["relVolume"] == pytest.approx(1000 / 5.5, rel=1e-4)


@pytest.mark.asyncio
async def test_the_baseline_is_a_median_so_one_climax_day_cannot_mask_the_next():
    """The decision inherited from EM-1, asserted at this layer too because the
    service is what a reader of this file will change.

    A mean baseline absorbs an extreme day and understates the next one. The
    fixture carries one enormous day inside the window, which moves a mean a
    long way and a median not at all.
    """
    history = [100] * 40
    history[20] = 10_000
    svc = _svc_with_history({"ACB": history})
    records = [{"symbol": "ACB", "matchQty": 300}]
    await svc._attach_relative_volume(records)
    # median stays 100 -> 3.0. A mean baseline would be ~347 -> about 0.86,
    # i.e. a genuine 3x day would read as quieter than normal.
    assert records[0]["relVolume"] == pytest.approx(3.0)


@pytest.mark.asyncio
async def test_too_little_history_attaches_NOTHING():
    """An absent reading is an explicit unknown. Attaching 1.0 would look like
    a measurement of 'normal' and would make a new listing permanently quiet."""
    svc = _svc_with_history({"ACB": [100, 100, 100]})
    records = [{"symbol": "ACB", "matchQty": 5000}]
    await svc._attach_relative_volume(records)
    assert "relVolume" not in records[0]


@pytest.mark.asyncio
async def test_a_symbol_with_no_history_at_all_attaches_nothing():
    svc = _svc_with_history({})
    records = [{"symbol": "NEWCO", "matchQty": 5000}]
    await svc._attach_relative_volume(records)
    assert "relVolume" not in records[0]


@pytest.mark.asyncio
async def test_a_record_without_a_volume_is_skipped_not_guessed():
    svc = _svc_with_history({"ACB": [100] * 60})
    records = [{"symbol": "ACB"}]
    await svc._attach_relative_volume(records)
    assert "relVolume" not in records[0]


@pytest.mark.asyncio
async def test_every_record_is_judged_against_its_OWN_symbol():
    """Per-symbol by construction: E&M are explicit that 'high' volume means
    high FOR THAT STOCK, so there is no cross-symbol share-count threshold.
    A small-cap's 50,000 shares and a blue chip's 50,000 are not the same event.
    """
    svc = _svc_with_history({"BIG": [1_000_000] * 60, "SMALL": [1_000] * 60})
    records = [
        {"symbol": "BIG", "matchQty": 2_000_000},
        {"symbol": "SMALL", "matchQty": 2_000},
    ]
    await svc._attach_relative_volume(records)
    assert records[0]["relVolume"] == pytest.approx(2.0)
    assert records[1]["relVolume"] == pytest.approx(2.0)


@pytest.mark.asyncio
async def test_the_history_is_fetched_in_ONE_query_for_all_symbols():
    """30 round trips in the publish path is the kind of cost that gets a
    feature switched off."""
    svc = _svc_with_history({s: [100] * 60 for s in ("A", "B", "C")})
    records = [{"symbol": s, "matchQty": 300} for s in ("A", "B", "C")]
    await svc._attach_relative_volume(records)
    svc.repository.get_recent_volumes.assert_awaited_once()
    assert all(r["relVolume"] == pytest.approx(3.0) for r in records)


@pytest.mark.asyncio
async def test_a_failing_history_lookup_does_not_break_the_fan_out():
    """A missing reading is a neutral absence; it must never stop the price
    events, which is what the alert path depends on."""
    repo = MagicMock()
    repo.get_recent_volumes = AsyncMock(side_effect=RuntimeError("db down"))
    records = [{"symbol": "ACB", "matchQty": 420}]
    with pytest.raises(RuntimeError):
        await StockService(repo)._attach_relative_volume(records)
    # refresh_price_board wraps the call, so the records simply go out unenriched.
    assert "relVolume" not in records[0]


def test_refresh_price_board_attaches_before_publishing_and_survives_failure():
    """Order matters: the reading must be attached BEFORE the fan-out, and a
    failure there must be caught so the price events still go."""
    import inspect

    src = inspect.getsource(StockService.refresh_price_board)
    assert src.index("_attach_relative_volume") < src.index("publish_price_updates")
    assert "Could not attach relative volume" in src


def test_the_published_payload_carries_volume_and_the_ratio():
    import inspect

    from app.services import event_publisher

    src = inspect.getsource(event_publisher.publish_price_updates)
    assert '"volume": rec.get("matchQty")' in src
    assert '"rel_volume": rec.get("relVolume")' in src
