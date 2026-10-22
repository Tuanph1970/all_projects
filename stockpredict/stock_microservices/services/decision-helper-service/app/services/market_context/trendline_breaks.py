"""EM-5 L2 — contacts, penetration, the shakeout, and amendment.

`FR-EM-L4` (counting only), `L5`, `L6`, `L7`.

E&M Ch 14's three tests of a valid penetration, and the one this module
implements is the first:

> **Extent** — a close beyond the line by about **3%** of the stock's price
> (2% in the averages). *"It need not happen in one day."*

Volume is E&M's second test and is *"not required for a downside break"*, so
it is not a gate here. The third — the feeble volume-less rally that rounds
over under the line — is a *pattern of subsequent behaviour*, which makes it
an outcome rather than a filter; see `detect_penetration`'s note on
causality.

Why contacts live here and not behind Gate A
---------------------------------------------
`L1` measured **89 admissible lines per bar** (median; max 216), and most rest
on exactly two anchors. Without a validity threshold a "break" would mean
"something happened to one of 89 lines", which is close to meaning nothing.

E&M already supply the threshold, in the amendment rules, and it is a
**validity rule rather than a score**:

> If the original line rested on only **two** points and the third contact
> penetrates it indecisively, **redraw** across the first and third (or second
> and third) bottoms. If the line has already been **confirmed** by a third or
> fourth bottom, **disregard** the indecisive break.

So two anchors are **provisional** and the third contact **confirms**. That is
why `L2` grew to include counting while the authority *ordering* (contacts ≫
duration > angle) stays a hypothesis behind the gate: counting contacts is a
rule from the book; ranking by a weighted composite is a claim about the
world.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence

from app.services.backtest.market_features import atr_series
from app.services.market_context.dow import confirmed_pivots
from app.services.market_context.trendline import (
    DEFAULT_PIVOT_PCT,
    KIND_UP,
    Trendline,
)
from app.services.signal.base import OHLCVBar

#: How near a close must sit to the line to count as a contact, in ATR units.
#: Tighter than EM-7's 0.5 ATR *band* on purpose: a band asks whether price
#: came back NEAR a level, a contact asks whether price arrived AT the line.
#: A loose tolerance inflates every line's count equally and would saturate
#: the measure, making the authority ordering untestable rather than weak.
CONTACT_TOL_ATR = 0.25

#: E&M's extent test: 3% of price for a stock (2% in the averages). A 1940s
#: NYSE figure and a legitimate default, not a measured one — `CLAUDE.md`
#: rule 3. EM-9 swept the pattern analogue and recommended leaving it at 3%.
PENETRATION_PCT = 0.03

#: The book's "third bottom". Two anchors are provisional.
MIN_CONTACTS_CONFIRMED = 3


@dataclass(frozen=True)
class Penetration:
    bar_index: int
    direction: str          # "down" for an UP line, "up" for a DOWN line
    beyond_pct: float       # how far past the line, as a fraction of the line


@dataclass(frozen=True)
class Amendment:
    original: Trendline
    line: Trendline
    rule: str               # "first_and_third" | "second_and_third"


def _atr(bars: Sequence[OHLCVBar], atr: Optional[Sequence[Optional[float]]]):
    return atr_series(bars) if atr is None else atr


def count_contacts(bars: Sequence[OHLCVBar], line: Trendline, at_index: int,
                   tol_atr: Optional[float] = None,
                   atr: Optional[Sequence[Optional[float]]] = None) -> int:
    """Closes within tolerance of the line, from the first anchor to `at_index`.

    Counted **beyond the second anchor** deliberately: E&M speak of a line
    *"confirmed by a third or fourth bottom"*, and those arrive after the
    original two, so restricting the count to the anchor segment would make
    confirmation impossible by construction.

    Causal — nothing past `at_index` is read.
    """
    if not bars:
        return 0
    tol = CONTACT_TOL_ATR if tol_atr is None else tol_atr
    end = min(at_index, len(bars) - 1)
    if end < line.a_index:
        return 0
    series = _atr(bars, atr)

    hits = 0
    for i in range(line.a_index, end + 1):
        a = series[i] if i < len(series) else None
        c = bars[i].close
        if c <= 0:
            continue
        band = (a * tol) if (a is not None and a > 0) else None
        if band is None:
            # No ATR yet. The anchors are exactly on the line by construction,
            # so they still count; nothing else can be judged.
            if i in (line.a_index, line.b_index):
                hits += 1
            continue
        if abs(c - line.value_at(i)) <= band:
            hits += 1
    return hits


def is_confirmed(bars: Sequence[OHLCVBar], line: Trendline, at_index: int,
                 tol_atr: Optional[float] = None,
                 atr: Optional[Sequence[Optional[float]]] = None) -> bool:
    """E&M's third-bottom test: provisional at two anchors, confirmed at three."""
    return count_contacts(bars, line, at_index, tol_atr, atr) >= MIN_CONTACTS_CONFIRMED


def detect_penetration(bars: Sequence[OHLCVBar], line: Trendline, at_index: int,
                       pct: Optional[float] = None) -> Optional[Penetration]:
    """The first decisive close beyond the line, or `None`.

    **Closes only** (`FR-EM-L3`), which makes E&M's shakeout warning —
    *"a high-volume crack through the line that closes back above it is
    usually a false move"* — **structural** rather than a separate rule: a bar
    whose close stayed on the right side simply is not a penetration, however
    far its low reached.

    **A penetration that price later recovers is still a penetration.**
    Whether a break failed is only knowable afterwards, so making it a
    condition on *recording* the break would be look-ahead. The recovery is an
    outcome, and outcomes are Gate A's subject.

    The scan starts after `b_index` because it cannot do otherwise:
    `FR-EM-L2` guarantees the price track never crosses the line between its
    anchors.
    """
    if not bars:
        return None
    threshold = PENETRATION_PCT if pct is None else pct
    end = min(at_index, len(bars) - 1)
    up_line = line.kind == KIND_UP

    for i in range(line.b_index + 1, end + 1):
        c = bars[i].close
        if c <= 0:
            continue
        v = line.value_at(i)
        if v <= 0:
            continue
        beyond = (v - c) / v if up_line else (c - v) / v
        if beyond >= threshold:
            return Penetration(bar_index=i,
                               direction="down" if up_line else "up",
                               beyond_pct=round(beyond, 6))
    return None


def _indecisively_broken(bars: Sequence[OHLCVBar], line: Trendline,
                         at_index: int, pct: float) -> Optional[int]:
    """A close beyond the line but by LESS than the extent test demands."""
    end = min(at_index, len(bars) - 1)
    up_line = line.kind == KIND_UP
    for i in range(line.b_index + 1, end + 1):
        c = bars[i].close
        if c <= 0:
            continue
        v = line.value_at(i)
        if v <= 0:
            continue
        beyond = (v - c) / v if up_line else (c - v) / v
        if 0.0 < beyond < pct:
            return i
    return None


def amend_line(bars: Sequence[OHLCVBar], line: Trendline, at_index: int,
               *,
               pct: Optional[float] = None,
               pivot_pct: Optional[float] = None,
               tol_atr: Optional[float] = None) -> Optional[Amendment]:
    """E&M's amendment rule, applied explicitly and recorded.

    > If the original line rested on only **two** points and the third contact
    > penetrates it indecisively, redraw across the first and third (or second
    > and third) bottoms. If the line has already been **confirmed**, disregard
    > the indecisive break.

    Both redraws are permitted by the book, so the choice is made
    deterministically and for a stated reason: **first-and-third is preferred**
    because the book names it first, and second-and-third is used only when
    the first-and-third redraw would be cut by the price track. Returning an
    `Amendment` rather than a bare line keeps the original attached, so an
    amended line is never silently a different line.
    """
    if not bars:
        return None
    threshold = PENETRATION_PCT if pct is None else pct
    scale = DEFAULT_PIVOT_PCT if pivot_pct is None else pivot_pct
    end = min(at_index, len(bars) - 1)
    series = atr_series(bars)

    # Confirmed lines disregard an indecisive break.
    if is_confirmed(bars, line, end, tol_atr, series):
        return None
    if _indecisively_broken(bars, line, end, threshold) is None:
        return None

    want = "LOW" if line.kind == KIND_UP else "HIGH"
    third = next(
        (p for p in confirmed_pivots(bars, pct=scale)
         if p.kind == want and p.index > line.b_index
         and p.confirmed_index <= end and p.price > 0),
        None,
    )
    if third is None:
        return None

    up_line = line.kind == KIND_UP
    for rule, a_idx, a_price in (("first_and_third", line.a_index, line.a_price),
                                 ("second_and_third", line.b_index, line.b_price)):
        run = third.index - a_idx
        if run <= 0:
            continue
        slope = (third.price - a_price) / run
        cut = False
        for i in range(a_idx, third.index + 1):
            c = bars[i].close
            if c <= 0:
                continue
            v = a_price + slope * (i - a_idx)
            if (c < v - 1e-9) if up_line else (c > v + 1e-9):
                cut = True
                break
        if cut:
            continue
        return Amendment(
            original=line,
            line=Trendline(kind=line.kind, a_index=a_idx, b_index=third.index,
                           a_price=a_price, b_price=third.price, slope=slope,
                           anchors_confirmed_at=max(line.anchors_confirmed_at,
                                                    third.confirmed_index)),
            rule=rule,
        )
    return None


__all__ = [
    "CONTACT_TOL_ATR",
    "MIN_CONTACTS_CONFIRMED",
    "PENETRATION_PCT",
    "Amendment",
    "Penetration",
    "amend_line",
    "count_contacts",
    "detect_penetration",
    "is_confirmed",
]
