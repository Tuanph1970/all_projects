"""s1_universe — liquidity filter helper tests.

Pre-screens watchlist tickers for tradeable liquidity (avg daily traded value
and volume) before the decision pipeline runs.  The helper is causal: it reads
only the most recent ``lookback`` bars.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Dict, List

import pytest

from app.services.signal.base import OHLCVBar
from app.services.universe.liquidity import (
    LiquidityResult,
    assess_liquidity,
    screen_watchlist,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _bar(i: int, close: float, volume: int) -> OHLCVBar:
    d = date(2023, 1, 2) + timedelta(days=i)
    return OHLCVBar(date=d, open=close, high=close, low=close, close=close, volume=volume)


def _series(closes_volumes: List[tuple]) -> List[OHLCVBar]:
    return [_bar(i, c, v) for i, (c, v) in enumerate(closes_volumes)]


# ---------------------------------------------------------------------------
# assess_liquidity — pure helper
# ---------------------------------------------------------------------------

def test_empty_series_fails():
    res = assess_liquidity([], ticker="X", lookback=20, min_avg_value=1, min_avg_volume=1)
    assert res.passed is False
    assert res.lookback == 0
    assert "no bars" in res.reason


def test_insufficient_history_fails_conservatively():
    bars = _series([(100.0, 10_000)] * 5)  # only 5 bars, need 20
    res = assess_liquidity(bars, ticker="X", lookback=20, min_avg_value=0, min_avg_volume=0)
    assert res.passed is False
    assert "insufficient history" in res.reason


def test_liquid_series_passes():
    bars = _series([(100.0, 50_000)] * 20)  # value = 5,000,000 each
    res = assess_liquidity(bars, ticker="VCB", lookback=20,
                           min_avg_value=1_000_000, min_avg_volume=10_000)
    assert res.passed is True
    assert res.avg_daily_value == pytest.approx(5_000_000)
    assert res.avg_daily_volume == pytest.approx(50_000)


def test_fails_on_low_value():
    bars = _series([(1.0, 1_000)] * 20)  # value = 1,000 each
    res = assess_liquidity(bars, ticker="X", lookback=20,
                           min_avg_value=1_000_000, min_avg_volume=0)
    assert res.passed is False
    assert "value" in res.reason


def test_fails_on_low_volume():
    bars = _series([(100.0, 100)] * 20)  # high price, tiny volume
    res = assess_liquidity(bars, ticker="X", lookback=20,
                           min_avg_value=0, min_avg_volume=10_000)
    assert res.passed is False
    assert "volume" in res.reason


def test_uses_only_recent_lookback_window():
    # 20 illiquid early bars + 20 liquid recent bars; lookback=20 must see only recent.
    illiquid = [(1.0, 100)] * 20
    liquid = [(100.0, 50_000)] * 20
    bars = _series(illiquid + liquid)
    res = assess_liquidity(bars, ticker="X", lookback=20,
                           min_avg_value=1_000_000, min_avg_volume=10_000)
    assert res.passed is True
    assert res.avg_daily_volume == pytest.approx(50_000)
    assert res.lookback == 20


def test_recent_illiquidity_fails_even_with_liquid_past():
    liquid_past = [(100.0, 50_000)] * 20
    illiquid_recent = [(1.0, 100)] * 20
    bars = _series(liquid_past + illiquid_recent)
    res = assess_liquidity(bars, ticker="X", lookback=20,
                           min_avg_value=1_000_000, min_avg_volume=10_000)
    assert res.passed is False


# ---------------------------------------------------------------------------
# screen_watchlist — async integration seam (mockable client)
# ---------------------------------------------------------------------------

class _FakeClient:
    def __init__(self, data: Dict[str, List[Dict[str, Any]]]):
        self._data = data
        self.calls: List[str] = []

    async def fetch_ohlcv(self, symbol: str, days: int = 300, end_date=None):
        self.calls.append(symbol)
        return self._data.get(symbol, [])


def _raw(closes_volumes: List[tuple]) -> List[Dict[str, Any]]:
    return [
        {"date": str(date(2023, 1, 2) + timedelta(days=i)), "close": c, "volume": v}
        for i, (c, v) in enumerate(closes_volumes)
    ]


async def test_screen_watchlist_partitions_liquid_and_illiquid():
    client = _FakeClient({
        "VCB": _raw([(100.0, 50_000)] * 25),   # liquid
        "TINY": _raw([(1.0, 100)] * 25),        # illiquid
    })
    results = await screen_watchlist(
        client, ["VCB", "TINY"],
        lookback=20, min_avg_value=1_000_000, min_avg_volume=10_000,
    )
    assert results["VCB"].passed is True
    assert results["TINY"].passed is False
    assert set(client.calls) == {"VCB", "TINY"}


async def test_screen_watchlist_handles_missing_data():
    client = _FakeClient({})  # no data for any ticker
    results = await screen_watchlist(
        client, ["GHOST"], lookback=20, min_avg_value=1, min_avg_volume=1,
    )
    assert results["GHOST"].passed is False
    assert "no bars" in results["GHOST"].reason


# ---------------------------------------------------------------------------
# Scheduler wiring — illiquid tickers are skipped before the pipeline runs
# ---------------------------------------------------------------------------

class _Entry:
    def __init__(self, ticker: str):
        self.ticker = ticker
        self.active = True


def _fake_session_factory(entries):
    """Return a callable producing an async-CM session whose query yields entries."""
    from contextlib import asynccontextmanager
    from unittest.mock import AsyncMock, MagicMock

    scalars = MagicMock()
    scalars.all.return_value = entries
    exec_result = MagicMock()
    exec_result.scalars.return_value = scalars
    session = MagicMock()
    session.execute = AsyncMock(return_value=exec_result)

    @asynccontextmanager
    async def factory():
        yield session

    return factory


async def test_scheduler_skips_illiquid_tickers(monkeypatch):
    from unittest.mock import AsyncMock
    import app.services.scheduler as sched

    entries = [_Entry("VCB"), _Entry("TINY")]

    monkeypatch.setattr(sched, "async_session_factory", _fake_session_factory(entries))
    monkeypatch.setattr(sched, "get_market_client", lambda: object())

    # Enable the filter and stub the screen so VCB passes, TINY fails.
    settings = sched.get_settings()
    monkeypatch.setattr(settings, "MIN_AVG_DAILY_VALUE", 1_000_000.0, raising=False)
    monkeypatch.setattr(settings, "MIN_AVG_DAILY_VOLUME", 10_000.0, raising=False)

    async def fake_screen(client, tickers, **kwargs):
        return {
            "VCB": LiquidityResult("VCB", 5_000_000, 50_000, 20, True, "ok"),
            "TINY": LiquidityResult("TINY", 100, 100, 20, False, "avg volume too low"),
        }

    monkeypatch.setattr(sched, "screen_watchlist", fake_screen)

    ran = []
    monkeypatch.setattr(sched, "run_recommendation", AsyncMock(
        side_effect=lambda **kw: ran.append(kw["ticker"]) or _Rec()
    ))

    await sched.run_for_user(user_id=1, bar_date=date(2023, 6, 1))

    assert ran == ["VCB"]  # TINY was filtered out before the pipeline


class _Rec:
    action = "HOLD"
    regime = "RANGE"
    confidence = 0.5
    stop_price = None
    target_price = None
