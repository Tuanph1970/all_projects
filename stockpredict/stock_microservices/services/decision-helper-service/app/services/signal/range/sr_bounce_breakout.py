"""F-015 — S/R bounce and breakout signals for trading-range regime (Schwager Ch 4, 14).

Two distinct signals are produced from the S/R level set:

BOUNCE (inside-range signal)
  LONG  — close touched / bounced off a support level and closed above it.
  SHORT — close touched / bounced off a resistance level and closed below it.
  Confidence rises with the strength (touch count) of the level and how
  close the low/high came to the level before closing back inside.

BREAKOUT (range-exit signal)
  LONG  — close penetrated resistance and closed above it.
  SHORT — close penetrated support and closed below it.
  Confidence scales with penetration depth (same formula as N-day breakout).

Only the strongest signal (by confidence) is returned; None if none fire.
"""
from __future__ import annotations

import logging
from datetime import date
from typing import Any, Dict, List, Optional

from app.services.signal.base import OHLCVBar, RawSignal

logger = logging.getLogger(__name__)

# proximity band: bar must have traded within this % of the level price
PROXIMITY_PCT = 0.015
# minimum penetration to count as a confirmed breakout
MIN_BREAKOUT_PCT = 0.005


def detect_sr_signal(
    bars: List[OHLCVBar],
    bar_date: date,
    sr_data: Dict[str, Any],
) -> Optional[RawSignal]:
    """Return the best (highest-confidence) S/R-based signal for bar_date."""
    idx = next((i for i, b in enumerate(bars) if b.date == bar_date), None)
    if idx is None:
        return None

    today = bars[idx]
    supports: List[Dict] = sr_data.get("supports", [])
    resistances: List[Dict] = sr_data.get("resistances", [])

    candidates: List[RawSignal] = []

    # --- BOUNCE at support (LONG signal) ---
    for lvl in supports:
        level_price: float = float(lvl["price"])
        strength: int = int(lvl.get("strength", 1))
        proximity = abs(today.low - level_price) / level_price if level_price else 1
        if proximity <= PROXIMITY_PCT and today.close > level_price:
            bounce_depth = (level_price - today.low) / level_price if level_price else 0
            conf = min(0.4 + strength * 0.05 + bounce_depth / 0.01 * 0.1, 0.9)
            candidates.append(RawSignal(
                kind="SR_BOUNCE",
                direction="LONG",
                confidence=round(conf, 3),
                bar_date=bar_date,
                trigger_price=today.close,
                evidence={
                    "level_price": round(level_price, 4),
                    "level_strength": strength,
                    "proximity_pct": round(proximity * 100, 3),
                    "bounce_type": "support",
                },
            ))

    # --- BOUNCE at resistance (SHORT signal) ---
    for lvl in resistances:
        level_price = float(lvl["price"])
        strength = int(lvl.get("strength", 1))
        proximity = abs(today.high - level_price) / level_price if level_price else 1
        if proximity <= PROXIMITY_PCT and today.close < level_price:
            bounce_depth = (today.high - level_price) / level_price if level_price else 0
            conf = min(0.4 + strength * 0.05 + bounce_depth / 0.01 * 0.1, 0.9)
            candidates.append(RawSignal(
                kind="SR_BOUNCE",
                direction="SHORT",
                confidence=round(conf, 3),
                bar_date=bar_date,
                trigger_price=today.close,
                evidence={
                    "level_price": round(level_price, 4),
                    "level_strength": strength,
                    "proximity_pct": round(proximity * 100, 3),
                    "bounce_type": "resistance",
                },
            ))

    # --- BREAKOUT above resistance (LONG signal) ---
    for lvl in resistances:
        level_price = float(lvl["price"])
        strength = int(lvl.get("strength", 1))
        penetration = (today.close - level_price) / level_price if level_price else 0
        if penetration >= MIN_BREAKOUT_PCT:
            conf = min(0.55 + strength * 0.05 + penetration / 0.03 * 0.3, 0.95)
            candidates.append(RawSignal(
                kind="SR_BREAKOUT",
                direction="LONG",
                confidence=round(conf, 3),
                bar_date=bar_date,
                trigger_price=today.close,
                evidence={
                    "level_price": round(level_price, 4),
                    "level_strength": strength,
                    "penetration_pct": round(penetration * 100, 3),
                    "breakout_type": "resistance",
                },
            ))

    # --- BREAKOUT below support (SHORT signal) ---
    for lvl in supports:
        level_price = float(lvl["price"])
        strength = int(lvl.get("strength", 1))
        penetration = (level_price - today.close) / level_price if level_price else 0
        if penetration >= MIN_BREAKOUT_PCT:
            conf = min(0.55 + strength * 0.05 + penetration / 0.03 * 0.3, 0.95)
            candidates.append(RawSignal(
                kind="SR_BREAKOUT",
                direction="SHORT",
                confidence=round(conf, 3),
                bar_date=bar_date,
                trigger_price=today.close,
                evidence={
                    "level_price": round(level_price, 4),
                    "level_strength": strength,
                    "penetration_pct": round(penetration * 100, 3),
                    "breakout_type": "support",
                },
            ))

    if not candidates:
        return None

    return max(candidates, key=lambda s: s.confidence)
