"""T4 — returns/ stage: market-model abnormal returns + CAR (FR-AR, EC4).

Mandatory gate: a known CAR is recovered from an injected abnormal bump.
"""
from __future__ import annotations

import numpy as np
import pytest

from event_reaction.returns import abnormal_returns


def _clean_model(rng, n=300, alpha=0.0002, beta=1.1, noise=0.0):
    rm = rng.normal(0.0, 0.01, n)
    ri = alpha + beta * rm + (rng.normal(0.0, noise, n) if noise else 0.0)
    return ri, rm


class TestRecovery:
    def test_recovers_alpha_beta(self, rng):
        ri, rm = _clean_model(rng, noise=0.002)
        out = abnormal_returns(ri, rm, est_window=(50, 250), event_window=(260, 261))
        assert out.beta == pytest.approx(1.1, abs=0.05)
        assert out.alpha == pytest.approx(0.0002, abs=0.001)

    def test_known_car_recovered(self, rng):
        """MANDATORY: inject a known bump δ at the event day -> CAR ≈ δ."""
        ri, rm = _clean_model(rng, noise=0.0)  # noiseless -> exact
        t0, delta = 250, 0.03
        ri = ri.copy()
        ri[t0] += delta
        out = abnormal_returns(ri, rm, est_window=(50, 240), event_window=(t0, t0 + 1))
        assert out.car == pytest.approx(delta, abs=1e-9)
        assert out.ar[0] == pytest.approx(delta, abs=1e-9)

    def test_multiday_car_is_sum_of_ar(self, rng):
        ri, rm = _clean_model(rng, noise=0.0)
        t0 = 250
        ri = ri.copy()
        ri[t0 - 1] += 0.01
        ri[t0] += 0.02
        ri[t0 + 1] += 0.005
        out = abnormal_returns(ri, rm, est_window=(50, 240), event_window=(t0 - 1, t0 + 2))
        assert out.car == pytest.approx(out.ar.sum())
        assert out.car == pytest.approx(0.035, abs=1e-9)


class TestNoLeakageOfEventWindow:
    def test_sigma_alpha_beta_use_estimation_only(self, rng):
        """Mutating event-window asset returns must NOT change alpha/beta/sigma_AR."""
        ri, rm = _clean_model(rng, noise=0.002)
        est, ev = (50, 250), (260, 263)
        base = abnormal_returns(ri, rm, est, ev)
        ri2 = ri.copy()
        ri2[260:263] += 5.0  # wild post-estimation mutation
        after = abnormal_returns(ri2, rm, est, ev)
        assert after.alpha == pytest.approx(base.alpha)
        assert after.beta == pytest.approx(base.beta)
        assert after.sigma_ar == pytest.approx(base.sigma_ar)
        assert after.sigma_ar > 0


class TestPlacebo:
    def test_placebo_distribution_length(self, rng):
        ri, rm = _clean_model(rng, noise=0.002)
        est, ev = (50, 250), (260, 263)  # window length 3
        out = abnormal_returns(ri, rm, est, ev)
        assert len(out.placebo_car) == (250 - 50) - 3 + 1
