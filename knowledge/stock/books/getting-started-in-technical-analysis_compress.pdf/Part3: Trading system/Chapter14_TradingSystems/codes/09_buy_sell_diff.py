"""
Concept: Differentiation Between Buy and Sell Signals
Chapter 14, Schwager.

Basic trend-following systems use SYMMETRIC rules — same N for buys
and sells. But bull and bear markets often behave differently:
  - Tops tend to break sharply (panic/liquidation).
  - Bottoms tend to form slowly (accumulation).

So a sensible asymmetry is: use a MORE sensitive condition for sells
than for buys (e.g., shorter N for sell breakouts).

Caution: more parameters = more overfitting risk (Chapter 15).
"""
import numpy as np
import pandas as pd

def asymmetric_breakout(prices, N_buy, N_sell):
    p = np.asarray(prices, dtype=float)
    sigs, pos = [], 0
    start = max(N_buy, N_sell)
    for i in range(start, len(p)):
        hi_buy = p[i-N_buy:i].max()
        lo_sell = p[i-N_sell:i].min()
        if p[i] > hi_buy and pos != 1:
            sigs.append({'day': i, 'price': p[i], 'side': 'BUY', 'N': N_buy}); pos = 1
        elif p[i] < lo_sell and pos != -1:
            sigs.append({'day': i, 'price': p[i], 'side': 'SELL', 'N': N_sell}); pos = -1
    return pd.DataFrame(sigs)

if __name__ == '__main__':
    rng = np.random.default_rng(88)
    up = 100 + np.cumsum(rng.normal(0.25, 0.8, 100))
    down = up[-1] + np.cumsum(-np.abs(rng.normal(0.5, 1.5, 50)))
    prices = np.concatenate([up, down])

    sym = asymmetric_breakout(prices, N_buy=20, N_sell=20)
    asym = asymmetric_breakout(prices, N_buy=30, N_sell=10)

    print("Symmetric (20/20):")
    print(sym.to_string(index=False))
    print()
    print("Asymmetric (buy=30, sell=10):")
    print(asym.to_string(index=False))
