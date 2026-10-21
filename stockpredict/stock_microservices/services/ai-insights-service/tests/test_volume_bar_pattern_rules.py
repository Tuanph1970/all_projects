"""EM-1 / V6b — `FR-EM-V5` rows 10–12: gap, one-day reversal, trap.

The last three detectors, and the three places where volume does something it
does nowhere else in EM-1:

* **Gap** (Ch 12) — volume does not merely score the gap, it **re-labels** it.
  An exhaustion gap is recognised by *"extraordinary volume with price failing
  to advance commensurately"* on the day after, which is a volume rule the
  shipped classifier has no way to express: it sees the same geometry as a
  runaway gap and says *runaway*. This is the only place in EM-1 where a
  `pattern_name` the UI renders changes.
* **Wide-Ranging Day / One-Day Reversal** (Ch 10, 10.1) — needs a **second,
  much longer baseline**. *"Volume exceeding anything for months"* is not a
  statement about the last fifty bars.
* **Trap** (Ch 13, 17.1, 35) — volume's role **inverts**. A genuine break is
  *"nearly always followed by sudden acceleration and a marked volume pickup"*
  after the penetration, so the **absence** of follow-through is the trap's
  signature and *raises* confidence rather than lowering it.

Two open questions from the SRS are settled here, and both answers are
asserted rather than only written down:

**Open question 4 — may volume re-classify a gap?** Yes, and narrowly. Only
the exhaustion case, which is the one the SRS says the current classifier
cannot express; breakaway-versus-runaway stays geometry-driven until the `S2`
sweep has evidence. The original label is preserved in `volume_evidence` so the
change is never silent, and Track F needs to know the label can move.

**Open question 3 — does the One-Day Reversal need a longer baseline?** Yes,
120 bars, and compared against a high **percentile** of that window rather
than its maximum. "Exceeding anything for months" reads as a maximum, but
`EC-V5` requires robustness to a single absurd vendor print, and one bad row in
the trailing window would otherwise suppress every one-day reversal behind it
— permanently, and silently. The 98th percentile of 120 bars is the second or
third heaviest bar: "anything for months" in substance, bounded against one bad
row. Recorded for `S2` to sweep.
"""
from __future__ import annotations

import pytest

from app.services.patterns.volume import (
    GAP_EXHAUSTION_RVOL,
    LONG_BASELINE_WINDOW,
    NEUTRAL_FACTOR,
    PATTERN_RULES,
    BarExtreme,
    SpanLevel,
    reclassify_gap,
)
from tests.volume_harness import bar_pattern_frames, detect_all, single_match

FORMATIONS = [
    ("exhaustion_gap", "Gap"),
    ("one_day_reversal", "Wide-Ranging Day"),
    ("bull_trap", "Bull Trap"),
]


def _frame(name: str, *, textbook: bool = True):
    return next(pf for pf in bar_pattern_frames(textbook=textbook) if pf.name == name)


def _match(name: str, prefix: str, *, textbook: bool = True):
    matches = [
        m for m in detect_all(_frame(name, textbook=textbook).frame)
        if m.pattern_name.startswith(prefix)
    ]
    assert len(matches) == 1, [m.pattern_name for m in matches]
    return matches[0]


def _pair(name: str, prefix: str):
    return _match(name, prefix), _match(name, prefix, textbook=False)


# ---------------------------------------------------------------------------
# Open question 4 — volume re-labels an exhaustion gap
# ---------------------------------------------------------------------------

class TestGapReclassification:
    def test_geometry_alone_calls_the_exhaustion_gap_a_runaway(self):
        """The premise of the whole rule. If the shipped classifier already got
        this right there would be nothing for volume to add, so this records
        that it does not."""
        from app.services.patterns.continuation import GapDetector

        frame = _frame("exhaustion_gap").frame
        raw = GapDetector().detect(frame.drop(columns=["volume"]))
        assert raw.details["gap_type"] == "runaway"

    def test_extraordinary_volume_with_no_follow_through_relabels_to_exhaustion(self):
        match = _match("exhaustion_gap", "Gap")
        assert match.pattern_name == "Gap (exhaustion)"
        assert match.details["gap_type"] == "exhaustion"

    def test_the_original_label_is_preserved_so_the_change_is_never_silent(self):
        """The UI renders `pattern_name`. A label that changes with no record
        of what it was would be indistinguishable from a detector bug."""
        match = _match("exhaustion_gap", "Gap")
        evidence = match.volume_evidence
        assert evidence["reclassified_from"] == "Gap (runaway)"
        assert evidence["reclassified_to"] == "Gap (exhaustion)"
        assert match.details["gap_type_before_volume"] == "runaway"

    def test_relabelling_to_exhaustion_withdraws_the_runaway_objective(self):
        """EM-8 M1 / Backlog #92, second site.

        `continuation.py` emits a measured objective for the **runaway**
        subtype only, because E&M give the halfway rule to that gap alone.
        But this volume rule can turn a runaway into an **exhaustion** gap
        afterwards -- and an exhaustion gap is "a wide gap at the very END of
        a move", so the objective it inherited points the way the move is
        finishing.

        Found by counting subtypes over the deep history: 61 of 488
        exhaustion gaps still carried a target, which is impossible from the
        detector alone. The scope rule has to hold after re-labelling, not
        only at detection.
        """
        match = _match("exhaustion_gap", "Gap")
        assert match.details["gap_type"] == "exhaustion"
        assert match.details["gap_type_before_volume"] == "runaway"

        assert match.measured_move_target is None
        assert match.details["measuring_rule"] == "none"
        assert match.details["measuring_rule_before_volume"] == "runaway_halfway"

    def test_a_genuine_runaway_gap_is_left_alone(self):
        """Same gap, ordinary volume, price carrying on. Re-classification must
        be the exception, not the default."""
        match = _match("exhaustion_gap", "Gap", textbook=False)
        assert match.pattern_name == "Gap (runaway)"
        assert "reclassified_to" not in match.volume_evidence

    def test_reclassification_needs_both_halves_of_the_rule(self):
        """*"Extraordinary volume WITH price failing to advance."* Either alone
        is not an exhaustion gap — heavy volume that carries price is a
        breakaway, and a stall on ordinary volume is just a stall."""
        for frame, expected in (
            (_frame("exhaustion_gap").frame, "Gap (exhaustion)"),
            (_frame("exhaustion_gap", textbook=False).frame, None),
        ):
            # The match has to come from the GEOMETRY-ONLY pass: a match taken
            # from the normal path has already been re-labelled, and
            # reclassify_gap declines to re-label an exhaustion gap twice, so
            # asking it again would always answer None.
            geometric = single_match_gap(frame.drop(columns=["volume"]))
            assert reclassify_gap(geometric, frame) == expected

    def test_a_gap_with_no_volume_is_never_relabelled(self):
        """`EC-V3`: without volume there is no volume evidence, so the label
        must stay exactly where geometry put it."""
        frame = _frame("exhaustion_gap").frame.drop(columns=["volume"])
        matches = [m for m in detect_all(frame) if m.pattern_name.startswith("Gap")]
        assert matches and matches[0].pattern_name == "Gap (runaway)"

    def test_reclassification_is_declared_by_the_rule_not_hardcoded(self):
        """So the dispatcher stays generic and the one detector that re-labels
        says so itself."""
        assert PATTERN_RULES["Gap (runaway)"].reclassify is not None
        assert PATTERN_RULES["Gap (common)"].reclassify is not None
        # Nothing outside the gap family may re-label.
        for name, rule in PATTERN_RULES.items():
            if not name.startswith("Gap ("):
                assert rule.reclassify is None, name


# ---------------------------------------------------------------------------
# Open question 3 — the One-Day Reversal's long baseline
# ---------------------------------------------------------------------------

class TestOneDayReversalLongBaseline:
    def test_a_wide_day_on_extreme_volume_scores_above_one_on_ordinary_volume(self):
        textbook, adverse = _pair("one_day_reversal", "Wide-Ranging Day")
        assert textbook.volume_score > adverse.volume_score

    def test_without_the_volume_it_is_an_ordinary_wide_day_and_scores_low(self):
        adverse = _match("one_day_reversal", "Wide-Ranging Day", textbook=False)
        assert adverse.volume_score < 0.5
        assert adverse.volume_factor < NEUTRAL_FACTOR

    def test_the_condition_uses_the_long_window_not_the_fifty_bar_baseline(self):
        """The whole point of row 11: *"exceeding anything for months"* is not
        a statement about the last fifty bars."""
        condition = next(
            c for c in PATTERN_RULES["Wide-Ranging Day"].conditions
            if isinstance(c, BarExtreme)
        )
        assert condition.window == LONG_BASELINE_WINDOW
        assert condition.window >= 100

    def test_the_comparison_is_a_percentile_not_a_maximum(self):
        """`EC-V5`. A maximum would let one absurd vendor print suppress every
        one-day reversal behind it, permanently and silently — the opposite of
        the robustness the edge case asks for."""
        condition = next(
            c for c in PATTERN_RULES["Wide-Ranging Day"].conditions
            if isinstance(c, BarExtreme)
        )
        assert 90.0 <= condition.percentile < 100.0

    def test_one_absurd_print_in_the_window_does_not_suppress_the_verdict(self):
        """The property the percentile choice exists for."""
        planted = _frame("one_day_reversal")
        clean = single_match(planted.frame, "Wide-Ranging Day")

        bar = clean.key_bars[0]
        frame = planted.frame.copy(deep=True)
        volume = frame["volume"].to_numpy(dtype=float).copy()
        # Planted INSIDE the long window, which is where it could do damage:
        # as the window's maximum it would have raised the reference bar above
        # anything the real series could clear.
        volume[bar - LONG_BASELINE_WINDOW // 2] = 1e10
        frame["volume"] = volume
        dirty = single_match(frame, "Wide-Ranging Day")

        assert dirty.volume_score == pytest.approx(clean.volume_score, abs=0.05), (
            f"one absurd print moved the verdict from {clean.volume_score} to "
            f"{dirty.volume_score} — a maximum-based reference would have"
        )

    def test_the_evidence_names_the_window_it_used(self):
        textbook = _match("one_day_reversal", "Wide-Ranging Day")
        component = next(
            d for label, d in textbook.volume_evidence["components"].items()
            if "months" in label or "anything" in label
        )
        assert component["window"] == LONG_BASELINE_WINDOW
        assert component["value"] is not None


# ---------------------------------------------------------------------------
# Row 12 — the trap, where volume's role inverts
# ---------------------------------------------------------------------------

class TestTrapVolumeInverts:
    def test_a_pierce_with_no_follow_through_volume_confirms_the_trap(self):
        """Backlog #81 set the factor ceiling to neutral, so a confirming
        verdict now withholds a penalty rather than granting a bonus. The
        verdict itself is unchanged, and the discrimination is asserted by
        `test_heavy_follow_through_volume_argues_against_the_trap` below —
        which is where it belongs."""
        textbook = _match("bull_trap", "Bull Trap")
        assert textbook.volume_evidence["verdict"] == "confirms"
        assert textbook.volume_factor == pytest.approx(NEUTRAL_FACTOR)

    def test_heavy_follow_through_volume_argues_against_the_trap(self):
        """The inversion, stated as the thing it inverts: everywhere else in
        EM-1 volume arriving on a break is evidence *for* the pattern. Here it
        is evidence against, because it says the break was real."""
        textbook, adverse = _pair("bull_trap", "Bull Trap")
        assert adverse.volume_score < textbook.volume_score
        assert adverse.volume_factor < NEUTRAL_FACTOR

    def test_the_condition_reads_the_bars_after_the_penetration_not_the_penetration(self):
        """E&M's tell is the absence of **follow-through**. The penetration bar
        itself often carries volume — that is what draws people in — so
        including it would blunt the rule."""
        condition = next(
            c for c in PATTERN_RULES["Bull Trap"].conditions if isinstance(c, SpanLevel)
        )
        assert condition.expect == "low"
        assert condition.start_offset == 1

    def test_both_trap_directions_carry_the_rule(self):
        for name in ("Bull Trap", "Bear Trap"):
            assert name in PATTERN_RULES
            assert any(
                isinstance(c, SpanLevel) and c.expect == "low"
                for c in PATTERN_RULES[name].conditions
            ), name

    def test_the_trap_declares_the_inversion_in_its_note(self):
        """A reader of `trap.py`'s rule would otherwise reasonably assume the
        sign was a mistake."""
        note = PATTERN_RULES["Bull Trap"].unscored_note.lower()
        assert "absence" in note or "without" in note


# ---------------------------------------------------------------------------
# The registry is now complete
# ---------------------------------------------------------------------------

class TestRegistryComplete:
    def test_every_shipped_detector_has_a_rule(self):
        """All twelve. The gap contributes four names because it labels itself
        by class, and the trap two."""
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
            "Gap (common)",
            "Gap (breakaway)",
            "Gap (runaway)",
            "Gap (exhaustion)",
            "Wide-Ranging Day",
            "Bull Trap",
            "Bear Trap",
        }

    @pytest.mark.parametrize("name,prefix", FORMATIONS, ids=[f[0] for f in FORMATIONS])
    def test_scores_and_factors_stay_in_range(self, name, prefix):
        for match in _pair(name, prefix):
            assert 0.0 <= match.volume_score <= 1.0
            assert 0.5 <= match.volume_factor <= 1.15
            assert 0.0 <= match.confidence <= 1.0

    @pytest.mark.parametrize("name,prefix", FORMATIONS, ids=[f[0] for f in FORMATIONS])
    def test_no_volume_column_is_neutral(self, name, prefix):
        frame = _frame(name).frame.drop(columns=["volume"])
        matches = [m for m in detect_all(frame) if m.pattern_name.startswith(prefix)]
        assert matches
        for match in matches:
            assert match.volume_score is None
            assert match.volume_factor == NEUTRAL_FACTOR
            assert match.confidence == match.geometric_confidence

    @pytest.mark.parametrize("name,prefix", FORMATIONS, ids=[f[0] for f in FORMATIONS])
    def test_geometry_is_identical_across_the_pair(self, name, prefix):
        textbook, adverse = _pair(name, prefix)
        assert textbook.geometric_confidence == adverse.geometric_confidence

    def test_the_exhaustion_threshold_is_declared_and_sweepable(self):
        assert GAP_EXHAUSTION_RVOL > 1.0

    def test_the_gap_condition_reads_the_gap_bar_and_not_a_window_around_it(self):
        """A gap is a single-bar event. Read over the default ±3-bar window the
        median is dominated by the six ordinary bars either side, and a gap on
        nine times its baseline scored *neutral* — measured, not hypothetical."""
        condition = next(
            c for c in PATTERN_RULES["Gap (runaway)"].conditions if isinstance(c, SpanLevel)
        )
        assert condition.to_anchor == condition.anchor

        textbook = _match("exhaustion_gap", "Gap")
        adverse = _match("exhaustion_gap", "Gap", textbook=False)
        assert textbook.volume_score > adverse.volume_score
        assert textbook.volume_evidence["components"]["volume on the gap"]["value"] > 5.0


def single_match_gap(frame):
    matches = [m for m in detect_all(frame) if m.pattern_name.startswith("Gap")]
    assert len(matches) == 1, [m.pattern_name for m in matches]
    return matches[0]
