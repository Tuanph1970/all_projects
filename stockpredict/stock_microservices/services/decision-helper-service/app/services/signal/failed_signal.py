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

#: Severity for the two reachable pattern-failure detectors, deliberately
#: BELOW `OVERRIDE_THRESHOLD` so neither can override a confirmed signal's
#: direction (Backlog #79).
#:
#: They used to sit at 0.60/0.65 and therefore drove REVERSE recommendations.
#: An outcome study over 6,797 CAUSAL scans — each seeing only bars up to its
#: own date — measured forward returns against the no-verdict baseline on the
#: same bars, with non-overlapping windows:
#:
#:   DOUBLE_TOP_BREAK   / SHORT  t = -0.81   (10 bars)  -> indistinguishable
#:   DOUBLE_TOP_BREAK   / LONG   t = +0.65              -> indistinguishable
#:   HS_TARGET_FAILURE  / LONG   t = -1.08              -> indistinguishable
#:   HS_TARGET_FAILURE  / SHORT  t = +2.34              -> BACKWARDS
#:
#: The last one is the reason this is a change and not a note: it implies SHORT
#: and the stock then OUTPERFORMS the baseline by 1.4% over ten bars, across 30
#: symbols. Nothing here beats the benchmark, and one is significantly wrong,
#: so by the same C4 rule EM-1 holds its own rules to, neither gets decision
#: authority. They remain in `failed_results` as evidence.
#:
#: Evidence: docs/dh79_failed_signal_outcome_study.md.
PATTERN_FAILURE_SEVERITY = 0.35


@dataclass
class FailedSignalResult:
    kind: str
    direction: str          # LONG | SHORT — trading implication of the failure
    severity: float         # 0..1
    evidence: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# ai-insights -> detector vocabulary (Backlog #73)
# ---------------------------------------------------------------------------

#: `pattern_name` as ai-insights reports it -> the SCREAMING_SNAKE
#: `pattern_type` the pattern detectors below match on. Direction-dependent
#: names (the flag) resolve through `_FLAG_BY_DIRECTION`.
_PATTERN_NAME_TO_TYPE = {
    "head and shoulders": "HEAD_AND_SHOULDERS",
    "inverse head and shoulders": "INV_HEAD_AND_SHOULDERS",
    "double top": "DOUBLE_TOP",
    "double bottom": "DOUBLE_BOTTOM",
}

_FLAG_BY_DIRECTION = {"bullish": "FLAG_BULL", "bearish": "FLAG_BEAR"}

#: How recently a formation must have completed for its failure to be worth
#: reporting (Backlog #78). ai-insights returns every pattern it finds across
#: the lookback window, so without this the detectors judged formations a
#: median of 86 bars old for the head-and-shoulders — roughly four months.
#: "An H&S from last April has failed" is history, not a signal about today,
#: and it is why the detectors fired on 100% of symbols.
#:
#: SWEPT over 20 real symbols (docs/dh78_failed_signal_calibration.md). Any of
#: the detectors firing, by age limit:
#:     3 -> 5%   5 -> 25%   10 -> 30%   15 -> 65%   20 -> 70%   60+ -> 100%
#: 10 bars is two trading weeks — recent enough to be about a live situation —
#: and sits at the knee: 10 -> 15 more than doubles the rate (30% -> 65%) as
#: stale formations flood back in.
MAX_PATTERN_AGE_BARS = 10

#: Exactly the keys the five pattern detectors read. The adapter emits NOTHING
#: else, and that is deliberate: `confidence` is excluded so decision-helper
#: still cannot see EM-1's composite confidence. S1
#: (docs/em1_s1_downstream_comparison.md) concluded the volume layer does not
#: reach this service; a whitelist keeps that STRUCTURALLY true rather than
#: true by accident, so wiring these detectors up does not quietly invalidate
#: that finding.
_ADAPTED_KEYS = (
    "pattern_type", "status", "break_direction",
    "measured_move_target", "neckline",
    "confirmation_level", "breakout_level",
)


def adapt_ai_insights_patterns(
    payload: Optional[Dict[str, Any]],
    last_close: Optional[float] = None,
    bar_index: Optional[int] = None,
    max_age_bars: int = MAX_PATTERN_AGE_BARS,
) -> Optional[Dict[str, Any]]:
    """Translate an ai-insights pattern payload into the detector vocabulary.

    The five pattern detectors in this module had never fired once. They match
    `pattern_type` against names like ``FLAG_BULL`` and ``DOUBLE_TOP`` and
    require ``status == "ACTIVE"``, but ai-insights sends ``pattern_type`` as
    ``"bullish"``/``"bearish"``/``"neutral"`` with the shape in
    ``pattern_name``, and sends no ``status`` field at all — so all three
    guards failed independently (Backlog #73).

    The translation is faithful rather than generous:

    * ``status`` becomes ``"ACTIVE"`` because ai-insights only returns patterns
      it found inside the lookback window; that is what active means here.
    * ``confirmation_level`` and ``breakout_level`` both come from
      ``neckline``, which is the level each detector is actually comparing
      price against.
    * ``break_direction`` is set ONLY when EM-1's ``volume_evidence`` has
      actually located a penetration. It is deliberately NOT inferred from the
      last close against the neckline: for a bull flag whose price sits below
      its breakout level that would read as "broke downward" when the truth is
      "has not broken at all", and `_counter_anticipated_flag` would then call
      every unresolved flag a failure. (That inference was in the first
      version of this adapter and is the bug Backlog #78 removed.)

    * Formations older than ``max_age_bars`` are dropped. Without it the
      detectors judged patterns a median of 86 bars old and fired on every
      symbol; see the module constant.

    Patterns with no counterpart are dropped rather than coerced. Nothing maps
    onto ``ROUNDING_TOP``/``ROUNDING_BOTTOM`` because ai-insights has no
    rounding detector, and nothing supplies ``reliability_score`` — so
    `_rounding_break` and `_future_reliability` remain unreachable by
    construction, which is asserted in the tests instead of left implicit.

    `_counter_anticipated_flag` is a THIRD unreachable one, and the reason is
    worth stating because the first version of this adapter appeared to revive
    it. `FlagDetector` reports flags that are still forming: across 14 real
    flags the last key bar was the final bar of the scan every single time
    (age 0/14). So within one scan the flag has not broken yet, and a
    counter-break is unobservable no matter what the age limit is. The earlier
    firings came from inferring `break_direction` from price-against-neckline,
    which labelled every unresolved bull flag a downward break — a false
    positive, now removed. Detecting a real counter-break needs the flag's
    lower boundary or a later bar, neither of which this payload carries.
    """
    if not payload:
        return None

    adapted = []
    for raw in payload.get("patterns", []):
        if not raw.get("found", True):
            continue

        # Recency, measured INSIDE ai-insights' own frame.
        #
        # `key_bars` are positions in the frame ai-insights scanned, which is
        # `lookback_bars` long and ends at the bar being judged. Using
        # decision-helper's own `idx` would be wrong whenever the two services
        # hold different amounts of history — with 500 local bars against a
        # 250-bar scan every pattern would look 250 bars old and be dropped.
        key_bars = raw.get("key_bars") or []
        last_index = payload.get("lookback_bars")
        if last_index is None:
            last_index = bar_index if bar_index is not None else None
        else:
            last_index = int(last_index) - 1
        if last_index is not None and key_bars:
            if last_index - int(key_bars[-1]) > max_age_bars:
                continue
        name = str(raw.get("pattern_name") or "").strip().lower()
        direction = str(raw.get("pattern_type") or "").strip().lower()

        kind = _PATTERN_NAME_TO_TYPE.get(name)
        if kind is None and name == "flag":
            kind = _FLAG_BY_DIRECTION.get(direction)
        if kind is None:
            continue

        neckline = raw.get("neckline")
        out: Dict[str, Any] = {
            "pattern_type": kind,
            "status": "ACTIVE",
            "measured_move_target": raw.get("measured_move_target"),
            "neckline": neckline,
            "confirmation_level": neckline,
            "breakout_level": neckline,
        }

        # Only a LOCATED penetration counts as a break. See the docstring:
        # inferring it from price-vs-neckline turns "has not broken out yet"
        # into "broke the wrong way".
        evidence = raw.get("volume_evidence") or {}
        component = (evidence.get("components") or {}).get("breakout volume") or {}
        if component.get("breakout_bar") is not None and evidence.get("direction"):
            out["break_direction"] = "UP" if evidence["direction"] == "bullish" else "DOWN"

        adapted.append({k: v for k, v in out.items() if k in _ADAPTED_KEYS})

    return {"patterns": adapted} if adapted else None


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

    # Backlog #73: the payload arrives in ai-insights' vocabulary and has to
    # be translated before these five can match on anything.
    adapted = adapt_ai_insights_patterns(
        patterns, last_close=bars[idx].close, bar_index=idx,
    )
    if adapted:
        for fn2 in (
            _counter_anticipated_flag,
            _hs_target_failure,
            _double_top_break,
            _rounding_break,
            _future_reliability,
        ):
            r = fn2(bars, idx, adapted)
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
                severity=PATTERN_FAILURE_SEVERITY,
                evidence={
                    "pattern_type": p["pattern_type"],
                    "measured_target": round(float(target), 4),
                },
            )
        if not is_hs and today.close < float(neckline):
            return FailedSignalResult(
                kind="HS_TARGET_FAILURE",
                direction="SHORT",
                severity=PATTERN_FAILURE_SEVERITY,
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
                severity=PATTERN_FAILURE_SEVERITY,
                evidence={
                    "pattern_type": p["pattern_type"],
                    "confirmation_level": round(conf_price, 4),
                },
            )
        if not is_top and today.close < conf_price:
            return FailedSignalResult(
                kind="DOUBLE_TOP_BREAK",
                direction="SHORT",
                severity=PATTERN_FAILURE_SEVERITY,
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
