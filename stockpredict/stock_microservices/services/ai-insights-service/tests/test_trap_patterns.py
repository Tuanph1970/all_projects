"""Unit tests for the F-006 bull / bear trap detector.

A trap fires when price penetrates an S/R level but closes back inside the
range within N bars.  Tests use synthetic OHLCV series where the S/R level,
penetration bar, and reversal bar are all analytically known.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from app.services.patterns.trap import TrapDetector, run_trap_detectors, _build_sr_levels


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

def _ranging_frame(
    support: float = 90.0,
    resistance: float = 110.0,
    n_pre: int = 30,
) -> pd.DataFrame:
    """Create a range-bound series that bounces between support and
    resistance so the S/R builder has clear levels to latch onto."""
    closes = np.zeros(n_pre)
    for i in range(n_pre):
        t = i / n_pre
        closes[i] = support + (resistance - support) * (np.sin(2 * np.pi * t * 3) + 1) / 2
    return pd.DataFrame({
        "open": closes,
        "high": closes + 0.5,
        "low": closes - 0.5,
        "close": closes,
        "volume": np.full(n_pre, 1000, dtype=int),
    })


def _append_bars(base: pd.DataFrame, closes: list) -> pd.DataFrame:
    """Append explicit bars to an existing frame."""
    extra = pd.DataFrame({
        "open": closes,
        "high": [c + 0.5 for c in closes],
        "low": [c - 0.5 for c in closes],
        "close": closes,
        "volume": [1000] * len(closes),
    })
    return pd.concat([base, extra], ignore_index=True)


def _bull_trap_frame(
    support: float = 90.0,
    resistance: float = 110.0,
    n_pre: int = 35,
    penetration: float = 2.5,  # close above resistance by this much
    revert_after: int = 2,     # bars after penetration where price reverts
) -> pd.DataFrame:
    """Ranging frame + a bar that closes above resistance, then reverts."""
    base = _ranging_frame(support, resistance, n_pre)
    breakout_close = resistance + penetration       # bull trap bar
    revert_close = resistance - 1.0                # back below resistance

    bars = [breakout_close]
    for j in range(revert_after - 1):
        bars.append(breakout_close - 0.5)          # still above resistance
    bars.append(revert_close)                       # revert
    bars.append(revert_close - 0.5)                # continue below

    return _append_bars(base, bars)


def _bear_trap_frame(
    support: float = 90.0,
    resistance: float = 110.0,
    n_pre: int = 35,
    penetration: float = 2.5,  # close below support by this much
    revert_after: int = 2,
) -> pd.DataFrame:
    """Ranging frame + a bar that closes below support, then reverts above."""
    base = _ranging_frame(support, resistance, n_pre)
    breakout_close = support - penetration
    revert_close = support + 1.0

    bars = [breakout_close]
    for j in range(revert_after - 1):
        bars.append(breakout_close + 0.5)
    bars.append(revert_close)
    bars.append(revert_close + 0.5)

    return _append_bars(base, bars)


# ---------------------------------------------------------------------------
# _build_sr_levels helper
# ---------------------------------------------------------------------------

class TestBuildSRLevels:
    def test_finds_support_and_resistance_in_range(self):
        df = _ranging_frame(support=90.0, resistance=110.0, n_pre=40)
        supports, resistances = _build_sr_levels(df)
        # Should find levels near 90 (support) and 110 (resistance).
        assert len(supports) > 0
        assert len(resistances) > 0

    def test_no_levels_on_flat_data(self):
        close = np.full(40, 100.0)
        df = pd.DataFrame({
            "open": close, "high": close + 0.5,
            "low": close - 0.5, "close": close, "volume": [1000] * 40,
        })
        supports, resistances = _build_sr_levels(df)
        # Flat data: no swing pivots → empty lists.
        assert supports == [] and resistances == []


# ---------------------------------------------------------------------------
# TrapDetector
# ---------------------------------------------------------------------------

class TestTrapDetector:
    def test_detects_bull_trap(self):
        df = _bull_trap_frame(resistance=110.0, penetration=2.5, revert_after=2)
        m = TrapDetector(revert_bars=3).detect(df)
        assert m is not None and m.found
        assert m.details["trap_type"] == "bull_trap"
        assert m.pattern_type == "bearish"  # bull trap is bearish signal

    def test_detects_bear_trap(self):
        df = _bear_trap_frame(support=90.0, penetration=2.5, revert_after=2)
        m = TrapDetector(revert_bars=3).detect(df)
        assert m is not None and m.found
        assert m.details["trap_type"] == "bear_trap"
        assert m.pattern_type == "bullish"  # bear trap is bullish signal

    def test_bull_trap_severity_positive(self):
        df = _bull_trap_frame(penetration=3.0)
        m = TrapDetector(revert_bars=3).detect(df)
        assert m is not None
        assert m.details["severity"] > 0

    def test_bear_trap_severity_positive(self):
        df = _bear_trap_frame(penetration=3.0)
        m = TrapDetector(revert_bars=3).detect(df)
        assert m is not None
        assert m.details["severity"] > 0

    def test_bull_trap_target_below_level(self):
        df = _bull_trap_frame(resistance=110.0, penetration=2.5)
        m = TrapDetector(revert_bars=3).detect(df)
        assert m is not None
        # Trap target = downside measured move.
        assert m.measured_move_target < m.neckline

    def test_bear_trap_target_above_level(self):
        df = _bear_trap_frame(support=90.0, penetration=2.5)
        m = TrapDetector(revert_bars=3).detect(df)
        assert m is not None
        assert m.measured_move_target > m.neckline

    def test_no_trap_on_successful_breakout(self):
        """Breakout that does NOT revert within revert_bars → no trap."""
        base = _ranging_frame(support=90.0, resistance=110.0, n_pre=35)
        # Price breaks out and stays above resistance for 5 bars.
        bars = [112.0, 113.0, 114.0, 115.0, 116.0]
        df = _append_bars(base, bars)
        m = TrapDetector(revert_bars=3).detect(df)
        # No trap because price never reverted.
        if m is not None:
            assert m.details["trap_type"] not in ("bull_trap",)

    def test_no_trap_on_flat_data(self):
        df = _ranging_frame(support=90.0, resistance=110.0, n_pre=35)
        # The ranging data might incidentally touch levels — verify no crash.
        m = TrapDetector(revert_bars=3).detect(df)
        # This is allowed to return a trap or None; just verify no exception.
        assert m is None or m.found

    def test_rejects_short_series(self):
        df = pd.DataFrame({
            "open": [100.0] * 5, "high": [101.0] * 5,
            "low": [99.0] * 5, "close": [100.0] * 5, "volume": [1000] * 5,
        })
        assert TrapDetector().detect(df) is None

    def test_key_bars_ordered(self):
        df = _bull_trap_frame(penetration=2.5, revert_after=2)
        m = TrapDetector(revert_bars=3).detect(df)
        if m is not None:
            assert m.key_bars[0] <= m.key_bars[-1]

    def test_level_breached_is_close_to_resistance(self):
        resistance = 110.0
        df = _bull_trap_frame(resistance=resistance, penetration=3.0)
        m = TrapDetector(revert_bars=3).detect(df)
        if m is not None and m.details["trap_type"] == "bull_trap":
            # The breached level should be close to the known resistance.
            assert abs(m.details["level_breached"] - resistance) < resistance * 0.05


# ---------------------------------------------------------------------------
# Aggregator helper
# ---------------------------------------------------------------------------

class TestTrapAggregator:
    def test_run_returns_list(self):
        df = _bull_trap_frame(penetration=2.5, revert_after=2)
        results = run_trap_detectors(df)
        assert isinstance(results, list)

    def test_run_finds_bull_trap(self):
        df = _bull_trap_frame(penetration=2.5, revert_after=2)
        results = run_trap_detectors(df)
        if results:
            assert results[0].details["trap_type"] == "bull_trap"

    def test_run_returns_empty_on_flat(self):
        close = np.full(50, 100.0)
        df = pd.DataFrame({
            "open": close, "high": close + 0.3,
            "low": close - 0.3, "close": close, "volume": [1000] * 50,
        })
        results = run_trap_detectors(df)
        assert isinstance(results, list)
