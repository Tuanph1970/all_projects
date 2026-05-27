"""CD-505 (partial) — Forecasting unit tests.

Tests HAR walk-forward structure, metric outputs, and basic sanity.
Full Heston SV end-to-end test is in test_e2e_heston.py (marked slow).
"""
from __future__ import annotations

import numpy as np
import pytest

import chart_decomp as cd
from chart_decomp.domain.exceptions import InsufficientDataError
from chart_decomp.domain.value_objects import HARParams


def _fake_log_rv(N: int = 600, seed: int = 0) -> np.ndarray:
    """AR(1)-like log-RV series."""
    rng = np.random.default_rng(seed)
    x = np.zeros(N)
    for t in range(1, N):
        x[t] = 0.9 * x[t - 1] + rng.normal(0, 0.3)
    return x - 10.0  # roughly log(daily var)


class TestHARForecast:
    def test_output_types(self):
        log_rv = _fake_log_rv(400)
        result = cd.har_forecast(log_rv)
        assert isinstance(result.predictions, np.ndarray)
        assert isinstance(result.actuals, np.ndarray)
        assert isinstance(result.metrics, dict)

    def test_predictions_align_with_actuals(self):
        """predictions[i] is the forecast for actuals[i]; same shape."""
        log_rv = _fake_log_rv(500)
        result = cd.har_forecast(log_rv)
        assert len(result.predictions) == len(result.actuals)
        assert len(result.timestamps) == len(result.predictions)

    def test_metrics_keys_present(self):
        log_rv = _fake_log_rv(400)
        result = cd.har_forecast(log_rv)
        for key in ("rmse", "mae", "r2", "qlike"):
            assert key in result.metrics, f"Missing metric: {key}"
            assert np.isfinite(result.metrics[key])

    def test_r2_reasonable_on_ar1(self):
        """AR(1) log-RV should give positive R² for HAR."""
        log_rv = _fake_log_rv(600)
        result = cd.har_forecast(log_rv)
        assert result.metrics["r2"] > 0.0, (
            f"HAR R²={result.metrics['r2']:.3f} expected > 0 on autocorrelated series"
        )

    def test_short_series_raises(self):
        with pytest.raises((InsufficientDataError, Exception)):
            cd.har_forecast(np.zeros(10))

    def test_feature_names_documented(self):
        log_rv = _fake_log_rv(400)
        result = cd.har_forecast(log_rv)
        assert len(result.features_used) == 3


class TestRealizedVol:
    def test_2d_input(self):
        rng = np.random.default_rng(99)
        intraday = rng.normal(0, 0.001, (100, 78))  # 100 days, 78 intraday
        rv, vol, log_rv = cd.realized_variance(intraday)
        assert rv.shape == (100,)
        assert np.all(rv >= 0)
        assert np.all(np.isfinite(log_rv))

    def test_1d_warns(self):
        """1-D input warns about high-noise estimator."""
        rng = np.random.default_rng(1)
        daily = rng.normal(0, 0.01, 100)
        with pytest.warns(UserWarning, match="high-noise"):
            rv, vol, log_rv = cd.realized_variance(daily)
        assert rv.shape == (100,)


class TestBacktest:
    def test_metrics_keys(self):
        rng = np.random.default_rng(7)
        N = 300
        returns = rng.normal(0, 0.01, N)
        vol_fc = np.full(N, 0.16)  # constant 16% vol forecast
        result = cd.vol_target_backtest(returns, vol_fc)
        for key in ("ann_ret", "ann_vol", "sharpe", "maxdd", "avg_leverage"):
            assert key in result.metrics

    def test_position_clipped_to_max_leverage(self):
        N = 200
        returns = np.ones(N) * 0.01
        vol_fc = np.full(N, 0.001)  # tiny vol → huge raw position
        result = cd.vol_target_backtest(returns, vol_fc, max_leverage=3.0)
        assert np.all(np.abs(result.positions) <= 3.0 + 1e-9)
