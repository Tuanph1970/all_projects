"""F-020 / F-021 — Stop-loss module (Schwager Ch 9).

Priority hierarchy (Schwager's stop quality):
    CHART > SWING > ATR > MONEY

Initial stop (F-020):
  * Chart stop  — nearest S/R level on the wrong side of entry
  * Swing stop  — nearest confirmed swing pivot on the wrong side
  * ATR stop    — entry ± ATR_MULTIPLIER × ATR
  * Money stop  — entry × (1 ± max_risk_pct) as last resort

Trailing stop (F-021):
  * ATR-based: LONG → max(current, close − mult×ATR)
                SHORT → min(current, close + mult×ATR)
  * The CIC anti-pattern is enforced: the stop NEVER widens.
    update_trailing_stop() returns None when no improvement is possible.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

ATR_MULTIPLIER = 2.0
MAX_RISK_PCT = 0.05          # 5 % maximum risk per trade
STOP_BUFFER_PCT = 0.005      # 0.5 % buffer past S/R / swing pivot


@dataclass
class StopResult:
    stop_price: float
    stop_kind: str   # CHART | SWING | ATR | MONEY
    reason: str


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_initial_stop(
    direction: str,
    entry_price: float,
    atr: Optional[float],
    swings: Optional[List[Dict[str, Any]]],
    sr_levels: Optional[Dict[str, Any]],
    max_risk_pct: float = MAX_RISK_PCT,
) -> StopResult:
    """Return the highest-quality stop available for a new entry.

    Args:
        direction:    "LONG" or "SHORT".
        entry_price:  Close price at which the position is entered.
        atr:          Latest ATR(14) value from analysis-service (may be None).
        swings:       List of swing-pivot dicts from analysis-service
                      (fields: date, type, price).
        sr_levels:    S/R dict from analysis-service
                      (fields: supports[], resistances[] each with price, type, strength).
        max_risk_pct: Maximum fraction of entry price allowed as risk
                      (default 5 %).  Stops beyond this are skipped.
    """
    chart = _chart_stop(direction, entry_price, sr_levels, max_risk_pct)
    if chart:
        return chart

    swing = _swing_stop(direction, entry_price, swings, max_risk_pct)
    if swing:
        return swing

    if atr and atr > 0:
        if direction == "LONG":
            price = entry_price - ATR_MULTIPLIER * atr
        else:
            price = entry_price + ATR_MULTIPLIER * atr
        return StopResult(
            stop_price=round(price, 4),
            stop_kind="ATR",
            reason=f"ATR stop {ATR_MULTIPLIER}×{atr:.4f} from entry {entry_price:.4f}",
        )

    # Money stop — last resort
    if direction == "LONG":
        price = entry_price * (1.0 - max_risk_pct)
    else:
        price = entry_price * (1.0 + max_risk_pct)
    return StopResult(
        stop_price=round(price, 4),
        stop_kind="MONEY",
        reason=f"Money stop at {max_risk_pct * 100:.1f}% from entry {entry_price:.4f}",
    )


def update_trailing_stop(
    direction: str,
    current_stop: float,
    current_close: float,
    atr: float,
    atr_multiplier: float = ATR_MULTIPLIER,
) -> Optional[float]:
    """Return an improved trailing-stop price, or None if no improvement.

    The stop NEVER widens (CIC anti-pattern guard):
      LONG:  new candidate = close − multiplier×ATR  →  valid only if > current_stop
      SHORT: new candidate = close + multiplier×ATR  →  valid only if < current_stop
    """
    if direction == "LONG":
        candidate = current_close - atr_multiplier * atr
        if candidate > current_stop:
            return round(candidate, 4)
    else:
        candidate = current_close + atr_multiplier * atr
        if candidate < current_stop:
            return round(candidate, 4)
    return None


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _chart_stop(
    direction: str,
    entry_price: float,
    sr_levels: Optional[Dict[str, Any]],
    max_risk_pct: float,
) -> Optional[StopResult]:
    if not sr_levels:
        return None

    if direction == "LONG":
        candidates = [
            lvl for lvl in sr_levels.get("supports", [])
            if float(lvl["price"]) < entry_price
        ]
        if not candidates:
            return None
        nearest = max(candidates, key=lambda l: float(l["price"]))
        stop_price = float(nearest["price"]) * (1.0 - STOP_BUFFER_PCT)
    else:
        candidates = [
            lvl for lvl in sr_levels.get("resistances", [])
            if float(lvl["price"]) > entry_price
        ]
        if not candidates:
            return None
        nearest = min(candidates, key=lambda l: float(l["price"]))
        stop_price = float(nearest["price"]) * (1.0 + STOP_BUFFER_PCT)

    # Backlog #93. A risk FRACTION of the entry price does not exist when the
    # entry price is not a price. The vendor serves 13 zero/negative bars in
    # 320,237 (VGC, GEX, NT2 x8, SCS, HHV x2), and `compute_sr_levels` derives
    # levels from those same bars -- so the candidate filter passes and this
    # line divided by zero, taking down a 92-symbol run 21 symbols in. This
    # stop kind abstains rather than inventing a number; the caller falls
    # through to ATR, and the harness declines the entry outright.
    if entry_price <= 0:
        return None
    risk = abs(entry_price - stop_price) / entry_price
    if risk > max_risk_pct:
        return None

    return StopResult(
        stop_price=round(stop_price, 4),
        stop_kind="CHART",
        reason=(
            f"Chart stop past {nearest.get('type', 'level')} at"
            f" {float(nearest['price']):.4f}"
            f" (strength={nearest.get('strength', 1)})"
        ),
    )


def _swing_stop(
    direction: str,
    entry_price: float,
    swings: Optional[List[Dict[str, Any]]],
    max_risk_pct: float,
) -> Optional[StopResult]:
    if not swings:
        return None

    if direction == "LONG":
        candidates = [
            s for s in swings
            if s.get("type") == "low" and float(s["price"]) < entry_price
        ]
        if not candidates:
            return None
        nearest = max(candidates, key=lambda s: float(s["price"]))
        stop_price = float(nearest["price"]) * (1.0 - STOP_BUFFER_PCT)
    else:
        candidates = [
            s for s in swings
            if s.get("type") == "high" and float(s["price"]) > entry_price
        ]
        if not candidates:
            return None
        nearest = min(candidates, key=lambda s: float(s["price"]))
        stop_price = float(nearest["price"]) * (1.0 + STOP_BUFFER_PCT)

    # Backlog #93. A risk FRACTION of the entry price does not exist when the
    # entry price is not a price. The vendor serves 13 zero/negative bars in
    # 320,237 (VGC, GEX, NT2 x8, SCS, HHV x2), and `compute_sr_levels` derives
    # levels from those same bars -- so the candidate filter passes and this
    # line divided by zero, taking down a 92-symbol run 21 symbols in. This
    # stop kind abstains rather than inventing a number; the caller falls
    # through to ATR, and the harness declines the entry outright.
    if entry_price <= 0:
        return None
    risk = abs(entry_price - stop_price) / entry_price
    if risk > max_risk_pct:
        return None

    return StopResult(
        stop_price=round(stop_price, 4),
        stop_kind="SWING",
        reason=f"Swing stop at {float(nearest['price']):.4f} (pivot date={nearest.get('date', '?')})",
    )
