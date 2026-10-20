"""Backlog #85 — does EM-3's edge concentrate in trending markets?

    PYTHONPATH=. python3 tests/em3_regime_gate_study.py

Why ask
-------
`#84` confirmed the basing-point stop's advantage **out of sample on
magnitude** (+37.82 gross per trade, clustered t = +3.39 across 32 symbols)
but **not on consistency** (54% of windows, 66% of symbols, sign test never
significant). The rule loses about as often as it wins; its wins are simply
bigger. So the edge sits in a tail, and the useful question is no longer "does
it work on average" but **where the magnitude comes from**.

E&M's own mechanism predicts an answer. A basing point is built from a
*reaction low in an advance* — the procedure assumes a trend to base within.
In a range there is no advance to protect, so a wider stop should buy nothing
and cost patience. If that is right, the advantage should be concentrated in
trend regimes and absent or negative in range.

Per trade, not per window
-------------------------
`#84` compared 192 windows. This conditions at **trade** granularity using
`TradeRecord.entry_regime`, which the replay already computes on every bar via
`compute_regime` — causal, reading only bars up to the entry. Thousands of
trades instead of 192 windows is far more power, and a per-trade gate is also
what would actually ship: the harness knows the regime at entry and could pick
the stop rule there.

CRITERION, FIXED BEFORE THE RUN
-------------------------------
A regime gate is worth building only if **both**:

  1. the basing-point advantage is significantly positive **within trend
     regimes** (TREND_UP and TREND_DOWN pooled); and
  2. that advantage is **larger in trend than in range** — the difference of
     differences is positive.

If the advantage is uniform across regimes there is nothing to gate on, and
#84's unconditional result is the whole story. If it is *negative* in range,
that is the strongest possible case for the gate.

Gross and per trade, per `#80`.
"""
from __future__ import annotations

import math
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

from app.services.backtest.harness import BacktestConfig, run_backtest_on_bars

from tests.failed_signal_override_study import MAX_SYMBOLS, WARMUP, load_bars

TREND = ("TREND_UP", "TREND_DOWN")


def collect(bars_by_symbol, **kw) -> Dict[str, List[float]]:
    """Gross P&L per trade, bucketed by the regime at entry."""
    out: Dict[str, List[float]] = defaultdict(list)
    for sym in sorted(bars_by_symbol)[:MAX_SYMBOLS]:
        b = bars_by_symbol[sym]
        if len(b) < WARMUP + 90:
            continue
        cfg = BacktestConfig(
            ticker=sym, start_date=b[WARMUP].date, end_date=b[-1].date, **kw
        )
        for t in run_backtest_on_bars(cfg, b).trade_ledger:
            out[t.entry_regime].append(t.gross_pnl or 0.0)
    return out


def _stats(xs: List[float]) -> Tuple[float, float, int]:
    n = len(xs)
    if n < 2:
        return 0.0, 0.0, n
    m = sum(xs) / n
    v = sum((x - m) ** 2 for x in xs) / (n - 1)
    return m, v, n


def welch(a: List[float], b: List[float]) -> Optional[float]:
    ma, va, na = _stats(a)
    mb, vb, nb = _stats(b)
    if na < 2 or nb < 2:
        return None
    se = math.sqrt(va / na + vb / nb)
    return (ma - mb) / se if se else None


def pool(buckets: Dict[str, List[float]], keys) -> List[float]:
    out: List[float] = []
    for k in keys:
        out.extend(buckets.get(k, []))
    return out


if __name__ == "__main__":
    bars = load_bars()
    atr = collect(bars)
    bp = collect(bars, trailing_stop_mode="BASING_POINT")

    print("gross P&L per trade, by regime at entry\n")
    print(f"{'regime':<12}{'n (ATR)':>9}{'ATR':>10}{'n (BP)':>9}{'BP':>10}"
          f"{'advantage':>11}{'Welch t':>9}")
    for regime in ("TREND_UP", "TREND_DOWN", "RANGE", "UNDEFINED"):
        a, b = atr.get(regime, []), bp.get(regime, [])
        if len(a) < 2 or len(b) < 2:
            continue
        ma, _, na = _stats(a)
        mb, _, nb = _stats(b)
        t = welch(b, a)
        flag = "SIG" if t is not None and abs(t) > 1.96 else "ns"
        print(f"{regime:<12}{na:>9}{ma:>10.2f}{nb:>9}{mb:>10.2f}"
              f"{mb - ma:>+11.2f}{t:>+8.2f} {flag}")

    trend_a, trend_b = pool(atr, TREND), pool(bp, TREND)
    range_a, range_b = atr.get("RANGE", []), bp.get("RANGE", [])

    ta, _, _ = _stats(trend_a)
    tb, _, _ = _stats(trend_b)
    ra, _, _ = _stats(range_a)
    rb, _, _ = _stats(range_b)
    t_trend = welch(trend_b, trend_a)
    t_range = welch(range_b, range_a)

    print("\nCRITERION (pre-registered)")
    print(f"  1. advantage significantly positive IN TREND: "
          f"{tb - ta:+.2f}  t={t_trend:+.2f}  "
          f"-> {'PASS' if t_trend and t_trend > 1.96 else 'FAIL'}")
    print(f"  2. larger in trend than in range: trend {tb - ta:+.2f} vs "
          f"range {rb - ra:+.2f}  (range t={t_range:+.2f})  "
          f"-> {'PASS' if (tb - ta) > (rb - ra) else 'FAIL'}")
