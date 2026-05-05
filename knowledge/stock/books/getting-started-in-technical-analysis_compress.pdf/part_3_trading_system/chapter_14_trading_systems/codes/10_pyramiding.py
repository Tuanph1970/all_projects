"""
Concept: Pyramiding
Chapter 14, Schwager.

Basic trend-following systems use a constant unit position size. But
major trends produce most of the system's profit, so it makes sense
to size up when one is in motion. Pyramiding adds units to a winning
position after a defined reaction-and-resumption pattern.

Example pyramid rules (long version):
  1. Reaction defined when net position is long and price closes
     below the prior 10-day low.
  2. After a reaction is defined, a new unit is added on the next
     close above the prior 10-day high — IF:
       (a) the pyramid signal price is above the most recent buy price
       (b) net position size is < max units (e.g., 3)

Stops are tighter on pyramids than on the base position.
"""
import numpy as np
import pandas as pd

def pyramid_long_only(prices, base_signal_idx, max_units=3, react_n=10):
    """Pyramid into an existing long. Returns list of buy events."""
    p = np.asarray(prices, dtype=float)
    units = [{'day': base_signal_idx, 'price': p[base_signal_idx], 'unit': 1}]
    in_reaction = False
    last_buy_price = p[base_signal_idx]

    for i in range(base_signal_idx + react_n, len(p)):
        lo_n = p[i-react_n:i].min()
        hi_n = p[i-react_n:i].max()

        if not in_reaction and p[i] < lo_n:
            in_reaction = True
        elif in_reaction and p[i] > hi_n and p[i] > last_buy_price and len(units) < max_units:
            units.append({'day': i, 'price': p[i], 'unit': len(units)+1})
            last_buy_price = p[i]
            in_reaction = False
    return pd.DataFrame(units)

if __name__ == '__main__':
    rng = np.random.default_rng(99)
    prices = 100 + np.cumsum(rng.normal(0.35, 1.3, 150))

    base_buy = 30
    pyr = pyramid_long_only(prices, base_buy, max_units=3, react_n=10)
    print("Pyramid trade log:")
    print(pyr.to_string(index=False))

    avg_cost = pyr['price'].mean()
    print(f"\nAverage cost per unit: {avg_cost:.2f}")
    print(f"Final price          : {prices[-1]:.2f}")
    print(f"Open profit          : {(prices[-1]-avg_cost)*len(pyr):+.2f}")
