"""F-014 — N-day high/low breakout detector (Schwager Ch 14).

LONG signal: today's close > highest close of the previous N bars.
SHORT signal: today's close < lowest close of the previous N bars.

The lookback window is *exclusive* of bar_date, so an N=20 breakout
fires when close exceeds the highest close of the 20 bars before it.

Confidence scales with how far the close penetrated the breakout level.

AN EXTERNAL REFERENCE LEVEL MAY RAISE THE BAR, NEVER LOWER IT (Backlog #140).
The momentum scanner draws a pivot at the top of a detected base — a level
chosen with base geometry and volume behind it, where this detector's N-bar high
is just the window maximum. Handing that pivot in lets the two surfaces agree
about what "the breakout" is, instead of the Scanner tab naming one price while
the decision engine judges another.

The coupling is deliberately one-directional. A reference BELOW the N-bar high
is ignored, because honouring it would fire a breakout the engine's own rule
would not — the scanner would be loosening the engine's standard, which EC-S6
forbids it from doing. The scanner proposes; it may make the trigger stricter,
and it may not make it easier.
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
    reference_level: Optional[float] = None,
    reference_source: str = "",
) -> Optional[RawSignal]:
    """Return a RawSignal if bar_date closed outside the N-bar range, else None.

    `reference_level` is an externally supplied LONG breakout level (the
    scanner's base pivot). It replaces the N-bar high only when it is at or
    above it — see the module docstring for why the coupling only goes one way.
    It does not affect the SHORT side: the scanner is a long-side funnel and has
    no view on breakdowns.
    """
    idx = next((i for i, b in enumerate(bars) if b.date == bar_date), None)
    if idx is None or idx < n:
        return None

    lookback = bars[idx - n : idx]   # n bars before today, exclusive
    today = bars[idx]

    highest = max(b.close for b in lookback)
    lowest = min(b.close for b in lookback)

    n_day_high = highest
    level_source = "n_day_high"
    if reference_level is not None and reference_level >= highest:
        highest = float(reference_level)
        level_source = reference_source or "external_reference"

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
            # Which level was used and what the engine's own rule would have
            # used. Both are reported so a user comparing the Scanner tab with
            # a recommendation can see WHY the two agree or differ, rather than
            # discovering a silent substitution (#140).
            "level_source": level_source if direction == "LONG" else "n_day_low",
            "n_day_level": round(n_day_high if direction == "LONG" else lowest, 4),
            "reference_level": (round(float(reference_level), 4)
                                if reference_level is not None else None),
        },
    )
