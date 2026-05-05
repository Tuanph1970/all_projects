"""
trading_range.py
Detect trading ranges in a price series.

A trading range is a horizontal corridor that contains price fluctuations
for an extended period (Schwager, Ch. 4).

Algorithm: a window of length `window` qualifies as a trading range if the
spread (max - min) within it is no greater than `max_pct_spread` of the
window's mean price.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import List
import numpy as np


@dataclass
class TradingRange:
    start: int
    end: int          # inclusive
    upper: float
    lower: float
    duration: int

    @property
    def width_pct(self) -> float:
        mid = (self.upper + self.lower) / 2
        return (self.upper - self.lower) / mid

    def __repr__(self) -> str:
        return (f"TradingRange(days {self.start}-{self.end}, "
                f"{self.lower:.2f}-{self.upper:.2f}, "
                f"width={self.width_pct:.1%}, duration={self.duration})")


def detect_trading_ranges(
    prices: np.ndarray,
    window: int = 30,
    max_pct_spread: float = 0.10,
) -> List[TradingRange]:
    """Slide a window over `prices`; merge overlapping qualifying windows."""
    prices = np.asarray(prices, dtype=float)
    n = len(prices)
    if n < window:
        return []

    candidates = []
    for i in range(n - window + 1):
        seg = prices[i:i + window]
        spread_pct = (seg.max() - seg.min()) / seg.mean()
        if spread_pct <= max_pct_spread:
            candidates.append((i, i + window - 1, seg.max(), seg.min()))

    if not candidates:
        return []

    # Merge overlapping windows into one range
    merged: List[TradingRange] = []
    cur_start, cur_end, cur_up, cur_low = candidates[0]
    for s, e, up, low in candidates[1:]:
        if s <= cur_end + 1:
            cur_end = max(cur_end, e)
            cur_up = max(cur_up, up)
            cur_low = min(cur_low, low)
        else:
            merged.append(TradingRange(cur_start, cur_end, cur_up, cur_low,
                                       cur_end - cur_start + 1))
            cur_start, cur_end, cur_up, cur_low = s, e, up, low
    merged.append(TradingRange(cur_start, cur_end, cur_up, cur_low,
                               cur_end - cur_start + 1))
    return merged


if __name__ == "__main__":
    np.random.seed(0)
    # Build 80 days of trading range, then trend up
    rng_part = 100 + 4*np.sin(np.linspace(0, 6*np.pi, 80)) + np.random.normal(0, 0.6, 80)
    trend_part = np.linspace(rng_part[-1], 130, 70) + np.random.normal(0, 0.6, 70)
    prices = np.concatenate([rng_part, trend_part])

    for tr in detect_trading_ranges(prices, window=25, max_pct_spread=0.12):
        print(tr)
