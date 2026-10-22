"""EM-7 T4 / GATE 2 — is the second chance better than taking the first?

    PYTHONPATH=. python3 tests/em7_gate2_study.py [bars.tsv] [n_symbols]

Not a test. The register's own benchmark for EM-7:

> Entry quality versus **taking the breakout itself** — a better average entry
> price must not be paid for with a materially lower fill rate.

PRE-REGISTERED CRITERION (plan §3, fixed before this file was written)
-----------------------------------------------------------------------
> Net P&L **per breakout opportunity** — counting the opportunities a rule
> declines as **zero**, not excluding them — improved over entering at the
> break, clustered **by symbol**, with the fill rate reported beside it.
>
> **Average entry price alone is invalid** and is not accepted as evidence: a
> rule that fills only on the best 20% of setups will always show a better
> average fill while making less money. This is the number that will look most
> persuasive and mean least.

Three arms on the SAME opportunities
-------------------------------------
Every decisive break of a level is one opportunity. For each:

* **BREAK** — enter at the break bar's close. What `SR_BREAKOUT` does today.
* **THROWBACK** — leave a resting order at the level, good for `WINDOW` bars.
  Fills when price returns within the band; **declines (P&L = 0) if it never
  does.** Causal: at bar *b* you place the order, and whether it fills is
  decided later by price, not by hindsight.
* **RETRACE_40** — the same, triggered by E&M's 40% give-back instead.

All three then hold for the **same** horizon and pay the **same** round-trip
cost, so the only difference is the entry. No stop is applied, deliberately:
the question is entry quality, and a stop would introduce a second variable
that interacts differently with each arm's entry price.

Gate 1 said the throwback fills about **82%** of the time at these settings.
So the trade-off is explicit: an entry nearer the level, on roughly four of
five opportunities, against taking every one of them immediately.
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

from app.services.backtest.harness import BacktestConfig  # noqa: E402
from app.services.backtest.market_features import (  # noqa: E402
    atr_series,
    detect_level_breaks,
)
from app.services.signal.base import OHLCVBar  # noqa: E402
from app.services.signal.trend.throwback import (  # noqa: E402
    DEFAULT_BAND_ATR,
    DEFAULT_RETRACE_PCT,
    DEFAULT_STALE_BARS,
)

PIVOT_WINDOW = 10
BAND = DEFAULT_BAND_ATR
WINDOW = DEFAULT_STALE_BARS
RETRACE = DEFAULT_RETRACE_PCT
HORIZONS = (10, 20, 60)
PRIMARY_H = 20
MIN_OPPORTUNITIES = 10

#: Round-trip cost in percent, from the shipped backtest config (#80's
#: proportional VN fees). Charged identically to every arm.
_CFG = BacktestConfig(ticker="_", start_date=date(2000, 1, 1), end_date=date(2000, 1, 2))
ROUND_TRIP_COST_PCT = 2.0 * _CFG.commission_pct + _CFG.sell_tax_pct


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


def levels_of(bars: Sequence[OHLCVBar], atr: Sequence[Optional[float]]):
    out = []
    n = len(bars)
    for i in range(PIVOT_WINDOW, n - PIVOT_WINDOW):
        lo = all(bars[j].low >= bars[i].low
                 for j in range(i - PIVOT_WINDOW, i + PIVOT_WINDOW + 1) if j != i)
        hi = all(bars[j].high <= bars[i].high
                 for j in range(i - PIVOT_WINDOW, i + PIVOT_WINDOW + 1) if j != i)
        for is_pivot, price, role in ((lo, bars[i].low, "support"),
                                      (hi, bars[i].high, "resistance")):
            if not is_pivot:
                continue
            a = atr[i] or 0.0
            if any(r == role and abs(p - price) <= a * 0.5 for p, r, _ in out):
                continue
            out.append((price, role, i + PIVOT_WINDOW))
    return out


def _net_return(bars: Sequence[OHLCVBar], entry_idx: int, horizon: int,
                up: bool) -> Optional[float]:
    """Percentage return from entry to `horizon` bars later, net of costs."""
    exit_idx = entry_idx + horizon
    if exit_idx >= len(bars):
        return None
    e, x = bars[entry_idx].close, bars[exit_idx].close
    # BOTH ends, not just the entry. The first version guarded `e` only and
    # died on `e / x` — the same 13 zero-price vendor bars that caused #93,
    # which I had just fixed in the shipped stop module and then reproduced
    # in my own study. A non-positive price is not a price at either end.
    if e <= 0 or x <= 0:
        return None
    gross = (x / e - 1.0) if up else (e / x - 1.0)
    return gross * 100.0 - ROUND_TRIP_COST_PCT


def _first_band_touch(bars, atr, level, b, window) -> Optional[int]:
    end = min(b + window, len(bars) - 1)
    for t in range(b + 1, end + 1):
        a = atr[t]
        if a is not None and a > 0 and abs(bars[t].close - level) <= a * BAND:
            return t
    return None


def _first_retrace(bars, level, b, window, up) -> Optional[int]:
    end = min(b + window, len(bars) - 1)
    for t in range(b + 1, end + 1):
        seg = bars[b:t + 1]
        extreme = max(x.high for x in seg) if up else min(x.low for x in seg)
        move = (extreme - level) if up else (level - extreme)
        if move <= 0:
            continue
        back = (extreme - bars[t].close) if up else (bars[t].close - extreme)
        if back >= RETRACE * move:
            return t
    return None


def sweep_symbol(bars: Sequence[OHLCVBar], horizon: int) -> Optional[Dict[str, object]]:
    atr = atr_series(bars)
    arms: Dict[str, List[float]] = {"BREAK": [], "THROWBACK": [], "RETRACE_40": []}
    filled_break: List[float] = []
    declined_break: List[float] = []
    fills: Dict[str, int] = defaultdict(int)
    entry_gap: Dict[str, List[float]] = defaultdict(list)
    n_opp = 0

    for price, role, first_bar in levels_of(bars, atr):
        for brk in detect_level_breaks(bars, price, role=role,
                                       first_bar=first_bar, atr=atr):
            b = brk["bar_index"]
            up = brk["direction"] == "up"
            base = _net_return(bars, b, horizon, up)
            if base is None:
                continue
            n_opp += 1
            arms["BREAK"].append(base)
            fills["BREAK"] += 1
            entry_gap["BREAK"].append(0.0)

            # Adverse selection: is the BREAK return on the opportunities the
            # throwback DECLINES different from the ones it fills? If waiting
            # systematically misses the breakouts that ran away, that is the
            # mechanism rather than the fill rate alone -- so it is measured
            # rather than asserted.
            tb_idx = _first_band_touch(bars, atr, price, b, WINDOW)
            (filled_break if tb_idx is not None else declined_break).append(base)

            for name, idx in (("THROWBACK", tb_idx),
                              ("RETRACE_40", _first_retrace(bars, price, b, WINDOW, up))):
                if idx is None:
                    arms[name].append(0.0)            # declined, counted as zero
                    continue
                r = _net_return(bars, idx, horizon, up)
                if r is None:
                    arms[name].append(0.0)
                    continue
                arms[name].append(r)
                fills[name] += 1
                # how much better the entry price was, in percent
                ep, bp = bars[idx].close, bars[b].close
                entry_gap[name].append(((bp - ep) / bp * 100.0) if up
                                       else ((ep - bp) / bp * 100.0))

    if n_opp < MIN_OPPORTUNITIES:
        return None
    return {
        "n": n_opp,
        "per_opp": {k: statistics.fmean(v) for k, v in arms.items() if v},
        "fill_rate": {k: fills[k] / n_opp for k in arms},
        "entry_gap": {k: (statistics.fmean(v) if v else 0.0)
                      for k, v in entry_gap.items()},
        "break_on_filled": statistics.fmean(filled_break) if filled_break else None,
        "break_on_declined": statistics.fmean(declined_break) if declined_break else None,
    }


def paired_t(diffs: Sequence[float]) -> Optional[float]:
    if len(diffs) < 3:
        return None
    sd = statistics.stdev(diffs)
    if sd <= 0:
        return None
    return statistics.fmean(diffs) / (sd / math.sqrt(len(diffs)))


def sign_p(wins: int, n: int) -> float:
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

    print("=" * 100, flush=True)
    print("EM-7 T4 / GATE 2 — the second chance versus taking the first", flush=True)
    print("=" * 100, flush=True)
    print(f"  {len(symbols)} symbols | band {BAND} ATR | order good for {WINDOW} bars "
          f"| retrace {RETRACE:.0%}", flush=True)
    print(f"  round-trip cost {ROUND_TRIP_COST_PCT:.2f}% charged to every arm | "
          f"horizons {HORIZONS}, primary {PRIMARY_H}", flush=True)
    print("  CRITERION: net P&L PER OPPORTUNITY, declines counted as ZERO, "
          "symbol-clustered.", flush=True)
    print("  Average entry price is NOT evidence.\n", flush=True)

    verdict_primary = False
    for horizon in HORIZONS:
        rows: Dict[str, List[float]] = defaultdict(list)
        fill: Dict[str, List[float]] = defaultdict(list)
        gap: Dict[str, List[float]] = defaultdict(list)
        adverse: List[float] = []
        total_opp = 0
        for sym in symbols:
            bars = data[sym]
            if len(bars) < 400:
                continue
            res = sweep_symbol(bars, horizon)
            if res is None:
                continue
            total_opp += res["n"]
            if (res["break_on_filled"] is not None
                    and res["break_on_declined"] is not None):
                adverse.append(res["break_on_declined"] - res["break_on_filled"])
            for arm in ("BREAK", "THROWBACK", "RETRACE_40"):
                if arm in res["per_opp"]:
                    rows[arm].append(res["per_opp"][arm])
                    fill[arm].append(res["fill_rate"][arm])
                    gap[arm].append(res["entry_gap"][arm])

        n_sym = len(rows["BREAK"])
        print("-" * 100)
        print(f"horizon {horizon} bars — {n_sym} symbols, {total_opp} opportunities")
        print(f"  {'arm':12s} {'net %/opp':>10s} {'fill rate':>10s} "
              f"{'entry better by':>16s} {'vs BREAK':>9s} {'t':>7s} {'symbols better':>15s}")
        for arm in ("BREAK", "THROWBACK", "RETRACE_40"):
            if not rows[arm]:
                continue
            mean = statistics.fmean(rows[arm])
            fr = statistics.fmean(fill[arm])
            g = statistics.fmean(gap[arm])
            if arm == "BREAK":
                print(f"  {arm:12s} {mean:>+9.3f}% {fr:>9.1%} {g:>15.2f}% "
                      f"{'—':>9s} {'—':>7s} {'—':>15s}")
                continue
            diffs = [a - b for a, b in zip(rows[arm], rows["BREAK"])]
            t = paired_t(diffs)
            wins = sum(1 for d in diffs if d > 0)
            better = t is not None and t > 1.96
            if horizon == PRIMARY_H and arm == "THROWBACK":
                verdict_primary = better
            print(f"  {arm:12s} {mean:>+9.3f}% {fr:>9.1%} {g:>15.2f}% "
                  f"{statistics.fmean(diffs):>+8.3f} "
                  f"{('n/a' if t is None else f'{t:+.2f}'):>7s} "
                  f"{wins}/{len(diffs)} p={sign_p(wins, len(diffs)):.3f}")
        if adverse:
            at = paired_t(adverse)
            print(f"    adverse selection: BREAK return on the opportunities the "
                  f"throwback DECLINED minus those it FILLED = "
                  f"{statistics.fmean(adverse):+.3f}pp "
                  f"(t={'n/a' if at is None else f'{at:+.2f}'}, {len(adverse)} symbols)")

    print("\n" + "=" * 100)
    print(f"GATE 2 (THROWBACK vs BREAK, horizon {PRIMARY_H}) -> "
          f"{'PASS' if verdict_primary else 'FAIL'}")
    if not verdict_primary:
        print("  Pre-registered consequence: the detector stays OFF and the "
              "result is recorded.")
    print("  'entry better by' is the average improvement in entry PRICE — "
          "reported because the")
    print("  register asks for it, and explicitly NOT the criterion.")
    print("=" * 100)


if __name__ == "__main__":
    main()
