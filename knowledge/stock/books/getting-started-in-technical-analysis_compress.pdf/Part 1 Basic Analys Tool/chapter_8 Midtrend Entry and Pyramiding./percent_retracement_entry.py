"""
Percent Retracement Entry — Chapter 8, Concept 2
Schwager: "Getting Started in Technical Analysis"

Enter a midtrend position when price retraces a specified
percentage of the prior swing. Stop placed at the swing extreme.
"""

import pandas as pd
import numpy as np
from typing import Literal


def find_swings(
    prices: pd.Series, lookback: int = 20
) -> list[dict]:
    """
    Identify alternating swing highs and swing lows.

    Returns list of dicts with 'type' ('high'/'low'), 'price', 'index'.
    """
    swing_highs = prices[
        prices == prices.rolling(lookback, center=True).max()
    ].dropna()
    swing_lows = prices[
        prices == prices.rolling(lookback, center=True).min()
    ].dropna()

    swings = pd.concat([
        swing_highs.rename("price").to_frame().assign(type="high"),
        swing_lows.rename("price").to_frame().assign(type="low"),
    ]).sort_index()

    # Remove consecutive same-type swings, keep most extreme
    filtered = []
    for idx, row in swings.iterrows():
        entry = {"type": row["type"], "price": row["price"], "index": idx}
        if not filtered or filtered[-1]["type"] != row["type"]:
            filtered.append(entry)
        else:
            if row["type"] == "high":
                if row["price"] > filtered[-1]["price"]:
                    filtered[-1] = entry
            else:
                if row["price"] < filtered[-1]["price"]:
                    filtered[-1] = entry

    return filtered


def retracement_entry_signals(
    prices: pd.Series,
    retracement_pct: float = 50.0,
    direction: Literal["long", "short"] = "long",
    lookback: int = 20,
) -> pd.DataFrame:
    """
    Generate entry signals when price retraces a given percentage
    of the prior swing.

    For 'long':
        - Identifies a swing low → swing high move
        - Entry triggered when price pulls back retracement_pct%
          of that move from the swing high
        - Stop placed at the swing low

    For 'short':
        - Identifies a swing high → swing low move
        - Entry triggered on rally of retracement_pct%
          from the swing low
        - Stop placed at the swing high

    Returns DataFrame with columns:
        date, signal, entry_price, stop_price, risk,
        swing_low, swing_high, retracement_pct
    """
    swings = find_swings(prices, lookback)
    signals = []

    for i in range(2, len(swings)):
        prev = swings[i - 1]
        curr_swing = swings[i]

        if direction == "long" and prev["type"] == "high":
            swing_low = swings[i - 2]["price"]
            swing_high = prev["price"]
            move = swing_high - swing_low
            entry_level = swing_high - move * (retracement_pct / 100)

            # Check if price actually reached the entry level
            # after the swing high
            post_high = prices.loc[prev["index"]:]
            triggered = post_high[post_high <= entry_level]

            if len(triggered) > 0:
                trigger_date = triggered.index[0]
                signals.append({
                    "date": trigger_date,
                    "signal": "BUY",
                    "entry_price": round(entry_level, 2),
                    "stop_price": round(swing_low, 2),
                    "risk": round(entry_level - swing_low, 2),
                    "swing_low": round(swing_low, 2),
                    "swing_high": round(swing_high, 2),
                    "retracement_pct": retracement_pct,
                })

        elif direction == "short" and prev["type"] == "low":
            swing_high = swings[i - 2]["price"]
            swing_low_price = prev["price"]
            move = swing_high - swing_low_price
            entry_level = swing_low_price + move * (retracement_pct / 100)

            post_low = prices.loc[prev["index"]:]
            triggered = post_low[post_low >= entry_level]

            if len(triggered) > 0:
                trigger_date = triggered.index[0]
                signals.append({
                    "date": trigger_date,
                    "signal": "SELL",
                    "entry_price": round(entry_level, 2),
                    "stop_price": round(swing_high, 2),
                    "risk": round(swing_high - entry_level, 2),
                    "swing_low": round(swing_low_price, 2),
                    "swing_high": round(swing_high, 2),
                    "retracement_pct": retracement_pct,
                })

    return pd.DataFrame(signals)


def compare_retracement_levels(
    prices: pd.Series,
    levels: list[float] = [35, 50, 65],
    direction: Literal["long", "short"] = "long",
    lookback: int = 20,
) -> pd.DataFrame:
    """
    Compare signal counts and average risk across multiple
    retracement thresholds — demonstrates the core tradeoff:
    deeper retracement = better price but fewer fills.
    """
    results = []
    for pct in levels:
        sigs = retracement_entry_signals(prices, pct, direction, lookback)
        results.append({
            "retracement_pct": pct,
            "num_signals": len(sigs),
            "avg_risk": round(sigs["risk"].mean(), 2) if len(sigs) > 0 else None,
            "avg_entry": round(sigs["entry_price"].mean(), 2) if len(sigs) > 0 else None,
        })
    return pd.DataFrame(results)


# --- Demo ---
if __name__ == "__main__":
    np.random.seed(42)
    # Simulate a trending market with pullbacks
    t = np.arange(300)
    trend = 100 + 0.15 * t
    cycles = 12 * np.sin(t / 15) + 6 * np.sin(t / 7)
    noise = np.random.normal(0, 2, 300)
    prices = pd.Series(
        trend + cycles + noise,
        index=pd.date_range("2024-01-01", periods=300, freq="B"),
        name="close",
    )

    print("=== 50% Retracement Signals (Long) ===")
    signals = retracement_entry_signals(prices, 50, "long")
    print(signals.to_string(index=False))

    print("\n=== Comparing Retracement Levels ===")
    comparison = compare_retracement_levels(prices, [35, 50, 65])
    print(comparison.to_string(index=False))
