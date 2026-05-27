"""Use-case: Estimate Hurst exponent via wavelet variance."""
from __future__ import annotations

import numpy as np

from chart_decomp.domain.entities import HurstResult
from chart_decomp.domain.value_objects import HurstParams, TimeSeries
from chart_decomp.infrastructure.long_memory.wavelet_hurst import WaveletHurstEstimator


class EstimateHurstUseCase:
    def __init__(self) -> None:
        self._estimator = WaveletHurstEstimator()

    def execute(self, x: np.ndarray, params: HurstParams | None = None) -> HurstResult:
        """Estimate H for series x.

        x      : raw 1-D series (log-price, log-RV, etc.)
        params : HurstParams; uses defaults if None
        """
        series = TimeSeries(x, min_length=64)
        return self._estimator.estimate(series, params or HurstParams())
