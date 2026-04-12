"""
Continuation Pattern & Trading Range Breakouts — Chapter 8, Concept 4
Schwager: "Getting Started in Technical Analysis"

Identify consolidation pauses within trends (flags, ranges,
narrow-band congestion) and generate entry signals on breakout
or within the pattern itself.
"""

import pandas as pd
import numpy as np
from typing import Literal


def detect_consolidation_zones(
    prices: pd.Series,
    min_days: int = 5,
    max_range_pct: float = 6.0,
) -> list[dict]:
    """
    Detect consolidation zones: periods of at least `min_days`
    where the price range (high-low) stays within `max_range_pct`
    of the zone's midpoint.

    Returns list of dicts:
        start_idx, end_idx, start_date, end_date,
        zone_high, zone_low, zone_mid, duration_days
    """
    zones = []
    i = 0
    n = len(prices)

    while i < n - min_days:
        window_start = i
        zone_high = prices.iloc[i]
        zone_low = prices.iloc[i]

        j = i + 1
        while j < n:
            zone_high = max(zone_high, prices.iloc[j])
            zone_low = min(zone_low, prices.iloc[j])
            zone_mid = (zone_high + zone_low) / 2
            range_pct = (zone_high - zone_low) / zone_mid * 100

            if range_pct > max_range_pct:
                break
            j += 1

        duration = j - window_start
        if duration >= min_days:
            zones.append({
                "start_idx": window_start,
                "end_idx": j - 1,
                "start_date": prices.index[window_start],
                "end_date": prices.index[j - 1],
                "zone_high": round(zone_high, 2),
                "zone_low": round(zone_low, 2),
                "zone_mid": round((zone_high + zone_low) / 2, 2),
                "duration_days": duration,
            })
            i = j  # skip past this zone
        else:
            i += 1

    return zones


def classify_trend_before_zone(
    prices: pd.Series,
    zone_start_idx: int,
    lookback: int = 20,
) -> str:
    """
    Determine the trend direction leading into a consolidation zone.

    Returns 'up', 'down', or 'neutral'.
    """
    start = max(0, zone_start_idx - lookback)
    pre_zone = prices.iloc[start:zone_start_idx]
    if len(pre_zone) < 5:
        return "neutral"

    slope = np.polyfit(range(len(pre_zone)), pre_zone.values, 1)[0]
    pct_change = (pre_zone.iloc[-1] - pre_zone.iloc[0]) / pre_zone.iloc[0] * 100

    if slope > 0 and pct_change > 3:
        return "up"
    elif slope < 0 and pct_change < -3:
        return "down"
    return "neutral"


def continuation_breakout_signals(
    prices: pd.Series,
    min_days: int = 5,
    max_range_pct: float = 6.0,
    entry_mode: Literal["breakout", "anticipate"] = "breakout",
    lookback: int = 20,
) -> pd.DataFrame:
    """
    Generate midtrend entry signals from continuation patterns.

    Parameters:
        prices: Series of closing prices
        min_days: Minimum duration for a consolidation zone
        max_range_pct: Maximum price range (%) to qualify as consolidation
        entry_mode:
            'breakout' — enter when price closes above zone_high
                (uptrend) or below zone_low (downtrend)
            'anticipate' — enter near zone_low (uptrend) or
                zone_high (downtrend) within the pattern
        lookback: Days before zone to assess trend direction

    Returns:
        DataFrame with: date, signal, entry_price, stop_price,
        risk, zone_high, zone_low, duration_days, trend, entry_mode
    """
    zones = detect_consolidation_zones(prices, min_days, max_range_pct)
    signals = []

    for zone in zones:
        trend = classify_trend_before_zone(prices, zone["start_idx"], lookback)
        if trend == "neutral":
            continue

        if entry_mode == "breakout":
            # Look for breakout after the zone
            post_zone = prices.iloc[zone["end_idx"] + 1:]
            if trend == "up":
                breakout = post_zone[post_zone > zone["zone_high"]]
                if len(breakout) > 0:
                    signals.append({
                        "date": breakout.index[0],
                        "signal": "BUY",
                        "entry_price": round(breakout.iloc[0], 2),
                        "stop_price": zone["zone_low"],
                        "risk": round(breakout.iloc[0] - zone["zone_low"], 2),
                        "zone_high": zone["zone_high"],
                        "zone_low": zone["zone_low"],
                        "duration_days": zone["duration_days"],
                        "trend": trend,
                        "entry_mode": "breakout",
                    })
            else:  # down
                breakout = post_zone[post_zone < zone["zone_low"]]
                if len(breakout) > 0:
                    signals.append({
                        "date": breakout.index[0],
                        "signal": "SELL",
                        "entry_price": round(breakout.iloc[0], 2),
                        "stop_price": zone["zone_high"],
                        "risk": round(zone["zone_high"] - breakout.iloc[0], 2),
                        "zone_high": zone["zone_high"],
                        "zone_low": zone["zone_low"],
                        "duration_days": zone["duration_days"],
                        "trend": trend,
                        "entry_mode": "breakout",
                    })

        else:  # anticipate
            # Enter within the pattern near the favorable extreme
            zone_prices = prices.iloc[zone["start_idx"]:zone["end_idx"] + 1]
            if trend == "up":
                # Enter near zone low (best price in uptrend)
                entry_idx = zone_prices.idxmin()
                entry_price = zone_prices[entry_idx]
                signals.append({
                    "date": entry_idx,
                    "signal": "BUY",
                    "entry_price": round(entry_price, 2),
                    "stop_price": round(zone["zone_low"] * 0.99, 2),
                    "risk": round(entry_price - zone["zone_low"] * 0.99, 2),
                    "zone_high": zone["zone_high"],
                    "zone_low": zone["zone_low"],
                    "duration_days": zone["duration_days"],
                    "trend": trend,
                    "entry_mode": "anticipate",
                })
            else:
                entry_idx = zone_prices.idxmax()
                entry_price = zone_prices[entry_idx]
                signals.append({
                    "date": entry_idx,
                    "signal": "SELL",
                    "entry_price": round(entry_price, 2),
                    "stop_price": round(zone["zone_high"] * 1.01, 2),
                    "risk": round(zone["zone_high"] * 1.01 - entry_price, 2),
                    "zone_high": zone["zone_high"],
                    "zone_low": zone["zone_low"],
                    "duration_days": zone["duration_days"],
                    "trend": trend,
                    "entry_mode": "anticipate",
                })

    return pd.DataFrame(signals)


def compare_entry_modes(
    prices: pd.Series,
    min_days: int = 5,
    max_range_pct: float = 6.0,
) -> pd.DataFrame:
    """
    Compare breakout vs anticipate entry modes side by side.
    """
    breakout = continuation_breakout_signals(
        prices, min_days, max_range_pct, "breakout"
    )
    anticipate = continuation_breakout_signals(
        prices, min_days, max_range_pct, "anticipate"
    )

    results = []
    for label, df in [("breakout", breakout), ("anticipate", anticipate)]:
        results.append({
            "entry_mode": label,
            "num_signals": len(df),
            "avg_risk": round(df["risk"].mean(), 2) if len(df) > 0 else None,
            "avg_entry": round(df["entry_price"].mean(), 2) if len(df) > 0 else None,
            "avg_zone_duration": (
                round(df["duration_days"].mean(), 1) if len(df) > 0 else None
            ),
        })
    return pd.DataFrame(results)


# --- Demo ---
if __name__ == "__main__":
    np.random.seed(42)
    # Simulate trending market with consolidation pauses
    t = np.arange(300)
    trend = 100 + 0.12 * t
    # Add flat consolidation zones
    pause = np.zeros(300)
    pause[60:75] = -0.12 * np.arange(15) + 2
    pause[140:158] = -0.12 * np.arange(18) + 3
    pause[220:238] = -0.12 * np.arange(18) + 4
    cycles = 3 * np.sin(t / 8)
    noise = np.random.normal(0, 1.2, 300)
    prices = pd.Series(
        trend + pause + cycles + noise,
        index=pd.date_range("2024-01-01", periods=300, freq="B"),
        name="close",
    )

    print("=== Consolidation Zones ===")
    zones = detect_consolidation_zones(prices)
    for z in zones[:5]:
        print(f"  {z['start_date'].date()} to {z['end_date'].date()}: "
              f"${z['zone_low']}-${z['zone_high']} ({z['duration_days']}d)")

    print("\n=== Breakout Signals ===")
    sigs = continuation_breakout_signals(prices, entry_mode="breakout")
    print(sigs.to_string(index=False) if len(sigs) > 0 else "  No signals")

    print("\n=== Anticipate Signals ===")
    sigs2 = continuation_breakout_signals(prices, entry_mode="anticipate")
    print(sigs2.to_string(index=False) if len(sigs2) > 0 else "  No signals")

    print("\n=== Mode Comparison ===")
    comp = compare_entry_modes(prices)
    print(comp.to_string(index=False))
