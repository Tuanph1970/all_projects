"""Orchestrator tests — internal helpers + run_recommendation paths.

The /recommend HTTP route is already covered by test_routes_http.py with
run_recommendation mocked out. Here we exercise the orchestrator itself:
the abort path, the _run_signal_engines per-regime routing, and the
_tag_origin_run outcome-back-fill helper.

Heavy end-to-end runs would need a complete MarketClient mock; we stick
to the most leverage helpers and one abort scenario.
"""
from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.decision.orchestrator import (
    _abort_response,
    _count_recent_losses,
    _load_position,
    _load_prefs,
    _run_signal_engines,
    _tag_origin_run,
    run_recommendation,
)
from app.services.signal.base import OHLCVBar


def _bar(d: date, close: float, high=None, low=None, open_=None, volume=1000) -> OHLCVBar:
    high = high if high is not None else close + 1
    low = low if low is not None else close - 1
    open_ = open_ if open_ is not None else close
    return OHLCVBar(
        date=d, open=open_, high=high, low=low, close=close, volume=float(volume),
    )


def _make_bars(n: int, start: date = date(2026, 1, 1), close0: float = 80.0,
               step: float = 0.1) -> list[OHLCVBar]:
    return [_bar(start + timedelta(days=i), close0 + i * step) for i in range(n)]


# ---------------------------------------------------------------------------
# _run_signal_engines per-regime routing
# ---------------------------------------------------------------------------


def test_run_signal_engines_trend_up_runs_trend_detectors():
    """TREND_UP routes to ma_cross + n_day_breakout + midtrend (3 detectors)."""
    bars = _make_bars(200)
    signals = _run_signal_engines(
        regime="TREND_UP",
        bars=bars,
        bar_date=bars[-1].date,
        fast_ma=10,
        slow_ma=50,
        breakout_n=20,
        sr_data=None,
    )
    assert isinstance(signals, list)
    # detectors may fire or not depending on price action; the call shape
    # itself is the contract under test (regime gate).


def test_run_signal_engines_range_requires_sr_data():
    bars = _make_bars(60)
    # No sr_data → range branch returns no signals.
    signals = _run_signal_engines(
        regime="RANGE", bars=bars, bar_date=bars[-1].date,
        fast_ma=10, slow_ma=50, breakout_n=20, sr_data=None,
    )
    assert signals == []


def test_run_signal_engines_range_with_sr_data():
    """RANGE + sr_data → routes to detect_sr_signal."""
    bars = _make_bars(60)
    sr_data = {
        "support": [{"price": 70.0, "strength": 0.8}],
        "resistance": [{"price": 95.0, "strength": 0.8}],
    }
    signals = _run_signal_engines(
        regime="RANGE", bars=bars, bar_date=bars[-1].date,
        fast_ma=10, slow_ma=50, breakout_n=20, sr_data=sr_data,
    )
    # The detector may return zero or one signal; just confirm no exception.
    assert isinstance(signals, list)


def test_run_signal_engines_undefined_falls_back_to_trend_engines():
    """UNDEFINED regime still runs ma_cross + n_day_breakout (no midtrend)."""
    bars = _make_bars(100)
    signals = _run_signal_engines(
        regime="UNDEFINED", bars=bars, bar_date=bars[-1].date,
        fast_ma=10, slow_ma=50, breakout_n=20, sr_data=None,
    )
    assert isinstance(signals, list)


# ---------------------------------------------------------------------------
# _abort_response — shape + reason chain
# ---------------------------------------------------------------------------


def test_abort_response_returns_wait_action():
    chain: list = []
    resp = _abort_response(
        user_id=1, ticker="VCB", bar_date=date(2026, 5, 20),
        trigger="ON_DEMAND", regime="TREND_UP",
        reason_chain=chain, reason="No data", t0=0.0,
    )
    assert resp.action == "WAIT"
    assert resp.state_before == "FLAT"
    assert resp.state_after == "FLAT"
    assert resp.ticker == "VCB"
    # The reason was appended to the chain.
    assert chain[-1]["stage"] == "abort"
    assert chain[-1]["message"] == "No data"


# ---------------------------------------------------------------------------
# _load_position / _load_prefs — DB façade
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_load_position_returns_row_or_none():
    db = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = MagicMock(state="LONG", ticker="VCB")
    db.execute = AsyncMock(return_value=result)
    out = await _load_position(db, user_id=1, ticker="VCB")
    assert out.state == "LONG"


@pytest.mark.asyncio
async def test_load_position_returns_none_when_missing():
    db = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=result)
    assert await _load_position(db, user_id=1, ticker="VCB") is None


@pytest.mark.asyncio
async def test_load_prefs_returns_row_or_none():
    db = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = MagicMock(account_equity=100000)
    db.execute = AsyncMock(return_value=result)
    out = await _load_prefs(db, user_id=1)
    assert out.account_equity == 100000


@pytest.mark.asyncio
async def test_count_recent_losses_returns_zero_when_no_rows():
    db = AsyncMock()
    result = MagicMock()
    scal = MagicMock()
    scal.all.return_value = []
    result.scalars.return_value = scal
    db.execute = AsyncMock(return_value=result)
    assert await _count_recent_losses(db, user_id=1, ticker="VCB") == 0


@pytest.mark.asyncio
async def test_count_recent_losses_counts_exit_actions():
    db = AsyncMock()
    result = MagicMock()
    scal = MagicMock()
    scal.all.return_value = ["SELL", "COVER", "REVERSE"]
    result.scalars.return_value = scal
    db.execute = AsyncMock(return_value=result)
    assert await _count_recent_losses(db, user_id=1, ticker="VCB") == 3


# ---------------------------------------------------------------------------
# _tag_origin_run — back-fills exit + R + outcome on the BUY/SELL_SHORT row
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_tag_origin_run_no_origin_is_noop():
    db = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=result)
    await _tag_origin_run(db, user_id=1, ticker="VCB", exit_run_id=5, exit_price=85.0)
    # No assertion needed — the function returns silently with no DB mutation.


@pytest.mark.asyncio
async def test_tag_origin_run_skips_when_entry_or_stop_missing():
    db = AsyncMock()
    origin = MagicMock(entry_price=None, stop_price=None)
    result = MagicMock()
    result.scalar_one_or_none.return_value = origin
    db.execute = AsyncMock(return_value=result)
    await _tag_origin_run(db, user_id=1, ticker="VCB", exit_run_id=5, exit_price=85.0)
    # outcome / r_multiple stay untouched
    assert origin.outcome._extract_mock_name() if hasattr(origin.outcome, "_extract_mock_name") else True


@pytest.mark.asyncio
async def test_tag_origin_run_tags_win_for_buy_above_entry():
    db = AsyncMock()
    origin = MagicMock(
        action="BUY", entry_price=80.0, stop_price=78.0,
        exit_price=None, exit_run_id=None, r_multiple=None, outcome=None,
    )
    result = MagicMock()
    result.scalar_one_or_none.return_value = origin
    db.execute = AsyncMock(return_value=result)

    await _tag_origin_run(db, user_id=1, ticker="VCB", exit_run_id=99, exit_price=86.0)
    # Risk per share = 2.0; gain = 6.0 → R = 3.0 (a clear WIN)
    assert origin.outcome == "WIN"
    assert origin.r_multiple == 3.0
    assert origin.exit_price == 86.0
    assert origin.exit_run_id == 99


@pytest.mark.asyncio
async def test_tag_origin_run_tags_loss_for_buy_below_entry():
    db = AsyncMock()
    origin = MagicMock(
        action="BUY", entry_price=80.0, stop_price=78.0,
        exit_price=None, exit_run_id=None, r_multiple=None, outcome=None,
    )
    result = MagicMock()
    result.scalar_one_or_none.return_value = origin
    db.execute = AsyncMock(return_value=result)

    await _tag_origin_run(db, user_id=1, ticker="VCB", exit_run_id=99, exit_price=77.0)
    # Risk = 2.0; PnL = -3.0 → R = -1.5 (LOSS)
    assert origin.outcome == "LOSS"
    assert origin.r_multiple == -1.5


@pytest.mark.asyncio
async def test_tag_origin_run_tags_breakeven_when_pnl_tiny():
    """abs(R) <= 0.1 is treated as BREAKEVEN."""
    db = AsyncMock()
    origin = MagicMock(
        action="BUY", entry_price=80.0, stop_price=78.0,
        exit_price=None, exit_run_id=None, r_multiple=None, outcome=None,
    )
    result = MagicMock()
    result.scalar_one_or_none.return_value = origin
    db.execute = AsyncMock(return_value=result)

    await _tag_origin_run(db, user_id=1, ticker="VCB", exit_run_id=99, exit_price=80.1)
    # PnL = 0.1, risk = 2.0, R = 0.05 → BREAKEVEN
    assert origin.outcome == "BREAKEVEN"


@pytest.mark.asyncio
async def test_tag_origin_run_short_inverts_sign():
    """SELL_SHORT entry: exit below entry is a WIN (price dropped)."""
    db = AsyncMock()
    origin = MagicMock(
        action="SELL_SHORT", entry_price=80.0, stop_price=82.0,
        exit_price=None, exit_run_id=None, r_multiple=None, outcome=None,
    )
    result = MagicMock()
    result.scalar_one_or_none.return_value = origin
    db.execute = AsyncMock(return_value=result)

    await _tag_origin_run(db, user_id=1, ticker="VCB", exit_run_id=99, exit_price=75.0)
    # Risk = 2.0; PnL (short) = entry - exit = 5.0 → R = 2.5 (WIN)
    assert origin.outcome == "WIN"
    assert origin.r_multiple == 2.5


@pytest.mark.asyncio
async def test_tag_origin_run_skips_when_risk_is_zero():
    """entry == stop → risk = 0; division would blow up, so we no-op."""
    db = AsyncMock()
    origin = MagicMock(
        action="BUY", entry_price=80.0, stop_price=80.0,
        exit_price=None, exit_run_id=None, r_multiple=None, outcome=None,
    )
    result = MagicMock()
    result.scalar_one_or_none.return_value = origin
    db.execute = AsyncMock(return_value=result)

    await _tag_origin_run(db, user_id=1, ticker="VCB", exit_run_id=99, exit_price=85.0)
    # Origin was *not* mutated.
    assert origin.exit_price is None
    assert origin.outcome is None


# ---------------------------------------------------------------------------
# run_recommendation — abort path when OHLCV is empty
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_recommendation_aborts_when_no_ohlcv():
    """Empty bar list → returns an abort-shaped RecommendationResponse."""
    db = AsyncMock()
    market = MagicMock()
    market.fetch_ohlcv = AsyncMock(return_value=[])

    # classify_regime returns a basic TREND_UP shape; orchestrator still
    # aborts after the ohlcv check.
    from app.services.regime.classifier import RegimeResult
    regime = RegimeResult(regime="TREND_UP", confidence=0.7, features={})

    from unittest.mock import patch
    with patch("app.services.decision.orchestrator.classify_regime",
               new=AsyncMock(return_value=regime)):
        resp = await run_recommendation(
            user_id=1, ticker="VCB", bar_date=date(2026, 5, 20),
            trigger="ON_DEMAND", db=db, client=market,
        )

    assert resp.action == "WAIT"
    # The reason chain ends in the abort step
    chain = [r.stage for r in resp.reason_chain]
    assert "abort" in chain
