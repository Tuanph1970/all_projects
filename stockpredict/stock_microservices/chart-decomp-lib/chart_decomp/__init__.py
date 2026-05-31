"""chart_decomp — public facade API.

All public functions live here.  Import from the top level:

    from chart_decomp import modwt, emd, eemd, vmd
    from chart_decomp import cwt_scalogram, hilbert_spectrum
    from chart_decomp import hurst_wavelet, wavelet_coherence
    from chart_decomp import realized_variance, realized_vol
    from chart_decomp import har_forecast, vmd_har_forecast
    from chart_decomp import vol_target_backtest

The facade creates use-cases and wires dependencies internally.
Callers never need to import from sub-packages directly.
"""
from __future__ import annotations

import numpy as np

from chart_decomp.application.compute_coherence_usecase import ComputeCoherenceUseCase
from chart_decomp.application.compute_time_freq_usecase import ComputeTimeFreqUseCase
from chart_decomp.application.decompose_series_usecase import DecomposeSeriesUseCase
from chart_decomp.application.estimate_hurst_usecase import EstimateHurstUseCase
from chart_decomp.application.hybrid_pipeline_usecase import HybridPipelineUseCase
from chart_decomp.application.run_backtest_usecase import RunBacktestUseCase
from chart_decomp.application.run_forecast_usecase import RunForecastUseCase
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
from chart_decomp.domain.exceptions import (
    CausalityViolationError,
    ChartDecompError,
    DecompositionError,
    InsufficientDataError,
    InputValidationError,
    MissingDependencyError,
)
from chart_decomp.domain.value_objects import (
    BacktestParams,
    CoherenceParams,
    CWTParams,
    EMDParams,
    EEMDParams,
    HARParams,
    HHTParams,
    HurstParams,
    MODWTParams,
    VMDHARParams,
    VMDParams,
)
from chart_decomp.infrastructure.realized_vol.rv_calculator import RealizedVolCalculator

# ── Module-level singletons (cheap; use-cases are stateless) ──────────────────
_decompose = DecomposeSeriesUseCase()
_tf        = ComputeTimeFreqUseCase()
_hurst_uc  = EstimateHurstUseCase()
_coh_uc    = ComputeCoherenceUseCase()
_fc_uc     = RunForecastUseCase()
_bt_uc     = RunBacktestUseCase()
_hyb_uc    = HybridPipelineUseCase()
_rv_calc   = RealizedVolCalculator()


# ── Decomposition ──────────────────────────────────────────────────────────────

def modwt(
    x: np.ndarray,
    wavelet: str = "sym8",
    level: int = 6,
    boundary: str = "symmetric",
) -> MODWTResult:
    """MODWT decomposition.

    Returns MODWTResult with approximation + details [D_1 … D_J] each length N.
    Sum of all components equals x within 1e-10 (energy-preserving).

    Pitfalls:
        Level > swt_max_level(N) raises InsufficientDataError.
    """
    return _decompose.execute(x, "modwt", MODWTParams(wavelet=wavelet, level=level, boundary=boundary))


def emd(
    x: np.ndarray,
    max_imfs: int | None = None,
    stop_tol: float = 1e-3,
    seed: int | None = None,
) -> EMDResult:
    """Empirical Mode Decomposition (PyEMD required).

    IMFs are ordered highest-to-lowest frequency; last row is the residue.

    Pitfalls:
        Trap B3: do not use the last few samples of fresh IMFs as features.
    """
    return _decompose.execute(x, "emd", EMDParams(max_imfs=max_imfs, stop_tol=stop_tol, seed=seed))


def eemd(
    x: np.ndarray,
    n_trials: int = 100,
    noise_width: float = 0.2,
    seed: int | None = None,
) -> EMDResult:
    """Ensemble EMD (noise-assisted, PyEMD required).

    noise_width is a fraction of std(x).  Use seed for reproducibility (NFR-RP1).
    """
    return _decompose.execute(x, "eemd", EEMDParams(n_trials=n_trials, noise_width=noise_width, seed=seed))


def vmd(
    x: np.ndarray,
    K: int = 5,
    alpha: float = 1500.0,
    tol: float = 1e-7,
) -> VMDResult:
    """Variational Mode Decomposition (vmdpy required).

    Modes are sorted by ascending center frequency (Constraint C3).

    Pitfalls:
        Trap B4: VMD is not exact reconstruction; do not treat variance
        shares as summing to 100%.
    """
    return _decompose.execute(x, "vmd", VMDParams(K=K, alpha=alpha, tol=tol))


# ── Time-frequency ─────────────────────────────────────────────────────────────

def cwt_scalogram(
    x: np.ndarray,
    scales: np.ndarray | None = None,
    wavelet: str = "cmor1.5-1.0",
) -> TimeFreqResult:
    """CWT power scalogram with mandatory COI.

    Pitfalls:
        Trap B7: never plot without overlaying coi from the result.
    """
    return _tf.cwt(x, CWTParams(scales=scales, wavelet=wavelet))


def hilbert_spectrum(
    components: np.ndarray,
    n_freq_bins: int = 120,
    smoothing: tuple = (1.5, 4.0),
) -> TimeFreqResult:
    """Hilbert spectrum from a (K, N) component array (IMFs or MODWT bands).

    Exclude the residue / approximation before passing.
    """
    return _tf.hilbert_spectrum(components, HHTParams(n_freq_bins=n_freq_bins, smoothing_sigma=smoothing))


# ── Long memory ────────────────────────────────────────────────────────────────

def hurst_wavelet(
    x: np.ndarray,
    wavelet: str = "db4",
    j_range: tuple = (2, 8),
) -> HurstResult:
    """Hurst exponent via wavelet variance.

    H = 0.5 → random walk; H > 0.5 → trending; H < 0.5 → mean-reverting.
    """
    return _hurst_uc.execute(x, HurstParams(wavelet=wavelet, j_lo=j_range[0], j_hi=j_range[1]))


# ── Bivariate ─────────────────────────────────────────────────────────────────

def wavelet_coherence(
    x: np.ndarray,
    y: np.ndarray,
    scales: np.ndarray | None = None,
) -> CoherenceResult:
    """Wavelet coherence R² and phase between x and y.

    Phase arrows: right=in-phase, left=anti-phase, up=y-leads, down=x-leads.
    Draw arrows only where r_squared > 0.6 and outside coi.
    """
    return _coh_uc.execute(x, y, CoherenceParams(scales=scales))


# ── Realized vol ───────────────────────────────────────────────────────────────

def realized_variance(
    returns: np.ndarray,
    annualization: int = 252,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Compute (rv, annualized_vol, log_rv) from intraday (2-D) or daily (1-D) returns."""
    return _rv_calc.compute(returns, annualization)


def realized_vol(
    returns: np.ndarray,
    annualization: int = 252,
) -> np.ndarray:
    """Convenience wrapper: return just the annualized vol array."""
    _, vol, _ = _rv_calc.compute(returns, annualization)
    return vol


# ── Forecasting ────────────────────────────────────────────────────────────────

def har_forecast(
    log_rv: np.ndarray,
    refit_every: int = 60,
    ridge_alpha: float = 5.0,
) -> ForecastResult:
    """Walk-forward HAR forecast (strictly causal).

    Constraint C4: always compare this baseline against any fancy model.
    """
    return _fc_uc.har(log_rv, HARParams(refit_every=refit_every, ridge_alpha=ridge_alpha))


def vmd_har_forecast(
    log_rv: np.ndarray,
    K: int = 4,
    alpha: float = 1500.0,
    window: int = 1000,
    refit_vmd_every: int = 20,
    refit_model_every: int = 60,
    edge_lag: int = 5,
    ridge_alpha: float = 5.0,
) -> ForecastResult:
    """Walk-forward VMD-augmented HAR forecast (strictly causal).

    Constraint C1: VMD is computed on a trailing window only.
    Constraint C3: modes sorted by ascending center frequency every refit.
    """
    return _fc_uc.vmd_har(
        log_rv,
        VMDHARParams(
            K=K,
            alpha=alpha,
            window=window,
            refit_vmd_every=refit_vmd_every,
            refit_model_every=refit_model_every,
            edge_lag=edge_lag,
            ridge_alpha=ridge_alpha,
        ),
    )


# ── Strategy ───────────────────────────────────────────────────────────────────

def vol_target_backtest(
    returns: np.ndarray,
    vol_forecast: np.ndarray,
    target_ann_vol: float = 0.15,
    max_leverage: float = 3.0,
    cost_bps: float = 2.0,
) -> BacktestResult:
    """Vol-targeting backtest with transaction costs."""
    return _bt_uc.execute(
        returns,
        vol_forecast,
        BacktestParams(
            target_ann_vol=target_ann_vol,
            max_leverage=max_leverage,
            cost_bps=cost_bps,
        ),
    )


# ── Hybrid pipelines ───────────────────────────────────────────────────────────

def hybrid_wavelet_emd(x: np.ndarray, k_drop: int = 2) -> EMDResult:
    """Hybrid A: wavelet-denoise then EMD (cleaner IMFs)."""
    return _hyb_uc.hybrid_a(x, k_drop=k_drop)


def hybrid_emd_cwt(x: np.ndarray) -> list[TimeFreqResult]:
    """Hybrid B: EMD then CWT-per-IMF (detect mode mixing)."""
    return _hyb_uc.hybrid_b(x)


def hybrid_modwt_hilbert(x: np.ndarray) -> TimeFreqResult:
    """Hybrid C: MODWT then Hilbert spectrum (recommended production pipeline)."""
    return _hyb_uc.hybrid_c(x)


# ── Part II — Pattern pipeline ─────────────────────────────────────────────────

from chart_decomp.application.denoise_swings_usecase import (  # noqa: E402
    CalibrationResult,
    calibrate_denoise_swings,
)
from chart_decomp.application.run_pattern_pipeline_usecase import (  # noqa: E402
    RunPatternPipelineUseCase,
)
from chart_decomp.domain.entities import PatternPipelineResult  # noqa: E402
from chart_decomp.domain.value_objects import (  # noqa: E402
    DenoiseParams,
    NullFPRParams,
    SwingParams,
)

_pattern_pipeline_uc = RunPatternPipelineUseCase()


def run_pattern_pipeline(
    x: np.ndarray,
    *,
    denoise_params: "DenoiseParams | None" = None,
    swing_params: "SwingParams | None" = None,
    detectors="all",
    compute_fpr: bool = True,
    fpr_params: "NullFPRParams | None" = None,
) -> PatternPipelineResult:
    """Denoise → swing extraction → pattern detection → (null FPR).

    Parameters
    ----------
    x              : raw price series (1-D float array).
    denoise_params : wavelet denoising config; default DenoiseParams().
    swing_params   : swing extractor config; default SwingParams().
    detectors      : 'all' or list of registered detector names.
    compute_fpr    : if True (default), run the null FPR evaluator and annotate
                     each Detection with null_percentile (FR-FPR-2). Set False
                     for interactive speed.
    fpr_params     : NullFPRParams for the null evaluator. Default n_null=1000;
                     pass NullFPRParams(n_null=100) for faster interactive use.

    Returns
    -------
    PatternPipelineResult with raw, denoised, swings, detections, fpr_by_pattern.
    Detections near the right-edge cone of influence have confirmed=False (B6/C2).
    """
    return _pattern_pipeline_uc.execute(
        x,
        denoise_params=denoise_params,
        swing_params=swing_params,
        detectors=detectors,
        compute_fpr=compute_fpr,
        fpr_params=fpr_params,
    )


__all__ = [
    # Decomposition
    "modwt", "emd", "eemd", "vmd",
    # Time-frequency
    "cwt_scalogram", "hilbert_spectrum",
    # Long memory
    "hurst_wavelet",
    # Bivariate
    "wavelet_coherence",
    # Realized vol
    "realized_variance", "realized_vol",
    # Forecasting
    "har_forecast", "vmd_har_forecast",
    # Strategy
    "vol_target_backtest",
    # Hybrid pipelines
    "hybrid_wavelet_emd", "hybrid_emd_cwt", "hybrid_modwt_hilbert",
    # Result entities
    "MODWTResult", "EMDResult", "VMDResult", "TimeFreqResult",
    "CoherenceResult", "HurstResult", "ForecastResult", "BacktestResult",
    # Params
    "MODWTParams", "EMDParams", "EEMDParams", "VMDParams",
    "CWTParams", "HHTParams", "HurstParams", "CoherenceParams",
    "HARParams", "VMDHARParams", "BacktestParams",
    # Exceptions
    "ChartDecompError", "InputValidationError", "CausalityViolationError",
    "InsufficientDataError", "DecompositionError", "MissingDependencyError",
    # Part II — pattern pipeline
    "run_pattern_pipeline", "PatternPipelineResult",
    "calibrate_denoise_swings", "CalibrationResult",
    "DenoiseParams", "SwingParams", "NullFPRParams",
]
