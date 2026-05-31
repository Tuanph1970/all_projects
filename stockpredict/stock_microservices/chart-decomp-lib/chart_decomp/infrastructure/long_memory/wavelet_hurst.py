"""Hurst exponent estimator via MODWT wavelet variance (FR-HURST).

Method (Percival & Walden §8.3):
    1. Compute MODWT to maximum level.
    2. For each level j in [j_lo, j_hi]: Var(d_j) = mean(d_j²).
    3. Regress log₂(Var(d_j)) on j over [j_lo, j_hi].
    4. H = (slope + 2) / 2.

The slope of log₂(Var) vs j equals 2H−2 for a long-memory process, hence
H = (slope + 2) / 2.

Validation target: |Ĥ - H_true| ≤ 0.07 on fGn with N=4096 (SRS §5.2).
"""
from __future__ import annotations

import warnings

import numpy as np
import pywt

from chart_decomp.domain.entities import HurstResult
from chart_decomp.domain.exceptions import InsufficientDataError
from chart_decomp.domain.value_objects import HurstParams, MODWTParams, TimeSeries
from chart_decomp.infrastructure.decomposition.modwt_decomposer import MODWTDecomposer

# Stationarity-ratio threshold (FR-HURST / SRS Exp 5).
# std(diff(x)) / std(x) is ≈1.4 for a stationary series and ≈sqrt(2/N) << 1
# for a random-walk price level.  A ratio below _STAT_THRESHOLD suggests
# price-level (non-stationary) input; we warn but do not raise.
_STAT_THRESHOLD = 0.5


def _check_stationarity(x: np.ndarray) -> None:
    """Emit a UserWarning if ``x`` looks non-stationary (FR-HURST / Exp 5).

    A low std(diff(x)) / std(x) ratio signals a drifting price level.
    Hurst on non-stationary input returns biased (too-high) estimates.
    Pass returns (first differences of log-prices) instead.
    """
    std_x = float(np.std(x))
    if std_x < 1e-10:
        return  # constant series — other checks will catch it
    ratio = float(np.std(np.diff(x))) / std_x
    if ratio < _STAT_THRESHOLD:
        warnings.warn(
            f"Input series looks non-stationary (stationarity ratio {ratio:.3f} < "
            f"{_STAT_THRESHOLD}).  FR-HURST requires stationary input (returns / "
            "first differences of log-prices).  Hurst on price levels gives "
            "unreliable, typically inflated estimates.  "
            "Pass np.diff(np.log(prices)) instead of raw prices.",
            UserWarning,
            stacklevel=3,
        )


class WaveletHurstEstimator:
    """Implements IHurstEstimator.

    Design patterns:
        Concrete Strategy.
        Depends on MODWTDecomposer (composition, not inheritance).
    """

    def __init__(self) -> None:
        self._decomposer = MODWTDecomposer()

    def estimate(self, series: TimeSeries, params: HurstParams) -> HurstResult:
        """Estimate the Hurst exponent.

        Parameters
        ----------
        series : TimeSeries
        params : HurstParams (wavelet, j_lo, j_hi)

        Returns
        -------
        HurstResult with Ĥ, slope, intercept, variance array, and scale mask.
        """
        _check_stationarity(series.values)  # FR-HURST non-binding guard (Exp 5)
        N = len(series)
        max_level = pywt.swt_max_level(N)
        J = min(params.j_hi, max_level)

        if params.j_lo >= J:
            raise InsufficientDataError(
                f"j_lo={params.j_lo} >= effective j_hi={J} for series length {N}"
            )

        # Decompose to level J
        modwt_params = MODWTParams(wavelet=params.wavelet, level=J)
        result = self._decomposer.decompose(series, modwt_params)

        # Compute variance of each detail level
        # result.details = [D_1, D_2, ..., D_J] (finest first, index 0 = D_1)
        variances = np.array([float(np.var(d)) for d in result.details])

        # Scale mask: include levels j_lo .. min(j_hi, J)
        # Detail index j_idx corresponds to level j_idx+1
        j_lo_idx = params.j_lo - 1
        j_hi_idx = min(params.j_hi, J) - 1
        scale_mask = np.zeros(J, dtype=bool)
        scale_mask[j_lo_idx : j_hi_idx + 1] = True

        included_levels = np.arange(1, J + 1)[scale_mask]
        included_vars = variances[scale_mask]

        # Guard against zero / negative variance (can happen on constant sub-bands)
        valid = included_vars > 0
        if np.sum(valid) < 2:
            raise InsufficientDataError(
                "Fewer than 2 levels have non-zero variance; "
                "try a longer series or different j_range"
            )
        x_reg = included_levels[valid].astype(np.float64)
        y_reg = np.log2(included_vars[valid])

        slope, intercept = np.polyfit(x_reg, y_reg, 1)
        H = float((slope + 2.0) / 2.0)

        return HurstResult(
            H=H,
            slope=float(slope),
            intercept=float(intercept),
            variances=variances,
            scale_mask=scale_mask,
        )
