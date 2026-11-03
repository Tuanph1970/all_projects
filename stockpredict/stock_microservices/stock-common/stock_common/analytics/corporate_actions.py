"""Detect price discontinuities that trading cannot explain (Backlog #119).

WHAT THIS IS ACTUALLY FOR, measured 2026-11-03 and not what it looks like.

The stored TCB history fell from 33.80 (2026-10-26) to 22.37 (2026-10-27), a
-33.8% overnight move. Vietnam's boards cap a session at +/-7% (HOSE), +/-10%
(HNX) or +/-15% (UPCoM), so that move is ARITHMETICALLY IMPOSSIBLE as trading.

The obvious reading is "the series is not adjusted for the stock dividend". That
reading is WRONG, and the difference matters because it changes the fix. Asked
directly, vnstock/VCI returns a CONTINUOUS series across that date -- 22.80,
22.53, 22.37 -- because the provider restates the entire prior history when a
share-count event changes the scale. Backlog #56 documented exactly that and
verified it against TCB's June 2024 bonus issue.

The discontinuity is OURS. `_top_up_prices` fetches only the bars after the last
stored date, so when the provider restates history, the already-stored pre-event
rows keep the old scale and the newly appended rows arrive on the new one. The
seam is the artifact. The repair is therefore to RE-FETCH the full history the
provider has already adjusted -- never to compute our own adjustment factor on
top of a series that is adjusted everywhere except at one seam.

So this module only ever DETECTS. It deliberately exposes no `adjust()`
function, because the correct remedy is upstream data, and a local
back-adjustment would silently diverge from the provider the next time a
symbol's history were re-pulled.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Optional, Sequence

#: Largest single-session move we will believe was trading.
#:
#: Vietnam caps daily moves per board: HOSE +/-7%, HNX +/-10%, UPCoM +/-15%. The
#: board is not known per symbol at this layer, so the default is the LOOSEST of
#: the three. A tighter 7% would flag every legitimate HNX and UPCoM limit day
#: as a data fault, and a detector that cries wolf on real trading gets tuned
#: out -- which costs more than the misses it prevents.
#:
#: The comparison is strictly greater-than, so a UPCoM limit-up of exactly
#: +15.0% is NOT flagged. Every real seam in this database clears 15% easily:
#: TCB -33.8% (2026-10-27), HDB -26.6% (2021-07-19), TPB -17.7% (2021-07-09),
#: VPB -17.5% (2021-07-01) -- all banks, all share-count events.
MAX_BELIEVABLE_DAILY_MOVE_PCT = 15.0


@dataclass(frozen=True)
class PriceSeam:
    """One overnight move too large to have been trading.

    `ratio` is prev/current, which reads as the share-count factor: TCB's
    33.80 -> 22.37 gives about 1.51, i.e. roughly a 3-for-2 issue.
    """
    index: int
    date: Optional[str]
    prev_close: float
    close: float
    move_pct: float
    ratio: Optional[float]

    def as_dict(self) -> dict:
        return {
            "index": self.index, "date": self.date,
            "prev_close": self.prev_close, "close": self.close,
            "move_pct": self.move_pct, "ratio": self.ratio,
            # kept for the #118 narrator, which named it bar_index first
            "bar_index": self.index,
        }


def _as_float(v: Any) -> Optional[float]:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if f != f else f          # NaN -> None


def find_price_seams(
    closes: Sequence[Any],
    dates: Optional[Sequence[Any]] = None,
    *,
    max_move_pct: float = MAX_BELIEVABLE_DAILY_MOVE_PCT,
) -> List[PriceSeam]:
    """Every overnight move beyond `max_move_pct`, oldest first.

    Never raises. A missing, non-numeric or non-positive prior close is skipped
    rather than divided by.

    An empty list is the normal answer: only four seams exist across five years
    and ~43,000 rows in this database, so a detector that fired on ordinary bars
    would be useless.
    """
    out: List[PriceSeam] = []
    n = len(closes)
    for i in range(1, n):
        prev, cur = _as_float(closes[i - 1]), _as_float(closes[i])
        if prev is None or cur is None or prev <= 0:
            continue
        move = (cur - prev) / prev * 100.0
        if abs(move) > max_move_pct:
            d = None
            if dates is not None and i < len(dates) and dates[i] is not None:
                d = str(dates[i])[:10]
            out.append(PriceSeam(
                index=i, date=d,
                prev_close=round(prev, 4), close=round(cur, 4),
                move_pct=round(move, 2),
                ratio=round(prev / cur, 4) if cur > 0 else None,
            ))
    return out
