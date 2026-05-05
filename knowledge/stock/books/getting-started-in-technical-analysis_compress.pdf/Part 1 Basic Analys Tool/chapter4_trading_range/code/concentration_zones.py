"""
concentration_zones.py
Identify support/resistance zones formed by clusters of prior relative
highs and relative lows (Schwager Ch. 4).

The idea: a single prior peak or trough is one data point. When several
relative highs (or lows) cluster in a narrow price band, that band
becomes a stronger zone of resistance (or support).
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Literal
import numpy as np

from support_resistance import find_relative_extremes


@dataclass
class Zone:
    lower: float
    upper: float
    kind: Literal['support', 'resistance']
    member_count: int
    member_days: List[int]

    @property
    def midpoint(self) -> float:
        return (self.lower + self.upper) / 2

    def __repr__(self) -> str:
        return (f"Zone({self.kind} {self.lower:.2f}-{self.upper:.2f}, "
                f"{self.member_count} members)")


def cluster_extremes(values: List[float], indices: List[int],
                     bandwidth_pct: float = 0.02, min_members: int = 3):
    """Greedy 1-D clustering: group values within `bandwidth_pct` of each
    other into the same cluster."""
    if not values:
        return []
    pairs = sorted(zip(values, indices))
    clusters: List[List[tuple]] = []
    current = [pairs[0]]
    for v, idx in pairs[1:]:
        anchor = current[0][0]
        if abs(v - anchor) / anchor <= bandwidth_pct:
            current.append((v, idx))
        else:
            clusters.append(current)
            current = [(v, idx)]
    clusters.append(current)
    return [c for c in clusters if len(c) >= min_members]


def find_zones(prices: np.ndarray, current_day: int,
               n: int = 5, bandwidth_pct: float = 0.02,
               min_members: int = 3) -> List[Zone]:
    p = prices[:current_day + 1]
    p_now = p[-1]
    highs, lows = find_relative_extremes(p, n=n)
    high_vals = [p[i] for i in highs]
    low_vals = [p[i] for i in lows]

    zones: List[Zone] = []

    for cluster in cluster_extremes(high_vals, highs, bandwidth_pct, min_members):
        vals = [v for v, _ in cluster]
        days = [d for _, d in cluster]
        kind = 'resistance' if min(vals) >= p_now else 'support'
        zones.append(Zone(min(vals), max(vals), kind, len(cluster), days))

    for cluster in cluster_extremes(low_vals, lows, bandwidth_pct, min_members):
        vals = [v for v, _ in cluster]
        days = [d for _, d in cluster]
        kind = 'support' if max(vals) <= p_now else 'resistance'
        zones.append(Zone(min(vals), max(vals), kind, len(cluster), days))

    return zones


if __name__ == "__main__":
    np.random.seed(11)
    n = 300
    base = 100 + 3*np.sin(np.linspace(0, 5*np.pi, n))
    p = base + np.random.normal(0, 1.0, n)
    # Plant clustered highs around 108
    for idx in [25, 70, 115, 160]:
        p[idx-1:idx+2] += 5

    zs = find_zones(p, current_day=290, n=5, bandwidth_pct=0.025, min_members=2)
    for z in zs:
        print(z)
