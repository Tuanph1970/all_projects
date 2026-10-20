"""EM-6 — Dow's primary trend, read from successive swing highs and lows.

`FR-EM-D1`, `FR-EM-D2`. Design: `docs/SRS_edwards_magee_dow_gate.md`.

What the book requires
----------------------
E&M read the primary trend from **successively higher tops *and* bottoms** (or
lower ones) — both conditions, never one — using **closing prices only**, where
*"any penetration, even 0.01, counts"* (tenets 8 and 11). And a trend, once
read, **stands until reversal is definitely signalled** (tenet 12): a higher
high unaccompanied by a higher low is not a reversal and must not clear or
flip the state.

The one judgment E&M leave open
--------------------------------
They never quantify the reaction that separates one top from the next — a
secondary reaction is recognised by eye, and tenet 10 describes "lines" as
sideways ranges of roughly 5%. A mechanical reader needs a number, so
`DEFAULT_SWING_PCT` is 5% and is **a choice, not a finding**: the plan sweeps
`{3, 5, 8}%` and reads sign robustness across the grid rather than the peak
cell. Nothing here should be quoted as the book's threshold, because the book
has none.

Pivot alternation, stated because it is a convention
-----------------------------------------------------
Legs strictly alternate, and the series opens on a *rising* leg, so the first
confirmed pivot is always a **high**. That is deterministic and harmless — a
series that opens by falling records its first bar as the high it reversed
from — but it is a convention rather than a deduction from the text.

Causality (C1)
--------------
Single forward pass: the reading at bar *i* depends only on bars 0..*i*. A
pivot is *confirmed* only once price has reversed away from it, which is
backward-looking confirmation and therefore legitimate — the pivot is dated to
the bar where it formed, but it only becomes *visible* at the later bar that
confirmed it, and no earlier reading moves when it does.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence

from app.services.signal.base import OHLCVBar

TREND_UP = "TREND_UP"
TREND_DOWN = "TREND_DOWN"
UNDEFINED = "UNDEFINED"

#: The discretisation of "secondary reaction". See the module docstring: this
#: is a choice the book does not make for us, and the plan sweeps it.
#:
#: Deliberately NOT used as a default argument value. A parameter whose
#: default reads a module constant in the signature is bound once at def
#: time, so patching the constant becomes a silent no-op and a sweep over it
#: reads as "flat — the parameter does not matter". This project has paid for
#: that five times (EM-1 S2, #78, W1, #84, and #87's HISTORY_YEARS), so the
#: resolution happens in the body and `H-D5` asserts it.
DEFAULT_SWING_PCT = 0.05


@dataclass(frozen=True)
class Pivot:
    """A confirmed swing point.

    `index` is the bar the pivot *formed* on; `confirmed_index` is the later
    bar at which the reversal made it visible. They differ, and conflating
    them is how look-ahead enters this kind of code.
    """
    index: int
    confirmed_index: int
    kind: str          # "HIGH" | "LOW"
    price: float


def _resolve(pct: Optional[float]) -> float:
    return DEFAULT_SWING_PCT if pct is None else pct


def confirmed_pivots(bars: Sequence[OHLCVBar],
                     pct: Optional[float] = None) -> List[Pivot]:
    """Swing highs and lows confirmed by a reversal of `pct`, closes only."""
    threshold = _resolve(pct)
    if not bars:
        return []

    pivots: List[Pivot] = []
    rising = True                      # the running extreme is a candidate HIGH
    extreme = bars[0].close
    extreme_index = 0

    for i, bar in enumerate(bars):
        close = bar.close
        if rising:
            if close > extreme:
                extreme, extreme_index = close, i
            elif close <= extreme * (1.0 - threshold):
                pivots.append(Pivot(extreme_index, i, "HIGH", extreme))
                rising = False
                extreme, extreme_index = close, i
        else:
            if close < extreme:
                extreme, extreme_index = close, i
            elif close >= extreme * (1.0 + threshold):
                pivots.append(Pivot(extreme_index, i, "LOW", extreme))
                rising = True
                extreme, extreme_index = close, i

    return pivots


def swing_trend_series(bars: Sequence[OHLCVBar],
                       pct: Optional[float] = None) -> List[str]:
    """Dow's primary trend per bar: one reading for every bar in `bars`.

    Turns UP only when the latest confirmed high **and** low both exceed their
    predecessors, DOWN only when both fall below, and otherwise **holds** the
    previous reading (tenet 12).
    """
    threshold = _resolve(pct)
    if not bars:
        return []

    out: List[str] = []
    trend = UNDEFINED
    highs: List[float] = []
    lows: List[float] = []
    rising = True
    extreme = bars[0].close

    for bar in bars:
        close = bar.close
        if rising:
            if close > extreme:
                extreme = close
            elif close <= extreme * (1.0 - threshold):
                highs.append(extreme)
                rising, extreme = False, close
        else:
            if close < extreme:
                extreme = close
            elif close >= extreme * (1.0 + threshold):
                lows.append(extreme)
                rising, extreme = True, close

        # Both conditions, or the trend stands. Tenets 8 and 12 together.
        if len(highs) >= 2 and len(lows) >= 2:
            if highs[-1] > highs[-2] and lows[-1] > lows[-2]:
                trend = TREND_UP
            elif highs[-1] < highs[-2] and lows[-1] < lows[-2]:
                trend = TREND_DOWN

        out.append(trend)

    return out
