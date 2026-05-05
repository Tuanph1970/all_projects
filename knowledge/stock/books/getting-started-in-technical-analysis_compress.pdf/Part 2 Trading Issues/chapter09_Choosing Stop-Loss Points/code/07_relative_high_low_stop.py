"""
Chapter 9 — Concept 7: Relative High / Relative Low Stop
A relative low is a bar whose low is below the lows of N bars on each
side. The most recent relative low is a natural stop level for a long.
"""
from typing import List, Optional


def find_relative_lows(lows: List[float], n: int = 10) -> List[int]:
    pivots = []
    for i in range(n, len(lows) - n):
        window = lows[i - n: i + n + 1]
        if lows[i] == min(window) and window.count(lows[i]) == 1:
            pivots.append(i)
    return pivots


def most_recent_relative_low(lows: List[float], n: int = 10) -> Optional[int]:
    pivots = find_relative_lows(lows, n=n)
    return pivots[-1] if pivots else None


def stop_level(lows: List[float], n: int = 10,
               buffer_pct: float = 0.002) -> Optional[float]:
    idx = most_recent_relative_low(lows, n=n)
    if idx is None:
        return None
    return lows[idx] * (1 - buffer_pct)


if __name__ == "__main__":
    lows = [50, 49, 47, 46, 45, 46, 47, 48, 49, 50, 51, 52, 51, 50,
            48, 49, 50, 51, 52, 53, 54, 53, 52, 51, 53, 55, 57, 58,
            59, 60, 58, 57, 56]
    idx = most_recent_relative_low(lows, n=5)
    print(f"Most recent relative low: index {idx}, price {lows[idx]}")
    print(f"Suggested stop: ${stop_level(lows, n=5):.2f}")
