"""EM-1 / V3 — `H2`, the local null-FPR harness.

`H2` of `docs/SRS_edwards_magee_volume.md` §6 asks how often the shipped
detectors fire on series that contain nothing: random-walk OHLCV matched in
length and volatility to a real target, with volume drawn independently of
price. The requirement is that EM-1 **shall not increase**
detections-per-surrogate and **shall reduce** the count of detections that
survive a confidence threshold set at the surrogate 95th percentile.

Why this harness is local
-------------------------
``chart-decomp-lib`` already has a null-FPR evaluator, but it is a different
package operating on a bare close series, while these detectors consume an
OHLCV frame and — after V4 — a price-volume relationship. Importing across the
two would mean adapting a frame interface to a series one, so `H2` is
deliberately implemented here. The one thing it does borrow is the
significance convention: strict ``>`` against the null's 95th percentile, and
"never fired on the null" counting as unconditionally significant, exactly as
``null_fpr.is_noteworthy`` defines it.

The two nulls
-------------
A price-volume rule needs a volume process for its null, and inventing one is
itself a modelling choice — the SRS records this as a real limitation. So every
number here is reported under both a parametric synthetic process and a
non-parametric block bootstrap, and the requirement has to hold under both or
the result is an artefact of one generator.

**What this task is for.** The numbers committed in
``tests/baselines/em1_null_fpr_geometry_only.json`` are the *before*-half of
the `C4` benchmark, captured while ``confidence`` is still geometry-only. Task
`V4` changes ``confidence``; without these recorded first, "volume improved
detection" would be unfalsifiable. Hence this task lands before V4, not after.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pytest

from tests.volume_harness import (
    block_bootstrap_volume,
    detect_all,
    random_walk_ohlcv,
    run_null,
    source_volume_series,
    synthetic_volume,
)

BASELINE_PATH = Path(__file__).parent / "baselines" / "em1_null_fpr_geometry_only.json"

# Null parameters. `volatility` is a plausible daily figure for a liquid VN
# large cap and `length` a typical scan window; both are harness choices, and
# the sweep in task `S2` is where they get varied, not here.
N_SURROGATES = int(os.environ.get("EM1_N_NULL", "200"))
LENGTH = 250
VOLATILITY = 0.015
SEED = 20261012
BLOCK_BARS = 10

#: Backlog #88. The share of the pre-EM-1 survivor count that may remain above
#: the geometry-only gate once volume is applied. Measured at ~0.50 on both
#: nulls (64 -> 34 and 68 -> 33), so 0.80 leaves real headroom while still
#: failing an inert volume layer, which would leave the counts EQUAL.
MAX_SURVIVOR_SHARE = 0.80

#: True when the harness is running with its committed defaults, which is the
#: only configuration the committed baseline describes.
DEFAULT_CONFIG = (
    N_SURROGATES == 200 and not os.environ.get("EM1_VOLUME_FIXTURE")
)


def _build_reports(thresholds_by_null: Dict[str, Dict[str, float]] | None = None):
    """Both nulls, in the order the baseline records them."""
    source, label = source_volume_series()
    specs = [
        ("synthetic_volume_process", None, "synthetic-process"),
        ("block_bootstrap_volume", source, label),
    ]
    out = []
    for name, vol_source, vol_label in specs:
        out.append(run_null(
            name, N_SURROGATES, LENGTH, VOLATILITY,
            seed=SEED,
            volume_source=vol_source,
            volume_source_label=vol_label,
            block_bars=BLOCK_BARS,
            thresholds=(thresholds_by_null or {}).get(name),
        ))
    return out


def _regenerate() -> Dict[str, Any]:
    """Two passes: the first fixes each null's 95th-percentile thresholds, the
    second counts how many detections clear them.

    Two passes rather than one because a survivor count against the run's
    *own* percentile is circular — it returns 5% whatever the detector does.
    The threshold has to be fixed before it can be a benchmark.
    """
    first = _build_reports()
    thresholds = {r.null_name: r.confidence_pct95_by_pattern for r in first}
    second = _build_reports(thresholds)
    return {
        "_comment": (
            "EM-1 H2: the null-FPR of the shipped chart-pattern detectors. "
            "Originally captured at task V3 as the geometry-only BEFORE-numbers "
            "of the C4 benchmark; EM-1 is complete and that comparison is "
            "settled, so the file's role is now a REGRESSION GUARD on the "
            "detectors. The geometric_* fields are always geometry-only, read "
            "from PatternMatch.geometric_confidence, which volume never "
            "touches. Regenerated 2026-10-19 for Backlog #70, which "
            "de-quantised every detector confidence. Do not edit by hand; "
            "regenerate with EM1_REGEN_BASELINE=1 pytest "
            "tests/test_volume_null_fpr.py and say in the commit message why "
            "the numbers moved."
        ),
        "requirement": "H2 (docs/SRS_edwards_magee_volume.md §6)",
        "state": "post-V4 composite + geometry-only columns; post-#70 de-quantised detectors",
        "params": {
            "n_surrogates": N_SURROGATES,
            "length": LENGTH,
            "volatility": VOLATILITY,
            "seed": SEED,
            "block_bars": BLOCK_BARS,
            "significance": "strict > the null's own 95th-percentile confidence, per pattern",
        },
        "nulls": {r.null_name: r.as_dict() for r in second},
    }


def _load_baseline() -> Dict[str, Any]:
    if not BASELINE_PATH.exists():
        pytest.fail(
            f"{BASELINE_PATH} is missing. Regenerate with "
            f"EM1_REGEN_BASELINE=1 pytest {Path(__file__).name}"
        )
    return json.loads(BASELINE_PATH.read_text())


#: Patterns whose NAME EM-1 may legitimately change. `FR-EM-V5` row 10 lets
#: volume re-label a gap — "Gap (runaway)" becomes "Gap (exhaustion)" when
#: extraordinary volume is not followed through (Ch 12) — so per-name counts in
#: this family are not comparable across V6b, while the family's TOTAL is: a
#: re-label moves a detection between classes and never creates or destroys
#: one. Measured on the committed nulls, 2 of 1377 detections are re-labelled.
RELABELLED_FAMILY = "Gap ("


def _collapse_family(counts: Dict[str, float]) -> Dict[str, float]:
    """Sum the re-labellable family into one key, leaving everything else."""
    out: Dict[str, float] = {}
    for key, value in counts.items():
        collapsed = "Gap" if key.startswith(RELABELLED_FAMILY) else key
        out[collapsed] = out.get(collapsed, 0.0) + value
    return out


def _without_family(counts: Dict[str, float]) -> Dict[str, float]:
    return {k: v for k, v in counts.items() if not k.startswith(RELABELLED_FAMILY)}


def _diffs(expected: Dict[str, float], actual: Dict[str, float], tol: float) -> List[str]:
    out: List[str] = []
    for key in sorted(set(expected) | set(actual)):
        want, got = expected.get(key), actual.get(key)
        if want is None or got is None or abs(want - got) > tol:
            out.append(f"{key}: baseline={want} now={got}")
    return out


# ---------------------------------------------------------------------------
# Regeneration — not a test, but it lives here so there is one source of truth
# ---------------------------------------------------------------------------

@pytest.mark.skipif(
    not os.environ.get("EM1_REGEN_BASELINE"),
    reason="set EM1_REGEN_BASELINE=1 to rewrite the committed before-numbers",
)
def test_regenerate_baseline():
    assert DEFAULT_CONFIG, "regenerate only with the committed defaults"
    payload = _regenerate()
    # The rail that matters, restated for the era after EM-1 shipped.
    #
    # It used to require `mean_confidence == mean_geometric`, i.e. that the
    # volume layer was switched off, because this file was then the
    # geometry-only BEFORE-half of the C4 benchmark. EM-1 is complete and that
    # comparison is settled, so the file is now a regression guard — and the
    # old condition can never hold again, which would make the file
    # permanently un-regenerable and so permanently stale.
    #
    # What still has to be protected is that the geometric_* columns are
    # genuinely geometry. `geometric_confidence_of` falls back to `confidence`
    # for matches that predate V4, and a silent fallback would quietly fill
    # those columns with composite numbers. If the two means are identical
    # across every null, that fallback is what happened.
    if all(n["mean_confidence"] == n["mean_geometric"] for n in payload["nulls"].values()):
        raise AssertionError(
            "every null reports mean_confidence == mean_geometric. Either the "
            "volume layer is disabled (fine — say so in the commit), or "
            "geometric_confidence_of() is silently falling back to "
            "`confidence` and the geometry columns are about to be filled "
            "with composite numbers."
        )
    BASELINE_PATH.parent.mkdir(parents=True, exist_ok=True)
    BASELINE_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(f"\nrewrote {BASELINE_PATH}")


# ---------------------------------------------------------------------------
# The before-numbers
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not DEFAULT_CONFIG, reason="baseline describes the committed defaults only")
class TestGeometryOnlyBaseline:
    """The recorded numbers must still be reproducible.

    This is not busywork: these are the figures V4's claim will be measured
    against, so a silent change in the geometry detectors — a tolerance
    tweaked, a swing window moved — must surface as a failure here rather than
    quietly invalidate the benchmark months later.
    """

    def test_reports_match_the_committed_baseline(self):
        baseline = _load_baseline()
        thresholds = {
            name: null["confidence_pct95_by_pattern"]
            for name, null in baseline["nulls"].items()
        }
        problems: List[str] = []
        for report in _build_reports(thresholds):
            want = baseline["nulls"].get(report.null_name)
            if want is None:
                problems.append(f"{report.null_name}: absent from the baseline")
                continue
            # Rates are k/n_surrogates, percentiles are rounded to 6 dp, so an
            # exact match is the expectation and the tolerance only absorbs
            # float representation.
            if abs(want["detections_per_surrogate"] - report.detections_per_surrogate) > 1e-9:
                problems.append(
                    f"{report.null_name}: detections_per_surrogate "
                    f"baseline={want['detections_per_surrogate']} "
                    f"now={report.detections_per_surrogate}"
                )
            # n_surviving is deliberately NOT asserted here. It is counted from
            # the COMPOSITE confidence, which FR-EM-V7 moves on purpose, so
            # asserting it in a geometry-drift guard would make the guard fail
            # by design the moment V4 landed — and the usual fix for that is to
            # delete the guard. It stays in the baseline file as the
            # before-number, and TestEM1DoesNotWorsenTheNull is what compares it.
            # The GEOMETRIC series, not the composite one: FR-EM-V7 moves
            # `confidence` on purpose at V4, so comparing that across the
            # change would fail by design and this test would have to be
            # deleted — which is how a drift guard gets lost. The geometric
            # reading is the thing that must not move.
            # Detection counts: compared with the re-labellable family
            # collapsed, so the comparison measures what it meant to — that
            # the detection SET did not move — rather than how EM-1 names it.
            for line in _diffs(
                _collapse_family(want["detections_by_pattern"]),
                _collapse_family(report.detections_by_pattern),
                1e-9,
            ):
                problems.append(f"{report.null_name}.detections_by_pattern {line}")

            # Geometric percentiles: the family is EXCLUDED rather than
            # collapsed, because a percentile of a union is not a function of
            # the per-class percentiles, so collapsing would be arithmetic
            # rather than a comparison. Every other pattern's geometric
            # reading must still be identical.
            for line in _diffs(
                _without_family(want["geometric_pct95_by_pattern"]),
                _without_family(report.geometric_pct95_by_pattern),
                1e-6,
            ):
                problems.append(f"{report.null_name}.geometric_pct95_by_pattern {line}")

        assert not problems, (
            "the geometry-only null-FPR baseline has drifted:\n  "
            + "\n  ".join(problems)
            + "\n\nIf the detectors changed on purpose, regenerate with "
              "EM1_REGEN_BASELINE=1 and say why in the commit message. If they "
              "did not, something changed the geometry without meaning to."
        )

    def test_the_null_is_not_degenerate(self):
        """A null in which nothing ever fires makes every later claim vacuous,
        and one in which everything fires at the ceiling makes the threshold
        meaningless. Assert the harness sits between those."""
        baseline = _load_baseline()
        for name, null in baseline["nulls"].items():
            assert null["n_detections_total"] > 0, f"{name}: the null never fired"
            assert null["detections_per_surrogate"] > 0.1, name
            assert 0.0 < null["confidence_pct95_overall"] <= 1.0, name
            assert null["n_surviving"] > 0, (
                f"{name}: no detection clears its own null threshold, so the "
                f"gate cannot register an improvement either"
            )

    def test_both_nulls_agree_on_the_order_of_magnitude(self):
        """The point of running two is that a conclusion holding under only
        one would be a property of that generator. They need not match, but a
        large divergence means the volume process is driving the geometry
        result, which would itself be the finding."""
        baseline = _load_baseline()
        rates = [n["detections_per_surrogate"] for n in baseline["nulls"].values()]
        assert max(rates) <= 2.0 * min(rates), (
            f"the two volume nulls disagree materially on detection rate: {rates}"
        )

    def test_report_is_reproducible_from_its_seed(self):
        """`H6` determinism, at the harness level. Without it a baseline
        comparison would be measuring sampling noise."""
        a, b = run_null("r", 25, LENGTH, VOLATILITY, seed=99), \
               run_null("r", 25, LENGTH, VOLATILITY, seed=99)
        assert a.as_dict() == b.as_dict()

    def test_a_different_seed_gives_a_different_draw(self):
        """The mirror of the above: if the seed were ignored, determinism
        would pass trivially."""
        a = run_null("r", 25, LENGTH, VOLATILITY, seed=99)
        b = run_null("r", 25, LENGTH, VOLATILITY, seed=100)
        assert a.n_detections_total != b.n_detections_total or \
               a.confidence_pct95_by_pattern != b.confidence_pct95_by_pattern


# ---------------------------------------------------------------------------
# The nulls have to be valid before their verdict means anything
# ---------------------------------------------------------------------------

class TestNullGeneratorValidity:
    def test_synthetic_volume_is_positive_skewed_and_clustered(self):
        """The three properties that make it a plausible volume process at
        all. Clustering especially: an i.i.d. draw would make a drying-up or
        building span impossible by construction, so the null would be easier
        to beat than reality."""
        v = synthetic_volume(2000, np.random.default_rng(3))
        assert np.all(v > 0)
        assert float(np.mean(v)) > float(np.median(v))          # right-skewed
        log_v = np.log(v)
        lag1 = float(np.corrcoef(log_v[:-1], log_v[1:])[0, 1])
        assert lag1 > 0.4, f"log-volume lag-1 autocorrelation only {lag1:.3f}"

    def test_block_bootstrap_only_emits_values_from_its_source(self):
        """What makes it non-parametric: nothing is invented."""
        source = synthetic_volume(400, np.random.default_rng(5))
        out = block_bootstrap_volume(source, 250, np.random.default_rng(6))
        assert set(np.unique(out)).issubset(set(np.unique(source)))

    def test_block_bootstrap_preserves_clustering_better_than_iid_resampling(self):
        """The reason for blocks rather than single bars, asserted rather than
        asserted-in-a-comment."""
        rng = np.random.default_rng(11)
        source = synthetic_volume(1500, np.random.default_rng(12))
        blocked = block_bootstrap_volume(source, 1200, rng, block_bars=20)
        iid = rng.choice(source, size=1200, replace=True)

        def lag1(x):
            lx = np.log(x)
            return float(np.corrcoef(lx[:-1], lx[1:])[0, 1])

        assert lag1(blocked) > lag1(iid) + 0.2, (
            f"blocked={lag1(blocked):.3f} iid={lag1(iid):.3f}"
        )

    def test_block_bootstrap_is_not_a_copy_of_its_source(self):
        source = synthetic_volume(600, np.random.default_rng(13))
        out = block_bootstrap_volume(source, 600, np.random.default_rng(14), block_bars=10)
        assert not np.array_equal(out, source)

    def test_block_bootstrap_rejects_an_empty_source(self):
        with pytest.raises(ValueError):
            block_bootstrap_volume([], 10, np.random.default_rng(15))

    def test_source_series_says_what_it_actually_is(self):
        """The label is returned, not assumed, because the strength of the
        `H2` claim depends on whether the second null bootstraps real market
        volume or a synthetic stand-in. A harness that silently substituted
        one for the other would overstate its own result."""
        series, label = source_volume_series()
        assert series.size >= 50
        assert np.all(series > 0)
        if os.environ.get("EM1_VOLUME_FIXTURE"):
            assert label.startswith("real:")
        else:
            assert label == "synthetic-source"


# ---------------------------------------------------------------------------
# H2's requirement on EM-1  (pending V4)
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not DEFAULT_CONFIG, reason="compares against the committed baseline")
class TestEM1DoesNotWorsenTheNull:
    """Live since V4 — committed at V3 as xfail(strict) and unmarked when the
    scorer landed.

    A caveat worth carrying forward rather than discovering during V4: at 200
    surrogates only a few dozen detections clear the geometry-only threshold,
    because these detectors' confidences are heavily quantised (every gap type
    is a fixed constant, the triangles all return 0.82, Double Top/Bottom cap
    at 0.95), so ties fall below a strict ``>`` gate. That is enough to see a
    real reduction but not much more. Task `S2`'s sweep should raise
    ``EM1_N_NULL`` before quoting a figure with confidence.
    """

    def test_detections_per_surrogate_does_not_increase(self):
        """`FR-EM-V7` weights confidence and must never gate ``found``, so this
        should hold *exactly*, not approximately. If it moves at all, V4 has
        changed what counts as a detection — which would be a contract break
        against ``PatternPanel.js`` and ``failed_signal.py``."""
        baseline = _load_baseline()
        for report in _build_reports():
            want = baseline["nulls"][report.null_name]["detections_per_surrogate"]
            assert report.detections_per_surrogate <= want + 1e-9, (
                f"{report.null_name}: EM-1 increased detections on the null, "
                f"{want} -> {report.detections_per_surrogate}"
            )

    def test_em1_lowers_the_confidence_it_assigns_to_noise(self):
        """`H2`'s substantive requirement, measured in the one way these
        detectors' scores support.

        The SRS states it as *"reduce the count of detections surviving a
        confidence threshold at the surrogate 95th percentile"*. That count is
        **not measurable on this detector set**, and the reason is recorded in
        **Both statistics are asserted, and the history matters.**

        The count is H2's own wording, but it had to be abandoned at V3:
        confidence was quantised (each gap type a fixed constant, all three
        triangles returning 0.82, Double Top/Bottom capped at 0.95), so close
        to a third of null detections sat *exactly* on their own
        95th-percentile gate. A count across that cliff measured where the
        cliff fell, not what the rule did — strict ``>`` reported 2.7%
        surviving and ``>=`` reported 31.6%, when a 95th percentile should
        report 5% either way.

        Backlog #70 de-quantised the detectors and that cliff is gone — 0% of
        null detections now tie their gate, and a 95th-percentile gate passes
        about 5% where it should (`TestTheGateIsNowUsable`). So the count was
        restored, as #70's note instructed.

        **It then failed for a second, unrelated reason.** Gated on the
        geometry-only percentile, EM-1 moved survivors from 4.6% *up* to
        21.7% — not because it flattered noise on average, but because
        `volume_factor` had a **ceiling of 1.15**, so a lucky volume reading
        on a random walk could be lifted across a bar set without volume.
        `FR-EM-V7`'s deliberate "volume may promote" meeting a threshold
        statistic that never anticipated it. The count was therefore reported
        rather than asserted, and the ceiling logged as Backlog #81.

        **#81 measured it and set the ceiling to neutral**, so volume can only
        discredit: `confidence <= geometric_confidence` for every detection,
        by construction, which `TestTheCeilingMakesTheCountWellPosed` asserts.
        Promotion is now impossible and the count is monotone in the one
        direction that matters, so Backlog #88 restores it here.

        **What the count asserts, and what it cannot.** That direction being
        guaranteed by the bounds makes `<=` a tautology, so it is not what is
        tested. The behavioural claim is a *material* reduction: if the volume
        layer were inert on noise — every factor exactly 1.0 — the two counts
        would be **equal**. Measured, EM-1 roughly halves them (64 -> 34 and
        68 -> 33), so the assertion is a stated margin well below that and far
        above "one detection".

        The tie-robust mean comparison is kept alongside. It reads the whole
        distribution rather than one threshold, and it stays meaningful if a
        future detector re-introduces quantisation.
        """
        baseline = _load_baseline()
        # Gated on the GEOMETRY-ONLY percentiles: the pre-EM-1 world's bar.
        thresholds = {
            name: null["geometric_pct95_by_pattern"]
            for name, null in baseline["nulls"].items()
        }
        failures: List[str] = []
        for report in _build_reports(thresholds):
            # H2's own wording, restored at #88: EM-1 must REDUCE the count of
            # detections surviving the pre-EM-1 bar. A material reduction, for
            # the reason in the docstring — `<=` is arithmetic, `much fewer` is
            # behaviour.
            if report.n_surviving > report.n_surviving_geometric * MAX_SURVIVOR_SHARE:
                failures.append(
                    f"{report.null_name}: EM-1 barely thinned the noise above "
                    f"the geometry-only gate — {report.n_surviving_geometric} "
                    f"-> {report.n_surviving} of {report.n_detections_total}, "
                    f"where at most "
                    f"{report.n_surviving_geometric * MAX_SURVIVOR_SHARE:.0f} "
                    f"was required. An inert volume layer would leave the two "
                    f"counts equal."
                )
            if report.mean_confidence >= report.mean_geometric:
                failures.append(
                    f"{report.null_name}: EM-1 did not lower the confidence it "
                    f"assigns to noise — geometric mean {report.mean_geometric} -> "
                    f"composite mean {report.mean_confidence}. "
                    f"(survivors {report.n_surviving_geometric} -> "
                    f"{report.n_surviving}, of which {report.n_tied_at_gate} "
                    f"tie the gate)"
                )
        assert not failures, failures

    def test_detections_are_unchanged_so_the_comparison_is_paired(self):
        """The within-run comparison above is only a fair pairing if volume
        changed no detection's *existence*. `FR-EM-V7` forbids gating `found`,
        so this must hold exactly — and it is what makes the paired statistic
        legitimate rather than a comparison of two different samples."""
        baseline = _load_baseline()
        for report in _build_reports():
            want = baseline["nulls"][report.null_name]
            assert report.detections_per_surrogate == pytest.approx(
                want["detections_per_surrogate"], abs=1e-9
            ), (
                f"{report.null_name}: the number of detections moved, so volume "
                f"has started gating `found` — FR-EM-V7 forbids that"
            )
            assert _collapse_family(report.detections_by_pattern) == pytest.approx(
                _collapse_family(want["detections_by_pattern"]), abs=1e-9
            ), (
                f"{report.null_name}: the detection set moved, so the paired "
                f"before/after comparison is no longer comparing like with like"
            )

    def test_relabelling_conserves_the_gap_family(self):
        """`FR-EM-V5` row 10 lets volume move a detection between gap classes.
        It must never create or destroy one — that would be gating `found` by
        the back door, and it is the invariant that makes collapsing the family
        a legitimate comparison rather than a convenient one."""
        baseline = _load_baseline()
        for report in _build_reports():
            want = baseline["nulls"][report.null_name]["detections_by_pattern"]
            before = sum(v for k, v in want.items() if k.startswith(RELABELLED_FAMILY))
            after = sum(
                v for k, v in report.detections_by_pattern.items()
                if k.startswith(RELABELLED_FAMILY)
            )
            assert after == pytest.approx(before, abs=1e-9), (
                f"{report.null_name}: the gap family went {before} -> {after}"
            )


@pytest.mark.skipif(not DEFAULT_CONFIG, reason="compares against the committed baseline")
class TestTheGateIsNowUsable:
    """Backlog #70, closed — and the inverse of what this class used to assert.

    It was `TestTheGateIsUnusable`, and it existed to explain why `H2`'s
    survivor-count requirement had been downgraded to a mean comparison: the
    shipped detectors emitted heavily quantised confidences, so a percentile
    gate had nowhere to land. Its failure message said that whoever
    de-quantised them should restore the count. That has happened, so these
    tests now pin the fixed state — if quantisation ever comes back, they fail
    and the count metric above becomes unreliable again.
    """

    def test_almost_no_null_detections_tie_their_own_gate(self):
        """Was 29%. A gate that a third of the sample sits exactly on cannot
        separate anything, and flips between 2.7% and 31.6% on the choice of
        ``>`` versus ``>=``."""
        baseline = _load_baseline()
        thresholds = {
            name: null["confidence_pct95_by_pattern"]
            for name, null in baseline["nulls"].items()
        }
        for report in _build_reports(thresholds):
            share = report.n_tied_at_gate / report.n_detections_total
            assert share < 0.02, (
                f"{report.null_name}: {share:.1%} of null detections tie their "
                f"gate. The detector confidences have re-quantised; the "
                f"survivor-count metric in TestEM1DoesNotWorsenTheNull is no "
                f"longer well-posed."
            )

    def test_a_ninety_fifth_percentile_gate_passes_about_five_percent(self):
        """The property that makes a percentile gate mean what it says. Under
        quantisation this read 2.7% or 31.6% depending on the comparison
        operator; it should be 5% either way."""
        baseline = _load_baseline()
        thresholds = {
            name: null["confidence_pct95_by_pattern"]
            for name, null in baseline["nulls"].items()
        }
        for report in _build_reports(thresholds):
            share = report.n_surviving / report.n_detections_total
            assert 0.03 < share < 0.08, (
                f"{report.null_name}: a 95th-percentile gate passes "
                f"{share:.1%} of detections, which is not 5%"
            )

    def test_the_three_triangles_no_longer_share_one_percentile(self):
        """Three detectors returning one identical 95th percentile was never a
        coincidence — it was three detectors emitting the same constant. They
        measure different geometry and must be able to score differently."""
        baseline = _load_baseline()
        for null in baseline["nulls"].values():
            pct95 = null["geometric_pct95_by_pattern"]
            triangles = [
                pct95[k] for k in
                ("Ascending Triangle", "Descending Triangle", "Symmetrical Triangle")
                if k in pct95
            ]
            assert len(set(triangles)) == len(triangles), triangles

    def test_the_gap_family_no_longer_emits_four_constants(self):
        """Each gap type used to return a single hardcoded number, so a huge
        gap and a marginal one scored identically. Confidence now carries the
        gap's size in ATR units, which is the evidence a gap actually has."""
        baseline = _load_baseline()
        for null in baseline["nulls"].values():
            pct95 = null["geometric_pct95_by_pattern"]
            gaps = [v for k, v in pct95.items() if k.startswith("Gap (")]
            assert len(set(gaps)) == len(gaps), gaps
            assert not any(
                v in (0.58, 0.65, 0.68, 0.70) for v in gaps
            ), f"a hardcoded gap constant survived: {gaps}"


class TestTheCeilingMakesTheCountWellPosed:
    """Backlog #88 — why the survivor count above is interpretable at all.

    `#81` measured that a `volume_factor` ceiling above neutral never raises
    detection power at a fixed false-positive rate, and set it to 1.0. The
    consequence is this invariant: volume can only *discredit*, so a detection
    can never be lifted across a bar that was set without volume.

    That is what makes H2's survivor count monotone in the direction it
    claims. If someone raises the ceiling again, this fails first and names
    the reason — rather than the count silently going back to measuring the
    factor's asymmetry, which is what #70 found and had to work around.
    """

    def test_volume_never_raises_a_detections_confidence(self):
        from app.services.patterns.volume import FACTOR_CEILING, NEUTRAL_FACTOR
        from tests.volume_harness import geometric_confidence_of

        assert FACTOR_CEILING <= NEUTRAL_FACTOR, (
            "the ceiling is above neutral again, so volume can promote a "
            "detection and the survivor-count assertion is no longer sound"
        )

        rng = np.random.default_rng(SEED)
        checked = 0
        for _ in range(40):
            volume = synthetic_volume(LENGTH, rng)
            frame = random_walk_ohlcv(LENGTH, VOLATILITY, volume, rng)
            for match in detect_all(frame):
                checked += 1
                assert float(match.confidence) <= geometric_confidence_of(match) + 1e-9, (
                    f"{match.pattern_name}: volume raised confidence from "
                    f"{geometric_confidence_of(match)} to {match.confidence}"
                )
        assert checked > 50, "too few detections to be a meaningful check"
