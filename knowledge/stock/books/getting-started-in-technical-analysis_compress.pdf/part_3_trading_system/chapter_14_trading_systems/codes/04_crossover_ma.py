"""
Concept: Crossover Moving Average System
Chapter 14, Schwager.

Trade signals come from the interaction of TWO moving averages:
  - BUY  when short-term MA crosses above long-term MA
  - SELL when short-term MA crosses below long-term MA

Because both series are smoothed, far fewer false signals are produced
than in the simple price-vs-MA system. The simple MA system can be
viewed as a special case where short_n = 1.
"""
import numpy as np
import pandas as pd

def crossover_signals(prices, short_n, long_n):
    s = pd.Series(prices)
    short = s.rolling(short_n).mean().values
    long_ = s.rolling(long_n).mean().values

    sigs, pos = [], 0
    for i in range(long_n, len(prices)):
        prev_diff = short[i-1] - long_[i-1]
        diff = short[i] - long_[i]
        if prev_diff <= 0 and diff > 0 and pos != 1:
            sigs.append((i, prices[i], 'BUY')); pos = 1
        elif prev_diff >= 0 and diff < 0 and pos != -1:
            sigs.append((i, prices[i], 'SELL')); pos = -1
    return sigs, short, long_

if __name__ == '__main__':
    rng = np.random.default_rng(44)
    prices = 100 + np.cumsum(rng.normal(0.15, 1.3, 180))

    sigs, short, long_ = crossover_signals(prices, 10, 40)
    print(f"Crossover MA(10, 40) generated {len(sigs)} signals:")
    for s in sigs:
        print(f"  Day {s[0]:3d}: {s[2]:4s} @ {s[1]:.2f}")

    # Compare to a simple MA-only system on the same data
    from importlib import import_module  # noqa
