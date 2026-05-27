"""Use-case: Walk-forward volatility forecasting.

Wires together HARForecaster and VMDHARForecaster, and optionally computes the
Diebold-Mariano statistic comparing two ForecastResult objects.
"""
from __future__ import annotations

import numpy as np

from chart_decomp.domain.entities import ForecastResult
from chart_decomp.domain.exceptions import InputValidationError
from chart_decomp.domain.value_objects import HARParams, VMDHARParams
from chart_decomp.infrastructure.forecasting.har_forecaster import HARForecaster
from chart_decomp.infrastructure.forecasting.vmd_har_forecaster import VMDHARForecaster


class RunForecastUseCase:
    """Orchestrates HAR and VMD-HAR forecasters and comparative evaluation.

    Design patterns:
        Facade — single entry point for all forecasting paths.
        Constraint C4: caller should always request both har and vmd_har to
        enable side-by-side comparison before claiming improvement.
    """

    def __init__(self) -> None:
        self._har = HARForecaster()
        self._vmd_har = VMDHARForecaster()

    def har(self, log_rv: np.ndarray, params: HARParams | None = None) -> ForecastResult:
        """HAR baseline walk-forward forecast."""
        log_rv = _validate_log_rv(log_rv)
        return self._har.forecast(log_rv, params)

    def vmd_har(
        self, log_rv: np.ndarray, params: VMDHARParams | None = None
    ) -> ForecastResult:
        """VMD-augmented HAR walk-forward forecast."""
        log_rv = _validate_log_rv(log_rv)
        return self._vmd_har.forecast(log_rv, params)

    @staticmethod
    def diebold_mariano(
        result_a: ForecastResult,
        result_b: ForecastResult,
        *,
        nw_lags: int = 22,
    ) -> float:
        """Compute the Diebold-Mariano test statistic (result_a vs result_b).

        Returns DM > 0 when result_a has smaller squared errors than result_b.
        Uses Newey-West HAC variance with bandwidth >= 22 days (SRS §3.7.3).

        The model is declared "improving" only if |DM| > 1.96 in its favour
        AND ΔRMSE > 0 AND ΔQLIKE > 0 — the caller must verify all three.
        """
        # Align on common timestamps
        ts_a = set(result_a.timestamps.tolist())
        ts_b = set(result_b.timestamps.tolist())
        common = sorted(ts_a & ts_b)
        if len(common) < 30:
            raise InputValidationError(
                f"Need at least 30 common timestamps for DM test; got {len(common)}"
            )

        idx_a = {t: i for i, t in enumerate(result_a.timestamps.tolist())}
        idx_b = {t: i for i, t in enumerate(result_b.timestamps.tolist())}

        e2_a = np.array([(result_a.actuals[idx_a[t]] - result_a.predictions[idx_a[t]]) ** 2
                         for t in common])
        e2_b = np.array([(result_b.actuals[idx_b[t]] - result_b.predictions[idx_b[t]]) ** 2
                         for t in common])

        d = e2_b - e2_a  # positive when a is better
        T = len(d)
        d_bar = d.mean()

        # Newey-West long-run variance
        lag = max(nw_lags, 22)
        gamma0 = np.sum((d - d_bar) ** 2) / T
        nw_var = gamma0
        for h in range(1, lag + 1):
            gamma_h = np.sum((d[h:] - d_bar) * (d[:-h] - d_bar)) / T
            nw_var += 2.0 * (1.0 - h / (lag + 1)) * gamma_h
        nw_var = max(nw_var, 1e-30)

        dm_stat = d_bar / np.sqrt(nw_var / T)
        return float(dm_stat)

    @staticmethod
    def improves_on_har(
        candidate: ForecastResult,
        baseline_har: ForecastResult,
        *,
        nw_lags: int = 22,
    ) -> bool:
        """Return True only when ALL three SRS §3.7.3 conditions pass.

        Constraint C4: always compare against HAR before claiming improvement.
        """
        m_c = candidate.metrics
        m_h = baseline_har.metrics
        if not (m_c and m_h):
            return False
        delta_rmse = m_h["rmse"] - m_c["rmse"]   # positive = candidate is better
        delta_qlike = m_h["qlike"] - m_c["qlike"]

        dm = RunForecastUseCase.diebold_mariano(candidate, baseline_har, nw_lags=nw_lags)
        return bool(delta_rmse > 0 and delta_qlike > 0 and dm > 1.96)


def _validate_log_rv(log_rv: np.ndarray) -> np.ndarray:
    arr = np.asarray(log_rv, dtype=np.float64)
    if arr.ndim != 1:
        raise InputValidationError("log_rv must be a 1-D array")
    if not np.all(np.isfinite(arr)):
        raise InputValidationError("log_rv contains NaN/Inf values")
    return arr
