"""Thin application-service layer wrapping the chart_decomp library.

Converts JSON-safe types (list[float]) to/from library result entities.
Calls the chart_decomp facade using its keyword-argument API — no internal
domain imports needed here.
"""
from __future__ import annotations

import numpy as np

import chart_decomp as cd

from chart_decomp.application.run_forecast_usecase import RunForecastUseCase
from chart_decomp.domain.value_objects import HARParams, VMDHARParams

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
    RealizedVarRequest,
    RealizedVarResponse,
    VMDHARForecastRequest,
    VMDRequest,
    VMDResponse,
)

_fc_uc = RunForecastUseCase()


# ---------------------------------------------------------------------------
# Decomposition
# ---------------------------------------------------------------------------

def run_modwt(req: MODWTRequest) -> MODWTResponse:
    x = np.asarray(req.series, dtype=np.float64)
    result = cd.modwt(x, wavelet=req.wavelet, level=req.level, boundary=req.boundary)
    recon = result.reconstruct()
    err = float(np.max(np.abs(x - recon)))
    return MODWTResponse(
        approximation=result.approximation.tolist(),
        details=[d.tolist() for d in result.details],
        coi_widths=result.coi_widths,
        wavelet=result.wavelet,
        level=result.level,
        reconstruction_error=err,
    )


def run_emd(req: EMDRequest) -> EMDResponse:
    x = np.asarray(req.series, dtype=np.float64)
    result = cd.emd(x, max_imfs=req.max_imfs or None)
    recon = result.reconstruct()
    err = float(np.max(np.abs(x - recon)))
    return EMDResponse(
        imfs=[row.tolist() for row in result.imfs],
        n_imfs=result.n_imfs,
        reconstruction_error=err,
    )


def run_eemd(req: EEMDRequest) -> EMDResponse:
    x = np.asarray(req.series, dtype=np.float64)
    result = cd.eemd(x, n_trials=req.n_trials, noise_width=req.noise_width, seed=req.seed)
    recon = result.reconstruct()
    err = float(np.max(np.abs(x - recon)))
    return EMDResponse(
        imfs=[row.tolist() for row in result.imfs],
        n_imfs=result.n_imfs,
        reconstruction_error=err,
    )


def run_vmd(req: VMDRequest) -> VMDResponse:
    x = np.asarray(req.series, dtype=np.float64)
    result = cd.vmd(x, K=req.K, alpha=req.alpha, tol=req.tol)
    recon = result.reconstruct()
    err = float(np.max(np.abs(x - recon)))
    return VMDResponse(
        modes=[row.tolist() for row in result.modes],
        omega_final=result.omega_final.tolist(),
        n_modes=result.n_modes,
        reconstruction_error=err,
    )


# ---------------------------------------------------------------------------
# Time-frequency
# ---------------------------------------------------------------------------

def run_cwt(req: CWTRequest) -> CWTResponse:
    x = np.asarray(req.series, dtype=np.float64)
    scales = np.asarray(req.scales, dtype=np.float64) if req.scales else None
    result = cd.cwt_scalogram(x, scales=scales, wavelet=req.wavelet)
    return CWTResponse(
        power=result.power.tolist(),
        frequencies=result.frequencies.tolist(),
        coi=result.coi.tolist(),
        wavelet=result.wavelet,
    )


def run_hht(req: HHTRequest) -> HHTResponse:
    x = np.asarray(req.series, dtype=np.float64)
    # HHT = EMD → Hilbert.  Run EMD first, then pass IMFs (excluding residue).
    emd_result = cd.emd(x, max_imfs=req.max_imfs or None)
    # exclude the residue (last row) before computing Hilbert spectrum
    imfs = emd_result.imfs[:-1] if emd_result.n_imfs > 1 else emd_result.imfs
    result = cd.hilbert_spectrum(imfs, n_freq_bins=req.n_freq_bins, smoothing=tuple(req.smoothing_sigma))
    return HHTResponse(
        power=result.power.tolist(),
        frequencies=result.frequencies.tolist(),
        coi=result.coi.tolist(),
    )


# ---------------------------------------------------------------------------
# Long memory
# ---------------------------------------------------------------------------

def run_hurst(req: HurstRequest) -> HurstResponse:
    x = np.asarray(req.series, dtype=np.float64)
    result = cd.hurst_wavelet(x, wavelet=req.wavelet, j_range=(req.j_lo, req.j_hi))
    return HurstResponse(
        hurst=float(result.H),
        slope=float(result.slope),
        intercept=float(result.intercept),
        variances=result.variances.tolist(),
    )


# ---------------------------------------------------------------------------
# Coherence
# ---------------------------------------------------------------------------

def run_coherence(req: CoherenceRequest) -> CoherenceResponse:
    x = np.asarray(req.x, dtype=np.float64)
    y = np.asarray(req.y, dtype=np.float64)
    scales = np.asarray(req.scales, dtype=np.float64) if req.scales else None
    result = cd.wavelet_coherence(x, y, scales=scales)
    return CoherenceResponse(
        r_squared=result.r_squared.tolist(),
        phase=result.phase.tolist(),
        frequencies=result.frequencies.tolist(),
        coi=result.coi.tolist(),
    )


# ---------------------------------------------------------------------------
# Forecasting
# ---------------------------------------------------------------------------

def run_har_forecast(req: HARForecastRequest) -> ForecastResponse:
    log_rv = np.asarray(req.log_rv, dtype=np.float64)
    result = cd.har_forecast(log_rv, refit_every=req.refit_every, ridge_alpha=req.ridge_alpha)
    return ForecastResponse(
        predictions=result.predictions.tolist(),
        actuals=result.actuals.tolist(),
        timestamps=result.timestamps.tolist(),
        metrics=result.metrics,
        features_used=result.features_used,
    )


def run_vmd_har_forecast(req: VMDHARForecastRequest) -> ForecastResponse:
    log_rv = np.asarray(req.log_rv, dtype=np.float64)
    result = cd.vmd_har_forecast(
        log_rv,
        K=req.K,
        alpha=req.alpha,
        window=req.window,
        refit_vmd_every=req.refit_vmd_every,
        refit_model_every=req.refit_model_every,
        edge_lag=req.edge_lag,
        ridge_alpha=req.ridge_alpha,
    )
    return ForecastResponse(
        predictions=result.predictions.tolist(),
        actuals=result.actuals.tolist(),
        timestamps=result.timestamps.tolist(),
        metrics=result.metrics,
        features_used=result.features_used,
    )


# ---------------------------------------------------------------------------
# Compare: HAR vs VMD-HAR + Diebold-Mariano in one call
# ---------------------------------------------------------------------------

def run_forecast_compare(req: ForecastCompareRequest) -> ForecastCompareResponse:
    log_rv = np.asarray(req.log_rv, dtype=np.float64)

    har_params = HARParams(
        ridge_alpha=req.har_ridge_alpha,
        min_train=req.har_min_train,
        refit_every=req.har_refit_every,
    )
    vmd_params = VMDHARParams(
        K=req.vmd_K,
        alpha=req.vmd_alpha,
        window=req.vmd_window,
        edge_lag=req.vmd_edge_lag,
        ridge_alpha=req.vmd_ridge_alpha,
        min_train=req.vmd_min_train,
        refit_vmd_every=req.vmd_refit_vmd_every,
        refit_model_every=req.vmd_refit_model_every,
    )

    har_result    = _fc_uc.har(log_rv, har_params)
    vmd_har_result = _fc_uc.vmd_har(log_rv, vmd_params)

    # Diebold-Mariano: VMD-HAR vs HAR baseline
    dm_stat: float | None = None
    try:
        dm_stat = RunForecastUseCase.diebold_mariano(vmd_har_result, har_result)
    except Exception:
        pass

    # Determine winner (Constraint C4: must beat on RMSE + QLIKE + DM)
    har_m   = har_result.metrics
    vmd_m   = vmd_har_result.metrics
    rmse_better = vmd_m.get("rmse", 1e9) < har_m.get("rmse", 1e9)
    qlike_better = vmd_m.get("qlike", 1e9) < har_m.get("qlike", 1e9)
    dm_sig  = dm_stat is not None and dm_stat > 1.96
    winner  = "vmd_har" if (rmse_better and qlike_better and dm_sig) else "har"

    def _to_fc_resp(r) -> ForecastResponse:
        return ForecastResponse(
            predictions=r.predictions.tolist(),
            actuals=r.actuals.tolist(),
            timestamps=r.timestamps.tolist(),
            metrics=r.metrics,
            features_used=r.features_used,
        )

    return ForecastCompareResponse(
        har=_to_fc_resp(har_result),
        vmd_har=_to_fc_resp(vmd_har_result),
        dm_stat=dm_stat,
        winner=winner,
    )


# ---------------------------------------------------------------------------
# Realised volatility
# ---------------------------------------------------------------------------

def run_realized_var(req: RealizedVarRequest) -> RealizedVarResponse:
    arr = np.asarray(req.returns, dtype=np.float64)
    if req.n_intraday is not None:
        n_days = len(arr) // req.n_intraday
        arr = arr[: n_days * req.n_intraday].reshape(n_days, req.n_intraday)
    rv, vol, log_rv = cd.realized_variance(arr)
    return RealizedVarResponse(
        rv=rv.tolist(),
        vol=vol.tolist(),
        log_rv=log_rv.tolist(),
    )


# ---------------------------------------------------------------------------
# Backtest
# ---------------------------------------------------------------------------

def run_backtest(req: BacktestRequest) -> BacktestResponse:
    returns = np.asarray(req.returns, dtype=np.float64)
    vol_fc = np.asarray(req.vol_forecasts, dtype=np.float64)
    result = cd.vol_target_backtest(
        returns,
        vol_fc,
        target_ann_vol=req.target_ann_vol,
        max_leverage=req.max_leverage,
        cost_bps=req.cost_bps,
    )
    return BacktestResponse(
        positions=result.positions.tolist(),
        pnl_net=result.pnl_net.tolist(),
        pnl_gross=result.pnl_gross.tolist(),
        turnover=result.turnover.tolist(),
        metrics=result.metrics,
    )
