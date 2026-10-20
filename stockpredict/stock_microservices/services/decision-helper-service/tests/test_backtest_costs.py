"""Backlog #80 — transaction costs, accounting, and the churn guards.

EM-9's sweep could not reach a quantitative verdict because the harness's own
cost model dominated every result: commission came to **1.8x the gross P&L it
was supposed to measure**, at a trade every ~2.46 bars. Any A/B run through it
was arbitrated by the fee schedule rather than by the thing under test, which
blocked EM-3 and every other backtest-arbitrated candidate.

Three separate defects sat behind that, and this file pins all three.

**1. The ledger did not reconcile with the equity curve.** A flat
``commission`` was deducted from equity at entry *and* subtracted again inside
``net_pnl`` at close, but ``TradeRecord.commission`` recorded only the exit
leg. So ``total_commission`` reported **half** the fees actually charged and
``total_net_pnl`` was overstated by one leg per trade — a 1,490 gap on a
151-trade replay. The end-of-period force-close then double-charged the entry
leg on top.

**2. The fee model was flat per trade.** Wrong for the market this platform
trades: Vietnamese brokerage is a percentage of turnover, and the sell side
pays a transfer tax on proceeds.

**3. The harness churned.** 66% of trades were closed by the failed-signal
override at a **median holding period of one day**, and 103 of 150 exits were
followed by a new entry on the **same bar** — the position closes, ``pos``
goes FLAT, and the entry block immediately re-opens it because the signal that
justified the first entry is level-triggered and still true.
"""
from __future__ import annotations

import math
import random
from collections import Counter
from datetime import date, timedelta
from typing import List

import pytest

from app.services.backtest.harness import BacktestConfig, run_backtest_on_bars
from app.services.backtest.slippage import trade_cost
from app.services.signal.base import OHLCVBar


def _bars(seed: int = 7, n: int = 700) -> List[OHLCVBar]:
    """A deterministic random walk long enough to prime the indicators."""
    rng = random.Random(seed)
    out: List[OHLCVBar] = []
    price, day = 100.0, date(2021, 1, 1)
    for _ in range(n):
        price *= math.exp(rng.gauss(0, 0.015))
        out.append(OHLCVBar(
            date=day, open=price, high=price * 1.012, low=price * 0.988,
            close=price, volume=1_000_000,
        ))
        day += timedelta(days=1)
    return out


def _run(bars: List[OHLCVBar], **kw):
    cfg = BacktestConfig(
        ticker="SYN", start_date=bars[320].date, end_date=bars[-1].date, **kw
    )
    return cfg, run_backtest_on_bars(cfg, bars)


#: The configuration as it behaved before #80 — flat fee, no guards. Kept so
#: the old model stays expressible and the before/after is measurable rather
#: than remembered.
LEGACY = dict(
    commission=10.0, commission_pct=0.0, sell_tax_pct=0.0,
    reentry_cooldown_bars=0, failed_signal_grace_bars=0,
    # The override was ON before #80; #82 later turned it off by DEFAULT, so
    # it has to be named explicitly here or "legacy" would quietly mean
    # "legacy costs with #82's exit behaviour".
    failed_signal_enabled=True,
)

#: The churn-guard arm: #80's guards with the override still ON, so those
#: tests isolate the COOLDOWN and GRACE WINDOW rather than mixing in #82's
#: decision to drop the override entirely. One test, one variable.
GUARDS_ONLY = dict(failed_signal_enabled=True)


# ---------------------------------------------------------------------------
# The cost function
# ---------------------------------------------------------------------------

class TestTradeCost:

    def test_commission_is_proportional_to_turnover(self):
        a = trade_cost(10_000, "BUY", commission_pct=0.15)
        b = trade_cost(20_000, "BUY", commission_pct=0.15)
        assert b == pytest.approx(2 * a)
        assert a == pytest.approx(15.0)

    def test_the_sell_tax_applies_only_to_disposals(self):
        """VN charges the transfer tax on proceeds, so it is a sell-side cost.
        Charging it on the buy would overstate every round trip by half."""
        buy = trade_cost(10_000, "BUY", commission_pct=0.15, sell_tax_pct=0.10)
        sell = trade_cost(10_000, "SELL", commission_pct=0.15, sell_tax_pct=0.10)
        assert buy == pytest.approx(15.0)
        assert sell == pytest.approx(25.0)

    def test_a_short_entry_is_a_buy_side_cost_and_a_cover_is_a_sell_side_one(self):
        assert trade_cost(10_000, "SELL_SHORT", commission_pct=0.1, sell_tax_pct=0.1) \
            == pytest.approx(10.0)
        assert trade_cost(10_000, "COVER", commission_pct=0.1, sell_tax_pct=0.1) \
            == pytest.approx(20.0)

    def test_the_old_flat_model_is_still_expressible(self):
        """So the before/after can be *measured* rather than remembered, and
        so a broker with a genuine flat fee can still be configured."""
        assert trade_cost(50_000, "BUY", commission_pct=0.0, flat_fee=10.0) \
            == pytest.approx(10.0)

    def test_costs_are_never_negative(self):
        for notional in (0.0, -5.0, 1_000.0):
            for side in ("BUY", "SELL"):
                assert trade_cost(notional, side, commission_pct=-1.0, sell_tax_pct=-1.0) >= 0.0


# ---------------------------------------------------------------------------
# Defect 1 — the ledger must reconcile with the equity curve
# ---------------------------------------------------------------------------

class TestAccountingReconciles:

    @pytest.mark.parametrize("kw", [{}, LEGACY], ids=["new", "legacy"])
    def test_every_trades_net_equals_gross_minus_its_round_trip_cost(self, kw):
        _, res = _run(_bars(), **kw)
        assert res.trade_ledger
        for t in res.trade_ledger:
            assert t.net_pnl == pytest.approx(t.gross_pnl - t.commission, abs=0.01)

    @pytest.mark.parametrize("kw", [{}, LEGACY], ids=["new", "legacy"])
    def test_the_reported_totals_reconcile(self, kw):
        """``total_commission`` used to report only the exit leg while equity
        was charged both, so the headline net was overstated by one leg per
        trade. These three numbers must now describe one set of books."""
        _, res = _run(_bars(), **kw)
        s = res.stats
        ledger_gross = sum(t.gross_pnl or 0 for t in res.trade_ledger)
        ledger_cost = sum(t.commission for t in res.trade_ledger)
        ledger_net = sum(t.net_pnl or 0 for t in res.trade_ledger)

        assert s.total_gross_pnl == pytest.approx(ledger_gross, abs=0.01)
        assert s.total_commission == pytest.approx(ledger_cost, abs=0.01)
        assert s.total_net_pnl == pytest.approx(ledger_net, abs=0.01)
        assert s.total_net_pnl == pytest.approx(
            s.total_gross_pnl - s.total_commission, abs=0.05
        )

    def test_the_round_trip_cost_covers_both_legs(self):
        """One leg per trade used to go missing from the ledger entirely."""
        _, res = _run(_bars(), commission=10.0, commission_pct=0.0, sell_tax_pct=0.0)
        for t in res.trade_ledger:
            assert t.commission == pytest.approx(20.0), (
                "a flat 10 per SIDE must bill 20 for a round trip"
            )


# ---------------------------------------------------------------------------
# Defect 2 — costs scale with what is actually traded
# ---------------------------------------------------------------------------

class TestCostsAreProportional:

    def test_bigger_accounts_pay_bigger_fees(self):
        """The flat model charged a 10,000 account and a 1,000,000 one the
        same 10 per trade, which is what let fees look negligible at size and
        ruinous at small size — neither of them true."""
        _, small = _run(_bars(), initial_equity=50_000.0)
        _, large = _run(_bars(), initial_equity=500_000.0)
        if small.stats.num_trades and large.stats.num_trades:
            small_per_trade = small.stats.total_commission / small.stats.num_trades
            large_per_trade = large.stats.total_commission / large.stats.num_trades
            assert large_per_trade > small_per_trade * 2

    def test_zero_rates_mean_zero_cost(self):
        _, res = _run(_bars(), commission=0.0, commission_pct=0.0, sell_tax_pct=0.0)
        assert res.stats.total_commission == pytest.approx(0.0)
        assert res.stats.total_net_pnl == pytest.approx(res.stats.total_gross_pnl, abs=0.05)

    def test_the_config_is_echoed_so_a_result_states_its_own_cost_model(self):
        """A stored result must say what it was charged, or it cannot be
        compared with another one later."""
        _, res = _run(_bars())
        for key in ("commission", "commission_pct", "sell_tax_pct",
                    "reentry_cooldown_bars", "failed_signal_grace_bars"):
            assert key in res.config


# ---------------------------------------------------------------------------
# Defect 3 — the churn guards
# ---------------------------------------------------------------------------

class TestChurnGuards:

    def test_no_entry_on_the_bar_a_position_closed(self):
        """103 of 150 exits used to be followed by a new entry on the same
        bar. The position closes, `pos` goes FLAT, and the entry block
        re-opens it immediately because the signal is level-triggered and
        still true."""
        _, res = _run(_bars())
        ledger = res.trade_ledger
        same_bar = [
            i for i in range(len(ledger) - 1)
            if ledger[i].exit_date and ledger[i + 1].entry_date == ledger[i].exit_date
        ]
        assert not same_bar, f"{len(same_bar)} re-entries on the exit bar"

    def test_the_cooldown_can_be_switched_off(self):
        """The old behaviour stays reachable, so the change is a default and
        not a silent redefinition."""
        _, res = _run(_bars(), **LEGACY)
        ledger = res.trade_ledger
        same_bar = [
            i for i in range(len(ledger) - 1)
            if ledger[i].exit_date and ledger[i + 1].entry_date == ledger[i].exit_date
        ]
        assert same_bar, "legacy config should still re-enter on the exit bar"

    def test_the_failed_signal_override_cannot_fire_in_its_grace_window(self):
        """It closed 66% of trades at a median holding period of ONE day: the
        confirmation layer approved an entry on bar N and the failed-signal
        detector declared it failed on bar N+1. Backlog #79 separately found
        those verdicts predict nothing."""
        _, res = _run(_bars(), failed_signal_enabled=True, failed_signal_grace_bars=3)
        for t in res.trade_ledger:
            if t.exit_reason == "FAILED_SIGNAL" and t.exit_date:
                held = (t.exit_date - t.entry_date).days
                assert held >= 3, f"failed-signal exit after {held} day(s)"

    def test_the_guards_cut_turnover_materially(self):
        """The headline of #80: the harness must stop trading so often that
        its own cost model is the dominant term."""
        bars = _bars()
        _, legacy = _run(bars, **LEGACY)
        _, now = _run(bars, **GUARDS_ONLY)
        assert now.stats.num_trades < legacy.stats.num_trades * 0.75, (
            f"turnover barely moved: {legacy.stats.num_trades} -> "
            f"{now.stats.num_trades}"
        )

    def test_the_rate_of_failed_signal_exits_falls(self):
        """Measured per bar, not as a share — and the distinction is a
        finding rather than a technicality.

        The guards roughly halve the number of failed-signal exits over the
        same window (99 -> 51 on the reference replay). They do **not** change
        its *share*: it was 66% of exits before and is 66% after, because the
        cooldown removes trades roughly uniformly across every exit reason
        rather than selectively removing the pathological ones.

        So the override remains the dominant way a position ends, and the
        grace window only postpones it. Together with Backlog #79 — which
        found these verdicts predict nothing — that is a question about
        whether the override belongs in the harness at all, logged separately
        rather than tuned away here.
        """
        bars = _bars()
        _, legacy = _run(bars, **LEGACY)
        _, now = _run(bars, **GUARDS_ONLY)

        legacy_n = Counter(t.exit_reason for t in legacy.trade_ledger)["FAILED_SIGNAL"]
        now_n = Counter(t.exit_reason for t in now.trade_ledger)["FAILED_SIGNAL"]
        assert now_n < legacy_n * 0.75, f"{legacy_n} -> {now_n}"

    def test_positions_are_held_longer(self):
        """The median holding period was ONE day. A trade sized for an ATR
        stop that is closed the next bar by a different component was never
        given the chance the sizing assumed."""
        bars = _bars()

        def median_hold(res):
            holds = sorted(
                (t.exit_date - t.entry_date).days
                for t in res.trade_ledger if t.exit_date
            )
            return holds[len(holds) // 2]

        _, legacy = _run(bars, **LEGACY)
        _, now = _run(bars, **GUARDS_ONLY)
        assert median_hold(now) > median_hold(legacy)


# ---------------------------------------------------------------------------
# The thing #80 exists to make possible
# ---------------------------------------------------------------------------

class TestTheHarnessCanArbitrateAnAB:

    def test_two_arms_differing_only_in_a_parameter_are_comparable(self):
        """EM-3 and every other backtest-arbitrated candidate needs this: two
        runs that differ in one parameter must differ in their *results*, and
        both must keep books that reconcile. The cost model may be large, but
        it must be the same on both sides and must not hide the difference.
        """
        bars = _bars()
        _, a = _run(bars, breakout_n=20)
        _, b = _run(bars, breakout_n=60)

        assert (a.stats.num_trades, a.stats.total_gross_pnl) != \
               (b.stats.num_trades, b.stats.total_gross_pnl)
        for res in (a, b):
            assert res.stats.total_net_pnl == pytest.approx(
                res.stats.total_gross_pnl - res.stats.total_commission, abs=0.05
            )


# ---------------------------------------------------------------------------
# Backlog #82 — the failed-signal override, measured and dropped
# ---------------------------------------------------------------------------

class TestFailedSignalOverrideIsOffByDefault:
    """#80 found this override closing 66% of trades at a median hold of one
    day. #82 then measured whether it earns that, against a criterion fixed
    before the run: *gross P&L per trade must be higher with it on*.

    It is not — −20.46 with it on against −11.81 with it off over 12 real VN
    symbols, Welch t = −0.44, so no better and probably worse while ending
    almost two thirds of every position. The study is
    `tests/failed_signal_override_study.py` and the write-up is
    `docs/backlog82_failed_signal_override.md`.

    Gross and per-trade for the reason #80 established: at ~3x fees an arm
    wins on net purely by trading less, and switching the override off reduces
    turnover by construction, so net and totals would both have flattered the
    answer automatically.
    """

    def test_the_backtest_default_is_off(self):
        assert BacktestConfig(
            ticker="X", start_date=date(2021, 1, 1), end_date=date(2021, 12, 31),
        ).failed_signal_enabled is False

    def test_no_trade_is_closed_by_the_override_under_the_default(self):
        _, res = _run(_bars())
        assert res.trade_ledger
        assert not [t for t in res.trade_ledger if t.exit_reason == "FAILED_SIGNAL"]

    def test_it_can_still_be_switched_on(self):
        """The finding is a default, not a deletion — the override is still
        reachable, so the measurement can be repeated and a different market
        or signal set can reach a different answer."""
        _, res = _run(_bars(), failed_signal_enabled=True, failed_signal_grace_bars=0)
        assert [t for t in res.trade_ledger if t.exit_reason == "FAILED_SIGNAL"]

    def test_positions_now_end_where_their_sizing_assumed(self):
        """The clinching secondary reading. A trade sized for an ATR stop
        should be decided by that stop, not pre-empted by another component."""
        _, res = _run(_bars())
        reasons = Counter(t.exit_reason for t in res.trade_ledger)
        decided_by_plan = reasons["STOP_HIT"] + reasons["TARGET_HIT"]
        assert decided_by_plan / sum(reasons.values()) > 0.9

    def test_the_live_recommendation_path_is_untouched(self):
        """#82 is scoped to the harness. The live orchestrator still consults
        these verdicts; changing user-visible recommendations needs its own
        decision (Backlog #83)."""
        import inspect

        from app.services.decision import orchestrator

        src = inspect.getsource(orchestrator)
        assert "detect_failed_signals" in src
        assert "failed_signal_enabled" not in src


# ---------------------------------------------------------------------------
# Backlog #84 — the walk-forward must carry the whole config
# ---------------------------------------------------------------------------

class TestWalkForwardForwardsEveryConfigField:
    """A silent no-op class of bug, caught at #84.

    `run_walk_forward` used to copy `BacktestConfig` field by field, and had
    fallen **five fields behind**: EM-3's `trailing_stop_mode`,
    `basing_point_filter_pct` and `basing_point_new_high_rule`, plus F-043's
    `allow_pyramiding` and `max_pyramid_fraction`, which predate it.

    A walk-forward comparing two stop rules would therefore have run the
    DEFAULT rule in both arms and reported no difference — the same shape of
    failure as a sweep that patches a bound default argument, and it would
    have read as "the rule does not work out of sample" rather than "the
    harness never applied it".
    """

    def test_no_field_is_dropped(self):
        import dataclasses

        from app.services.backtest.walk_forward import (
            WalkForwardConfig,
            run_walk_forward,
        )

        bars = _bars()
        base = BacktestConfig(
            ticker="SYN",
            start_date=bars[330].date,
            end_date=bars[-1].date,
            # deliberately non-default on every field a window could drop
            trailing_stop_mode="BASING_POINT",
            basing_point_filter_pct=9.5,
            basing_point_new_high_rule=True,
            allow_pyramiding=True,
            max_pyramid_fraction=0.25,
            commission_pct=0.33,
            sell_tax_pct=0.05,
            reentry_cooldown_bars=4,
            failed_signal_grace_bars=7,
            failed_signal_enabled=True,
        )

        seen: list = []
        import app.services.backtest.walk_forward as wf

        original = wf.run_backtest_on_bars

        def spy(config, bars_arg):
            seen.append(config)
            return original(config, bars_arg)

        wf.run_backtest_on_bars = spy
        try:
            run_walk_forward(base, bars, WalkForwardConfig(wf_window_days=90))
        finally:
            wf.run_backtest_on_bars = original

        assert seen, "no window ran"
        skip = {"start_date", "end_date"}
        for window_config in seen:
            for f in dataclasses.fields(BacktestConfig):
                if f.name in skip:
                    continue
                assert getattr(window_config, f.name) == getattr(base, f.name), (
                    f"walk-forward dropped {f.name}: window has "
                    f"{getattr(window_config, f.name)!r}, base has "
                    f"{getattr(base, f.name)!r}"
                )
