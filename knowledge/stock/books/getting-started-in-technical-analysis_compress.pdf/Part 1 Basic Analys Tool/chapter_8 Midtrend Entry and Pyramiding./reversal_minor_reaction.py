"""
Reversal of Minor Reaction — Chapter 8, Concept 3
Schwager: "Getting Started in Technical Analysis"

Two-phase midtrend entry:
  Phase 1: Detect a counter-trend reaction (N-day extreme)
  Phase 2: Enter on trend resumption (X-day extreme in trend direction)
  Stop: placed at the reaction extreme
"""

import pandas as pd
import numpy as np
from typing import Literal


def n_day_high(prices: pd.Series, n: int) -> pd.Series:
    """Rolling N-day high (highest high of previous N days)."""
    return prices.shift(1).rolling(n).max()


def n_day_low(prices: pd.Series, n: int) -> pd.Series:
    """Rolling N-day low (lowest low of previous N days)."""
    return prices.shift(1).rolling(n).min()


def reversal_of_minor_reaction(
    prices: pd.Series,
    n_reaction: int = 8,
    x_resumption: int = 3,
    direction: Literal["long", "short"] = "short",
) -> pd.DataFrame:
    """
    Generate midtrend re-entry signals using the reversal of
    minor reaction method.

    Parameters:
        prices: Series of closing prices
        n_reaction: N-day window to detect a counter-trend reaction.
            In a downtrend: reaction = new N-day high.
            In an uptrend: reaction = new N-day low.
        x_resumption: X-day window to confirm trend resumption.
            In a downtrend: resumption = close below X-day low.
            In an uptrend: resumption = close above X-day high.
        direction: 'long' for uptrend re-entry, 'short' for downtrend.

    Returns:
        DataFrame with columns:
            date, signal, entry_price, stop_price, risk,
            reaction_start_date, reaction_extreme,
            n_reaction, x_resumption
    """
    nday_high = n_day_high(prices, n_reaction)
    nday_low = n_day_low(prices, n_reaction)
    xday_high = n_day_high(prices, x_resumption)
    xday_low = n_day_low(prices, x_resumption)

    signals = []
    in_reaction = False
    reaction_extreme = None
    reaction_start = None

    for i in range(max(n_reaction, x_resumption) + 1, len(prices)):
        date = prices.index[i]
        price = prices.iloc[i]

        if direction == "short":
            # Phase 1: Detect reaction — price exceeds N-day high
            if not in_reaction and price > nday_high.iloc[i]:
                in_reaction = True
                reaction_extreme = price
                reaction_start = date

            if in_reaction:
                # Track the highest point of the reaction
                reaction_extreme = max(reaction_extreme, price)

                # Phase 2: Trend resumption — close below X-day low
                if price < xday_low.iloc[i]:
                    signals.append({
                        "date": date,
                        "signal": "SELL",
                        "entry_price": round(price, 2),
                        "stop_price": round(reaction_extreme, 2),
                        "risk": round(reaction_extreme - price, 2),
                        "reaction_start_date": reaction_start,
                        "reaction_extreme": round(reaction_extreme, 2),
                        "n_reaction": n_reaction,
                        "x_resumption": x_resumption,
                    })
                    in_reaction = False

        else:  # direction == "long"
            # Phase 1: Detect reaction — price drops below N-day low
            if not in_reaction and price < nday_low.iloc[i]:
                in_reaction = True
                reaction_extreme = price
                reaction_start = date

            if in_reaction:
                # Track the lowest point of the reaction
                reaction_extreme = min(reaction_extreme, price)

                # Phase 2: Trend resumption — close above X-day high
                if price > xday_high.iloc[i]:
                    signals.append({
                        "date": date,
                        "signal": "BUY",
                        "entry_price": round(price, 2),
                        "stop_price": round(reaction_extreme, 2),
                        "risk": round(price - reaction_extreme, 2),
                        "reaction_start_date": reaction_start,
                        "reaction_extreme": round(reaction_extreme, 2),
                        "n_reaction": n_reaction,
                        "x_resumption": x_resumption,
                    })
                    in_reaction = False

    return pd.DataFrame(signals)


def sensitivity_comparison(
    prices: pd.Series,
    direction: Literal["long", "short"] = "short",
    n_values: list[int] = [5, 8, 12],
    x_values: list[int] = [3, 5, 7],
) -> pd.DataFrame:
    """
    Compare signal counts and avg risk across different N/X
    parameter combinations.

    Demonstrates the sensitivity tradeoff:
    - Smaller N + smaller X = more signals, more false entries
    - Larger N + larger X = fewer signals, better quality
    """
    results = []
    for n in n_values:
        for x in x_values:
            sigs = reversal_of_minor_reaction(prices, n, x, direction)
            results.append({
                "N_reaction": n,
                "X_resumption": x,
                "total_sensitivity": n + x,
                "num_signals": len(sigs),
                "avg_risk": round(sigs["risk"].mean(), 2) if len(sigs) > 0 else None,
                "avg_entry": round(sigs["entry_price"].mean(), 2) if len(sigs) > 0 else None,
            })
    return pd.DataFrame(results)


# --- Demo ---
if __name__ == "__main__":
    np.random.seed(42)
    # Simulate a downtrending market with rallies
    t = np.arange(200)
    trend = 180 - 0.2 * t
    cycles = 8 * np.sin(t / 12) + 4 * np.sin(t / 5)
    noise = np.random.normal(0, 1.5, 200)
    prices = pd.Series(
        trend + cycles + noise,
        index=pd.date_range("2024-01-01", periods=200, freq="B"),
        name="close",
    )

    print("=== Reversal of Minor Reaction (Short, N=8, X=3) ===")
    signals = reversal_of_minor_reaction(prices, n_reaction=8, x_resumption=3)
    print(signals.to_string(index=False))

    print("\n=== Sensitivity Comparison ===")
    comp = sensitivity_comparison(prices, "short")
    print(comp.to_string(index=False))
