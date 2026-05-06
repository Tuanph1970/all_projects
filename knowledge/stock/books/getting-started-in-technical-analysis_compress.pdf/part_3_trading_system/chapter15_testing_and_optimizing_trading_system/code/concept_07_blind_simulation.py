"""
Concept 7 — Blind Simulation (Walk-Forward Testing)
---------------------------------------------------
Optimize on past window only -> 'lock in' those parameters ->
test on the NEXT (untouched) window. Slide forward and repeat.

The optimization and test windows must NEVER overlap. Otherwise
you're peeking at the answers.

Run: python concept_07_blind_simulation.py
"""
import numpy as np

np.random.seed(0)


def fake_market(n_years=15):
    days = n_years * 252
    return 100 * np.exp(np.cumsum(np.random.normal(0.0003, 0.012, days)))


def breakout_pnl(prices, N):
    pos = 0
    pnl = 0.0
    entry = 0.0
    for i in range(N, len(prices)):
        hi = max(prices[i - N:i])
        lo = min(prices[i - N:i])
        if pos == 0 and prices[i] > hi:
            pos, entry = 1, prices[i]
        elif pos == 1 and prices[i] < lo:
            pnl += prices[i] - entry
            pos = 0
    if pos:
        pnl += prices[-1] - entry
    return pnl


prices = fake_market(15)
year_len = 252
folds = [
    ("1985-1992", 0,           year_len * 8,  year_len * 8,  year_len * 10),
    ("1987-1994", year_len * 2, year_len * 10, year_len * 10, year_len * 12),
    ("1989-1996", year_len * 4, year_len * 12, year_len * 12, year_len * 14),
]

print(f"{'Fold':<10} {'Best N (in-sample)':>20} {'OOS P&L':>15}")
print("-" * 50)
for label, opt_a, opt_b, oos_a, oos_b in folds:
    in_sample = prices[opt_a:opt_b]
    oos       = prices[oos_a:oos_b]
    # optimize on in-sample
    best_N = max(range(5, 60), key=lambda N: breakout_pnl(in_sample, N))
    # test on out-of-sample with the locked-in N
    oos_pnl = breakout_pnl(oos, best_N)
    print(f"{label:<10} {best_N:>20d} {oos_pnl:>15.2f}")

print()
print("Each fold's parameter is chosen using ONLY past data -> closer to")
print("the situation you'll actually face when trading live.")
