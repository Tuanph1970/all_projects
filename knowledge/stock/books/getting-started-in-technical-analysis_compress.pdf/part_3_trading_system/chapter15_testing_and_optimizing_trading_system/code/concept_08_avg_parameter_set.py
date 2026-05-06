"""
Concept 8 — Average Parameter Set Performance
---------------------------------------------
An alternative to walk-forward testing: define ALL parameter sets you
care about up-front, run them all, and use the AVERAGE (across all sets,
not just the profitable ones) as your honest estimate of the system's
edge.

Run: python concept_08_avg_parameter_set.py
"""
import numpy as np

np.random.seed(42)


def synthetic_returns(seed, n=500):
    rng = np.random.default_rng(seed)
    return rng.normal(0.0004, 0.013, n)


def system_pnl(returns, lookback, threshold):
    """Trivial momentum filter: only trade when |trailing| > threshold."""
    pnl = 0.0
    for t in range(lookback, len(returns)):
        signal_strength = np.sum(returns[t - lookback:t])
        if abs(signal_strength) > threshold:
            pnl += np.sign(signal_strength) * returns[t]
    return pnl


market = synthetic_returns(seed=99)

# define the FULL parameter grid up-front (no peeking)
lookbacks  = [5, 10, 15, 20, 30, 50]
thresholds = [0.00, 0.01, 0.02, 0.03]

results = {}
for lb in lookbacks:
    for th in thresholds:
        results[(lb, th)] = system_pnl(market, lb, th)

values = np.array(list(results.values()))
best   = max(results.items(), key=lambda kv: kv[1])

print(f"Number of parameter sets : {len(results)}")
print(f"Best (cherry-picked)     : {best[0]} -> {best[1]:+.4f}")
print(f"Worst                    : {min(values):+.4f}")
print(f"AVERAGE across all sets  : {values.mean():+.4f}   <-- honest estimate")
print(f"% of sets profitable     : {(values > 0).mean() * 100:.0f}%")
print()
print("If the AVERAGE across all sets is barely positive, your system")
print("doesn't have real edge — the 'best' set is just lucky noise.")
