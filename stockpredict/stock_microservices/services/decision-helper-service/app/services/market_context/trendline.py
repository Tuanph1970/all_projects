"""EM-5 Phase A — the admissible-line enumerator (`FR-EM-L1`..`L3`).

E&M Ch 14: up trendlines across the minor-reaction **bottoms**, down lines
across the minor-rally **tops** — *never bottom-to-top, never through the
price track*. And on which price to use, unambiguously:

> Intraday breaks that don't close beyond the line are ignored — *"closing
> prices often make a better trendline than extreme lows, especially in thin
> erratic stocks."*

So this reads **closes** only, which also puts it in the same vocabulary as
`dow.py` (Dow tenet 11) rather than inventing a second one.

Why it returns a SET
--------------------
E&M's method is explicitly plural: *"draw every line the action permits,
lightly; erase the useless, heavy the survivors. The quickest way — in fact,
the only way — of acquiring the experience."* Picking one line by taste is not
reproducible, and the project's determinism harness forbids it. So the
enumeration is **total** and the pruning is a **hard rule**:

1. every pair of **confirmed** same-side pivots, subject to a minimum span;
2. discard any line **the price track violates** — this does the real work;
3. return the survivors, deterministically ordered.

`H-L9` asserts step 2 actually prunes. If it did not, the set size would be a
function of the lookback rather than of the price action, and every number
downstream would be measuring the cap.

The pivot scale, which is a fifth parameter the plan did not name
---------------------------------------------------------------------
`dow.py`'s 5% zigzag is calibrated for E&M's **secondary** reactions, because
it reads the *primary* trend. Trendlines are drawn across **minor**-reaction
bottoms — the smaller degree, the "ripple" of tide/wave/ripple. Using dow's
scale would anchor lines on the wrong degree of reversal, so the default here
is finer (2%), parameterised, and swept at Gate A.

Causality (C1)
--------------
Anchors come from `dow.confirmed_pivots`, which carries both the bar a pivot
**formed** on and the later bar that **confirmed** it. A line is admissible at
bar *t* only when both anchors were confirmed at or before *t* — reading
`Pivot.index` instead of `confirmed_index` is exactly the look-ahead EM-6 D1's
first test contained.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

from app.services.market_context.dow import Pivot, confirmed_pivots
from app.services.signal.base import OHLCVBar

#: Minor-reaction scale, finer than `dow.DEFAULT_SWING_PCT` (see the module
#: docstring). Read in the body, never as a default argument.
DEFAULT_PIVOT_PCT = 0.02

#: `EC-L2`/`EC-L3`: a line through adjacent pivots is noise with a slope, and
#: bounding the bar separation is also what rules out a near-vertical line.
DEFAULT_MIN_SPAN = 10

#: What production hands its detectors (`lookback_bars=250`, `df.tail(250)`),
#: per EM-8 M2 — a windowed detector is measured in production's window, not
#: an invented one. NOT the thing that keeps the set finite; see `H-L9`.
DEFAULT_LOOKBACK = 250

KIND_UP = "UP"        # through LOW pivots — a support line
KIND_DOWN = "DOWN"    # through HIGH pivots — a resistance line


@dataclass(frozen=True)
class Trendline:
    """One admissible line, anchored on two confirmed same-side pivots.

    `kind` records which side the anchors are on, **not** the sign of the
    slope. E&M's "up trendline" is a `KIND_UP` line with a positive slope, but
    a down-sloping support line is also a real object (a down-sloping neckline
    is one), so the sign is reported rather than filtered — and the slope sign
    is one of the SRS's declared secondary splits.
    """
    kind: str
    a_index: int
    b_index: int
    a_price: float
    b_price: float
    slope: float                 # price per bar
    anchors_confirmed_at: int    # the bar this line became knowable

    def value_at(self, i: int) -> float:
        return self.a_price + self.slope * (i - self.a_index)


def _resolve(pivot_pct, min_span, lookback) -> Tuple[float, int, int]:
    return (
        DEFAULT_PIVOT_PCT if pivot_pct is None else pivot_pct,
        DEFAULT_MIN_SPAN if min_span is None else min_span,
        DEFAULT_LOOKBACK if lookback is None else lookback,
    )


def _usable_anchors(bars: Sequence[OHLCVBar], pivots: Sequence[Pivot],
                    at_index: int, lookback: int) -> Tuple[List[Pivot], List[Pivot]]:
    """Confirmed pivots inside the lookback, split by side.

    `EC-L6`: a non-positive price is not a price and never anchors a line —
    13 such bars exist in the vendor data (`#93`).
    """
    lo: List[Pivot] = []
    hi: List[Pivot] = []
    floor = max(0, at_index - lookback + 1)
    for p in pivots:
        if p.confirmed_index > at_index:      # not yet knowable (C1)
            continue
        if p.index < floor or p.index > at_index:
            continue
        if not (p.price > 0):
            continue
        (lo if p.kind == "LOW" else hi).append(p)
    return lo, hi


def _violated(bars: Sequence[OHLCVBar], a: Pivot, b: Pivot,
              slope: float, up: bool) -> bool:
    """`FR-EM-L2` — does the price track cut this line?

    Strict, with no tolerance: the anchors are the extremes of their own
    reactions, so a close between them that crosses the connecting line means
    the line is not supported by the action. That is E&M's rule read literally
    and it needs no magic number — and `L1`'s count measurement is what checks
    whether reading it literally prunes too hard.
    """
    for i in range(a.index, b.index + 1):
        c = bars[i].close
        if c <= 0:
            continue
        v = a.price + slope * (i - a.index)
        if up:
            if c < v - 1e-9:
                return True
        elif c > v + 1e-9:
            return True
    return False


def candidate_pair_count(bars: Sequence[OHLCVBar],
                         at_index: Optional[int] = None,
                         *,
                         pivot_pct: Optional[float] = None,
                         min_span: Optional[int] = None,
                         lookback: Optional[int] = None) -> int:
    """How many pairs pass the span filter **before** the price-track rule.

    Exists for `H-L9`: the admissible count must be strictly smaller, or the
    constraint is inert and the line set is governed by the cap.
    """
    pct, span, look = _resolve(pivot_pct, min_span, lookback)
    if not bars:
        return 0
    at = len(bars) - 1 if at_index is None else at_index
    if at < 0 or at >= len(bars):
        return 0
    lo, hi = _usable_anchors(bars, confirmed_pivots(bars, pct=pct), at, look)
    total = 0
    for group in (lo, hi):
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                if group[j].index - group[i].index >= span:
                    total += 1
    return total


def admissible_lines(bars: Sequence[OHLCVBar],
                     at_index: Optional[int] = None,
                     *,
                     pivot_pct: Optional[float] = None,
                     min_span: Optional[int] = None,
                     lookback: Optional[int] = None) -> List[Trendline]:
    """Every line the action permits at `at_index`, deterministically ordered.

    `EC-L5`: recomputed from bars up to `at_index` on every call. Lines are
    never accumulated across bars — a line admissible at *t* that a later
    close cuts is simply absent at *t+k*.
    """
    pct, span, look = _resolve(pivot_pct, min_span, lookback)
    if not bars:
        return []
    at = len(bars) - 1 if at_index is None else at_index
    if at < 0 or at >= len(bars):
        return []

    lo, hi = _usable_anchors(bars, confirmed_pivots(bars, pct=pct), at, look)

    out: List[Trendline] = []
    for group, kind in ((lo, KIND_UP), (hi, KIND_DOWN)):
        up = kind == KIND_UP
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                a, b = group[i], group[j]
                run = b.index - a.index
                if run < span:                      # EC-L2 / EC-L3
                    continue
                slope = (b.price - a.price) / run
                if _violated(bars, a, b, slope, up):
                    continue
                out.append(Trendline(
                    kind=kind,
                    a_index=a.index, b_index=b.index,
                    a_price=a.price, b_price=b.price,
                    slope=slope,
                    anchors_confirmed_at=max(a.confirmed_index, b.confirmed_index),
                ))

    out.sort(key=lambda ln: (ln.kind, ln.a_index, ln.b_index))
    return out
