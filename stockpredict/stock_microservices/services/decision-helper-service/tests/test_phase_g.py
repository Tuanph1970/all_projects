"""Tests for Phase G — Discipline overlay (F-060..F-065)."""
from __future__ import annotations

import pytest

from app.services.discipline.checks import (
    DisciplineViolation,
    check_no_averaging_down,
    check_plan_completeness,
    check_stop_widening,
    check_streak_and_drawdown,
    run_all_checks,
)
from app.services.discipline.rules_engine import RuleAdvisory, evaluate_rules


# ---------------------------------------------------------------------------
# F-060 — plan-before-trade
# ---------------------------------------------------------------------------

class TestCheckPlanCompleteness:
    def test_entry_with_stop_and_target_is_ok(self):
        assert check_plan_completeness("BUY", 95.0, 110.0) is None

    def test_buy_without_stop_is_block(self):
        v = check_plan_completeness("BUY", None, 110.0)
        assert v is not None
        assert v.severity == "BLOCK"
        assert v.rule_id == "F-060"
        assert "stop" in v.evidence["missing"]

    def test_sell_short_without_target_is_block(self):
        v = check_plan_completeness("SELL_SHORT", 105.0, None)
        assert v is not None
        assert v.severity == "BLOCK"
        assert "target" in v.evidence["missing"]

    def test_entry_without_both_lists_both(self):
        v = check_plan_completeness("BUY", None, None)
        assert v is not None
        assert "stop" in v.evidence["missing"]
        assert "target" in v.evidence["missing"]

    def test_non_entry_actions_not_checked(self):
        for action in ("SELL", "COVER", "HOLD", "WAIT", "REVERSE"):
            assert check_plan_completeness(action, None, None) is None

    def test_sell_short_with_both_is_ok(self):
        assert check_plan_completeness("SELL_SHORT", 105.0, 90.0) is None


# ---------------------------------------------------------------------------
# F-061 — no averaging down
# ---------------------------------------------------------------------------

class TestCheckNoAveragingDown:
    def test_no_position_never_triggers(self):
        assert check_no_averaging_down("BUY", "FLAT", 100.0, 95.0) is None

    def test_buy_into_profitable_long_is_ok(self):
        assert check_no_averaging_down("BUY", "LONG", 90.0, 100.0) is None

    def test_buy_into_losing_long_warns(self):
        v = check_no_averaging_down("BUY", "LONG", 100.0, 90.0)
        assert v is not None
        assert v.rule_id == "F-061"
        assert v.severity == "WARNING"
        assert v.evidence["loss_pct"] == pytest.approx(10.0, rel=1e-2)

    def test_sell_short_into_losing_short_warns(self):
        v = check_no_averaging_down("SELL_SHORT", "SHORT", 100.0, 110.0)
        assert v is not None
        assert v.rule_id == "F-061"
        assert v.severity == "WARNING"

    def test_sell_short_into_profitable_short_is_ok(self):
        assert check_no_averaging_down("SELL_SHORT", "SHORT", 100.0, 90.0) is None

    def test_missing_prices_returns_none(self):
        assert check_no_averaging_down("BUY", "LONG", None, 90.0) is None
        assert check_no_averaging_down("BUY", "LONG", 100.0, None) is None

    def test_hold_action_never_triggers(self):
        assert check_no_averaging_down("HOLD", "LONG", 100.0, 80.0) is None


# ---------------------------------------------------------------------------
# F-062 — stop widening
# ---------------------------------------------------------------------------

class TestCheckStopWidening:
    def test_non_hold_never_triggers(self):
        for action in ("BUY", "SELL_SHORT", "SELL", "COVER", "WAIT"):
            assert check_stop_widening(action, 90.0, 95.0, "LONG") is None

    def test_long_stop_widened_warns(self):
        v = check_stop_widening("HOLD", 88.0, 92.0, "LONG")
        assert v is not None
        assert v.rule_id == "F-062"
        assert v.severity == "WARNING"
        assert v.evidence["prev_stop"] == pytest.approx(92.0)
        assert v.evidence["proposed_stop"] == pytest.approx(88.0)

    def test_long_stop_tightened_is_ok(self):
        assert check_stop_widening("HOLD", 95.0, 90.0, "LONG") is None

    def test_short_stop_widened_warns(self):
        v = check_stop_widening("HOLD", 108.0, 104.0, "SHORT")
        assert v is not None
        assert v.rule_id == "F-062"
        assert v.severity == "WARNING"

    def test_short_stop_tightened_is_ok(self):
        assert check_stop_widening("HOLD", 102.0, 106.0, "SHORT") is None

    def test_missing_stops_returns_none(self):
        assert check_stop_widening("HOLD", None, 92.0, "LONG") is None
        assert check_stop_widening("HOLD", 90.0, None, "LONG") is None

    def test_missing_direction_returns_none(self):
        assert check_stop_widening("HOLD", 88.0, 92.0, None) is None


# ---------------------------------------------------------------------------
# F-063 — streak / drawdown
# ---------------------------------------------------------------------------

class TestCheckStreakAndDrawdown:
    def test_no_streak_no_drawdown_returns_none(self):
        assert check_streak_and_drawdown(1, 3) is None

    def test_loss_streak_warns(self):
        v = check_streak_and_drawdown(4, 3)
        assert v is not None
        assert v.rule_id == "F-063"
        assert v.severity == "WARNING"
        assert v.evidence["recent_losses"] == 4

    def test_exactly_at_threshold_warns(self):
        v = check_streak_and_drawdown(3, 3)
        assert v is not None

    def test_drawdown_above_20pct_warns(self):
        v = check_streak_and_drawdown(0, 3, current_equity=75_000, peak_equity=100_000)
        assert v is not None
        assert v.rule_id == "F-063"
        assert v.evidence["drawdown_pct"] == pytest.approx(25.0, rel=1e-2)

    def test_drawdown_below_20pct_is_ok(self):
        assert check_streak_and_drawdown(0, 3, current_equity=85_000, peak_equity=100_000) is None

    def test_drawdown_beats_streak_in_same_call(self):
        # Drawdown check runs first; returns drawdown violation (not streak)
        v = check_streak_and_drawdown(5, 3, current_equity=60_000, peak_equity=100_000)
        assert v is not None
        assert "drawdown" in v.message.lower()

    def test_missing_equity_skips_drawdown(self):
        assert check_streak_and_drawdown(0, 3, current_equity=None, peak_equity=100_000) is None
        assert check_streak_and_drawdown(0, 3, current_equity=80_000, peak_equity=None) is None


# ---------------------------------------------------------------------------
# run_all_checks aggregator
# ---------------------------------------------------------------------------

class TestRunAllChecks:
    def test_clean_entry_returns_empty(self):
        violations = run_all_checks(
            action="BUY",
            stop_price=95.0,
            target_price=110.0,
            pos_state="FLAT",
            recent_losses=0,
            loss_streak_threshold=3,
        )
        assert violations == []

    def test_multiple_violations_all_collected(self):
        violations = run_all_checks(
            action="BUY",
            stop_price=None,          # F-060 BLOCK
            target_price=None,        # F-060 BLOCK (same violation)
            pos_state="LONG",
            entry_price=100.0,
            current_price=85.0,       # F-061 WARNING (averaging down)
            recent_losses=5,          # F-063 WARNING (streak)
            loss_streak_threshold=3,
        )
        rule_ids = {v.rule_id for v in violations}
        assert "F-060" in rule_ids
        assert "F-061" in rule_ids
        assert "F-063" in rule_ids

    def test_block_severity_present(self):
        violations = run_all_checks(action="BUY", stop_price=None, target_price=None)
        blocks = [v for v in violations if v.severity == "BLOCK"]
        assert len(blocks) >= 1


# ---------------------------------------------------------------------------
# F-065 — Rules engine
# ---------------------------------------------------------------------------

class TestEvaluateRules:
    def _base_kwargs(self, **overrides):
        defaults = dict(
            action="WAIT",
            stop_price=None,
            target_price=None,
            entry_price=None,
            direction=None,
            regime=None,
            recent_losses=0,
            loss_streak_threshold=3,
            violations=[],
        )
        defaults.update(overrides)
        return defaults

    def test_returns_10_advisories(self):
        advisories = evaluate_rules(**self._base_kwargs())
        assert len(advisories) == 10

    def test_all_have_required_fields(self):
        advisories = evaluate_rules(**self._base_kwargs())
        for a in advisories:
            assert isinstance(a, RuleAdvisory)
            assert a.rule_id.startswith("R-")
            assert a.rule_text
            assert a.chapter
            assert a.severity in ("INFO", "WARNING")

    def test_r01_triggers_when_no_stop_on_entry(self):
        advisories = evaluate_rules(**self._base_kwargs(action="BUY", stop_price=None))
        r01 = next(a for a in advisories if a.rule_id == "R-01")
        assert r01.triggered

    def test_r01_not_triggered_when_stop_present(self):
        advisories = evaluate_rules(**self._base_kwargs(action="BUY", stop_price=95.0))
        r01 = next(a for a in advisories if a.rule_id == "R-01")
        assert not r01.triggered

    def test_r05_triggers_on_loss_streak(self):
        advisories = evaluate_rules(**self._base_kwargs(recent_losses=4, loss_streak_threshold=3))
        r05 = next(a for a in advisories if a.rule_id == "R-05")
        assert r05.triggered
        assert "4" in r05.detail

    def test_r06_triggers_when_rrr_below_1_5(self):
        # risk=2, reward=1 → R:R=0.5 < 1.5
        advisories = evaluate_rules(**self._base_kwargs(
            action="BUY", entry_price=100.0, stop_price=98.0, target_price=101.0
        ))
        r06 = next(a for a in advisories if a.rule_id == "R-06")
        assert r06.triggered

    def test_r06_not_triggered_when_rrr_above_2(self):
        advisories = evaluate_rules(**self._base_kwargs(
            action="BUY", entry_price=100.0, stop_price=97.0, target_price=109.0
        ))
        r06 = next(a for a in advisories if a.rule_id == "R-06")
        assert not r06.triggered

    def test_r08_triggers_when_trading_against_trend(self):
        advisories = evaluate_rules(**self._base_kwargs(
            action="BUY", direction="LONG", regime="TREND_DOWN"
        ))
        r08 = next(a for a in advisories if a.rule_id == "R-08")
        assert r08.triggered

    def test_r08_not_triggered_when_aligned_with_trend(self):
        advisories = evaluate_rules(**self._base_kwargs(
            action="BUY", direction="LONG", regime="TREND_UP"
        ))
        r08 = next(a for a in advisories if a.rule_id == "R-08")
        assert not r08.triggered

    def test_r02_triggers_from_violations(self):
        from app.services.discipline.checks import DisciplineViolation
        v = DisciplineViolation(rule_id="F-061", severity="WARNING", message="x")
        advisories = evaluate_rules(**self._base_kwargs(violations=[v]))
        r02 = next(a for a in advisories if a.rule_id == "R-02")
        assert r02.triggered
