"""
Overbought / Oversold Indicators for trade exits.

The RSI (Relative Strength Index, Wilder 1978) is the canonical example.
Range: 0 to 100.
    > 70 -> overbought  (signal to LIQUIDATE longs)
    < 30 -> oversold    (signal to LIQUIDATE shorts)

The thresholds are subjective. Tighter (75/25, 80/20) catches turning
points more closely but misses more of them.

CRUCIAL NUANCE (Schwager): this method works well in TRADING-RANGE markets
and FAILS in strong trending markets, where RSI can sit above 70 (or below
30) for long stretches while the trend continues.
"""

from typing import List, Tuple
import numpy as np


def rsi(prices: List[float], period: int = 14) -> np.ndarray:
    """Wilder's RSI. Returns array of same length as `prices`; first
    `period` values are NaN."""
    p = np.asarray(prices, dtype=float)
    diff = np.diff(p)
    up = np.where(diff > 0, diff, 0.0)
    dn = np.where(diff < 0, -diff, 0.0)
    out = np.full(len(p), np.nan)
    if len(p) <= period:
        return out

    avg_up = up[:period].mean()
    avg_dn = dn[:period].mean()
    for i in range(period, len(p)):
        if i > period:
            avg_up = (avg_up * (period - 1) + up[i - 1]) / period
            avg_dn = (avg_dn * (period - 1) + dn[i - 1]) / period
        rs = avg_up / avg_dn if avg_dn != 0 else float("inf")
        out[i] = 100.0 if avg_dn == 0 else 100 - 100 / (1 + rs)
    return out


def rsi_exit_signals(prices: List[float],
                     position: str,
                     period: int = 14,
                     overbought: float = 70.0,
                     oversold: float = 30.0) -> List[Tuple[int, str]]:
    """Generate exit signals for an existing `position` ('long' or 'short').
    A signal fires on the bar that crosses the threshold."""
    r = rsi(prices, period)
    signals = []
    for i in range(period + 1, len(prices)):
        prev, cur = r[i - 1], r[i]
        if np.isnan(prev) or np.isnan(cur):
            continue
        if position == "long" and prev < overbought <= cur:
            signals.append((i, "exit_long: RSI crossed above overbought"))
        elif position == "short" and prev > oversold >= cur:
            signals.append((i, "exit_short: RSI crossed below oversold"))
    return signals


# --- demo ---------------------------------------------------------------
if __name__ == "__main__":
    np.random.seed(1)
    # Trading-range market (RSI exits work well here)
    n = 200
    t = np.arange(n)
    prices = (50 + 5 * np.sin(t * 0.18) + np.random.normal(0, 0.6, n)).tolist()

    r = rsi(prices, 14)
    print(f"Latest RSI(14): {r[-1]:.2f}")
    print(f"Latest price:   {prices[-1]:.2f}")

    signals = rsi_exit_signals(prices, position="long")
    print(f"\n{len(signals)} long-exit signals fired in this series.")
    for idx, msg in signals[:5]:
        print(f"  bar {idx}: price={prices[idx]:.2f}, RSI={r[idx]:.2f} -> {msg}")
    # Sample first signals (values vary with seed):
    #   bar 24: price=54.71, RSI=72.18 -> exit_long: RSI crossed above overbought
