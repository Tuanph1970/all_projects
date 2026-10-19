"""F-051 — Walk-forward train/test split (Schwager Ch 15).

Non-overlapping out-of-sample windows.  Since we do not optimise parameters
in v1, the "train" window is purely contextual (for data warmup); the
"test" window is the OOS period that is actually evaluated.

WalkForwardConfig
-----------------
  wf_window_days : int   — length of each OOS test window in calendar days
  warmup_days    : int   — bars before the OOS window used for indicator warm-up

The full date range is split into N non-overlapping test windows; each runs
the backtest on [start, start + wf_window_days] and advances by that amount.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any, Dict, List, Optional

from app.services.signal.base import OHLCVBar
from app.services.backtest.harness import BacktestConfig, BacktestResult, BacktestStats, run_backtest_on_bars


@dataclass
class WalkForwardConfig:
    wf_window_days: int = 90
    warmup_days: int = 300      # bars before window start to prime indicators


@dataclass
class WalkForwardWindow:
    window_index: int
    start_date: date
    end_date: date
    stats: BacktestStats
    num_trades: int


@dataclass
class WalkForwardResult:
    ticker: str
    full_start: date
    full_end: date
    wf_window_days: int
    windows: List[WalkForwardWindow] = field(default_factory=list)
    aggregate_stats: Optional[Dict[str, Any]] = None


def run_walk_forward(
    base_config: BacktestConfig,
    bars: List[OHLCVBar],
    wf_config: WalkForwardConfig,
) -> WalkForwardResult:
    """Slice [start_date, end_date] into non-overlapping windows and backtest each."""
    result = WalkForwardResult(
        ticker=base_config.ticker,
        full_start=base_config.start_date,
        full_end=base_config.end_date,
        wf_window_days=wf_config.wf_window_days,
    )

    window_start = base_config.start_date
    window_idx = 0

    while window_start < base_config.end_date:
        window_end = min(
            window_start + timedelta(days=wf_config.wf_window_days - 1),
            base_config.end_date,
        )

        # OOS window must have at least 5 calendar days to be meaningful
        if (window_end - window_start).days < 5:
            break

        window_config = BacktestConfig(
            ticker=base_config.ticker,
            start_date=window_start,
            end_date=window_end,
            initial_equity=base_config.initial_equity,
            risk_per_trade_pct=base_config.risk_per_trade_pct,
            fast_ma=base_config.fast_ma,
            slow_ma=base_config.slow_ma,
            breakout_n=base_config.breakout_n,
            k_delay=base_config.k_delay,
            slippage_bps=base_config.slippage_bps,
            commission=base_config.commission,
            commission_pct=base_config.commission_pct,
            sell_tax_pct=base_config.sell_tax_pct,
            reentry_cooldown_bars=base_config.reentry_cooldown_bars,
            failed_signal_grace_bars=base_config.failed_signal_grace_bars,
            failed_signal_enabled=base_config.failed_signal_enabled,
        )

        window_result: BacktestResult = run_backtest_on_bars(window_config, bars)

        result.windows.append(WalkForwardWindow(
            window_index=window_idx,
            start_date=window_start,
            end_date=window_end,
            stats=window_result.stats,
            num_trades=window_result.stats.num_trades,
        ))

        window_start = window_end + timedelta(days=1)
        window_idx += 1

    result.aggregate_stats = _aggregate(result.windows)
    return result


def _aggregate(windows: List[WalkForwardWindow]) -> Dict[str, Any]:
    if not windows:
        return {}
    total_trades = sum(w.num_trades for w in windows)
    all_net_pnls = [w.stats.total_net_pnl for w in windows]
    all_win_rates = [w.stats.win_rate for w in windows if w.num_trades > 0]
    all_max_dds = [w.stats.max_drawdown_pct for w in windows]
    all_expectancies = [w.stats.expectancy for w in windows if w.num_trades > 0]

    import statistics as _stat

    def _safe_stat(lst, fn):
        return round(fn(lst), 4) if len(lst) > 1 else (round(lst[0], 4) if lst else 0.0)

    return {
        "num_windows": len(windows),
        "total_trades": total_trades,
        "avg_net_pnl": round(sum(all_net_pnls) / len(all_net_pnls), 2) if all_net_pnls else 0,
        "net_pnl_std": _safe_stat(all_net_pnls, _stat.stdev),
        "avg_win_rate": round(sum(all_win_rates) / len(all_win_rates), 4) if all_win_rates else 0,
        "win_rate_std": _safe_stat(all_win_rates, _stat.stdev),
        "avg_max_drawdown": round(sum(all_max_dds) / len(all_max_dds), 4) if all_max_dds else 0,
        "avg_expectancy": round(sum(all_expectancies) / len(all_expectancies), 2) if all_expectancies else 0,
        "profitable_windows": sum(1 for w in windows if w.stats.total_net_pnl > 0),
    }
