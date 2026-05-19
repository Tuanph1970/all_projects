"""F-024 / F-025 — Position-sizing module (Schwager Ch 16).

F-024  Fixed-fractional sizing (v1):
    shares = equity × risk_pct / |entry − stop|

F-025  Adjustments (v2):
    * ATR volatility adjustment — shrink size when current ATR implies
      higher risk than the stop-distance suggests.
    * Losing-streak halving — halve size after N consecutive losses.
    * Position cap — never exceed MAX_POSITION_PCT of equity in one leg.

A result of shares=0 signals that the trade should NOT be taken
(stop equals entry, or risk-per-share is negligible).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

MAX_POSITION_PCT = 0.20    # hard cap: 20 % of equity per position
ATR_RISK_MULTIPLIER = 2.0  # ATR × this = implied per-share risk


@dataclass
class SizeResult:
    shares: int
    risk_amount: float       # dollar risk for the full position
    risk_pct_actual: float   # actual % of equity at risk
    adjustments: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_size(
    entry_price: float,
    stop_price: float,
    equity: float,
    risk_pct: float,
    atr: Optional[float] = None,
    recent_losses: int = 0,
    loss_streak_threshold: int = 3,
    loss_streak_size_cut: float = 0.5,
) -> SizeResult:
    """Compute the position size for a new entry.

    Args:
        entry_price:          Close price at entry.
        stop_price:           Initial stop price.
        equity:               Current account equity in currency units.
        risk_pct:             Desired risk as a percentage of equity (e.g. 1.0 = 1 %).
        atr:                  Latest ATR value; enables F-025 volatility adjustment.
        recent_losses:        Number of consecutive losing trades; enables streak adj.
        loss_streak_threshold: Trigger level for streak adjustment (F-025).
        loss_streak_size_cut: Fraction of size kept after a losing streak (e.g. 0.5).
    """
    adjustments: List[str] = []

    per_share_risk = abs(entry_price - stop_price)
    if per_share_risk <= 0:
        return SizeResult(
            shares=0,
            risk_amount=0.0,
            risk_pct_actual=0.0,
            adjustments=["stop_price equals entry_price — cannot size position"],
        )

    # ── F-024: base fixed-fractional size ──────────────────────────────────
    base_risk_amount = equity * (risk_pct / 100.0)
    shares = base_risk_amount / per_share_risk

    # ── F-025: ATR volatility adjustment ───────────────────────────────────
    if atr and atr > 0:
        atr_implied_risk = atr * ATR_RISK_MULTIPLIER
        if atr_implied_risk > per_share_risk * 1.5:
            # Current ATR implies the stop will likely be hit by normal noise;
            # reduce size proportionally.
            factor = max(0.5, min(per_share_risk / atr_implied_risk, 1.0))
            shares *= factor
            adjustments.append(
                f"ATR-vol adj ×{factor:.2f} "
                f"(ATR-implied risk {atr_implied_risk:.4f} > stop risk {per_share_risk:.4f})"
            )

    # ── F-025: losing-streak adjustment ────────────────────────────────────
    if recent_losses >= loss_streak_threshold:
        shares *= loss_streak_size_cut
        adjustments.append(
            f"Streak adj ×{loss_streak_size_cut} "
            f"({recent_losses} consecutive losses ≥ threshold {loss_streak_threshold})"
        )

    # ── Position cap ───────────────────────────────────────────────────────
    max_shares_by_capital = (equity * MAX_POSITION_PCT) / entry_price
    if shares > max_shares_by_capital:
        shares = max_shares_by_capital
        adjustments.append(
            f"Capped at {MAX_POSITION_PCT * 100:.0f}% of equity "
            f"({max_shares_by_capital:.1f} shares)"
        )

    shares_int = max(0, int(shares))
    actual_risk = shares_int * per_share_risk
    actual_risk_pct = (actual_risk / equity * 100.0) if equity > 0 else 0.0

    return SizeResult(
        shares=shares_int,
        risk_amount=round(actual_risk, 2),
        risk_pct_actual=round(actual_risk_pct, 4),
        adjustments=adjustments,
    )
