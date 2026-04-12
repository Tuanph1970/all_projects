"""
Wide-Ranging Day Stops — Chapter 9, Concept 5
===============================================
After a wide-ranging day (a bar whose true range exceeds k times the
average true range), the return to the opposite end signals reversal
→ place stop at the true low (for bullish WRD) or true high (for bearish).

Schwager: "Similar to flags and pennants, after a breakout in one direction,
the return to the opposite end can be used as a signal of a price reversal."

This module provides:
  - OHLC: dataclass for price bar data
  - true_high, true_low, true_range: Welles Wilder's true range components
  - detect_wide_ranging_days: find WRDs in a bar series
  - wrd_stop_price: compute stop at the opposite end
  - evaluate_wrd_stop: backtest WRD stop performance
"""

from dataclasses import dataclass
from typing import Optional
import random


@dataclass
class OHLC:
    """A single price bar with open, high, low, close."""
    open: float
    high: float
    low: float
    close: float

    @property
    def range(self) -> float:
        """Simple range: high - low."""
        return self.high - self.low

    @property
    def is_bullish(self) -> bool:
        """Close above open."""
        return self.close >= self.open

    @property
    def body_ratio(self) -> float:
        """Ratio of body to total range (0-1). High = strong close direction."""
        if self.range == 0:
            return 0
        return abs(self.close - self.open) / self.range


def true_high(bar: OHLC, prev_close: float) -> float:
    """
    True high = max(high, previous close).
    Accounts for gap-ups where the previous close is above the current high.
    Welles Wilder's definition from the Appendix.
    """
    return max(bar.high, prev_close)


def true_low(bar: OHLC, prev_close: float) -> float:
    """
    True low = min(low, previous close).
    Accounts for gap-downs where the previous close is below the current low.
    """
    return min(bar.low, prev_close)


def true_range(bar: OHLC, prev_close: float) -> float:
    """True range = true high - true low."""
    return true_high(bar, prev_close) - true_low(bar, prev_close)


def average_true_range(bars: list[OHLC], period: int = 10) -> list[float]:
    """
    Compute average true range (ATR) for each bar.
    Returns a list of the same length as bars; first 'period' entries are None.
    """
    atrs = [None] * len(bars)
    if len(bars) < period + 1:
        return atrs

    for i in range(period, len(bars)):
        total = 0
        for j in range(i - period, i):
            prev_c = bars[j - 1].close if j > 0 else bars[j].open
            total += true_range(bars[j], prev_c)
        atrs[i] = total / period

    return atrs


@dataclass
class WideRangingDay:
    """A detected wide-ranging day."""
    bar_index: int
    bar: OHLC
    true_high_val: float
    true_low_val: float
    true_range_val: float
    avg_true_range: float
    multiplier: float           # how many times ATR

    @property
    def direction(self) -> str:
        """'up' if close is in upper half of range, else 'down'."""
        mid = (self.bar.high + self.bar.low) / 2
        return 'up' if self.bar.close > mid else 'down'

    @property
    def stop_price(self) -> float:
        """
        Stop at the opposite end (true low for up WRD, true high for down WRD).
        """
        if self.direction == 'up':
            return self.true_low_val
        else:
            return self.true_high_val

    @property
    def entry_price(self) -> float:
        """Entry at the close of the WRD."""
        return self.bar.close

    @property
    def risk_pct(self) -> float:
        """Risk from entry to stop as percentage."""
        return abs(self.entry_price - self.stop_price) / self.entry_price * 100


def detect_wide_ranging_days(
    bars: list[OHLC],
    multiplier: float = 2.0,
    lookback: int = 10,
) -> list[WideRangingDay]:
    """
    Detect wide-ranging days: bars whose true range exceeds
    multiplier * average true range of the preceding lookback bars.
    
    Args:
        bars: List of OHLC bars
        multiplier: Threshold (Schwager suggests ~2.0)
        lookback: Number of bars for ATR calculation
    
    Returns:
        List of detected WideRangingDay objects
    """
    atrs = average_true_range(bars, lookback)
    wrds = []

    for i in range(lookback, len(bars)):
        if atrs[i] is None or atrs[i] == 0:
            continue

        prev_c = bars[i - 1].close
        tr = true_range(bars[i], prev_c)
        th = true_high(bars[i], prev_c)
        tl = true_low(bars[i], prev_c)

        if tr > multiplier * atrs[i]:
            wrds.append(WideRangingDay(
                bar_index=i,
                bar=bars[i],
                true_high_val=th,
                true_low_val=tl,
                true_range_val=tr,
                avg_true_range=atrs[i],
                multiplier=round(tr / atrs[i], 2),
            ))

    return wrds


def wrd_stop_price(wrd: WideRangingDay, buffer_pct: float = 0.0) -> float:
    """
    Compute stop price from a WRD.
    For up WRD: stop at true low (minus optional buffer).
    For down WRD: stop at true high (plus optional buffer).
    """
    base = wrd.stop_price
    if wrd.direction == 'up':
        return base * (1 - buffer_pct / 100)
    else:
        return base * (1 + buffer_pct / 100)


def evaluate_wrd_stop(
    n_trials: int = 500,
    multiplier: float = 2.0,
    lookback: int = 10,
    n_bars: int = 90,
    seed_base: int = 42,
) -> dict:
    """
    Backtest WRD stop performance across simulated scenarios.
    Each scenario has a spike bar injected at bar 40.
    
    Returns:
        dict with avg_pnl, worst_pnl, false_stop_rate, avg_risk
    """
    pnls = []
    risks = []
    false_stops = 0
    total_stopped = 0
    no_wrd = 0

    for t in range(n_trials):
        random.seed(seed_base + t * 23)
        
        # Generate bars
        bars = []
        price = 100.0
        for i in range(n_bars):
            vol = 1.5
            # Inject spike at bar 40
            if i == 40:
                vol = 5 + random.random() * 4
            drift = 0.1 if i < 55 else -0.15
            o = price
            move = vol * random.gauss(0, 1) + drift
            if i == 40:
                move = abs(move) + 2  # force bullish WRD
            c = o + move
            h = max(o, c) + abs(random.gauss(0, 1)) * vol * 0.3
            l = min(o, c) - abs(random.gauss(0, 1)) * vol * 0.3
            bars.append(OHLC(o, h, l, c))
            price = c

        # Detect WRDs
        wrds = detect_wide_ranging_days(bars, multiplier, lookback)
        if not wrds:
            no_wrd += 1
            continue

        wrd = wrds[0]
        stop = wrd.stop_price
        entry = wrd.entry_price
        risks.append(wrd.risk_pct)

        # Evaluate post-WRD
        stopped = False
        for i in range(wrd.bar_index + 1, len(bars)):
            if bars[i].low <= stop:
                pnl = (stop - entry) / entry * 100
                pnls.append(pnl)
                total_stopped += 1
                future = bars[i + 1:min(i + 20, len(bars))]
                if any(b.high > entry for b in future):
                    false_stops += 1
                stopped = True
                break

        if not stopped:
            final = bars[-1].close
            pnl = (final - entry) / entry * 100
            pnls.append(pnl)

    return {
        "n_trials": n_trials,
        "multiplier": multiplier,
        "lookback": lookback,
        "detected_wrd_pct": round((n_trials - no_wrd) / n_trials * 100, 1),
        "avg_risk_pct": round(sum(risks) / max(len(risks), 1), 1),
        "avg_pnl": round(sum(pnls) / max(len(pnls), 1), 2),
        "worst_pnl": round(min(pnls) if pnls else 0, 2),
        "false_stop_rate": round(false_stops / max(total_stopped, 1) * 100, 1),
        "total_stopped": total_stopped,
    }


# --- Demo ---
if __name__ == "__main__":
    # 1. Generate sample bars with a spike
    random.seed(42)
    bars = []
    price = 100.0
    for i in range(60):
        vol = 1.5 if i != 30 else 7.0
        drift = 0.1
        o = price
        move = vol * random.gauss(0, 1) + drift
        if i == 30:
            move = abs(move) + 3
        c = o + move
        h = max(o, c) + abs(random.gauss(0, 1)) * 0.5
        l = min(o, c) - abs(random.gauss(0, 1)) * 0.5
        bars.append(OHLC(round(o, 2), round(h, 2), round(l, 2), round(c, 2)))
        price = c

    # 2. Detect WRDs
    wrds = detect_wide_ranging_days(bars, multiplier=2.0, lookback=10)
    print(f"Detected {len(wrds)} wide-ranging day(s)")
    for w in wrds:
        print(f"  Bar {w.bar_index}: direction={w.direction}, "
              f"TR={w.true_range_val:.1f} ({w.multiplier:.1f}x ATR), "
              f"stop={w.stop_price:.1f}, risk={w.risk_pct:.1f}%")

    # 3. Backtest at different multipliers
    print("\n--- Multiplier comparison ---")
    print(f"{'Mult':>6} {'Detected':>10} {'Avg Risk':>9} {'Avg P&L':>8} {'Worst':>8} {'False%':>8}")
    print("-" * 55)
    for m in [1.5, 2.0, 2.5, 3.0]:
        r = evaluate_wrd_stop(n_trials=500, multiplier=m)
        print(f"{m:>5.1f}x {r['detected_wrd_pct']:>9.1f}% "
              f"{r['avg_risk_pct']:>8.1f}% {r['avg_pnl']:>+7.1f}% "
              f"{r['worst_pnl']:>+7.1f}% {r['false_stop_rate']:>7.1f}%")
