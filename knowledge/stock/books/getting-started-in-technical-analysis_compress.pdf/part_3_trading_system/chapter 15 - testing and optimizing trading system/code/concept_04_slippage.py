"""
Concept 4 — Realistic Assumptions: Slippage & Transaction Costs
----------------------------------------------------------------
Backtests look great when you assume you can fill at the signal price
with no friction. Real life adds:
  - commissions
  - bid/ask spread
  - market-impact slippage
  - limit-locked days where the market gaps past you with no fill

Run: python concept_04_slippage.py
"""
import numpy as np

np.random.seed(2)


def backtest(prices, signals, commission=0.0, slippage_pct=0.0):
    """
    signals: np.array of {-1, 0, +1} same length as prices.
    Position changes generate fills with friction.
    """
    pos = 0
    cash = 0.0
    n_trades = 0
    for i in range(1, len(prices)):
        new_pos = signals[i]
        if new_pos != pos:
            fill_px = prices[i] * (1 + np.sign(new_pos - pos) * slippage_pct)
            cash -= (new_pos - pos) * fill_px
            cash -= commission
            pos = new_pos
            n_trades += 1
    cash += pos * prices[-1]
    return cash, n_trades


# fake price series + a moderately active signal stream
prices  = 100 * np.exp(np.cumsum(np.random.normal(0.0005, 0.015, 1000)))
signals = np.where(np.random.random(1000) > 0.85,
                   np.random.choice([-1, 1], 1000), 0)
signals = np.where(signals == 0, np.roll(signals, 1), signals)

print(f"{'Scenario':<35} {'Net P&L ($)':>15} {'# trades':>10}")
print("-" * 62)
for label, comm, slip in [
    ("Paper (no friction)",            0.0,  0.0000),
    ("+ commission $5/trade",          5.0,  0.0000),
    ("+ 0.05% slippage",               5.0,  0.0005),
    ("+ realistic ($25 + 0.10%)",     25.0,  0.0010),
    ("+ pessimistic ($50 + 0.25%)",   50.0,  0.0025),
]:
    pnl, n = backtest(prices, signals, comm, slip)
    print(f"{label:<35} {pnl:>15.2f} {n:>10}")

print()
print("A 'profitable' paper system can flip negative once realistic")
print("transaction costs are included. Bake in friction BEFORE you decide.")
