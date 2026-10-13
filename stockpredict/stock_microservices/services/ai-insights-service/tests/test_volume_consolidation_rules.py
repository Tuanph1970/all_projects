"""EM-1 / V6a — `FR-EM-V5` rows 5–9 and `FR-EM-V4`, the suspect-volume rule.

Five formations, and the reason they are one task is that they share a single
condition: **volume must dry up through the consolidation**. What makes them
interesting is `FR-EM-V4`, the requirement no conventional indicator encodes —
volume evidence here is **not monotone**, so more volume can score *worse*:

* **Flag / Pennant** (Ch 11) — *"high or irregular volume inside the pattern
  turns it into a minor reversal area"*. Expansion inside the consolidation
  does not merely weaken the pattern, it **inverts its meaning**. The pennant
  is stricter: *"volume dries up even faster, sometimes to almost nothing"*.
* **Symmetrical Triangle** (Ch 8) — *"volume diminishes irregularly but
  noticeably toward the apex, then expands on the breakout"*. Upside break:
  expansion **required**. Downside break: **suspect**, often a 2–3 day
  shakeout. It is also the book's worst offender for false moves, so it
  carries the heaviest volume weighting of the three triangles.
* **Ascending Triangle** (Ch 8) — resolves upside about 9:1, so breakout
  expansion is **required**.
* **Descending Triangle** (Ch 8) — downside resolution, so breakout volume
  only **corroborates**; an *extreme* downside break is **suspect**.

Two structural facts shaped this suite and are worth knowing before reading it:

1. **All five are detected while still unresolved.** A flag or a triangle is
   actionable precisely before it breaks, so there is usually no penetration to
   read and the formation conditions are the whole of the evidence. The
   breakout rules are therefore tested on frames resolved on purpose by
   ``with_resolution``.
2. **The symmetrical triangle has no direction.** It reports
   ``pattern_type="neutral"``, so its breakout rule cannot be selected from the
   pattern type the way every rule before it was — the direction has to be
   *inferred from the penetration itself*. That is what `breakout_event` adds.
"""
from __future__ import annotations

import numpy as np
import pytest

from app.services.patterns.volume import (
    ASCENDING_BREAKOUT,
    DESCENDING_BREAKOUT,
    PATTERN_RULES,
    SYMMETRICAL_DOWN_BREAKOUT,
    SYMMETRICAL_UP_BREAKOUT,
    VERDICT_SUSPECT,
    BreakoutRule,
    SpanTrend,
    breakout_event,
    score_breakout,
)
from tests.volume_harness import (
    consolidation_frames,
    single_match,
    with_resolution,
)

FORMATIONS = [
    ("bull_flag", "Flag"),
    ("bull_pennant", "Pennant"),
    ("symmetrical_triangle", "Symmetrical Triangle"),
    ("ascending_triangle", "Ascending Triangle"),
    ("descending_triangle", "Descending Triangle"),
]


def _frame(name: str, *, textbook: bool = True):
    return next(pf for pf in consolidation_frames(textbook=textbook) if pf.name == name)


def _pair(name: str, pattern: str):
    return (
        single_match(_frame(name).frame, pattern),
        single_match(_frame(name, textbook=False).frame, pattern),
    )


# ---------------------------------------------------------------------------
# The shared condition: volume dries up through the consolidation
# ---------------------------------------------------------------------------

class TestDryingUpIsRequired:
    @pytest.mark.parametrize("name,pattern", FORMATIONS, ids=[f[0] for f in FORMATIONS])
    def test_drying_volume_scores_above_swelling_volume(self, name, pattern):
        textbook, adverse = _pair(name, pattern)
        assert textbook.volume_score is not None, f"{name}: no verdict on the textbook frame"
        assert adverse.volume_score is not None, f"{name}: no verdict on the adverse frame"
        assert textbook.volume_score > adverse.volume_score, (
            f"{name}: drying={textbook.volume_score} did not beat "
            f"swelling={adverse.volume_score}"
        )

    @pytest.mark.parametrize("name,pattern", FORMATIONS, ids=[f[0] for f in FORMATIONS])
    def test_the_verdict_reads_confirms_when_volume_dries(self, name, pattern):
        textbook, _ = _pair(name, pattern)
        assert textbook.volume_evidence["verdict"] == "confirms"

    @pytest.mark.parametrize("name,pattern", FORMATIONS, ids=[f[0] for f in FORMATIONS])
    def test_geometry_is_identical_across_the_pair(self, name, pattern):
        textbook, adverse = _pair(name, pattern)
        assert textbook.geometric_confidence == adverse.geometric_confidence

    @pytest.mark.parametrize("name,pattern", FORMATIONS, ids=[f[0] for f in FORMATIONS])
    def test_every_rule_carries_a_drying_condition(self, name, pattern):
        rule = PATTERN_RULES[pattern]
        assert any(
            isinstance(c, SpanTrend) and c.expect == "drying" for c in rule.conditions
        ), f"{pattern} has no drying-up condition"


# ---------------------------------------------------------------------------
# FR-EM-V4 — volume evidence is NOT monotone
# ---------------------------------------------------------------------------

class TestFRV4SuspectVolume:
    """The requirement that no conventional indicator encodes.

    Tested on the scoring function across the whole `rvol` range rather than at
    two sampled points, because the claim is about the *shape* of the rule: it
    must rise into the corroborating band and then **fall** once volume becomes
    extreme. A two-point test would pass for a monotone rule if the points were
    chosen carelessly.
    """

    def test_a_downside_triangle_break_scores_lower_as_volume_becomes_extreme(self):
        rule = DESCENDING_BREAKOUT
        assert rule.suspect_above_rvol is not None, "the rule declares no suspect band"

        moderate = score_breakout(rule.confirm_rvol * 1.1, rule)
        extreme = score_breakout(rule.suspect_above_rvol * 2.0, rule)
        assert extreme < moderate, (
            f"more volume on a downside break scored higher, not lower "
            f"(moderate={moderate}, extreme={extreme}) — E&M Ch 8: a high-volume "
            f"downside break is suspect, often a 2-3 day shakeout"
        )

    def test_the_scoring_curve_is_genuinely_non_monotone(self):
        """Rises then falls. This is the property a later refactor is most
        likely to "simplify" into a monotone rule, because a rule where more
        evidence is worse reads like a sign error."""
        rule = DESCENDING_BREAKOUT
        rvols = np.linspace(0.2, rule.suspect_above_rvol * 3.0, 200)
        scores = [score_breakout(float(r), rule) for r in rvols]
        peak = int(np.argmax(scores))
        assert 0 < peak < len(scores) - 1, (
            "the curve peaks at an endpoint, so it is monotone — FR-EM-V4 is not encoded"
        )
        assert scores[-1] < scores[peak]

    def test_the_suspect_band_is_labelled_suspect_not_merely_low(self):
        """`suspect` is one of the four user-facing verdicts (`FR-EM-V9`). A
        shakeout and a dull break are different things and must not read the
        same on the card."""
        rule = DESCENDING_BREAKOUT
        planted = _frame("descending_triangle")
        resolved = with_resolution(
            planted.frame, "bearish", volume_multiple=rule.suspect_above_rvol * 2.0
        )
        match = single_match(resolved, "Descending Triangle")
        component = match.volume_evidence["components"]["breakout volume"]
        assert component["verdict"] == VERDICT_SUSPECT, component

    def test_a_moderate_downside_break_still_corroborates(self):
        """The band below suspect must still reward, or the rule has become a
        plain penalty and the non-monotonicity is lost."""
        rule = DESCENDING_BREAKOUT
        planted = _frame("descending_triangle")
        resolved = with_resolution(
            planted.frame, "bearish", volume_multiple=rule.confirm_rvol * 1.1
        )
        component = single_match(resolved, "Descending Triangle").volume_evidence[
            "components"
        ]["breakout volume"]
        assert component["verdict"] == "confirms", component

    def test_a_dull_downside_break_is_not_penalised(self):
        """`FR-EM-V3` still governs: they can fall of their own weight."""
        resolved = with_resolution(
            _frame("descending_triangle").frame, "bearish", volume_multiple=0.4
        )
        component = single_match(resolved, "Descending Triangle").volume_evidence[
            "components"
        ]["breakout volume"]
        assert component["score"] == 0.5, component

    def test_expansion_inside_a_flag_is_suspect_not_merely_unmet(self):
        """Ch 11: high volume inside the pattern turns a continuation into a
        minor reversal area — an inversion of meaning, not a shortfall.

        On a **flag** the inversion is carried by the mast ratio rather than by
        the trend, and that is a consequence of the detector rather than a
        choice: `FlagDetector` returns the *shortest* qualifying flag, which
        here is three bars — too short for a rank trend to be readable at all.
        So the condition that has to express the inversion is the one that can
        be read, and a consolidation trading as heavily as the thrust that
        created it is exactly E&M's reversal area.
        """
        _, adverse = _pair("bull_flag", "Flag")
        ratio = adverse.volume_evidence["components"]["flag volume markedly below the mast"]
        assert ratio["verdict"] == VERDICT_SUSPECT, ratio
        assert ratio["value"] > 1.0, "the adverse flag should trade above its mast"

    def test_expansion_inside_a_pennant_is_suspect_on_the_trend_too(self):
        """The pennant's span *is* long enough for the trend to be read, so the
        same inversion shows up through the other mechanism. Both are tested
        because a later detector change to flag length would move which one
        carries it."""
        _, adverse = _pair("bull_pennant", "Pennant")
        trend = adverse.volume_evidence["components"][
            "volume dries up continuously through the pennant"
        ]
        assert trend["verdict"] == VERDICT_SUSPECT, trend
        assert trend["value"] > 0.0, "the adverse pennant's volume should be rising"


# ---------------------------------------------------------------------------
# The symmetrical triangle has no direction of its own
# ---------------------------------------------------------------------------

class TestDirectionInference:
    def test_a_neutral_pattern_gets_its_direction_from_the_penetration(self):
        planted = _frame("symmetrical_triangle")
        match = single_match(planted.frame, "Symmetrical Triangle")
        assert match.pattern_type == "neutral"

        for direction in ("bullish", "bearish"):
            resolved = with_resolution(planted.frame, direction)
            resolved_match = single_match(resolved, "Symmetrical Triangle")
            event = breakout_event(resolved_match, resolved)
            assert event is not None, f"no {direction} break located"
            assert event.direction == direction
            assert event.bar >= resolved_match.key_bars[-1]

    def test_a_formation_still_inside_its_boundaries_reports_no_event(self):
        """Cut the frame at the final pivot, so price has not yet left the
        converging channel. ``None`` here is a real state, not a failure — and
        it is the state most live triangles are in when they are scanned.

        (The full fixture *does* resolve, upward, a bar after its last pivot:
        the oscillation carries price above the upper line as the two lines
        converge. That is a genuine penetration by the detector's own boundary
        definition, which is why this test truncates rather than relying on the
        unresolved frame being unresolved.)
        """
        planted = _frame("symmetrical_triangle")
        match = single_match(planted.frame, "Symmetrical Triangle")
        truncated = planted.frame.iloc[: match.key_bars[-1] + 1]
        assert breakout_event(match, truncated) is None

    def test_the_two_directions_select_different_breakout_rules(self):
        """Upside break: expansion required. Downside break: suspect. Same
        pattern, opposite treatment — which is only possible because the rule
        is chosen by the inferred direction rather than by `pattern_type`."""
        rule = PATTERN_RULES["Symmetrical Triangle"]
        assert rule.breakout_by_direction is not None
        assert rule.breakout_by_direction["bullish"] is SYMMETRICAL_UP_BREAKOUT
        assert rule.breakout_by_direction["bearish"] is SYMMETRICAL_DOWN_BREAKOUT
        assert SYMMETRICAL_UP_BREAKOUT.expansion_required is True
        assert SYMMETRICAL_DOWN_BREAKOUT.suspect_above_rvol is not None

    def test_a_dull_upside_break_of_a_symmetrical_triangle_is_penalised(self):
        resolved = with_resolution(
            _frame("symmetrical_triangle").frame, "bullish", volume_multiple=0.4
        )
        component = single_match(resolved, "Symmetrical Triangle").volume_evidence[
            "components"
        ]["breakout volume"]
        assert component["score"] < 0.5, component

    def test_a_high_volume_downside_break_of_a_symmetrical_triangle_is_suspect(self):
        resolved = with_resolution(
            _frame("symmetrical_triangle").frame, "bearish",
            volume_multiple=SYMMETRICAL_DOWN_BREAKOUT.suspect_above_rvol * 2.0,
        )
        component = single_match(resolved, "Symmetrical Triangle").volume_evidence[
            "components"
        ]["breakout volume"]
        assert component["verdict"] == VERDICT_SUSPECT, component


# ---------------------------------------------------------------------------
# The per-detector calibration the book asks for
# ---------------------------------------------------------------------------

class TestPerDetectorCalibration:
    def test_the_pennant_demands_faster_drying_than_the_flag(self):
        """Ch 11: *"volume dries up even faster, sometimes to almost nothing."*"""
        def drying(pattern):
            return next(
                c for c in PATTERN_RULES[pattern].conditions
                if isinstance(c, SpanTrend) and c.expect == "drying"
            )
        assert drying("Pennant").threshold > drying("Flag").threshold

    def test_the_symmetrical_triangle_carries_the_heaviest_weighting(self):
        """The book's worst offender for false moves, so volume gets more say
        there than on the other two triangles."""
        weights = {
            name: PATTERN_RULES[name].breakout_weight
            for name in ("Symmetrical Triangle", "Ascending Triangle", "Descending Triangle")
        }
        assert weights["Symmetrical Triangle"] > weights["Ascending Triangle"]
        assert weights["Symmetrical Triangle"] > weights["Descending Triangle"]

    def test_the_ascending_triangle_requires_its_upside_expansion(self):
        """~9:1 upside resolution, so an upside break without volume is a
        failed requirement, not a missing nicety."""
        assert ASCENDING_BREAKOUT.expansion_required is True
        resolved = with_resolution(
            _frame("ascending_triangle").frame, "bullish", volume_multiple=0.4
        )
        component = single_match(resolved, "Ascending Triangle").volume_evidence[
            "components"
        ]["breakout volume"]
        assert component["score"] < 0.5, component

    def test_the_descending_triangle_does_not_require_expansion(self):
        assert DESCENDING_BREAKOUT.expansion_required is False


# ---------------------------------------------------------------------------
# Registry, bounds, and unavailability
# ---------------------------------------------------------------------------

class TestRegistryAndBounds:
    def test_the_registry_now_covers_nine_detectors(self):
        """Four reversal from V5, five consolidation from V6a. The three V6b
        reaches — Gap, Wide-Ranging Day and the traps — are still absent, so
        that task cannot land half-done unnoticed."""
        assert set(PATTERN_RULES) == {
            "Head and Shoulders",
            "Inverse Head and Shoulders",
            "Double Top",
            "Double Bottom",
            "Flag",
            "Pennant",
            "Symmetrical Triangle",
            "Ascending Triangle",
            "Descending Triangle",
        }

    @pytest.mark.parametrize("name,pattern", FORMATIONS, ids=[f[0] for f in FORMATIONS])
    def test_scores_and_factors_stay_in_range(self, name, pattern):
        for match in _pair(name, pattern):
            assert 0.0 <= match.volume_score <= 1.0
            assert 0.5 <= match.volume_factor <= 1.15
            assert 0.0 <= match.confidence <= 1.0

    @pytest.mark.parametrize("name,pattern", FORMATIONS, ids=[f[0] for f in FORMATIONS])
    def test_no_volume_column_is_neutral(self, name, pattern):
        frame = _frame(name).frame.drop(columns=["volume"])
        match = single_match(frame, pattern)
        assert match.volume_score is None
        assert match.confidence == match.geometric_confidence

    @pytest.mark.parametrize("name,pattern", FORMATIONS, ids=[f[0] for f in FORMATIONS])
    def test_every_condition_is_reported_as_evidence(self, name, pattern):
        textbook, _ = _pair(name, pattern)
        components = textbook.volume_evidence["components"]
        for condition in PATTERN_RULES[pattern].conditions:
            assert condition.label in components, condition.label

    def test_suspect_rules_declare_their_penalty(self):
        for name, rule in PATTERN_RULES.items():
            for breakout in rule.all_breakouts():
                assert isinstance(breakout, BreakoutRule), name
                if breakout.suspect_above_rvol is not None:
                    assert breakout.suspect_above_rvol > breakout.confirm_rvol, name
                    assert breakout.suspect_penalty > 0.0, name
