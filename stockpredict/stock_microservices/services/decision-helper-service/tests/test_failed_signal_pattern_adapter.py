"""Backlog #73 — the pattern-based failed-signal detectors had never fired.

Five detectors in `failed_signal.py` match `pattern_type` against names like
``FLAG_BULL`` and ``DOUBLE_TOP`` and require ``status == "ACTIVE"``. ai-insights
sends ``pattern_type`` as ``"bullish"``/``"bearish"``/``"neutral"``, puts the
shape in ``pattern_name``, and sends no ``status`` field at all — so all three
guards failed independently and none of the five had ever produced a result.

`adapt_ai_insights_patterns` translates the payload. These tests use realistic
ai-insights payloads — the field names and values are the shapes
`/insights/patterns/{symbol}` actually returns, including EM-1's
`volume_evidence` — and check both what now works and what still cannot.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import List

import pytest

from app.services.signal.base import OHLCVBar
from app.services.signal.failed_signal import (
    adapt_ai_insights_patterns,
    detect_failed_signals,
)


def _bars(closes: List[float]) -> List[OHLCVBar]:
    start = date(2026, 1, 1)
    return [
        OHLCVBar(
            date=start + timedelta(days=i),
            open=c, high=c + 0.5, low=c - 0.5, close=c, volume=10_000,
        )
        for i, c in enumerate(closes)
    ]


def _ai_pattern(**over):
    """A pattern in the shape ai-insights really sends."""
    base = {
        "pattern_name": "Head and Shoulders",
        "pattern_type": "bearish",
        "found": True,
        "confidence": 0.707,
        "geometric_confidence": 0.798,
        "volume_score": 0.31,
        "volume_factor": 0.886,
        "key_bars": [10, 18, 26, 34, 42],
        "measured_move_target": 80.5,
        "neckline": 99.5,
        "details": {},
        "volume_evidence": {
            "status": "known", "verdict": "contradicts", "direction": "bearish",
            "components": {"breakout volume": {"verdict": "confirms", "value": 2.1,
                                               "breakout_bar": 44}},
            "baseline_window": 100,
        },
    }
    base.update(over)
    return {"patterns": [base]}


# ---------------------------------------------------------------------------
# The translation itself
# ---------------------------------------------------------------------------

class TestAdapter:
    def test_pattern_name_becomes_the_detector_vocabulary(self):
        out = adapt_ai_insights_patterns(_ai_pattern())
        assert out["patterns"][0]["pattern_type"] == "HEAD_AND_SHOULDERS"
        assert out["patterns"][0]["status"] == "ACTIVE"

    @pytest.mark.parametrize("name,direction,expected", [
        ("Head and Shoulders", "bearish", "HEAD_AND_SHOULDERS"),
        ("Inverse Head and Shoulders", "bullish", "INV_HEAD_AND_SHOULDERS"),
        ("Double Top", "bearish", "DOUBLE_TOP"),
        ("Double Bottom", "bullish", "DOUBLE_BOTTOM"),
        ("Flag", "bullish", "FLAG_BULL"),
        ("Flag", "bearish", "FLAG_BEAR"),
    ])
    def test_every_mappable_shape(self, name, direction, expected):
        out = adapt_ai_insights_patterns(
            _ai_pattern(pattern_name=name, pattern_type=direction)
        )
        assert out["patterns"][0]["pattern_type"] == expected

    def test_the_neckline_feeds_both_level_fields(self):
        """Different detectors read the same level under different names."""
        out = adapt_ai_insights_patterns(_ai_pattern())["patterns"][0]
        assert out["confirmation_level"] == 99.5
        assert out["breakout_level"] == 99.5

    def test_break_direction_comes_from_em1_evidence_when_present(self):
        out = adapt_ai_insights_patterns(_ai_pattern())["patterns"][0]
        assert out["break_direction"] == "DOWN"   # bearish penetration

    def test_break_direction_is_never_inferred_from_price(self):
        """Backlog #78 — the bug this replaced.

        The first version inferred the direction from the last close against
        the neckline. That turns "has not broken out yet" into "broke the
        wrong way": a bull flag trading below its upside breakout level would
        read as a downward break, and `_counter_anticipated_flag` then called
        every unresolved flag a failure. Only a LOCATED penetration counts.
        """
        payload = _ai_pattern(volume_evidence={"status": "unknown", "reason": "no_breakout_yet"})
        for close in (105.0, 95.0):
            out = adapt_ai_insights_patterns(payload, last_close=close)["patterns"][0]
            assert "break_direction" not in out

    def test_break_direction_is_absent_rather_than_guessed(self):
        payload = _ai_pattern(volume_evidence={}, neckline=None)
        out = adapt_ai_insights_patterns(payload, last_close=None)["patterns"][0]
        assert "break_direction" not in out

    def test_stale_formations_are_dropped(self):
        """Backlog #78's main lever.

        ai-insights returns every pattern in the lookback window, so without
        this the detectors judged formations a median of 86 bars old for the
        head-and-shoulders (max 201) and fired on 100% of symbols. Age is
        measured inside the scan's own frame, from `lookback_bars`.
        """
        recent = _ai_pattern(key_bars=[200, 210, 220, 230, 240])   # 9 bars old
        stale = _ai_pattern(key_bars=[10, 20, 30, 40, 50])         # 199 bars old
        payload_recent = {"patterns": recent["patterns"], "lookback_bars": 250}
        payload_stale = {"patterns": stale["patterns"], "lookback_bars": 250}
        assert adapt_ai_insights_patterns(payload_recent) is not None
        assert adapt_ai_insights_patterns(payload_stale) is None

    def test_age_is_measured_in_the_scans_frame_not_the_callers(self):
        """The two services need not hold the same amount of history.

        `key_bars` index ai-insights' frame, which is `lookback_bars` long. Had
        this used decision-helper's own bar index, a caller with 500 local bars
        against a 250-bar scan would see every pattern as 250 bars old and drop
        the lot.
        """
        payload = {"patterns": _ai_pattern(key_bars=[200, 210, 220, 230, 240])["patterns"],
                   "lookback_bars": 250}
        # A caller far beyond the scan's own length must not change the verdict.
        assert adapt_ai_insights_patterns(payload, bar_index=4999) is not None

    def test_unmappable_patterns_are_dropped_not_coerced(self):
        """A pennant is a continuation like a flag, but the detectors only know
        FLAG_BULL/FLAG_BEAR — calling a pennant a flag would be asserting
        something the payload does not say."""
        for name in ("Pennant", "Symmetrical Triangle", "Gap (runaway)",
                     "Bull Trap", "Wide-Ranging Day"):
            assert adapt_ai_insights_patterns(_ai_pattern(pattern_name=name)) is None

    def test_not_found_patterns_are_skipped(self):
        assert adapt_ai_insights_patterns(_ai_pattern(found=False)) is None

    def test_an_empty_payload_stays_empty(self):
        assert adapt_ai_insights_patterns(None) is None
        assert adapt_ai_insights_patterns({"patterns": []}) is None


# ---------------------------------------------------------------------------
# The S1 invariant — this must not become a confidence consumer
# ---------------------------------------------------------------------------

class TestS1InvariantHolds:
    """S1 (docs/em1_s1_downstream_comparison.md) established that
    decision-helper never reads pattern `confidence`, so EM-1's composite
    confidence cannot affect its decisions.

    Wiring these detectors up is exactly the change that could have
    invalidated that. The adapter emits a whitelist, so it stays true
    structurally rather than by luck — and this test is what stops a future
    field being added without someone noticing the consequence.
    """

    def test_no_confidence_field_survives_the_adapter(self):
        out = adapt_ai_insights_patterns(_ai_pattern())["patterns"][0]
        for banned in ("confidence", "geometric_confidence", "volume_score",
                       "volume_factor", "volume_evidence"):
            assert banned not in out

    def test_the_adapter_emits_only_what_detectors_read(self):
        out = adapt_ai_insights_patterns(_ai_pattern())["patterns"][0]
        assert set(out) <= {
            "pattern_type", "status", "break_direction",
            "measured_move_target", "neckline",
            "confirmation_level", "breakout_level",
        }


# ---------------------------------------------------------------------------
# The detectors that now fire
# ---------------------------------------------------------------------------

class TestDetectorsNowReachable:
    def test_hs_target_failure_fires(self):
        """H&S top whose price is back above the neckline — the measured move
        failed."""
        bars = _bars([100.0] * 40 + [101.0])
        results = detect_failed_signals(
            bars, bars[-1].date, patterns=_ai_pattern(neckline=99.5)
        )
        assert any(r.kind == "HS_TARGET_FAILURE" for r in results)

    def test_double_top_break_fires(self):
        bars = _bars([100.0] * 40 + [101.0])
        results = detect_failed_signals(
            bars, bars[-1].date,
            patterns=_ai_pattern(pattern_name="Double Top", neckline=99.5),
        )
        assert any(r.kind == "DOUBLE_TOP_BREAK" for r in results)

    def test_only_two_of_the_five_are_actually_reachable(self):
        """#73 claimed three; the honest number is two.

        `_counter_anticipated_flag` only appeared to work because of the
        price-inference bug removed at #78 — see
        TestDetectorsStillUnreachable.
        """
        bars = _bars([100.0] * 40 + [101.0])
        kinds = {
            r.kind
            for r in detect_failed_signals(
                bars, bars[-1].date, patterns=_ai_pattern(neckline=99.5)
            )
        }
        assert "HS_TARGET_FAILURE" in kinds

    def test_nothing_fires_without_a_patterns_payload(self):
        bars = _bars([100.0] * 40 + [101.0])
        results = detect_failed_signals(bars, bars[-1].date)
        assert not any(
            r.kind in ("HS_TARGET_FAILURE", "DOUBLE_TOP_BREAK",
                       "COUNTER_ANTICIPATED_FLAG")
            for r in results
        )


# ---------------------------------------------------------------------------
# The two that remain unreachable, and why
# ---------------------------------------------------------------------------

class TestDetectorsStillUnreachable:
    """Two of the five cannot be revived by translation, and that is a fact
    about the upstream data rather than a gap in the adapter. Asserted so the
    limitation is visible instead of implied.
    """

    def test_rounding_break_cannot_be_mapped(self):
        for name in ("Rounding Top", "Rounding Bottom", "Rounded Bottom"):
            assert adapt_ai_insights_patterns(_ai_pattern(pattern_name=name)) is None

    def test_counter_anticipated_flag_cannot_fire_from_one_scan(self):
        """The third unreachable detector, and the correction to #73.

        `FlagDetector` reports flags that are STILL FORMING: across 14 real
        flags the last key bar was the final bar of the scan every time
        (age 0/14). So inside one scan the flag has not broken yet, and a
        counter-break is unobservable whatever the age limit. Detecting a real
        one needs the flag's lower boundary or a later bar, neither of which
        this payload carries.
        """
        # A bull flag, still forming, price below its upside breakout level —
        # the exact shape the old inference mislabelled as a downward break.
        bars = _bars([100.0] * 40 + [95.0])
        payload = _ai_pattern(
            pattern_name="Flag", pattern_type="bullish", neckline=99.5,
            volume_evidence={}, key_bars=[30, 37, 38, 40],
        )
        adapted = adapt_ai_insights_patterns(payload, last_close=95.0)
        assert "break_direction" not in adapted["patterns"][0]
        results = detect_failed_signals(bars, bars[-1].date, patterns=payload)
        assert not any(r.kind == "COUNTER_ANTICIPATED_FLAG" for r in results)

    def test_future_reliability_needs_a_field_nobody_sends(self):
        """It reads `reliability_score`, which is not in the ai-insights
        payload and is not derivable from it, so the adapter does not invent
        one."""
        out = adapt_ai_insights_patterns(_ai_pattern())["patterns"][0]
        assert "reliability_score" not in out
