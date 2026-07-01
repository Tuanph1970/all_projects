"""T5 — jumps/ stage: Lee-Mykland daily jump test (FR-JUMP, EC4, EC5).

Mandatory gates: an injected jump is detected (and a calm series is not); the null
FPR on random-walk surrogates is ≈ nominal level.
"""
from __future__ import annotations

import numpy as np
import pytest

from event_reaction.jumps import jump_test_daily


class TestDetection:
    def test_injected_jump_detected(self, rng):
        """MANDATORY: a large event-day return is flagged as a jump."""
        r = rng.normal(0.0, 0.005, 300)
        t0 = 200
        r[t0] = 0.05  # ~10 local sigma
        out = jump_test_daily(r, t0, level=0.01, local_window=21)
        assert out.is_jump is True
        assert abs(out.statistic) > out.threshold
        assert out.sigma_local > 0

    def test_calm_series_not_flagged(self, rng):
        r = rng.normal(0.0, 0.005, 300)
        t0 = 200
        r[t0] = 0.0003  # ~0.06 local sigma — deterministically below threshold
        out = jump_test_daily(r, t0, level=0.01, local_window=21)
        assert out.is_jump is False


class TestNullFPR:
    def test_null_fpr_near_nominal(self, rng):
        """MANDATORY (EC4): empirical jump FPR on gaussian surrogates ≈ level."""
        r = rng.normal(0.0, 0.01, 200)
        out = jump_test_daily(r, 150, level=0.05, local_window=21, n_null=500, seed=1)
        assert out.null_fpr == pytest.approx(0.05, abs=0.03)

    def test_null_fpr_nan_when_not_requested(self, rng):
        r = rng.normal(0.0, 0.01, 200)
        out = jump_test_daily(r, 150, level=0.05, local_window=21)
        assert np.isnan(out.null_fpr)


class TestCausality:
    def test_sigma_local_uses_pre_event_only(self, rng):
        """Mutating post-t0 returns must not change the local vol (EC1)."""
        r = rng.normal(0.0, 0.005, 300)
        t0 = 200
        base = jump_test_daily(r, t0, local_window=21)
        r2 = r.copy()
        r2[t0 + 1:] += 5.0
        after = jump_test_daily(r2, t0, local_window=21)
        assert after.sigma_local == pytest.approx(base.sigma_local)
