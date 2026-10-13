"""EM-1 / V2 — `H1`, the volume-shuffle harness.

`H1` of `docs/SRS_edwards_magee_volume.md` §6 is the test that separates a real
volume rule from a decorative one, and it is the cheapest possible statement of
the `C4` benchmark that `CLAUDE.md` requires. Permute the ``volume`` column
against price — which leaves volume's marginal distribution exactly intact and
destroys only its alignment with price — then assert two things:

1. mean ``volume_score`` over real detections **falls measurably**, and
2. ``geometric_confidence`` is **bit-identical**.

Property 2 is live and green today. Property 1 cannot be evaluated until task
`V4` adds the scorer, so the tests that need it are marked
``xfail(strict=True, raises=VolumeScorerMissing)``:

* while V4 is pending they fail with that one specific exception type, which is
  *red for the right reason* — and any other failure in them is reported as a
  genuine failure, so the marker cannot hide a broken harness;
* the moment V4 lands they pass, ``strict`` turns the unexpected pass into a
  failure, and the markers must come off. The test cannot be silently
  forgotten, which is the usual fate of a to-do comment.

Why property 2 is worth asserting *now*
---------------------------------------
Today it states the before-half of the benchmark as an executable fact: the
shipped detectors ignore volume completely, so permuting it changes nothing —
not a confidence, not a key bar, not a target. After V4 the same test keeps the
geometry channel honest, because ``geometric_confidence`` must stay the
untouched geometric reading no matter what the volume layer decides.
"""
from __future__ import annotations

from typing import List

import numpy as np
import pytest

from tests.volume_harness import (
    detect_all,
    geometric_confidence_of,
    planted_frames,
    shuffle_volume,
    volume_score_of,
)

SHUFFLE_SEED = 31337

#: How much the mean volume score must fall before we call it "measurably".
#: A property threshold, not a magnitude from the book: it only has to be
#: clearly outside the noise of the scripted frames' lognormal jitter.
MIN_SCORE_DROP = 0.05

#: Frames whose E&M condition is **not** a breakout event, and which V4's
#: generic breakout rule therefore cannot score. Recorded here, named, rather
#: than quietly dropped from the assertion:
#:
#: * ``bull_flag`` — the planted frame ends *inside* the flag, so there is no
#:   penetration to read. Its condition is "volume dries up through the flag"
#:   (Ch 8/11), a span measure, which is `FR-EM-V5` / task V6.
#: * ``symmetrical_triangle`` — ``SymmetricalTriangleDetector`` returns
#:   ``pattern_type="neutral"``, so the direction-aware rule has no direction
#:   to apply. Its condition is "volume diminishes toward the apex", also V6.
#:
#: Both were covered by an xfail(strict) test until **V6a** implemented their
#: span conditions, at which point it XPASSed and the marker came off — which
#: is exactly what strict xfail is for. They stay excluded from the breakout
#: assertion above and are asserted by
#: ``test_consolidation_frames_score_since_v6a`` instead.
CONSOLIDATION_FRAMES = {"bull_flag", "symmetrical_triangle"}


def _signature(matches) -> List[tuple]:
    """Everything a detector asserts about geometry, in a comparable form.

    Compared as a whole rather than field by field, because the claim is that
    the *entire* geometric output is untouched by volume — a test that checked
    only confidence would miss a volume rule that quietly moved a target.
    """
    return [
        (
            m.pattern_name,
            m.pattern_type,
            m.found,
            geometric_confidence_of(m),
            tuple(m.key_bars),
            m.measured_move_target,
            m.neckline,
        )
        for m in matches
    ]


def _mean_volume_score(matches) -> float:
    scores = [s for s in (volume_score_of(m) for m in matches) if s is not None]
    if not scores:
        raise AssertionError(
            "no detection carried a volume_score — the harness measured "
            "nothing, which is a harness failure, not a passing test"
        )
    return float(np.mean(scores))


# ---------------------------------------------------------------------------
# The harness itself has to be sound before its verdict means anything
# ---------------------------------------------------------------------------

class TestHarnessPreconditions:
    def test_every_planted_frame_yields_its_target_pattern(self):
        """If the planted pattern is not detected there are no "real
        detections" to average over, and `H1` would pass vacuously."""
        missing = [
            pf.name
            for pf in planted_frames()
            if pf.target_pattern not in {m.pattern_name for m in detect_all(pf.frame)}
        ]
        assert not missing, f"planted target pattern not detected in: {missing}"

    def test_shuffle_preserves_the_volume_multiset_exactly(self):
        """The whole argument for a permutation is that it changes alignment
        and nothing else — same bars, same share counts, same median, same
        outliers. If that is not exact, the test is measuring a distribution
        change instead."""
        rng = np.random.default_rng(SHUFFLE_SEED)
        for pf in planted_frames():
            shuffled = shuffle_volume(pf.frame, rng)
            assert sorted(shuffled["volume"].tolist()) == sorted(pf.frame["volume"].tolist())

    def test_shuffle_leaves_price_bit_identical(self):
        rng = np.random.default_rng(SHUFFLE_SEED)
        for pf in planted_frames():
            shuffled = shuffle_volume(pf.frame, rng)
            for col in ("open", "high", "low", "close"):
                assert np.array_equal(shuffled[col].to_numpy(), pf.frame[col].to_numpy()), col

    def test_shuffle_actually_reorders_volume(self):
        """Guards the degenerate case: a constant volume column, or a
        permutation that happens to be the identity, would make `H1`
        unfalsifiable. The existing planted fixtures carry ``volume = 1000``
        on every bar, which is exactly why this harness builds its own."""
        rng = np.random.default_rng(SHUFFLE_SEED)
        for pf in planted_frames():
            original = pf.frame["volume"].to_numpy()
            shuffled = shuffle_volume(pf.frame, rng)["volume"].to_numpy()
            moved = int(np.sum(original != shuffled))
            assert moved > len(original) // 4, (
                f"{pf.name}: only {moved}/{len(original)} volume bars moved"
            )

    def test_shuffle_is_reproducible_from_its_seed(self):
        a = shuffle_volume(planted_frames()[0].frame, np.random.default_rng(7))
        b = shuffle_volume(planted_frames()[0].frame, np.random.default_rng(7))
        assert np.array_equal(a["volume"].to_numpy(), b["volume"].to_numpy())


# ---------------------------------------------------------------------------
# H1 property 2 — the geometry channel is invariant under a volume shuffle
# ---------------------------------------------------------------------------

class TestH1GeometryIsInvariant:
    """Live now, and stays live after V4.

    Today this records the before-state of the `C4` benchmark: volume is not
    read at all. After V4 it is `H1`'s second property, and the thing that
    stops the volume layer from leaking into the geometric reading it is
    supposed to be weighting.
    """

    @pytest.mark.parametrize("planted", planted_frames(), ids=lambda pf: pf.name)
    def test_detection_signature_is_bit_identical(self, planted):
        rng = np.random.default_rng(SHUFFLE_SEED)
        before = _signature(detect_all(planted.frame))
        after = _signature(detect_all(shuffle_volume(planted.frame, rng)))
        assert before == after, (
            f"{planted.name}: shuffling volume moved the geometric output. "
            f"Condition under test: {planted.condition} ({planted.citation})."
        )

    def test_invariance_holds_across_many_independent_shuffles(self):
        """One permutation could coincidentally preserve a reading; twenty
        could not. Cheap, and it is the difference between "did not happen"
        and "cannot happen"."""
        rng = np.random.default_rng(SHUFFLE_SEED)
        for pf in planted_frames():
            baseline = _signature(detect_all(pf.frame))
            for trial in range(20):
                after = _signature(detect_all(shuffle_volume(pf.frame, rng)))
                assert after == baseline, f"{pf.name}: diverged on shuffle {trial}"


# ---------------------------------------------------------------------------
# H1 property 1 — the score must care about alignment  (pending V4)
# ---------------------------------------------------------------------------

class TestH1VolumeScoreFallsUnderShuffle:
    """The core evidence test — **live since V4**.

    It was committed at V2 as ``xfail(strict=True, raises=VolumeScorerMissing)``
    and the markers came off when V4's scorer landed, which is what
    ``strict=True`` was there to force.
    """

    def test_mean_volume_score_falls_across_the_planted_set(self):
        rng = np.random.default_rng(SHUFFLE_SEED)
        aligned: List[float] = []
        shuffled: List[float] = []
        for pf in planted_frames():
            aligned.append(_mean_volume_score(detect_all(pf.frame)))
            shuffled.append(_mean_volume_score(detect_all(shuffle_volume(pf.frame, rng))))

        drop = float(np.mean(aligned) - np.mean(shuffled))
        assert drop >= MIN_SCORE_DROP, (
            f"mean volume_score fell by only {drop:.4f} when volume was permuted "
            f"against price (aligned={np.mean(aligned):.4f}, "
            f"shuffled={np.mean(shuffled):.4f}). A score that does not care "
            f"whether volume lines up with price is not measuring what E&M "
            f"describe."
        )

    @pytest.mark.parametrize(
        "planted",
        [pf for pf in planted_frames() if pf.name not in CONSOLIDATION_FRAMES],
        ids=lambda pf: pf.name,
    )
    def test_the_drop_shows_on_the_planted_pattern_itself(self, planted):
        """The aggregate could be carried by incidental detections, so assert
        it where the volume script actually is.

        Parametrised per frame rather than collected into one dict, because
        *which* E&M condition failed to register is the whole diagnostic, and a
        lumped assertion reports only that an average moved. The split also
        makes the scope of V4 explicit: see ``CONSOLIDATION_FRAMES``.
        """
        rng = np.random.default_rng(SHUFFLE_SEED)

        def target_scores(frame):
            return [
                s
                for s in (
                    volume_score_of(m)
                    for m in detect_all(frame)
                    if m.pattern_name == planted.target_pattern
                )
                if s is not None
            ]

        aligned = target_scores(planted.frame)
        shuffled = target_scores(shuffle_volume(planted.frame, rng))
        assert aligned, f"{planted.name}: the planted pattern carried no volume_score"
        assert shuffled, f"{planted.name}: the shuffled frame carried no volume_score"
        assert float(np.mean(aligned)) > float(np.mean(shuffled)), (
            f"{planted.name}: aligned={np.mean(aligned):.4f} did not exceed "
            f"shuffled={np.mean(shuffled):.4f} — {planted.condition} ({planted.citation})"
        )

    def test_unavailable_volume_scores_none_not_zero(self):
        """`FR-EM-V7`: unknown must read as ``None``, never ``0.0``, which
        would be indistinguishable from "volume actively contradicts". Asserted
        here as well as in `H5` because the shuffle averages over scores, and a
        ``0.0`` sentinel would silently drag the mean."""
        no_volume = planted_frames()[0].frame.drop(columns=["volume"])
        for match in detect_all(no_volume):
            assert volume_score_of(match) is None


@pytest.mark.parametrize("name", sorted(CONSOLIDATION_FRAMES))
def test_consolidation_frames_score_since_v6a(name):
    """Was `xfail(strict)` from V4 until V6a implemented the span conditions.

    The debt it recorded is paid: the flag now scores from its mast ratio and
    the symmetrical triangle from its drying trend, so both planted conditions
    register and both respond to the volume being permuted away.
    """
    planted = next(pf for pf in planted_frames() if pf.name == name)
    rng = np.random.default_rng(SHUFFLE_SEED)

    def target_scores(frame):
        return [
            s
            for s in (
                volume_score_of(m)
                for m in detect_all(frame)
                if m.pattern_name == planted.target_pattern
            )
            if s is not None
        ]

    aligned = target_scores(planted.frame)
    assert aligned, f"{name}: no volume_score on the planted pattern"
    shuffled = target_scores(shuffle_volume(planted.frame, rng))
    assert shuffled, f"{name}: no volume_score after the shuffle"
    assert float(np.mean(aligned)) > float(np.mean(shuffled))
