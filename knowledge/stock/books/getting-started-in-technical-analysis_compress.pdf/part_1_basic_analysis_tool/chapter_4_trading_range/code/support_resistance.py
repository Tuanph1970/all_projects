"""
support_resistance.py
Identify support and resistance levels from prior major highs and lows,
including the role-reversal behavior described in Schwager Ch. 4.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Literal
import numpy as np


@dataclass
class SRLevel:
    price: float
    day: int
    kind: Literal['support', 'resistance']
    source: str  # e.g. 'prior_high', 'prior_low_flipped'

    def __repr__(self) -> str:
        return f"SRLevel({self.kind} @ {self.price:.2f} from day {self.day} [{self.source}])"


def find_relative_extremes(prices: np.ndarray, n: int = 5):
    """A relative high (low) is higher (lower) than the n preceding and
    succeeding bars. Returns (highs_idx, lows_idx)."""
    prices = np.asarray(prices, dtype=float)
    highs, lows = [], []
    for i in range(n, len(prices) - n):
        window = prices[i - n:i + n + 1]
        if prices[i] == window.max() and (window == prices[i]).sum() == 1:
            highs.append(i)
        if prices[i] == window.min() and (window == prices[i]).sum() == 1:
            lows.append(i)
    return highs, lows


def major_highs_lows(prices: np.ndarray, n: int = 5, top_k: int = 3):
    """Return the top_k most-extreme relative highs and lows."""
    highs, lows = find_relative_extremes(prices, n)
    high_vals = sorted(highs, key=lambda i: -prices[i])[:top_k]
    low_vals = sorted(lows, key=lambda i: prices[i])[:top_k]
    return high_vals, low_vals


def levels_at_now(prices: np.ndarray, current_day: int, n: int = 5) -> List[SRLevel]:
    """
    For prices known up to current_day, classify prior major highs/lows as
    support or resistance from the perspective of the current price.
    Schwager's role-reversal rule: once a prior high is decisively
    penetrated, it BECOMES support; once a prior low is decisively
    penetrated, it BECOMES resistance.
    """
    p_now = prices[current_day]
    highs, lows = major_highs_lows(prices[:current_day + 1], n=n, top_k=4)

    levels: List[SRLevel] = []
    for h in highs:
        ph = prices[h]
        if ph > p_now:
            levels.append(SRLevel(ph, h, 'resistance', 'prior_high'))
        else:
            levels.append(SRLevel(ph, h, 'support', 'prior_high_flipped'))
    for l in lows:
        pl = prices[l]
        if pl < p_now:
            levels.append(SRLevel(pl, l, 'support', 'prior_low'))
        else:
            levels.append(SRLevel(pl, l, 'resistance', 'prior_low_flipped'))

    levels.sort(key=lambda x: x.price)
    return levels


if __name__ == "__main__":
    np.random.seed(3)
    n = 200
    p = 100 + np.cumsum(np.random.normal(0.05, 1.0, n))
    p[40] = p[40] + 8   # plant an obvious peak
    p[120] = p[120] - 7 # plant an obvious trough
    for lvl in levels_at_now(p, current_day=180):
        print(lvl)
