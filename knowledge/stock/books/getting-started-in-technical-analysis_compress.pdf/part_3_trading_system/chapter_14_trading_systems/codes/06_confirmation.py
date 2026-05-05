"""
Concept: Confirmation Conditions
Chapter 14, Schwager.

A confirmation rule waits for a *secondary event* before acting on the
basic system signal. Three common types:

  1) PENETRATION : require the breakout to exceed the level by X% (or X ticks)
  2) TIME DELAY  : re-check the signal D days later; trade only if still valid
  3) PATTERN     : require K thrust days after the signal

Trade-off: confirmation rules cut whipsaws but also delay entry on real
signals, so per-trade gains shrink. They pay off only when the avoided
losses exceed the surrendered profits.
"""
import numpy as np
import pandas as pd

def basic_breakout(prices, n):
    p = np.asarray(prices, dtype=float)
    sigs, pos = [], 0
    for i in range(n, len(p)):
        if p[i] > p[i-n:i].max() and pos != 1:
            sigs.append({'day': i, 'price': p[i], 'side': 'BUY'}); pos = 1
        elif p[i] < p[i-n:i].min() and pos != -1:
            sigs.append({'day': i, 'price': p[i], 'side': 'SELL'}); pos = -1
    return pd.DataFrame(sigs)

def confirm_penetration(prices, n, pct=0.02):
    """Trade only if close penetrates the breakout level by `pct`."""
    p = np.asarray(prices, dtype=float)
    sigs, pos = [], 0
    for i in range(n, len(p)):
        hi, lo = p[i-n:i].max(), p[i-n:i].min()
        if p[i] > hi*(1+pct) and pos != 1:
            sigs.append({'day': i, 'price': p[i], 'side': 'BUY'}); pos = 1
        elif p[i] < lo*(1-pct) and pos != -1:
            sigs.append({'day': i, 'price': p[i], 'side': 'SELL'}); pos = -1
    return pd.DataFrame(sigs)

def confirm_time_delay(prices, n, delay=5):
    """After basic signal, wait `delay` days; trade only if still beyond level."""
    base = basic_breakout(prices, n)
    p = np.asarray(prices, dtype=float)
    confirmed = []
    for _, row in base.iterrows():
        d = int(row['day']) + delay
        if d >= len(p):
            continue
        if row['side'] == 'BUY' and p[d] > row['price']:
            confirmed.append({'day': d, 'price': p[d], 'side': 'BUY'})
        elif row['side'] == 'SELL' and p[d] < row['price']:
            confirmed.append({'day': d, 'price': p[d], 'side': 'SELL'})
    return pd.DataFrame(confirmed)

def confirm_thrust_days(prices, n, k=3):
    """Trade after K consecutive thrust days in the signal direction."""
    base = basic_breakout(prices, n)
    p = np.asarray(prices, dtype=float)
    confirmed = []
    for _, row in base.iterrows():
        idx, side = int(row['day']), row['side']
        cnt = 0
        for j in range(idx+1, min(idx+30, len(p))):
            up = p[j] > p[j-1]
            if side == 'BUY' and up:    cnt += 1
            elif side == 'SELL' and not up: cnt += 1
            else:                       cnt = 0
            if cnt >= k:
                confirmed.append({'day': j, 'price': p[j], 'side': side})
                break
    return pd.DataFrame(confirmed)

if __name__ == '__main__':
    rng = np.random.default_rng(66)
    prices = 100 + np.cumsum(rng.normal(0.05, 1.3, 140))

    n = 15
    print(f"Basic breakout (N={n})              : {len(basic_breakout(prices, n))} signals")
    print(f"+ 2% penetration confirmation       : {len(confirm_penetration(prices, n))} signals")
    print(f"+ 5-day time-delay confirmation     : {len(confirm_time_delay(prices, n))} signals")
    print(f"+ 3 thrust-day confirmation         : {len(confirm_thrust_days(prices, n))} signals")
