"""
Chapter 17 - Concept 6: Market Pattern Signal Detection
=======================================================
Detectors for the patterns Schwager identifies as
particularly high-probability:
  - New historical high that holds
  - Range breakout after extended consolidation
  - Wide-gap move (trade in its direction)
  - Bull/bear trap (failed breakout)
  - Failed-signal master principle: when a textbook signal fails,
    that failure itself is a stronger signal in the opposite direction
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class Bar:
    high: float
    low: float
    close: float
    open: float = 0.0


def is_new_historical_high_holding(bars: list[Bar], hold_days: int = 5) -> bool:
    """
    Pattern: market sets new historical high and HOLDS for `hold_days`.
    Schwager: odds favor a big move beyond the old high.
    """
    if len(bars) < hold_days + 20:           # need history for context
        return False
    historical_window = bars[:-hold_days]
    holding_window = bars[-hold_days:]
    prior_max = max(b.high for b in historical_window)
    new_high = max(b.high for b in holding_window)
    if new_high <= prior_max:
        return False
    # Holding = lowest close in the holding window stays above prior max
    lowest_close_after = min(b.close for b in holding_window)
    return lowest_close_after > prior_max


def is_range_breakout(bars: list[Bar], range_days: int = 14,
                      breakout_days: int = 1, range_tolerance: float = 0.05
                      ) -> Optional[str]:
    """
    Pattern: 1-2 weeks+ tight range, then breakout.
    Returns 'up', 'down', or None.
    """
    if len(bars) < range_days + breakout_days:
        return None
    range_bars = bars[-(range_days + breakout_days):-breakout_days]
    breakout = bars[-breakout_days:]
    range_high = max(b.high for b in range_bars)
    range_low = min(b.low for b in range_bars)
    range_size = range_high - range_low
    avg_price = sum(b.close for b in range_bars) / len(range_bars)
    if range_size / avg_price > range_tolerance * 3:
        return None                          # too wide to be a "narrow" range
    last_close = breakout[-1].close
    if last_close > range_high:
        return "up"
    if last_close < range_low:
        return "down"
    return None


def is_wide_gap(today_open: float, prev_high: float, prev_low: float,
                avg_range: float, threshold: float = 1.5
                ) -> Optional[str]:
    """
    Returns 'up' or 'down' if today's open creates a gap
    bigger than `threshold * avg_range`.
    """
    gap_up = today_open - prev_high
    gap_down = prev_low - today_open
    if gap_up > threshold * avg_range:
        return "up"
    if gap_down > threshold * avg_range:
        return "down"
    return None


def is_bull_trap(bars: list[Bar], lookback: int = 30,
                 confirm_pullback_pct: float = 0.5) -> bool:
    """
    Pattern: market breaks above prior trading range high,
    then pulls back into the range to or beyond the median.

    confirm_pullback_pct: 0.5 = initial confirmation (median of range),
                         1.0 = strong confirmation (return to lower bound)
    """
    if len(bars) < lookback + 5:
        return False
    range_bars = bars[-lookback:-5]
    breakout_window = bars[-5:]
    range_high = max(b.high for b in range_bars)
    range_low = min(b.low for b in range_bars)
    median = (range_high + range_low) / 2

    # Did we break out above range_high recently?
    breakout_made = any(b.high > range_high for b in breakout_window)
    if not breakout_made:
        return False

    # Did we pull back to the confirmation level?
    threshold_price = range_high - confirm_pullback_pct * (range_high - range_low)
    target = median if confirm_pullback_pct == 0.5 else threshold_price
    pullback = breakout_window[-1].close
    return pullback < target


def is_bear_trap(bars: list[Bar], lookback: int = 30,
                 confirm_pullback_pct: float = 0.5) -> bool:
    """Mirror of is_bull_trap for a downside breakout that fails."""
    if len(bars) < lookback + 5:
        return False
    range_bars = bars[-lookback:-5]
    breakout_window = bars[-5:]
    range_high = max(b.high for b in range_bars)
    range_low = min(b.low for b in range_bars)
    median = (range_high + range_low) / 2

    breakdown_made = any(b.low < range_low for b in breakout_window)
    if not breakdown_made:
        return False

    threshold_price = range_low + confirm_pullback_pct * (range_high - range_low)
    target = median if confirm_pullback_pct == 0.5 else threshold_price
    rebound = breakout_window[-1].close
    return rebound > target


def failed_signal_check(original_signal: str, market_followed_through: bool,
                        bars_since_signal: int, max_bars: int = 5) -> Optional[str]:
    """
    Master principle: a failed signal is more reliable than
    the original signal.

    original_signal: 'up' or 'down'
    Returns the suggested OPPOSITE-direction trade if the original failed.
    """
    if market_followed_through:
        return None
    if bars_since_signal > max_bars:
        return None
    return "down" if original_signal == "up" else "up"


# ─── DEMO ────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Build bars: 14-day tight range around 100, then breakout to 105
    range_bars = [Bar(high=101, low=99, close=100) for _ in range(14)]
    breakout_bars = [Bar(high=105, low=103, close=104.5)]
    bars = range_bars + breakout_bars
    print("Range breakout detection:", is_range_breakout(bars))

    # Bull trap: break out above 101, then collapse back to 95
    trap_bars = [Bar(high=101, low=99, close=100) for _ in range(28)] + [
        Bar(high=103, low=101, close=102.5),     # breakout
        Bar(high=104, low=102, close=103),       # extension
        Bar(high=103, low=99, close=100),        # back into range
        Bar(high=100, low=96, close=97),         # deeper pullback
        Bar(high=97, low=94, close=95),          # bull trap confirmed
    ]
    print("Bull trap detected (initial conf):",
          is_bull_trap(trap_bars, confirm_pullback_pct=0.5))
    print("Bull trap detected (strong conf):",
          is_bull_trap(trap_bars, confirm_pullback_pct=1.0))

    # Wide gap detection
    print("Wide gap:", is_wide_gap(today_open=110, prev_high=104,
                                    prev_low=102, avg_range=2.0))

    # Failed-signal principle
    print("Failed up-breakout suggests:",
          failed_signal_check("up", market_followed_through=False,
                              bars_since_signal=3))
