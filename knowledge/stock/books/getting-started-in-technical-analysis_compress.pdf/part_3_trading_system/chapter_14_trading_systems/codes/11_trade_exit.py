"""
Concept: Trade Exit (and Re-entry)
Chapter 14, Schwager.

In a basic trend-following system, you only exit when an OPPOSITE signal
fires. A trade-exit rule allows liquidation BEFORE that — to:
  - cap losses on losing trades
  - lock in some profit on winners

Two consequences to handle:
  - You must define a RE-ENTRY rule, otherwise the system would miss
    big trends after early exits.
  - The combination (exit + re-entry) introduces whipsaw losses where
    the original trade was actually fine. Trade-exit rules don't always
    improve performance.
"""
import numpy as np
import pandas as pd

def trailing_stop_exit(prices, entry_idx, entry_price, side='LONG',
                        stop_distance=5.0):
    """Trailing stop based on best price since entry."""
    p = np.asarray(prices, dtype=float)
    best = entry_price
    for i in range(entry_idx + 1, len(p)):
        if side == 'LONG':
            best = max(best, p[i])
            if p[i] < best - stop_distance:
                return i, p[i]
        else:
            best = min(best, p[i])
            if p[i] > best + stop_distance:
                return i, p[i]
    return None, None

def reentry_breakout(prices, exit_idx, side='LONG', n=20):
    """Re-enter on a fresh breakout in the original direction."""
    p = np.asarray(prices, dtype=float)
    for i in range(exit_idx + n, len(p)):
        if side == 'LONG' and p[i] > p[exit_idx:i].max():
            return i, p[i]
        if side == 'SHORT' and p[i] < p[exit_idx:i].min():
            return i, p[i]
    return None, None

if __name__ == '__main__':
    rng = np.random.default_rng(111)
    prices = 100 + np.cumsum(rng.normal(0.18, 1.2, 120))
    entry = 20

    print(f"Initial buy day {entry} @ {prices[entry]:.2f}")
    exit_idx, exit_px = trailing_stop_exit(prices, entry, prices[entry],
                                            side='LONG', stop_distance=5.0)
    if exit_idx is None:
        print("No trade-exit; held to end of data.")
    else:
        print(f"Trade exit day {exit_idx} @ {exit_px:.2f}  (P&L: {exit_px-prices[entry]:+.2f})")
        re_idx, re_px = reentry_breakout(prices, exit_idx, side='LONG', n=10)
        if re_idx is not None:
            print(f"Re-entry day {re_idx} @ {re_px:.2f}")
            print(f"Final price {prices[-1]:.2f}, second-trade P&L: {prices[-1]-re_px:+.2f}")
