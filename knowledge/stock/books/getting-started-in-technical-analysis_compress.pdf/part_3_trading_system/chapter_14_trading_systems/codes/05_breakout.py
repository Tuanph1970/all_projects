"""
Concept: Breakout System
Chapter 14, Schwager.

The premise: a market's ability to push to a new high (or low) suggests
that the move will continue in that direction.

Rules:
  1. Cover short and go long  if today's close > prior N-day high
  2. Cover long  and go short if today's close < prior N-day low

N controls sensitivity:
  - Small N (e.g. 7)  -> earlier reversals, many false signals
  - Large N (e.g. 40) -> fewer signals, slower entry, smaller per-trade losses
"""
import numpy as np
import pandas as pd

def breakout_system(prices, n):
    """Stop-and-reverse breakout. Returns DataFrame of signals + position."""
    p = np.asarray(prices, dtype=float)
    pos = np.zeros(len(p), dtype=int)
    signals = []
    cur = 0
    for i in range(n, len(p)):
        prior_high = p[i-n:i].max()
        prior_low  = p[i-n:i].min()
        if p[i] > prior_high and cur != 1:
            signals.append({'day': i, 'price': p[i], 'side': 'BUY'})
            cur = 1
        elif p[i] < prior_low and cur != -1:
            signals.append({'day': i, 'price': p[i], 'side': 'SELL'})
            cur = -1
        pos[i] = cur
    return pd.DataFrame(signals), pos

def round_trip_pnl(signals_df):
    pnl = 0.0
    for (_, a), (_, b) in zip(signals_df.iloc[:-1].iterrows(),
                              signals_df.iloc[1:].iterrows()):
        sign = 1 if a['side'] == 'BUY' else -1
        pnl += sign * (b['price'] - a['price'])
    return pnl

if __name__ == '__main__':
    rng = np.random.default_rng(55)
    prices = 100 + np.cumsum(rng.normal(0.20, 1.4, 150))

    for n in (7, 20, 40):
        sigs, _ = breakout_system(prices, n)
        print(f"N={n:2d}: {len(sigs):2d} signals, "
              f"closed-trade P&L = {round_trip_pnl(sigs):+.2f}")
