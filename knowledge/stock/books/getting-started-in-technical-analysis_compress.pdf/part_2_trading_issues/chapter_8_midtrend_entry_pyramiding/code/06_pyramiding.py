"""
Concept 6 — Pyramiding (Chapter 8)
==================================
Pyramiding = adding to an existing winning position as the trend
continues. Schwager points out that the *timing decision* for a pyramid
add is identical to the midtrend-entry decision, so any of the four
midtrend-entry strategies can serve as the trigger for adding units.

Three core risk rules from the chapter, encoded here as guards:
    1. Never add unless the LAST unit placed is currently profitable.
    2. Never add if the new aggregate stop would imply a NET LOSS on
       the entire position.
    3. Pyramid units must be NO LARGER than the base (initial) unit.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Literal


@dataclass
class Unit:
    bar: int
    qty: int
    entry_price: float


@dataclass
class PyramidPosition:
    side: Literal["LONG", "SHORT"]
    base_qty: int
    units: list[Unit] = field(default_factory=list)
    stop_price: float | None = None        # current aggregate stop

    # ------- queries -------
    @property
    def total_qty(self) -> int:
        return sum(u.qty for u in self.units)

    @property
    def avg_entry(self) -> float:
        if not self.units:
            return 0.0
        notion = sum(u.qty * u.entry_price for u in self.units)
        return notion / self.total_qty

    def unrealized_pnl(self, mark: float) -> float:
        sign = 1 if self.side == "LONG" else -1
        return sign * (mark - self.avg_entry) * self.total_qty

    def pnl_at_stop(self, stop: float) -> float:
        sign = 1 if self.side == "LONG" else -1
        return sign * (stop - self.avg_entry) * self.total_qty

    # ------- mutations -------
    def open_base(self, bar: int, price: float, stop: float) -> None:
        if self.units:
            raise RuntimeError("Base already opened")
        self.units.append(Unit(bar=bar, qty=self.base_qty, entry_price=price))
        self.stop_price = stop

    def try_add(self, bar: int, price: float, qty: int,
                proposed_stop: float) -> tuple[bool, str]:
        """
        Apply Schwager's three pyramid guards. Returns (accepted, reason).
        Modifies state only if accepted.
        """
        if not self.units:
            return False, "No base position open."

        # Rule 3 — qty cap
        if qty > self.base_qty:
            return False, (f"Pyramid unit ({qty}) exceeds base size "
                           f"({self.base_qty}).")

        # Rule 1 — last unit must be profitable
        last = self.units[-1]
        sign = 1 if self.side == "LONG" else -1
        if sign * (price - last.entry_price) <= 0:
            return False, ("Last unit is not in profit "
                           f"(last entry {last.entry_price:.2f}, "
                           f"current {price:.2f}).")

        # Rule 2 — combined stop must not imply net loss
        # Tentatively add the unit and re-check the aggregate.
        trial_units = self.units + [Unit(bar, qty, price)]
        trial_qty = sum(u.qty for u in trial_units)
        trial_avg = sum(u.qty * u.entry_price for u in trial_units) / trial_qty
        trial_pnl = sign * (proposed_stop - trial_avg) * trial_qty
        if trial_pnl < 0:
            return False, (f"Combined stop {proposed_stop:.2f} would imply "
                           f"net loss {trial_pnl:.2f} on the position.")

        # All guards passed — commit
        self.units = trial_units
        self.stop_price = proposed_stop
        return True, "Pyramid unit added."


# ---------------------------------------------------------------------
if __name__ == "__main__":
    pos = PyramidPosition(side="LONG", base_qty=100)
    pos.open_base(bar=10, price=30.0, stop=28.0)
    print(f"Base opened: 100 @ $30 (stop $28). Avg entry = {pos.avg_entry:.2f}")

    # Try to pyramid at $35 with stop raised to $32
    ok, reason = pos.try_add(bar=40, price=35.0, qty=100, proposed_stop=32.0)
    print(f"\nAdd #1 @ $35, stop $32 → {ok}: {reason}")
    print(f"   total qty={pos.total_qty}, avg={pos.avg_entry:.2f}, "
          f"PnL_at_stop={pos.pnl_at_stop(pos.stop_price):.0f}")

    # Try to pyramid at $42 with stop $36
    ok, reason = pos.try_add(bar=70, price=42.0, qty=100, proposed_stop=36.0)
    print(f"\nAdd #2 @ $42, stop $36 → {ok}: {reason}")
    print(f"   total qty={pos.total_qty}, avg={pos.avg_entry:.2f}, "
          f"PnL_at_stop={pos.pnl_at_stop(pos.stop_price):.0f}")

    # Violation: pyramid bigger than base
    ok, reason = pos.try_add(bar=80, price=44.0, qty=200, proposed_stop=40.0)
    print(f"\nAdd #3 with qty=200 (bigger than base) → {ok}: {reason}")

    # Violation: stop would imply net loss
    ok, reason = pos.try_add(bar=80, price=44.0, qty=100, proposed_stop=30.0)
    print(f"\nAdd #3 with stop=$30 (too low) → {ok}: {reason}")

    # Violation: last unit not in profit
    ok, reason = pos.try_add(bar=85, price=41.0, qty=100, proposed_stop=39.0)
    print(f"\nAdd #3 @ $41 (last unit was @ $42) → {ok}: {reason}")

    # Valid add
    ok, reason = pos.try_add(bar=85, price=48.0, qty=100, proposed_stop=42.0)
    print(f"\nAdd #3 @ $48, stop $42 → {ok}: {reason}")
    print(f"   total qty={pos.total_qty}, avg={pos.avg_entry:.2f}, "
          f"PnL_at_stop={pos.pnl_at_stop(pos.stop_price):.0f}")
