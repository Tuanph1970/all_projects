"""
Concept 1 — The Well-Chosen Example
-----------------------------------
Demonstrates the cherry-picking trap: any system can look brilliant on a
favorable slice of history. We test the SAME system on 100 random windows
and look at the distribution, instead of just the prettiest one.

Run: python concept_01_well_chosen_example.py
"""
import numpy as np

np.random.seed(0)


def random_walk(n, drift=0.0002, vol=0.015, start=100.0):
    rets = np.random.normal(drift, vol, n)
    return start * np.exp(np.cumsum(rets))


def naive_breakout_pnl(prices, N=20):
    """Tiny long-only breakout system. Returns total $ P&L per share."""
    pos = 0
    entry = 0.0
    pnl = 0.0
    for i in range(N, len(prices)):
        hi = max(prices[i - N:i])
        lo = min(prices[i - N:i])
        if pos == 0 and prices[i] > hi:
            pos, entry = 1, prices[i]
        elif pos == 1 and prices[i] < lo:
            pnl += prices[i] - entry
            pos = 0
    if pos == 1:
        pnl += prices[-1] - entry
    return pnl


# --- run the same system on 100 random 6-month windows ---
results = [naive_breakout_pnl(random_walk(120)) for _ in range(100)]
results = np.array(results)

print(f"Trials run        : {len(results)}")
print(f"Best window       : ${results.max():+.2f}    <-- the 'seminar slide'")
print(f"Worst window      : ${results.min():+.2f}")
print(f"Mean across all   : ${results.mean():+.2f}    <-- the honest answer")
print(f"% of windows > 0  : {(results > 0).mean() * 100:.1f}%")
print()
print("Lesson: a single great chart proves nothing. Always look at the")
print("distribution across many independent samples.")
