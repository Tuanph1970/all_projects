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
    VolumeScorerMissing,
    block_bootstrap_volume,
    run_null,
    source_volume_series,
    synthetic_volume,
    volume_score_of,
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
            if want["n_surviving"] != report.n_surviving:
                problems.append(
                    f"{report.null_name}: n_surviving baseline={want['n_surviving']} "
                    f"now={report.n_surviving}"
                )
            for label, tol in (("detections_by_pattern", 1e-9),
                               ("confidence_pct95_by_pattern", 1e-6)):
                for line in _diffs(want[label], getattr(report, label), tol):
                    problems.append(f"{report.null_name}.{label} {line}")

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

@pytest.mark.xfail(
    strict=True,
    raises=VolumeScorerMissing,
    reason="EM-1 task V4 (PatternMatch composition + asymmetry rule) not implemented yet",
)
@pytest.mark.skipif(not DEFAULT_CONFIG, reason="compares against the committed baseline")
class TestEM1DoesNotWorsenTheNull:
    """Red until V4, then it must flip and these markers must come off.

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
        # Ask for the V4 field first, so while V4 is pending this fails with
        # the expected exception type instead of passing vacuously — today the
        # detections are identical because nothing reads volume at all.
        volume_score_of(_any_match())
        for report in _build_reports():
            want = baseline["nulls"][report.null_name]["detections_per_surrogate"]
            assert report.detections_per_surrogate <= want + 1e-9, (
                f"{report.null_name}: EM-1 increased detections on the null, "
                f"{want} -> {report.detections_per_surrogate}"
            )

    def test_fewer_detections_survive_the_geometry_only_threshold(self):
        """The substantive requirement: on series with no genuine price-volume
        relationship, the volume layer should mostly decline to confirm, so
        fewer null detections clear the bar the geometry-only detectors set."""
        baseline = _load_baseline()
        thresholds = {
            name: null["confidence_pct95_by_pattern"]
            for name, null in baseline["nulls"].items()
        }
        volume_score_of(_any_match())
        failures: List[str] = []
        for report in _build_reports(thresholds):
            was = baseline["nulls"][report.null_name]["n_surviving"]
            if report.n_surviving >= was:
                failures.append(
                    f"{report.null_name}: {was} -> {report.n_surviving} survivors "
                    f"(needed a reduction)"
                )
        assert not failures, failures


def _any_match():
    """One real `PatternMatch`, used only to ask whether V4's fields exist.

    A detection rather than a hand-built instance, so the question is asked of
    the object the production path actually returns.
    """
    from tests.volume_harness import detect_all, planted_frames
    matches = detect_all(planted_frames()[0].frame)
    assert matches, "harness precondition: the planted frame must detect something"
    return matches[0]
