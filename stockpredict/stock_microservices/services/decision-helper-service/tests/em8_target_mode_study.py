"""EM-8 M3 — do profit targets beat a pure trailing stop?

    PYTHONPATH=. python3 tests/em8_target_mode_study.py [bars.tsv] [n_symbols]

Not a test. The measurable half of the plan's question (c), after the other
half turned out to be unanswerable: `MEASURED_MOVE` has never fired in either
path, so there is no behaviour to compare (see `tests/test_target_mode.py`).

What is left is E&M's actual Ch 32 position, and it is a strong one:

> Moves in the direction of the trend cannot be estimated — a bull move *"may,
> and often does, overrun the upper trendline by running up as far again"* —
> because the overrun *is itself an unreasonable move*. This is why the book
> **prefers nearby progressive stops for taking profits over limit orders** at
> trendlines or resistance levels.

Bassetti sharpens it: *"Decisions should always be made in the here and now,
not in the I measured it then."*

Targets do fire in this system — 25.3% of exits are TARGET_HIT, via S/R and
fixed R:R — so the comparison is real.

PRE-REGISTERED CRITERION
-------------------------
> `TARGETS_ON` keeps its place only if it beats `TRAILING_ONLY` on **net P&L
> per trade**, clustered **by symbol**, with the trade count reported beside
> it. A target regime that improves per-trade P&L while destroying trade
> count has not helped.

Why there is no walk-forward split here
----------------------------------------
`#84` needed one because it swept `basing_point_filter_pct` — a tuned
parameter can be overfit to its sample. **Nothing is tuned here.** The arms
are a binary switch with no free parameter, so a split would cost half the
power to protect against an overfit that cannot occur. The full-sample paired
comparison across symbols *is* the test, and saying so is more honest than
performing the ritual.
"""
from __future__ import annotations

import math
import os
import statistics
import sys
from collections import defaultdict
from datetime import date
from typing import Dict, List, Optional, Sequence, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.backtest.harness import (  # noqa: E402
    BacktestConfig,
    run_backtest_on_bars,
)
from app.services.signal.base import OHLCVBar  # noqa: E402

MODES = ("TARGETS_ON", "TRAILING_ONLY")
START = date(2010, 1, 1)
END = date(2026, 10, 1)
MIN_TRADES = 10          # a symbol with fewer is not a measurement


def load(path: str) -> Dict[str, List[OHLCVBar]]:
    rows: Dict[str, List[OHLCVBar]] = defaultdict(list)
    with open(path) as fh:
        for line in fh:
            p = line.rstrip("\n").split("\t")
            if len(p) >= 7:
                rows[p[0]].append(OHLCVBar(
                    date=date.fromisoformat(p[1]), open=float(p[2]),
                    high=float(p[3]), low=float(p[4]), close=float(p[5]),
                    volume=int(float(p[6]))))
    return {s: sorted(b, key=lambda x: x.date) for s, b in rows.items()}


def arm(sym: str, bars: Sequence[OHLCVBar], mode: str) -> Tuple[int, float, float, Dict[str, int]]:
    # trailing_stop_mode pinned by Backlog #101 (the class default moved to
    # "BASING_POINT"); this study measures target modes against an ATR stop.
    cfg = BacktestConfig(ticker=sym, start_date=START, end_date=END,
                         target_mode=mode, trailing_stop_mode="ATR")
    res = run_backtest_on_bars(cfg, list(bars))
    led = [t for t in res.trade_ledger if t.net_pnl is not None]
    reasons: Dict[str, int] = defaultdict(int)
    for t in res.trade_ledger:
        reasons[t.exit_reason] += 1
    if not led:
        return 0, 0.0, 0.0, dict(reasons)
    total = sum(float(t.net_pnl) for t in led)
    return len(led), total / len(led), total, dict(reasons)


def paired_t(diffs: Sequence[float]) -> Optional[float]:
    if len(diffs) < 3:
        return None
    sd = statistics.stdev(diffs)
    if sd <= 0:
        return None
    return statistics.fmean(diffs) / (sd / math.sqrt(len(diffs)))


def sign_test_p(wins: int, n: int) -> float:
    """Two-sided exact binomial — consistency, which `#84` showed is a
    separate claim from magnitude and can fail while magnitude passes."""
    if n == 0:
        return 1.0
    tail = sum(math.comb(n, k) for k in range(0, min(wins, n - wins) + 1))
    return min(1.0, 2.0 * tail / (2 ** n))


def main() -> None:
    path = sys.argv[1] if len(sys.argv) > 1 else "/tmp/deep_bars.tsv"
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    data = load(path)
    symbols = sorted(data)
    if limit:
        symbols = symbols[:limit]

    print("=" * 96, flush=True)
    print("EM-8 M3 — profit targets versus a pure trailing stop", flush=True)
    print("=" * 96, flush=True)
    print(f"  {len(symbols)} symbols, {START} .. {END}, "
          f"min {MIN_TRADES} trades per arm", flush=True)
    print("  CRITERION: TARGETS_ON must beat TRAILING_ONLY on net P&L per "
          "trade, symbol-clustered,", flush=True)
    print("  with trade count reported. No walk-forward: nothing is tuned.",
          flush=True)

    per_symbol: Dict[str, Dict[str, Tuple[int, float, float, Dict[str, int]]]] = {}
    for i, sym in enumerate(symbols, 1):
        bars = data[sym]
        if len(bars) < 400:
            continue
        got = {m: arm(sym, bars, m) for m in MODES}
        if all(got[m][0] >= MIN_TRADES for m in MODES):
            per_symbol[sym] = got
        if i % 10 == 0:
            print(f"    ... {i}/{len(symbols)} symbols, "
                  f"{len(per_symbol)} usable", flush=True)

    print(f"\n  usable symbols: {len(per_symbol)}", flush=True)
    if not per_symbol:
        print("  nothing to compare")
        return

    print("\n" + "-" * 96)
    print(f"{'mode':16s} {'trades':>8s} {'net/trade':>11s} {'total net':>14s} "
          f"{'TARGET_HIT':>11s} {'STOP_HIT':>9s}")
    print("-" * 96)
    for m in MODES:
        trades = sum(per_symbol[s][m][0] for s in per_symbol)
        total = sum(per_symbol[s][m][2] for s in per_symbol)
        th = sum(per_symbol[s][m][3].get("TARGET_HIT", 0) for s in per_symbol)
        sh = sum(per_symbol[s][m][3].get("STOP_HIT", 0) for s in per_symbol)
        print(f"{m:16s} {trades:>8d} {total/max(1,trades):>11.2f} "
              f"{total:>14.2f} {th:>11d} {sh:>9d}")

    diffs = [per_symbol[s]["TARGETS_ON"][1] - per_symbol[s]["TRAILING_ONLY"][1]
             for s in per_symbol]
    wins = sum(1 for d in diffs if d > 0)
    t = paired_t(diffs)
    p_sign = sign_test_p(wins, len(diffs))

    print("\n" + "-" * 96)
    print("TARGETS_ON − TRAILING_ONLY, net P&L per trade, paired by symbol")
    print("-" * 96)
    print(f"  symbols            {len(diffs)}")
    print(f"  mean difference    {statistics.fmean(diffs):+.2f} per trade")
    print(f"  median difference  {statistics.median(diffs):+.2f}")
    print(f"  paired t           {('n/a' if t is None else f'{t:+.2f}')}")
    print(f"  symbols better     {wins}/{len(diffs)} "
          f"({wins/len(diffs):.0%})   sign test p = {p_sign:.4f}")

    sig = t is not None and abs(t) > 1.96
    better = t is not None and t > 0 and abs(t) > 1.96
    print(f"\n  CRITERION: TARGETS_ON beats TRAILING_ONLY -> "
          f"{'PASS' if better else 'FAIL'}"
          f"{'' if sig else '  (difference not significant either way)'}")
    if t is not None and t < 0 and sig:
        print("  The difference is significantly NEGATIVE: the trailing stop "
              "alone did better,")
        print("  which is what E&M's Ch 32 argues and what this system's "
              "default does not do.")
    print("=" * 96)


if __name__ == "__main__":
    main()
