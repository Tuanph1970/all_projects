"""
Pyramiding Rules — Chapter 8, Concept 6
Schwager: "Getting Started in Technical Analysis"

Three rules for safely adding to winning positions:
1. Last unit must show a profit
2. Stop must not imply net loss for entire position
3. Pyramid units <= base position size

Midtrend entry strategies (Concepts 2-5) apply to pyramid timing.
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import Literal


@dataclass
class PyramidUnit:
    """A single unit (tranche) in a pyramid position."""
    entry_price: float
    shares: int
    entry_date: str = ""

    @property
    def cost(self) -> float:
        return self.entry_price * self.shares


@dataclass
class PyramidPosition:
    """
    Manages a full pyramid position with Schwager's three rules.
    """
    direction: Literal["long", "short"] = "long"
    units: list = field(default_factory=list)

    @property
    def total_shares(self) -> int:
        return sum(u.shares for u in self.units)

    @property
    def total_cost(self) -> float:
        return sum(u.cost for u in self.units)

    @property
    def avg_cost(self) -> float:
        if self.total_shares == 0:
            return 0
        return self.total_cost / self.total_shares

    @property
    def base_shares(self) -> int:
        return self.units[0].shares if self.units else 0

    def current_pnl(self, current_price: float) -> float:
        """Total P/L at current price."""
        if self.direction == "long":
            return (current_price - self.avg_cost) * self.total_shares
        return (self.avg_cost - current_price) * self.total_shares

    def pnl_at_stop(self, stop_price: float) -> float:
        """Total P/L if stopped out."""
        if self.direction == "long":
            return (stop_price - self.avg_cost) * self.total_shares
        return (self.avg_cost - stop_price) * self.total_shares

    def check_rule_1(self, current_price: float) -> dict:
        """Rule 1: Last unit must show a profit."""
        if len(self.units) < 2:
            return {"pass": True, "detail": "Only base position -- rule N/A"}
        last = self.units[-1]
        if self.direction == "long":
            profitable = current_price > last.entry_price
        else:
            profitable = current_price < last.entry_price
        return {
            "pass": profitable,
            "detail": (
                f"Last unit entry=${last.entry_price:.2f}, "
                f"current=${current_price:.2f}, "
                f"{'profitable' if profitable else 'UNDERWATER'}"
            ),
        }

    def check_rule_2(self, stop_price: float) -> dict:
        """Rule 2: Stop must not imply net loss for entire position."""
        pnl = self.pnl_at_stop(stop_price)
        ok = pnl >= 0
        return {
            "pass": ok,
            "detail": (
                f"P/L at stop ${stop_price:.2f} = ${pnl:.2f} "
                f"({'break-even or profit' if ok else 'NET LOSS'})"
            ),
        }

    def check_rule_3(self) -> dict:
        """Rule 3: Pyramid units <= base position size."""
        if len(self.units) < 2:
            return {"pass": True, "detail": "Only base position -- rule N/A"}
        base = self.units[0].shares
        violations = [
            u for u in self.units[1:] if u.shares > base
        ]
        ok = len(violations) == 0
        return {
            "pass": ok,
            "detail": (
                f"Base={base} shares. "
                + (
                    "All pyramid units <= base"
                    if ok
                    else f"{len(violations)} unit(s) exceed base size"
                )
            ),
        }

    def check_all_rules(
        self, current_price: float, stop_price: float
    ) -> list[dict]:
        """Check all three pyramiding rules."""
        return [
            {"rule": "1. Last unit profitable", **self.check_rule_1(current_price)},
            {"rule": "2. Stop != net loss", **self.check_rule_2(stop_price)},
            {"rule": "3. Units <= base", **self.check_rule_3()},
        ]

    def can_add_unit(
        self,
        new_shares: int,
        new_price: float,
        current_price: float,
        stop_price: float,
    ) -> dict:
        """
        Check whether a new pyramid unit can be safely added.
        """
        reasons = []

        # Rule 1: last unit must be profitable NOW
        r1 = self.check_rule_1(current_price)
        if not r1["pass"]:
            reasons.append(f"Rule 1 violated: {r1['detail']}")

        # Rule 3: new unit must not exceed base
        if new_shares > self.base_shares:
            reasons.append(
                f"Rule 3 violated: new unit {new_shares} shares > "
                f"base {self.base_shares} shares"
            )

        # Rule 2: simulate adding, check stop P/L
        sim_units = self.units + [PyramidUnit(new_price, new_shares)]
        sim_pos = PyramidPosition(self.direction, sim_units)
        r2 = sim_pos.check_rule_2(stop_price)
        if not r2["pass"]:
            reasons.append(f"Rule 2 violated after adding: {r2['detail']}")

        return {
            "allowed": len(reasons) == 0,
            "reasons": reasons if reasons else ["All rules pass -- safe to add"],
        }

    def add_unit(
        self,
        shares: int,
        entry_price: float,
        current_price: float,
        stop_price: float,
        entry_date: str = "",
        force: bool = False,
    ) -> dict:
        """
        Attempt to add a pyramid unit. Checks all rules first.
        """
        check = self.can_add_unit(shares, entry_price, current_price, stop_price)

        if check["allowed"] or force:
            self.units.append(PyramidUnit(entry_price, shares, entry_date))
            return {
                "added": True,
                "check": check,
                "total_shares": self.total_shares,
                "avg_cost": round(self.avg_cost, 2),
                "pnl_at_stop": round(self.pnl_at_stop(stop_price), 2),
            }
        return {"added": False, "check": check}

    def summary(self, current_price: float, stop_price: float) -> dict:
        """Full position summary."""
        return {
            "num_units": len(self.units),
            "total_shares": self.total_shares,
            "avg_cost": round(self.avg_cost, 2),
            "current_pnl": round(self.current_pnl(current_price), 2),
            "pnl_at_stop": round(self.pnl_at_stop(stop_price), 2),
            "rules": self.check_all_rules(current_price, stop_price),
            "units": [
                {
                    "entry": u.entry_price,
                    "shares": u.shares,
                    "pnl": round(
                        (current_price - u.entry_price) * u.shares
                        if self.direction == "long"
                        else (u.entry_price - current_price) * u.shares,
                        2,
                    ),
                }
                for u in self.units
            ],
        }


def build_example_pyramid() -> PyramidPosition:
    """
    Build Schwager's textbook example:
    Buy at $30, add at $35, $45, with tapering size.
    """
    pos = PyramidPosition(direction="long")
    pos.units = [
        PyramidUnit(30, 100, "Day 1"),
        PyramidUnit(35, 80, "Day 15"),
        PyramidUnit(45, 60, "Day 30"),
    ]
    return pos


# --- Demo ---
if __name__ == "__main__":
    print("=== Schwager's Textbook Pyramid ===")
    pos = build_example_pyramid()

    current = 50.0
    stop = 32.0
    summary = pos.summary(current, stop)

    print(f"  Units: {summary['num_units']}")
    print(f"  Total shares: {summary['total_shares']}")
    print(f"  Avg cost: ${summary['avg_cost']}")
    print(f"  Current P/L: ${summary['current_pnl']}")
    print(f"  P/L at stop ${stop}: ${summary['pnl_at_stop']}")
    print()

    for r in summary["rules"]:
        status = "PASS" if r["pass"] else "FAIL"
        print(f"  [{status}] {r['rule']}: {r['detail']}")

    print()
    for u in summary["units"]:
        print(f"  Entry ${u['entry']}, {u['shares']}sh -> P/L ${u['pnl']}")

    print("\n=== Can we add another unit? ===")
    check = pos.can_add_unit(
        new_shares=50, new_price=52, current_price=50, stop_price=32
    )
    print(f"  Allowed: {check['allowed']}")
    for r in check["reasons"]:
        print(f"  - {r}")

    print("\n=== What if stop is too low? ===")
    bad_stop = 25.0
    bad_summary = pos.summary(current, bad_stop)
    print(f"  P/L at stop ${bad_stop}: ${bad_summary['pnl_at_stop']}")
    for r in bad_summary["rules"]:
        status = "PASS" if r["pass"] else "FAIL"
        print(f"  [{status}] {r['rule']}: {r['detail']}")
