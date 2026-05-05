"""
Concept: Simple Moving Average (SMA) System
Chapter 14, Schwager.

Buy when price closes above the N-day SMA; sell when it closes below.
Weights every day in the window equally (1/N).

Weakness: short-term price spikes that briefly cross the average
generate frequent false signals (whipsaws), even in trending markets.
"""
import numpy as np
import pandas as pd

def sma(prices, n):
    """N-day simple moving average."""
    s = pd.Series(prices)
    return s.rolling(n).mean().values

def sma_signals(prices, n):
    """Generate buy/sell on close-vs-SMA crossover."""
    ma = sma(prices, n)
    sigs, pos = [], 0
    for i in range(n, len(prices)):
        if prices[i] > ma[i] and prices[i-1] <= ma[i-1] and pos != 1:
            sigs.append((i, prices[i], 'BUY')); pos = 1
        elif prices[i] < ma[i] and prices[i-1] >= ma[i-1] and pos != -1:
            sigs.append((i, prices[i], 'SELL')); pos = -1
    return sigs, ma

if __name__ == '__main__':
    # Example matching Table 14.1 in the book — illustrating crossover detection
    closes = [80.50, 81.00, 81.90, 81.40, 83.10, 82.60, 82.20, 83.10, 84.40,
              85.20, 84.60, 83.90, 84.40, 85.20, 86.10, 85.40, 84.10, 89.50,
              83.90, 83.10, 82.50, 81.90, 81.80, 81.60, 82.20, 82.80, 89.40,
              83.80, 83.90, 83.50]
    closes = np.array(closes)

    sigs, ma = sma_signals(closes, 10)
    print("Day | Close  | 10-SMA | Signal")
    for i in range(9, len(closes)):
        sig = ''
        for s in sigs:
            if s[0] == i:
                sig = s[2]; break
        print(f"{i+1:3d} | {closes[i]:6.2f} | {ma[i]:6.2f} | {sig}")
