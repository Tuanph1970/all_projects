"""
Concept 3 — Time Stability
--------------------------
Time stability = consistency of returns across SUB-periods of the test
window. Two systems can have the same total return but very different
year-by-year reliability. The lumpy one is dangerous because you might
start trading right before its multi-year flat stretch.

Run: python concept_03_time_stability.py
"""
import numpy as np

np.random.seed(11)

# both systems have the same approximate cumulative gain over 15 years
sys_A = np.random.normal(2,  4, 15);  sys_A[[3, 8, 11]] = [55, 48, 60]   # lumpy
sys_B = np.random.normal(11, 4, 15);  sys_B[2] = -3                       # steady

def report(name, returns):
    cum = np.sum(returns)
    pct_pos = (returns > 0).mean() * 100
    coef_var = np.std(returns) / np.mean(returns) if np.mean(returns) else float("inf")
    worst = returns.min()
    print(f"{name}")
    print(f"  cumulative return   : {cum:6.1f}%")
    print(f"  % positive years    : {pct_pos:5.1f}%")
    print(f"  worst single year   : {worst:5.1f}%")
    print(f"  coef. of variation  : {coef_var:5.2f}   (lower = more time-stable)")
    print()

report("System A (3 hero years carry the rest)", sys_A)
report("System B (steady winner)",                sys_B)

print("Same total profit, very different psychological + practical risk.")
print("Prefer System B — its edge is reproducible across time.")
