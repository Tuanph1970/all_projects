"""
Midtrend Entry Problem — Chapter 8, Concept 1
Schwager: "Getting Started in Technical Analysis"

Detects when price has moved substantially from a swing low/high,
quantifies what fraction of historical trend moves this represents,
and flags whether "too late" hesitation is likely unjustified.
"""

import pandas as pd
import numpy as np
from typing import Literal


def find_swing_low(prices: pd.Series, lookback: int = 20) -> float:
    """Find the lowest price in the recent lookback window."""
    return prices.rolling(lookback).min().iloc[-1]


def find_swing_high(prices: pd.Series, lookback: int = 20) -> float:
    """Find the highest price in the recent lookback window."""
    return prices.rolling(lookback).max().iloc[-1]


def measure_move_so_far(
    prices: pd.Series,
    direction: Literal["long", "short"] = "long",
    lookback: int = 20,
) -> dict:
    """
    Measure how much price has already moved from the recent swing point.

    Returns:
        dict with:
        - swing_price: the swing low (long) or high (short)
        - current_price: latest price
        - pct_move: percent move from swing to current
        - direction: long or short
    """
    current = prices.iloc[-1]

    if direction == "long":
        swing = find_swing_low(prices, lookback)
        pct_move = (current - swing) / swing * 100
    else:
        swing = find_swing_high(prices, lookback)
        pct_move = (swing - current) / swing * 100

    return {
        "swing_price": round(swing, 2),
        "current_price": round(current, 2),
        "pct_move": round(pct_move, 2),
        "direction": direction,
    }


def historical_trend_magnitudes(
    prices: pd.Series,
    min_move_pct: float = 10.0,
    lookback: int = 20,
) -> list[float]:
    """
    Scan historical data for completed trend moves (peak-to-trough
    or trough-to-peak) and return their magnitudes as percentages.

    This gives context: if past trends averaged 60%, a 35% move
    so far is likely only ~halfway done.
    """
    swing_highs = prices[
        (prices == prices.rolling(lookback, center=True).max())
    ].dropna()
    swing_lows = prices[
        (prices == prices.rolling(lookback, center=True).min())
    ].dropna()

    # Merge and sort all swing points
    swings = pd.concat([
        swing_highs.rename("price").to_frame().assign(type="high"),
        swing_lows.rename("price").to_frame().assign(type="low"),
    ]).sort_index()

    # Remove consecutive same-type swings (keep most extreme)
    filtered = []
    for _, row in swings.iterrows():
        if not filtered or filtered[-1]["type"] != row["type"]:
            filtered.append({"price": row["price"], "type": row["type"]})
        else:
            if row["type"] == "high":
                filtered[-1]["price"] = max(filtered[-1]["price"], row["price"])
            else:
                filtered[-1]["price"] = min(filtered[-1]["price"], row["price"])

    # Calculate move magnitudes between alternating swings
    magnitudes = []
    for i in range(1, len(filtered)):
        prev, curr = filtered[i - 1]["price"], filtered[i]["price"]
        pct = abs(curr - prev) / prev * 100
        if pct >= min_move_pct:
            magnitudes.append(round(pct, 2))

    return magnitudes


def assess_midtrend_position(
    prices: pd.Series,
    direction: Literal["long", "short"] = "long",
    lookback: int = 20,
    min_move_pct: float = 10.0,
) -> dict:
    """
    Full assessment: how far has price moved vs. historical norms?

    Returns context to help overcome "too late" hesitation.
    """
    move = measure_move_so_far(prices, direction, lookback)
    hist = historical_trend_magnitudes(prices, min_move_pct, lookback)

    if hist:
        avg_trend = round(np.mean(hist), 2)
        median_trend = round(np.median(hist), 2)
        max_trend = round(max(hist), 2)
        fraction_complete = round(move["pct_move"] / avg_trend, 2)
    else:
        avg_trend = median_trend = max_trend = None
        fraction_complete = None

    return {
        **move,
        "historical_avg_trend_pct": avg_trend,
        "historical_median_trend_pct": median_trend,
        "historical_max_trend_pct": max_trend,
        "estimated_fraction_complete": fraction_complete,
        "num_historical_trends": len(hist),
        "assessment": _generate_assessment(move["pct_move"], fraction_complete),
    }


def _generate_assessment(pct_move: float, fraction: float | None) -> str:
    """Human-readable assessment of midtrend hesitation risk."""
    if fraction is None:
        return "Insufficient historical data to assess."
    if fraction < 0.3:
        return (
            f"Move is ~{fraction:.0%} of average trend. "
            "Early stage — strong case for entry with defined risk."
        )
    if fraction < 0.6:
        return (
            f"Move is ~{fraction:.0%} of average trend. "
            "Mid-stage — entry viable but tighten stops. "
            "Recall: coffee 1994 was at 1/5 when it felt 'too late'."
        )
    if fraction < 1.0:
        return (
            f"Move is ~{fraction:.0%} of average trend. "
            "Late stage — still possible (trends overshoot averages) "
            "but position size should be smaller."
        )
    return (
        f"Move is ~{fraction:.0%} of average trend. "
        "Extended beyond historical average. Caution warranted — "
        "but outlier trends (like coffee 1994) do exist."
    )


# --- Demo ---
if __name__ == "__main__":
    np.random.seed(42)
    # Simulate a trending market
    returns = np.random.normal(0.002, 0.015, 200)
    prices = pd.Series(100 * np.cumprod(1 + returns), name="close")

    result = assess_midtrend_position(prices, direction="long")
    for k, v in result.items():
        print(f"  {k}: {v}")
