"""EM-1 / V7 — `FR-EM-V6` the climactic-volume flag, `FR-EM-V8` the API surface.

The last backend task, and it is two small things rather than one:

**`FR-EM-V6`** flags a bar as **climactic** when `rvol` is extreme against a
long baseline *and* price progress is not commensurate — Ch 10's selling
climax, Ch 28's *"prepare to retire into your shell"*, Ch 12's exhaustion gap.
It is **independent of any pattern**, so it is a reading on the frame rather
than a condition inside a rule, and in this slice it is **evidence only**: it
must not alter a signal, a score or a stop. The consuming decision — E&M's
"cancel further commitments in that direction" — belongs to decision-helper
and is a separate candidate.

**`FR-EM-V8`** puts the volume fields on the wire. They have existed on
`PatternMatch` since V4 and in the pydantic schema since V4, but
`insights_service` builds `PatternMatchSchema` field by field in **two** places,
so until now none of them reached a client. The response also has to carry the
`baseline_window` actually used, so a reading is reproducible after the `S2`
sweep changes the default.

Both endpoints are additive: every pre-V7 field keeps its name, type and
meaning, which the response-shape test below pins down.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.models.schemas import AllPatternsResponse, ReversalPatternsResponse, VolumeClimax
from app.services.insights_service import InsightsService
from app.services.patterns.volume import (
    CLIMAX_PROGRESS_RATIO,
    CLIMAX_RVOL,
    DEFAULT_BASELINE_WINDOW,
    LONG_BASELINE_WINDOW,
    ClimaxFlag,
    detect_volume_climax,
)
from tests.volume_harness import (
    bar_pattern_frames,
    climax_frames,
    detect_all,
    planted_frames,
)

#: Every field the pattern payload carried before V7. A client written against
#: the old response must keep working, so these are pinned by name.
PRE_V7_PATTERN_FIELDS = {
    "pattern_name", "pattern_type", "found", "confidence", "key_bars",
    "measured_move_target", "neckline", "details",
}


def _frame(name: str, *, textbook: bool = True):
    pool = climax_frames(textbook=textbook) + bar_pattern_frames(textbook=textbook)
    return next(pf for pf in pool if pf.name == name).frame


async def _all_patterns(frame) -> AllPatternsResponse:
    service = InsightsService()
    with patch.object(service, "_fetch_historical_prices", AsyncMock(return_value=frame)):
        return await service.get_all_patterns("VNM", lookback_bars=len(frame))


async def _reversal_patterns(frame) -> ReversalPatternsResponse:
    service = InsightsService()
    with patch.object(service, "_fetch_historical_prices", AsyncMock(return_value=frame)):
        return await service.get_reversal_patterns("VNM", lookback_bars=len(frame))


# ---------------------------------------------------------------------------
# FR-EM-V6 — the climactic-volume flag
# ---------------------------------------------------------------------------

class TestFRV6ClimaxFlag:
    def test_extreme_volume_with_no_progress_is_flagged(self):
        flag = detect_volume_climax(_frame("selling_climax"))
        assert isinstance(flag, ClimaxFlag)
        assert flag.rvol_long >= CLIMAX_RVOL
        assert flag.progress_ratio <= CLIMAX_PROGRESS_RATIO

    def test_the_same_bar_on_ordinary_volume_is_not_flagged(self):
        """The pair differs only in that one bar's volume, so this is the
        statement that the flag reads volume and not shape."""
        assert detect_volume_climax(_frame("selling_climax", textbook=False)) is None

    def test_a_big_move_on_big_volume_is_not_climactic(self):
        """*"Progress not commensurate"* is half the definition. The one-day
        reversal spikes volume just as hard but **makes its move**, so it is a
        reversal signal, not a climax — and conflating the two would turn every
        high-volume day into a warning."""
        assert detect_volume_climax(_frame("one_day_reversal")) is None

    def test_the_flag_uses_the_long_baseline(self):
        """A climax is extreme *against months*, not against the last fifty
        bars — the same reasoning as `FR-EM-V5` row 11."""
        flag = detect_volume_climax(_frame("selling_climax"))
        assert flag.window == LONG_BASELINE_WINDOW

    def test_the_flag_carries_the_figures_behind_it(self):
        flag = detect_volume_climax(_frame("selling_climax"))
        assert flag.bar_index > 0
        assert flag.rvol_long > 1.0
        assert flag.citation.startswith("E&M")
        assert flag.reason

    def test_a_frame_with_no_volume_is_not_flagged(self):
        assert detect_volume_climax(_frame("selling_climax").drop(columns=["volume"])) is None

    def test_a_short_frame_is_not_flagged(self):
        """`EC-V4`: below the long window there is no basis for "extreme
        against months", and guessing would be worse than declining."""
        short = _frame("selling_climax").tail(40).reset_index(drop=True)
        assert detect_volume_climax(short) is None

    def test_the_flag_is_deterministic(self):
        frame = _frame("selling_climax")
        assert detect_volume_climax(frame) == detect_volume_climax(frame)


class TestTheFlagIsEvidenceOnly:
    """`FR-EM-V6` is explicit that this slice must not act on the flag."""

    def test_no_detection_carries_a_climax_field(self):
        """The flag lives on the response, never on a `PatternMatch` — so
        nothing downstream can accidentally start scoring with it."""
        for match in detect_all(_frame("selling_climax")):
            assert not hasattr(match, "climax")
            assert "climax" not in match.volume_evidence

    def test_computing_the_flag_does_not_touch_the_frame(self):
        frame = _frame("selling_climax")
        before = frame.copy(deep=True)
        detect_volume_climax(frame)
        assert frame.equals(before)

    def test_detections_are_identical_whether_or_not_the_flag_is_computed(self):
        frame = _frame("selling_climax")
        plain = [(m.pattern_name, m.confidence, m.measured_move_target)
                 for m in detect_all(frame)]
        detect_volume_climax(frame)
        after = [(m.pattern_name, m.confidence, m.measured_move_target)
                 for m in detect_all(frame)]
        assert plain == after


# ---------------------------------------------------------------------------
# FR-EM-V8 — the fields reach a client
# ---------------------------------------------------------------------------

class TestFRV8AllPatternsEndpoint:
    async def test_the_volume_fields_are_on_the_wire(self):
        """They have existed on PatternMatch since V4 and in the schema since
        V4, but `_to_schema` built the payload field by field, so no client
        ever saw them. That is the gap this task closes."""
        frame = planted_frames()[0].frame
        response = await _all_patterns(frame)
        assert response.patterns

        scored = [p for p in response.patterns if p.volume_score is not None]
        assert scored, "no pattern carried a volume verdict"
        for pattern in scored:
            assert 0.0 <= pattern.volume_score <= 1.0
            assert 0.5 <= pattern.volume_factor <= 1.15
            assert pattern.geometric_confidence is not None
            assert pattern.volume_evidence

    async def test_the_response_reports_the_baseline_window_it_used(self):
        """So a reading is reproducible. `S2` will change the default, and a
        figure recorded against an unknown window is not evidence."""
        response = await _all_patterns(planted_frames()[0].frame)
        assert response.baseline_window == DEFAULT_BASELINE_WINDOW

    async def test_the_climax_flag_rides_on_the_response(self):
        response = await _all_patterns(_frame("selling_climax"))
        assert isinstance(response.volume_climax, VolumeClimax)
        assert response.volume_climax.rvol_long >= CLIMAX_RVOL

    async def test_no_climax_is_a_null_field_not_a_fabricated_one(self):
        response = await _all_patterns(_frame("selling_climax", textbook=False))
        assert response.volume_climax is None

    async def test_the_evidence_survives_serialisation_in_order(self):
        """`FR-EM-V7`: the evidence is the product feature, and `FR-EM-V9`
        renders it row by row, so its key order has to survive the round trip
        to JSON rather than being re-sorted on the way out."""
        response = await _all_patterns(planted_frames()[0].frame)
        pattern = next(p for p in response.patterns if p.volume_evidence)
        dumped = response.model_dump(mode="json")
        on_wire = next(
            p for p in dumped["patterns"] if p["pattern_name"] == pattern.pattern_name
        )
        assert list(on_wire["volume_evidence"]) == list(pattern.volume_evidence)

    async def test_an_empty_scan_still_reports_its_window(self):
        """A symbol with no data must not return a half-formed response."""
        service = InsightsService()
        with patch.object(service, "_fetch_historical_prices", AsyncMock(return_value=None)):
            response = await service.get_all_patterns("NOPE")
        assert response.patterns == []
        assert response.baseline_window == DEFAULT_BASELINE_WINDOW
        assert response.volume_climax is None


class TestFRV8ReversalEndpoint:
    async def test_the_volume_fields_are_on_the_wire(self):
        """The second construction site. It is a separate code path and was
        missed exactly as easily as the first."""
        response = await _reversal_patterns(planted_frames()[0].frame)
        scored = [p for p in response.patterns if p.volume_score is not None]
        assert scored
        for pattern in scored:
            assert pattern.geometric_confidence is not None
            assert pattern.volume_evidence

    async def test_it_reports_the_baseline_window_and_the_climax(self):
        response = await _reversal_patterns(_frame("selling_climax"))
        assert response.baseline_window == DEFAULT_BASELINE_WINDOW
        assert isinstance(response.volume_climax, VolumeClimax)


# ---------------------------------------------------------------------------
# Old clients are unaffected
# ---------------------------------------------------------------------------

class TestTheChangeIsAdditive:
    async def test_every_pre_v7_pattern_field_is_still_present(self):
        response = await _all_patterns(planted_frames()[0].frame)
        for pattern in response.patterns:
            present = set(pattern.model_dump())
            missing = PRE_V7_PATTERN_FIELDS - present
            assert not missing, f"removed from the payload: {missing}"

    async def test_the_new_fields_all_default_so_a_bare_payload_still_validates(self):
        """A client — or decision-helper — posting or parsing the old shape
        must not hit a validation error on the new fields."""
        from app.models.schemas import PatternMatch as PatternMatchSchema

        bare = PatternMatchSchema(
            pattern_name="Flag", pattern_type="bullish", found=True,
            confidence=0.7, key_bars=[1, 2, 3],
        )
        assert bare.volume_score is None
        assert bare.volume_factor == 1.0
        assert bare.geometric_confidence is None
        assert bare.volume_evidence == {}

    @pytest.mark.parametrize("field", sorted(PRE_V7_PATTERN_FIELDS))
    async def test_pre_v7_fields_keep_their_meaning(self, field):
        """`confidence` is the one that changed value — deliberately, per
        `FR-EM-V7` — but not its name, type or range, which is what a client
        depends on."""
        response = await _all_patterns(planted_frames()[0].frame)
        for pattern in response.patterns:
            assert hasattr(pattern, field)
        if field == "confidence":
            for pattern in response.patterns:
                assert 0.0 <= pattern.confidence <= 1.0
