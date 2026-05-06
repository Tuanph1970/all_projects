"""
Chapter 16 — Volatility-Adjusted Position Sizing
=================================================
Step Three of the planned approach calls for sizing DOWN in volatile markets.
This module uses the Average True Range (ATR) to set both the stop distance
and the share count automatically.
"""

import pandas as pd
import numpy as np


def average_true_range(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """
    Compute Wilder's ATR. df must have 'high', 'low', 'close' columns.
    """
    high = df["high"]
    low = df["low"]
    prev_close = df["close"].shift(1)

    tr = pd.concat(
        [(high - low).abs(),
         (high - prev_close).abs(),
         (low - prev_close).abs()],
        axis=1
    ).max(axis=1)

    # Wilder's smoothing — equivalent to EWM with alpha = 1/period
    return tr.ewm(alpha=1.0 / period, adjust=False).mean()


def volatility_sized_position(
    df: pd.DataFrame,
    equity: float,
    risk_pct: float = 0.02,
    atr_multiple_for_stop: float = 2.0,
    atr_period: int = 14,
) -> dict:
    """
    Use ATR to derive both the stop distance and the share count.

    stop_distance = atr_multiple_for_stop * ATR
    shares        = (equity * risk_pct) / stop_distance

    Volatile markets get a wider stop AND fewer shares — risk stays constant.
    """
    atr = average_true_range(df, atr_period).iloc[-1]
    last_close = df["close"].iloc[-1]
    stop_distance = atr_multiple_for_stop * atr
    dollar_budget = equity * risk_pct
    shares = int(dollar_budget // stop_distance)

    return {
        "last_close": round(last_close, 2),
        "atr": round(atr, 4),
        "stop_distance": round(stop_distance, 4),
        "stop_price": round(last_close - stop_distance, 2),  # for a long
        "shares": shares,
        "dollar_risk": round(shares * stop_distance, 2),
        "capital_required": round(shares * last_close, 2),
    }


def equity_adjusted_leverage(starting_equity: float, current_equity: float, base_risk_pct: float) -> float:
    """
    Schwager's rule: as equity changes, scale risk percentage proportionally.
    A trader who started at $100k and has dropped to $80k should reduce risk
    by 20% — keeping the dollar risk per trade in line with shrinking equity.
    """
    scale = current_equity / starting_equity
    return base_risk_pct * scale


# -------- Demo --------
if __name__ == "__main__":
    # Synthetic price data — normally replace with yfinance / your data source
    np.random.seed(42)
    n = 60

    # Build a calm series and a wild series for comparison
    calm_close = 60 + np.cumsum(np.random.normal(0, 0.5, n))
    wild_close = 250 + np.cumsum(np.random.normal(0, 8.0, n))

    def fake_ohlc(close, vol_factor=1.0):
        rng = np.random.default_rng(0)
        noise = rng.normal(0, vol_factor, len(close))
        return pd.DataFrame({
            "high":  close + np.abs(noise),
            "low":   close - np.abs(noise),
            "close": close,
        })

    calm_df = fake_ohlc(calm_close, vol_factor=0.5)
    wild_df = fake_ohlc(wild_close, vol_factor=8.0)

    print("=" * 60)
    print("Calm market (KO-like)")
    print("=" * 60)
    for k, v in volatility_sized_position(calm_df, equity=100_000, risk_pct=0.03).items():
        print(f"  {k:<20} {v}")

    print()
    print("=" * 60)
    print("Wild market (TSLA-like) — same risk budget, different size")
    print("=" * 60)
    for k, v in volatility_sized_position(wild_df, equity=100_000, risk_pct=0.03).items():
        print(f"  {k:<20} {v}")

    print()
    print("=" * 60)
    print("Equity-adjusted leverage")
    print("=" * 60)
    for current in [120_000, 100_000, 80_000, 60_000]:
        new_pct = equity_adjusted_leverage(100_000, current, base_risk_pct=0.02)
        print(f"  Equity ${current:>7,}  →  risk per trade {new_pct*100:.2f}%")
