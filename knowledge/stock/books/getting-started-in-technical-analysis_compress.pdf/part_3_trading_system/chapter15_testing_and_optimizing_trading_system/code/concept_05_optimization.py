"""
Concept 5 — Optimization (with Parameter Stability)
---------------------------------------------------
Optimization = finding the best parameter set on past data.
Naively picking the absolute peak is dangerous — peaks are often flukes.
Better: pick from a broad PLATEAU of decent performance.

Run: python concept_05_optimization.py
"""
import numpy as np

np.random.seed(7)


def synthetic_profit(short_n, long_n):
    """Toy profit landscape: smooth ridge + isolated lucky spikes."""
    base = 100 * np.exp(-((short_n - 10)**2 + (long_n - 50)**2) / 600)
    fluke = 0
    if short_n == 5 and long_n == 25:
        fluke = 130
    return base + fluke + np.random.normal(0, 8)


# sweep parameter grid
best_value = -np.inf
best_set   = None
plateau_score = -np.inf
plateau_set   = None

results = {}
for s in range(2, 21):
    for l in range(20, 81, 4):
        results[(s, l)] = synthetic_profit(s, l)

# strategy 1 — naive: pick the single peak
best_set, best_value = max(results.items(), key=lambda kv: kv[1])

# strategy 2 — robust: pick the set whose neighborhood average is highest
def neighbor_avg(s, l, radius=3):
    vals = [v for (a, b), v in results.items()
            if abs(a - s) <= radius and abs(b - l) <= radius]
    return np.mean(vals)

plateau_set, plateau_score = max(
    results.keys(),
    key=lambda k: neighbor_avg(*k)), 0.0
plateau_score = neighbor_avg(*plateau_set)

print("Strategy 1 — naive peak picker:")
print(f"  best (short, long) = {best_set},  in-sample profit = ${best_value:.0f}")
print()
print("Strategy 2 — neighborhood-aware (robust) picker:")
print(f"  best (short, long) = {plateau_set},  plateau score = ${plateau_score:.0f}")
print()
print("Why prefer strategy 2: a peak that disappears 2 ticks in either")
print("direction is almost certainly noise, not signal.")
