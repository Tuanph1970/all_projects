"""Unit tests for Phase C modules: stop_module, target_module, sizing_module,
position state_machine.

These are pure-logic tests with no DB or HTTP calls.
"""
from __future__ import annotations

import pytest
from datetime import date

from app.services.risk.stop_module import (
    compute_initial_stop,
    update_trailing_stop,
)
from app.services.risk.target_module import compute_target
from app.services.risk.sizing_module import compute_size
from app.services.position.state_machine import next_state


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sr(supports=(), resistances=()):
    return {
        "supports": [{"price": p, "type": "support", "strength": 2} for p in supports],
        "resistances": [{"price": p, "type": "resistance", "strength": 2} for p in resistances],
    }


def _swings(lows=(), highs=()):
    pivots = [
        {"price": p, "type": "low", "date": "2024-01-01"} for p in lows
    ] + [
        {"price": p, "type": "high", "date": "2024-01-01"} for p in highs
    ]
    return pivots


# ---------------------------------------------------------------------------
# stop_module
# ---------------------------------------------------------------------------

class TestStopModule:
    def test_chart_stop_long_prefers_nearest_support(self):
        sr = _sr(supports=[95, 98, 92])
        result = compute_initial_stop("LONG", entry_price=100, atr=2.0, swings=None, sr_levels=sr)
        assert result.stop_kind == "CHART"
        # nearest support below 100 is 98; stop = 98 * (1 - 0.005)
        assert result.stop_price == pytest.approx(98 * 0.995, abs=0.001)

    def test_chart_stop_short_prefers_nearest_resistance(self):
        sr = _sr(resistances=[105, 110, 103])
        result = compute_initial_stop("SHORT", entry_price=100, atr=2.0, swings=None, sr_levels=sr)
        assert result.stop_kind == "CHART"
        # nearest resistance above 100 is 103; stop = 103 * 1.005
        assert result.stop_price == pytest.approx(103 * 1.005, abs=0.001)

    def test_chart_stop_skipped_when_too_far(self):
        """Support 10 % away → exceeds max_risk_pct=5 % → falls back to swing/ATR."""
        sr = _sr(supports=[88])   # 12 % below 100
        swings = _swings(lows=[97])
        result = compute_initial_stop("LONG", entry_price=100, atr=2.0, swings=swings, sr_levels=sr)
        assert result.stop_kind == "SWING"

    def test_swing_stop_long(self):
        swings = _swings(lows=[96, 98])
        result = compute_initial_stop("LONG", entry_price=100, atr=None, swings=swings, sr_levels=None)
        assert result.stop_kind == "SWING"
        # nearest low below 100 is 98
        assert result.stop_price == pytest.approx(98 * 0.995, abs=0.001)

    def test_atr_stop_long(self):
        result = compute_initial_stop("LONG", entry_price=100, atr=2.0, swings=None, sr_levels=None)
        assert result.stop_kind == "ATR"
        assert result.stop_price == pytest.approx(100 - 2.0 * 2.0, abs=0.001)

    def test_atr_stop_short(self):
        result = compute_initial_stop("SHORT", entry_price=100, atr=3.0, swings=None, sr_levels=None)
        assert result.stop_kind == "ATR"
        assert result.stop_price == pytest.approx(100 + 2.0 * 3.0, abs=0.001)

    def test_money_stop_fallback(self):
        result = compute_initial_stop("LONG", entry_price=100, atr=None, swings=None, sr_levels=None)
        assert result.stop_kind == "MONEY"
        assert result.stop_price == pytest.approx(100 * 0.95, abs=0.001)

    def test_trailing_stop_improves_for_long(self):
        # Current stop 94; close now 101 → ATR 2 → candidate = 101 - 4 = 97 > 94
        new_stop = update_trailing_stop("LONG", current_stop=94.0, current_close=101.0, atr=2.0)
        assert new_stop == pytest.approx(97.0, abs=0.001)

    def test_trailing_stop_never_widens_for_long(self):
        # Current stop 98; close 100 → candidate 96 < 98 → None
        new_stop = update_trailing_stop("LONG", current_stop=98.0, current_close=100.0, atr=2.0)
        assert new_stop is None

    def test_trailing_stop_improves_for_short(self):
        # Current stop 106; close 99 → candidate = 99 + 4 = 103 < 106
        new_stop = update_trailing_stop("SHORT", current_stop=106.0, current_close=99.0, atr=2.0)
        assert new_stop == pytest.approx(103.0, abs=0.001)

    def test_trailing_stop_never_widens_for_short(self):
        new_stop = update_trailing_stop("SHORT", current_stop=103.0, current_close=104.0, atr=2.0)
        assert new_stop is None


# ---------------------------------------------------------------------------
# target_module
# ---------------------------------------------------------------------------

class TestTargetModule:
    def test_measured_move_used_when_available(self):
        evidence = {"measured_move_target": 115.0}
        result = compute_target("LONG", 100, 95, "N_DAY_BREAKOUT", evidence, None)
        assert result.target_kind == "MEASURED_MOVE"
        assert result.target_price == 115.0
        assert result.partial_target == pytest.approx((100 + 115) / 2, abs=0.001)

    def test_measured_move_ignored_when_wrong_side(self):
        evidence = {"measured_move_target": 90.0}   # below entry for a LONG
        sr = _sr(resistances=[110])
        result = compute_target("LONG", 100, 95, "MA_CROSS", evidence, sr)
        assert result.target_kind in ("SR_LEVEL", "FIXED_RR")

    def test_sr_level_target_long(self):
        sr = _sr(resistances=[110, 120])
        result = compute_target("LONG", 100, 96, "MA_CROSS", {}, sr)
        assert result.target_kind == "SR_LEVEL"
        assert result.target_price == 110.0

    def test_sr_level_target_short(self):
        sr = _sr(supports=[90, 80])
        result = compute_target("SHORT", 100, 104, "MA_CROSS", {}, sr)
        assert result.target_kind == "SR_LEVEL"
        assert result.target_price == 90.0

    def test_fixed_rr_fallback(self):
        result = compute_target("LONG", 100, 98, "MA_CROSS", {}, None)
        assert result.target_kind == "FIXED_RR"
        # risk = 2; target = 100 + 2*2 = 104
        assert result.target_price == pytest.approx(104.0, abs=0.001)

    def test_partial_target_is_midpoint(self):
        sr = _sr(resistances=[110])
        result = compute_target("LONG", 100, 96, "MA_CROSS", {}, sr)
        assert result.partial_target == pytest.approx((100 + 110) / 2, abs=0.001)


# ---------------------------------------------------------------------------
# sizing_module
# ---------------------------------------------------------------------------

class TestSizingModule:
    def test_basic_fixed_fractional(self):
        # entry=10, stop=9 → per_share_risk=1; equity=10000, risk=1% → 100 shares
        # max_position = 10000*0.20/10 = 200 → no cap
        result = compute_size(10.0, 9.0, 10_000, 1.0)
        assert result.shares == 100
        assert result.risk_amount == pytest.approx(100.0, abs=0.1)

    def test_zero_when_stop_equals_entry(self):
        result = compute_size(100, 100, 10_000, 1.0)
        assert result.shares == 0

    def test_position_cap(self):
        # Very tight stop → raw size exceeds 20% equity cap
        # entry=100, stop=99.99 → per_share=0.01; equity=10000, risk=1% → 10000 raw shares
        # max = 10000*0.20/100 = 20 shares
        result = compute_size(100, 99.99, 10_000, 1.0)
        max_shares = int(10_000 * 0.20 / 100)
        assert result.shares <= max_shares
        assert any("Capped" in a for a in result.adjustments)

    def test_atr_vol_adjustment_reduces_size(self):
        # entry=10, stop=9, atr=5 → ATR-implied risk=10 >> stop risk*1.5=1.5
        # factor = max(0.5, min(1/10, 1.0)) = 0.5 → size halved
        result_base = compute_size(10.0, 9.0, 10_000, 1.0, atr=None)
        result_adj = compute_size(10.0, 9.0, 10_000, 1.0, atr=5.0)
        assert result_adj.shares < result_base.shares
        assert any("ATR-vol" in a for a in result_adj.adjustments)

    def test_losing_streak_halves_size(self):
        # Using same params as basic test (no cap, no ATR)
        base = compute_size(10.0, 9.0, 10_000, 1.0)
        streak = compute_size(10.0, 9.0, 10_000, 1.0, recent_losses=3,
                              loss_streak_threshold=3, loss_streak_size_cut=0.5)
        assert streak.shares == base.shares // 2
        assert any("Streak" in a for a in streak.adjustments)


# ---------------------------------------------------------------------------
# position state_machine
# ---------------------------------------------------------------------------

class TestStateMachine:
    def test_flat_no_signal_stays_wait(self):
        t = next_state("FLAT", None, 100.0, None, None)
        assert t.action == "WAIT"
        assert t.state_after == "FLAT"

    def test_flat_confirmed_long_buys(self):
        t = next_state("FLAT", "LONG", 100.0, None, None, signal_confirmed=True)
        assert t.action == "BUY"
        assert t.state_after == "LONG"
        assert t.entry_price == 100.0

    def test_flat_confirmed_short_sells_short(self):
        t = next_state("FLAT", "SHORT", 100.0, None, None, signal_confirmed=True)
        assert t.action == "SELL_SHORT"
        assert t.state_after == "SHORT"

    def test_flat_unconfirmed_signal_waits(self):
        t = next_state("FLAT", "LONG", 100.0, None, None, signal_confirmed=False)
        assert t.action == "WAIT"

    def test_long_hold_when_no_trigger(self):
        t = next_state("LONG", None, 100.0, 95.0, 110.0)
        assert t.action == "HOLD"
        assert t.state_after == "LONG"

    def test_long_stop_hit_sells(self):
        t = next_state("LONG", None, 94.0, 95.0, 110.0)
        assert t.action == "SELL"
        assert t.state_after == "FLAT"

    def test_long_target_hit_sells(self):
        t = next_state("LONG", None, 112.0, 95.0, 110.0)
        assert t.action == "SELL"
        assert t.state_after == "FLAT"

    def test_long_reverse_on_short_signal(self):
        t = next_state("LONG", "SHORT", 100.0, 95.0, 110.0, signal_confirmed=True)
        assert t.action == "REVERSE"
        assert t.state_after == "FLAT"

    def test_short_stop_hit_covers(self):
        t = next_state("SHORT", None, 106.0, 105.0, 90.0)
        assert t.action == "COVER"
        assert t.state_after == "FLAT"

    def test_short_target_hit_covers(self):
        t = next_state("SHORT", None, 89.0, 105.0, 90.0)
        assert t.action == "COVER"
        assert t.state_after == "FLAT"

    def test_short_reverse_on_long_signal(self):
        t = next_state("SHORT", "LONG", 100.0, 105.0, 90.0, signal_confirmed=True)
        assert t.action == "REVERSE"
        assert t.state_after == "FLAT"

    def test_long_to_short_must_pass_through_flat(self):
        """v1 constraint: LONG+SHORT_signal → REVERSE → FLAT (not directly SHORT)."""
        t = next_state("LONG", "SHORT", 100.0, 95.0, 110.0, signal_confirmed=True)
        assert t.state_after == "FLAT"
        # Must NOT be SHORT in a single step
        assert t.state_after != "SHORT"
