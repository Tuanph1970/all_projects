"""Tests for Phase F — Backtest / Walk-Forward Harness (F-050..F-052)."""
from __future__ import annotations

import math
from datetime import date, timedelta
from typing import List

import pytest

from app.services.backtest.slippage import apply_slippage
from app.services.backtest.market_features import (
    compute_atr,
    compute_regime,
    compute_rsi,
    compute_sr_levels,
    compute_swings,
)
from app.services.backtest.harness import (
    BacktestConfig,
    BacktestResult,
    BacktestStats,
    EquityPoint,
    TradeRecord,
    _Position,
    _check_exit,
    _close_trade,
    _compute_stats,
    _empty_stats,
    run_backtest_on_bars,
)
from app.services.backtest.walk_forward import (
    WalkForwardConfig,
    WalkForwardWindow,
    _aggregate,
    run_walk_forward,
)
from app.services.signal.base import OHLCVBar


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _bar(d: date, o: float, h: float, l: float, c: float, v: int = 1_000_000) -> OHLCVBar:
    return OHLCVBar(date=d, open=o, high=h, low=l, close=c, volume=v)


def _flat_bars(n: int, price: float = 100.0, start: date = date(2023, 1, 2)) -> List[OHLCVBar]:
    """N bars with tiny noise — essentially flat price."""
    bars = []
    for i in range(n):
        d = start + timedelta(days=i)
        bars.append(_bar(d, price, price + 0.1, price - 0.1, price))
    return bars


def _trend_bars(
    n: int,
    step: float = 0.5,
    start_price: float = 80.0,
    start: date = date(2022, 1, 3),
) -> List[OHLCVBar]:
    """N steadily rising bars — produces TREND_UP regime after warmup."""
    bars = []
    price = start_price
    for i in range(n):
        d = start + timedelta(days=i)
        bars.append(_bar(d, price, price + step, price - 0.1, price + step))
        price += step
    return bars


# ---------------------------------------------------------------------------
# F-052 — Slippage model
# ---------------------------------------------------------------------------

class TestApplySlippage:
    def test_buy_pays_more(self):
        fill = apply_slippage(100.0, "BUY", 5.0)
        assert fill == pytest.approx(100.05, rel=1e-6)

    def test_sell_short_pays_more(self):
        fill = apply_slippage(100.0, "SELL_SHORT", 5.0)
        assert fill == pytest.approx(100.05, rel=1e-6)

    def test_sell_receives_less(self):
        fill = apply_slippage(100.0, "SELL", 5.0)
        assert fill == pytest.approx(99.95, rel=1e-6)

    def test_cover_receives_less(self):
        fill = apply_slippage(100.0, "COVER", 5.0)
        assert fill == pytest.approx(99.95, rel=1e-6)

    def test_zero_bps_is_no_op(self):
        assert apply_slippage(100.0, "BUY", 0.0) == 100.0
        assert apply_slippage(100.0, "SELL", 0.0) == 100.0

    def test_large_bps_still_consistent(self):
        price = 50.0
        bps = 100.0  # 1%
        fill_buy = apply_slippage(price, "BUY", bps)
        fill_sell = apply_slippage(price, "SELL", bps)
        assert fill_buy > price
        assert fill_sell < price
        assert fill_buy == pytest.approx(price * 1.01, rel=1e-6)
        assert fill_sell == pytest.approx(price * 0.99, rel=1e-6)


# ---------------------------------------------------------------------------
# Inline market features
# ---------------------------------------------------------------------------

class TestComputeRegime:
    def test_insufficient_bars_returns_undefined(self):
        bars = _flat_bars(30)
        assert compute_regime(bars) == "UNDEFINED"

    def test_rising_prices_returns_trend_up(self):
        bars = _trend_bars(100, step=1.0)
        assert compute_regime(bars) == "TREND_UP"

    def test_falling_prices_returns_trend_down(self):
        bars = _trend_bars(100, step=-1.0, start_price=200.0)
        assert compute_regime(bars) == "TREND_DOWN"

    def test_flat_prices_returns_range(self):
        bars = _flat_bars(100)
        assert compute_regime(bars) == "RANGE"

    def test_custom_fast_slow(self):
        bars = _trend_bars(100, step=0.5)
        result = compute_regime(bars, fast=10, slow=30)
        assert result in ("TREND_UP", "RANGE")


class TestComputeATR:
    def test_insufficient_bars_returns_none(self):
        bars = _flat_bars(5)
        assert compute_atr(bars, period=14) is None

    def test_returns_float_with_enough_bars(self):
        bars = _flat_bars(30)
        atr = compute_atr(bars, period=14)
        assert isinstance(atr, float)
        assert atr >= 0

    def test_wider_range_gives_larger_atr(self):
        narrow_bars = [_bar(date(2023, 1, 1) + timedelta(i), 100, 101, 99, 100) for i in range(30)]
        wide_bars = [_bar(date(2023, 1, 1) + timedelta(i), 100, 105, 95, 100) for i in range(30)]
        assert compute_atr(wide_bars) > compute_atr(narrow_bars)


class TestComputeRSI:
    def test_insufficient_bars_returns_none(self):
        bars = _flat_bars(5)
        assert compute_rsi(bars, period=14) is None

    def test_all_up_days_returns_100(self):
        bars = _trend_bars(30, step=1.0)
        rsi = compute_rsi(bars, period=14)
        assert rsi == 100.0

    def test_returns_value_between_0_and_100(self):
        import random
        random.seed(42)
        bars = []
        price = 100.0
        for i in range(30):
            price += random.uniform(-1, 1)
            d = date(2023, 1, 2) + timedelta(i)
            bars.append(_bar(d, price, price + 0.5, price - 0.5, price))
        rsi = compute_rsi(bars)
        assert rsi is not None
        assert 0 <= rsi <= 100


class TestComputeSwings:
    def test_empty_bars(self):
        assert compute_swings([]) == []

    def test_detects_pivots_in_v_shape(self):
        # build a V-shape: down then up
        bars = []
        for i, price in enumerate([10, 9, 8, 7, 6, 7, 8, 9, 10, 11]):
            bars.append(_bar(date(2023, 1, 2) + timedelta(i), price, price + 0.1, price - 0.1, price))
        pivots = compute_swings(bars, window=2)
        kinds = {p["kind"] for p in pivots}
        # Should detect at least a LOW pivot at the V-bottom
        assert "LOW" in kinds

    def test_returns_at_most_40(self):
        bars = _flat_bars(200)
        pivots = compute_swings(bars)
        assert len(pivots) <= 40


class TestComputeSRLevels:
    def test_returns_dict_with_support_resistance(self):
        bars = _flat_bars(50)
        result = compute_sr_levels(bars)
        assert "supports" in result
        assert "resistances" in result

    def test_max_levels_respected(self):
        bars = _trend_bars(60)
        result = compute_sr_levels(bars, max_levels=3)
        assert len(result["supports"]) <= 3
        assert len(result["resistances"]) <= 3


# ---------------------------------------------------------------------------
# Harness internals
# ---------------------------------------------------------------------------

class TestCheckExit:
    def _long_pos(self, stop=90.0, target=110.0):
        pos = _Position(state="LONG", direction="LONG", entry_price=100.0, stop=stop, target=target, shares=10)
        return pos

    def _short_pos(self, stop=110.0, target=90.0):
        pos = _Position(state="SHORT", direction="SHORT", entry_price=100.0, stop=stop, target=target, shares=10)
        return pos

    def test_flat_pos_never_exits(self):
        flat = _Position()
        bar = _bar(date(2023, 1, 2), 100, 105, 95, 102)
        exited, price, reason = _check_exit(bar, flat)
        assert not exited

    def test_long_stop_hit(self):
        pos = self._long_pos(stop=95.0)
        bar = _bar(date(2023, 1, 2), 100, 100, 90, 93)   # low=90 < stop=95
        exited, price, reason = _check_exit(bar, pos)
        assert exited and reason == "STOP_HIT" and price == 95.0

    def test_long_target_hit(self):
        pos = self._long_pos(target=105.0)
        bar = _bar(date(2023, 1, 2), 100, 110, 99, 108)  # high=110 > target=105
        exited, price, reason = _check_exit(bar, pos)
        assert exited and reason == "TARGET_HIT" and price == 105.0

    def test_long_stop_beats_target_in_same_bar(self):
        pos = self._long_pos(stop=95.0, target=105.0)
        # Both stop and target touched — stop wins (evaluated first)
        bar = _bar(date(2023, 1, 2), 100, 110, 90, 100)
        exited, price, reason = _check_exit(bar, pos)
        assert exited and reason == "STOP_HIT"

    def test_long_no_exit_when_price_in_range(self):
        pos = self._long_pos(stop=90.0, target=110.0)
        bar = _bar(date(2023, 1, 2), 100, 105, 95, 102)  # within range
        exited, _, _ = _check_exit(bar, pos)
        assert not exited

    def test_short_stop_hit(self):
        pos = self._short_pos(stop=105.0)
        bar = _bar(date(2023, 1, 2), 100, 110, 99, 107)  # high=110 > stop=105
        exited, price, reason = _check_exit(bar, pos)
        assert exited and reason == "STOP_HIT" and price == 105.0

    def test_short_target_hit(self):
        pos = self._short_pos(target=95.0)
        bar = _bar(date(2023, 1, 2), 100, 101, 90, 92)   # low=90 < target=95
        exited, price, reason = _check_exit(bar, pos)
        assert exited and reason == "TARGET_HIT" and price == 95.0


class TestCloseTrade:
    def test_long_winning_trade(self):
        pos = _Position(
            state="LONG", direction="LONG",
            entry_date=date(2023, 1, 2), entry_price=100.0, shares=10
        )
        trade = _close_trade(pos, "TEST", date(2023, 1, 10), 110.0, "TARGET_HIT", 10.0)
        assert trade.gross_pnl == pytest.approx(100.0)   # (110-100)*10
        assert trade.net_pnl == pytest.approx(90.0)      # gross - commission
        assert trade.exit_reason == "TARGET_HIT"

    def test_short_winning_trade(self):
        pos = _Position(
            state="SHORT", direction="SHORT",
            entry_date=date(2023, 1, 2), entry_price=100.0, shares=10
        )
        trade = _close_trade(pos, "TEST", date(2023, 1, 10), 90.0, "TARGET_HIT", 10.0)
        assert trade.gross_pnl == pytest.approx(100.0)   # (100-90)*10
        assert trade.net_pnl == pytest.approx(90.0)

    def test_losing_trade(self):
        pos = _Position(
            state="LONG", direction="LONG",
            entry_date=date(2023, 1, 2), entry_price=100.0, shares=10
        )
        trade = _close_trade(pos, "TEST", date(2023, 1, 10), 95.0, "STOP_HIT", 10.0)
        assert trade.gross_pnl == pytest.approx(-50.0)   # (95-100)*10
        assert trade.net_pnl == pytest.approx(-60.0)     # gross - commission


class TestComputeStats:
    def _make_trade(self, net_pnl: float, gross_pnl: float = None) -> TradeRecord:
        if gross_pnl is None:
            gross_pnl = net_pnl + 10.0
        return TradeRecord(
            ticker="T", direction="LONG",
            entry_date=date(2023, 1, 2), entry_price=100.0,
            exit_date=date(2023, 1, 5), exit_price=105.0,
            shares=10, gross_pnl=gross_pnl, commission=10.0,
            net_pnl=net_pnl, exit_reason="TARGET_HIT",
        )

    def _make_equity_curve(self, values) -> List[EquityPoint]:
        return [
            EquityPoint(date=date(2023, 1, 2) + timedelta(i), equity=v, drawdown_pct=0.0)
            for i, v in enumerate(values)
        ]

    def test_empty_trades_returns_zero_stats(self):
        stats = _compute_stats([], self._make_equity_curve([100_000, 100_000]))
        assert stats.num_trades == 0
        assert stats.win_rate == 0.0
        assert stats.expectancy == 0.0

    def test_all_winners(self):
        trades = [self._make_trade(100.0), self._make_trade(200.0)]
        eq = self._make_equity_curve([100_000, 100_100, 100_300])
        stats = _compute_stats(trades, eq)
        assert stats.num_trades == 2
        assert stats.num_wins == 2
        assert stats.win_rate == 1.0
        assert stats.total_net_pnl == pytest.approx(300.0)

    def test_profit_factor_computed(self):
        wins = [self._make_trade(100.0, 110.0), self._make_trade(50.0, 60.0)]
        losses = [self._make_trade(-80.0, -70.0)]
        eq = self._make_equity_curve([100_000] * 5)
        stats = _compute_stats(wins + losses, eq)
        # gross_wins = 110+60 = 170; gross_losses = 70
        assert stats.profit_factor == pytest.approx(170 / 70, rel=1e-2)

    def test_sharpe_computed_for_sufficient_curve(self):
        # Monotonically rising equity → small std, large Sharpe
        eq = self._make_equity_curve([100_000 + i * 10 for i in range(10)])
        stats = _compute_stats([], eq)
        assert stats.sharpe_ratio is not None
        assert stats.sharpe_ratio > 0


class TestEmptyStats:
    def test_returns_all_zeros(self):
        s = _empty_stats()
        assert s.num_trades == 0
        assert s.sharpe_ratio is None


# ---------------------------------------------------------------------------
# Full harness integration
# ---------------------------------------------------------------------------

class TestRunBacktest:
    def _build_bars(self) -> List[OHLCVBar]:
        """400 warmup + 200 signal bars: flat warmup then a strong uptrend."""
        warmup = _flat_bars(400, price=100.0, start=date(2022, 1, 3))
        trend = _trend_bars(200, step=1.0, start_price=100.0, start=date(2022, 1, 3) + timedelta(400))
        return warmup + trend

    def _config(self, start: date, end: date) -> BacktestConfig:
        return BacktestConfig(
            ticker="TEST",
            start_date=start,
            end_date=end,
            initial_equity=100_000.0,
            risk_per_trade_pct=1.0,
            fast_ma=10,
            slow_ma=50,
            breakout_n=20,
            k_delay=1,
            slippage_bps=5.0,
            commission=10.0,
        )

    def test_returns_backtest_result(self):
        bars = self._build_bars()
        start = date(2022, 1, 3) + timedelta(410)
        end = start + timedelta(50)
        result = run_backtest_on_bars(self._config(start, end), bars)
        assert isinstance(result, BacktestResult)
        assert result.ticker == "TEST"

    def test_equity_curve_has_entries(self):
        bars = self._build_bars()
        start = date(2022, 1, 3) + timedelta(410)
        end = start + timedelta(50)
        result = run_backtest_on_bars(self._config(start, end), bars)
        assert len(result.equity_curve) > 0

    def test_stats_populated(self):
        bars = self._build_bars()
        start = date(2022, 1, 3) + timedelta(410)
        end = start + timedelta(50)
        result = run_backtest_on_bars(self._config(start, end), bars)
        assert isinstance(result.stats, BacktestStats)
        assert result.stats.win_rate >= 0
        assert result.stats.max_drawdown_pct >= 0

    def test_no_bars_in_range_returns_empty(self):
        bars = _flat_bars(10, start=date(2020, 1, 2))
        config = BacktestConfig(
            ticker="X",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 6, 1),
            initial_equity=100_000.0,
        )
        result = run_backtest_on_bars(config, bars)
        assert result.equity_curve == []
        assert result.stats.num_trades == 0

    def test_config_dict_in_result(self):
        bars = self._build_bars()
        start = date(2022, 1, 3) + timedelta(410)
        end = start + timedelta(30)
        config = self._config(start, end)
        result = run_backtest_on_bars(config, bars)
        assert result.config["initial_equity"] == 100_000.0
        assert result.config["slippage_bps"] == 5.0


# ---------------------------------------------------------------------------
# F-051 — Walk-forward
# ---------------------------------------------------------------------------

class TestAggregate:
    def _window(self, net_pnl: float, win_rate: float, dd: float, num_trades: int = 5) -> WalkForwardWindow:
        from app.services.backtest.harness import BacktestStats
        stats = BacktestStats(
            num_trades=num_trades, num_wins=int(win_rate * num_trades),
            win_rate=win_rate, total_gross_pnl=net_pnl + 50,
            total_commission=50.0, total_net_pnl=net_pnl,
            max_drawdown_pct=dd, expectancy=net_pnl / num_trades if num_trades else 0,
            sharpe_ratio=None, profit_factor=None,
        )
        return WalkForwardWindow(
            window_index=0, start_date=date(2023, 1, 1),
            end_date=date(2023, 3, 31), stats=stats, num_trades=num_trades,
        )

    def test_empty_windows_returns_empty_dict(self):
        assert _aggregate([]) == {}

    def test_basic_aggregation(self):
        w1 = self._window(net_pnl=1000.0, win_rate=0.6, dd=0.05)
        w2 = self._window(net_pnl=-500.0, win_rate=0.4, dd=0.10)
        agg = _aggregate([w1, w2])
        assert agg["num_windows"] == 2
        assert agg["total_trades"] == 10
        assert agg["avg_net_pnl"] == pytest.approx(250.0)
        assert agg["avg_win_rate"] == pytest.approx(0.5)
        assert agg["profitable_windows"] == 1

    def test_all_profitable(self):
        windows = [self._window(500.0, 0.6, 0.03) for _ in range(3)]
        agg = _aggregate(windows)
        assert agg["profitable_windows"] == 3

    def test_net_pnl_std_present(self):
        w1 = self._window(100.0, 0.5, 0.05)
        w2 = self._window(900.0, 0.7, 0.03)
        agg = _aggregate([w1, w2])
        assert "net_pnl_std" in agg
        assert agg["net_pnl_std"] > 0


class TestRunWalkForward:
    def _build_bars(self) -> List[OHLCVBar]:
        warmup = _flat_bars(400, start=date(2021, 1, 4))
        trend = _trend_bars(365, step=0.5, start_price=100.0, start=date(2021, 1, 4) + timedelta(400))
        return warmup + trend

    def _config(self) -> BacktestConfig:
        start = date(2021, 1, 4) + timedelta(410)
        end = start + timedelta(270)
        return BacktestConfig(
            ticker="WF",
            start_date=start,
            end_date=end,
            initial_equity=100_000.0,
        )

    def test_produces_multiple_windows(self):
        bars = self._build_bars()
        config = self._config()
        wf_config = WalkForwardConfig(wf_window_days=90)
        result = run_walk_forward(config, bars, wf_config)
        assert len(result.windows) >= 2

    def test_windows_are_non_overlapping(self):
        bars = self._build_bars()
        config = self._config()
        wf_config = WalkForwardConfig(wf_window_days=90)
        result = run_walk_forward(config, bars, wf_config)
        for i in range(1, len(result.windows)):
            assert result.windows[i].start_date > result.windows[i - 1].end_date

    def test_aggregate_stats_present(self):
        bars = self._build_bars()
        config = self._config()
        wf_config = WalkForwardConfig(wf_window_days=90)
        result = run_walk_forward(config, bars, wf_config)
        assert result.aggregate_stats is not None
        assert "num_windows" in result.aggregate_stats
        assert result.aggregate_stats["num_windows"] == len(result.windows)

    def test_each_window_has_stats(self):
        bars = self._build_bars()
        config = self._config()
        wf_config = WalkForwardConfig(wf_window_days=90)
        result = run_walk_forward(config, bars, wf_config)
        for w in result.windows:
            assert isinstance(w.stats, BacktestStats)
            assert w.num_trades >= 0
            assert w.stats.win_rate >= 0.0
