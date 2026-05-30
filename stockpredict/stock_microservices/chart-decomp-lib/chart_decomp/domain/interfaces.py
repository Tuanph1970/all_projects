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
    Detection,
    EMDResult,
    ForecastResult,
    HurstResult,
    MODWTResult,
    SwingSkeleton,
    Swing,
    TimeFreqResult,
    VMDResult,
)
from chart_decomp.domain.value_objects import (
    BacktestParams,
    BivariateSeries,
    CoherenceParams,
    CWTParams,
    DenoiseParams,
    EMDParams,
    EEMDParams,
    HARParams,
    HHTParams,
    HurstParams,
    MODWTParams,
    NullFPRParams,
    SwingParams,
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


# ── Part II — Pattern detection interfaces (SRS §II.4) ───────────────────────


@runtime_checkable
class IDenoiser(Protocol):
    """Strategy interface for Layer-1 wavelet denoising (FR-DN-1)."""

    def denoise(self, series: TimeSeries, params: DenoiseParams) -> np.ndarray:
        ...


@runtime_checkable
class ISwingExtractor(Protocol):
    """Strategy interface for Layer-2a swing extraction (FR-SW-*).

    Implementations MUST use a vetted extrema primitive (L2), not a hand-rolled
    comparison loop, and MUST emit a strictly-alternating H/L pivot list.
    """

    def extract(self, series: TimeSeries, params: SwingParams) -> list[Swing]:
        ...


@runtime_checkable
class IPatternDetector(Protocol):
    """Strategy interface for a single chart-pattern detector (FR-PAT-EXT).

    Adapts the SRS's illustrative ``(piv, kinds, x, params) -> list[Detection]``
    to the project's Protocol style: detectors consume the SwingSkeleton plus
    the underlying (denoised) array and return zero or more Detections.
    The detector registry runs every registered detector and aggregates.
    """

    name: str

    def detect(self, skeleton: SwingSkeleton, x: np.ndarray, params=None) -> list[Detection]:
        ...


@runtime_checkable
class INullEvaluator(Protocol):
    """Strategy interface for the mandatory random-walk null comparison (FR-FPR-1).

    Reports a per-pattern false-positive rate so a detection's significance can
    be judged (L3). This is the pattern-world analogue of the forecasting
    module's HAR benchmark gate (Constraint C4).
    """

    def null_fpr(
        self,
        length: int,
        volatility: float,
        detectors,
        params: NullFPRParams,
    ) -> dict:
        ...
