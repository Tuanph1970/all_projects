"""
Confirmation Conditions Evaluator — Chapter 11, Concept 4
==========================================================
Implements Schwager's three confirmation conditions for bull/bear traps:
  1. Initial Price Confirmation — retrace to midpoint
  2. Strong Price Confirmation — retrace to opposite boundary
  3. Time Confirmation — no return to breakout extreme within N bars

Also implements the invalidation rules and a multi-factor scoring system.

Schwager: "The trade-off between initial and strong price confirmations
is that the former will provide better entry levels in trading bull and
bear traps, whereas the latter will provide more reliable signals."
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class TrapType(Enum):
    BULL = "bull"  # Failed upside breakout → sell signal
    BEAR = "bear"  # Failed downside breakout → buy signal


class ConfirmationLevel(Enum):
    NONE = "none"
    INITIAL_PRICE = "initial_price"
    STRONG_PRICE = "strong_price"
    TIME = "time"


@dataclass
class ConfirmationState:
    """Tracks which confirmations have fired and when."""
    initial_price: bool = False
    initial_price_date: Optional[pd.Timestamp] = None
    initial_price_level: Optional[float] = None

    strong_price: bool = False
    strong_price_date: Optional[pd.Timestamp] = None
    strong_price_level: Optional[float] = None

    time: bool = False
    time_date: Optional[pd.Timestamp] = None
    time_elapsed_bars: int = 0

    invalidated: bool = False
    invalidation_date: Optional[pd.Timestamp] = None

    @property
    def count(self) -> int:
        """Number of confirmations that have fired."""
        return sum([self.initial_price, self.strong_price, self.time])

    @property
    def first_confirmation_date(self) -> Optional[pd.Timestamp]:
        """Date of the earliest confirmation."""
        dates = []
        if self.initial_price_date:
            dates.append(self.initial_price_date)
        if self.strong_price_date:
            dates.append(self.strong_price_date)
        if self.time_date:
            dates.append(self.time_date)
        return min(dates) if dates else None

    @property
    def confidence_score(self) -> float:
        """
        Weighted confidence score (0.0 to 1.0).

        Strong price confirmation carries the most weight because
        Schwager calls it the "more reliable" signal.
        """
        if self.invalidated:
            return 0.0
        score = 0.0
        if self.initial_price:
            score += 0.25
        if self.strong_price:
            score += 0.45
        if self.time:
            score += 0.30
        return score


@dataclass
class TradeParameters:
    """Entry, stop, and risk parameters derived from confirmation state."""
    trap_type: TrapType
    entry_price: float
    stop_loss: float
    entry_confirmation: str
    risk: float
    reward_to_risk: Optional[float] = None
    target: Optional[float] = None


def evaluate_confirmations(
    trap_type: TrapType,
    breakout_extreme: float,
    range_high: float,
    range_low: float,
    post_breakout_df: pd.DataFrame,
    time_confirm_bars: int = 20,
    invalidation_buffer_pct: float = 0.005,
) -> ConfirmationState:
    """
    Evaluate all three confirmation conditions against post-breakout price data.

    Parameters
    ----------
    trap_type : BULL or BEAR
    breakout_extreme : the high (bull trap) or low (bear trap) of the breakout
    range_high : resistance level of the prior consolidation
    range_low : support level of the prior consolidation
    post_breakout_df : DataFrame with ['high', 'low', 'close'] after breakout
    time_confirm_bars : number of bars for time confirmation
    invalidation_buffer_pct : buffer beyond breakout extreme for invalidation

    Returns
    -------
    ConfirmationState with all three conditions evaluated
    """
    midpoint = (range_high + range_low) / 2
    state = ConfirmationState()

    for i, (date, bar) in enumerate(post_breakout_df.iterrows()):
        # ── Invalidation check (always first) ──
        if trap_type == TrapType.BULL:
            invalidation_level = breakout_extreme * (1 + invalidation_buffer_pct)
            if bar['high'] > invalidation_level:
                state.invalidated = True
                state.invalidation_date = date
                return state
        else:  # BEAR
            invalidation_level = breakout_extreme * (1 - invalidation_buffer_pct)
            if bar['low'] < invalidation_level:
                state.invalidated = True
                state.invalidation_date = date
                return state

        # ── Initial Price Confirmation ──
        if not state.initial_price:
            if trap_type == TrapType.BULL and bar['close'] < midpoint:
                state.initial_price = True
                state.initial_price_date = date
                state.initial_price_level = bar['close']
            elif trap_type == TrapType.BEAR and bar['close'] > midpoint:
                state.initial_price = True
                state.initial_price_date = date
                state.initial_price_level = bar['close']

        # ── Strong Price Confirmation ──
        if not state.strong_price:
            if trap_type == TrapType.BULL and bar['close'] < range_low:
                state.strong_price = True
                state.strong_price_date = date
                state.strong_price_level = bar['close']
            elif trap_type == TrapType.BEAR and bar['close'] > range_high:
                state.strong_price = True
                state.strong_price_date = date
                state.strong_price_level = bar['close']

        # ── Time Confirmation ──
        if not state.time and i + 1 >= time_confirm_bars:
            if trap_type == TrapType.BULL and bar['close'] < range_high:
                state.time = True
                state.time_date = date
                state.time_elapsed_bars = i + 1
            elif trap_type == TrapType.BEAR and bar['close'] > range_low:
                state.time = True
                state.time_date = date
                state.time_elapsed_bars = i + 1

    return state


def derive_trade_params(
    trap_type: TrapType,
    state: ConfirmationState,
    breakout_extreme: float,
    range_high: float,
    range_low: float,
    target_multiple: float = 2.0,
    preferred_confirmation: str = "earliest",
) -> Optional[TradeParameters]:
    """
    Derive trade entry parameters from confirmation state.

    Parameters
    ----------
    trap_type : BULL or BEAR
    state : evaluated ConfirmationState
    breakout_extreme : stop loss level
    range_high, range_low : consolidation boundaries
    target_multiple : target distance as multiple of range height
    preferred_confirmation : 'earliest', 'initial_price', 'strong_price', 'time'

    Returns
    -------
    TradeParameters or None if no confirmation / invalidated
    """
    if state.invalidated or state.count == 0:
        return None

    range_height = range_high - range_low

    # Select entry based on preference
    if preferred_confirmation == "earliest":
        date = state.first_confirmation_date
        if state.initial_price_date == date:
            entry = state.initial_price_level
            conf = "initial_price"
        elif state.time_date == date:
            entry = state.strong_price_level or state.initial_price_level
            conf = "time"
        else:
            entry = state.strong_price_level
            conf = "strong_price"
    elif preferred_confirmation == "initial_price" and state.initial_price:
        entry = state.initial_price_level
        conf = "initial_price"
    elif preferred_confirmation == "strong_price" and state.strong_price:
        entry = state.strong_price_level
        conf = "strong_price"
    elif preferred_confirmation == "time" and state.time:
        # Use best available price level at time confirmation
        entry = state.strong_price_level or state.initial_price_level
        conf = "time"
    else:
        return None

    if entry is None:
        return None

    stop = breakout_extreme

    if trap_type == TrapType.BULL:
        risk = stop - entry
        target = range_low - range_height * target_multiple
        reward = entry - target
    else:
        risk = entry - stop
        target = range_high + range_height * target_multiple
        reward = target - entry

    rr = reward / risk if risk > 0 else 0

    return TradeParameters(
        trap_type=trap_type,
        entry_price=entry,
        stop_loss=stop,
        entry_confirmation=conf,
        risk=risk,
        reward_to_risk=rr,
        target=target,
    )


def compare_confirmations(
    trap_type: TrapType,
    state: ConfirmationState,
    breakout_extreme: float,
    range_high: float,
    range_low: float,
) -> dict:
    """
    Compare all fired confirmations side-by-side for decision support.

    Returns a dict of {confirmation_type: TradeParameters} for each
    confirmation that has fired.
    """
    results = {}
    for conf_type in ["initial_price", "strong_price", "time"]:
        params = derive_trade_params(
            trap_type, state, breakout_extreme,
            range_high, range_low,
            preferred_confirmation=conf_type,
        )
        if params:
            results[conf_type] = params
    return results


# ── Example usage ──────────────────────────────────────────────────
if __name__ == "__main__":
    np.random.seed(42)
    dates = pd.date_range('2024-01-01', periods=60, freq='B')

    # Bull trap scenario: range 95-105, breakout to 110, then decline
    range_bars = np.clip(100 + np.random.randn(25) * 2, 96, 104)
    breakout = [107, 110, 111]
    decline = [108, 105, 102, 100, 98, 96, 94, 93, 92, 91,
               90, 89, 88, 87, 86, 85, 84, 83, 82, 81,
               80, 79, 78, 77, 76, 75, 74, 73, 72, 71, 70, 69]

    all_close = np.concatenate([range_bars, breakout, decline])
    highs = all_close + np.random.uniform(0.5, 2, len(all_close))
    lows = all_close - np.random.uniform(0.5, 2, len(all_close))

    df = pd.DataFrame({
        'high': highs, 'low': lows, 'close': all_close
    }, index=dates)

    # Evaluate
    post_df = df.iloc[28:]  # After breakout
    state = evaluate_confirmations(
        trap_type=TrapType.BULL,
        breakout_extreme=111 + 2,  # high of breakout bar
        range_high=104,
        range_low=96,
        post_breakout_df=post_df,
    )

    print("=== Confirmation State ===")
    print(f"  Initial price: {state.initial_price}"
          + (f" ({state.initial_price_date.date()})" if state.initial_price else ""))
    print(f"  Strong price:  {state.strong_price}"
          + (f" ({state.strong_price_date.date()})" if state.strong_price else ""))
    print(f"  Time:          {state.time}"
          + (f" ({state.time_date.date()}, {state.time_elapsed_bars} bars)" if state.time else ""))
    print(f"  Invalidated:   {state.invalidated}")
    print(f"  Confidence:    {state.confidence_score:.0%}")
    print(f"  Count:         {state.count}/3")

    print("\n=== Comparison ===")
    comparison = compare_confirmations(
        TrapType.BULL, state, 113, 104, 96
    )
    for conf_type, params in comparison.items():
        print(f"\n  {conf_type}:")
        print(f"    Entry:    {params.entry_price:.1f}")
        print(f"    Stop:     {params.stop_loss:.1f}")
        print(f"    Target:   {params.target:.1f}")
        print(f"    Risk:     {params.risk:.1f}")
        print(f"    R:R:      {params.reward_to_risk:.1f}")
