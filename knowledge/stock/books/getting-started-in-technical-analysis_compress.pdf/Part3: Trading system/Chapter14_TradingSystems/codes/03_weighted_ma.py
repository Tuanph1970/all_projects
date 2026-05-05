"""
Concept: Weighted Moving Averages (LWMA, EWMA)
Chapter 14, Schwager.

Different weighting schemes attempt to make recent prices more influential
than older prices. The book's empirical view: weighted MAs do not
consistently outperform simple MAs. Use the simplest form that works.

  - SMA  : equal weight 1/N for the last N days
  - LWMA : weights 1, 2, ..., N (linearly increasing)
  - EWMA : alpha = 2/(N+1); recursive: ewma_t = a*p_t + (1-a)*ewma_{t-1}
"""
import numpy as np
import pandas as pd

def sma(prices, n):
    return pd.Series(prices).rolling(n).mean().values

def lwma(prices, n):
    """Linearly Weighted Moving Average."""
    weights = np.arange(1, n+1)
    out = np.full(len(prices), np.nan)
    for i in range(n-1, len(prices)):
        window = prices[i-n+1:i+1]
        out[i] = np.dot(window, weights) / weights.sum()
    return out

def ewma(prices, n):
    """Exponentially Weighted Moving Average (alpha = 2/(N+1))."""
    a = 2.0 / (n + 1)
    out = np.zeros(len(prices))
    out[0] = prices[0]
    for i in range(1, len(prices)):
        out[i] = a * prices[i] + (1 - a) * out[i-1]
    return out

if __name__ == '__main__':
    rng = np.random.default_rng(33)
    prices = 100 + np.cumsum(rng.normal(0.2, 1.0, 60))
    n = 10

    s = sma(prices, n)
    l = lwma(prices, n)
    e = ewma(prices, n)

    print(f"Day | Price  | SMA    | LWMA   | EWMA")
    for i in range(n-1, len(prices), 5):
        print(f"{i:3d} | {prices[i]:6.2f} | {s[i]:6.2f} | {l[i]:6.2f} | {e[i]:6.2f}")

    print()
    print("Observation: LWMA & EWMA react faster to recent moves,")
    print("but Schwager notes no consistent edge over SMA in real trading.")
