"""Use-case: Compute time-frequency representation (CWT or HHT)."""
from __future__ import annotations

import numpy as np

from chart_decomp.domain.entities import TimeFreqResult
from chart_decomp.domain.value_objects import CWTParams, HHTParams, TimeSeries
from chart_decomp.infrastructure.time_freq.cwt_analyzer import CWTAnalyzer
from chart_decomp.infrastructure.time_freq.hht_analyzer import HHTAnalyzer


class ComputeTimeFreqUseCase:
    """Orchestrates CWT and HHT time-frequency views.

    Design patterns:
        Facade — exposes two methods (cwt / hilbert) using injected analyzers.
    """

    def __init__(self) -> None:
        self._cwt = CWTAnalyzer()
        self._hht = HHTAnalyzer()

    def cwt(self, x: np.ndarray, params: CWTParams | None = None) -> TimeFreqResult:
        """CWT scalogram with mandatory COI.

        x      : raw 1-D series
        params : CWTParams; uses defaults if None
        """
        series = TimeSeries(x)
        return self._cwt.analyze(series, params or CWTParams())

    def hilbert_spectrum(
        self,
        components: np.ndarray,
        params: HHTParams | None = None,
    ) -> TimeFreqResult:
        """Hilbert spectrum from (K, N) component array (IMFs or MODWT bands).

        components : shape (K, N) — do NOT include residue / approximation.
        params     : HHTParams; uses defaults if None
        """
        return self._hht.analyze(components, params or HHTParams())
