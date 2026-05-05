"""
breakout.py
Detect trading-range breakouts with confirmation rules.

Schwager (Ch. 4) emphasizes: a "raw" penetration of a range boundary is
unreliable. Breakouts gain reliability when they include:
  - duration confirmation (N consecutive closes beyond the boundary)
  - magnitude confirmation (penetration of at least P% of the price)
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Literal
import numpy as np


@dataclass
class BreakoutSignal:
    day: int               # day on which signal is confirmed
    direction: Literal['up', 'down']
    breakout_price: float
    boundary: float
    is_confirmed: bool


def detect_breakouts(
    prices: np.ndarray,
    range_upper: float,
    range_lower: float,
    confirm_days: int = 5,
    min_pct_penetration: float = 0.01,
) -> List[BreakoutSignal]:
    """
    Walk through prices and tag breakouts.
    `confirm_days`: number of consecutive closes required beyond the boundary.
    `min_pct_penetration`: required percentage penetration of the boundary.
    """
    prices = np.asarray(prices, dtype=float)
    signals: List[BreakoutSignal] = []
    n = len(prices)

    upper_threshold = range_upper * (1 + min_pct_penetration)
    lower_threshold = range_lower * (1 - min_pct_penetration)

    in_signal = False
    for i in range(confirm_days - 1, n):
        window = prices[i - confirm_days + 1:i + 1]
        if all(p >= upper_threshold for p in window) and not in_signal:
            signals.append(BreakoutSignal(i, 'up', prices[i], range_upper, True))
            in_signal = True
        elif all(p <= lower_threshold for p in window) and not in_signal:
            signals.append(BreakoutSignal(i, 'down', prices[i], range_lower, True))
            in_signal = True
        elif lower_threshold < prices[i] < upper_threshold:
            in_signal = False

    return signals


if __name__ == "__main__":
    np.random.seed(7)
    # 100 days of range, then sustained breakout
    range_part = 100 + 3*np.sin(np.linspace(0, 5*np.pi, 100)) + np.random.normal(0, 0.6, 100)
    # False break
    false_break = np.array([105, 105.5, 104, 102])
    # True break
    true_break = np.array([105.2, 106, 106.5, 107.1, 107.8, 108.4, 109.0])
    extension = np.linspace(109, 118, 30)

    prices = np.concatenate([range_part, false_break, true_break, extension])
    sigs = detect_breakouts(prices, 104.5, 95.5, confirm_days=5, min_pct_penetration=0.005)
    for s in sigs:
        print(s)
