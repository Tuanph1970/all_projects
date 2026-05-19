"""F-022 / F-023 — Profit-target module (Schwager Ch 10).

Priority:
    1. MEASURED_MOVE  — from pattern evidence (measured_move_target field)
    2. SR_LEVEL       — first viable S/R level in the direction of trade
    3. FIXED_RR       — 2:1 reward-to-risk fallback

F-023 partial exits:
    partial_target is the price at which 50 % of the position should be
    closed.  It sits at the midpoint between entry and the full target.
    The remainder is held with a trailing stop.

A candidate target is only accepted if it achieves at least MIN_RR
reward-to-risk relative to the initial stop.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

MIN_RR = 1.0      # minimum reward : risk ratio
FIXED_RR = 2.0    # fallback R:R multiple


@dataclass
class TargetResult:
    target_price: float
    target_kind: str           # MEASURED_MOVE | SR_LEVEL | FIXED_RR
    partial_target: Optional[float]   # 50 % exit level (F-023)
    reason: str


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_target(
    direction: str,
    entry_price: float,
    stop_price: float,
    signal_kind: str,
    signal_evidence: Dict[str, Any],
    sr_levels: Optional[Dict[str, Any]],
) -> TargetResult:
    """Return the best available profit target for a new entry.

    Args:
        direction:        "LONG" or "SHORT".
        entry_price:      Close price at which the position is entered.
        stop_price:       Initial stop computed by stop_module.
        signal_kind:      e.g. "MA_CROSS", "N_DAY_BREAKOUT", "SR_BREAKOUT".
        signal_evidence:  Evidence dict from the raw signal; may contain
                          "measured_move_target" from pattern detectors.
        sr_levels:        S/R response dict from analysis-service.
    """
    risk = abs(entry_price - stop_price)

    # 1. Measured move from pattern evidence
    mm_raw = signal_evidence.get("measured_move_target")
    if mm_raw is not None:
        mm = float(mm_raw)
        correct_side = (
            (direction == "LONG" and mm > entry_price)
            or (direction == "SHORT" and mm < entry_price)
        )
        rr = abs(mm - entry_price) / risk if risk > 0 else 0.0
        if correct_side and rr >= MIN_RR:
            return TargetResult(
                target_price=round(mm, 4),
                target_kind="MEASURED_MOVE",
                partial_target=round(_midpoint(entry_price, mm), 4),
                reason=(
                    f"Measured-move target from {signal_kind} pattern"
                    f" ({mm:.4f}, R:R={rr:.1f}:1)"
                ),
            )

    # 2. S/R level objective
    sr = _sr_target(direction, entry_price, stop_price, sr_levels)
    if sr:
        return sr

    # 3. Fixed R:R fallback
    if direction == "LONG":
        target = entry_price + FIXED_RR * risk
    else:
        target = entry_price - FIXED_RR * risk
    return TargetResult(
        target_price=round(target, 4),
        target_kind="FIXED_RR",
        partial_target=round(_midpoint(entry_price, target), 4),
        reason=f"Fixed {FIXED_RR:.0f}:1 R:R target (no pattern / S/R target available)",
    )


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _sr_target(
    direction: str,
    entry_price: float,
    stop_price: float,
    sr_levels: Optional[Dict[str, Any]],
) -> Optional[TargetResult]:
    if not sr_levels:
        return None

    risk = abs(entry_price - stop_price)
    if risk <= 0:
        return None

    if direction == "LONG":
        candidates = [
            lvl for lvl in sr_levels.get("resistances", [])
            if float(lvl["price"]) > entry_price
        ]
        if not candidates:
            return None
        nearest = min(candidates, key=lambda l: float(l["price"]))
    else:
        candidates = [
            lvl for lvl in sr_levels.get("supports", [])
            if float(lvl["price"]) < entry_price
        ]
        if not candidates:
            return None
        nearest = max(candidates, key=lambda l: float(l["price"]))

    rr = abs(float(nearest["price"]) - entry_price) / risk
    if rr < MIN_RR:
        return None

    return TargetResult(
        target_price=round(float(nearest["price"]), 4),
        target_kind="SR_LEVEL",
        partial_target=round(_midpoint(entry_price, float(nearest["price"])), 4),
        reason=(
            f"{nearest.get('type', 'level')} at {float(nearest['price']):.4f}"
            f" (strength={nearest.get('strength', 1)}, R:R={rr:.1f}:1)"
        ),
    )


def _midpoint(a: float, b: float) -> float:
    return (a + b) / 2.0
