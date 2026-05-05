"""
Support and Resistance Levels as exit objectives.

For a long position, set an initial objective at or just below a known
resistance level (typically a prior significant high or a concentration
of prior relative highs).

For a short position, set the objective at or just above known support.

Per Schwager: these levels usually serve as TEMPORARY rather than major
objectives — so plan to potentially re-enter at a better price if a
reaction develops.
"""

from dataclasses import dataclass
from typing import List, Optional, Tuple
import numpy as np


@dataclass
class Position:
    side: str          # "long" or "short"
    entry: float
    quantity: int


def find_relative_highs(prices: List[float], window: int = 5) -> List[Tuple[int, float]]:
    """Return (index, price) for points that are the highest in +/- `window`."""
    out = []
    for i in range(window, len(prices) - window):
        local = prices[i - window: i + window + 1]
        if prices[i] == max(local) and prices[i] > prices[i - 1]:
            out.append((i, prices[i]))
    return out


def find_relative_lows(prices: List[float], window: int = 5) -> List[Tuple[int, float]]:
    out = []
    for i in range(window, len(prices) - window):
        local = prices[i - window: i + window + 1]
        if prices[i] == min(local) and prices[i] < prices[i - 1]:
            out.append((i, prices[i]))
    return out


def cluster_levels(levels: List[float], tolerance_pct: float = 0.015
                   ) -> List[Tuple[float, int]]:
    """Group nearby price levels and return (avg_price, count) per cluster."""
    if not levels:
        return []
    sorted_l = sorted(levels)
    clusters = [[sorted_l[0]]]
    for p in sorted_l[1:]:
        if abs(p - clusters[-1][-1]) / clusters[-1][-1] <= tolerance_pct:
            clusters[-1].append(p)
        else:
            clusters.append([p])
    return [(sum(c) / len(c), len(c)) for c in clusters]


def set_objective(position: Position,
                  prices: List[float],
                  buffer_pct: float = 0.005) -> Optional[float]:
    """Place exit objective just inside the nearest relevant S/R cluster.
    `buffer_pct` reserves a small cushion so the order can fill before the
    crowd's order does."""
    current = prices[-1]
    if position.side == "long":
        highs = [p for _, p in find_relative_highs(prices)]
        clusters = cluster_levels(highs)
        candidates = [(price, count) for price, count in clusters if price > current]
        if not candidates:
            return None
        # Pick the strongest cluster within the next 10% of price
        nearby = [c for c in candidates if c[0] <= current * 1.10]
        chosen = (sorted(nearby, key=lambda c: -c[1]) or candidates)[0]
        return chosen[0] * (1 - buffer_pct)
    else:  # short
        lows = [p for _, p in find_relative_lows(prices)]
        clusters = cluster_levels(lows)
        candidates = [(price, count) for price, count in clusters if price < current]
        if not candidates:
            return None
        nearby = [c for c in candidates if c[0] >= current * 0.90]
        chosen = (sorted(nearby, key=lambda c: -c[1]) or candidates)[0]
        return chosen[0] * (1 + buffer_pct)


# --- demo ---------------------------------------------------------------
if __name__ == "__main__":
    np.random.seed(7)
    # Synthetic price series: prior highs cluster around 100, then a pullback,
    # then a current rally heading back toward that resistance zone.
    series = (np.concatenate([
        np.linspace(80, 100, 25),
        np.linspace(100, 88, 15),
        np.linspace(88, 100.5, 15),
        np.linspace(100.5, 82, 25),
        np.linspace(82, 96, 30),
    ]) + np.random.normal(0, 0.4, 110)).tolist()

    pos = Position(side="long", entry=83.0, quantity=100)
    objective = set_objective(pos, series)
    current = series[-1]
    print(f"Current price: {current:.2f}")
    print(f"Objective for long position: {objective:.2f}")
    if objective:
        gain_per_share = objective - pos.entry
        gain_total = gain_per_share * pos.quantity
        print(f"Implied gain: ${gain_per_share:.2f}/share x {pos.quantity} "
              f"= ${gain_total:.2f}")
    # Sample output:
    #   Current price: 96.20
    #   Objective for long position: 99.51
    #   Implied gain: $16.51/share x 100 = $1651.13
