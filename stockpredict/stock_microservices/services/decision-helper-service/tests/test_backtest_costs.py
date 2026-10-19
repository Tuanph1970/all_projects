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
)


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
        _, res = _run(_bars(), failed_signal_grace_bars=3)
        for t in res.trade_ledger:
            if t.exit_reason == "FAILED_SIGNAL" and t.exit_date:
                held = (t.exit_date - t.entry_date).days
                assert held >= 3, f"failed-signal exit after {held} day(s)"

    def test_the_guards_cut_turnover_materially(self):
        """The headline of #80: the harness must stop trading so often that
        its own cost model is the dominant term."""
        bars = _bars()
        _, legacy = _run(bars, **LEGACY)
        _, now = _run(bars)
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
        _, now = _run(bars)

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
        _, now = _run(bars)
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
