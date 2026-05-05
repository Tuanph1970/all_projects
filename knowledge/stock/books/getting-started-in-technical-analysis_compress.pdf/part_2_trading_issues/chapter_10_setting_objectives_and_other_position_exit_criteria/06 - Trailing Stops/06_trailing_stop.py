"""
Trailing Stops as a position-exit method.

Among the LEAST glamorous, but MOST sensible methods (Schwager).
You will never sell the absolute high or buy the absolute low, but
the approach lets a profitable trade run as long as the trend is
intact, and it has no preset target -- so it doesn't cap upside.

Three common varieties (covered in detail in Chapter 9 too):
    1. Chart-point trailing stop  (e.g. close below most recent N-day low)
    2. Fixed dollar/percent trailing stop
    3. ATR-based trailing stop

Cardinal rule: stops should ONLY be moved in the direction of reducing
risk -- never widened to give a losing position more room.
"""

from dataclasses import dataclass
from typing import List, Optional, Tuple
import numpy as np


@dataclass
class TrailingStopResult:
    exit_index: Optional[int]
    exit_price: Optional[float]
    stop_path: List[float]


def chart_point_trailing_stop(prices: List[float],
                              lookback: int = 10,
                              buffer: float = 0.0
                              ) -> TrailingStopResult:
    """For a long position: stop = (rolling N-day low) - buffer,
    monotonically non-decreasing. Triggered when close < stop."""
    n = len(prices)
    stop = -np.inf
    path = []
    exit_idx = None
    for i in range(n):
        window_lo = min(prices[max(0, i - lookback): i + 1])
        candidate = window_lo - buffer
        if candidate > stop:
            stop = candidate
        path.append(stop)
        if i > 0 and prices[i] < stop:
            exit_idx = i
            break
    return TrailingStopResult(
        exit_index=exit_idx,
        exit_price=prices[exit_idx] if exit_idx is not None else None,
        stop_path=path,
    )


def percent_trailing_stop(prices: List[float],
                          drawdown_pct: float = 0.05
                          ) -> TrailingStopResult:
    """For a long position: stop = highest_close_so_far * (1 - drawdown_pct),
    monotonically non-decreasing."""
    n = len(prices)
    high_water = prices[0]
    stop = high_water * (1 - drawdown_pct)
    path = []
    exit_idx = None
    for i in range(n):
        if prices[i] > high_water:
            high_water = prices[i]
            stop = max(stop, high_water * (1 - drawdown_pct))
        path.append(stop)
        if i > 0 and prices[i] < stop:
            exit_idx = i
            break
    return TrailingStopResult(
        exit_index=exit_idx,
        exit_price=prices[exit_idx] if exit_idx is not None else None,
        stop_path=path,
    )


# --- demo ---------------------------------------------------------------
if __name__ == "__main__":
    np.random.seed(11)
    # Synthetic uptrend that eventually rolls over.
    prices = (40 + np.concatenate([
        np.linspace(0,   6, 20),
        np.linspace(6,   4, 8),
        np.linspace(4,  14, 25),
        np.linspace(14, 11, 8),
        np.linspace(11, 22, 25),
        np.linspace(22, 19, 10),
        np.linspace(19,  8, 24),
    ]) + np.random.normal(0, 0.4, 120)).tolist()

    entry_price = prices[0]
    print(f"Entry price: {entry_price:.2f}")
    print(f"Final price: {prices[-1]:.2f}")
    print(f"Max price during trade: {max(prices):.2f}")

    # Method 1: chart-point trailing stop
    res1 = chart_point_trailing_stop(prices, lookback=10, buffer=0.5)
    if res1.exit_index is not None:
        pnl = res1.exit_price - entry_price
        print(f"\n[Chart-point trailing, 10-day low - 0.5]")
        print(f"  Exit at bar {res1.exit_index}, price {res1.exit_price:.2f}")
        print(f"  P/L per share: {pnl:+.2f}")

    # Method 2: percent trailing stop
    res2 = percent_trailing_stop(prices, drawdown_pct=0.08)
    if res2.exit_index is not None:
        pnl = res2.exit_price - entry_price
        print(f"\n[Percent trailing, 8% drawdown]")
        print(f"  Exit at bar {res2.exit_index}, price {res2.exit_price:.2f}")
        print(f"  P/L per share: {pnl:+.2f}")
    # Sample output (varies with seed):
    #   Entry price: 40.43
    #   Final price: 47.96
    #   Max price during trade: 62.27
    #   [Chart-point trailing, 10-day low - 0.5]
    #     Exit at bar 113, price 51.04
    #     P/L per share: +10.61
