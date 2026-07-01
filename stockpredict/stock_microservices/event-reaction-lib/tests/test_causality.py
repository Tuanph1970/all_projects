"""T7 — causality: no-leakage guard + look-ahead tripwire (FR-NOLEAK, EC1).

Mandatory gate: mutating post-event data must NOT change a surprise (nor alpha/beta,
sigma_AR, sigma_local, CAR).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from event_reaction.exceptions import LeakageError
from event_reaction.pipeline import assert_no_leakage, measure_event_reaction
from event_reaction.returns import abnormal_returns


def _prices(rng, n=400, start="2022-01-03"):
    idx = pd.date_range(start, periods=n, freq="B", tz="UTC")
    rm = rng.normal(0.0, 0.01, n - 1)
    ra = 1.0 * rm + rng.normal(0.0, 0.002, n - 1)
    market = pd.Series(100 * np.exp(np.concatenate([[0.0], np.cumsum(rm)])), index=idx)
    asset = pd.Series(100 * np.exp(np.concatenate([[0.0], np.cumsum(ra)])), index=idx)
    return asset, market, idx


class TestNoLeakage:
    def test_mutating_post_event_data_changes_nothing(self, rng):
        """MANDATORY: assert_no_leakage passes (post-event mutation is inert)."""
        asset, market, idx = _prices(rng)
        event = pd.Series(
            {"event_id": "e1", "ts_utc": idx[201], "kind": "k", "actual": 0.5, "consensus": 0.2}
        )
        # Must not raise.
        assert_no_leakage(event, asset, market)

    def test_pre_event_quantities_are_identical_after_mutation(self, rng):
        asset, market, idx = _prices(rng)
        event = pd.Series(
            {"event_id": "e1", "ts_utc": idx[201], "kind": "k", "actual": 0.5, "consensus": 0.2}
        )
        base = measure_event_reaction(event, asset, market)
        t0 = base.aligned.t0_index
        asset2 = asset.copy()
        asset2.iloc[t0 + 4:] *= 1.5  # wild post-event-window mutation
        after = measure_event_reaction(event, asset2, market)
        assert after.abnormal.alpha == pytest.approx(base.abnormal.alpha)
        assert after.abnormal.beta == pytest.approx(base.abnormal.beta)
        assert after.abnormal.sigma_ar == pytest.approx(base.abnormal.sigma_ar)
        assert after.jump.sigma_local == pytest.approx(base.jump.sigma_local)
        assert after.surprise.s == pytest.approx(base.surprise.s)


class TestLookAheadTripwire:
    def test_noncausal_window_leaks_while_causal_does_not(self, rng):
        """A non-causal estimation window (placed AFTER t0) is sensitive to post-event
        mutation; the causal (pre-t0) window is not — the regression guard for EC1."""
        rm = rng.normal(0.0, 0.01, 400)
        ri = 1.0 * rm + rng.normal(0.0, 0.002, 400)
        t0 = 200
        ev = (t0 - 1, t0 + 2)
        causal_est = (50, 190)      # ends before t0 (correct)
        noncausal_est = (210, 350)  # begins after t0 (leaks future data)

        ri_mut = ri.copy()
        ri_mut[t0 + 5:] += 0.05     # mutate post-event returns

        causal_base = abnormal_returns(ri, rm, causal_est, ev)
        causal_after = abnormal_returns(ri_mut, rm, causal_est, ev)
        noncausal_base = abnormal_returns(ri, rm, noncausal_est, ev)
        noncausal_after = abnormal_returns(ri_mut, rm, noncausal_est, ev)

        # Causal fit is invariant to post-event mutation...
        assert causal_after.alpha == pytest.approx(causal_base.alpha)
        assert causal_after.beta == pytest.approx(causal_base.beta)
        # ...the non-causal fit is NOT (it used the mutated future).
        assert abs(noncausal_after.alpha - noncausal_base.alpha) > 1e-4
