"""EM-1 / V5 — `FR-EM-V5` rows 1–4: the reversal detectors' volume conditions.

Four rules, each from a different page of Edwards & Magee, and the point of the
task is that they are **four different rules** rather than one applied four
times:

* **Head and Shoulders** (Ch 6) — left shoulder heavy, right shoulder
  **decidedly less**; breakout volume corroborating only, the break being
  bearish. **Head volume is not scored at all.**
* **Inverse H&S** (Ch 7) — volume **builds** through the head and the
  right-shoulder rally; a conspicuous burst on the neckline penetration is
  **required**, and carries the strongest penalty in the rule set.
* **Double Top** (Ch 9) — **less volume on the second top**, which is the
  distinguishing evidence; valley-break volume corroborating only.
* **Double Bottom** (Ch 9) — second bottom *"conspicuously dull and rounded"*;
  the pattern is not proven until price exceeds the intervening high **on
  rising volume**, so breakout expansion is required.

Two of these are easy to get wrong in ways a thinner test suite would not
catch, so each has a test of its own:

* **The head's volume must not be scored.** E&M report that of confirmed H&S
  tops, roughly a third are heavier on the left shoulder, a third about equal
  and a third heavier on the head — so head volume carries no information, and
  a rule that scored it would be reading noise as evidence.
* **The inverse H&S must not reuse the top's rule inverted.** The price pattern
  is a reflection; the volume pattern is not. This is the single most likely
  "simplification" a later refactor will make, so it is asserted structurally
  (on the rule objects) as well as behaviourally.

Each detector is exercised against a **textbook / adverse pair** — identical
geometry, opposite volume script — which is the cleanest statement that the
rule reads the condition rather than the shape.
"""
from __future__ import annotations

import numpy as np
import pytest

from dataclasses import replace

from app.services.patterns.volume import (
    BEARISH_BREAKOUT,
    BULLISH_BREAKOUT,
    INVERSE_HS_BREAKOUT,
    NEUTRAL_FACTOR,
    PATTERN_RULES,
    BreakoutRule,
    SpanLevel,
    SpanRatio,
    SpanTrend,
    evaluate_pattern_volume,
)
from tests.volume_harness import (
    adverse_frames,
    planted_frames,
    single_match,
)

PAIRS = [
    ("hs_top", "Head and Shoulders"),
    ("inv_hs", "Inverse Head and Shoulders"),
    ("double_top", "Double Top"),
    ("double_bottom", "Double Bottom"),
]


def _by_name(frames, name):
    return next(pf for pf in frames if pf.name == name)


def _textbook_and_adverse(frame_name: str, pattern: str):
    textbook = single_match(_by_name(planted_frames(), frame_name).frame, pattern)
    adverse = single_match(_by_name(adverse_frames(), frame_name).frame, pattern)
    return textbook, adverse


# ---------------------------------------------------------------------------
# The four conditions, as textbook-vs-adverse pairs
# ---------------------------------------------------------------------------

class TestFRV5ReversalConditions:
    @pytest.mark.parametrize("frame_name,pattern", PAIRS, ids=[p[0] for p in PAIRS])
    def test_textbook_volume_scores_above_adverse(self, frame_name, pattern):
        textbook, adverse = _textbook_and_adverse(frame_name, pattern)
        assert textbook.volume_score is not None, f"{frame_name}: no verdict on the textbook frame"
        assert adverse.volume_score is not None, f"{frame_name}: no verdict on the adverse frame"
        assert textbook.volume_score > adverse.volume_score, (
            f"{frame_name}: textbook={textbook.volume_score} did not exceed "
            f"adverse={adverse.volume_score} — the rule is not reading its condition"
        )

    @pytest.mark.parametrize("frame_name,pattern", PAIRS, ids=[p[0] for p in PAIRS])
    def test_textbook_volume_confirms_and_adverse_does_not(self, frame_name, pattern):
        """The verdict label is user-facing (`FR-EM-V9`), so assert the words
        a trader will read, not only the number behind them."""
        textbook, adverse = _textbook_and_adverse(frame_name, pattern)
        assert textbook.volume_evidence["verdict"] == "confirms"
        assert adverse.volume_evidence["verdict"] != "confirms"

    @pytest.mark.parametrize("frame_name,pattern", PAIRS, ids=[p[0] for p in PAIRS])
    def test_geometry_is_untouched_by_either_script(self, frame_name, pattern):
        """`H1`'s invariant, restated per pair: the same geometry must yield
        the same geometric reading whatever the volume says."""
        textbook, adverse = _textbook_and_adverse(frame_name, pattern)
        assert textbook.geometric_confidence == adverse.geometric_confidence

    @pytest.mark.parametrize("frame_name,pattern", PAIRS, ids=[p[0] for p in PAIRS])
    def test_every_condition_is_reported_as_evidence(self, frame_name, pattern):
        """E&M's rules are the product feature; each condition the rule tested
        has to be visible with the figure behind it."""
        textbook, _ = _textbook_and_adverse(frame_name, pattern)
        components = textbook.volume_evidence["components"]
        rule = PATTERN_RULES[pattern]
        expected = {c.label for c in rule.conditions}
        if rule.breakout is not None:
            expected.add("breakout volume")
        assert set(components) == expected
        for label, detail in components.items():
            assert "verdict" in detail, label
            assert "value" in detail, label


# ---------------------------------------------------------------------------
# Head volume is deliberately not scored (E&M Ch 6)
# ---------------------------------------------------------------------------

class TestHeadVolumeIsNotScored:
    #: How much smaller the head's influence must be than a shoulder's.
    #: A ratio rather than an absolute bound, so the assertion stays meaningful
    #: if the thresholds are re-swept at `S2`.
    MAX_HEAD_SHARE = 0.1

    def _score_with_spike(self, anchor_position: int, multiplier: float) -> float:
        planted = _by_name(planted_frames(), "hs_top")
        reference = single_match(planted.frame, "Head and Shoulders")
        centre = reference.key_bars[anchor_position]
        frame = planted.frame.copy(deep=True)
        volume = frame["volume"].to_numpy(dtype=float).copy()
        volume[centre - 3: centre + 4] *= multiplier
        frame["volume"] = volume
        return single_match(frame, "Head and Shoulders").volume_score

    def test_the_head_moves_the_verdict_far_less_than_a_shoulder_does(self):
        """E&M Ch 6: of confirmed H&S tops, roughly a third are heavier on the
        left shoulder, a third about equal and a third heavier on the head — so
        head volume is not a tell, and a rule that scored it would be fitting
        noise.

        Asserted as a ratio rather than as exact invariance, because exact
        invariance is **not achievable and should not be**: `rvol` is measured
        against a trailing median (`FR-EM-V1`), that window necessarily
        contains the head, so a violent head spike shifts the baseline every
        later bar is read against. That is E&M's own framing — *"high" means
        high for that stock in that period* — not a leak.

        Measured: a 6x head spike moves the score by ~0.009; the same spike on
        a shoulder moves it by ~0.43. The head's residual influence is roughly
        fifty times smaller, which is the difference between "not scored" and
        "scored".
        """
        base = single_match(
            _by_name(planted_frames(), "hs_top").frame, "Head and Shoulders"
        ).volume_score

        head = max(
            abs(self._score_with_spike(2, 6.0) - base),
            abs(self._score_with_spike(2, 0.2) - base),
        )
        shoulder = max(
            abs(self._score_with_spike(4, 6.0) - base),
            abs(self._score_with_spike(0, 0.2) - base),
        )
        assert shoulder > 0.05, f"the shoulder conditions are not responsive ({shoulder})"
        assert head <= self.MAX_HEAD_SHARE * shoulder, (
            f"head volume moved the verdict by {head:.4f} against a shoulder's "
            f"{shoulder:.4f} — the head is being scored as evidence"
        )

    def test_the_rule_declares_what_it_deliberately_ignores(self):
        rule = PATTERN_RULES["Head and Shoulders"]
        assert "head" in rule.unscored_note.lower()
        assert not any(c.anchors_include(2) for c in rule.conditions), (
            "a condition anchors on key_bars[2], which is the head"
        )


# ---------------------------------------------------------------------------
# The inverse H&S is not the top's rule inverted (E&M Ch 7)
# ---------------------------------------------------------------------------

class TestInverseIsNotTheTopInverted:
    def test_the_two_rules_test_different_conditions(self):
        top = PATTERN_RULES["Head and Shoulders"]
        bottom = PATTERN_RULES["Inverse Head and Shoulders"]
        assert {type(c) for c in top.conditions} != {type(c) for c in bottom.conditions}

    def test_the_bottom_reads_a_building_trend_not_a_shoulder_ratio(self):
        """The top's evidence is a *comparison* between shoulders; the bottom's
        is a *direction* through the formation. Asserted on the rule objects so
        a refactor that collapses them into one parametrised rule fails here
        rather than silently halving the rule set."""
        bottom = PATTERN_RULES["Inverse Head and Shoulders"]
        assert any(isinstance(c, SpanTrend) and c.expect == "building" for c in bottom.conditions)
        assert not any(isinstance(c, SpanRatio) for c in bottom.conditions)

    def test_the_bottom_requires_its_breakout_burst_and_the_top_does_not(self):
        assert PATTERN_RULES["Inverse Head and Shoulders"].breakout.expansion_required is True
        assert PATTERN_RULES["Head and Shoulders"].breakout.expansion_required is False

    def test_the_head_and_shoulders_bottom_carries_the_strongest_penalty(self):
        """E&M: *"there must be a conspicuous burst of volume on the neckline
        penetration. Without it, don't trust the breakout."* The SRS makes that
        the strongest penalty in the rule set, so it must beat the generic
        bullish rule on both axes — how much it costs, and how much volume it
        demands before it is satisfied."""
        others = [
            r.breakout for r in PATTERN_RULES.values()
            if r.breakout is not None and r.breakout is not INVERSE_HS_BREAKOUT
        ] + [BULLISH_BREAKOUT, BEARISH_BREAKOUT]

        assert all(INVERSE_HS_BREAKOUT.dull_penalty >= o.dull_penalty for o in others)
        assert INVERSE_HS_BREAKOUT.dull_penalty > BULLISH_BREAKOUT.dull_penalty
        assert all(
            INVERSE_HS_BREAKOUT.confirm_rvol >= o.confirm_rvol
            for o in others if o.expansion_required
        )

    def test_a_missing_burst_hurts_the_bottom_more_than_a_missing_one_hurts_a_double_bottom(self):
        """Both are bullish breaks that require expansion, so this isolates the
        *strength* of the requirement rather than its direction."""
        inv = single_match(_by_name(adverse_frames(), "inv_hs").frame, "Inverse Head and Shoulders")
        dbl = single_match(_by_name(adverse_frames(), "double_bottom").frame, "Double Bottom")
        inv_break = inv.volume_evidence["components"]["breakout volume"]["score"]
        dbl_break = dbl.volume_evidence["components"]["breakout volume"]["score"]
        assert inv_break < dbl_break, (
            f"inverse H&S breakout component {inv_break} was not punished harder "
            f"than the double bottom's {dbl_break}"
        )


# ---------------------------------------------------------------------------
# FR-EM-V3 still governs the breakout component
# ---------------------------------------------------------------------------

class TestAsymmetryStillHoldsPerComponent:
    def test_a_bearish_breakout_component_is_never_penalised(self):
        """V5 adds formation conditions that *can* penalise a bearish pattern,
        which is correct — `FR-EM-V3` is about the **breakout**, not about the
        formation. So the invariant is asserted on the breakout component."""
        for frame_name, pattern in (("hs_top", "Head and Shoulders"),
                                    ("double_top", "Double Top")):
            for planted in (_by_name(planted_frames(), frame_name),
                            _by_name(adverse_frames(), frame_name)):
                match = single_match(planted.frame, pattern)
                component = match.volume_evidence["components"]["breakout volume"]
                assert component["score"] >= 0.5, (
                    f"{frame_name}: a downside break was penalised on volume "
                    f"grounds — 'they can fall of their own weight' (Ch 7)"
                )


# ---------------------------------------------------------------------------
# Unknown stays neutral, and the composition stays bounded
# ---------------------------------------------------------------------------

class TestUnavailabilityAndBounds:
    @pytest.mark.parametrize("frame_name,pattern", PAIRS, ids=[p[0] for p in PAIRS])
    def test_no_volume_column_is_neutral_for_every_reversal_rule(self, frame_name, pattern):
        frame = _by_name(planted_frames(), frame_name).frame.drop(columns=["volume"])
        match = single_match(frame, pattern)
        assert match.volume_score is None
        assert match.volume_factor == NEUTRAL_FACTOR
        assert match.confidence == match.geometric_confidence

    @pytest.mark.parametrize("frame_name,pattern", PAIRS, ids=[p[0] for p in PAIRS])
    def test_a_partially_unknown_rule_still_returns_a_verdict(self, frame_name, pattern):
        """`EC-V1`: NULLs on some bars must not void the whole verdict — the
        conditions that can still be read are still evidence."""
        planted = _by_name(planted_frames(), frame_name)
        frame = planted.frame.copy(deep=True)
        volume = frame["volume"].to_numpy(dtype=float).copy()
        volume[: len(volume) // 2] = np.nan       # blank the early history
        frame["volume"] = volume
        match = single_match(frame, pattern)
        # Either a verdict from what remains, or an honest unknown — never a crash
        # and never a 0.0 masquerading as "volume contradicts".
        assert match.volume_score is None or 0.0 <= match.volume_score <= 1.0
        assert match.volume_factor >= 0.5

    @pytest.mark.parametrize("frame_name,pattern", PAIRS, ids=[p[0] for p in PAIRS])
    def test_scores_and_factors_stay_in_range(self, frame_name, pattern):
        for match in (*_textbook_and_adverse(frame_name, pattern),):
            assert 0.0 <= match.volume_score <= 1.0
            assert 0.5 <= match.volume_factor <= 1.15
            assert 0.0 <= match.confidence <= 1.0

    def test_repeated_evaluation_is_identical(self):
        """`H6` determinism over the new composition path."""
        planted = _by_name(planted_frames(), "hs_top")
        match = single_match(planted.frame, "Head and Shoulders")
        assert evaluate_pattern_volume(match, planted.frame) == evaluate_pattern_volume(
            match, planted.frame
        )


# ---------------------------------------------------------------------------
# The registry is the extension point for V6
# ---------------------------------------------------------------------------

class TestTheRegistry:
    def test_the_four_reversal_detectors_are_registered(self):
        """Membership of the whole registry is asserted in
        ``test_volume_consolidation_rules.py`` since V6a added five more
        entries; this keeps V5's own four under test."""
        assert {
            "Head and Shoulders",
            "Inverse Head and Shoulders",
            "Double Top",
            "Double Bottom",
        } <= set(PATTERN_RULES)

    def test_an_unregistered_pattern_falls_back_to_the_generic_breakout_rule(self):
        """The detectors V6b has not reached yet — Gap, Wide-Ranging Day and
        the traps — must keep V4's generic behaviour rather than losing their
        verdict entirely.

        Asked of a match carrying an unregistered name rather than of a real
        detection, so the test keeps testing the fallback as more patterns get
        registered instead of going stale the moment one does.
        """
        planted = _by_name(planted_frames(), "hs_top")
        real = single_match(planted.frame, "Head and Shoulders")
        unregistered = replace(real, pattern_name="Not A Registered Pattern")
        assert unregistered.pattern_name not in PATTERN_RULES

        verdict = evaluate_pattern_volume(unregistered, planted.frame)
        assert verdict.score is not None
        # The generic rule reports a flat breakout verdict, not the nested
        # per-condition evidence a registered rule produces.
        assert "components" not in verdict.evidence
        assert verdict.evidence["condition"] == "breakout volume"

    def test_every_rule_cites_the_book(self):
        for name, rule in PATTERN_RULES.items():
            assert rule.citation.startswith("E&M"), name
            assert isinstance(rule.breakout, (BreakoutRule, type(None))), name
            assert rule.conditions, name

    def test_every_condition_declares_whether_it_is_required(self):
        """"Required" vs "corroborating" is the vocabulary `FR-EM-V5` is
        written in, so it is a field, not a convention."""
        for rule in PATTERN_RULES.values():
            for condition in rule.conditions:
                assert isinstance(condition.required, bool)
                assert isinstance(condition, (SpanRatio, SpanLevel, SpanTrend))
