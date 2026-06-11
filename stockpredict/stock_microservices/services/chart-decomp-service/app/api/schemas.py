"""Pydantic request/response schemas for Chart Decomposition Service.

Arrays are serialized as list[float] for JSON-safe transport.
Optional[list[float]] for second series in bivariate endpoints.
"""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _check_array(v: list[float], min_len: int = 4) -> list[float]:
    if len(v) < min_len:
        raise ValueError(f"series must have at least {min_len} values")
    return v


# ---------------------------------------------------------------------------
# Decomposition requests
# ---------------------------------------------------------------------------

class MODWTRequest(BaseModel):
    series: list[float] = Field(..., description="Univariate price/return series")
    wavelet: str = Field("sym8", description="PyWavelets wavelet name")
    level: int = Field(6, ge=1, le=20)
    boundary: str = Field("periodic")

    @field_validator("series")
    @classmethod
    def _check_series(cls, v: list[float]) -> list[float]:
        return _check_array(v, min_len=16)


class EMDRequest(BaseModel):
    series: list[float]
    max_imfs: int = Field(0, ge=0)
    spline_kind: str = Field("cubic")

    @field_validator("series")
    @classmethod
    def _check(cls, v: list[float]) -> list[float]:
        return _check_array(v)


class EEMDRequest(BaseModel):
    series: list[float]
    n_trials: int = Field(100, ge=10, le=2000)
    noise_width: float = Field(0.2, gt=0.0)
    max_imfs: int = Field(0, ge=0)
    seed: int = Field(42)

    @field_validator("series")
    @classmethod
    def _check(cls, v: list[float]) -> list[float]:
        return _check_array(v)


class VMDRequest(BaseModel):
    series: list[float]
    K: int = Field(5, ge=2, le=20, description="Number of modes")
    alpha: float = Field(1500.0, gt=0.0, description="Bandwidth constraint")
    tau: float = Field(0.0, description="Noise tolerance (0 for exact reconstruction)")
    dc: bool = Field(False, description="Include DC component")
    init: int = Field(1, description="Frequency initialisation (0=all zero, 1=uniform, 2=random)")
    tol: float = Field(1e-7)
    seed: int = Field(42)

    @field_validator("series")
    @classmethod
    def _check(cls, v: list[float]) -> list[float]:
        return _check_array(v)


# ---------------------------------------------------------------------------
# Time-frequency requests
# ---------------------------------------------------------------------------

class CWTRequest(BaseModel):
    series: list[float]
    wavelet: str = Field("cmor1.5-1.0")
    scales: Optional[list[float]] = Field(None, description="Explicit scales; None → auto log-spaced")
    n_scales: int = Field(64, ge=8, le=512)
    sampling_period: float = Field(1.0, gt=0.0)

    @field_validator("series")
    @classmethod
    def _check(cls, v: list[float]) -> list[float]:
        return _check_array(v)


class HHTRequest(BaseModel):
    series: list[float]
    n_freq_bins: int = Field(120, ge=16, le=1024)
    smoothing_sigma: tuple[float, float] = Field((1.5, 4.0))
    max_imfs: int = Field(0)

    @field_validator("series")
    @classmethod
    def _check(cls, v: list[float]) -> list[float]:
        return _check_array(v)


# ---------------------------------------------------------------------------
# Long-memory request
# ---------------------------------------------------------------------------

class HurstRequest(BaseModel):
    series: list[float]
    wavelet: str = Field("db4")
    j_lo: int = Field(2, ge=1)
    j_hi: int = Field(8, ge=2)

    @field_validator("series")
    @classmethod
    def _check(cls, v: list[float]) -> list[float]:
        return _check_array(v, min_len=64)


# ---------------------------------------------------------------------------
# Coherence request
# ---------------------------------------------------------------------------

class CoherenceRequest(BaseModel):
    x: list[float]
    y: list[float]
    wavelet: str = Field("cmor1.5-1.0")
    scales: Optional[list[float]] = None
    n_scales: int = Field(64, ge=8, le=512)
    smoothing_sigma_time: float = Field(0.25, gt=0.0)
    smoothing_sigma_scale: float = Field(0.6, ge=0.0)

    @field_validator("x", "y")
    @classmethod
    def _check(cls, v: list[float]) -> list[float]:
        return _check_array(v)


# ---------------------------------------------------------------------------
# Forecast / backtest requests
# ---------------------------------------------------------------------------

class HARForecastRequest(BaseModel):
    log_rv: list[float] = Field(..., description="Log realised-variance series")
    ridge_alpha: float = Field(5.0, gt=0.0)
    min_train: int = Field(252, ge=50)
    refit_every: int = Field(60, ge=1)

    @field_validator("log_rv")
    @classmethod
    def _check(cls, v: list[float]) -> list[float]:
        return _check_array(v, min_len=60)


class VMDHARForecastRequest(BaseModel):
    log_rv: list[float]
    K: int = Field(4, ge=2, le=10)
    alpha: float = Field(2000.0, gt=0.0)
    window: int = Field(1000, ge=200)
    edge_lag: int = Field(5, ge=0)
    ridge_alpha: float = Field(5.0, gt=0.0)
    min_train: int = Field(252, ge=50)
    refit_vmd_every: int = Field(20, ge=1)
    refit_model_every: int = Field(60, ge=1)

    @field_validator("log_rv")
    @classmethod
    def _check(cls, v: list[float]) -> list[float]:
        return _check_array(v, min_len=60)


class RealizedVarRequest(BaseModel):
    returns: list[float] = Field(..., description="1-D daily returns or flattened 2-D intraday (row-major)")
    n_intraday: Optional[int] = Field(None, description="If set, reshape returns into (N, n_intraday) before computing RV")


class BacktestRequest(BaseModel):
    returns: list[float]
    vol_forecasts: list[float]
    target_ann_vol: float = Field(0.15, gt=0.0)
    max_leverage: float = Field(3.0, gt=0.0)
    cost_bps: float = Field(2.0, ge=0.0)
    lookback_vol: int = Field(21, ge=1)


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------

class MODWTResponse(BaseModel):
    approximation: list[float]
    details: list[list[float]]
    coi_widths: list[int]
    wavelet: str
    level: int
    reconstruction_error: float = Field(..., description="max|x - (approx + sum(details))|")


class EMDResponse(BaseModel):
    imfs: list[list[float]]
    n_imfs: int
    reconstruction_error: float


class VMDResponse(BaseModel):
    modes: list[list[float]]
    omega_final: list[float]
    n_modes: int
    reconstruction_error: float


class CWTResponse(BaseModel):
    power: list[list[float]]
    frequencies: list[float]
    coi: list[float]
    wavelet: str


class HHTResponse(BaseModel):
    power: list[list[float]]   # Hilbert marginal spectrum (n_freq_bins, N)
    frequencies: list[float]
    coi: list[float]


class HurstResponse(BaseModel):
    hurst: float          # H = (slope + 2) / 2
    slope: float
    intercept: float
    variances: list[float]  # Var(d_j) per wavelet level


class CoherenceResponse(BaseModel):
    r_squared: list[list[float]]
    phase: list[list[float]]
    frequencies: list[float]
    coi: list[float]


class ForecastResponse(BaseModel):
    predictions: list[float]
    actuals: list[float]
    timestamps: list[int]
    # dm_vs_har is None for the HAR baseline (no self-comparison), so metric
    # values are Optional — declaring dict[str, float] makes the HAR endpoint
    # fail response validation with a 500.
    metrics: dict[str, float | None]
    features_used: list[str]


class RealizedVarResponse(BaseModel):
    rv: list[float]
    vol: list[float]
    log_rv: list[float]


class BacktestResponse(BaseModel):
    positions: list[float]
    pnl_net: list[float]    # daily net P&L after transaction costs
    pnl_gross: list[float]
    turnover: list[float]
    metrics: dict[str, float]


# ---------------------------------------------------------------------------
# Compare request/response (HAR vs VMD-HAR + DM test in one call)
# ---------------------------------------------------------------------------

class ForecastCompareRequest(BaseModel):
    log_rv: list[float] = Field(..., description="Log realised-variance series")
    har_ridge_alpha: float = Field(5.0, gt=0.0)
    har_min_train: int = Field(252, ge=50)
    har_refit_every: int = Field(60, ge=1)
    vmd_K: int = Field(4, ge=2, le=10)
    vmd_alpha: float = Field(2000.0, gt=0.0)
    vmd_window: int = Field(1000, ge=200)
    vmd_edge_lag: int = Field(5, ge=0)
    vmd_ridge_alpha: float = Field(5.0, gt=0.0)
    vmd_min_train: int = Field(252, ge=50)
    vmd_refit_vmd_every: int = Field(20, ge=1)
    vmd_refit_model_every: int = Field(60, ge=1)

    @field_validator("log_rv")
    @classmethod
    def _check(cls, v: list[float]) -> list[float]:
        return _check_array(v, min_len=60)


class ForecastCompareResponse(BaseModel):
    har: ForecastResponse
    vmd_har: ForecastResponse
    dm_stat: Optional[float] = Field(None, description="Diebold-Mariano stat (VMD-HAR vs HAR); >1.96 → VMD-HAR significantly better")


# ---------------------------------------------------------------------------
# Part II — Pattern detection (CD-616 / A16)
# ---------------------------------------------------------------------------

class PatternDenoiseRequest(BaseModel):
    series: list[float]
    wavelet: str = "sym8"
    level: int = Field(4, ge=1, le=12)
    k_drop: int = Field(1, ge=0)
    method: str = "drop"

    @field_validator("series")
    @classmethod
    def _check(cls, v: list[float]) -> list[float]:
        return _check_array(v, min_len=8)


class PatternDenoiseResponse(BaseModel):
    denoised: list[float]


class PatternSwingsRequest(BaseModel):
    series: list[float]
    order: int = Field(10, ge=1)
    threshold: float = Field(0.08, gt=0.0)
    threshold_mode: str = "range_frac"
    min_gap: int = Field(8, ge=1)

    @field_validator("series")
    @classmethod
    def _check(cls, v: list[float]) -> list[float]:
        return _check_array(v, min_len=8)


class SwingInfo(BaseModel):
    index: int
    price: float
    kind: str


class PatternSwingsResponse(BaseModel):
    swings: list[SwingInfo]


class DetectionInfo(BaseModel):
    pattern: str
    start_index: int
    end_index: int
    pivots: list[int]
    score: float
    null_percentile: Optional[float] = None
    noteworthy: Optional[bool] = None
    confirmed: bool = True
    details: dict[str, Any] = Field(default_factory=dict)


class PatternDetectRequest(BaseModel):
    """Denoise → swings → detect (no FPR)."""
    series: list[float]
    wavelet: str = "sym8"
    level: int = Field(4, ge=1, le=12)
    k_drop: int = Field(1, ge=0)
    denoise_method: str = "drop"
    order: int = Field(10, ge=1)
    threshold: float = Field(0.08, gt=0.0)
    threshold_mode: str = "range_frac"
    min_gap: int = Field(8, ge=1)
    detectors: list[str] = Field(default_factory=list)

    @field_validator("series")
    @classmethod
    def _check(cls, v: list[float]) -> list[float]:
        return _check_array(v, min_len=8)


class PatternDetectResponse(BaseModel):
    denoised: list[float]
    swings: list[SwingInfo]
    detections: list[DetectionInfo]


class PatternPipelineRequest(PatternDetectRequest):
    """Full pipeline: denoise → swings → detect → optional null-FPR."""
    compute_fpr: bool = False
    n_null: int = Field(100, ge=10, le=2000)
    fpr_seed: Optional[int] = None


class PatternPipelineResponse(PatternDetectResponse):
    fpr_by_pattern: dict[str, float] = Field(default_factory=dict)


class PatternNullFPRRequest(BaseModel):
    series: list[float]
    detectors: list[str] = Field(default_factory=list)
    n_null: int = Field(100, ge=10, le=2000)
    seed: Optional[int] = None

    @field_validator("series")
    @classmethod
    def _check(cls, v: list[float]) -> list[float]:
        return _check_array(v, min_len=8)


class PatternNullFPRResponse(BaseModel):
    fpr_by_pattern: dict[str, float]
    score_pct95_by_pattern: dict[str, float]
    n_null: int
    winner: str = Field("har", description="'har' | 'vmd_har' | 'tie'")
