"""T7 — end-to-end: measure_event_reaction -> cross_sectional_exposure (SRS §5.5)."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from event_reaction.cross_section import cross_sectional_exposure
from event_reaction.pipeline import measure_event_reaction


def _fixed_prior():
    sp = np.array([0.1, -0.2, 0.3, -0.1, 0.15, 0.05, -0.25])
    prior = pd.DataFrame({"actual": sp, "consensus": np.zeros_like(sp)})
    return prior, float(np.std(sp, ddof=1))


def _build_event(rng, raw, g1, n=300, p=200, noise=0.0003):
    idx = pd.date_range("2022-01-03", periods=n, freq="B", tz="UTC")
    rm = rng.normal(0.0, 0.01, n - 1)
    ra = 1.0 * rm + rng.normal(0.0, noise, n - 1)
    scale = _fixed_prior()[1]
    ra[p - 1] += g1 * (raw / scale)  # inject abnormal bump = g1 * standardised surprise
    market = pd.Series(100 * np.exp(np.concatenate([[0.0], np.cumsum(rm)])), index=idx)
    asset = pd.Series(100 * np.exp(np.concatenate([[0.0], np.cumsum(ra)])), index=idx)
    event = pd.Series(
        {"event_id": "e", "ts_utc": idx[p], "kind": "rate_decision", "actual": raw, "consensus": 0.0}
    )
    return event, asset, market, idx[p]


class TestEndToEnd:
    def test_measure_populates_full_event_reaction(self, rng):
        event, asset, market, _ = _build_event(rng, raw=0.4, g1=0.02)
        prior, _ = _fixed_prior()
        er = measure_event_reaction(event, asset, market, prior_same_kind=prior)
        assert er.aligned.t0_index == 199
        assert er.surprise.method == "consensus"
        assert isinstance(er.jump.is_jump, bool)
        assert er.abnormal.car == pytest.approx(0.02 * er.surprise.s, abs=2e-3)

    def test_pipeline_recovers_exposure(self, rng):
        """MANDATORY e2e: feed measure outputs into the exposure regression -> gamma1."""
        prior, scale = _fixed_prior()
        g1 = 0.02
        raws = np.linspace(-2, 2, 12) * scale  # spread of surprises
        rows = []
        for j, raw in enumerate(raws):
            event, asset, market, date = _build_event(rng, raw=float(raw), g1=g1)
            er = measure_event_reaction(event, asset, market, prior_same_kind=prior)
            rows.append(
                {"asset": f"A{j}", "event_date": date, "surprise": er.surprise.s, "car": er.abnormal.car}
            )
        panel = pd.DataFrame(rows)
        out = cross_sectional_exposure(panel, cluster="iid")
        assert out.gamma1 == pytest.approx(g1, abs=5e-3)
