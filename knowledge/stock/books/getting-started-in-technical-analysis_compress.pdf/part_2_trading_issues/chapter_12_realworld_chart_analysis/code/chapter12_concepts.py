"""
chapter12_concepts.py
=====================
Reference implementations for the concepts in Chapter 12 of
"Getting Started in Technical Analysis" by Jack D. Schwager.

Each function corresponds to one concept and is written for clarity over
performance. Inputs are pandas Series/DataFrame with OHLC columns named
'open', 'high', 'low', 'close'.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd


# ------------------------------------------------------------------
# 1. PRIMARY PREMISE VIOLATION
# ------------------------------------------------------------------
def premise_violated(
    df: pd.DataFrame,
    invalidation_level: float,
    direction: str = "long",
) -> pd.Series:
    """
    Return a boolean series flagging bars where the trade premise is
    violated. For a long, premise is violated when close < invalidation_level.
    For a short, premise is violated when close > invalidation_level.
    """
    if direction == "long":
        return df["close"] < invalidation_level
    elif direction == "short":
        return df["close"] > invalidation_level
    raise ValueError("direction must be 'long' or 'short'")


# ------------------------------------------------------------------
# 2. MARKET ORDER vs LIMIT ORDER
# ------------------------------------------------------------------
@dataclass
class FillResult:
    filled: bool
    fill_price: Optional[float]
    fill_index: Optional[int]


def simulate_limit_buy(df: pd.DataFrame, limit_price: float) -> FillResult:
    """A limit buy is filled when the bar's low <= limit price."""
    hit = df.index[df["low"] <= limit_price]
    if len(hit) == 0:
        return FillResult(False, None, None)
    idx = hit[0]
    return FillResult(True, limit_price, idx)


def simulate_market_buy(df: pd.DataFrame, signal_index: int) -> FillResult:
    """A market buy is filled at the next bar's open."""
    if signal_index + 1 >= len(df):
        return FillResult(False, None, None)
    px = float(df.iloc[signal_index + 1]["open"])
    return FillResult(True, px, signal_index + 1)


# ------------------------------------------------------------------
# 3. STOP-PLACEMENT QUALITY
# ------------------------------------------------------------------
def closest_meaningful_level(
    df: pd.DataFrame, lookback: int = 20, side: str = "below"
) -> float:
    """
    A 'meaningful' stop sits beyond a real structural level — e.g. the
    mid-point of the most recent consolidation, or the prior swing low.
    Here we approximate it with the lookback low/high.
    """
    window = df.tail(lookback)
    return float(window["low"].min() if side == "below" else window["high"].max())


def stop_was_too_tight(
    entry_price: float, stop_price: float, atr: float, k: float = 1.0
) -> bool:
    """
    A stop is 'too tight' if the distance from entry to stop is less than
    k * ATR — flag-and-pennant noise tends to exceed 1 ATR in spikes.
    """
    return abs(entry_price - stop_price) < k * atr


# ------------------------------------------------------------------
# 4. MEASURED MOVE OBJECTIVE
# ------------------------------------------------------------------
def measured_move_target(swing_low: float, swing_high: float, pullback_low: float,
                         direction: str = "up") -> float:
    """
    Project the size of the prior move onto the pullback low (uptrend) or
    pullback high (downtrend).
        target_up   = pullback_low  + (swing_high - swing_low)
        target_down = pullback_high - (swing_high - swing_low)
    """
    move_size = swing_high - swing_low
    if direction == "up":
        return pullback_low + move_size
    elif direction == "down":
        return pullback_low - move_size  # caller passes pullback_high as 3rd arg
    raise ValueError("direction must be 'up' or 'down'")


# ------------------------------------------------------------------
# 5. BULL TRAP
# ------------------------------------------------------------------
def detect_bull_trap(
    df: pd.DataFrame, range_high: float, range_low: float, lookforward: int = 10
) -> pd.Series:
    """
    Mark bars that look like a bull-trap top:
      (a) close > range_high (breakout)
      (b) within `lookforward` bars, close <= range_low or below median
    """
    flags = pd.Series(False, index=df.index)
    median = (range_high + range_low) / 2
    for i in range(len(df) - lookforward):
        if df.iloc[i]["close"] > range_high:
            window = df.iloc[i + 1 : i + 1 + lookforward]
            if (window["close"] <= median).any():
                flags.iloc[i] = True
    return flags


# ------------------------------------------------------------------
# 6. BEAR TRAP
# ------------------------------------------------------------------
def detect_bear_trap(
    df: pd.DataFrame, range_high: float, range_low: float, lookforward: int = 10
) -> pd.Series:
    """Mirror of `detect_bull_trap`."""
    flags = pd.Series(False, index=df.index)
    median = (range_high + range_low) / 2
    for i in range(len(df) - lookforward):
        if df.iloc[i]["close"] < range_low:
            window = df.iloc[i + 1 : i + 1 + lookforward]
            if (window["close"] >= median).any():
                flags.iloc[i] = True
    return flags


# ------------------------------------------------------------------
# 7. FLAG / PENNANT CONTINUATION
# ------------------------------------------------------------------
def detect_flag(
    df: pd.DataFrame,
    pole_bars: int = 8,
    flag_bars: int = 8,
    pole_min_pct: float = 0.04,
    flag_max_pct: float = 0.02,
) -> Optional[dict]:
    """
    Very simple flag detector. Looks at the last `pole_bars + flag_bars` bars:
      - 'pole' = first `pole_bars`, must move >= pole_min_pct
      - 'flag' = last  `flag_bars`,  must stay within flag_max_pct of its midpoint
    Returns a dict with the flag boundaries, or None.
    """
    n = pole_bars + flag_bars
    if len(df) < n:
        return None
    sub = df.tail(n)
    pole = sub.iloc[:pole_bars]
    flag = sub.iloc[pole_bars:]

    pole_pct = (pole.iloc[-1]["close"] - pole.iloc[0]["close"]) / pole.iloc[0]["close"]
    if abs(pole_pct) < pole_min_pct:
        return None

    flag_mid = flag["close"].mean()
    flag_dev = (flag["close"].max() - flag["close"].min()) / flag_mid
    if flag_dev > flag_max_pct:
        return None

    return {
        "direction": "up" if pole_pct > 0 else "down",
        "flag_high": float(flag["high"].max()),
        "flag_low":  float(flag["low"].min()),
        "pole_size": abs(float(pole.iloc[-1]["close"] - pole.iloc[0]["close"])),
    }


# ------------------------------------------------------------------
# 8. COUNTER-TO-ANTICIPATED BREAKOUT
# ------------------------------------------------------------------
def counter_to_anticipated_breakout(flag: dict, latest_close: float) -> Optional[str]:
    """
    Given a detected flag dict and the latest close, decide whether a
    counter-to-anticipated breakout has occurred.
    """
    if flag is None:
        return None
    if flag["direction"] == "up" and latest_close < flag["flag_low"]:
        return "counter_breakout_down"
    if flag["direction"] == "down" and latest_close > flag["flag_high"]:
        return "counter_breakout_up"
    return None


# ------------------------------------------------------------------
# 9. WIDE-RANGING DAY
# ------------------------------------------------------------------
def true_range(df: pd.DataFrame) -> pd.Series:
    """Standard true range."""
    prev_close = df["close"].shift(1)
    tr = pd.concat([
        df["high"] - df["low"],
        (df["high"] - prev_close).abs(),
        (df["low"]  - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr


def wide_ranging_day(df: pd.DataFrame, lookback: int = 14, k: float = 2.0) -> pd.Series:
    """A bar whose true range >= k * average true range of the prior `lookback` bars."""
    tr = true_range(df)
    atr = tr.rolling(lookback).mean().shift(1)
    return tr >= k * atr


# ------------------------------------------------------------------
# 10. TRAILING STOP
# ------------------------------------------------------------------
def trailing_stop(close: pd.Series, distance: float, side: str = "long") -> pd.Series:
    """
    Long: stop = max(close so far) - distance, never decreases.
    Short: stop = min(close so far) + distance, never increases.
    """
    if side == "long":
        running = close.cummax()
        return running - distance
    elif side == "short":
        running = close.cummin()
        return running + distance
    raise ValueError("side must be 'long' or 'short'")


# ------------------------------------------------------------------
# 11. ISLAND REVERSAL + SPIKE HIGH
# ------------------------------------------------------------------
def detect_island_reversal(df: pd.DataFrame) -> pd.Series:
    """
    A 3-bar island reversal at the top: gap up on bar i, gap down on bar i+2,
    so the middle bar (or cluster) is isolated by gaps on both sides.
    """
    flags = pd.Series(False, index=df.index)
    for i in range(1, len(df) - 1):
        prev_high = df.iloc[i - 1]["high"]
        next_low  = df.iloc[i + 1]["low"]
        cur_low   = df.iloc[i]["low"]
        cur_high  = df.iloc[i]["high"]
        if cur_low > prev_high and cur_high > next_low and next_low < prev_high:
            flags.iloc[i] = True
    return flags


def spike_high(df: pd.DataFrame, lookback: int = 20, k: float = 1.5) -> pd.Series:
    """A bar whose high is at least `k` ATRs above the previous bar's close."""
    tr = true_range(df)
    atr = tr.rolling(lookback).mean().shift(1)
    return (df["high"] - df["close"].shift(1)) >= k * atr


# ------------------------------------------------------------------
# 12. EXPECTED GAIN PER TRADE
# ------------------------------------------------------------------
def expected_gain_per_trade(win_rate: float, avg_win: float, avg_loss: float) -> float:
    """
    E = (win_rate * avg_win) - ((1 - win_rate) * avg_loss)
    Expressed in the same units as avg_win and avg_loss (R, $, %, etc.).
    """
    if not 0 <= win_rate <= 1:
        raise ValueError("win_rate must be in [0, 1]")
    if avg_loss < 0 or avg_win < 0:
        raise ValueError("avg_win and avg_loss must be non-negative magnitudes")
    return win_rate * avg_win - (1 - win_rate) * avg_loss


# ------------------------------------------------------------------
# Quick demo
# ------------------------------------------------------------------
if __name__ == "__main__":
    np.random.seed(42)
    n = 80
    close = 100 + np.cumsum(np.random.normal(0.05, 1.0, n))
    df = pd.DataFrame({
        "open":  close + np.random.normal(0, 0.3, n),
        "high":  close + np.abs(np.random.normal(0.5, 0.4, n)),
        "low":   close - np.abs(np.random.normal(0.5, 0.4, n)),
        "close": close,
    })

    print("Wide-ranging days:", int(wide_ranging_day(df).sum()))
    print("MM target (100, 110, 105 up):", measured_move_target(100, 110, 105, "up"))
    print("E[gain] (0.40, +3R, -1R):",
          round(expected_gain_per_trade(0.40, 3.0, 1.0), 3), "R per trade")
    print("E[gain] (0.65, +1R, -1R):",
          round(expected_gain_per_trade(0.65, 1.0, 1.0), 3), "R per trade")
    print("Trailing stop (last 5):",
          trailing_stop(df["close"], 2.0, "long").tail().round(2).tolist())
