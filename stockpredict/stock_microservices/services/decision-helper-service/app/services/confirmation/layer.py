"""F-016 — Confirmation layer (Schwager Ch 7, 14).

Applies three independent tests to a RawSignal before it can advance
to the recommendation stage:

1. PENETRATION %
   The close must have moved at least `min_penetration_pct` beyond the
   trigger level.  For MA-cross signals the trigger level is the slow MA;
   for breakout signals it's the breakout level stored in evidence.
   Minimum: 0.3% to filter noise; configurable per signal kind.

2. TIME DELAY (K bars)
   Checks that the N most recent closes have held on the correct side of
   the trigger level.  K=1 means we require only the current bar (no
   delay); K=2 means the previous bar also closed correctly.  For Phase B
   we default to K=1 (immediate) so as not to lose real signals while the
   pipeline is young.

3. OSCILLATOR-AS-ALERT RULE (Schwager Ch 6 / rule)
   In a TREND regime: oscillators (RSI) must NOT be at an extreme against
   the signal direction (i.e. overbought when entering LONG).  The signal
   is not rejected outright but confidence is penalised 20 % and a
   warning reason step is added.
   In a RANGE regime: oscillators ARE required to be at a boundary
   (oversold for LONG bounce, overbought for SHORT bounce) — absence of
   oscillator confirmation reduces confidence by 15 %.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Dict, List, Optional

from app.services.signal.base import OHLCVBar, RawSignal

logger = logging.getLogger(__name__)

# Minimum penetration per signal kind (as fraction of trigger price)
MIN_PENETRATION: Dict[str, float] = {
    "MA_CROSS": 0.003,
    "N_DAY_BREAKOUT": 0.005,
    "SR_BOUNCE": 0.003,
    "SR_BREAKOUT": 0.005,
}

RSI_OVERBOUGHT = 70.0
RSI_OVERSOLD = 30.0


@dataclass
class ConfirmationResult:
    accepted: bool
    signal: RawSignal
    final_confidence: float
    reason_steps: List[Dict[str, Any]] = field(default_factory=list)
    rejection_reason: Optional[str] = None


def _extract_trigger_level(signal: RawSignal) -> Optional[float]:
    """Return the level price that defines the penetration baseline."""
    ev = signal.evidence
    if signal.kind == "MA_CROSS":
        return ev.get("slow_ma")
    if signal.kind in ("N_DAY_BREAKOUT",):
        return ev.get("breakout_level")
    if signal.kind in ("SR_BOUNCE", "SR_BREAKOUT"):
        return ev.get("level_price")
    return None


def confirm(
    signal: RawSignal,
    bars: List[OHLCVBar],
    regime: str,
    rsi: Optional[float] = None,
    k_delay: int = 1,
) -> ConfirmationResult:
    """Run all three confirmation checks and return a ConfirmationResult.

    Args:
        signal:  The raw signal to confirm.
        bars:    Full OHLCV series (sorted oldest → newest).
        regime:  TREND_UP | TREND_DOWN | RANGE | UNDEFINED
        rsi:     Latest RSI value (may be None if unavailable).
        k_delay: Number of consecutive closing bars (including today) that
                 must hold on the correct side of the trigger level.
    """
    reason_steps: List[Dict[str, Any]] = []
    confidence = signal.confidence

    # ------------------------------------------------------------------ #
    # 1. Penetration check                                                 #
    # ------------------------------------------------------------------ #
    trigger_level = _extract_trigger_level(signal)
    min_pct = MIN_PENETRATION.get(signal.kind, 0.003)

    if trigger_level and trigger_level > 0:
        if signal.direction == "LONG":
            penetration = (signal.trigger_price - trigger_level) / trigger_level
        else:
            penetration = (trigger_level - signal.trigger_price) / trigger_level

        if penetration < min_pct:
            reason_steps.append({
                "stage": "penetration_check",
                "result": "FAIL",
                "penetration_pct": round(penetration * 100, 3),
                "required_pct": round(min_pct * 100, 3),
            })
            return ConfirmationResult(
                accepted=False,
                signal=signal,
                final_confidence=0.0,
                reason_steps=reason_steps,
                rejection_reason=f"Penetration {penetration*100:.2f}% < required {min_pct*100:.2f}%",
            )
        reason_steps.append({
            "stage": "penetration_check",
            "result": "PASS",
            "penetration_pct": round(penetration * 100, 3),
        })
    else:
        reason_steps.append({
            "stage": "penetration_check",
            "result": "SKIP",
            "note": "trigger level unavailable",
        })

    # ------------------------------------------------------------------ #
    # 2. Time-delay check (k consecutive bars on correct side)            #
    # ------------------------------------------------------------------ #
    if k_delay > 1 and trigger_level:
        # Check the k most recent bars (including bar_date)
        bar_date = signal.bar_date
        idx = next((i for i, b in enumerate(bars) if b.date == bar_date), None)
        if idx is not None and idx >= k_delay - 1:
            window = bars[idx - k_delay + 1 : idx + 1]
            if signal.direction == "LONG":
                held = all(b.close > trigger_level for b in window)
            else:
                held = all(b.close < trigger_level for b in window)

            if not held:
                reason_steps.append({
                    "stage": "time_delay_check",
                    "result": "FAIL",
                    "k": k_delay,
                })
                return ConfirmationResult(
                    accepted=False,
                    signal=signal,
                    final_confidence=0.0,
                    reason_steps=reason_steps,
                    rejection_reason=f"Price did not hold above/below trigger for {k_delay} bars",
                )
            reason_steps.append({"stage": "time_delay_check", "result": "PASS", "k": k_delay})
    else:
        reason_steps.append({"stage": "time_delay_check", "result": "SKIP", "k": k_delay})

    # ------------------------------------------------------------------ #
    # 3. Oscillator-as-alert rule                                         #
    # ------------------------------------------------------------------ #
    if rsi is not None:
        in_trend = regime in ("TREND_UP", "TREND_DOWN")
        if in_trend:
            if signal.direction == "LONG" and rsi >= RSI_OVERBOUGHT:
                confidence *= 0.80
                reason_steps.append({
                    "stage": "oscillator_alert",
                    "result": "WARN",
                    "note": f"RSI {rsi:.1f} overbought on LONG entry in TREND — confidence -20%",
                    "rsi": rsi,
                })
            elif signal.direction == "SHORT" and rsi <= RSI_OVERSOLD:
                confidence *= 0.80
                reason_steps.append({
                    "stage": "oscillator_alert",
                    "result": "WARN",
                    "note": f"RSI {rsi:.1f} oversold on SHORT entry in TREND — confidence -20%",
                    "rsi": rsi,
                })
            else:
                reason_steps.append({"stage": "oscillator_alert", "result": "PASS", "rsi": rsi})
        else:
            # RANGE regime: oscillator confirmation IS required for bounces
            if signal.kind == "SR_BOUNCE":
                if signal.direction == "LONG" and rsi > RSI_OVERSOLD:
                    confidence *= 0.85
                    reason_steps.append({
                        "stage": "oscillator_alert",
                        "result": "WARN",
                        "note": f"RSI {rsi:.1f} not oversold at support bounce — confidence -15%",
                        "rsi": rsi,
                    })
                elif signal.direction == "SHORT" and rsi < RSI_OVERBOUGHT:
                    confidence *= 0.85
                    reason_steps.append({
                        "stage": "oscillator_alert",
                        "result": "WARN",
                        "note": f"RSI {rsi:.1f} not overbought at resistance bounce — confidence -15%",
                        "rsi": rsi,
                    })
                else:
                    reason_steps.append({"stage": "oscillator_alert", "result": "PASS", "rsi": rsi})
            else:
                reason_steps.append({"stage": "oscillator_alert", "result": "SKIP", "rsi": rsi})
    else:
        reason_steps.append({"stage": "oscillator_alert", "result": "SKIP", "note": "RSI unavailable"})

    return ConfirmationResult(
        accepted=True,
        signal=signal,
        final_confidence=round(confidence, 3),
        reason_steps=reason_steps,
    )
