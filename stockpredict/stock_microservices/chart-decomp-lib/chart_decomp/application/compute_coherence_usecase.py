"""Use-case: Wavelet coherence between two series."""
from __future__ import annotations

import numpy as np

from chart_decomp.domain.entities import CoherenceResult
from chart_decomp.domain.value_objects import BivariateSeries, CoherenceParams
from chart_decomp.infrastructure.coherence.wavelet_coherence import WaveletCoherenceAnalyzer


class ComputeCoherenceUseCase:
    def __init__(self) -> None:
        self._analyzer = WaveletCoherenceAnalyzer()

    def execute(
        self,
        x: np.ndarray,
        y: np.ndarray,
        params: CoherenceParams | None = None,
    ) -> CoherenceResult:
        """Compute R² coherence and phase between x and y.

        x, y   : equal-length 1-D series
        params : CoherenceParams; uses defaults if None
        """
        pair = BivariateSeries(x, y)
        return self._analyzer.analyze(pair, params or CoherenceParams())
