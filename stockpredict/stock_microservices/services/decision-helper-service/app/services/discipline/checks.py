"""F-060..F-063 — Discipline checks (Schwager Ch 16, 17).

Four rule checks, each returning an Optional[DisciplineViolation].
Severity is either WARNING (advisory) or BLOCK (blocks entry in UI).

F-060  plan-before-trade      — entry without stop/target is BLOCK
F-061  no-averaging-down      — adding to a losing position is WARNING
F-062  stop-widening          — moving stop further from entry is WARNING
F-063  streak / drawdown      — N losses or ≥20% drawdown is WARNING
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class DisciplineViolation:
    rule_id: str
    severity: str           # "BLOCK" | "WARNING"
    message: str
    evidence: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# F-060 — Plan before trade
# ---------------------------------------------------------------------------

def check_plan_completeness(
    action: str,
    stop_price: Optional[float],
    target_price: Optional[float],
) -> Optional[DisciplineViolation]:
    """Block an entry that has no stop or no target (Schwager Ch 16)."""
    if action not in ("BUY", "SELL_SHORT"):
        return None
    missing = []
    if stop_price is None:
        missing.append("stop")
    if target_price is None:
        missing.append("target")
    if not missing:
        return None
    return DisciplineViolation(
        rule_id="F-060",
        severity="BLOCK",
        message=(
            f"Entry blocked: {' and '.join(missing)} not set "
            "(Ch 16 — always plan the trade before entering)"
        ),
        evidence={"missing": missing, "action": action},
    )


# ---------------------------------------------------------------------------
# F-061 — No averaging down
# ---------------------------------------------------------------------------

def check_no_averaging_down(
    action: str,
    pos_state: Optional[str],
    entry_price: Optional[float],
    current_price: Optional[float],
) -> Optional[DisciplineViolation]:
    """Warn if the user is adding to an existing losing position (Ch 17 rule 14)."""
    if entry_price is None or current_price is None:
        return None

    averaging_long = (
        action == "BUY"
        and pos_state == "LONG"
        and current_price < entry_price
    )
    averaging_short = (
        action == "SELL_SHORT"
        and pos_state == "SHORT"
        and current_price > entry_price
    )

    if averaging_long:
        loss_pct = (entry_price - current_price) / entry_price * 100
        return DisciplineViolation(
            rule_id="F-061",
            severity="WARNING",
            message=(
                f"Averaging down on LONG: position is {loss_pct:.1f}% in loss "
                "(Ch 17 rule 14 — never average a losing trade)"
            ),
            evidence={
                "entry_price": round(entry_price, 4),
                "current_price": round(current_price, 4),
                "loss_pct": round(loss_pct, 2),
            },
        )

    if averaging_short:
        loss_pct = (current_price - entry_price) / entry_price * 100
        return DisciplineViolation(
            rule_id="F-061",
            severity="WARNING",
            message=(
                f"Averaging down on SHORT: position is {loss_pct:.1f}% in loss "
                "(Ch 17 rule 14 — never average a losing trade)"
            ),
            evidence={
                "entry_price": round(entry_price, 4),
                "current_price": round(current_price, 4),
                "loss_pct": round(loss_pct, 2),
            },
        )

    return None


# ---------------------------------------------------------------------------
# F-062 — Stop-widening detector
# ---------------------------------------------------------------------------

def check_stop_widening(
    action: str,
    proposed_stop: Optional[float],
    prev_stop: Optional[float],
    direction: Optional[str],
) -> Optional[DisciplineViolation]:
    """Warn when a HOLD update moves the stop further from entry (Ch 9)."""
    if action != "HOLD":
        return None
    if proposed_stop is None or prev_stop is None or direction is None:
        return None

    widened_long = direction == "LONG" and proposed_stop < prev_stop
    widened_short = direction == "SHORT" and proposed_stop > prev_stop

    if widened_long or widened_short:
        return DisciplineViolation(
            rule_id="F-062",
            severity="WARNING",
            message=(
                f"Stop widened from {prev_stop:.4f} to {proposed_stop:.4f} "
                "(Ch 9 — never widen a stop once placed)"
            ),
            evidence={
                "prev_stop": round(prev_stop, 4),
                "proposed_stop": round(proposed_stop, 4),
                "direction": direction,
            },
        )

    return None


# ---------------------------------------------------------------------------
# F-063 — Streak + drawdown detector
# ---------------------------------------------------------------------------

DRAWDOWN_THRESHOLD = 0.20   # 20% from equity peak triggers warning

def check_streak_and_drawdown(
    recent_losses: int,
    loss_streak_threshold: int,
    current_equity: Optional[float] = None,
    peak_equity: Optional[float] = None,
) -> Optional[DisciplineViolation]:
    """Warn on a loss streak or a >20% drawdown from peak equity (Ch 16)."""
    if peak_equity and peak_equity > 0 and current_equity is not None:
        drawdown = (peak_equity - current_equity) / peak_equity
        if drawdown >= DRAWDOWN_THRESHOLD:
            return DisciplineViolation(
                rule_id="F-063",
                severity="WARNING",
                message=(
                    f"Drawdown alert: {drawdown * 100:.1f}% from equity peak "
                    "(Ch 16 — consider taking a break and reviewing your plan)"
                ),
                evidence={
                    "drawdown_pct": round(drawdown * 100, 2),
                    "current_equity": round(current_equity, 2),
                    "peak_equity": round(peak_equity, 2),
                },
            )

    if recent_losses >= loss_streak_threshold:
        return DisciplineViolation(
            rule_id="F-063",
            severity="WARNING",
            message=(
                f"Loss streak: {recent_losses} consecutive losses "
                f"(threshold {loss_streak_threshold}) — "
                "reduce size and consider a break (Ch 16)"
            ),
            evidence={
                "recent_losses": recent_losses,
                "threshold": loss_streak_threshold,
            },
        )

    return None


# ---------------------------------------------------------------------------
# Aggregator
# ---------------------------------------------------------------------------

def run_all_checks(
    action: str,
    stop_price: Optional[float] = None,
    target_price: Optional[float] = None,
    pos_state: Optional[str] = None,
    entry_price: Optional[float] = None,
    current_price: Optional[float] = None,
    proposed_stop: Optional[float] = None,
    prev_stop: Optional[float] = None,
    direction: Optional[str] = None,
    recent_losses: int = 0,
    loss_streak_threshold: int = 3,
    current_equity: Optional[float] = None,
    peak_equity: Optional[float] = None,
) -> List[DisciplineViolation]:
    violations: List[DisciplineViolation] = []
    for fn_result in (
        check_plan_completeness(action, stop_price, target_price),
        check_no_averaging_down(action, pos_state, entry_price, current_price),
        check_stop_widening(action, proposed_stop, prev_stop, direction),
        check_streak_and_drawdown(recent_losses, loss_streak_threshold, current_equity, peak_equity),
    ):
        if fn_result is not None:
            violations.append(fn_result)
    return violations
