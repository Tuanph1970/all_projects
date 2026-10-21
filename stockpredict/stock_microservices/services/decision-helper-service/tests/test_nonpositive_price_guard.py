"""A non-positive price is not a price — found by EM-8 M3 (Backlog #93).

The M3 study crashed 21 symbols into a 92-symbol run:

    stop_module.py:147  risk = abs(entry_price - stop_price) / entry_price
    ZeroDivisionError: float division by zero

The vendor serves **13 bars with a zero or negative price** across 320,237
(VGC, GEX, NT2 x8, SCS, HHV x2). `_chart_stop` and `_swing_stop` both divide
by `entry_price` with no guard, so one bad bar takes down the whole pipeline —
and this is shipped code on the live path, not study code: a feed hiccup
returning 0 would do the same thing in production.

Two guards, at the two places that each own part of the problem:

* **`stop_module`** must not divide by a non-positive price. It cannot compute
  a risk fraction there, so those stop kinds simply decline.
* **the harness** must not open a position at a non-positive price at all.
  That is the real error — the stop is only where it surfaced.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import List

from app.services.backtest.harness import BacktestConfig, run_backtest_on_bars
from app.services.risk.stop_module import compute_initial_stop
from app.services.signal.base import OHLCVBar

#: Close enough to entry that the chart stop is inside MAX_RISK_PCT (5%);
#: a support at 90 implies 11.8% risk and is correctly declined, which is what
#: the first draft of this file got wrong.
SR = {
    "supports": [{"price": 97.0, "type": "support", "strength": 3}],
    "resistances": [{"price": 103.0, "type": "resistance", "strength": 3}],
}

#: What the crash actually needed. `compute_sr_levels` derives levels FROM the
#: bars, so a zero-price bar yields zero/negative levels -- and then the
#: candidate filter passes and the division happens. A fixture with healthy
#: levels never reaches line 147 at all.
SR_DEGENERATE = {
    "supports": [{"price": -1.0, "type": "support", "strength": 3}],
    "resistances": [{"price": 1.0, "type": "resistance", "strength": 3}],
}
SWINGS = [{"date": "2020-01-01", "type": "low", "price": 92.0},
          {"date": "2020-02-01", "type": "high", "price": 108.0}]


class TestStopModuleSurvivesANonPrice:

    def test_a_zero_entry_price_does_not_raise(self):
        """The exact shape that crashed the M3 run: a zero price alongside
        levels derived from the same bad bars."""
        res = compute_initial_stop(direction="LONG", entry_price=0.0, atr=1.0,
                                   swings=SWINGS, sr_levels=SR_DEGENERATE)
        assert res is not None

    def test_a_negative_entry_price_does_not_raise(self):
        res = compute_initial_stop(direction="SHORT", entry_price=-5.0, atr=1.0,
                                   swings=SWINGS, sr_levels=SR_DEGENERATE)
        assert res is not None

    def test_the_chart_and_swing_stops_decline_rather_than_guess(self):
        """They need a risk FRACTION of the entry price, which does not exist
        at zero — so they must abstain, not invent one."""
        res = compute_initial_stop(direction="LONG", entry_price=0.0, atr=1.0,
                                   swings=SWINGS, sr_levels=SR_DEGENERATE)
        assert res.stop_kind not in ("CHART", "SWING")

    def test_a_normal_price_is_unaffected(self):
        """The guard must not change the behaviour it was added beneath."""
        res = compute_initial_stop(direction="LONG", entry_price=100.0, atr=1.0,
                                   swings=SWINGS, sr_levels=SR)
        assert res.stop_kind == "CHART"


def _bars_with_a_bad_bar(bad_index: int = 420, n: int = 700) -> List[OHLCVBar]:
    out, price, day = [], 100.0, date(2018, 1, 1)
    for i in range(n):
        price *= 1.0 + (0.012 if (i // 23) % 2 == 0 else -0.009)
        p = 0.0 if i == bad_index else price
        out.append(OHLCVBar(date=day, open=p, high=p, low=p, close=p,
                            volume=1_000_000))
        day += timedelta(days=1)
    return out


class TestTheHarnessSkipsANonPrice:

    def test_a_single_zero_bar_does_not_crash_the_replay(self):
        bars = _bars_with_a_bad_bar()
        cfg = BacktestConfig(ticker="X", start_date=bars[300].date,
                             end_date=bars[-1].date)
        res = run_backtest_on_bars(cfg, bars)      # must not raise
        assert res is not None

    def test_no_trade_is_ever_opened_at_a_non_positive_price(self):
        bars = _bars_with_a_bad_bar()
        cfg = BacktestConfig(ticker="X", start_date=bars[300].date,
                             end_date=bars[-1].date)
        res = run_backtest_on_bars(cfg, bars)
        assert all(t.entry_price > 0 for t in res.trade_ledger)

    def test_a_clean_series_is_unaffected(self):
        clean = _bars_with_a_bad_bar(bad_index=-1)
        cfg = BacktestConfig(ticker="X", start_date=clean[300].date,
                             end_date=clean[-1].date)
        assert run_backtest_on_bars(cfg, clean) is not None
