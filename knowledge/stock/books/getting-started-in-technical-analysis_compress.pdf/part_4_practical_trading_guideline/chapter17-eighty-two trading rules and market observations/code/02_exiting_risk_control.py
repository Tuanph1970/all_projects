"""
Chapter 17 - Concept 2: Exiting Losing Trades & Risk Control
============================================================
Implements three independent exit triggers:
  1. Hard stop-loss (set at entry)
  2. Premise-broken (chart pattern that justified the trade fails)
  3. Volatility shock (move far in excess of recent range, against you)

Bonus: gap-breakout detection — Schwager says liquidate immediately
on a gap breakout against your position.
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class ExitReason(Enum):
    HARD_STOP = "hard_stop"
    PREMISE_BROKEN = "premise_broken"
    VOL_SHOCK = "vol_shock"
    GAP_BREAKOUT_AGAINST = "gap_breakout_against"
    NONE = "none"


@dataclass
class Bar:
    """A single OHLC bar."""
    date: str
    open: float
    high: float
    low: float
    close: float


@dataclass
class Position:
    symbol: str
    direction: str                         # "long" or "short"
    entry_price: float
    shares: int
    hard_stop: float                       # mandatory
    premise: str                           # text description of original setup
    premise_still_valid: bool = True       # flip to False when chart says so
    open: bool = True
    exit_price: Optional[float] = None
    exit_reason: ExitReason = ExitReason.NONE


def average_true_range(bars: list[Bar], window: int = 20) -> float:
    """ATR — used as the volatility yardstick."""
    if len(bars) < 2:
        return 0.0
    bars = bars[-window - 1:]
    trs = []
    for i in range(1, len(bars)):
        high, low = bars[i].high, bars[i].low
        prev_close = bars[i - 1].close
        tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
        trs.append(tr)
    return sum(trs) / len(trs) if trs else 0.0


def check_exit(pos: Position, today: Bar, prior: Bar,
               recent_bars: list[Bar],
               vol_shock_multiplier: float = 2.5) -> ExitReason:
    """
    Evaluate the three triggers in priority order.
    Returns the first trigger that fires.
    """
    if not pos.open:
        return ExitReason.NONE

    # Trigger 1: hard stop hit
    if pos.direction == "long" and today.low <= pos.hard_stop:
        return ExitReason.HARD_STOP
    if pos.direction == "short" and today.high >= pos.hard_stop:
        return ExitReason.HARD_STOP

    # Trigger 4 (highest priority): gap breakout against position
    # Defined as: today's open gaps past a key level in the wrong direction.
    if pos.direction == "long" and today.open < prior.low and today.open < pos.entry_price:
        return ExitReason.GAP_BREAKOUT_AGAINST
    if pos.direction == "short" and today.open > prior.high and today.open > pos.entry_price:
        return ExitReason.GAP_BREAKOUT_AGAINST

    # Trigger 3: volatility shock (move far exceeds recent normal range)
    atr = average_true_range(recent_bars)
    if atr > 0:
        adverse_move = (
            pos.entry_price - today.close if pos.direction == "long"
            else today.close - pos.entry_price
        )
        if adverse_move > vol_shock_multiplier * atr:
            return ExitReason.VOL_SHOCK

    # Trigger 2: original premise has been invalidated by analyst
    if not pos.premise_still_valid:
        return ExitReason.PREMISE_BROKEN

    return ExitReason.NONE


def liquidate(pos: Position, price: float, reason: ExitReason) -> None:
    pos.open = False
    pos.exit_price = price
    pos.exit_reason = reason


def pnl(pos: Position) -> float:
    if pos.exit_price is None:
        return 0.0
    sign = 1 if pos.direction == "long" else -1
    return sign * (pos.exit_price - pos.entry_price) * pos.shares


# ─── DEMO ────────────────────────────────────────────────────────
if __name__ == "__main__":
    pos = Position(
        symbol="MSFT",
        direction="long",
        entry_price=100.00,
        shares=100,
        hard_stop=94.00,
        premise="Bull flag breakout above $99",
    )

    # Simulate 21 prior bars of normal ~$2 daily range
    history = [
        Bar(f"D-{i}", 99 + i * 0.05, 101 + i * 0.05, 99 - 1 + i * 0.05, 100 + i * 0.05)
        for i in range(21)
    ]

    # Scenario A: Volatility shock — 6-point drop on what was a $2-range stock
    today = Bar("D+1", 99.5, 99.8, 92.0, 92.5)
    prior = history[-1]
    reason = check_exit(pos, today, prior, history)
    print(f"Scenario A (vol shock): trigger = {reason.value}")
    if reason != ExitReason.NONE:
        liquidate(pos, today.close, reason)
        print(f"  Exit @ ${pos.exit_price}, P/L = ${pnl(pos):+,.2f}")

    # Reset for scenario B
    pos2 = Position(symbol="MSFT", direction="long", entry_price=100, shares=100,
                    hard_stop=94, premise="Bull flag")
    today2 = Bar("D+1", 90.0, 91.0, 89.5, 90.5)   # GAP DOWN at open
    prior2 = history[-1]                           # prior low ~99
    print(f"\nScenario B (gap against): trigger = "
          f"{check_exit(pos2, today2, prior2, history).value}")

    # Scenario C: Premise broken (analyst flips the flag interpretation)
    pos3 = Position(symbol="MSFT", direction="long", entry_price=100, shares=100,
                    hard_stop=94, premise="Bull flag")
    pos3.premise_still_valid = False               # analyst marks it broken
    today3 = Bar("D+1", 99.5, 100, 98.5, 99.0)
    print(f"\nScenario C (premise broken): trigger = "
          f"{check_exit(pos3, today3, history[-1], history).value}")
