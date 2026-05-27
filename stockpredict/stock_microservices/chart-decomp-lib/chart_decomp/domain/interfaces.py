"""Domain interfaces (Protocols) for the Strategy pattern.

Each algorithm family (decomposers, analyzers, forecasters) implements one of
these protocols.  The application layer and factories depend only on these
interfaces, never on concrete implementations — making it trivial to swap
algorithms or add new ones without touching callers.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

import numpy as np

from chart_decomp.domain.entities import (
    BacktestResult,
    CoherenceResult,
    EMDResult,
    ForecastResult,
    HurstResult,
    MODWTResult,
    TimeFreqResult,
    VMDResult,
)
from chart_decomp.domain.value_objects import (
    BacktestParams,
    BivariateSeries,
    CoherenceParams,
    CWTParams,
    EMDParams,
    EEMDParams,
    HARParams,
    HHTParams,
    HurstParams,
    MODWTParams,
    TimeSeries,
    VMDHARParams,
    VMDParams,
)


@runtime_checkable
class IDecomposer(Protocol):
    """Strategy interface for all univariate decomposition methods."""

    def decompose(self, series: TimeSeries) -> MODWTResult | EMDResult | VMDResult:
        ...


@runtime_checkable
class IMODWTDecomposer(Protocol):
    def decompose(self, series: TimeSeries, params: MODWTParams) -> MODWTResult:
        ...


@runtime_checkable
class IEMDDecomposer(Protocol):
    def decompose(self, series: TimeSeries, params: EMDParams) -> EMDResult:
        ...

    def decompose_ensemble(self, series: TimeSeries, params: EEMDParams) -> EMDResult:
        ...


@runtime_checkable
class IVMDDecomposer(Protocol):
    def decompose(self, series: TimeSeries, params: VMDParams) -> VMDResult:
        ...


@runtime_checkable
class ITimeFreqAnalyzer(Protocol):
    """Strategy interface for time-frequency views (CWT, HHT)."""

    def analyze(self, series: TimeSeries) -> TimeFreqResult:
        ...


@runtime_checkable
class ICWTAnalyzer(Protocol):
    def analyze(self, series: TimeSeries, params: CWTParams) -> TimeFreqResult:
        ...


@runtime_checkable
class IHHTAnalyzer(Protocol):
    def analyze(self, components: np.ndarray, params: HHTParams) -> TimeFreqResult:
        """Compute Hilbert spectrum from an (K, N) array of components (IMFs or bands)."""
        ...


@runtime_checkable
class IHurstEstimator(Protocol):
    """Strategy interface for long-memory estimation."""

    def estimate(self, series: TimeSeries, params: HurstParams) -> HurstResult:
        ...


@runtime_checkable
class ICoherenceAnalyzer(Protocol):
    """Strategy interface for bivariate wavelet coherence."""

    def analyze(self, pair: BivariateSeries, params: CoherenceParams) -> CoherenceResult:
        ...


@runtime_checkable
class IForecaster(Protocol):
    """Strategy interface for walk-forward volatility forecasters.

    Causality contract: implementations MUST NOT access log_rv[t+1] or later
    when computing the prediction for time t.  See Constraint C1 and NFR-R2.
    """

    def forecast(self, log_rv: np.ndarray) -> ForecastResult:
        ...


@runtime_checkable
class IBacktester(Protocol):
    """Strategy interface for strategy backtesting."""

    def run(
        self,
        returns: np.ndarray,
        vol_forecast: np.ndarray,
        params: BacktestParams,
    ) -> BacktestResult:
        ...
