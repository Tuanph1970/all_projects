"""F-042 — Midtrend entry detectors (Schwager Ch 5, 14).

Four strategies for entering an established trend mid-move:

1. PCT_RETRACEMENT        — 33/50/67% pullback in trend direction, then reversal bar.
2. MINOR_REACTION_REVERSAL — N counter-trend bars followed by a trend-aligned bar.
3. CONTINUATION_BREAKOUT  — tight consolidation (flag/pennant) breaks in trend direction.
4. LONG_MA_REACTION        — price touches slow MA and bounces back in trend direction.

These fire only in TREND_UP or TREND_DOWN regimes.
"""
from __future__ import annotations

import logging
from datetime import date
from typing import List, Optional

from app.services.signal.base import OHLCVBar, RawSignal, _sma

logger = logging.getLogger(__name__)

RETRACEMENT_LEVELS = [0.33, 0.50, 0.67]
RETRACEMENT_BAND = 0.03
REACTION_N = 3
CONSOLIDATION_MIN = 5
CONSOLIDATION_MAX = 20
TIGHT_RANGE_PCT = 0.015
LONG_MA_PERIOD = 50
MA_TOUCH_BAND = 0.005


def detect_midtrend_entry(
    bars: List[OHLCVBar],
    bar_date: date,
    regime: str,
    slow_ma_period: int = LONG_MA_PERIOD,
) -> Optional[RawSignal]:
    """Return the best midtrend entry signal for bar_date, or None."""
    idx = next((i for i, b in enumerate(bars) if b.date == bar_date), None)
    if idx is None or idx < slow_ma_period + 2:
        return None

    trend_up = regime == "TREND_UP"

    candidates: List[RawSignal] = []

    for sig in (
        _pct_retracement(bars, idx, bar_date, trend_up),
        _minor_reaction_reversal(bars, idx, bar_date, trend_up),
        _continuation_breakout(bars, idx, bar_date, trend_up),
        _long_ma_reaction(bars, idx, bar_date, trend_up, slow_ma_period),
    ):
        if sig:
            candidates.append(sig)

    if not candidates:
        return None
    return max(candidates, key=lambda s: s.confidence)


# ---------------------------------------------------------------------------
# Individual detectors
# ---------------------------------------------------------------------------

def _pct_retracement(
    bars: List[OHLCVBar],
    idx: int,
    bar_date: date,
    trend_up: bool,
) -> Optional[RawSignal]:
    """33/50/67% pullback of the most recent swing move, with reversal bar."""
    lookback = min(idx, 60)
    sub = bars[idx - lookback: idx + 1]
    if len(sub) < 4:
        return None

    current = sub[-1]

    if trend_up:
        swing_low_idx = min(range(len(sub) - 1), key=lambda i: sub[i].low)
        swing_high_idx = max(
            (i for i in range(swing_low_idx, len(sub) - 1)),
            key=lambda i: sub[i].high,
            default=None,
        )
        if swing_high_idx is None or swing_high_idx <= swing_low_idx:
            return None
        move_low = sub[swing_low_idx].low
        move_high = sub[swing_high_idx].high
        move_size = move_high - move_low
        if move_size <= 0:
            return None
        pullback = (move_high - current.low) / move_size
        for level in RETRACEMENT_LEVELS:
            if abs(pullback - level) <= RETRACEMENT_BAND and current.close > current.open:
                conf = min(0.55 + (0.67 - level) * 0.4, 0.85)
                return RawSignal(
                    kind="PCT_RETRACEMENT",
                    direction="LONG",
                    confidence=round(conf, 3),
                    bar_date=bar_date,
                    trigger_price=current.close,
                    evidence={
                        "retracement_level": level,
                        "actual_pullback": round(pullback, 3),
                        "move_low": round(move_low, 4),
                        "move_high": round(move_high, 4),
                    },
                )

    else:  # trend_down
        swing_high_idx = max(range(len(sub) - 1), key=lambda i: sub[i].high)
        swing_low_idx = min(
            (i for i in range(swing_high_idx, len(sub) - 1)),
            key=lambda i: sub[i].low,
            default=None,
        )
        if swing_low_idx is None or swing_low_idx <= swing_high_idx:
            return None
        move_high = sub[swing_high_idx].high
        move_low = sub[swing_low_idx].low
        move_size = move_high - move_low
        if move_size <= 0:
            return None
        pullback = (current.high - move_low) / move_size
        for level in RETRACEMENT_LEVELS:
            if abs(pullback - level) <= RETRACEMENT_BAND and current.close < current.open:
                conf = min(0.55 + (0.67 - level) * 0.4, 0.85)
                return RawSignal(
                    kind="PCT_RETRACEMENT",
                    direction="SHORT",
                    confidence=round(conf, 3),
                    bar_date=bar_date,
                    trigger_price=current.close,
                    evidence={
                        "retracement_level": level,
                        "actual_pullback": round(pullback, 3),
                        "move_high": round(move_high, 4),
                        "move_low": round(move_low, 4),
                    },
                )
    return None


def _minor_reaction_reversal(
    bars: List[OHLCVBar],
    idx: int,
    bar_date: date,
    trend_up: bool,
) -> Optional[RawSignal]:
    """N counter-trend bars followed by a trend-aligned bar."""
    if idx < REACTION_N + 1:
        return None

    current = bars[idx]
    closes_up = current.close > current.open
    if closes_up != trend_up:
        return None

    counter_bars = bars[idx - REACTION_N: idx]
    for b in counter_bars:
        if (b.close > b.open) == trend_up:
            return None  # not a clean counter-trend reaction

    open_of_first = counter_bars[0].open
    close_of_last = counter_bars[-1].close
    counter_move = abs(close_of_last - open_of_first) / open_of_first if open_of_first else 0
    conf = min(0.55 + counter_move / 0.03 * 0.2, 0.80)

    return RawSignal(
        kind="MINOR_REACTION_REVERSAL",
        direction="LONG" if trend_up else "SHORT",
        confidence=round(conf, 3),
        bar_date=bar_date,
        trigger_price=current.close,
        evidence={
            "reaction_bars": REACTION_N,
            "counter_move_pct": round(counter_move * 100, 2),
        },
    )


def _continuation_breakout(
    bars: List[OHLCVBar],
    idx: int,
    bar_date: date,
    trend_up: bool,
) -> Optional[RawSignal]:
    """Tight consolidation (flag/pennant) breaks in the trend direction."""
    if idx < CONSOLIDATION_MAX + 2:
        return None

    current = bars[idx]

    # Walk backward from idx-1 counting tight-range bars
    consolidation_start = idx - 1
    for i in range(idx - 1, max(0, idx - CONSOLIDATION_MAX - 1), -1):
        b = bars[i]
        range_pct = (b.high - b.low) / b.close if b.close else 1
        if range_pct <= TIGHT_RANGE_PCT:
            consolidation_start = i
        else:
            break

    consolidation_len = (idx - 1) - consolidation_start + 1
    if consolidation_len < CONSOLIDATION_MIN:
        return None

    consol_bars = bars[consolidation_start: idx]
    consol_high = max(b.high for b in consol_bars)
    consol_low = min(b.low for b in consol_bars)

    if trend_up and current.close > consol_high:
        pen = (current.close - consol_high) / consol_high if consol_high else 0
        conf = min(0.60 + pen / 0.01 * 0.15 + consolidation_len * 0.01, 0.88)
        return RawSignal(
            kind="CONTINUATION_BREAKOUT",
            direction="LONG",
            confidence=round(conf, 3),
            bar_date=bar_date,
            trigger_price=current.close,
            evidence={
                "consolidation_bars": consolidation_len,
                "consol_high": round(consol_high, 4),
                "penetration_pct": round(pen * 100, 2),
            },
        )

    if not trend_up and current.close < consol_low:
        pen = (consol_low - current.close) / consol_low if consol_low else 0
        conf = min(0.60 + pen / 0.01 * 0.15 + consolidation_len * 0.01, 0.88)
        return RawSignal(
            kind="CONTINUATION_BREAKOUT",
            direction="SHORT",
            confidence=round(conf, 3),
            bar_date=bar_date,
            trigger_price=current.close,
            evidence={
                "consolidation_bars": consolidation_len,
                "consol_low": round(consol_low, 4),
                "penetration_pct": round(pen * 100, 2),
            },
        )

    return None


def _long_ma_reaction(
    bars: List[OHLCVBar],
    idx: int,
    bar_date: date,
    trend_up: bool,
    slow_ma_period: int = LONG_MA_PERIOD,
) -> Optional[RawSignal]:
    """Price touched slow MA in last 3 bars and today bounces in trend direction."""
    if idx < slow_ma_period + 1:
        return None

    closes = [b.close for b in bars[: idx + 1]]
    slow_ma_list = _sma(closes, slow_ma_period)
    current_ma = slow_ma_list[-1]
    if current_ma is None:
        return None

    touch_found = False
    for i in range(max(0, idx - 3), idx):
        bar_ma = slow_ma_list[i]
        if bar_ma is None:
            continue
        b = bars[i]
        proximity = (
            abs(b.low - bar_ma) / bar_ma if trend_up else abs(b.high - bar_ma) / bar_ma
        )
        if proximity <= MA_TOUCH_BAND:
            touch_found = True
            break

    if not touch_found:
        return None

    current = bars[idx]
    if trend_up and current.close > current_ma and current.close > current.open:
        gap_pct = (current.close - current_ma) / current_ma
        conf = min(0.50 + gap_pct / 0.01 * 0.1, 0.75)
        return RawSignal(
            kind="LONG_MA_REACTION",
            direction="LONG",
            confidence=round(conf, 3),
            bar_date=bar_date,
            trigger_price=current.close,
            evidence={
                "ma_period": slow_ma_period,
                "slow_ma": round(current_ma, 4),
                "gap_pct": round(gap_pct * 100, 2),
            },
        )

    if not trend_up and current.close < current_ma and current.close < current.open:
        gap_pct = (current_ma - current.close) / current_ma
        conf = min(0.50 + gap_pct / 0.01 * 0.1, 0.75)
        return RawSignal(
            kind="LONG_MA_REACTION",
            direction="SHORT",
            confidence=round(conf, 3),
            bar_date=bar_date,
            trigger_price=current.close,
            evidence={
                "ma_period": slow_ma_period,
                "slow_ma": round(current_ma, 4),
                "gap_pct": round(gap_pct * 100, 2),
            },
        )

    return None
