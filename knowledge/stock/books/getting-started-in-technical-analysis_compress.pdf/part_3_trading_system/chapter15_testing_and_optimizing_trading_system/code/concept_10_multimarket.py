"""
Concept 10 — Multimarket System Testing
---------------------------------------
A trustworthy system should be profitable across a broad portfolio of
markets — not just the one it was tuned on. Rule of thumb from the
chapter: profitability in ~85%+ of actively traded futures markets
(or beating buy-and-hold on a majority of stocks).

Demo: simulate the same system on 10 synthetic markets, report the
distribution of outcomes.

Run: python concept_10_multimarket.py
"""
import numpy as np

np.random.seed(0)


def fake_market(seed, n=2520, drift=None, vol=None):
    rng = np.random.default_rng(seed)
    if drift is None: drift = rng.uniform(-0.0002, 0.0006)
    if vol   is None: vol   = rng.uniform(0.008, 0.025)
    return 100 * np.exp(np.cumsum(rng.normal(drift, vol, n)))


def system_pnl(prices, short_n=10, long_n=40):
    if len(prices) < long_n: return 0.0
    sma_s = np.convolve(prices, np.ones(short_n) / short_n, mode="valid")
    sma_l = np.convolve(prices, np.ones(long_n)  / long_n,  mode="valid")
    sma_s = sma_s[long_n - short_n:]
    aligned_px = prices[long_n - 1:]
    pos = np.where(sma_s > sma_l, 1, -1)
    return np.sum(np.diff(aligned_px) * pos[:-1])


markets = ["Coffee", "Sugar", "Crude", "Gold",   "Corn",
           "Wheat",  "Cocoa", "Soy",   "Cotton", "Lumber"]

print(f"{'Market':<10} {'Total P&L ($/share)':>22}")
print("-" * 35)
pnls = []
for i, m in enumerate(markets):
    px = fake_market(seed=i)
    p  = system_pnl(px)
    pnls.append(p)
    print(f"{m:<10} {p:>22.2f}")

pnls = np.array(pnls)
print("-" * 35)
print(f"% profitable markets : {(pnls > 0).mean() * 100:.0f}%   (target: ~85%+)")
print(f"Mean across markets  : {pnls.mean():.2f}")
print(f"Median               : {np.median(pnls):.2f}")
print()
print("If only 30% of markets are profitable, the system is curve-fit to")
print("the original test market. Diversify in TESTING, not just trading.")
