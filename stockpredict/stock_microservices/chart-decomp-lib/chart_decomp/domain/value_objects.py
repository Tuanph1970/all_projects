"""Domain value objects — immutable, self-validating wrappers for inputs.

All parameter dataclasses are frozen so they are safe to share across layers.
TimeSeries is the core VO: it validates on construction and exposes the
underlying numpy array as a read-only property.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Literal, Optional

import numpy as np

from chart_decomp.domain.exceptions import InputValidationError


# ── Core time-series value object ─────────────────────────────────────────────

class TimeSeries:
    """Immutable, validated wrapper around a 1-D float64 numpy array.

    Construction validates:
    - Array is 1-D and non-empty
    - dtype is castable to float64
    - No NaN or Inf values
    - Length meets an optional minimum

    Pitfalls:
        Pass already-aligned series; this class does NOT handle missing data,
        holidays, or timezone shifts.
    """

    __slots__ = ("_data",)

    def __init__(self, data: np.ndarray, *, min_length: int = 4) -> None:
        arr = np.asarray(data, dtype=np.float64)
        if arr.ndim != 1:
            raise InputValidationError(
                f"TimeSeries requires a 1-D array; got shape {arr.shape}"
            )
        if len(arr) < min_length:
            raise InputValidationError(
                f"TimeSeries length {len(arr)} < minimum {min_length}"
            )
        if not np.all(np.isfinite(arr)):
            n_bad = int(np.sum(~np.isfinite(arr)))
            raise InputValidationError(
                f"TimeSeries contains {n_bad} NaN/Inf value(s); "
                "pre-process missing data before passing to chart-decomp"
            )
        self._data = arr

    @property
    def values(self) -> np.ndarray:
        return self._data

    def __len__(self) -> int:
        return len(self._data)

    def __repr__(self) -> str:
        return f"TimeSeries(len={len(self._data)}, μ={self._data.mean():.4g})"


class BivariateSeries:
    """Pair of equal-length TimeSeries for bivariate analysis."""

    def __init__(self, x: np.ndarray, y: np.ndarray) -> None:
        self.x = TimeSeries(x)
        self.y = TimeSeries(y)
        if len(self.x) != len(self.y):
            raise InputValidationError(
                f"Both series must have equal length; got {len(self.x)} and {len(self.y)}"
            )

    def __repr__(self) -> str:
        return f"BivariateSeries(len={len(self.x)})"


# ── Parameter value objects ────────────────────────────────────────────────────

@dataclass(frozen=True)
class MODWTParams:
    wavelet: str = "sym8"
    level: int = 6
    boundary: Literal["symmetric", "periodic", "zero"] = "symmetric"

    def __post_init__(self) -> None:
        if self.level < 1:
            raise InputValidationError("MODWT level must be >= 1")


@dataclass(frozen=True)
class EMDParams:
    max_imfs: Optional[int] = None
    stop_tol: float = 1e-3
    max_sift: int = 20
    seed: Optional[int] = None


@dataclass(frozen=True)
class EEMDParams:
    n_trials: int = 100
    noise_width: float = 0.2
    max_imfs: Optional[int] = None
    stop_tol: float = 1e-3
    seed: Optional[int] = None

    def __post_init__(self) -> None:
        if self.n_trials < 1:
            raise InputValidationError("EEMD n_trials must be >= 1")
        if self.noise_width < 0:
            raise InputValidationError("EEMD noise_width must be >= 0")


@dataclass(frozen=True)
class VMDParams:
    K: int = 5
    alpha: float = 1500.0
    tau: float = 0.0
    tol: float = 1e-7
    DC: int = 0
    init: int = 1

    def __post_init__(self) -> None:
        if self.K < 1:
            raise InputValidationError("VMD K must be >= 1")
        if self.alpha <= 0:
            raise InputValidationError("VMD alpha must be > 0")


@dataclass(frozen=True)
class CWTParams:
    scales: Optional[np.ndarray] = None
    wavelet: str = "cmor1.5-1.0"
    sampling_period: float = 1.0

    class Config:
        arbitrary_types_allowed = True


@dataclass(frozen=True)
class HHTParams:
    n_freq_bins: int = 120
    smoothing_sigma: tuple[float, float] = (1.5, 4.0)


@dataclass(frozen=True)
class HurstParams:
    wavelet: str = "db4"
    j_lo: int = 2
    j_hi: int = 8

    def __post_init__(self) -> None:
        if self.j_lo < 1:
            raise InputValidationError("Hurst j_lo must be >= 1")
        if self.j_hi <= self.j_lo:
            raise InputValidationError("Hurst j_hi must be > j_lo")


@dataclass(frozen=True)
class CoherenceParams:
    scales: Optional[np.ndarray] = None
    wavelet: str = "cmor1.5-1.0"
    smoothing_sigma_time: float = 1.0
    smoothing_sigma_scale: float = 0.5

    class Config:
        arbitrary_types_allowed = True


@dataclass(frozen=True)
class HARParams:
    refit_every: int = 60
    ridge_alpha: float = 5.0
    min_train: int = 252

    def __post_init__(self) -> None:
        if self.refit_every < 1:
            raise InputValidationError("refit_every must be >= 1")
        if self.ridge_alpha < 0:
            raise InputValidationError("ridge_alpha must be >= 0")


@dataclass(frozen=True)
class VMDHARParams:
    K: int = 4
    alpha: float = 1500.0
    window: int = 1000
    refit_vmd_every: int = 20
    refit_model_every: int = 60
    edge_lag: int = 5
    ridge_alpha: float = 5.0
    min_train: int = 252

    def __post_init__(self) -> None:
        if self.edge_lag < 0:
            raise InputValidationError("edge_lag must be >= 0")
        if self.window < 100:
            raise InputValidationError("VMD window must be >= 100")


@dataclass(frozen=True)
class BacktestParams:
    target_ann_vol: float = 0.15
    max_leverage: float = 3.0
    cost_bps: float = 2.0
    annualization: int = 252

    def __post_init__(self) -> None:
        if self.target_ann_vol <= 0:
            raise InputValidationError("target_ann_vol must be > 0")
        if self.max_leverage <= 0:
            raise InputValidationError("max_leverage must be > 0")
        if self.cost_bps < 0:
            raise InputValidationError("cost_bps must be >= 0")
