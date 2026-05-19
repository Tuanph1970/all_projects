"""F-040 — Failed-signal detectors (Schwager Ch 11).

Twelve pure-function detectors covering all major categories of failed patterns.
No I/O; all inputs are plain Python data structures.

Public API:
  detect_failed_signals(bars, bar_date, sr_data, patterns) -> List[FailedSignalResult]
  highest_severity(results) -> Optional[FailedSignalResult]
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Dict, List, Optional, Any

from app.services.signal.base import OHLCVBar, _sma

TRAP_LOOKBACK = 5
GAP_THRESHOLD_PCT = 0.005
SPIKE_RANGE_MULTIPLE = 2.5
WRD_RANGE_MULTIPLE = 2.0
TL_MA_PERIOD = 50
OVERRIDE_THRESHOLD = 0.5


@dataclass
class FailedSignalResult:
    kind: str
    direction: str          # LONG | SHORT — trading implication of the failure
    severity: float         # 0..1
    evidence: Dict[str, Any] = field(default_factory=dict)


def detect_failed_signals(
    bars: List[OHLCVBar],
    bar_date: date,
    sr_data: Optional[Dict[str, Any]] = None,
    patterns: Optional[Dict[str, Any]] = None,
) -> List[FailedSignalResult]:
    """Run all 12 detectors; return results sorted by severity descending."""
    idx = next((i for i, b in enumerate(bars) if b.date == bar_date), None)
    if idx is None or idx < 2:
        return []

    results: List[FailedSignalResult] = []

    for r in (
        _bull_trap(bars, idx, sr_data),
        _bear_trap(bars, idx, sr_data),
        _false_tl_break(bars, idx, sr_data),
        _filled_gap(bars, idx, sr_data),
        _return_to_spike(bars, idx, sr_data),
        _wrd_return(bars, idx, sr_data),
        _opposite_breakout(bars, idx, sr_data),
    ):
        if r:
            results.append(r)

    if patterns:
        for fn2 in (
            _counter_anticipated_flag,
            _hs_target_failure,
            _double_top_break,
            _rounding_break,
            _future_reliability,
        ):
            r = fn2(bars, idx, patterns)
            if r:
                results.append(r)

    results.sort(key=lambda x: x.severity, reverse=True)
    return results


def highest_severity(results: List[FailedSignalResult]) -> Optional[FailedSignalResult]:
    return max(results, key=lambda x: x.severity) if results else None


# ---------------------------------------------------------------------------
# Price-based detectors
# ---------------------------------------------------------------------------

def _bull_trap(
    bars: List[OHLCVBar],
    idx: int,
    sr_data: Optional[Dict[str, Any]],
) -> Optional[FailedSignalResult]:
    """Upside breakout above resistance closes back below it → SHORT implication."""
    if not sr_data:
        return None
    resistances = sr_data.get("resistances", [])
    if not resistances:
        return None

    today = bars[idx]
    lookback_start = max(0, idx - TRAP_LOOKBACK)
    prev_bars = bars[lookback_start:idx]

    for lvl in resistances:
        level_price = float(lvl["price"])
        strength = int(lvl.get("strength", 1))
        break_bar = next((b for b in prev_bars if b.close > level_price), None)
        if break_bar is None:
            continue
        if today.close < level_price:
            drop_pct = (level_price - today.close) / level_price
            severity = min(0.45 + strength * 0.05 + drop_pct / 0.02 * 0.2, 0.95)
            return FailedSignalResult(
                kind="BULL_TRAP",
                direction="SHORT",
                severity=round(severity, 3),
                evidence={
                    "level_price": round(level_price, 4),
                    "strength": strength,
                    "break_bar_date": str(break_bar.date),
                    "drop_pct": round(drop_pct * 100, 2),
                },
            )
    return None


def _bear_trap(
    bars: List[OHLCVBar],
    idx: int,
    sr_data: Optional[Dict[str, Any]],
) -> Optional[FailedSignalResult]:
    """Downside breakdown below support closes back above it → LONG implication."""
    if not sr_data:
        return None
    supports = sr_data.get("supports", [])
    if not supports:
        return None

    today = bars[idx]
    lookback_start = max(0, idx - TRAP_LOOKBACK)
    prev_bars = bars[lookback_start:idx]

    for lvl in supports:
        level_price = float(lvl["price"])
        strength = int(lvl.get("strength", 1))
        break_bar = next((b for b in prev_bars if b.close < level_price), None)
        if break_bar is None:
            continue
        if today.close > level_price:
            recovery_pct = (today.close - level_price) / level_price
            severity = min(0.45 + strength * 0.05 + recovery_pct / 0.02 * 0.2, 0.95)
            return FailedSignalResult(
                kind="BEAR_TRAP",
                direction="LONG",
                severity=round(severity, 3),
                evidence={
                    "level_price": round(level_price, 4),
                    "strength": strength,
                    "break_bar_date": str(break_bar.date),
                    "recovery_pct": round(recovery_pct * 100, 2),
                },
            )
    return None


def _false_tl_break(
    bars: List[OHLCVBar],
    idx: int,
    sr_data: Optional[Dict[str, Any]] = None,
) -> Optional[FailedSignalResult]:
    """Prev bar closed on one side of slow MA; today reverses back through it."""
    if idx < TL_MA_PERIOD + 1:
        return None

    closes = [b.close for b in bars[: idx + 1]]
    slow_ma_list = _sma(closes, TL_MA_PERIOD)
    prev_ma = slow_ma_list[-2]
    curr_ma = slow_ma_list[-1]
    if prev_ma is None or curr_ma is None:
        return None

    prev_close = bars[idx - 1].close
    curr_close = bars[idx].close

    if prev_close > prev_ma and curr_close < curr_ma:
        drop_pct = (prev_close - curr_close) / prev_close if prev_close else 0
        severity = min(0.40 + drop_pct / 0.02 * 0.3, 0.85)
        return FailedSignalResult(
            kind="FALSE_TL_BREAK",
            direction="SHORT",
            severity=round(severity, 3),
            evidence={
                "ma_period": TL_MA_PERIOD,
                "prev_close": round(prev_close, 4),
                "curr_close": round(curr_close, 4),
                "slow_ma": round(curr_ma, 4),
                "drop_pct": round(drop_pct * 100, 2),
            },
        )

    if prev_close < prev_ma and curr_close > curr_ma:
        rise_pct = (curr_close - prev_close) / prev_close if prev_close else 0
        severity = min(0.40 + rise_pct / 0.02 * 0.3, 0.85)
        return FailedSignalResult(
            kind="FALSE_TL_BREAK",
            direction="LONG",
            severity=round(severity, 3),
            evidence={
                "ma_period": TL_MA_PERIOD,
                "prev_close": round(prev_close, 4),
                "curr_close": round(curr_close, 4),
                "slow_ma": round(curr_ma, 4),
                "rise_pct": round(rise_pct * 100, 2),
            },
        )
    return None


def _filled_gap(
    bars: List[OHLCVBar],
    idx: int,
    sr_data: Optional[Dict[str, Any]] = None,
) -> Optional[FailedSignalResult]:
    """A recent directional gap is fully filled today."""
    today = bars[idx]
    lookback_start = max(1, idx - TRAP_LOOKBACK)

    for i in range(lookback_start, idx):
        bar_now = bars[i]
        bar_prev = bars[i - 1]
        gap = bar_now.open - bar_prev.close
        gap_pct = abs(gap) / bar_prev.close if bar_prev.close else 0
        if gap_pct < GAP_THRESHOLD_PCT:
            continue

        if gap > 0 and today.low <= bar_prev.close:
            severity = min(0.40 + gap_pct / 0.01 * 0.15, 0.80)
            return FailedSignalResult(
                kind="FILLED_GAP",
                direction="SHORT",
                severity=round(severity, 3),
                evidence={
                    "gap_date": str(bar_now.date),
                    "gap_pct": round(gap_pct * 100, 2),
                    "gap_direction": "UP",
                },
            )

        if gap < 0 and today.high >= bar_prev.close:
            severity = min(0.40 + gap_pct / 0.01 * 0.15, 0.80)
            return FailedSignalResult(
                kind="FILLED_GAP",
                direction="LONG",
                severity=round(severity, 3),
                evidence={
                    "gap_date": str(bar_now.date),
                    "gap_pct": round(gap_pct * 100, 2),
                    "gap_direction": "DOWN",
                },
            )
    return None


def _return_to_spike(
    bars: List[OHLCVBar],
    idx: int,
    sr_data: Optional[Dict[str, Any]] = None,
) -> Optional[FailedSignalResult]:
    """Price returns to the extreme of a prior spike bar."""
    if idx < 10:
        return None
    today = bars[idx]
    recent = bars[max(0, idx - 20): idx]
    if not recent:
        return None

    avg_range = sum(b.high - b.low for b in recent) / len(recent)
    if avg_range == 0:
        return None

    for i in range(idx - 1, max(0, idx - 15) - 1, -1):
        b = bars[i]
        bar_range = b.high - b.low
        if bar_range < SPIKE_RANGE_MULTIPLE * avg_range:
            continue

        body_mid = (b.open + b.close) / 2

        if (body_mid - b.low) > bar_range * 0.4:  # downside spike wick
            if today.close <= b.low * 1.005:
                severity = min(0.50 + (bar_range / avg_range - SPIKE_RANGE_MULTIPLE) * 0.05, 0.90)
                return FailedSignalResult(
                    kind="RETURN_TO_SPIKE",
                    direction="SHORT",
                    severity=round(severity, 3),
                    evidence={
                        "spike_date": str(b.date),
                        "spike_extreme": round(b.low, 4),
                        "spike_range_ratio": round(bar_range / avg_range, 2),
                    },
                )

        if (b.high - body_mid) > bar_range * 0.4:  # upside spike wick
            if today.close >= b.high * 0.995:
                severity = min(0.50 + (bar_range / avg_range - SPIKE_RANGE_MULTIPLE) * 0.05, 0.90)
                return FailedSignalResult(
                    kind="RETURN_TO_SPIKE",
                    direction="LONG",
                    severity=round(severity, 3),
                    evidence={
                        "spike_date": str(b.date),
                        "spike_extreme": round(b.high, 4),
                        "spike_range_ratio": round(bar_range / avg_range, 2),
                    },
                )
    return None


def _wrd_return(
    bars: List[OHLCVBar],
    idx: int,
    sr_data: Optional[Dict[str, Any]] = None,
) -> Optional[FailedSignalResult]:
    """Price fully retraces a wide-ranging day."""
    if idx < 5:
        return None
    today = bars[idx]
    recent = bars[max(0, idx - 20): idx]
    avg_range = sum(b.high - b.low for b in recent) / len(recent) if recent else 0
    if avg_range == 0:
        return None

    for i in range(max(1, idx - TRAP_LOOKBACK), idx):
        b = bars[i]
        bar_range = b.high - b.low
        if bar_range < WRD_RANGE_MULTIPLE * avg_range:
            continue

        if b.close > b.open and today.close < b.open:
            severity = min(0.45 + (bar_range / avg_range - WRD_RANGE_MULTIPLE) * 0.05, 0.85)
            return FailedSignalResult(
                kind="WRD_RETURN",
                direction="SHORT",
                severity=round(severity, 3),
                evidence={
                    "wrd_date": str(b.date),
                    "wrd_open": round(b.open, 4),
                    "wrd_close": round(b.close, 4),
                },
            )

        if b.close < b.open and today.close > b.open:
            severity = min(0.45 + (bar_range / avg_range - WRD_RANGE_MULTIPLE) * 0.05, 0.85)
            return FailedSignalResult(
                kind="WRD_RETURN",
                direction="LONG",
                severity=round(severity, 3),
                evidence={
                    "wrd_date": str(b.date),
                    "wrd_open": round(b.open, 4),
                    "wrd_close": round(b.close, 4),
                },
            )
    return None


def _opposite_breakout(
    bars: List[OHLCVBar],
    idx: int,
    sr_data: Optional[Dict[str, Any]],
) -> Optional[FailedSignalResult]:
    """In an uptrend, price breaks below support (unexpected direction) and vice versa."""
    if not sr_data or idx < 20:
        return None

    today = bars[idx]
    start_bar = bars[max(0, idx - 20)]
    trend_up = bars[idx - 1].close > start_bar.close

    if trend_up:
        for lvl in sr_data.get("supports", []):
            level_price = float(lvl["price"])
            strength = int(lvl.get("strength", 1))
            if today.close < level_price * 0.995:
                return FailedSignalResult(
                    kind="OPPOSITE_BREAKOUT",
                    direction="SHORT",
                    severity=round(min(0.50 + strength * 0.05, 0.85), 3),
                    evidence={
                        "level_price": round(level_price, 4),
                        "strength": strength,
                        "trend": "UP",
                        "breakout_direction": "DOWN",
                    },
                )
    else:
        for lvl in sr_data.get("resistances", []):
            level_price = float(lvl["price"])
            strength = int(lvl.get("strength", 1))
            if today.close > level_price * 1.005:
                return FailedSignalResult(
                    kind="OPPOSITE_BREAKOUT",
                    direction="LONG",
                    severity=round(min(0.50 + strength * 0.05, 0.85), 3),
                    evidence={
                        "level_price": round(level_price, 4),
                        "strength": strength,
                        "trend": "DOWN",
                        "breakout_direction": "UP",
                    },
                )
    return None


# ---------------------------------------------------------------------------
# Pattern-based detectors (require ai-insights patterns payload)
# ---------------------------------------------------------------------------

def _counter_anticipated_flag(
    bars: List[OHLCVBar],
    idx: int,
    patterns: Dict[str, Any],
) -> Optional[FailedSignalResult]:
    """Flag breaks opposite to the expected continuation direction."""
    for p in patterns.get("patterns", []):
        if p.get("pattern_type") not in ("FLAG_BULL", "FLAG_BEAR"):
            continue
        if p.get("status") != "ACTIVE":
            continue
        expected_dir = "LONG" if p["pattern_type"] == "FLAG_BULL" else "SHORT"
        actual_break = p.get("break_direction")
        if actual_break is None:
            continue
        broke_wrong = (
            (expected_dir == "LONG" and actual_break == "DOWN") or
            (expected_dir == "SHORT" and actual_break == "UP")
        )
        if broke_wrong:
            return FailedSignalResult(
                kind="COUNTER_ANTICIPATED_FLAG",
                direction="SHORT" if expected_dir == "LONG" else "LONG",
                severity=0.65,
                evidence={
                    "pattern_type": p["pattern_type"],
                    "expected_direction": expected_dir,
                    "actual_break": actual_break,
                },
            )
    return None


def _hs_target_failure(
    bars: List[OHLCVBar],
    idx: int,
    patterns: Dict[str, Any],
) -> Optional[FailedSignalResult]:
    """H&S measured-move target not reached before price reverses."""
    today = bars[idx]
    for p in patterns.get("patterns", []):
        if p.get("pattern_type") not in ("HEAD_AND_SHOULDERS", "INV_HEAD_AND_SHOULDERS"):
            continue
        if p.get("status") != "ACTIVE":
            continue
        target = p.get("measured_move_target")
        if target is None:
            continue
        neckline = p.get("neckline", today.close)
        is_hs = p["pattern_type"] == "HEAD_AND_SHOULDERS"
        if is_hs and today.close > float(neckline):
            return FailedSignalResult(
                kind="HS_TARGET_FAILURE",
                direction="LONG",
                severity=0.60,
                evidence={
                    "pattern_type": p["pattern_type"],
                    "measured_target": round(float(target), 4),
                },
            )
        if not is_hs and today.close < float(neckline):
            return FailedSignalResult(
                kind="HS_TARGET_FAILURE",
                direction="SHORT",
                severity=0.60,
                evidence={
                    "pattern_type": p["pattern_type"],
                    "measured_target": round(float(target), 4),
                },
            )
    return None


def _double_top_break(
    bars: List[OHLCVBar],
    idx: int,
    patterns: Dict[str, Any],
) -> Optional[FailedSignalResult]:
    """Double top/bottom confirmation level fails to hold."""
    today = bars[idx]
    for p in patterns.get("patterns", []):
        if p.get("pattern_type") not in ("DOUBLE_TOP", "DOUBLE_BOTTOM"):
            continue
        if p.get("status") != "ACTIVE":
            continue
        confirmation = p.get("confirmation_level")
        if confirmation is None:
            continue
        conf_price = float(confirmation)
        is_top = p["pattern_type"] == "DOUBLE_TOP"
        if is_top and today.close > conf_price:
            return FailedSignalResult(
                kind="DOUBLE_TOP_BREAK",
                direction="LONG",
                severity=0.60,
                evidence={
                    "pattern_type": p["pattern_type"],
                    "confirmation_level": round(conf_price, 4),
                },
            )
        if not is_top and today.close < conf_price:
            return FailedSignalResult(
                kind="DOUBLE_TOP_BREAK",
                direction="SHORT",
                severity=0.60,
                evidence={
                    "pattern_type": p["pattern_type"],
                    "confirmation_level": round(conf_price, 4),
                },
            )
    return None


def _rounding_break(
    bars: List[OHLCVBar],
    idx: int,
    patterns: Dict[str, Any],
) -> Optional[FailedSignalResult]:
    """Rounding turn fails to follow through after breakout."""
    today = bars[idx]
    for p in patterns.get("patterns", []):
        if p.get("pattern_type") not in ("ROUNDING_BOTTOM", "ROUNDING_TOP"):
            continue
        if p.get("status") != "ACTIVE":
            continue
        breakout_level = p.get("breakout_level")
        if breakout_level is None:
            continue
        bl = float(breakout_level)
        is_bottom = p["pattern_type"] == "ROUNDING_BOTTOM"
        if is_bottom and today.close < bl:
            return FailedSignalResult(
                kind="ROUNDING_BREAK",
                direction="SHORT",
                severity=0.55,
                evidence={"pattern_type": p["pattern_type"], "breakout_level": round(bl, 4)},
            )
        if not is_bottom and today.close > bl:
            return FailedSignalResult(
                kind="ROUNDING_BREAK",
                direction="LONG",
                severity=0.55,
                evidence={"pattern_type": p["pattern_type"], "breakout_level": round(bl, 4)},
            )
    return None


def _future_reliability(
    bars: List[OHLCVBar],
    idx: int,
    patterns: Dict[str, Any],
) -> Optional[FailedSignalResult]:
    """Meta-tag: active pattern with below-threshold historical reliability."""
    threshold = 0.45
    for p in patterns.get("patterns", []):
        if p.get("status") != "ACTIVE":
            continue
        reliability = float(p.get("reliability_score", 1.0))
        if reliability < threshold:
            direction = p.get("implied_direction", "LONG")
            severity = round(0.55 * (1.0 - reliability / threshold), 3)
            return FailedSignalResult(
                kind="FUTURE_RELIABILITY",
                direction="SHORT" if direction == "LONG" else "LONG",
                severity=severity,
                evidence={
                    "pattern_type": p.get("pattern_type"),
                    "reliability_score": reliability,
                },
            )
    return None
