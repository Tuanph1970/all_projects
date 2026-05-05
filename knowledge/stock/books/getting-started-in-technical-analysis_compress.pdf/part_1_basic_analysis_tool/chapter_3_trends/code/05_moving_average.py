"""
Concept 8: Simple Moving Average (SMA) and Trend Signals.

From Schwager Ch.3, p.45-50:

    "A simple moving average is defined as the average close of the
    past N days, ending in the current day."

Two key insights:
  1. SMA(today) > SMA(yesterday) iff close(today) > close(N days ago).
     (One bar enters, one bar leaves; everything else cancels.)
  2. Smoothing comes at the cost of LAG: turning points in the SMA
     always trail the corresponding turns in price.

Signal rule (Schwager, Figs 3.20-3.21):
  Buy  when SMA reverses UP   by at least M ticks off its low.
  Sell when SMA reverses DOWN by at least M ticks off its high.
  Threshold M prevents whipsaw flipping near zero slope. SMA works
  beautifully in TRENDING markets and disastrously in CHOPPY ones.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Iterator, Tuple
from collections import deque


def sma(prices: List[float], window: int) -> List[float]:
    """Simple moving average. Returns NaN-equivalent (None) for the
    leading bars where the window isn't full yet."""
    out: List[float] = []
    buf: deque[float] = deque(maxlen=window)
    rolling_sum = 0.0
    for p in prices:
        if len(buf) == window:
            rolling_sum -= buf[0]
        buf.append(p)
        rolling_sum += p
        out.append(rolling_sum / window if len(buf) == window else float("nan"))
    return out


def sma_streaming(prices: Iterator[float], window: int) -> Iterator[float]:
    """Memory-efficient streaming SMA — useful for live tick processing."""
    buf: deque[float] = deque(maxlen=window)
    s = 0.0
    for p in prices:
        if len(buf) == window:
            s -= buf[0]
        buf.append(p)
        s += p
        yield s / len(buf)


@dataclass
class MASignal:
    bar: int
    kind: str        # "buy" or "sell"
    ma_value: float


def ma_reversal_signals(ma_series: List[float], threshold: float) -> List[MASignal]:
    """Generate buy/sell signals from MA direction reversals (Schwager's rule).

    Buy:  MA rises by >= `threshold` from its running minimum since last sell.
    Sell: MA falls by >= `threshold` from its running maximum since last buy.

    Threshold prevents whipsawing when the MA is nearly flat.
    """
    signals: List[MASignal] = []
    state = "neutral"
    running_max = float("-inf")
    running_min = float("inf")
    for i in range(len(ma_series)):
        v = ma_series[i]
        if v != v:           # skip NaN (leading bars before window fills)
            continue
        running_max = max(running_max, v)
        running_min = min(running_min, v)
        if state != "long" and (v - running_min) >= threshold:
            signals.append(MASignal(i, "buy", v))
            state = "long"
            running_max = v
        elif state != "short" and (running_max - v) >= threshold:
            signals.append(MASignal(i, "sell", v))
            state = "short"
            running_min = v
    return signals


def is_rising(prev_ma: float, curr_ma: float) -> bool:
    """The basic 'trend up' test from Schwager's text:
    rising MA is equivalent to today's close > close N days ago."""
    return curr_ma > prev_ma


# ---------- Backtest helper ----------

def backtest_ma_signals(prices: List[float], window: int, threshold: float
                        ) -> Tuple[List[MASignal], float]:
    """Simple long/flat/short backtest. Returns (signals, total return %)."""
    ma_vals = sma(prices, window)
    signals = ma_reversal_signals(ma_vals, threshold)
    if not signals:
        return signals, 0.0

    pnl = 0.0
    pos = 0          # +1 long, -1 short
    entry = 0.0
    for s in signals:
        px = prices[s.bar]
        if pos != 0:
            pnl += pos * (px - entry)
        pos = 1 if s.kind == "buy" else -1
        entry = px
    return signals, pnl


if __name__ == "__main__":
    import random, math
    random.seed(42)

    # Trending market
    n = 200
    prices_up = [50 + 0.2 * i + random.gauss(0, 0.3) for i in range(n // 2)]
    prices_dn = [prices_up[-1] - 0.2 * i + random.gauss(0, 0.3) for i in range(n // 2)]
    prices = prices_up + prices_dn

    sigs, pnl = backtest_ma_signals(prices, window=30, threshold=0.5)
    print(f"Trending market: {len(sigs)} signals, P&L = {pnl:.2f}")
    for s in sigs:
        print(f"  bar {s.bar:>3}: {s.kind:<4} @ MA={s.ma_value:.2f}, price={prices[s.bar]:.2f}")

    # Choppy market
    prices_chop = [60 + 5 * math.sin(i / 8) + random.gauss(0, 0.5) for i in range(200)]
    sigs2, pnl2 = backtest_ma_signals(prices_chop, window=30, threshold=0.3)
    print(f"\nChoppy market: {len(sigs2)} signals, P&L = {pnl2:.2f}")
    print("  (lots of whipsaws, typically losing money)")
