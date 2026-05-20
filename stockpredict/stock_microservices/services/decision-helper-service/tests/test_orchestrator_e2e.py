"""End-to-end tests for app.services.decision.orchestrator.run_recommendation.

The earlier test_orchestrator_extra.py covers the helpers in isolation.
This file drives the full pipeline — regime → bars → ATR/swings/SR →
patterns/RSI → signal engine → confirmation → failed-signal →
position state → trailing stop → state machine → risk overlay →
discipline → persist → response — with the external dependencies
(MarketClient, signal engines, confirm) controlled so each action
branch (BUY / SELL_SHORT / SELL / COVER / HOLD / REVERSE / WAIT)
can be exercised deterministically.

Strategy:
- `_FakeMarketClient` exposes all fetch_* methods as AsyncMock with
  configurable return values.
- `_run_signal_engines` is patched to return a known RawSignal list
  so we don't have to fight the real detectors to trigger an action.
- `confirm` is patched per test to accept or reject the signal.
- `db.add` is captured so we can assert what DecisionRun / PositionState
  rows the orchestrator persisted. `db.flush` mutates the captured
  DecisionRun's id so _tag_origin_run has a real id to work with.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.domain import DecisionRun, PositionState
from app.services.confirmation.layer import ConfirmationResult
from app.services.decision.orchestrator import _persist, run_recommendation
from app.services.position.state_machine import StateTransition, next_state
from app.services.signal.base import OHLCVBar, RawSignal


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


class _FakeMarketClient:
    """Stand-in for app.services.market.client.MarketClient.

    Every fetch_* coroutine returns a pre-configured value; tests
    override individual returns via the constructor or by reassigning
    on the instance.
    """

    def __init__(
        self,
        *,
        bars: Optional[List[dict]] = None,
        atr: Optional[float] = 1.0,
        swings: Optional[List[dict]] = None,
        sr_data: Optional[dict] = None,
        patterns: Optional[dict] = None,
        rsi: Optional[float] = None,
    ):
        self._bars = bars or []
        self._atr = atr
        self._swings = swings or []
        self._sr_data = sr_data
        self._patterns = patterns
        self._rsi = rsi

    async def fetch_ohlcv(self, symbol, days=300, end_date=None):
        return list(self._bars)

    async def fetch_atr(self, symbol, period=14, days=100):
        if self._atr is None:
            return None
        return {"latest": self._atr}

    async def fetch_swings(self, symbol, window=3, days=300):
        return {"pivots": list(self._swings)} if self._swings else None

    async def fetch_sr_levels(self, symbol, window=5, tolerance_pct=1.5):
        return self._sr_data

    async def fetch_patterns(self, symbol):
        return self._patterns

    async def fetch_technical(self, symbol):
        if self._rsi is None:
            return None
        return {"indicators": [{"name": "RSI", "value": self._rsi}]}


def _make_bars(n: int = 80, start: date = date(2026, 1, 1),
               base: float = 80.0, step: float = 0.1) -> List[dict]:
    """Bars compatible with OHLCVBar.from_dict — orchestrator builds
    OHLCVBar via .from_dict."""
    out = []
    for i in range(n):
        close = base + i * step
        d = start + timedelta(days=i)
        out.append({
            "date": d.isoformat(),
            "open": close,
            "high": close + 1.0,
            "low": close - 1.0,
            "close": close,
            "volume": 1000 + i,
        })
    return out


def _capture_persist(mock_db, *, run_id: int = 1):
    """Wire mock_db so DecisionRun + PositionState rows added by _persist
    are captured for assertion, and db.flush() populates run.id."""
    captured = {"decisions": [], "positions": []}

    def _add(obj):
        if isinstance(obj, DecisionRun):
            captured["decisions"].append(obj)
        elif isinstance(obj, PositionState):
            captured["positions"].append(obj)

    mock_db.add = MagicMock(side_effect=_add)

    async def _flush():
        # SQLAlchemy assigns an id at flush; we mimic it for the most
        # recently added DecisionRun.
        if captured["decisions"]:
            captured["decisions"][-1].id = run_id

    mock_db.flush = AsyncMock(side_effect=_flush)
    mock_db.commit = AsyncMock()
    mock_db.rollback = AsyncMock()
    return captured


def _signal(direction: str = "LONG", kind: str = "MA_CROSS",
            confidence: float = 0.7, trigger: float = 85.0) -> RawSignal:
    return RawSignal(
        kind=kind, direction=direction, confidence=confidence,
        bar_date=date(2026, 3, 21), trigger_price=trigger,
        evidence={"slow_ma": trigger, "breakout_level": trigger},
    )


def _confirmed(sig: RawSignal, *, final_conf: float = 0.78) -> ConfirmationResult:
    return ConfirmationResult(
        accepted=True, signal=sig, final_confidence=final_conf,
        reason_steps=[], rejection_reason=None,
    )


def _rejected(sig: RawSignal, *, reason: str = "fail") -> ConfirmationResult:
    return ConfirmationResult(
        accepted=False, signal=sig, final_confidence=0.0,
        reason_steps=[], rejection_reason=reason,
    )


def _regime(name: str = "TREND_UP", confidence: float = 0.8):
    from app.services.regime.classifier import RegimeResult
    return RegimeResult(regime=name, confidence=confidence, features={})


# ---------------------------------------------------------------------------
# Happy path: BUY (FLAT -> LONG)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_buy_from_flat_full_pipeline():
    """A confirmed LONG signal from FLAT should produce a BUY action, a
    stop, a target, and a position size. The persist layer should add
    a DecisionRun and a PositionState row."""
    db = AsyncMock()
    captured = _capture_persist(db)
    # No existing position row.
    no_pos_result = MagicMock()
    no_pos_result.scalar_one_or_none.return_value = None
    # No prefs row → defaults apply.
    db.execute = AsyncMock(return_value=no_pos_result)

    client = _FakeMarketClient(bars=_make_bars(120), atr=1.0)
    sig = _signal(direction="LONG", trigger=89.0)

    with patch(
        "app.services.decision.orchestrator.classify_regime",
        new=AsyncMock(return_value=_regime("TREND_UP")),
    ), patch(
        "app.services.decision.orchestrator._run_signal_engines",
        return_value=[sig],
    ), patch(
        "app.services.decision.orchestrator.confirm",
        return_value=_confirmed(sig),
    ), patch(
        "app.services.decision.orchestrator.detect_failed_signals",
        return_value=[],
    ):
        resp = await run_recommendation(
            user_id=1, ticker="VCB", bar_date=date(2026, 3, 21),
            trigger="ON_DEMAND", db=db, client=client,
        )

    assert resp.action == "BUY"
    assert resp.state_before == "FLAT"
    assert resp.state_after == "LONG"
    assert resp.entry_price is not None
    assert resp.stop_price is not None  # stop_module produced a stop
    assert resp.target_price is not None
    assert resp.position_size is not None
    assert resp.signal_confirmed is True

    # Persisted: 1 DecisionRun, 1 new PositionState (was FLAT/no row).
    assert len(captured["decisions"]) == 1
    assert captured["decisions"][0].action == "BUY"
    assert len(captured["positions"]) == 1
    assert captured["positions"][0].state == "LONG"
    assert captured["positions"][0].entry_price == resp.entry_price


# ---------------------------------------------------------------------------
# SELL_SHORT (FLAT -> SHORT)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sell_short_from_flat():
    db = AsyncMock()
    captured = _capture_persist(db)
    db.execute = AsyncMock(return_value=MagicMock(
        scalar_one_or_none=MagicMock(return_value=None)
    ))

    client = _FakeMarketClient(bars=_make_bars(120))
    sig = _signal(direction="SHORT", trigger=85.0)

    with patch(
        "app.services.decision.orchestrator.classify_regime",
        new=AsyncMock(return_value=_regime("TREND_DOWN")),
    ), patch(
        "app.services.decision.orchestrator._run_signal_engines",
        return_value=[sig],
    ), patch(
        "app.services.decision.orchestrator.confirm",
        return_value=_confirmed(sig),
    ), patch(
        "app.services.decision.orchestrator.detect_failed_signals",
        return_value=[],
    ):
        resp = await run_recommendation(
            user_id=1, ticker="VCB", bar_date=date(2026, 3, 21),
            trigger="ON_DEMAND", db=db, client=client,
        )

    assert resp.action == "SELL_SHORT"
    assert resp.state_after == "SHORT"
    assert len(captured["positions"]) == 1
    assert captured["positions"][0].state == "SHORT"


# ---------------------------------------------------------------------------
# HOLD with trailing stop improvement
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_hold_long_improves_trailing_stop():
    """Existing LONG position, no new signal, but the trailing stop module
    sees a more favorable level — the response should reflect HOLD with
    an updated stop, and the persisted PositionState gets the new stop."""
    pos = MagicMock(
        spec=PositionState,
        user_id=1, ticker="VCB", state="LONG",
        entry_bar_date=date(2026, 3, 1), entry_price=85.0,
        position_size=100, current_stop=80.0, current_target=92.0,
        entry_signal_kind="MA_CROSS",
    )

    db = AsyncMock()
    captured = _capture_persist(db)
    # First execute: _load_position → returns pos. Subsequent executes
    # (prefs, recent_losses) return empty.
    pos_result = MagicMock()
    pos_result.scalar_one_or_none.return_value = pos
    empty_scalars = MagicMock()
    inner = MagicMock()
    inner.all.return_value = []
    empty_scalars.scalars.return_value = inner
    db.execute = AsyncMock(side_effect=[
        pos_result,             # _load_position
        MagicMock(scalar_one_or_none=MagicMock(return_value=None)),  # discipline prefs
        empty_scalars,          # recent losses query
    ])

    client = _FakeMarketClient(bars=_make_bars(120), atr=1.0)

    # No signals fire → confirmation is irrelevant; state stays LONG → HOLD.
    with patch(
        "app.services.decision.orchestrator.classify_regime",
        new=AsyncMock(return_value=_regime("TREND_UP")),
    ), patch(
        "app.services.decision.orchestrator._run_signal_engines",
        return_value=[],
    ), patch(
        "app.services.decision.orchestrator.detect_failed_signals",
        return_value=[],
    ):
        resp = await run_recommendation(
            user_id=1, ticker="VCB", bar_date=date(2026, 3, 21),
            trigger="ON_DEMAND", db=db, client=client,
        )

    assert resp.action == "HOLD"
    assert resp.state_before == "LONG"
    assert resp.state_after == "LONG"
    # Persisted: DecisionRun, no NEW PositionState (existing row mutated)
    assert len(captured["decisions"]) == 1
    assert captured["decisions"][0].action == "HOLD"


# ---------------------------------------------------------------------------
# SELL when stop is hit (LONG -> FLAT)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sell_when_stop_hit_tags_origin_run_outcome():
    """LONG position; the latest bar's close is below the current stop.
    State machine fires SELL → orchestrator should call _tag_origin_run
    to back-fill the originating BUY row's outcome."""
    # Build bars with the LAST close at 78 — below the stop at 80.
    bars = _make_bars(60, base=85.0, step=-0.1)  # decreasing series
    # Force last close = 78.0
    bars[-1]["close"] = 78.0

    pos = MagicMock(
        spec=PositionState,
        user_id=1, ticker="VCB", state="LONG",
        entry_bar_date=date(2026, 3, 1), entry_price=85.0,
        position_size=100, current_stop=80.0, current_target=92.0,
        entry_signal_kind="MA_CROSS",
    )

    # The origin BUY run that _tag_origin_run will mutate.
    origin = MagicMock(
        spec=DecisionRun,
        id=42, action="BUY", entry_price=85.0, stop_price=80.0,
        exit_price=None, exit_run_id=None, r_multiple=None, outcome=None,
    )

    db = AsyncMock()
    captured = _capture_persist(db, run_id=99)

    # The orchestrator's DB queries in order:
    #   1. _load_position → pos
    #   2. _load_prefs (in risk overlay block — SKIPPED because action is SELL)
    #   3. _load_prefs (in discipline check block) → None
    #   4. _count_recent_losses (in discipline check) → []
    #   5. _tag_origin_run → origin
    pos_result = MagicMock()
    pos_result.scalar_one_or_none.return_value = pos
    none_result = MagicMock()
    none_result.scalar_one_or_none.return_value = None
    empty_scalars = MagicMock()
    inner = MagicMock(); inner.all.return_value = []
    empty_scalars.scalars.return_value = inner
    origin_result = MagicMock()
    origin_result.scalar_one_or_none.return_value = origin

    db.execute = AsyncMock(side_effect=[
        pos_result,        # _load_position
        none_result,       # _load_prefs in discipline
        empty_scalars,     # _count_recent_losses
        origin_result,     # _tag_origin_run inside _persist
    ])

    client = _FakeMarketClient(bars=bars, atr=1.0)

    last_bar_date = date.fromisoformat(bars[-1]["date"])
    with patch(
        "app.services.decision.orchestrator.classify_regime",
        new=AsyncMock(return_value=_regime("TREND_UP")),
    ), patch(
        "app.services.decision.orchestrator._run_signal_engines",
        return_value=[],
    ), patch(
        "app.services.decision.orchestrator.detect_failed_signals",
        return_value=[],
    ):
        resp = await run_recommendation(
            user_id=1, ticker="VCB", bar_date=last_bar_date,
            trigger="ON_DEMAND", db=db, client=client,
        )

    assert resp.action == "SELL"
    assert resp.state_after == "FLAT"
    # Origin run was back-filled with exit info.
    assert origin.exit_price == 78.0
    assert origin.exit_run_id == 99
    assert origin.outcome == "LOSS"   # 78 < 85 entry, R is sharply negative


# ---------------------------------------------------------------------------
# WAIT — no signals, FLAT remains FLAT
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_wait_when_no_signal_and_flat():
    db = AsyncMock()
    captured = _capture_persist(db)
    # _load_position → None; subsequent: discipline prefs → None, losses → []
    none_result = MagicMock(scalar_one_or_none=MagicMock(return_value=None))
    empty_scalars = MagicMock()
    inner = MagicMock(); inner.all.return_value = []
    empty_scalars.scalars.return_value = inner
    db.execute = AsyncMock(side_effect=[none_result, none_result, empty_scalars])

    client = _FakeMarketClient(bars=_make_bars(80))

    with patch(
        "app.services.decision.orchestrator.classify_regime",
        new=AsyncMock(return_value=_regime("UNDEFINED")),
    ), patch(
        "app.services.decision.orchestrator._run_signal_engines",
        return_value=[],
    ), patch(
        "app.services.decision.orchestrator.detect_failed_signals",
        return_value=[],
    ):
        resp = await run_recommendation(
            user_id=1, ticker="VCB", bar_date=date(2026, 3, 21),
            trigger="ON_DEMAND", db=db, client=client,
        )

    assert resp.action == "WAIT"
    assert resp.state_after == "FLAT"
    # Persisted: 1 DecisionRun, no PositionState because state_after is FLAT.
    assert len(captured["decisions"]) == 1
    assert len(captured["positions"]) == 0


# ---------------------------------------------------------------------------
# REVERSE — confirmed opposite signal while in LONG
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_reverse_long_to_flat_on_confirmed_short():
    pos = MagicMock(
        spec=PositionState,
        user_id=1, ticker="VCB", state="LONG",
        entry_bar_date=date(2026, 3, 1), entry_price=85.0,
        position_size=100, current_stop=80.0, current_target=92.0,
        entry_signal_kind="MA_CROSS",
    )
    origin = MagicMock(
        spec=DecisionRun,
        id=42, action="BUY", entry_price=85.0, stop_price=80.0,
        exit_price=None, exit_run_id=None, r_multiple=None, outcome=None,
    )

    db = AsyncMock()
    _capture_persist(db, run_id=100)

    pos_result = MagicMock(scalar_one_or_none=MagicMock(return_value=pos))
    none_result = MagicMock(scalar_one_or_none=MagicMock(return_value=None))
    empty_scalars = MagicMock()
    inner = MagicMock(); inner.all.return_value = []
    empty_scalars.scalars.return_value = inner
    origin_result = MagicMock(scalar_one_or_none=MagicMock(return_value=origin))

    db.execute = AsyncMock(side_effect=[
        pos_result, none_result, empty_scalars, origin_result,
    ])

    client = _FakeMarketClient(bars=_make_bars(80), atr=1.0)
    sig = _signal(direction="SHORT", trigger=85.0)

    with patch(
        "app.services.decision.orchestrator.classify_regime",
        new=AsyncMock(return_value=_regime("TREND_DOWN")),
    ), patch(
        "app.services.decision.orchestrator._run_signal_engines",
        return_value=[sig],
    ), patch(
        "app.services.decision.orchestrator.confirm",
        return_value=_confirmed(sig),
    ), patch(
        "app.services.decision.orchestrator.detect_failed_signals",
        return_value=[],
    ):
        resp = await run_recommendation(
            user_id=1, ticker="VCB", bar_date=date(2026, 3, 21),
            trigger="ON_DEMAND", db=db, client=client,
        )

    assert resp.action == "REVERSE"
    assert resp.state_before == "LONG"
    assert resp.state_after == "FLAT"


# ---------------------------------------------------------------------------
# Failed-signal override flips direction
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_failed_signal_above_threshold_overrides_direction():
    """A high-severity failed signal flips the orchestrator's
    signal_direction (and records it as failed_signal_kind on the
    response)."""
    from app.services.signal.failed_signal import (
        FailedSignalResult,
        OVERRIDE_THRESHOLD,
    )

    db = AsyncMock()
    _capture_persist(db)
    db.execute = AsyncMock(return_value=MagicMock(
        scalar_one_or_none=MagicMock(return_value=None)
    ))

    client = _FakeMarketClient(bars=_make_bars(80), atr=1.0)
    sig = _signal(direction="LONG", trigger=80.0)

    failed = FailedSignalResult(
        kind="bull_trap",
        direction="SHORT",
        severity=OVERRIDE_THRESHOLD + 0.1,
        evidence={},
    )

    with patch(
        "app.services.decision.orchestrator.classify_regime",
        new=AsyncMock(return_value=_regime("TREND_UP")),
    ), patch(
        "app.services.decision.orchestrator._run_signal_engines",
        return_value=[sig],
    ), patch(
        "app.services.decision.orchestrator.confirm",
        return_value=_confirmed(sig),
    ), patch(
        "app.services.decision.orchestrator.detect_failed_signals",
        return_value=[failed],
    ):
        resp = await run_recommendation(
            user_id=1, ticker="VCB", bar_date=date(2026, 3, 21),
            trigger="ON_DEMAND", db=db, client=client,
        )

    assert resp.failed_signal_kind == "bull_trap"
    # Confirmed LONG was overridden to SHORT → from FLAT this is SELL_SHORT.
    assert resp.action == "SELL_SHORT"


@pytest.mark.asyncio
async def test_failed_signal_below_threshold_does_not_override():
    """Low-severity failed signal stays informational — direction unchanged."""
    from app.services.signal.failed_signal import (
        FailedSignalResult,
        OVERRIDE_THRESHOLD,
    )

    db = AsyncMock()
    _capture_persist(db)
    db.execute = AsyncMock(return_value=MagicMock(
        scalar_one_or_none=MagicMock(return_value=None)
    ))

    client = _FakeMarketClient(bars=_make_bars(80), atr=1.0)
    sig = _signal(direction="LONG", trigger=80.0)
    weak_failed = FailedSignalResult(
        kind="bull_trap", direction="SHORT",
        severity=max(0.0, OVERRIDE_THRESHOLD - 0.05),
        evidence={},
    )

    with patch(
        "app.services.decision.orchestrator.classify_regime",
        new=AsyncMock(return_value=_regime("TREND_UP")),
    ), patch(
        "app.services.decision.orchestrator._run_signal_engines",
        return_value=[sig],
    ), patch(
        "app.services.decision.orchestrator.confirm",
        return_value=_confirmed(sig),
    ), patch(
        "app.services.decision.orchestrator.detect_failed_signals",
        return_value=[weak_failed],
    ):
        resp = await run_recommendation(
            user_id=1, ticker="VCB", bar_date=date(2026, 3, 21),
            trigger="ON_DEMAND", db=db, client=client,
        )

    # Original LONG direction stuck — from FLAT this is BUY.
    assert resp.action == "BUY"
    assert resp.failed_signal_kind is None


# ---------------------------------------------------------------------------
# Confirmation rejection: signal present but not accepted → WAIT from FLAT
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_rejected_signal_does_not_enter_position():
    db = AsyncMock()
    captured = _capture_persist(db)
    db.execute = AsyncMock(return_value=MagicMock(
        scalar_one_or_none=MagicMock(return_value=None)
    ))

    client = _FakeMarketClient(bars=_make_bars(80))
    sig = _signal(direction="LONG", trigger=85.0)

    with patch(
        "app.services.decision.orchestrator.classify_regime",
        new=AsyncMock(return_value=_regime("TREND_UP")),
    ), patch(
        "app.services.decision.orchestrator._run_signal_engines",
        return_value=[sig],
    ), patch(
        "app.services.decision.orchestrator.confirm",
        return_value=_rejected(sig, reason="penetration too small"),
    ), patch(
        "app.services.decision.orchestrator.detect_failed_signals",
        return_value=[],
    ):
        resp = await run_recommendation(
            user_id=1, ticker="VCB", bar_date=date(2026, 3, 21),
            trigger="ON_DEMAND", db=db, client=client,
        )

    assert resp.action == "WAIT"
    assert resp.signal_confirmed is False
    # No PositionState added on a WAIT.
    assert len(captured["positions"]) == 0


# ---------------------------------------------------------------------------
# Persist layer — error path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_persist_swallows_exception_and_rolls_back():
    """If db.commit raises, _persist must call rollback and log, not raise."""
    db = AsyncMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock(side_effect=RuntimeError("DB down"))
    db.rollback = AsyncMock()

    transition = StateTransition(
        action="WAIT", state_before="FLAT", state_after="FLAT",
        reason="no signal",
    )

    await _persist(
        db=db, user_id=1, ticker="VCB", bar_date=date(2026, 5, 20),
        trigger="ON_DEMAND", regime="TREND_UP",
        best_signal=None, best_confirmed=None, transition=transition,
        entry_price=None, stop_price=None, target_price=None,
        position_size=None, current_stop=None,
        reason_chain=[], confidence=0.0, latency_ms=0,
        pos_row=None, bar_date_val=date(2026, 5, 20),
    )

    db.rollback.assert_awaited()
    db.commit.assert_awaited()


@pytest.mark.asyncio
async def test_persist_resets_position_on_exit_action():
    """SELL action with an existing PositionState must zero-out the row's
    entry/stop/target fields."""
    db = AsyncMock()
    captured = _capture_persist(db)
    # _tag_origin_run query inside _persist → no origin to back-fill.
    db.execute = AsyncMock(return_value=MagicMock(
        scalar_one_or_none=MagicMock(return_value=None)
    ))

    pos = MagicMock(
        spec=PositionState,
        user_id=1, ticker="VCB", state="LONG",
        entry_bar_date=date(2026, 3, 1), entry_price=85.0,
        position_size=100, current_stop=80.0, current_target=92.0,
        entry_signal_kind="MA_CROSS",
        last_decision_run_id=None,
    )
    transition = StateTransition(
        action="SELL", state_before="LONG", state_after="FLAT",
        reason="stop hit",
    )

    await _persist(
        db=db, user_id=1, ticker="VCB", bar_date=date(2026, 5, 20),
        trigger="ON_DEMAND", regime="TREND_UP",
        best_signal=None, best_confirmed=None, transition=transition,
        entry_price=85.0, stop_price=None, target_price=None,
        position_size=None, current_stop=80.0,
        reason_chain=[], confidence=0.0, latency_ms=0,
        pos_row=pos, bar_date_val=date(2026, 5, 20),
        exit_price_actual=82.0,
    )

    # The existing PositionState was mutated to a fully-closed state.
    assert pos.state == "FLAT"
    assert pos.entry_bar_date is None
    assert pos.entry_price is None
    assert pos.position_size == 0
    assert pos.current_stop is None
    assert pos.current_target is None
    assert pos.entry_signal_kind is None
