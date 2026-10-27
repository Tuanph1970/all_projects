"""Backlog #84(a) — EM-3's walk-forward confirmation, and the filter sweep.

    PYTHONPATH=. python3 tests/em3_walk_forward_study.py

What a walk-forward means for THIS rule
---------------------------------------
Nothing in the basing-point rule is fitted. Three days clear, a 6% filter and
a 3% new-high threshold all come from Edwards & Magee, fixed a priori. So this
is **not** a test for parameter overfitting — there are no parameters to
overfit. It tests **temporal stability**: does the effect hold window after
window, or was yesterday's pooled result carried by one lucky stretch?

That is the meaningful reading of `C4`'s "out-of-sample" for a parameter-free
rule, and it is worth stating because the usual reason for a walk-forward does
not apply here.

Why paired, and why this is stronger than yesterday's run
---------------------------------------------------------
Yesterday's A/B pooled every trade from both arms and ran a Welch t: +39.31 at
t = +2.02, marginal. Pooling carries all the between-period variance — a
quiet year and a crash year sit in the same variance term.

Here the two arms run on the **same window**, so each window gives a *paired*
difference and the between-window variance drops out. A paired t across
windows plus a sign test on how many windows the rule wins is both a tighter
statistic and a direct read on stability.

CRITERION, FIXED BEFORE THE RUN
-------------------------------
Both of these, or EM-3 does not clear `C4`:

  1. the basing-point arm wins a MAJORITY of windows on gross P&L per trade,
     and the sign test on window wins is significant; and
  2. the PAIRED mean difference across windows is positive and significant.

Gross and per-trade, per `#80`: at ~3x fees an arm wins on net purely by
trading less, and a wider stop holds positions longer by construction.

Part (b), the filter sweep, is a ROBUSTNESS check and not a tuning exercise.
The question is whether the result survives across 4-12%, not which value is
highest. Picking the maximum would be choosing a parameter after seeing the
data, which is what this workstream has spent nine tasks avoiding.
"""
from __future__ import annotations

import math
from typing import Dict, List, Optional, Tuple

from app.services.backtest.harness import BacktestConfig, run_backtest_on_bars

from tests.failed_signal_override_study import WARMUP, load_bars

WINDOW_DAYS = 180          # ~6 months of calendar days per OOS window
MAX_SYMBOLS = 32


def _windows(bars) -> List[Tuple[int, int]]:
    """Index ranges for non-overlapping windows after the warm-up."""
    out = []
    i = WARMUP
    while i < len(bars):
        j = min(i + WINDOW_DAYS, len(bars))
        if j - i >= 60:
            out.append((i, j))
        i = j
    return out


def _arm_on_window(bars, lo: int, hi: int, **kw) -> Optional[Tuple[float, int]]:
    """Gross per trade and trade count for one arm on one window."""
    cfg = BacktestConfig(
        ticker="X", start_date=bars[lo].date, end_date=bars[hi - 1].date, **kw
    )
    res = run_backtest_on_bars(cfg, bars[:hi])
    n = res.stats.num_trades
    if n == 0:
        return None
    return res.stats.total_gross_pnl / n, n


def paired(diffs: List[float]) -> Dict[str, float]:
    n = len(diffs)
    if n < 2:
        return {}
    mean = sum(diffs) / n
    var = sum((d - mean) ** 2 for d in diffs) / (n - 1)
    se = math.sqrt(var / n)
    wins = sum(1 for d in diffs if d > 0)
    # Sign test: normal approximation to the binomial, continuity-corrected.
    z_sign = (
        (abs(wins - n / 2) - 0.5) / math.sqrt(n / 4) * (1 if wins > n / 2 else -1)
        if n else 0.0
    )
    return {
        "n_windows": n, "mean_diff": mean,
        "t_paired": mean / se if se else 0.0,
        "wins": wins, "win_share": wins / n, "z_sign": z_sign,
    }


def run(filter_pct: float = 6.0, new_high: bool = False) -> Dict[str, float]:
    bars_by_symbol = load_bars()
    diffs: List[float] = []
    for sym in sorted(bars_by_symbol)[:MAX_SYMBOLS]:
        b = bars_by_symbol[sym]
        if len(b) < WARMUP + 90:
            continue
        for lo, hi in _windows(b):
            # ATR named explicitly, Backlog #101: it is no longer the default.
            atr = _arm_on_window(b, lo, hi, trailing_stop_mode="ATR")
            bp = _arm_on_window(
                b, lo, hi, trailing_stop_mode="BASING_POINT",
                basing_point_filter_pct=filter_pct,
                basing_point_new_high_rule=new_high,
            )
            if atr is None or bp is None:
                continue
            diffs.append(bp[0] - atr[0])
    return paired(diffs)


def show(label: str, r: Dict[str, float]) -> None:
    if not r:
        print(f"{label:28s} insufficient windows")
        return
    sig_t = "SIG" if abs(r["t_paired"]) > 1.96 else "ns "
    sig_s = "SIG" if abs(r["z_sign"]) > 1.96 else "ns "
    print(f"{label:28s} windows={r['n_windows']:4d}  mean diff={r['mean_diff']:+8.2f}  "
          f"paired t={r['t_paired']:+6.2f} {sig_t}  "
          f"wins={r['wins']:3d}/{r['n_windows']:<3d} ({r['win_share']:.0%})  "
          f"sign z={r['z_sign']:+5.2f} {sig_s}")


if __name__ == "__main__":
    print(f"EM-3 walk-forward — paired per window, {WINDOW_DAYS}-day OOS windows\n")
    print("(a) CONFIRMATION at the book's 6% filter")
    base = run(6.0)
    show("basing point, rules 1-3", base)
    show("basing point + rule 4", run(6.0, new_high=True))

    print("\n(b) ROBUSTNESS across the filter (not a search for the best)")
    for f in (3.0, 4.5, 6.0, 8.0, 10.0, 12.0):
        show(f"filter = {f:.1f}%", run(f))


def run_clustered(filter_pct: float = 6.0) -> Dict[str, float]:
    """The conservative version of (a): cluster by SYMBOL.

    The 192 windows are not independent — roughly six come from each of 32
    symbols, and windows from one symbol share its regime, its liquidity and
    its idiosyncratic drift. A paired t over all 192 treats them as if they
    were independent draws, which understates the standard error and
    overstates t.

    Averaging each symbol's window differences first gives one observation per
    symbol: 32 genuinely independent units. It is the right denominator, and
    it is the number the verdict should rest on.
    """
    bars_by_symbol = load_bars()
    per_symbol: List[float] = []
    for sym in sorted(bars_by_symbol)[:MAX_SYMBOLS]:
        b = bars_by_symbol[sym]
        if len(b) < WARMUP + 90:
            continue
        diffs = []
        for lo, hi in _windows(b):
            # ATR named explicitly, Backlog #101: it is no longer the default.
            atr = _arm_on_window(b, lo, hi, trailing_stop_mode="ATR")
            bp = _arm_on_window(
                b, lo, hi, trailing_stop_mode="BASING_POINT",
                basing_point_filter_pct=filter_pct,
            )
            if atr is None or bp is None:
                continue
            diffs.append(bp[0] - atr[0])
        if diffs:
            per_symbol.append(sum(diffs) / len(diffs))
    return paired(per_symbol)
