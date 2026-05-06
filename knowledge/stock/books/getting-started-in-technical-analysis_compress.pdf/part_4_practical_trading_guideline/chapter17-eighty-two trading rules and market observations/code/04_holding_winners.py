"""
Chapter 17 - Concept 4: Holding and Exiting Winning Trades
==========================================================
The "let winners run" mechanism: trailing stops with optional
partial-profit logic.

Schwager's principles applied here:
  - Don't take small/quick profits in major position trades
  - Use trailing stops, not fixed objectives, as the main exit
  - If 50-60% of an objective is hit very fast (1 week),
    consider partial profit-taking with intent to re-enter
  - When equity is surging "too fast", scale-up profits cautiously
"""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class TrailingStop:
    """ATR-multiple trailing stop that ratchets only in the trade direction."""
    direction: str                 # "long" or "short"
    atr_multiplier: float = 2.5
    current_stop: Optional[float] = None
    highest_high_since_entry: Optional[float] = None
    lowest_low_since_entry: Optional[float] = None

    def update(self, today_high: float, today_low: float, atr: float) -> float:
        if self.direction == "long":
            if self.highest_high_since_entry is None \
                    or today_high > self.highest_high_since_entry:
                self.highest_high_since_entry = today_high
            new_stop = self.highest_high_since_entry - self.atr_multiplier * atr
            if self.current_stop is None or new_stop > self.current_stop:
                self.current_stop = new_stop  # ratchets up only
        else:
            if self.lowest_low_since_entry is None \
                    or today_low < self.lowest_low_since_entry:
                self.lowest_low_since_entry = today_low
            new_stop = self.lowest_low_since_entry + self.atr_multiplier * atr
            if self.current_stop is None or new_stop < self.current_stop:
                self.current_stop = new_stop  # ratchets down only
        return self.current_stop

    def is_hit(self, today_high: float, today_low: float) -> bool:
        if self.current_stop is None:
            return False
        if self.direction == "long":
            return today_low <= self.current_stop
        return today_high >= self.current_stop


@dataclass
class WinnerPosition:
    symbol: str
    direction: str
    entry_price: float
    shares: int
    initial_objective: float          # used only for the "fast move" trigger
    trail: TrailingStop
    open_shares: Optional[int] = None
    partial_taken: bool = False

    def __post_init__(self):
        self.open_shares = self.shares

    def fraction_of_objective_reached(self, current_price: float) -> float:
        """How far between entry and initial objective have we travelled?"""
        denom = self.initial_objective - self.entry_price
        if denom == 0:
            return 0.0
        progress = (current_price - self.entry_price) / denom
        return progress

    def consider_partial_profit(self, current_price: float, days_held: int,
                                fast_threshold: float = 0.55,
                                fast_days: int = 7) -> bool:
        """
        Rule of thumb: if 50-60% of objective hit within 1 week,
        scale out part of the position.
        Returns True if partial profit was taken on this call.
        """
        if self.partial_taken or self.open_shares is None:
            return False
        progress = self.fraction_of_objective_reached(current_price)
        if days_held <= fast_days and progress >= fast_threshold:
            sold = self.open_shares // 2
            self.open_shares -= sold
            self.partial_taken = True
            print(f"  [partial profit] sold {sold} shares of "
                  f"{self.symbol} @ ${current_price:.2f} "
                  f"(progress {progress*100:.0f}% in {days_held} days)")
            return True
        return False


# ─── DEMO ────────────────────────────────────────────────────────
if __name__ == "__main__":
    pos = WinnerPosition(
        symbol="NVDA",
        direction="long",
        entry_price=100.0,
        shares=200,
        initial_objective=115.0,
        trail=TrailingStop(direction="long", atr_multiplier=2.5),
    )

    # Simulate 15 days of strong rally — daily price + ATR ~$2
    daily_data = [
        # (high, low, close)
        (102, 100, 101),
        (104, 101, 103.5),
        (107, 103, 106.5),
        (110, 106, 109),       # day 4: progress = (109-100)/(115-100) = 60%
        (113, 108, 112),
        (116, 112, 115),
        (119, 114, 118.5),
        (122, 117, 121),
        (125, 120, 124),
        (130, 123, 128),       # parabolic — equity surging
        (134, 126, 132),
        (137, 130, 134),
        (139, 132, 135),
        (140, 134, 138),
        (138, 130, 132),       # first pullback
    ]
    atr = 2.0
    for day, (h, l, c) in enumerate(daily_data, start=1):
        stop = pos.trail.update(h, l, atr)
        pos.consider_partial_profit(c, days_held=day)
        hit = pos.trail.is_hit(h, l)
        flag = "  ← STOP HIT" if hit else ""
        print(f"Day {day:2d}: H={h} L={l} C={c} | "
              f"trailing stop={stop:.2f}{flag}")
        if hit:
            exit_price = stop  # assume filled at stop
            sign = 1
            pnl_per_share = sign * (exit_price - pos.entry_price)
            total_pnl = (pnl_per_share * pos.open_shares
                         + (pos.shares - pos.open_shares)
                         * (124 - pos.entry_price))  # rough partial value
            print(f"\nFinal exit @ ${exit_price:.2f}, "
                  f"open shares P/L = ${pnl_per_share*pos.open_shares:+,.2f}")
            break
