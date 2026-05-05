"""
Concept: Diversification (and Single Market System Variation)
Chapter 14, Schwager.

Standard meaning: spread trading across many markets. The chapter
points out that diversification has THREE levels:
  1. Multiple markets
  2. Multiple systems per market
  3. Multiple variations of each system per market

A "Single Market System Variation" (SMSV) is one specific (system,
parameter set, market) combo. The full portfolio is a collection of
SMSVs.

Two benefits beyond the headline reduction in drawdowns:
  - Insurance against missing rare, giant moves.
  - Smoother equity curve = ability to take more leverage per market.
"""
import numpy as np
import pandas as pd

def max_drawdown(equity):
    peak = np.maximum.accumulate(equity)
    dd = (equity - peak) / peak
    return dd.min()

def simulate_market(seed, n=250, mu=0.0006, sigma=0.018):
    rng = np.random.default_rng(seed)
    rets = rng.normal(mu, sigma, n)
    return np.cumprod(1 + rets)

if __name__ == '__main__':
    n = 250
    markets = [simulate_market(seed=s, n=n) for s in [1, 2, 3, 4, 5, 6]]

    # Single-market portfolio
    eq_single = markets[0]

    # Equal-weight 6-market portfolio
    rets = np.column_stack([np.diff(np.log(m)) for m in markets])
    portfolio_rets = rets.mean(axis=1)
    eq_port = np.cumprod(1 + portfolio_rets)

    print(f"Single market : final equity {eq_single[-1]:.3f}, max DD {max_drawdown(eq_single)*100:6.2f}%")
    print(f"6-mkt portfolio: final equity {eq_port[-1]:.3f}, max DD {max_drawdown(eq_port)*100:6.2f}%")

    # Show how an SMSV portfolio differs from a single SMSV
    print()
    print("If equity allows, you can also diversify within a market by trading")
    print("multiple parameter sets (e.g., breakout N=20, N=40, N=60 simultaneously).")
    print("This is the SMSV (Single Market System Variation) framework.")
