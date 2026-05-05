"""
Concept: Filter
Chapter 14, Schwager.

A filter is a screening rule applied AT the time of the basic signal.
It eliminates trades the system designer believes have a low probability
of success — so the trade is rejected rather than just delayed.

Difference from a confirmation rule:
  - filter      : applied at signal time
  - confirmation: applied AFTER signal time

Classic example: only take MA crossover signals that align with the
direction of the moving average itself (i.e., trade only with the trend).
"""
import numpy as np
import pandas as pd

def sma(prices, n):
    return pd.Series(prices).rolling(n).mean().values

def ma_signals_with_filter(prices, n, use_filter=True):
    """SMA crossover, optionally filtered by MA slope."""
    ma = sma(prices, n)
    sigs, pos = [], 0
    for i in range(n+1, len(prices)):
        ma_rising = ma[i] > ma[i-1]
        cross_up = prices[i] > ma[i] and prices[i-1] <= ma[i-1]
        cross_dn = prices[i] < ma[i] and prices[i-1] >= ma[i-1]
        if cross_up and pos != 1:
            if not use_filter or ma_rising:
                sigs.append({'day': i, 'price': prices[i], 'side': 'BUY'}); pos = 1
        elif cross_dn and pos != -1:
            if not use_filter or not ma_rising:
                sigs.append({'day': i, 'price': prices[i], 'side': 'SELL'}); pos = -1
    return pd.DataFrame(sigs)

def round_trip_pnl(df):
    pnl = 0.0
    for (_, a), (_, b) in zip(df.iloc[:-1].iterrows(), df.iloc[1:].iterrows()):
        sign = 1 if a['side'] == 'BUY' else -1
        pnl += sign * (b['price'] - a['price'])
    return pnl

if __name__ == '__main__':
    rng = np.random.default_rng(77)
    prices = 100 + np.cumsum(rng.normal(0.18, 1.5, 180))

    no_filter = ma_signals_with_filter(prices, 20, use_filter=False)
    filtered  = ma_signals_with_filter(prices, 20, use_filter=True)

    print(f"WITHOUT filter: {len(no_filter):2d} signals, P&L = {round_trip_pnl(no_filter):+.2f}")
    print(f"WITH filter   : {len(filtered):2d} signals, P&L = {round_trip_pnl(filtered):+.2f}")
    print()
    print("Filter rejects signals against the MA's own direction.")
    print("It keeps the trader 'with the trend' and tends to skip whipsaw zones.")
