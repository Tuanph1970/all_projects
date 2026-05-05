"""
Concept 1 & 2: Defining Uptrend / Downtrend by relative highs and relative lows.

An UPTREND   = succession of higher highs AND higher lows
A DOWNTREND  = succession of lower lows  AND lower highs

The trend is "intact" until the most recent reaction low (uptrend) or
reaction high (downtrend) is broken.

Reference: Schwager, "Getting Started in Technical Analysis", Ch. 3, p. 33-36.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Literal


@dataclass
class Pivot:
    index: int
    price: float
    kind: Literal["RH", "RL"]   # relative high or relative low


def find_pivots(highs: List[float], lows: List[float], n: int = 3) -> List[Pivot]:
    """Find n-bar fractal pivots: a Relative High is the highest high
    over the surrounding n bars on each side; a Relative Low is the lowest low.

    Args:
        highs, lows: parallel lists of bar highs and lows.
        n: lookback / lookforward window.

    Returns:
        list of Pivot objects in chronological order.
    """
    pivots: List[Pivot] = []
    for i in range(n, len(highs) - n):
        before_h = highs[i - n: i]
        after_h = highs[i + 1: i + n + 1]
        before_l = lows[i - n: i]
        after_l = lows[i + 1: i + n + 1]
        if highs[i] > max(before_h) and highs[i] > max(after_h):
            pivots.append(Pivot(i, highs[i], "RH"))
        elif lows[i] < min(before_l) and lows[i] < min(after_l):
            pivots.append(Pivot(i, lows[i], "RL"))
    return pivots


def classify_trend(pivots: List[Pivot]) -> Literal["uptrend", "downtrend", "no trend"]:
    """Classify trend from the last few pivots.

    Looks at the two most recent highs and two most recent lows.
    """
    rhs = [p for p in pivots if p.kind == "RH"][-2:]
    rls = [p for p in pivots if p.kind == "RL"][-2:]
    if len(rhs) < 2 or len(rls) < 2:
        return "no trend"
    higher_highs = rhs[-1].price > rhs[-2].price
    higher_lows = rls[-1].price > rls[-2].price
    lower_highs = rhs[-1].price < rhs[-2].price
    lower_lows = rls[-1].price < rls[-2].price
    if higher_highs and higher_lows:
        return "uptrend"
    if lower_highs and lower_lows:
        return "downtrend"
    return "no trend"


def trend_broken(pivots: List[Pivot], current_price: float) -> bool:
    """An uptrend is broken when price falls below the most recent reaction low;
    a downtrend is broken when price rises above the most recent reaction high.
    """
    state = classify_trend(pivots)
    if state == "uptrend":
        last_rl = next((p for p in reversed(pivots) if p.kind == "RL"), None)
        return last_rl is not None and current_price < last_rl.price
    if state == "downtrend":
        last_rh = next((p for p in reversed(pivots) if p.kind == "RH"), None)
        return last_rh is not None and current_price > last_rh.price
    return False


if __name__ == "__main__":
    # Demonstration with synthetic uptrend data that has clear swings
    import random, math
    random.seed(0)
    n_bars = 80
    closes = [100 + 0.3 * i + 4 * math.sin(i / 6) + random.gauss(0, 0.4) for i in range(n_bars)]
    highs = [c + 0.5 + random.random() * 0.3 for c in closes]
    lows  = [c - 0.5 - random.random() * 0.3 for c in closes]

    piv = find_pivots(highs, lows, n=3)
    print(f"Found {len(piv)} pivots")
    for p in piv:
        print(f"  bar {p.index:>3}: {p.kind} @ {p.price:6.2f}")

    print("\nTrend classification:", classify_trend(piv))
    print("Trend broken at price 95?", trend_broken(piv, 95.0))
    print("Trend broken at price 110?", trend_broken(piv, 110.0))
