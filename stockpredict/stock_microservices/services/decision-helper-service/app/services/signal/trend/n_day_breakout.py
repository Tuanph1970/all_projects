"""F-014 — N-day high/low breakout detector (Schwager Ch 14).

LONG signal: today's close > highest close of the previous N bars.
SHORT signal: today's close < lowest close of the previous N bars.

The lookback window is *exclusive* of bar_date, so an N=20 breakout
fires when close exceeds the highest close of the 20 bars before it.

Confidence scales with how far the close penetrated the breakout level.
"""
from __future__ import annotations

import logging
from datetime import date
from typing import List, Optional

from app.services.signal.base import OHLCVBar, RawSignal

logger = logging.getLogger(__name__)

DEFAULT_N = 20


def detect_n_day_breakout(
    bars: List[OHLCVBar],
    bar_date: date,
    n: int = DEFAULT_N,
) -> Optional[RawSignal]:
    """Return a RawSignal if bar_date closed outside the N-bar range, else None."""
    idx = next((i for i, b in enumerate(bars) if b.date == bar_date), None)
    if idx is None or idx < n:
        return None

    lookback = bars[idx - n : idx]   # n bars before today, exclusive
    today = bars[idx]

    highest = max(b.close for b in lookback)
    lowest = min(b.close for b in lookback)

    breakout_up = today.close > highest
    breakout_dn = today.close < lowest

    if not (breakout_up or breakout_dn):
        return None

    if breakout_up:
        penetration = (today.close - highest) / highest if highest else 0.0
        direction = "LONG"
        level = highest
    else:
        penetration = (lowest - today.close) / lowest if lowest else 0.0
        direction = "SHORT"
        level = lowest

    confidence = min(0.5 + penetration / 0.03 * 0.5, 1.0)

    return RawSignal(
        kind="N_DAY_BREAKOUT",
        direction=direction,
        confidence=round(confidence, 3),
        bar_date=bar_date,
        trigger_price=today.close,
        evidence={
            "n": n,
            "breakout_level": round(level, 4),
            "penetration_pct": round(penetration * 100, 3),
            "close": today.close,
        },
    )
