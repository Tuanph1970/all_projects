"""EM-1 / V4 — `H3` asymmetry, `FR-EM-V7` composition, `EC-V3`, `NFR-V1`.

`FR-EM-V3` is the requirement the SRS calls *"the single most important
requirement in this document, and the one a naive 'volume confirms everything'
implementation gets wrong"*. Edwards & Magee, Ch 7:

> **"It takes buying to put stocks up, but they can fall of their own weight."**

So the rule is asymmetric, and the spec demands this test by name: the same
geometry mirrored, with the same flat breakout volume, must score **lower
bullish than bearish**.

What is compared, and why it is the volume verdict rather than `confidence`
-------------------------------------------------------------------------
``mirrored_pair`` reflects price to the bit, but the two detectors that fire on
the halves do not assign the same *geometric* confidence (0.917 for the H&S
top, 0.95 for the inverse). That difference is a geometry fact and has nothing
to do with the asymmetry, so comparing composite ``confidence`` across the pair
would be comparing two things at once. These tests compare ``volume_score`` and
``volume_factor`` — the volume verdict itself — and check the composition
separately, on one pattern at a time.
"""
from __future__ import annotations

import numpy as np
import pytest

from app.services.patterns.base import PatternDetector, PatternMatch
from app.services.patterns.volume import (
    BEARISH_BREAKOUT,
    BULLISH_BREAKOUT,
    FACTOR_CEILING,
    FACTOR_FLOOR,
    NEUTRAL_FACTOR,
    breakout_bar,
    evaluate_breakout_volume,
    factor_from_score,
)
from tests.volume_harness import (
    detect_all,
    mirrored_pair,
    planted_frames,
    single_match,
    with_burst_at,
)

BEARISH_PATTERN = "Head and Shoulders"
BULLISH_PATTERN = "Inverse Head and Shoulders"


def _pair():
    bearish, bullish = mirrored_pair()
    return (
        (bearish.frame, single_match(bearish.frame, BEARISH_PATTERN)),
        (bullish.frame, single_match(bullish.frame, BULLISH_PATTERN)),
    )


# ---------------------------------------------------------------------------
# H3 — the asymmetry rule
# ---------------------------------------------------------------------------

class TestH3Asymmetry:
    def test_flat_volume_scores_lower_bullish_than_bearish(self):
        """`FR-EM-V3`'s named test. The whole slice exists for this line."""
        (_, bearish), (_, bullish) = _pair()
        assert bullish.volume_score is not None and bearish.volume_score is not None
        assert bullish.volume_score < bearish.volume_score, (
            f"mirrored geometry with identical flat volume scored "
            f"bullish={bullish.volume_score} >= bearish={bearish.volume_score}. "
            f"A symmetric volume requirement is exactly what E&M Ch 7 forbids."
        )

    def test_a_bearish_break_on_flat_volume_is_not_penalised(self):
        """*"They can fall of their own weight."* Absence of expansion on a
        downside break SHALL NOT penalise — so the factor is exactly neutral,
        not merely "not much below" it."""
        (_, bearish), _ = _pair()
        assert bearish.volume_factor == NEUTRAL_FACTOR

    def test_a_bullish_break_on_flat_volume_is_penalised(self):
        """*"It takes buying to put stocks up."* Absence of expansion on an
        upside break is adverse evidence, not missing evidence."""
        _, (_, bullish) = _pair()
        assert bullish.volume_factor < NEUTRAL_FACTOR

    def test_a_bullish_break_on_expanding_volume_is_rewarded(self):
        """The other half of "required": present expansion must help, or the
        rule would only ever be a penalty and `H1` would be satisfiable by a
        constant."""
        frame, match = _pair()[1]
        bar = breakout_bar(match, frame)
        assert bar is not None, "fixture precondition: the upside break must be locatable"
        boosted = single_match(with_burst_at(frame, bar, 4.0), BULLISH_PATTERN)
        assert boosted.volume_factor > NEUTRAL_FACTOR
        assert boosted.volume_score > match.volume_score

    def test_expansion_corroborates_a_bearish_break_more_weakly_than_a_bullish_one(self):
        """Corroboration is worth less than required evidence being met. Same
        burst, same geometry mirrored: the bullish gain must be the larger."""
        (bear_frame, bear), (bull_frame, bull) = _pair()
        bear_bar, bull_bar = breakout_bar(bear, bear_frame), breakout_bar(bull, bull_frame)
        bear_up = single_match(with_burst_at(bear_frame, bear_bar, 4.0), BEARISH_PATTERN)
        bull_up = single_match(with_burst_at(bull_frame, bull_bar, 4.0), BULLISH_PATTERN)

        bear_gain = bear_up.volume_score - bear.volume_score
        bull_gain = bull_up.volume_score - bull.volume_score
        assert bull_gain > bear_gain, f"bullish gain {bull_gain} <= bearish gain {bear_gain}"

    def test_the_asymmetry_lives_in_the_rule_objects_not_in_the_detectors(self):
        """`FR-EM-V3` is encoded once, as data, so V5/V6 extend it by
        instantiating stricter rules rather than by adding an `if` per
        detector — which is how the inverse-H&S rule would otherwise drift
        into being the top's rule inverted."""
        assert BULLISH_BREAKOUT.expansion_required is True
        assert BEARISH_BREAKOUT.expansion_required is False
        assert BEARISH_BREAKOUT.dull_penalty == 0.0
        assert BULLISH_BREAKOUT.dull_penalty > 0.0
        assert BULLISH_BREAKOUT.confirm_reward > BEARISH_BREAKOUT.confirm_reward


# ---------------------------------------------------------------------------
# FR-EM-V7 — composition
# ---------------------------------------------------------------------------

class TestFRV7Composition:
    def test_confidence_is_geometric_times_factor(self):
        for frame, match in _pair():
            expected = min(1.0, max(0.0, match.geometric_confidence * match.volume_factor))
            # abs=1e-3 because `confidence` is rounded to 3dp, as it always has been.
            assert match.confidence == pytest.approx(expected, abs=1e-3)

    def test_geometric_confidence_preserves_the_pre_volume_value(self):
        """The geometric reading must survive intact — it is what `H1`'s
        invariance test and the UI's "volume moved the number" both read."""
        bearish, bullish = mirrored_pair()
        for planted, name, expected in (
            (bearish, BEARISH_PATTERN, 0.917),
            (bullish, BULLISH_PATTERN, 0.95),
        ):
            # The pre-V4 geometric values, recorded by V2's baseline run.
            assert single_match(planted.frame, name).geometric_confidence == pytest.approx(expected)

    def test_factor_is_bounded_however_extreme_the_score(self):
        """Volume is corroboration, not the finding: no verdict may erase a
        geometrically excellent pattern or manufacture a poor one."""
        for score in np.linspace(0.0, 1.0, 101):
            factor = factor_from_score(float(score))
            assert FACTOR_FLOOR <= factor <= FACTOR_CEILING
        assert factor_from_score(0.0) == pytest.approx(FACTOR_FLOOR)
        assert factor_from_score(0.5) == pytest.approx(NEUTRAL_FACTOR)
        assert factor_from_score(1.0) == pytest.approx(FACTOR_CEILING)

    def test_factor_is_monotone_in_the_score(self):
        factors = [factor_from_score(s) for s in np.linspace(0.0, 1.0, 51)]
        assert all(b >= a for a, b in zip(factors, factors[1:]))

    def test_confidence_stays_in_the_unit_interval(self):
        """The ceiling is above 1.0, so a 0.95 geometric reading would compose
        past 1.0 without the clamp — and `found`/`confidence` are consumed by
        PatternPanel.js and failed_signal.py as a 0..1 number."""
        for pf in planted_frames():
            for match in detect_all(pf.frame):
                assert 0.0 <= match.confidence <= 1.0

    def test_an_extreme_burst_cannot_push_confidence_above_one(self):
        frame, match = _pair()[1]
        boosted = single_match(with_burst_at(frame, breakout_bar(match, frame), 50.0), BULLISH_PATTERN)
        assert boosted.volume_factor == pytest.approx(FACTOR_CEILING)
        assert boosted.confidence == 1.0


# ---------------------------------------------------------------------------
# Unknown is neutral, never adverse
# ---------------------------------------------------------------------------

class TestUnknownIsNeutral:
    def test_no_locatable_breakout_is_neutral_not_adverse(self):
        """A pattern that has not broken out yet has no breakout volume to
        judge. That is missing evidence, not bad evidence — scoring it 0.0
        would read as "volume contradicts"."""
        flag = next(pf for pf in planted_frames() if pf.name == "bull_flag")
        match = single_match(flag.frame, "Flag")
        assert breakout_bar(match, flag.frame) is None
        assert match.volume_score is None
        assert match.volume_factor == NEUTRAL_FACTOR
        assert match.confidence == match.geometric_confidence

    def test_a_neutral_pattern_type_carries_no_directional_verdict(self):
        """`SymmetricalTriangleDetector` returns ``pattern_type="neutral"``,
        so the direction-aware rule has nothing to apply. Its own condition —
        volume diminishing toward the apex — is `FR-EM-V5`, task V6."""
        triangle = next(pf for pf in planted_frames() if pf.name == "symmetrical_triangle")
        match = single_match(triangle.frame, "Symmetrical Triangle")
        assert match.pattern_type == "neutral"
        assert match.volume_score is None
        assert match.volume_factor == NEUTRAL_FACTOR

    def test_evidence_says_why_there_is_no_verdict(self):
        flag = next(pf for pf in planted_frames() if pf.name == "bull_flag")
        evidence = single_match(flag.frame, "Flag").volume_evidence
        assert evidence["status"] == "unknown"
        assert evidence["reason"]


# ---------------------------------------------------------------------------
# EC-V3 — volume is strictly optional
# ---------------------------------------------------------------------------

class TestECV3VolumeIsOptional:
    def test_a_frame_with_no_volume_column_behaves_exactly_as_before(self):
        for pf in planted_frames():
            with_vol = detect_all(pf.frame)
            without = detect_all(pf.frame.drop(columns=["volume"]))
            assert [m.pattern_name for m in without] == [m.pattern_name for m in with_vol]
            for match in without:
                assert match.volume_score is None
                assert match.volume_factor == NEUTRAL_FACTOR
                assert match.confidence == match.geometric_confidence

    def test_validate_ohlc_still_requires_only_high_low_close(self):
        """`EC-V3` is a contract, not a courtesy: the existing fixtures and
        several callers hand over frames with no volume at all."""
        frame = planted_frames()[0].frame.drop(columns=["volume", "open"])
        ok, reason = PatternDetector._validate_ohlc(frame, min_bars=10)
        assert ok, reason

    def test_an_all_null_volume_column_is_neutral(self):
        """`EC-V1`: the upstream column is nullable, and NULL must never be
        imputed as zero."""
        frame = planted_frames()[0].frame.copy()
        frame["volume"] = np.nan
        for match in detect_all(frame):
            assert match.volume_score is None
            assert match.volume_factor == NEUTRAL_FACTOR


# ---------------------------------------------------------------------------
# NFR-V1 — a volume bug must not drop a detection
# ---------------------------------------------------------------------------

class TestNFRV1FailureIsolation:
    def test_a_raising_scorer_degrades_to_neutral_and_keeps_the_detection(self, monkeypatch):
        """The detectors' own ``try/except`` would swallow the *detection*
        along with the error. Volume evaluation therefore has to fail inward,
        to ``volume_factor = 1.0``, rather than outward."""
        import app.services.patterns.base as base_module

        def boom(*_args, **_kwargs):
            raise RuntimeError("synthetic volume failure")

        monkeypatch.setattr(base_module, "evaluate_breakout_volume", boom)

        pf = planted_frames()[0]
        matches = detect_all(pf.frame)
        assert matches, "the detection must survive a volume failure"
        for match in matches:
            assert match.volume_factor == NEUTRAL_FACTOR
            assert match.volume_score is None
            assert match.confidence == match.geometric_confidence
            assert match.volume_evidence.get("reason") == "volume_evaluation_failed"


# ---------------------------------------------------------------------------
# The evidence is the product feature (FR-EM-V7) and H6 determinism
# ---------------------------------------------------------------------------

class TestEvidenceIsRenderable:
    def test_evidence_names_the_condition_and_carries_its_rvol(self):
        """E&M's rules *are* the feature here; a bare number would hide them
        from the trader reading the card."""
        _, (_, bullish) = _pair()
        evidence = bullish.volume_evidence
        assert evidence["status"] == "known"
        assert evidence["verdict"] in {"confirms", "neutral", "contradicts", "suspect"}
        assert evidence["direction"] == "bullish"
        assert evidence["expansion_required"] is True
        assert isinstance(evidence["rvol"], float)
        assert evidence["breakout_bar"] == breakout_bar(bullish, mirrored_pair()[1].frame)
        assert evidence["baseline_window"] > 0

    def test_evidence_key_order_is_stable(self):
        """`H6`. The UI renders this dict in order, and a comparison test on
        the evidence is only meaningful if the order does not drift."""
        first = [list(m.volume_evidence) for m in detect_all(planted_frames()[0].frame)]
        second = [list(m.volume_evidence) for m in detect_all(planted_frames()[0].frame)]
        assert first == second

    def test_repeated_evaluation_is_identical(self):
        frame, match = _pair()[1]
        a = evaluate_breakout_volume(match, frame)
        b = evaluate_breakout_volume(match, frame)
        assert a == b

    def test_a_contradicting_verdict_is_labelled_as_such(self):
        """The four labels are a user-facing vocabulary, so the mapping from
        score to label is asserted rather than left to the renderer."""
        _, (_, bullish) = _pair()
        assert bullish.volume_evidence["verdict"] == "contradicts"
        (_, bearish), _ = _pair()
        assert bearish.volume_evidence["verdict"] == "neutral"


class TestPatternMatchDefaults:
    def test_the_new_fields_are_optional_and_additive(self):
        """Every existing construction site — and `decision-helper` over
        HTTP — must keep working without passing any volume field."""
        match = PatternMatch(
            pattern_name="X", pattern_type="bullish", found=True, confidence=0.7
        )
        assert match.volume_score is None
        assert match.volume_factor == NEUTRAL_FACTOR
        assert match.volume_evidence == {}
        assert match.geometric_confidence is None
