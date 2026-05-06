"""
Chapter 17 - Concept 1: Entering Trades
========================================
A pre-trade checklist that enforces Schwager's discipline rules
for major position entry.

Key principles synthesized:
- Differentiate major position trades vs short-term
- Plan entries; never trade on intraday impulse
- Require a confirming chart pattern
- Don't fade gaps, don't fade recent failure patterns
- Use market orders for important entries
- Don't double up after retracement to entry
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class TradeType(Enum):
    MAJOR_POSITION = "major"        # Larger size, focus of book
    SHORT_TERM = "short_term"        # Smaller size, lower priority


class OrderType(Enum):
    MARKET = "market"
    LIMIT = "limit"


@dataclass
class EntryChecklist:
    """Pre-trade gate. ALL must be True for a major position trade."""
    has_confirming_pattern: bool = False
    pattern_description: str = ""
    planned_in_advance: bool = False           # Not an intraday impulse
    stop_loss_defined: bool = False
    stop_price: Optional[float] = None
    no_recent_failure_signal: bool = True      # No bull/bear trap recently
    not_fading_first_gap: bool = True
    instinct_aligns: bool = True               # Gut read of chart agrees

    def is_ready(self, trade_type: TradeType) -> tuple[bool, list[str]]:
        """Return (passes, list_of_blockers)."""
        blockers = []
        if not self.has_confirming_pattern:
            blockers.append("No confirming chart pattern.")
        if not self.planned_in_advance:
            blockers.append("Trade is an intraday impulse, not planned.")
        if not self.stop_loss_defined or self.stop_price is None:
            blockers.append("Stop-loss not defined at entry.")
        if not self.no_recent_failure_signal:
            blockers.append("Fading a recent failure pattern is forbidden.")
        if not self.not_fading_first_gap:
            blockers.append("Don't fade the first gap of a price move.")
        if trade_type == TradeType.MAJOR_POSITION and not self.instinct_aligns:
            blockers.append("Instinctive chart read disagrees with the trade.")
        return (len(blockers) == 0, blockers)


@dataclass
class PlannedTrade:
    symbol: str
    direction: str                           # "long" or "short"
    trade_type: TradeType
    entry_price_target: float
    size_shares: int
    checklist: EntryChecklist
    order_type: OrderType = OrderType.MARKET  # Schwager prefers market orders
    notes: str = ""
    created_at: datetime = field(default_factory=datetime.now)

    def implied_risk(self) -> float:
        """Dollar risk if stop is hit."""
        if self.checklist.stop_price is None:
            return float("nan")
        per_share = abs(self.entry_price_target - self.checklist.stop_price)
        return per_share * self.size_shares

    def attempt_entry(self) -> str:
        ready, blockers = self.checklist.is_ready(self.trade_type)
        if not ready:
            return "REJECTED:\n  - " + "\n  - ".join(blockers)
        risk = self.implied_risk()
        return (
            f"ENTRY APPROVED — {self.direction.upper()} {self.size_shares} "
            f"{self.symbol} @ ~${self.entry_price_target:.2f} "
            f"(stop ${self.checklist.stop_price:.2f}, "
            f"risk ${risk:,.2f}) via {self.order_type.value} order"
        )


def already_chasing(target_price: float, current_price: float,
                    direction: str, max_slippage_pct: float = 1.0) -> bool:
    """
    Rule: don't be greedy chasing a slightly-better entry.
    But also: don't chase too far past your plan either — that's the
    flip side. Returns True if current price is too far past target
    in the direction of the trade.
    """
    move_pct = (current_price - target_price) / target_price * 100
    if direction == "long" and move_pct > max_slippage_pct:
        return True
    if direction == "short" and move_pct < -max_slippage_pct:
        return True
    return False


# ─── DEMO ────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Example: a planned long entry on a flag breakout
    checklist = EntryChecklist(
        has_confirming_pattern=True,
        pattern_description="Bull flag after 30% advance; tight 5-day consolidation",
        planned_in_advance=True,
        stop_loss_defined=True,
        stop_price=94.00,                      # Just below flag low
        no_recent_failure_signal=True,
        not_fading_first_gap=True,
        instinct_aligns=True,
    )

    trade = PlannedTrade(
        symbol="AAPL",
        direction="long",
        trade_type=TradeType.MAJOR_POSITION,
        entry_price_target=100.00,
        size_shares=100,
        checklist=checklist,
        notes="Breakout on 35-day chart; market structure healthy.",
    )
    print(trade.attempt_entry())

    # Example of a rejected impulse trade
    bad = PlannedTrade(
        symbol="TSLA",
        direction="long",
        trade_type=TradeType.MAJOR_POSITION,
        entry_price_target=250.00,
        size_shares=50,
        checklist=EntryChecklist(
            has_confirming_pattern=False,
            planned_in_advance=False,          # Impulse
            stop_loss_defined=False,
        ),
    )
    print()
    print(bad.attempt_entry())

    # Chase check
    print()
    print("Chase check (target=100, current=101.5, long):",
          already_chasing(100, 101.5, "long"))
