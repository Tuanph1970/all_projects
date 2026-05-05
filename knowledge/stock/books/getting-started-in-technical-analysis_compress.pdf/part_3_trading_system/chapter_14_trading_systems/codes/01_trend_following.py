"""
Concept: Trend-Following Systems (fast vs slow)
Chapter 14, Schwager — "There are only two types of trend-following systems: fast and slow."

The same system architecture with a smaller lookback (fast) catches turns earlier
but generates many false signals; a larger lookback (slow) catches fewer signals
but with cleaner trades.
"""
import numpy as np
import pandas as pd

def breakout_signals(prices, N):
    """Return list of (index, price, side) for an N-day breakout system."""
    p = np.asarray(prices, dtype=float)
    sigs, pos = [], 0
    for i in range(N, len(p)):
        hi = p[i-N:i].max()
        lo = p[i-N:i].min()
        if p[i] > hi and pos != 1:
            sigs.append((i, p[i], 'BUY')); pos = 1
        elif p[i] < lo and pos != -1:
            sigs.append((i, p[i], 'SELL')); pos = -1
    return sigs

def evaluate(prices, signals):
    """Compute simple round-trip P&L from alternating buy/sell signals."""
    pnl = 0.0
    for a, b in zip(signals[:-1], signals[1:]):
        sign = 1 if a[2] == 'BUY' else -1
        pnl += sign * (b[1] - a[1])
    return pnl

if __name__ == '__main__':
    rng = np.random.default_rng(11)
    prices = 100 + np.cumsum(rng.normal(0.2, 1.5, 150))

    fast = breakout_signals(prices, 7)
    slow = breakout_signals(prices, 40)

    print(f"Fast (N=7):  {len(fast)} signals, P&L ≈ {evaluate(prices, fast):+.2f}")
    print(f"Slow (N=40): {len(slow)} signals, P&L ≈ {evaluate(prices, slow):+.2f}")
    print()
    print("Trade-off: more signals = faster reaction + more whipsaws.")
    print("In most markets, slower systems win because reduced losses on false")
    print("signals more than offset the smaller gains from delayed entry.")
