"""F-043 — Pyramiding guard rails (Schwager Ch 8, 14).

Schwager allows adding to a *winning* position, but only with strict risk
discipline.  ``evaluate_pyramid`` is a pure decision function that enforces the
three guards from the backlog:

    1. **50 % pyramid cap** — cumulative pyramid shares may not exceed
       ``max_pyramid_fraction`` (default 0.5) of the *initial* entry size.
       An over-sized add is clamped to the remaining allowance, not rejected.
    2. **Tighter stops on add** — the position stop is moved to the tighter of
       the current stop and the new leg's stop; it is NEVER widened.
    3. **No adds after a losing streak** — once ``recent_losses`` reaches
       ``loss_streak_threshold`` the add is refused outright.

A precondition gates all of the above: pyramids are only ever added to a
position that is currently in profit (add to winners, not losers).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class PyramidDecision:
    allowed: bool
    add_shares: int
    new_stop: Optional[float]          # recommended (tightened) position stop
    reason: str
    guards_triggered: List[str] = field(default_factory=list)


def evaluate_pyramid(
    *,
    direction: str,                    # "LONG" | "SHORT"
    entry_price: float,
    current_close: float,
    current_stop: float,
    initial_shares: int,
    pyramided_shares: int,
    proposed_add_shares: int,
    proposed_add_stop: float,
    recent_losses: int = 0,
    loss_streak_threshold: int = 3,
    max_pyramid_fraction: float = 0.5,
) -> PyramidDecision:
    guards: List[str] = []

    if initial_shares <= 0 or proposed_add_shares <= 0:
        return PyramidDecision(False, 0, None, "no base position or zero add", guards)

    # ── Precondition: only add to winners ────────────────────────────────
    in_profit = (
        current_close > entry_price if direction == "LONG"
        else current_close < entry_price
    )
    if not in_profit:
        guards.append("not_winning")
        return PyramidDecision(False, 0, None, "position not in profit — no pyramid", guards)

    # ── Guard 3: no adds during a losing streak ──────────────────────────
    if recent_losses >= loss_streak_threshold:
        guards.append("loss_streak")
        return PyramidDecision(
            False, 0, None,
            f"{recent_losses} consecutive losses ≥ threshold {loss_streak_threshold}",
            guards,
        )

    # ── Guard 1: 50 % pyramid cap ────────────────────────────────────────
    max_pyramid_shares = int(math.floor(max_pyramid_fraction * initial_shares))
    allowance = max_pyramid_shares - pyramided_shares
    if allowance <= 0:
        guards.append("max_pyramid")
        return PyramidDecision(
            False, 0, None,
            f"pyramid cap reached ({pyramided_shares}/{max_pyramid_shares} shares)",
            guards,
        )

    add_shares = min(proposed_add_shares, allowance)
    if add_shares < proposed_add_shares:
        guards.append("max_pyramid")  # clamped, not rejected

    # ── Guard 2: tighten the stop, never widen ───────────────────────────
    if direction == "LONG":
        new_stop = max(current_stop, proposed_add_stop)   # higher = tighter
    else:
        new_stop = min(current_stop, proposed_add_stop)   # lower = tighter

    return PyramidDecision(
        allowed=True,
        add_shares=add_shares,
        new_stop=new_stop,
        reason=f"pyramid add of {add_shares} shares (stop → {new_stop:.4f})",
        guards_triggered=guards,
    )
