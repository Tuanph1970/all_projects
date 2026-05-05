"""
Concept 6: TD Lines (DeMark's objective trend lines).

From Schwager Ch.3, p.41 (citing Tom DeMark, "The New Science of
Technical Analysis", 1994):

    For uptrend lines: connect the MOST RECENT relative low and the
        MOST RECENT PRECEDING LOWER relative low.
    For downtrend lines: connect the MOST RECENT relative high and the
        MOST RECENT PRECEDING HIGHER relative high.

A "relative low" (with parameter N) is a bar whose low is lower than
the lows of the N preceding and N succeeding bars. Higher N -> fewer
but more significant lines (slower signals).
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class TDLine:
    a_index: int
    a_price: float
    b_index: int
    b_price: float
    slope: float
    kind: str  # "uptrend" or "downtrend"

    def value_at(self, x: int) -> float:
        return self.a_price + self.slope * (x - self.a_index)


def relative_lows(lows: List[float], n: int) -> List[int]:
    """Indices of bars whose low is strictly less than the surrounding N lows."""
    result = []
    for i in range(n, len(lows) - n):
        before = lows[i - n: i]
        after = lows[i + 1: i + n + 1]
        if lows[i] < min(before) and lows[i] < min(after):
            result.append(i)
    return result


def relative_highs(highs: List[float], n: int) -> List[int]:
    """Indices of bars whose high is strictly greater than the surrounding N highs."""
    result = []
    for i in range(n, len(highs) - n):
        before = highs[i - n: i]
        after = highs[i + 1: i + n + 1]
        if highs[i] > max(before) and highs[i] > max(after):
            result.append(i)
    return result


def td_uptrend_line(lows: List[float], n: int = 4) -> Optional[TDLine]:
    """Build the current TD uptrend line.

    Algorithm: scan relative lows from newest to oldest; the most
    recent low is anchor B; find the most recent earlier low that is
    LOWER than B — that becomes anchor A.
    """
    pivots = relative_lows(lows, n)
    if len(pivots) < 2:
        return None
    b = pivots[-1]
    for a in reversed(pivots[:-1]):
        if lows[a] < lows[b]:
            slope = (lows[b] - lows[a]) / (b - a)
            return TDLine(a, lows[a], b, lows[b], slope, "uptrend")
    return None


def td_downtrend_line(highs: List[float], n: int = 4) -> Optional[TDLine]:
    """Build the current TD downtrend line."""
    pivots = relative_highs(highs, n)
    if len(pivots) < 2:
        return None
    b = pivots[-1]
    for a in reversed(pivots[:-1]):
        if highs[a] > highs[b]:
            slope = (highs[b] - highs[a]) / (b - a)
            return TDLine(a, highs[a], b, highs[b], slope, "downtrend")
    return None


if __name__ == "__main__":
    import random
    random.seed(2)
    n_bars = 80
    base = [50 + 0.2 * i for i in range(n_bars)]
    osc = [2 * ((i % 20) / 10 - 1) ** 2 for i in range(n_bars)]
    closes = [b + o + random.gauss(0, 0.4) for b, o in zip(base, osc)]
    highs = [c + 0.6 for c in closes]
    lows = [c - 0.6 for c in closes]

    for nval in (4, 8):
        line = td_uptrend_line(lows, n=nval)
        if line:
            print(f"N={nval}: TD line connects bar {line.a_index} ({line.a_price:.2f}) "
                  f"-> bar {line.b_index} ({line.b_price:.2f}), slope={line.slope:.4f}")
        else:
            print(f"N={nval}: not enough qualifying pivots")
