"""Chart Decomposition Service — API routes.

All endpoints are stateless; heavy computation is delegated to
app.services.decomp_service which wraps the chart_decomp library.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, status

from chart_decomp.domain.exceptions import (
    ChartDecompError,
    InsufficientDataError,
    MissingDependencyError,
)

from app.api.schemas import (
    BacktestRequest,
    BacktestResponse,
    CoherenceRequest,
    CoherenceResponse,
    CWTRequest,
    CWTResponse,
    EMDRequest,
    EMDResponse,
    EEMDRequest,
    ForecastCompareRequest,
    ForecastCompareResponse,
    ForecastResponse,
    HARForecastRequest,
    HHTRequest,
    HHTResponse,
    HurstRequest,
    HurstResponse,
    MODWTRequest,
    MODWTResponse,
    PatternDenoiseRequest,
    PatternDenoiseResponse,
    PatternDetectRequest,
    PatternDetectResponse,
    PatternNullFPRRequest,
    PatternNullFPRResponse,
    PatternPipelineRequest,
    PatternPipelineResponse,
    PatternSwingsRequest,
    PatternSwingsResponse,
    RealizedVarRequest,
    RealizedVarResponse,
    VMDHARForecastRequest,
    VMDRequest,
    VMDResponse,
)
import app.services.decomp_service as svc

logger = logging.getLogger(__name__)

router = APIRouter()


def _handle(exc: Exception) -> HTTPException:
    if isinstance(exc, InsufficientDataError):
        return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    if isinstance(exc, MissingDependencyError):
        return HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=str(exc))
    if isinstance(exc, ChartDecompError):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    logger.exception("Unexpected error in chart-decomp endpoint")
    return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


# ---------------------------------------------------------------------------
# Decomposition
# ---------------------------------------------------------------------------

@router.post("/decompose/modwt", response_model=MODWTResponse, summary="MODWT decomposition")
async def decompose_modwt(req: MODWTRequest) -> MODWTResponse:
    """Maximal Overlap Discrete Wavelet Transform with MRA reconstruction."""
    try:
        return svc.run_modwt(req)
    except Exception as exc:
        raise _handle(exc) from exc


@router.post("/decompose/emd", response_model=EMDResponse, summary="EMD decomposition")
async def decompose_emd(req: EMDRequest) -> EMDResponse:
    """Empirical Mode Decomposition (requires emd extra)."""
    try:
        return svc.run_emd(req)
    except Exception as exc:
        raise _handle(exc) from exc


@router.post("/decompose/eemd", response_model=EMDResponse, summary="EEMD decomposition")
async def decompose_eemd(req: EEMDRequest) -> EMDResponse:
    """Ensemble EMD with noise trials (requires emd extra)."""
    try:
        return svc.run_eemd(req)
    except Exception as exc:
        raise _handle(exc) from exc


@router.post("/decompose/vmd", response_model=VMDResponse, summary="VMD decomposition")
async def decompose_vmd(req: VMDRequest) -> VMDResponse:
    """Variational Mode Decomposition (requires vmd extra)."""
    try:
        return svc.run_vmd(req)
    except Exception as exc:
        raise _handle(exc) from exc


# ---------------------------------------------------------------------------
# Time-frequency
# ---------------------------------------------------------------------------

@router.post("/time-freq/cwt", response_model=CWTResponse, summary="CWT scalogram")
async def time_freq_cwt(req: CWTRequest) -> CWTResponse:
    """Continuous Wavelet Transform power scalogram with COI."""
    try:
        return svc.run_cwt(req)
    except Exception as exc:
        raise _handle(exc) from exc


@router.post("/time-freq/hht", response_model=HHTResponse, summary="Hilbert-Huang Transform")
async def time_freq_hht(req: HHTRequest) -> HHTResponse:
    """Hilbert-Huang Transform: EMD + Hilbert marginal spectrum."""
    try:
        return svc.run_hht(req)
    except Exception as exc:
        raise _handle(exc) from exc


# ---------------------------------------------------------------------------
# Long memory
# ---------------------------------------------------------------------------

@router.post("/hurst", response_model=HurstResponse, summary="Wavelet Hurst exponent")
async def hurst(req: HurstRequest) -> HurstResponse:
    """Estimate Hurst exponent via wavelet variance regression."""
    try:
        return svc.run_hurst(req)
    except Exception as exc:
        raise _handle(exc) from exc


# ---------------------------------------------------------------------------
# Coherence
# ---------------------------------------------------------------------------

@router.post("/coherence", response_model=CoherenceResponse, summary="Wavelet coherence")
async def coherence(req: CoherenceRequest) -> CoherenceResponse:
    """Time-varying R² coherence and phase between two series."""
    try:
        return svc.run_coherence(req)
    except Exception as exc:
        raise _handle(exc) from exc


# ---------------------------------------------------------------------------
# Forecasting
# ---------------------------------------------------------------------------

@router.post("/forecast/har", response_model=ForecastResponse, summary="HAR volatility forecast")
async def forecast_har(req: HARForecastRequest) -> ForecastResponse:
    """Walk-forward HAR model for log realised-variance."""
    try:
        return svc.run_har_forecast(req)
    except Exception as exc:
        raise _handle(exc) from exc


@router.post("/forecast/vmd-har", response_model=ForecastResponse, summary="VMD-HAR forecast")
async def forecast_vmd_har(req: VMDHARForecastRequest) -> ForecastResponse:
    """Walk-forward VMD-augmented HAR (causal window, edge-lag protected)."""
    try:
        return svc.run_vmd_har_forecast(req)
    except Exception as exc:
        raise _handle(exc) from exc


@router.post("/forecast/compare", response_model=ForecastCompareResponse, summary="HAR vs VMD-HAR comparison")
async def forecast_compare(req: ForecastCompareRequest) -> ForecastCompareResponse:
    """Run HAR and VMD-HAR in one call, return both results and the Diebold-Mariano statistic.
    Constraint C4: winner is declared only if VMD-HAR beats HAR on RMSE + QLIKE + DM > 1.96.
    """
    try:
        return svc.run_forecast_compare(req)
    except Exception as exc:
        raise _handle(exc) from exc


# ---------------------------------------------------------------------------
# Realised volatility
# ---------------------------------------------------------------------------

@router.post("/realized-vol", response_model=RealizedVarResponse, summary="Realised variance")
async def realized_vol(req: RealizedVarRequest) -> RealizedVarResponse:
    """Compute realised variance, vol, and log-RV from daily or intraday returns."""
    try:
        return svc.run_realized_var(req)
    except Exception as exc:
        raise _handle(exc) from exc


# ---------------------------------------------------------------------------
# Backtest
# ---------------------------------------------------------------------------

@router.post("/backtest/vol-target", response_model=BacktestResponse, summary="Vol-target backtest")
async def backtest_vol_target(req: BacktestRequest) -> BacktestResponse:
    """Volatility-targeting backtest with leverage cap and transaction costs."""
    try:
        return svc.run_backtest(req)
    except Exception as exc:
        raise _handle(exc) from exc


# ---------------------------------------------------------------------------
# Part II — Pattern detection (CD-616 / A16)
# ---------------------------------------------------------------------------

@router.post("/patterns/denoise", response_model=PatternDenoiseResponse,
             summary="Wavelet denoise (FR-DN-1)")
async def patterns_denoise(req: PatternDenoiseRequest) -> PatternDenoiseResponse:
    """Layer-1 wavelet denoising only — returns the skeleton-ready series."""
    try:
        return svc.run_pattern_denoise(req)
    except Exception as exc:
        raise _handle(exc) from exc


@router.post("/patterns/swings", response_model=PatternSwingsResponse,
             summary="Swing extraction (FR-SW-1/2/3)")
async def patterns_swings(req: PatternSwingsRequest) -> PatternSwingsResponse:
    """Extract alternating H/L swing pivots from a (denoised) series."""
    try:
        return svc.run_pattern_swings(req)
    except Exception as exc:
        raise _handle(exc) from exc


@router.post("/patterns/detect", response_model=PatternDetectResponse,
             summary="Detect patterns (no FPR)")
async def patterns_detect(req: PatternDetectRequest) -> PatternDetectResponse:
    """Denoise → swings → detect all registered patterns.  No null-FPR computation."""
    try:
        return svc.run_pattern_detect(req)
    except Exception as exc:
        raise _handle(exc) from exc


@router.post("/patterns/pipeline", response_model=PatternPipelineResponse,
             summary="Full pattern pipeline (FR-PAT-* + optional FR-FPR-1/2)")
async def patterns_pipeline(req: PatternPipelineRequest) -> PatternPipelineResponse:
    """Denoise → swings → detect → optional null-FPR annotation.
    Set compute_fpr=true to annotate detections with null_percentile (slower).
    Right-edge detections are flagged confirmed=false (B6/C2).
    """
    try:
        return svc.run_pattern_pipeline(req)
    except Exception as exc:
        raise _handle(exc) from exc


@router.post("/patterns/null-fpr", response_model=PatternNullFPRResponse,
             summary="Null-FPR evaluation (FR-FPR-1/2)")
async def patterns_null_fpr(req: PatternNullFPRRequest) -> PatternNullFPRResponse:
    """Run the full pipeline on n_null random-walk surrogates and return per-pattern FPR."""
    try:
        return svc.run_pattern_null_fpr(req)
    except Exception as exc:
        raise _handle(exc) from exc
