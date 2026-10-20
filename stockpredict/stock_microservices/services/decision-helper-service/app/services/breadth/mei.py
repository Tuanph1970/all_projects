"""EM-4 — the Magee Evaluative Index (E&M Ch 38, applied in Ch 42).

One of the book's genuinely original tools, and the only E&M candidate that
competes with nothing: there is no breadth measure anywhere in this system and
no portfolio-level exposure scaling.

Magee's construction, verbatim in method: keep daily charts on (say) 100
stocks; at the end of each week mark each chart **+** or **−** according to
your judgment of whether it is in a bullish or bearish *major* trend; total
them. *"If 75 are plus, the market looks 75% Bullish to you."*

His premise is a statistical demolition of the averages. Of ~700 listed stocks
around 1929, only **184** made their highs in Aug–Oct 1929 and crashed with
the index — *"in other words, only 27% of the stocks acted the way everybody
knows all stocks acted."* The index is an abstraction; breadth is what
actually happened.

What replaces Magee's judgment
------------------------------
He marked charts by eye and said so: the index *"is a reflection of the
judgment and opinion of the person who is maintaining it"*. We already have an
objective stand-in — `compute_regime`, which the backtest calls on every bar
and which returns TREND_UP / TREND_DOWN / RANGE from a fast/slow MA spread.
TREND_UP is Magee's **+**.

That is a deliberate substitution and it changes the measure's character: it
is mechanical and reproducible where his was expert and personal. Whether the
mechanical version carries the information he claimed for his is exactly what
the `EM-4` study tests, rather than assuming.

Causality
---------
Each day's reading is computed from bars **up to and including that day** and
nothing later, per symbol. `compute_regime` reads only the tail of what it is
given, so slicing the history at day *i* is sufficient and a test asserts that
appending future bars leaves every past reading unchanged.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Dict, List, Optional, Sequence

from app.services.backtest.market_features import compute_regime
from app.services.signal.base import OHLCVBar

#: Below this many classifiable symbols a reading is withheld rather than
#: reported on a thin universe. Magee kept ~100 charts; a reading off three
#: would be noise wearing a percentage sign.
MIN_UNIVERSE = 10


@dataclass(frozen=True)
class MeiPoint:
    """One day's breadth reading."""
    day: date
    mei: float                  # % of the universe in a bullish major trend
    bullish: int
    bearish: int
    neutral: int
    classified: int

    @property
    def mei_excluding_neutral(self) -> Optional[float]:
        """Magee marked each chart **+ or −** with no neutral option, so the
        binary reading forces RANGE out of the denominator.

        Reported alongside `mei` rather than instead of it, because the two
        answer different questions: `mei` is "what share of the market is
        advancing", this is "of the stocks that have a direction, what share
        is up". The primary measure is `mei`, which is the direct reading of
        "if 75 are plus, the market looks 75% Bullish".
        """
        directional = self.bullish + self.bearish
        if directional == 0:
            return None
        return self.bullish / directional * 100.0


def compute_mei_series(
    bars_by_symbol: Dict[str, Sequence[OHLCVBar]],
    min_universe: int = MIN_UNIVERSE,
) -> List[MeiPoint]:
    """The breadth series, one point per trading day the universe shares.

    Causal by construction: day *i*'s reading uses each symbol's bars up to
    day *i* only.
    """
    # Index each symbol's bars by date so a day can be sliced per symbol
    # without assuming the calendars line up — they do not, since symbols
    # list at different times and halt independently.
    by_symbol: Dict[str, List[OHLCVBar]] = {
        sym: sorted(bars, key=lambda b: b.day if hasattr(b, "day") else b.date)
        for sym, bars in bars_by_symbol.items()
    }
    all_days = sorted({b.date for bars in by_symbol.values() for b in bars})

    cursors: Dict[str, int] = {sym: 0 for sym in by_symbol}
    out: List[MeiPoint] = []

    for day in all_days:
        bullish = bearish = neutral = 0
        for sym, bars in by_symbol.items():
            # Advance this symbol's cursor to the last bar at or before `day`.
            i = cursors[sym]
            while i < len(bars) and bars[i].date <= day:
                i += 1
            cursors[sym] = i
            if i == 0:
                continue
            regime = compute_regime(bars[:i])
            if regime == "TREND_UP":
                bullish += 1
            elif regime == "TREND_DOWN":
                bearish += 1
            elif regime == "RANGE":
                neutral += 1
            # UNDEFINED means too little history: not counted either way.

        classified = bullish + bearish + neutral
        if classified < min_universe:
            continue
        out.append(MeiPoint(
            day=day,
            mei=round(bullish / classified * 100.0, 4),
            bullish=bullish, bearish=bearish, neutral=neutral,
            classified=classified,
        ))
    return out


def percentile_of(series: Sequence[MeiPoint], index: int) -> Optional[float]:
    """Where day `index`'s reading sits in the history **up to that day**.

    E&M read the MEI against its own past — *"all major stock market Bottoms
    have corresponded with extremely low MEI readings"* is a statement about
    extremes, and an extreme is only definable against a distribution. Using
    the whole series would be look-ahead, so the window is strictly the past.
    """
    if index <= 0 or index >= len(series):
        return None
    past = [p.mei for p in series[:index]]
    if not past:
        return None
    below = sum(1 for v in past if v < series[index].mei)
    return below / len(past) * 100.0
