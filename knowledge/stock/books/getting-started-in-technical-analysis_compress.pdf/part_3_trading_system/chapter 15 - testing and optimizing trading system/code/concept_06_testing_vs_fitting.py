"""
Concept 6 — Testing vs Fitting
------------------------------
"Curve fitting" = tuning so many knobs that you describe past noise
perfectly but learn nothing about the future.

Demo: random coin-flip 'returns'. We pick the 'best' parameter on the
first half (in-sample) and see how it does on the second half.
Spoiler: there's no signal in random data, but on enough trials
something will *look* great in-sample.

Run: python concept_06_testing_vs_fitting.py
"""
import numpy as np

np.random.seed(2024)

n_days  = 1000
returns = np.random.normal(0, 0.01, n_days)   # pure noise
in_sample, oos = returns[:500], returns[500:]


def strategy_pnl(rets, lookback):
    """Trade direction = sign of trailing 'lookback' return."""
    pnl = 0.0
    for t in range(lookback, len(rets)):
        signal = np.sign(np.sum(rets[t - lookback:t]))
        pnl += signal * rets[t]
    return pnl


# Try 50 different lookback values, pick the best on in-sample
candidates = range(2, 52)
in_sample_pnls = {k: strategy_pnl(in_sample, k) for k in candidates}
best_lookback  = max(in_sample_pnls, key=in_sample_pnls.get)

print(f"Best in-sample lookback : {best_lookback}")
print(f"In-sample P&L           : {in_sample_pnls[best_lookback]:+.4f}")
print(f"Out-of-sample P&L       : {strategy_pnl(oos, best_lookback):+.4f}")
print()
print("Average across all 50 lookbacks (a more honest estimator):")
print(f"  In-sample mean        : {np.mean(list(in_sample_pnls.values())):+.4f}")
oos_all = [strategy_pnl(oos, k) for k in candidates]
print(f"  Out-of-sample mean    : {np.mean(oos_all):+.4f}")
print()
print("There is no signal here at all — but if you only show the")
print("'best' run, you'd swear you found edge. That's curve fitting.")
