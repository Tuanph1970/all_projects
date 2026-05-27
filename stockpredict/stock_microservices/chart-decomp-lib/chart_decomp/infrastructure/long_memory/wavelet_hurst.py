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

import numpy as np
import pywt

from chart_decomp.domain.entities import HurstResult
from chart_decomp.domain.exceptions import InsufficientDataError
from chart_decomp.domain.value_objects import HurstParams, TimeSeries
from chart_decomp.infrastructure.decomposition.modwt_decomposer import MODWTDecomposer
from chart_decomp.domain.value_objects import MODWTParams


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
