"""
Concept: Market Characteristic Adjustments
Chapter 14, Schwager.

A criticism of basic trend-following systems: they treat all market
states the same. A 20-day breakout on a quiet bond market is not the
same event as a 20-day breakout on a volatile commodity.

Market characteristic adjustments make the parameters DYNAMIC, contingent
on the current market state. The most natural classifier is volatility.

This transforms a static system into a dynamic one without adding a
fundamentally different rule set.
"""
import numpy as np
import pandas as pd

def realized_volatility(prices, lookback=50):
    """Average 2-day range as a proportion of price (a simple vol proxy)."""
    p = np.asarray(prices, dtype=float)
    rng = np.zeros(len(p))
    for i in range(2, len(p)):
        rng[i] = abs(p[i] - p[i-2]) / p[i]
    return pd.Series(rng).rolling(lookback).mean().values

def adaptive_N(vol, low_thresh=0.04, high_thresh=0.08, low_N=12, mid_N=20, high_N=30):
    """Map volatility regime to a breakout lookback."""
    if np.isnan(vol):       return mid_N
    if vol < low_thresh:    return low_N
    if vol < high_thresh:   return high_N // 1  # mid
    return high_N

def adaptive_breakout(prices):
    p = np.asarray(prices, dtype=float)
    vol = realized_volatility(p, 50)
    sigs, pos = [], 0
    for i in range(50, len(p)):
        N = int(adaptive_N(vol[i]))
        if i < N: continue
        hi, lo = p[i-N:i].max(), p[i-N:i].min()
        if p[i] > hi and pos != 1:
            sigs.append({'day': i, 'N': N, 'price': p[i], 'side': 'BUY'}); pos = 1
        elif p[i] < lo and pos != -1:
            sigs.append({'day': i, 'N': N, 'price': p[i], 'side': 'SELL'}); pos = -1
    return pd.DataFrame(sigs)

if __name__ == '__main__':
    # Two regimes glued together: calm then volatile
    rng = np.random.default_rng(101)
    seg1 = 100 + np.cumsum(rng.normal(0.05, 0.4, 80))
    seg2 = seg1[-1] + np.cumsum(rng.normal(0.10, 2.0, 80))
    prices = np.concatenate([seg1, seg2])

    adapt = adaptive_breakout(prices)
    print("Day | Side | N used | Price")
    for _, r in adapt.iterrows():
        print(f"{int(r['day']):3d} | {r['side']:4s} | {int(r['N']):6d} | {r['price']:6.2f}")
