"""T6 — cross_section/ stage: exposure regression + clustering (FR-XS, EC2, EC3).

Mandatory gates: the true exposure coefficient is recovered; under same-day
clustering the iid t-test over-rejects while the robust route holds size.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from event_reaction.cross_section import cross_sectional_exposure


def _panel(rng, n_dates=10, per_date=12, g0=0.0, g1=0.5, noise=0.002):
    rows = []
    for d in range(n_dates):
        date = pd.Timestamp("2022-01-03", tz="UTC") + pd.Timedelta(days=d)
        for a in range(per_date):
            s = rng.normal(0.0, 1.0)
            car = g0 + g1 * s + rng.normal(0.0, noise)
            rows.append({"asset": f"A{a}", "event_date": date, "surprise": s, "car": car})
    return pd.DataFrame(rows)


class TestRecovery:
    def test_true_exposure_recovered(self, rng):
        """MANDATORY: recover a planted gamma1."""
        panel = _panel(rng, g1=0.5, noise=0.002)
        out = cross_sectional_exposure(panel, cluster="event_date")
        assert out.gamma1 == pytest.approx(0.5, abs=0.02)
        assert out.n_event_dates == 10

    def test_portfolio_route_recovers(self, rng):
        panel = _panel(rng, g1=0.3, noise=0.002)
        out = cross_sectional_exposure(panel, cluster="portfolio")
        assert out.gamma1 == pytest.approx(0.3, abs=0.1)

    def test_missing_columns_raise(self):
        with pytest.raises(Exception):
            cross_sectional_exposure(pd.DataFrame({"surprise": [1, 2, 3]}))


def _clustered_null_panel(seed, n_dates=30, per_date=15):
    """H0: gamma1=0. Same-day events share a surprise s_d and a common car shock f_d,
    so CAR is unrelated to surprise but correlated within a date (EC3)."""
    rng = np.random.default_rng(seed)
    rows = []
    for d in range(n_dates):
        date = pd.Timestamp("2022-01-03", tz="UTC") + pd.Timedelta(days=d)
        s_d = rng.normal(0.0, 1.0)          # one macro surprise shared by the day's assets
        f_d = rng.normal(0.0, 0.02)         # common same-day car shock (independent of s_d)
        for a in range(per_date):
            car = f_d + rng.normal(0.0, 0.005)   # gamma1_true = 0
            rows.append({"asset": f"A{a}", "event_date": date, "surprise": s_d, "car": car})
    return pd.DataFrame(rows)


class TestClusteringOverRejection:
    def test_iid_over_rejects_robust_holds_size(self):
        """MANDATORY (EC3): iid t-test over-rejects; cluster/portfolio hold nominal size."""
        R = 200
        rej_iid = rej_cluster = rej_port = 0
        for rep in range(R):
            panel = _clustered_null_panel(seed=rep)
            for mode, counter in (("iid", "iid"), ("event_date", "cluster"), ("portfolio", "port")):
                out = cross_sectional_exposure(panel, cluster=mode)
                t = abs(out.gamma1 / out.se_gamma1)
                if t > 1.96:
                    if mode == "iid":
                        rej_iid += 1
                    elif mode == "event_date":
                        rej_cluster += 1
                    else:
                        rej_port += 1
        size_iid = rej_iid / R
        size_cluster = rej_cluster / R
        size_port = rej_port / R
        # The iid test rejects the true null far too often...
        assert size_iid > 0.20
        # ...while the clustering-robust routes stay near the nominal 5%.
        assert size_cluster < 0.12
        assert size_port < 0.12
        assert size_iid > size_cluster
