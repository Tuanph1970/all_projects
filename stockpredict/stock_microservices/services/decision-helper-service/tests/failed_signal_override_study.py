"""Backlog #82 — does the failed-signal override belong in the backtest?

Test-support, not a test module. Run it::

    PYTHONPATH=. python3 tests/failed_signal_override_study.py

The question
------------
`#80` measured that this override closes ~66% of all backtest trades, and the
grace window it added halves the *count* without moving the *share*. A
component that ends two thirds of every position means the ATR stop each trade
was **sized** for almost never gets to act — which also makes `EM-3`
(basing-point stops) unevaluable, since a stop rule cannot be judged on a
bench where something else closes the position first.

What #79 does and does not settle
---------------------------------
`#79` measured the two **pattern-based** verdicts over 6,797 causal scans and
found neither predicts anything (`HS_TARGET_FAILURE/SHORT` is significantly
*backwards*). It then set both severities **below** `OVERRIDE_THRESHOLD`, so
neither can drive an override any more.

So #79 does **not** answer this question. The override in the harness is
driven by the other ten kinds — traps, false trendline breaks, filled gaps,
opposite breakouts and so on — and none of those has ever been measured. The
backlog entry for #82 leaned on #79 for them, and that lean was only partly
valid; this study is the correction.

The criterion, pre-registered before the run
--------------------------------------------
The override exists to **cut losses early**. So:

    It earns its place if removing it makes results WORSE — specifically if
    GROSS P&L PER TRADE is higher with the override than without, on the same
    bars. If removing it leaves results the same or better, it is not earning
    its place and should default off in the harness.

**Gross, not net**, and per trade, not in total. `#80` established why: with
fees at ~3x gross, an arm can win on net purely by trading less, and "an
improvement that comes from doing less is not an improvement". Turning the
override off reduces turnover by construction, so net and totals would both
flatter it automatically. Gross-per-trade is the statistic that cannot be
gamed by trading less.

A secondary reading, reported but not decisive: the exit mix. If the override
is removed and positions start ending at their stops and targets, that is the
sizing assumption being honoured rather than overridden.
"""
from __future__ import annotations

import math
from collections import Counter, defaultdict
from datetime import datetime
from typing import Dict, List

from app.services.backtest.harness import BacktestConfig, run_backtest_on_bars
from app.services.signal.base import OHLCVBar

BARS_TSV = "/tmp/all_bars.tsv"
MAX_SYMBOLS = 12
WARMUP = 330


def load_bars(path: str = BARS_TSV) -> Dict[str, List[OHLCVBar]]:
    rows: Dict[str, List[OHLCVBar]] = defaultdict(list)
    with open(path) as fh:
        for line in fh:
            parts = line.rstrip("\n").split("\t")
            if len(parts) != 7:
                continue
            sym, d, o, hi, lo, c, v = parts
            try:
                rows[sym].append(OHLCVBar(
                    date=datetime.strptime(d, "%Y-%m-%d").date(),
                    open=float(o), high=float(hi), low=float(lo),
                    close=float(c), volume=float(v),
                ))
            except ValueError:
                continue
    return rows


def run_arm(bars_by_symbol, **kw) -> Dict[str, object]:
    trades = 0
    gross = 0.0
    net = 0.0
    comm = 0.0
    wins = 0
    reasons: Counter = Counter()
    holds: List[int] = []
    bars_seen = 0

    for sym in sorted(bars_by_symbol)[:MAX_SYMBOLS]:
        b = bars_by_symbol[sym]
        if len(b) < WARMUP + 90:
            continue
        cfg = BacktestConfig(
            ticker=sym, start_date=b[WARMUP].date, end_date=b[-1].date, **kw
        )
        res = run_backtest_on_bars(cfg, b)
        trades += res.stats.num_trades
        gross += res.stats.total_gross_pnl
        net += res.stats.total_net_pnl
        comm += res.stats.total_commission
        wins += res.stats.num_wins
        bars_seen += sum(1 for x in b if x.date >= cfg.start_date)
        for t in res.trade_ledger:
            reasons[t.exit_reason] += 1
            if t.exit_date:
                holds.append((t.exit_date - t.entry_date).days)

    holds.sort()
    return {
        "trades": trades,
        "bars_per_trade": bars_seen / trades if trades else 0.0,
        "gross": gross,
        "gross_per_trade": gross / trades if trades else 0.0,
        "net": net,
        "commission": comm,
        "win_rate": wins / trades if trades else 0.0,
        "median_hold": holds[len(holds) // 2] if holds else 0,
        "reasons": dict(reasons),
    }


def welch_t(a_mean, a_var, a_n, b_mean, b_var, b_n):
    """Two-sample Welch t for the gross-per-trade difference."""
    if a_n < 2 or b_n < 2:
        return None
    se = math.sqrt(a_var / a_n + b_var / b_n)
    return (a_mean - b_mean) / se if se else None


def per_trade_gross(bars_by_symbol, **kw) -> List[float]:
    """Every trade's gross P&L, for a significance test on the mean."""
    out: List[float] = []
    for sym in sorted(bars_by_symbol)[:MAX_SYMBOLS]:
        b = bars_by_symbol[sym]
        if len(b) < WARMUP + 90:
            continue
        cfg = BacktestConfig(
            ticker=sym, start_date=b[WARMUP].date, end_date=b[-1].date, **kw
        )
        res = run_backtest_on_bars(cfg, b)
        out.extend(t.gross_pnl or 0.0 for t in res.trade_ledger)
    return out


def _stats(xs: List[float]):
    n = len(xs)
    if n < 2:
        return 0.0, 0.0, n
    mean = sum(xs) / n
    var = sum((x - mean) ** 2 for x in xs) / (n - 1)
    return mean, var, n


if __name__ == "__main__":
    bars = load_bars()
    print(f"symbols={min(MAX_SYMBOLS, len(bars))}  (source {BARS_TSV})\n")

    arms = {
        "override ON  (shipped)": {},
        "override OFF": {"failed_signal_enabled": False},
    }
    results = {}
    for label, kw in arms.items():
        r = run_arm(bars, **kw)
        results[label] = r
        print(f"{label}")
        print(f"   trades={r['trades']:5d}  bars/trade={r['bars_per_trade']:5.2f}  "
              f"median hold={r['median_hold']:3d}d  win rate={r['win_rate']:.1%}")
        print(f"   gross={r['gross']:12,.0f}   GROSS PER TRADE={r['gross_per_trade']:8.2f}   "
              f"net={r['net']:12,.0f}")
        print(f"   exits={r['reasons']}\n")

    on = per_trade_gross(bars)
    off = per_trade_gross(bars, failed_signal_enabled=False)
    m1, v1, n1 = _stats(on)
    m2, v2, n2 = _stats(off)
    t = welch_t(m1, v1, n1, m2, v2, n2)
    print("PRE-REGISTERED CRITERION: the override earns its place only if "
          "gross-per-trade is HIGHER with it on.")
    print(f"   ON  mean={m1:8.2f} (n={n1})")
    print(f"   OFF mean={m2:8.2f} (n={n2})")
    print(f"   difference={m1 - m2:+8.2f}   Welch t={t:+.2f}"
          if t is not None else "   t: insufficient sample")
    if t is not None:
        verdict = ("KEEP — the override improves gross per trade"
                   if m1 > m2 and abs(t) > 1.96 else
                   "DROP — it does not earn its place")
        print(f"   VERDICT: {verdict}")
