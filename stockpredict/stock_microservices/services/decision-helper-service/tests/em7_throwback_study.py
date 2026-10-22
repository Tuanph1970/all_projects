"""EM-7 T2 / GATE 1 — is a throwback more than a coincidence?

    PYTHONPATH=. python3 tests/em7_throwback_study.py [bars.tsv] [n_symbols]

Not a test. The cheapest decisive measurement in the EM-7 plan: it needs only
`T1` and can close `#67` before a detector is written.

E&M make TWO claims about the return to a broken boundary, and both are
measured here because a frequency result alone would answer half the book:

> **Pullback** to the neckline after the break is **common** … It is the
> short-seller's second chance. (Ch 6)

> Pullbacks … stop **more exactly** at the old line. (Ch 14)

PRE-REGISTERED CRITERION (plan §3, fixed before this file was written)
-----------------------------------------------------------------------
> Against a **band- and window-matched** random-entry null, the return rate
> must be **higher** AND the overshoot **smaller**, at the primary
> (0.5 ATR, 60 bar) setting, clustered **by symbol**.
>
> **If neither holds, stop.** A throwback that happens no more often than
> chance and stops no more precisely is a random limit order with a story
> attached. Record the negative and close `#67`.

The null, which is the whole design
------------------------------------
A level is "returned to" **often by chance** — that is EM-2's warning, where
the levels were real and every elaboration on them failed. So the control has
to be tight. For each real break of a level at bar *b*, the null draws random
bars *b'* in the **same symbol**, against the **same level price**, requiring
that price at *b'* sits **the same number of ATRs from the level** as the real
break's penetration (±25%), and that *b'* does not fall inside any real
break's window.

**The distance match is not a refinement, it is the whole control.** The first
version of this null required only that price be *at least* one band away, and
it reported a +75 percentage-point effect at t = +24.7 — because over 19 years
a level formed in 2010 sits hundreds of ATRs from 2024 prices, so those draws
could never return, while a real break sits by definition just past the band
edge. The two arms were being compared across different distance regimes. That
is EM-2's matched-distance lesson, got wrong once more before being got right.

So the only difference between arm and control is **that a break happened**.
The question becomes exactly E&M's: *is price returning to a level it has just
broken more likely than price returning to a level it merely sits far from?*

Matching on band AND window matters because a wider band and a longer window
each find more throwbacks **trivially** (plan §1).

Causality
---------
A level is formed from a swing pivot, and a pivot is not confirmed until
`PIVOT_WINDOW` bars after it forms. Breaks are therefore only counted from
`pivot_index + PIVOT_WINDOW` onward: a penetration that predates the level's
existence is not a penetration of it.
"""
from __future__ import annotations

import math
import os
import random
import statistics
import sys
from collections import defaultdict
from datetime import date
from typing import Dict, List, Optional, Sequence, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.backtest.market_features import (  # noqa: E402
    atr_series,
    detect_level_breaks,
)
from app.services.signal.base import OHLCVBar  # noqa: E402

PIVOT_WINDOW = 10
BANDS = (0.25, 0.5, 1.0)          # ATR units
WINDOWS = (20, 60, 120)           # bars
PRIMARY = (0.5, 60)
NULL_DRAWS = 25
OVERSHOOT_BARS = 10
RNG_SEED = 20261022
MIN_BREAKS = 5                    # a symbol with fewer is not a measurement


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


# ---------------------------------------------------------------------------
# levels
# ---------------------------------------------------------------------------

class Level:
    __slots__ = ("price", "role", "first_bar", "touches")

    def __init__(self, price: float, role: str, first_bar: int):
        self.price, self.role, self.first_bar, self.touches = price, role, first_bar, 1


def levels_of(bars: Sequence[OHLCVBar], atr: Sequence[Optional[float]]) -> List[Level]:
    """Swing pivots clustered into levels, with a touch count.

    Clustering within half a band keeps the level set from being a hundred
    near-identical prices, and the merge count is the **touches** that EM-2
    established is what carries information about a level.
    """
    out: List[Level] = []
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
            a = atr[i]
            tol = (a or 0.0) * 0.5
            merged = False
            for lvl in out:
                if lvl.role == role and abs(lvl.price - price) <= tol:
                    lvl.touches += 1
                    merged = True
                    break
            if not merged:
                out.append(Level(price, role, i + PIVOT_WINDOW))
    return out


# ---------------------------------------------------------------------------
# the measurement
# ---------------------------------------------------------------------------

def returns_to(bars: Sequence[OHLCVBar], atr: Sequence[Optional[float]],
               level: float, start: int, band_mult: float,
               window: int) -> Tuple[bool, Optional[float]]:
    """Did price come back within the band, and how far past the level did it go?

    Overshoot is measured in ATR units over `OVERSHOOT_BARS` from the first
    touch — E&M's *"stop more exactly at the old line"* made numeric.
    """
    end = min(start + window, len(bars) - 1)
    for t in range(start + 1, end + 1):
        a = atr[t]
        if a is None or a <= 0:
            continue
        if abs(bars[t].close - level) <= a * band_mult:
            stop = min(t + OVERSHOOT_BARS, len(bars) - 1)
            beyond = 0.0
            for u in range(t, stop + 1):
                beyond = max(beyond,
                             bars[u].high - level if bars[u].high > level else 0.0,
                             level - bars[u].low if bars[u].low < level else 0.0)
            ref = atr[t] or 1.0
            return True, beyond / ref
    return False, None


def sweep_symbol(bars: Sequence[OHLCVBar], rng: random.Random,
                 band_mult: float, window: int) -> Dict[str, object]:
    atr = atr_series(bars)
    n = len(bars)
    lv = levels_of(bars, atr)

    real_hits: List[int] = []
    real_over: List[float] = []
    null_hits: List[float] = []
    null_over: List[float] = []
    by_strength: Dict[str, List[int]] = defaultdict(list)
    by_direction: Dict[str, List[int]] = defaultdict(list)

    for level in lv:
        brks = detect_level_breaks(bars, level.price, role=level.role,
                                   first_bar=level.first_bar, atr=atr)
        if not brks:
            continue
        blocked = {b["bar_index"] for b in brks}

        for b in brks:
            bi = b["bar_index"]
            hit, over = returns_to(bars, atr, level.price, bi, band_mult, window)
            real_hits.append(1 if hit else 0)
            if over is not None:
                real_over.append(over)
            by_strength["strong (3+ touches)" if level.touches >= 3
                         else "weak (1-2 touches)"].append(1 if hit else 0)
            by_direction[b["direction"]].append(1 if hit else 0)

            # --- the DISTANCE-matched null ------------------------------
            # The first version of this matched only a MINIMUM distance
            # ("at least one band away"), and it manufactured a +75pp effect
            # at t = +24.7. Over 19 years a level formed in 2010 sits
            # HUNDREDS of ATRs from 2024 prices, so those draws could never
            # return — while a real break sits, by definition, just past the
            # band edge. The arms were being compared across two completely
            # different distance regimes.
            #
            # So the null now matches the break's OWN penetration distance:
            # price must be the same number of ATRs from the level, within
            # +/-25%. That is EM-2's matched-distance construction, and
            # getting it wrong here is the same mistake in a new place.
            pen = b["penetration_atr"]
            lo_d, hi_d = pen * 0.75, pen * 1.25
            drawn = 0
            tries = 0
            while drawn < NULL_DRAWS and tries < NULL_DRAWS * 200:
                tries += 1
                r = rng.randrange(PIVOT_WINDOW, max(PIVOT_WINDOW + 1, n - window - 1))
                a = atr[r]
                if a is None or a <= 0:
                    continue
                d = abs(bars[r].close - level.price) / a
                if not (lo_d <= d <= hi_d):
                    continue
                if any(abs(r - x) <= window for x in blocked):
                    continue
                nh, no = returns_to(bars, atr, level.price, r, band_mult, window)
                null_hits.append(1.0 if nh else 0.0)
                if no is not None:
                    null_over.append(no)
                drawn += 1

    return {
        "n_breaks": len(real_hits),
        "real_rate": statistics.fmean(real_hits) if real_hits else None,
        "null_rate": statistics.fmean(null_hits) if null_hits else None,
        "real_over": statistics.median(real_over) if real_over else None,
        "null_over": statistics.median(null_over) if null_over else None,
        "by_strength": {k: statistics.fmean(v) for k, v in by_strength.items() if v},
        "by_direction": {k: statistics.fmean(v) for k, v in by_direction.items() if v},
    }


def paired_t(diffs: Sequence[float]) -> Optional[float]:
    if len(diffs) < 3:
        return None
    sd = statistics.stdev(diffs)
    if sd <= 0:
        return None
    return statistics.fmean(diffs) / (sd / math.sqrt(len(diffs)))


def main() -> None:
    path = sys.argv[1] if len(sys.argv) > 1 else "/tmp/deep_bars.tsv"
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    data = load(path)
    symbols = sorted(data)
    if limit:
        symbols = symbols[:limit]

    print("=" * 104, flush=True)
    print("EM-7 T2 / GATE 1 — does price return to a BROKEN level more than to a level "
          "it merely sits far from?", flush=True)
    print("=" * 104, flush=True)
    print(f"  {len(symbols)} symbols | bands {BANDS} ATR | windows {WINDOWS} bars | "
          f"primary {PRIMARY}", flush=True)
    print(f"  null: same symbol, same level price, same band, same window, and "
          f"the SAME penetration distance (+/-25%)", flush=True)
    print(f"  CRITERION: return rate HIGHER and overshoot SMALLER than the null "
          f"at the primary setting, symbol-clustered\n", flush=True)

    rows = []
    strength_agg: Dict[str, List[float]] = defaultdict(list)
    direction_agg: Dict[str, List[float]] = defaultdict(list)

    for band_mult in BANDS:
        for window in WINDOWS:
            rng = random.Random(RNG_SEED)
            rate_d, over_d, nb = [], [], 0
            rr, nr = [], []
            for i, sym in enumerate(symbols, 1):
                bars = data[sym]
                if len(bars) < 400:
                    continue
                res = sweep_symbol(bars, rng, band_mult, window)
                if (res["n_breaks"] or 0) < MIN_BREAKS or res["null_rate"] is None:
                    continue
                nb += res["n_breaks"]
                rr.append(res["real_rate"])
                nr.append(res["null_rate"])
                rate_d.append(res["real_rate"] - res["null_rate"])
                if res["real_over"] is not None and res["null_over"] is not None:
                    over_d.append(res["real_over"] - res["null_over"])
                if (band_mult, window) == PRIMARY:
                    for k, v in res["by_strength"].items():
                        strength_agg[k].append(v)
                    for k, v in res["by_direction"].items():
                        direction_agg[k].append(v)
            rows.append((band_mult, window, len(rate_d), nb,
                         statistics.fmean(rr) if rr else float("nan"),
                         statistics.fmean(nr) if nr else float("nan"),
                         statistics.fmean(rate_d) if rate_d else float("nan"),
                         paired_t(rate_d),
                         statistics.fmean(over_d) if over_d else float("nan"),
                         paired_t(over_d)))
            print(f"    ... band {band_mult} window {window}: "
                  f"{len(rate_d)} symbols, {nb} breaks", flush=True)

    print("\n" + "-" * 104)
    print(f"{'band':>5s} {'win':>4s} {'syms':>5s} {'breaks':>7s} {'return':>7s} "
          f"{'null':>6s} {'edge':>7s} {'t':>7s} {'overshoot Δ':>12s} {'t':>7s}  verdict")
    print("-" * 104)
    primary_pass = False
    for band_mult, window, syms, nb, real, null, edge, t, od, ot in rows:
        rate_ok = t is not None and t > 1.96
        over_ok = ot is not None and ot < -1.96
        mark = "PRIMARY" if (band_mult, window) == PRIMARY else ""
        if mark:
            primary_pass = rate_ok and over_ok
        print(f"{band_mult:>5.2f} {window:>4d} {syms:>5d} {nb:>7d} {real:>6.1%} "
              f"{null:>5.1%} {edge:>+6.1%} "
              f"{('n/a' if t is None else f'{t:+.2f}'):>7s} "
              f"{od:>+11.2f} {('n/a' if ot is None else f'{ot:+.2f}'):>7s}  "
              f"{'rate+' if rate_ok else 'rate-'} "
              f"{'over+' if over_ok else 'over-'} {mark}")

    print("\n" + "-" * 104)
    print("PRE-REGISTERED ORDERINGS at the primary setting (plan §1 Q4)")
    print("-" * 104)
    for label, agg in (("by level strength", strength_agg),
                       ("by break direction", direction_agg)):
        print(f"  {label}:")
        for k in sorted(agg):
            print(f"    {k:22s} mean return rate {statistics.fmean(agg[k]):6.1%} "
                  f"({len(agg[k])} symbols)")

    print("\n" + "=" * 104)
    print(f"GATE 1 at the primary setting {PRIMARY} -> "
          f"{'PASS' if primary_pass else 'FAIL'}")
    if not primary_pass:
        print("  Pre-registered consequence: STOP. Record the negative and close #67.")
    print("  'overshoot Δ' is real minus null, in ATR units: NEGATIVE means the "
          "throwback stopped MORE")
    print("  exactly at the old line, which is E&M's Ch 14 claim.")
    print("=" * 104)


if __name__ == "__main__":
    main()
