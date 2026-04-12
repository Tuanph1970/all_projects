"""
Reaction to Long-Term Moving Average — Chapter 8, Concept 5
Schwager: "Getting Started in Technical Analysis"

Enter midtrend when price pulls back to a long-term moving average.
The MA acts as a dynamic support (uptrend) or resistance (downtrend).

Key insight: Price vs. MA crossover is deliberately MORE sensitive
than MA vs. MA crossover (Ch. 14) because we're re-entering an
established trend, not identifying a new one.
"""

import pandas as pd
import numpy as np
from typing import Literal


def simple_moving_average(prices: pd.Series, period: int) -> pd.Series:
    """Compute simple moving average."""
    return prices.rolling(period).mean()


def ma_reaction_signals(
    prices: pd.Series,
    ma_period: int = 40,
    direction: Literal["long", "short"] = "long",
    entry_trigger: Literal["touch", "cross"] = "cross",
) -> pd.DataFrame:
    """
    Generate midtrend entry signals when price reacts to a moving average.

    Parameters:
        prices: Series of closing prices
        ma_period: Moving average lookback period
        direction:
            'long' — buy when price pulls back to/below MA in uptrend
            'short' — sell when price rallies to/above MA in downtrend
        entry_trigger:
            'cross' — signal on the bar where price crosses the MA
            'touch' — signal when price comes within 0.5% of MA

    Returns:
        DataFrame with: date, signal, entry_price, ma_value,
        distance_pct, ma_period
    """
    ma = simple_moving_average(prices, ma_period)
    signals = []

    for i in range(ma_period + 1, len(prices)):
        price = prices.iloc[i]
        prev_price = prices.iloc[i - 1]
        ma_val = ma.iloc[i]
        prev_ma = ma.iloc[i - 1]

        if pd.isna(ma_val) or pd.isna(prev_ma):
            continue

        distance_pct = (price - ma_val) / ma_val * 100

        if direction == "long":
            if entry_trigger == "cross":
                # Price crosses below MA (was above, now at/below)
                if prev_price > prev_ma and price <= ma_val:
                    signals.append(_make_signal(
                        prices, i, "BUY", price, ma_val, distance_pct, ma_period
                    ))
            else:  # touch
                # Price comes within 0.5% of MA from above
                if price > ma_val and distance_pct < 0.5 and prev_price > prev_ma:
                    signals.append(_make_signal(
                        prices, i, "BUY", price, ma_val, distance_pct, ma_period
                    ))

        else:  # short
            if entry_trigger == "cross":
                # Price crosses above MA (was below, now at/above)
                if prev_price < prev_ma and price >= ma_val:
                    signals.append(_make_signal(
                        prices, i, "SELL", price, ma_val, distance_pct, ma_period
                    ))
            else:
                if price < ma_val and abs(distance_pct) < 0.5 and prev_price < prev_ma:
                    signals.append(_make_signal(
                        prices, i, "SELL", price, ma_val, distance_pct, ma_period
                    ))

    return pd.DataFrame(signals)


def _make_signal(prices, i, signal, price, ma_val, dist_pct, ma_period):
    return {
        "date": prices.index[i],
        "signal": signal,
        "entry_price": round(price, 2),
        "ma_value": round(ma_val, 2),
        "distance_pct": round(dist_pct, 2),
        "ma_period": ma_period,
    }


def compare_ma_periods(
    prices: pd.Series,
    periods: list[int] = [20, 40, 60],
    direction: Literal["long", "short"] = "long",
) -> pd.DataFrame:
    """
    Compare signal characteristics across different MA periods.

    Demonstrates the sensitivity tradeoff:
    - Shorter MA = more signals, catches smaller pullbacks
    - Longer MA = fewer signals, only catches deep pullbacks
    """
    results = []
    for period in periods:
        sigs = ma_reaction_signals(prices, period, direction)
        results.append({
            "ma_period": period,
            "num_signals": len(sigs),
            "avg_entry": (
                round(sigs["entry_price"].mean(), 2) if len(sigs) > 0 else None
            ),
            "avg_distance_pct": (
                round(sigs["distance_pct"].mean(), 2) if len(sigs) > 0 else None
            ),
            "sensitivity": (
                "High" if period <= 20
                else "Medium" if period <= 50
                else "Low"
            ),
        })
    return pd.DataFrame(results)


def sensitivity_comparison_table(
    prices: pd.Series,
    direction: Literal["long", "short"] = "long",
) -> pd.DataFrame:
    """
    Schwager's key insight: compare countertrend entry (price vs MA)
    sensitivity against trend-identification (MA vs MA) sensitivity.

    Shows why price-vs-MA crossovers are deliberately more sensitive.
    """
    results = []

    # Countertrend entry: price vs single MA
    for period in [20, 40, 60]:
        sigs = ma_reaction_signals(prices, period, direction)
        results.append({
            "method": f"Price vs {period}-MA (countertrend entry)",
            "signals": len(sigs),
            "purpose": "Re-enter established trend",
            "sensitivity": "High" if period <= 20 else "Medium",
        })

    # Trend identification: MA vs MA crossovers
    for fast, slow in [(10, 40), (20, 50), (20, 60)]:
        ma_fast = simple_moving_average(prices, fast)
        ma_slow = simple_moving_average(prices, slow)
        crossovers = 0
        for i in range(slow + 1, len(prices)):
            if pd.isna(ma_fast.iloc[i]) or pd.isna(ma_slow.iloc[i]):
                continue
            prev_above = ma_fast.iloc[i - 1] > ma_slow.iloc[i - 1]
            curr_above = ma_fast.iloc[i] > ma_slow.iloc[i]
            if prev_above != curr_above:
                crossovers += 1
        results.append({
            "method": f"{fast}-MA vs {slow}-MA (trend identification)",
            "signals": crossovers,
            "purpose": "Identify new trend",
            "sensitivity": "Low",
        })

    return pd.DataFrame(results)


# --- Demo ---
if __name__ == "__main__":
    np.random.seed(42)
    # Simulate uptrending market with pullbacks
    t = np.arange(250)
    trend = 100 + 0.15 * t
    cycles = 8 * np.sin(t / 18) + 4 * np.sin(t / 9)
    noise = np.random.normal(0, 2, 250)
    prices = pd.Series(
        trend + cycles + noise,
        index=pd.date_range("2024-01-01", periods=250, freq="B"),
        name="close",
    )

    print("=== MA Reaction Signals (40-day, Long) ===")
    signals = ma_reaction_signals(prices, 40, "long")
    print(signals.to_string(index=False))

    print("\n=== Period Comparison ===")
    comp = compare_ma_periods(prices, [20, 40, 60])
    print(comp.to_string(index=False))

    print("\n=== Sensitivity Comparison (Schwager's Key Insight) ===")
    sens = sensitivity_comparison_table(prices, "long")
    print(sens.to_string(index=False))
