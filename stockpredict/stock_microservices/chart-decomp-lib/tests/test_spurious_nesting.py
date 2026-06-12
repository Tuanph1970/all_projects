"""B6 — Spurious-nesting null rate (FR-MS-5 / FR-MS-TEST-5).

How often does the multi-scale pipeline report parent→child nesting links on
pure random-walk series, where no genuine nested structure exists? That rate is
the null against which real nesting must be judged: a nesting relationship is
"noteworthy" only when it occurs MORE than this null rate (FR-MS-5).

Mandatory tests (FR-MS-TEST-5):
  ✓ spurious_nesting_fpr is reported and in [0, ∞) (links per surrogate).
  ✓ On pure-noise input, nesting links are NOT flagged noteworthy unless they
    exceed the null rate (and on noise the large majority do not).

Additional properties tested:
  - fpr equals the mean of the per-surrogate link-count array.
  - Determinism: same seed → identical fpr; the result is reproducible.
  - is_nesting_noteworthy gate logic (below / equal / above the null rate).
  - detect_multiscale wires the rate in only when compute_fpr=True.
"""
from __future__ import annotations

import numpy as np
import pytest

from chart_decomp.application.multiscale_pipeline_usecase import detect_multiscale
from chart_decomp.infrastructure.validation.spurious_nesting import (
    SpuriousNestingNull,
    is_nesting_noteworthy,
    spurious_nesting_distribution,
    spurious_nesting_fpr,
)


# ── is_nesting_noteworthy gate ────────────────────────────────────────────────

class TestNoteworthyGate:
    def test_below_rate_not_noteworthy(self):
        assert is_nesting_noteworthy(0, 0.3) is False

    def test_equal_rate_not_noteworthy(self):
        """'no more than the null rate is not noteworthy' (FR-MS-5)."""
        assert is_nesting_noteworthy(2, 2.0) is False

    def test_above_rate_noteworthy(self):
        assert is_nesting_noteworthy(3, 2.0) is True

    def test_zero_rate_any_link_noteworthy(self):
        # If the null never nests, a single real link already exceeds it.
        assert is_nesting_noteworthy(1, 0.0) is True
        assert is_nesting_noteworthy(0, 0.0) is False


# ── Distribution computation ──────────────────────────────────────────────────

class TestDistribution:
    @pytest.fixture(scope="class")
    def dist(self) -> SpuriousNestingNull:
        return spurious_nesting_distribution(
            length=220, volatility=0.012, scales=(1, 2),
            n_null=30, seed=0,
        )

    def test_reported_and_in_range(self, dist):
        """MANDATORY: fpr is a finite float in [0, ∞)."""
        assert isinstance(dist.fpr, float)
        assert np.isfinite(dist.fpr)
        assert dist.fpr >= 0.0

    def test_link_counts_shape(self, dist):
        assert dist.link_counts.shape == (30,)
        assert (dist.link_counts >= 0).all()

    def test_fpr_is_mean_of_counts(self, dist):
        assert dist.fpr == pytest.approx(float(dist.link_counts.mean()))

    def test_pct95_in_range(self, dist):
        assert dist.link_counts.min() <= dist.pct95 <= dist.link_counts.max()

    def test_determinism_same_seed(self):
        a = spurious_nesting_distribution(length=220, volatility=0.012,
                                          scales=(1, 2), n_null=20, seed=3)
        b = spurious_nesting_distribution(length=220, volatility=0.012,
                                          scales=(1, 2), n_null=20, seed=3)
        assert a.fpr == b.fpr
        np.testing.assert_array_equal(a.link_counts, b.link_counts)

    def test_fpr_helper_matches_distribution(self):
        d = spurious_nesting_distribution(length=200, volatility=0.012,
                                          scales=(1, 2), n_null=20, seed=5)
        f = spurious_nesting_fpr(length=200, volatility=0.012,
                                 scales=(1, 2), n_null=20, seed=5)
        assert f == d.fpr


# ── MANDATORY: noise is not flagged noteworthy unless above the null rate ──────

class TestNoiseNotNoteworthy:
    def test_majority_of_noise_not_noteworthy(self):
        """On pure noise, the per-surrogate link count rarely exceeds the mean
        null rate — the noteworthy gate flags only a minority (the right tail)."""
        dist = spurious_nesting_distribution(
            length=240, volatility=0.012, scales=(1, 2, 3),
            n_null=40, seed=1,
        )
        flagged = [c for c in dist.link_counts
                   if is_nesting_noteworthy(int(c), dist.fpr)]
        # By the gate's definition no surrogate at/below the rate is flagged …
        for c in dist.link_counts:
            assert is_nesting_noteworthy(int(c), dist.fpr) == (c > dist.fpr)
        # … and on noise the flagged set is a minority.
        assert len(flagged) < len(dist.link_counts) / 2

    def test_zero_link_surrogates_never_noteworthy(self):
        dist = spurious_nesting_distribution(
            length=240, volatility=0.012, scales=(1, 2, 3),
            n_null=40, seed=1,
        )
        for c in dist.link_counts:
            if c == 0:
                assert not is_nesting_noteworthy(int(c), dist.fpr)


# ── Integration with detect_multiscale ────────────────────────────────────────

class TestIntegration:
    def test_not_computed_when_compute_fpr_false(self):
        rng = np.random.default_rng(0)
        x = 100.0 + np.cumsum(rng.normal(0, 0.012, 240))
        res = detect_multiscale(x, scales=(1, 2), compute_fpr=False)
        assert res.spurious_nesting_fpr == 0.0

    @pytest.mark.slow
    def test_populated_when_compute_fpr_true(self):
        """MANDATORY (integration): detect_multiscale reports the null rate."""
        rng = np.random.default_rng(0)
        x = 100.0 + np.cumsum(rng.normal(0, 0.012, 240))
        res = detect_multiscale(x, scales=(1, 2), compute_fpr=True,
                                n_null=20, seed=42)
        assert isinstance(res.spurious_nesting_fpr, float)
        assert np.isfinite(res.spurious_nesting_fpr)
        assert res.spurious_nesting_fpr >= 0.0

    @pytest.mark.slow
    def test_observed_links_gated_by_null_rate(self):
        """On a random-walk (null) input, the observed nesting in the series'
        OWN result is judged against the reported null rate; noise must not be
        spuriously flagged as noteworthy unless it genuinely exceeds the rate."""
        rng = np.random.default_rng(2)
        x = 100.0 + np.cumsum(rng.normal(0, 0.012, 240))
        res = detect_multiscale(x, scales=(1, 2, 3), compute_fpr=True,
                                n_null=30, seed=7)
        observed = sum(1 for d in res.detections if d.parent_id is not None)
        noteworthy = is_nesting_noteworthy(observed, res.spurious_nesting_fpr)
        assert noteworthy == (observed > res.spurious_nesting_fpr)
