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
            "EM-1 H2 before-numbers: the GEOMETRY-ONLY null-FPR of the shipped "
            "chart-pattern detectors, captured at task V3, before task V4 makes "
            "confidence a composite. Do not edit by hand; regenerate with "
            "EM1_REGEN_BASELINE=1 pytest tests/test_volume_null_fpr.py and say "
            "in the commit message why the numbers moved."
        ),
        "requirement": "H2 (docs/SRS_edwards_magee_volume.md §6)",
        "state": "geometry-only — EM-1 V4 not applied",
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
    # The rail that matters: this file IS the before-measurement. Regenerating
    # it from code whose confidence is already a composite would overwrite the
    # geometry-only record with post-V4 numbers and quietly destroy the C4
    # benchmark — the exact failure the V3 task existed to prevent.
    for name, null in payload["nulls"].items():
        assert null["mean_confidence"] == null["mean_geometric"], (
            f"{name}: confidence is no longer geometry-only "
            f"({null['mean_geometric']} -> {null['mean_confidence']}). This file "
            f"is the BEFORE-numbers of the C4 benchmark; regenerating it now "
            f"would overwrite them. Disable the volume layer first, or edit "
            f"deliberately and say why in the commit message."
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
        ``TestTheGateIsUnusable`` below: close to a third of null detections
        sit *exactly* on their own 95th-percentile gate, because confidence
        here is heavily quantised (each gap type is a fixed constant, all
        three triangles return 0.82, Double Top/Bottom cap at 0.95). A count
        across that cliff measures where the cliff falls, not what the rule
        does — strict ``>`` reports 2.7% of detections surviving and ``>=``
        reports 31.6%, when a 95th percentile should report 5% either way.

        So the same intent is asserted tie-robustly: on series with no genuine
        price-volume relationship, EM-1 must assign **lower** confidence than
        geometry alone did. The comparison is *paired within one run* — every
        detection carries both its ``geometric_confidence`` and its composite
        ``confidence`` — which is stronger than comparing against a stored
        number and immune to baseline drift.

        The old count is still computed and reported in the failure message,
        so nothing is hidden by the change of statistic.
        """
        baseline = _load_baseline()
        thresholds = {
            name: null["confidence_pct95_by_pattern"]
            for name, null in baseline["nulls"].items()
        }
        failures: List[str] = []
        for report in _build_reports(thresholds):
            was = baseline["nulls"][report.null_name]["n_surviving"]
            if report.mean_confidence >= report.mean_geometric:
                failures.append(
                    f"{report.null_name}: EM-1 did not lower the confidence it "
                    f"assigns to noise — geometric mean {report.mean_geometric} -> "
                    f"composite mean {report.mean_confidence}. "
                    f"(fixed-gate survivor count, reported not asserted: "
                    f"{was} -> {report.n_surviving}, of which "
                    f"{report.n_tied_at_gate} geometry-only readings tie the gate)"
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
class TestTheGateIsUnusable:
    """Why `H2`'s survivor-count requirement had to be restated.

    This is a finding about the **shipped detectors**, not about EM-1, and it
    is carried as a test rather than a comment for a specific reason: if some
    later task de-quantises the confidences, this test fails, and whoever sees
    it should restore the count metric above — which is the better measure the
    moment the data can support it.
    """

    def test_a_large_share_of_null_detections_tie_their_own_gate(self):
        baseline = _load_baseline()
        thresholds = {
            name: null["confidence_pct95_by_pattern"]
            for name, null in baseline["nulls"].items()
        }
        for report in _build_reports(thresholds):
            share = report.n_tied_at_gate / report.n_detections_total
            assert share > 0.1, (
                f"{report.null_name}: only {share:.1%} of null detections tie "
                f"their gate. If the confidences have been de-quantised, the "
                f"survivor-count metric in TestEM1DoesNotWorsenTheNull is now "
                f"well-posed and should be restored."
            )

    def test_the_quantisation_is_visible_in_the_percentiles_themselves(self):
        """Three triangles returning one identical 95th percentile is not a
        coincidence — it is three detectors emitting the same constant."""
        baseline = _load_baseline()
        for null in baseline["nulls"].values():
            pct95 = null["confidence_pct95_by_pattern"]
            triangles = [
                pct95[k] for k in
                ("Ascending Triangle", "Descending Triangle") if k in pct95
            ]
            assert len(set(triangles)) == 1, triangles
