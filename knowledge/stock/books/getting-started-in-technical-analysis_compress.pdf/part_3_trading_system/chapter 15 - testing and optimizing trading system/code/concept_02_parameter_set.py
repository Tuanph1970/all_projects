"""
Concept 2 — Parameter & Parameter Set
-------------------------------------
A *parameter* is a knob you can turn (e.g. N in a breakout system).
A *parameter set* is one specific combination of all knob settings
(e.g. {short_MA=10, long_MA=40}).

Demo: same crossover-MA system, sweep across parameter sets.

Run: python concept_02_parameter_set.py
"""
import numpy as np
import itertools

np.random.seed(1)


def crossover_ma_pnl(prices, short_n, long_n):
    if long_n <= short_n or long_n >= len(prices):
        return 0.0
    short_ma = np.convolve(prices, np.ones(short_n) / short_n, mode="valid")
    long_ma  = np.convolve(prices, np.ones(long_n)  / long_n,  mode="valid")
    aligned_short = short_ma[long_n - short_n:]
    aligned_px    = prices[long_n - 1:]
    pos = np.where(aligned_short > long_ma, 1, -1)
    rets = np.diff(aligned_px) * pos[:-1]
    return rets.sum()


prices = 100 * np.exp(np.cumsum(np.random.normal(0.0005, 0.015, 1500)))

shorts = [5, 10, 15, 20]
longs  = [30, 50, 80, 120]

print(f"{'short_MA':>10} {'long_MA':>10} {'P&L ($/share)':>15}")
print("-" * 38)
for s, l in itertools.product(shorts, longs):
    pnl = crossover_ma_pnl(prices, s, l)
    print(f"{s:>10} {l:>10} {pnl:>15.2f}")

print()
print("Each row = one PARAMETER SET. The system's *rules* don't change;")
print("only the knob values do, and signal timing changes drastically.")
