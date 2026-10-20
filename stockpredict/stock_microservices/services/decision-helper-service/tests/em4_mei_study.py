"""EM-4 — does an extremely low MEI mark a market bottom?

    PYTHONPATH=. python3 tests/em4_mei_study.py

E&M's falsifiable claim, from Magee's market letter of 28 September 1985
reproduced in Ch 38:

    "For over 20 years, all major stock market Bottoms have corresponded with
    extremely low MEI readings."

He cites 9% Strong at the June 1982 low before the run from 770 to ~1300, and
8% at the February/June 1984 double bottom before 1079 to 1372.

That is a prediction, not a parameter, and it is testable without touching the
backtest: if extreme lows mark bottoms, forward market returns after a
low-MEI reading should beat the unconditional forward return.

CRITERION, FIXED BEFORE THE RUN
-------------------------------
Both, or the claim does not reproduce:

  1. forward market return after a BOTTOM-DECILE MEI reading is significantly
     higher than the unconditional forward return; and
  2. it holds at MORE THAN ONE horizon (10, 20, 60 sessions), so the result is
     not one lucky window length.

NON-OVERLAPPING samples only. Consecutive days' forward returns overlap almost
completely, and overlapping windows inflate significance — the trap #79
documented. Observations are therefore sampled every `horizon` sessions.

The market proxy, and its honest limits
---------------------------------------
There is no VN-Index series in the local dump, so the market is proxied by an
**equal-weighted** basket of the same 32 symbols, each normalised to 1 at its
first bar. Two consequences, stated rather than buried:

* VN-Index is **cap-weighted**, and the VN market is dominated by a handful of
  large caps, so a cap-weighted proxy would be closer to what a user sees.
* The proxy is built from the **same universe** the MEI is built from, so the
  two are not independent. That makes this a test of internal consistency —
  "does breadth of this basket predict the basket" — which is the weaker form
  of E&M's claim. The stronger form needs the real index.
"""
from __future__ import annotations

import math
from statistics import mean
from typing import Dict, List, Optional, Sequence, Tuple

from app.services.breadth.mei import MeiPoint, compute_mei_series
from app.services.signal.base import OHLCVBar

from tests.failed_signal_override_study import load_bars

HORIZONS = (10, 20, 60)
DECILE = 10.0        # "extremely low" = bottom decile of the trailing history
WARMUP_POINTS = 250  # readings before a percentile is trusted


def market_proxy(bars_by_symbol: Dict[str, Sequence[OHLCVBar]]) -> Dict[object, float]:
    """Equal-weighted basket: each symbol normalised to 1 at its first bar."""
    first: Dict[str, float] = {}
    level: Dict[object, List[float]] = {}
    for sym, bars in bars_by_symbol.items():
        for b in sorted(bars, key=lambda x: x.date):
            if sym not in first:
                first[sym] = b.close
            if first[sym] > 0:
                level.setdefault(b.date, []).append(b.close / first[sym])
    return {d: mean(v) for d, v in level.items() if v}


def welch(a: Sequence[float], b: Sequence[float]) -> Optional[float]:
    if len(a) < 2 or len(b) < 2:
        return None
    ma, mb = mean(a), mean(b)
    va = sum((x - ma) ** 2 for x in a) / (len(a) - 1)
    vb = sum((x - mb) ** 2 for x in b) / (len(b) - 1)
    se = math.sqrt(va / len(a) + vb / len(b))
    return (ma - mb) / se if se else None


def forward_returns(
    series: List[MeiPoint],
    proxy: Dict[object, float],
    horizon: int,
) -> Tuple[List[float], List[float], int]:
    """(low-MEI forward returns, all forward returns, n low) — non-overlapping."""
    days = [p.day for p in series]
    low: List[float] = []
    every: List[float] = []

    for i in range(WARMUP_POINTS, len(series) - horizon, horizon):
        d0, d1 = days[i], days[i + horizon]
        if d0 not in proxy or d1 not in proxy or proxy[d0] <= 0:
            continue
        fwd = (proxy[d1] / proxy[d0] - 1.0) * 100.0
        every.append(fwd)

        # "Extremely low" against the reading's OWN trailing history, so the
        # threshold is never set with hindsight.
        past = [p.mei for p in series[:i]]
        if not past:
            continue
        cutoff = sorted(past)[max(0, int(len(past) * DECILE / 100.0) - 1)]
        if series[i].mei <= cutoff:
            low.append(fwd)

    return low, every, len(low)


if __name__ == "__main__":
    bars = load_bars()
    print(f"universe = {len(bars)} symbols\n")

    series = compute_mei_series(bars)
    proxy = market_proxy(bars)
    print(f"MEI series: {len(series)} readings, {series[0].day} -> {series[-1].day}")
    values = [p.mei for p in series]
    print(f"   range {min(values):.1f}% - {max(values):.1f}%   "
          f"mean {mean(values):.1f}%   proxy days {len(proxy)}\n")

    print("E&M: extremely low MEI marks a bottom. Forward proxy returns, "
          "non-overlapping:\n")
    print(f"{'horizon':>8}{'n low':>7}{'after low MEI':>15}{'unconditional':>15}"
          f"{'edge':>9}{'Welch t':>10}")
    passes = 0
    for h in HORIZONS:
        low, every, n = forward_returns(series, proxy, h)
        if len(low) < 2 or len(every) < 2:
            print(f"{h:>8}{n:>7}  insufficient non-overlapping sample")
            continue
        t = welch(low, every)
        sig = t is not None and t > 1.96
        passes += 1 if sig else 0
        print(f"{h:>8}{n:>7}{mean(low):>14.2f}%{mean(every):>14.2f}%"
              f"{mean(low) - mean(every):>+8.2f}%{t:>+9.2f} "
              f"{'SIG' if sig else 'ns'}")

    print(f"\nCRITERION: significant at more than one horizon -> "
          f"{passes} of {len(HORIZONS)} significant: "
          f"{'PASS' if passes >= 2 else 'FAIL'}")


# ---------------------------------------------------------------------------
# Two follow-ups the first result forces
# ---------------------------------------------------------------------------

def describe_extremes(series: List[MeiPoint], proxy: Dict[object, float]) -> None:
    """Did the MEI actually collapse during the one real bear market here?

    DESCRIPTIVE, not a test — n=1 event. But if the measure failed even to
    fall during a 2022-style decline, nothing built on it could work, so it is
    worth knowing before the predictive question is pursued further.
    """
    lows = sorted(series, key=lambda p: p.mei)[:8]
    print("the eight lowest readings in the series:")
    for p in lows:
        print(f"   {p.day}  MEI={p.mei:5.1f}%  "
              f"(+{p.bullish} -{p.bearish} ={p.neutral} of {p.classified})")

    dd = sorted(proxy.items(), key=lambda kv: kv[1])[:3]
    print("\nthe proxy's three lowest closes:")
    for d, v in dd:
        at = next((p.mei for p in series if p.day == d), None)
        print(f"   {d}  level={v:.3f}   MEI that day="
              f"{'n/a' if at is None else f'{at:.1f}%'}")


def quintile_monotonicity(
    series: List[MeiPoint], proxy: Dict[object, float], horizon: int
) -> None:
    """Does forward return vary with the LEVEL of breadth, across all of it?

    A different question from E&M's bottoms claim, and the one the register's
    other half actually needs: an exposure governor scales commitments with
    the reading, so what matters is whether the reading carries information
    across its whole range — not only at a rare extreme.

    It is also the better-powered question: every observation is used instead
    of a tail, so a null here is informative where the bottoms null is merely
    underpowered.
    """
    days = [p.day for p in series]
    rows: List[Tuple[float, float]] = []
    for i in range(WARMUP_POINTS, len(series) - horizon, horizon):
        d0, d1 = days[i], days[i + horizon]
        if d0 not in proxy or d1 not in proxy or proxy[d0] <= 0:
            continue
        rows.append((series[i].mei, (proxy[d1] / proxy[d0] - 1.0) * 100.0))

    if len(rows) < 10:
        print(f"   horizon {horizon}: only {len(rows)} observations")
        return

    rows.sort(key=lambda r: r[0])
    k = len(rows) // 5 or 1
    print(f"   horizon {horizon} sessions, {len(rows)} non-overlapping observations")
    buckets = []
    for q in range(5):
        chunk = rows[q * k: (q + 1) * k] if q < 4 else rows[4 * k:]
        if not chunk:
            continue
        mei_lo, mei_hi = chunk[0][0], chunk[-1][0]
        fwd = mean(r[1] for r in chunk)
        buckets.append(fwd)
        print(f"      Q{q + 1}  MEI {mei_lo:5.1f}-{mei_hi:5.1f}%  "
              f"n={len(chunk):3d}  forward {fwd:+7.2f}%")
    if len(buckets) == 5:
        t = welch([r[1] for r in rows[4 * k:]], [r[1] for r in rows[:k]])
        print(f"      top quintile vs bottom: {buckets[-1] - buckets[0]:+.2f}%  "
              f"Welch t={t:+.2f} {'SIG' if t and abs(t) > 1.96 else 'ns'}")
