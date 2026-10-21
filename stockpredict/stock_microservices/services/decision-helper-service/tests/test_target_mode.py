"""EM-8 M3 — question (c), re-scoped by what the code turned out to do.

The plan asked: *should a measured objective be a target at all?* It specified
three backtest arms — `MEASURED_FIRST`, `NO_MEASURED`, `TRAILING_ONLY` — and
expected the first two to differ.

**They cannot.** `MEASURED_MOVE` has never fired, in either path:

* `target_module.compute_target` reads `measured_move_target` out of
  `signal_evidence`, i.e. out of a `RawSignal`;
* **no shipped signal detector puts that key in evidence** — the full set of
  keys across `signal/trend/` and `signal/range/` does not contain it;
* the only producer is ai-insights, and `orchestrator.py:179` hands those
  patterns to the **failed-signal detectors** instead, which its own comment
  at `:118` says outright;
* measured: **4,193 of 4,193** target computations over 12 symbols and 11
  years carried no such key, and `MEASURED_MOVE` was **0%** of chosen targets
  (FIXED_RR 68%, SR_LEVEL 32%).

This is the `#73` shape in a new place — *"the five pattern detectors in this
module had never fired once"* — and it means question (c) cannot be answered
for `MEASURED_MOVE` by measurement: there is no behaviour to compare.

So the measurable half of (c) is what remains, and it is E&M's actual Ch 32
claim: the book *"prefers nearby progressive stops for taking profits over
limit orders"*. Targets do fire here, via S/R and fixed R:R — 25.3% of exits
are TARGET_HIT — so **targets-on versus a pure trailing stop** is a real
question with a real answer.

These tests keep the dead path dead-by-record rather than dead-by-accident,
the way `#78`'s whitelist and `#89`'s registry do.
"""
from __future__ import annotations

import inspect
import re
from datetime import date, timedelta
from typing import List

import pytest

from app.services.backtest.harness import BacktestConfig, run_backtest_on_bars
from app.services.risk.target_module import compute_target
from app.services.signal.base import OHLCVBar


# ---------------------------------------------------------------------------
# the dead path, recorded structurally
# ---------------------------------------------------------------------------

#: Every module that builds a RawSignal the orchestrator or harness can act on.
SIGNAL_MODULES = (
    "app.services.signal.trend.ma_cross",
    "app.services.signal.trend.midtrend",
    "app.services.signal.range.sr_bounce_breakout",
)


class TestMeasuredMoveIsUnreachable:

    def test_no_signal_detector_emits_a_measured_move_target(self):
        """If a detector ever starts supplying one, this test fails and the
        next reader learns that `MEASURED_MOVE` has become live — which is the
        point of asserting it rather than noting it in a comment."""
        import importlib
        offenders = []
        for name in SIGNAL_MODULES:
            src = inspect.getsource(importlib.import_module(name))
            if "measured_move_target" in src:
                offenders.append(name)
        assert offenders == [], (
            f"{offenders} now emit measured_move_target: MEASURED_MOVE is "
            f"reachable, so EM-8's question (c) has become answerable and the "
            f"backtest A/B in docs/implementation_plan_em8_measuring.md M3 "
            f"should be built after all."
        )

    def test_the_branch_itself_still_works_when_handed_the_key(self):
        """The code is dead, not broken. Given the evidence it expects, it
        does the right thing — which is why this is a wiring question and not
        a bug in `target_module`."""
        res = compute_target(
            direction="LONG", entry_price=100.0, stop_price=95.0,
            signal_kind="N_DAY_BREAKOUT",
            signal_evidence={"measured_move_target": 120.0},
            sr_levels=None,
        )
        assert res.target_kind == "MEASURED_MOVE"
        assert res.target_price == pytest.approx(120.0)

    def test_the_orchestrator_routes_patterns_to_failed_signals_not_to_targets(self):
        """The reason the path is dead, pinned at its cause."""
        import app.services.decision.orchestrator as orch
        src = inspect.getsource(orch)
        # patterns reach detect_failed_signals...
        assert re.search(r"patterns=patterns_data", src)
        # ...and compute_target is handed the signal's own evidence only.
        assert re.search(r"signal_evidence=best_signal\.evidence", src)


# ---------------------------------------------------------------------------
# the measurable half: targets on, or a pure trailing stop
# ---------------------------------------------------------------------------

def _bars(n: int = 700, seed: float = 100.0) -> List[OHLCVBar]:
    """A series with enough structure to produce trades in both arms."""
    out, price, day = [], seed, date(2018, 1, 1)
    for i in range(n):
        price *= 1.0 + (0.012 if (i // 23) % 2 == 0 else -0.009)
        out.append(OHLCVBar(date=day, open=price, high=price * 1.02,
                            low=price * 0.98, close=price, volume=1_000_000))
        day += timedelta(days=1)
    return out


class TestTargetMode:

    def test_the_default_is_todays_behaviour(self):
        assert BacktestConfig(ticker="X", start_date=date(2020, 1, 1),
                              end_date=date(2021, 1, 1)).target_mode == "TARGETS_ON"

    def test_trailing_only_never_exits_on_a_target(self):
        bars = _bars()
        cfg = BacktestConfig(ticker="X", start_date=bars[300].date,
                             end_date=bars[-1].date, target_mode="TRAILING_ONLY")
        res = run_backtest_on_bars(cfg, bars)
        assert all(t.exit_reason != "TARGET_HIT" for t in res.trade_ledger)

    def test_targets_on_is_byte_identical_to_the_unswitched_pipeline(self):
        """H-M7, the no-op proof: adding the switch must not change what the
        default run does. Asserted on the whole ledger, not a summary."""
        bars = _bars()
        base = BacktestConfig(ticker="X", start_date=bars[300].date,
                              end_date=bars[-1].date)
        on = BacktestConfig(ticker="X", start_date=bars[300].date,
                            end_date=bars[-1].date, target_mode="TARGETS_ON")
        a = run_backtest_on_bars(base, bars).trade_ledger
        b = run_backtest_on_bars(on, bars).trade_ledger
        assert [(t.entry_date, t.exit_date, t.exit_reason, t.net_pnl) for t in a] \
            == [(t.entry_date, t.exit_date, t.exit_reason, t.net_pnl) for t in b]

    def test_an_unknown_mode_is_refused_rather_than_silently_ignored(self):
        bars = _bars()
        cfg = BacktestConfig(ticker="X", start_date=bars[300].date,
                             end_date=bars[-1].date, target_mode="NONSENSE")
        with pytest.raises(ValueError, match="target_mode"):
            run_backtest_on_bars(cfg, bars)

    def test_the_mode_is_recorded_in_the_result_config(self):
        bars = _bars()
        cfg = BacktestConfig(ticker="X", start_date=bars[300].date,
                             end_date=bars[-1].date, target_mode="TRAILING_ONLY")
        assert run_backtest_on_bars(cfg, bars).config["target_mode"] == "TRAILING_ONLY"
