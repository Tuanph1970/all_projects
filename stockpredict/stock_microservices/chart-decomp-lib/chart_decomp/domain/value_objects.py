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


# ── Part II — Pattern detection parameter value objects (SRS §II.A) ───────────


@dataclass(frozen=True)
class DenoiseParams:
    """Layer-1 wavelet denoising (FR-DN-1).

    method='drop' zeroes the finest `k_drop` MODWT detail bands and
    reconstructs; 'soft'/'hard' apply universal-threshold coefficient
    shrinkage instead.
    """
    wavelet: str = "sym8"
    level: int = 4
    k_drop: int = 1
    method: Literal["drop", "soft", "hard"] = "drop"

    def __post_init__(self) -> None:
        if self.level < 1:
            raise InputValidationError("DenoiseParams level must be >= 1")
        if self.k_drop < 0:
            raise InputValidationError("DenoiseParams k_drop must be >= 0")
        if self.k_drop > self.level:
            raise InputValidationError(
                f"DenoiseParams k_drop ({self.k_drop}) cannot exceed level ({self.level})"
            )
        if self.method not in ("drop", "soft", "hard"):
            raise InputValidationError(
                f"DenoiseParams method must be drop/soft/hard; got '{self.method}'"
            )


@dataclass(frozen=True)
class SwingParams:
    """Layer-2a swing extraction (FR-SW-1/2/3).

    threshold_mode is scale-robust by design (L4): a fraction of the series
    range, a multiple of rolling ATR, or an absolute price distance.
    Percent-of-price is deliberately NOT offered as the sole option.
    """
    order: int = 10
    threshold_mode: Literal["range_frac", "atr", "absolute"] = "range_frac"
    threshold: float = 0.08
    atr_period: int = 14
    min_gap: int = 8

    def __post_init__(self) -> None:
        if self.order < 1:
            raise InputValidationError("SwingParams order must be >= 1")
        if self.threshold < 0:
            raise InputValidationError("SwingParams threshold must be >= 0")
        if self.atr_period < 1:
            raise InputValidationError("SwingParams atr_period must be >= 1")
        if self.min_gap < 1:
            raise InputValidationError("SwingParams min_gap must be >= 1")
        if self.threshold_mode not in ("range_frac", "atr", "absolute"):
            raise InputValidationError(
                "SwingParams threshold_mode must be range_frac/atr/absolute "
                f"(L4: percent-of-price is not allowed); got '{self.threshold_mode}'"
            )


@dataclass(frozen=True)
class HSParams:
    """Head & Shoulders detector tolerances (FR-PAT-HS)."""
    tol_shoulder: float = 0.35
    tol_neckline: float = 0.50

    def __post_init__(self) -> None:
        if self.tol_shoulder < 0:
            raise InputValidationError("HSParams tol_shoulder must be >= 0")
        if self.tol_neckline < 0:
            raise InputValidationError("HSParams tol_neckline must be >= 0")


@dataclass(frozen=True)
class FlagParams:
    """Flag / Pennant detector parameters (FR-PAT-FLAG)."""
    pole_min: float = 0.40
    retr_max: float = 0.60

    def __post_init__(self) -> None:
        if self.pole_min <= 0:
            raise InputValidationError("FlagParams pole_min must be > 0")
        if not (0.0 < self.retr_max < 1.0):
            raise InputValidationError("FlagParams retr_max must be in (0, 1)")


@dataclass(frozen=True)
class TriangleParams:
    """Triangle detector parameters (FR-PAT-TRI).

    flat_slope_eps : a fitted trendline counts as "flat" when |slope| scaled by
                     the series range is below this threshold.
    min_pivots     : minimum pivots required to fit upper/lower bounds.
                     Raised to 6 (from 4) after A6 null-FPR precision audit:
                     4-pivot windows fire too often on random walks, saturating
                     null pct95 at 1.0 and blocking genuine detections.
    """
    flat_slope_eps: float = 0.04
    min_pivots: int = 6

    def __post_init__(self) -> None:
        if self.flat_slope_eps < 0:
            raise InputValidationError("TriangleParams flat_slope_eps must be >= 0")
        if self.min_pivots < 4:
            raise InputValidationError("TriangleParams min_pivots must be >= 4")


@dataclass(frozen=True)
class DoubleParams:
    """Double top / bottom detector parameters (FR-PAT-DT)."""
    tol_equal: float = 0.03
    min_separation: int = 5
    min_trough_depth: float = 0.03

    def __post_init__(self) -> None:
        if self.tol_equal < 0:
            raise InputValidationError("DoubleParams tol_equal must be >= 0")
        if self.min_separation < 1:
            raise InputValidationError("DoubleParams min_separation must be >= 1")
        if self.min_trough_depth < 0:
            raise InputValidationError("DoubleParams min_trough_depth must be >= 0")


@dataclass(frozen=True)
class NullFPRParams:
    """Null-FPR evaluation parameters (FR-FPR-1/2).

    noteworthy_pct is the null-score percentile a detection must exceed to be
    flagged "noteworthy" (FR-FPR-2). seed makes the surrogate draw reproducible
    (NFR-RP1).
    """
    n_null: int = 1000
    noteworthy_pct: float = 95.0
    seed: Optional[int] = None

    def __post_init__(self) -> None:
        if self.n_null < 1:
            raise InputValidationError("NullFPRParams n_null must be >= 1")
        if not (0.0 <= self.noteworthy_pct <= 100.0):
            raise InputValidationError("NullFPRParams noteworthy_pct must be in [0, 100]")
