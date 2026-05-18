"""F-013 — MA-crossover signal detector (Schwager Ch 14).

Emits a LONG signal when the fast MA crosses above the slow MA on the
bar identified by bar_date, and a SHORT signal on the inverse crossing.

Confidence is proportional to how far apart the two MAs are relative to
the slow MA value — a wider gap at the crossover is a stronger signal.
"""
from __future__ import annotations

import logging
from datetime import date
from typing import List, Optional

from app.services.signal.base import OHLCVBar, RawSignal, _sma

logger = logging.getLogger(__name__)

DEFAULT_FAST = 10
DEFAULT_SLOW = 50


def detect_ma_cross(
    bars: List[OHLCVBar],
    bar_date: date,
    fast_period: int = DEFAULT_FAST,
    slow_period: int = DEFAULT_SLOW,
) -> Optional[RawSignal]:
    """Return a RawSignal if a crossover occurred on bar_date, else None.

    Requires at least slow_period + 1 bars to detect a cross (need the
    bar before the target bar to determine crossing direction).
    """
    if len(bars) < slow_period + 2:
        logger.debug("Not enough bars for MA cross (%d < %d)", len(bars), slow_period + 2)
        return None

    # Find the index of bar_date
    idx = next((i for i, b in enumerate(bars) if b.date == bar_date), None)
    if idx is None or idx == 0:
        return None

    closes = [b.close for b in bars[: idx + 1]]
    fast_ma = _sma(closes, fast_period)
    slow_ma = _sma(closes, slow_period)

    curr_fast = fast_ma[-1]
    curr_slow = slow_ma[-1]
    prev_fast = fast_ma[-2]
    prev_slow = slow_ma[-2]

    if None in (curr_fast, curr_slow, prev_fast, prev_slow):
        return None

    cross_up = prev_fast <= prev_slow and curr_fast > curr_slow
    cross_dn = prev_fast >= prev_slow and curr_fast < curr_slow

    if not (cross_up or cross_dn):
        return None

    direction = "LONG" if cross_up else "SHORT"
    gap_pct = abs(curr_fast - curr_slow) / curr_slow if curr_slow else 0.0
    # confidence: 0.5 baseline + up to 0.5 scaled by gap (capped at 5% gap → full score)
    confidence = min(0.5 + gap_pct / 0.05 * 0.5, 1.0)

    return RawSignal(
        kind="MA_CROSS",
        direction=direction,
        confidence=round(confidence, 3),
        bar_date=bar_date,
        trigger_price=bars[idx].close,
        evidence={
            "fast_period": fast_period,
            "slow_period": slow_period,
            "fast_ma": round(curr_fast, 4),
            "slow_ma": round(curr_slow, 4),
            "gap_pct": round(gap_pct * 100, 3),
        },
    )
