# Software Requirements Specification

## Chart Decomposition & Multi-Scale Analysis System

**Document version:** 1.0
**Date:** 2026-05-27
**Status:** Draft

---

## 1. Introduction

### 1.1 Purpose

This document specifies the requirements for a chart decomposition system that separates a financial price or volatility series into trend, cycle, and noise components using complementary signal-processing techniques: the Maximal Overlap Discrete Wavelet Transform (MODWT), the Continuous Wavelet Transform (CWT), Empirical Mode Decomposition (EMD/EEMD), Variational Mode Decomposition (VMD), and the Hilbert-Huang Transform (HHT). The system also provides downstream applications: Hurst exponent estimation, wavelet coherence between two series, causal volatility forecasting, and a vol-targeting backtest with transaction costs.

The system is intended for quantitative researchers, traders, and analysts who need to (a) understand the multi-scale structure of a time series, (b) generate volatility forecasts that improve risk-sizing, and (c) backtest the resulting strategies with proper causal hygiene.

### 1.2 Scope

The system shall:

- Decompose a single univariate price/return/volatility series into scale-localized components using MODWT, EMD, EEMD, and VMD.
- Produce two-dimensional time-frequency representations (CWT scalogram and Hilbert spectrum).
- Estimate long-memory parameters (Hurst exponent) via wavelet variance.
- Compute wavelet coherence between two series, including phase information.
- Provide hybrid pipelines that combine wavelet denoising, mode decomposition, and Hilbert spectral analysis.
- Support causally honest walk-forward forecasting of log-realized-volatility using HAR and VMD-augmented HAR models.
- Implement a vol-targeting strategy backtest with transaction costs.

The system shall **not**:

- Provide direct market-data ingestion (the user supplies arrays).
- Trade live capital or place orders.
- Make investment recommendations.

### 1.3 Definitions, Acronyms, Abbreviations

| Term | Definition |
|---|---|
| MODWT | Maximal Overlap Discrete Wavelet Transform — translation-invariant DWT |
| DWT | Discrete Wavelet Transform |
| CWT | Continuous Wavelet Transform |
| EMD | Empirical Mode Decomposition (Huang et al., 1998) |
| EEMD | Ensemble EMD with noise-assisted averaging |
| VMD | Variational Mode Decomposition (Dragomiretskiy & Zosso, 2014) |
| HHT | Hilbert-Huang Transform — EMD followed by Hilbert spectral analysis |
| IMF | Intrinsic Mode Function — one component produced by EMD |
| HAR | Heterogeneous Autoregressive model (Corsi, 2009) |
| RV | Realized Variance — sum of squared intraday returns |
| log-RV | Natural log of realized variance |
| COI | Cone of Influence — region of a time-frequency plot affected by boundary padding |
| QLIKE | Quasi-likelihood loss for volatility forecasts |
| OOS | Out-of-sample |
| Hurst exponent H | Long-memory parameter; H = 0.5 ↔ random walk |

### 1.4 References

1. Percival, D. B., & Walden, A. T. (2000). *Wavelet Methods for Time Series Analysis*. Cambridge.
2. Gençay, R., Selçuk, F., & Whitcher, B. (2001). *An Introduction to Wavelets and Other Filtering Methods in Finance and Economics*. Academic Press.
3. Torrence, C., & Compo, G. P. (1998). A Practical Guide to Wavelet Analysis. *Bulletin of the AMS*, 79(1).
4. Huang, N. E. et al. (1998). The empirical mode decomposition and the Hilbert spectrum for nonlinear and non-stationary time series analysis. *Proc. Royal Society A*, 454.
5. Wu, Z., & Huang, N. E. (2009). Ensemble Empirical Mode Decomposition. *Advances in Adaptive Data Analysis*, 1(1).
6. Dragomiretskiy, K., & Zosso, D. (2014). Variational Mode Decomposition. *IEEE Trans. Signal Processing*, 62(3).
7. Corsi, F. (2009). A Simple Approximate Long-Memory Model of Realized Volatility. *Journal of Financial Econometrics*, 7(2).

### 1.5 Document Overview

Section 2 gives the overall system context, users, and constraints. Section 3 enumerates functional and non-functional requirements grouped by module. Section 4 specifies data models, interfaces, and configuration. Section 5 covers validation and test requirements. Appendix A summarizes parameter defaults; Appendix B lists known limitations and traps that the implementation must guard against.

---

## 2. Overall Description

### 2.1 Product Perspective

The system is a self-contained Python library plus a thin CLI/notebook layer. It depends only on widely available scientific-Python packages and a small number of decomposition libraries. It is designed to be used:

- Interactively from a Jupyter notebook for exploratory analysis.
- Scripted in batch mode for nightly backtests or scheduled vol-forecast updates.
- As an importable package from a downstream trading or risk system.

### 2.2 Product Functions

At a high level the system provides eight functional modules:

1. **Decomposition** — MODWT, EMD, EEMD, VMD of a 1-D series.
2. **Time-frequency views** — CWT scalogram, HHT spectrum, MODWT-Hilbert spectrum.
3. **Long-memory estimation** — Hurst exponent via wavelet variance.
4. **Bivariate analysis** — wavelet coherence, cross-wavelet phase.
5. **Hybrid pipelines** — wavelet-denoise → EMD; EMD → CWT-per-IMF; MODWT → Hilbert.
6. **Realized volatility computation** from intraday returns.
7. **Forecasting** — walk-forward HAR and VMD-augmented HAR for log-RV.
8. **Strategy evaluation** — vol-targeting backtest with transaction costs.

### 2.3 User Classes and Characteristics

| User class | Description | Key needs |
|---|---|---|
| Quantitative researcher | Explores time-series structure | Diagnostics, plots, parameter flexibility |
| Vol forecaster / risk manager | Produces daily vol forecasts | Causal pipelines, OOS metrics, robust defaults |
| Strategy developer | Builds vol-targeting systems | Backtest module, transaction-cost handling, Sharpe/QLIKE diagnostics |

### 2.4 Operating Environment

- Python 3.10+
- Linux, macOS, or Windows
- NumPy, SciPy, Matplotlib, scikit-learn, PyWavelets, EMD-signal (PyEMD), vmdpy
- Optional: Jupyter for interactive notebooks

### 2.5 Design and Implementation Constraints

The design is constrained by lessons learned in prior research:

**C1. Strict causality.** Every forecasting and feature-computation path must use only data available up to the prediction time. Decompositions applied to a full series and then sliced into "past" and "future" windows are forbidden in the forecasting module. Diagnostic modules may decompose the full series but must clearly label outputs as non-causal.

**C2. Boundary handling.** All time-frequency views must overlay or otherwise report the cone of influence so users can distinguish edge-contaminated regions from reliable ones.

**C3. Mode-ordering stability.** Data-adaptive decompositions (EMD, EEMD, VMD) reorder components run-to-run. The implementation must sort modes by a stable criterion (e.g. center frequency for VMD; dominant period for EMD) before any feature is extracted across multiple decompositions.

**C4. Benchmark gating.** The forecasting module must always evaluate a fancy model against (a) a lag-return naive forecaster and (b) HAR. A fancy model is reported as "improving" only if it beats both by a statistically significant Diebold-Mariano margin.

**C5. Reproducibility.** All stochastic routines (EEMD noise, synthetic data, train/test sampling) accept a seed argument.

### 2.6 Assumptions and Dependencies

- The input series is uniformly sampled (daily by default).
- For realized-vol computation, intraday returns are provided as a 2-D array of shape (days, returns_per_day).
- The user is responsible for handling missing data, holidays, and time-zone alignment.

---

## 3. Specific Requirements

### 3.1 Module: Decomposition

#### 3.1.1 MODWT (FR-DECOMP-MODWT)

The system **shall** implement MODWT decomposition with the following behavior:

- **Input:** a 1-D NumPy array `x` of length N, a wavelet name (default `'sym8'`), and a level `J` (default 6).
- **Output:** a list `[A_J, D_J, D_{J-1}, ..., D_1]` where every component has length N.
- **Normalization:** energy-preserving (i.e. `pywt.swt(norm=True)`).
- **Boundary handling:** symmetric reflection by default; configurable to periodic or zero-padding.
- **Cone of influence:** for each level *j*, return the per-sample width `coi_width(j) = (2^j - 1) * (L - 1)` where L is the wavelet filter length.
- **Power-of-two restriction:** if N is not a power of 2, the implementation **shall** pad to the next power of 2, run SWT, then trim back to N.

#### 3.1.2 EMD and EEMD (FR-DECOMP-EMD)

- **Input:** a 1-D NumPy array `x`.
- **Output:** an array of shape `(K, N)` where the last row is the monotonic residue and rows 0..K-2 are IMFs ordered from highest to lowest frequency.
- **Stopping criterion:** Cauchy-style sifting with configurable tolerance and maximum sift iterations.
- **EEMD:** the system **shall** support an ensemble variant that runs EMD on `n_trials` noise-perturbed copies of the signal (default n_trials = 100, noise_width = 0.2 × std(x)) and averages the resulting IMFs.
- **Reporting:** for each IMF the system **shall** report a dominant period estimated via zero-crossing counting: `period = 2 * N / n_zero_crossings`.

#### 3.1.3 VMD (FR-DECOMP-VMD)

- **Input:** a 1-D NumPy array `x`, the number of modes `K` (default 5), and a bandwidth constraint `alpha` (default 1500).
- **Output:** an array of shape `(K, N)` of modes, and an array of length K of center frequencies.
- **Mode sorting:** the system **shall** sort modes by ascending center frequency before returning.
- **Mean handling:** the system **shall** subtract the input mean before decomposition and store it for reconstruction.
- **Reconstruction error:** the system **shall** report the relative L2 reconstruction error.

### 3.2 Module: Time-Frequency Views

#### 3.2.1 CWT Scalogram (FR-TF-CWT)

- **Input:** a 1-D series, scale array (default `geomspace(2, 256, 64)`), and wavelet (default complex Morlet `'cmor1.5-1.0'`).
- **Output:** a 2-D power array `|W|²` of shape `(n_scales, N)`, a frequency vector, and the cone-of-influence boundary as a 1-D array indexed by time.
- **Phase:** the system **shall** return phase `angle(W)` as a separate array on request.
- **Visualization:** the system **shall** provide a plotting function that draws the scalogram on a log-period y-axis with the COI overlaid as a dashed line.

#### 3.2.2 Hilbert Spectrum (FR-TF-HHT)

- **Input:** an array of IMFs (or MODWT detail bands) of shape `(K, N)`.
- **Method:** for each component, compute the Hilbert analytic signal `z = c + i·H(c)`, then instantaneous amplitude `A(t) = |z(t)|` and instantaneous frequency `f(t) = (1/2π)·d(arg z)/dt` via phase unwrapping.
- **Output:** a 2-D energy array `(n_freq_bins, N)` accumulated from `A(t)²` placed at the bin containing `f(t)` for each (component, time).
- **Smoothing:** the system **shall** apply a small Gaussian filter (default `sigma=(1.5, 4)`) before returning, with smoothing parameters configurable.

#### 3.2.3 MODWT-Hilbert Spectrum (FR-TF-MODWT-HHT)

- The system **shall** support computing the Hilbert spectrum from MODWT detail bands as an alternative to EMD IMFs. This is the recommended production-friendly time-frequency view (per the hybrid pipeline in Section 3.5).

### 3.3 Module: Long-Memory Estimation

#### 3.3.1 Hurst via Wavelet Variance (FR-HURST)

- **Input:** a 1-D series, a wavelet (default `'db4'`), and a level range `(j_lo, j_hi)`.
- **Method:** compute MODWT to max level, then for each level *j* compute `Var(d_j)`. Regress `log₂ Var(d_j)` on `j` over `[j_lo, j_hi]`. The Hurst exponent is `H = (slope + 2) / 2` (this normalization accounts for the energy-preserving MODWT).
- **Output:** point estimate Ĥ, the slope, intercept, full variance array, and the included scale mask.
- **Diagnostics:** the system **shall** produce a log-log plot of variance vs scale with the fitted line overlaid, so users can detect kinks (scale-dependent dynamics).
- **Validation:** the implementation **shall** be unit-tested against fractional Gaussian noise of known H ∈ {0.3, 0.5, 0.7, 0.85}, with target estimation error ≤ 0.07.

### 3.4 Module: Bivariate Analysis

#### 3.4.1 Wavelet Coherence (FR-COH)

- **Input:** two 1-D series of equal length, scale array, wavelet (complex Morlet recommended).
- **Method:**
  - Compute CWTs `W_x`, `W_y`.
  - Form cross-wavelet `W_xy = W_x · conj(W_y)`.
  - Smooth `W_xy`, `|W_x|²`, `|W_y|²` in time (Gaussian with σ proportional to scale) and across scales.
  - Coherence: `R²(a,b) = |S(W_xy)|² / (S(|W_x|²) · S(|W_y|²))`.
- **Output:** R² array of shape `(n_scales, N)` bounded in [0, 1], phase array `angle(S(W_xy))`, frequency vector, and COI.
- **Visualization:** the system **shall** provide a heatmap function that overlays phase arrows (right = in-phase, left = anti-phase, up = y leads, down = x leads) only where coherence exceeds a configurable threshold (default 0.6) and the point is outside the COI.

### 3.5 Module: Hybrid Pipelines

The system **shall** provide three named hybrid pipelines:

#### 3.5.1 Hybrid A — Wavelet Denoise → EMD (FR-HYB-A)

- Apply wavelet decomposition, zero out the finest `k_drop` detail bands (default 2), reconstruct, then run EMD on the reconstruction.
- Use case: cleaner IMFs by removing noise-induced spurious extrema.

#### 3.5.2 Hybrid B — EMD → CWT-per-IMF (FR-HYB-B)

- Run EMD, then compute a CWT scalogram of each individual IMF.
- Use case: detect residual mode mixing within an IMF.

#### 3.5.3 Hybrid C — MODWT → Hilbert Spectrum (FR-HYB-C)

- Run MODWT, then apply Hilbert spectral analysis to each detail band.
- Use case: production-friendly time-frequency view with no mode mixing and full reproducibility.

### 3.6 Module: Realized Volatility

#### 3.6.1 RV Computation (FR-RV)

- **Input:** intraday returns of shape `(N_days, M_intraday)`.
- **Output:** for each day, realized variance `RV = sum(r_intraday²)`, realized vol `sqrt(RV * 252)`, log-RV `log(RV + eps)`.
- The system **shall** also accept a 1-D daily returns array, in which case RV is approximated as `r²` with a warning that this is a high-noise estimator.

### 3.7 Module: Forecasting

#### 3.7.1 HAR Baseline (FR-FCST-HAR)

- **Features at time t:** `[log_rv[t], mean(log_rv[t-4:t+1]), mean(log_rv[t-21:t+1])]`.
- **Model:** ridge regression with configurable regularization (default α = 5).
- **Target:** `log_rv[t+1]` (one-step-ahead).
- **Refit cadence:** every `REFIT_MOD` days (default 60), trained on all data with timestamp strictly less than t.

#### 3.7.2 VMD-Augmented HAR (FR-FCST-VMD-HAR)

- **Causal VMD:** at each prediction time t, run VMD on a trailing window of length `WINDOW` (default 1000) of log-RV up to and including time t.
- **Refit cadence for VMD:** every `REFIT_VMD` days (default 20). Modes are reused between refits.
- **Mode sorting:** sort by ascending center frequency at every refit (Constraint C3).
- **Edge lag:** read mode values at relative index `(t - lo) - EDGE_LAG` (default EDGE_LAG = 5) to avoid the unstable VMD right edge.
- **Per-mode features:** for each of K modes, append `[m[t-lag], mean(m[t-lag-4:t-lag+1]), mean(m[t-lag-21:t-lag+1])]`.
- **Composition:** the final feature vector concatenates the 3 HAR features with the 3K VMD features.
- **Model:** ridge regression refit every `REFIT_MOD` days.

#### 3.7.3 Evaluation (FR-FCST-EVAL)

The system **shall** compute and report, on the OOS test window:

- RMSE and MAE on log-RV.
- R² on log-RV.
- QLIKE on variance scale: `mean(σ²_true/σ²_pred − log(σ²_true/σ²_pred) − 1)`.
- Diebold-Mariano statistic comparing the candidate model's squared errors to HAR's, using Newey-West HAC standard errors with bandwidth ≥ 22 days.

A model is reported as "improves on HAR" only if **all** of the following hold:
- ΔRMSE > 0 (lower is better).
- ΔQLIKE > 0.
- |DM statistic| > 1.96 in favor of the model.

### 3.8 Module: Vol-Targeting Backtest

#### 3.8.1 Position Sizing (FR-BT-POS)

At end of day t, position `w[t]` for day t+1 is computed from forecast `σ̂[t+1]` as:

```
w[t] = clip(target_ann_vol / max(σ̂[t+1], eps), -MAX_LEV, +MAX_LEV)
```

Defaults: `target_ann_vol = 0.15`, `MAX_LEV = 3.0`.

#### 3.8.2 PnL Accounting (FR-BT-PNL)

- Gross PnL on day t+1: `w[t] * ret[t+1]`.
- Turnover on day t+1: `|w[t+1] - w[t]|`.
- Transaction cost on day t+1: `turnover * BPS_COST / 10000` (default `BPS_COST = 2`).
- Net PnL: gross minus cost.

#### 3.8.3 Backtest Metrics (FR-BT-METRICS)

The system **shall** report, over the evaluation window:

- Annualized return and vol.
- Sharpe ratio.
- Maximum drawdown.
- Average gross leverage.
- Annualized turnover.
- Cost drag (gross return − net return, annualized).

The system **shall** also produce three plots:

1. Cumulative net PnL vs buy-and-hold and naive vol-target.
2. 30-day rolling realized strategy vol vs target line.
3. Position size over time.

### 3.9 Non-Functional Requirements

#### 3.9.1 Performance

- **NFR-P1:** A single MODWT decomposition of a length-2048 series shall complete in < 100 ms on commodity hardware.
- **NFR-P2:** A single VMD decomposition (K = 5, length 1024) shall complete in < 2 seconds.
- **NFR-P3:** A 2000-day walk-forward HAR backtest with refits every 60 days shall complete in < 10 seconds end-to-end.
- **NFR-P4:** A 2000-day walk-forward VMD-HAR backtest with VMD refits every 20 days shall complete in < 5 minutes.

#### 3.9.2 Reliability

- **NFR-R1:** All decomposition functions shall validate input length, dtype, and NaN content, raising informative errors before invoking the underlying algorithm.
- **NFR-R2:** The forecasting module shall fail loudly (raise an exception) if the user attempts to fit on data that includes timestamps ≥ the prediction time.

#### 3.9.3 Usability

- **NFR-U1:** Every public function shall have a docstring with: purpose, parameters with types and defaults, return value description, an example, and a "Pitfalls" section where relevant.
- **NFR-U2:** The library shall ship with three Jupyter notebooks: (a) decomposition tour, (b) forecasting walkthrough, (c) vol-targeting backtest.

#### 3.9.4 Reproducibility

- **NFR-RP1:** Every stochastic routine accepts a `seed` argument.
- **NFR-RP2:** The library shall log its version and the version of all decomposition dependencies into any saved result.

---

## 4. Data Models and Interfaces

### 4.1 Core Data Types

```python
@dataclass
class MODWTResult:
    approximation: np.ndarray        # shape (N,)
    details: list[np.ndarray]        # [D1, D2, ..., DJ], each shape (N,)
    wavelet: str
    level: int
    coi_widths: list[int]            # one per detail level

@dataclass
class EMDResult:
    imfs: np.ndarray                 # shape (K, N), last row is residue
    dominant_periods: list[float]    # length K-1
    n_sift_iterations: list[int]     # one per IMF

@dataclass
class VMDResult:
    modes: np.ndarray                # shape (K, N), sorted by center freq
    center_frequencies: np.ndarray   # shape (K,)
    series_mean: float
    reconstruction_error: float

@dataclass
class TimeFreqResult:
    power: np.ndarray                # shape (n_freqs, N)
    frequencies: np.ndarray          # shape (n_freqs,)
    periods: np.ndarray              # shape (n_freqs,) = 1/frequencies
    coi: np.ndarray                  # shape (N,) — max valid period at each t
    phase: np.ndarray | None         # optional, same shape as power

@dataclass
class CoherenceResult:
    r_squared: np.ndarray            # shape (n_scales, N), bounded [0, 1]
    phase: np.ndarray                # shape (n_scales, N)
    frequencies: np.ndarray
    coi: np.ndarray

@dataclass
class ForecastResult:
    timestamps: np.ndarray
    predictions: np.ndarray
    actuals: np.ndarray
    metrics: dict                    # {rmse, mae, r2, qlike, dm_vs_har}
    features_used: list[str]

@dataclass
class BacktestResult:
    pnl_gross: np.ndarray
    pnl_net: np.ndarray
    positions: np.ndarray
    turnover: np.ndarray
    metrics: dict                    # {ann_ret, ann_vol, sharpe, maxdd, ...}
```

### 4.2 Public API (Illustrative)

```python
# Decomposition
modwt(x, wavelet='sym8', level=6, boundary='symmetric') -> MODWTResult
emd(x, max_imfs=None, stop_tol=1e-3, seed=None) -> EMDResult
eemd(x, n_trials=100, noise_width=0.2, seed=None) -> EMDResult
vmd(x, K=5, alpha=1500, tol=1e-7) -> VMDResult

# Time-frequency
cwt_scalogram(x, scales=None, wavelet='cmor1.5-1.0') -> TimeFreqResult
hilbert_spectrum(components, n_freq_bins=120, smoothing=(1.5, 4)) -> TimeFreqResult

# Long memory
hurst_wavelet(x, wavelet='db4', j_range=(2, 8)) -> HurstResult

# Bivariate
wavelet_coherence(x, y, scales=None) -> CoherenceResult

# Realized vol
realized_variance(intraday_returns) -> np.ndarray
realized_vol(intraday_returns, annualization=252) -> np.ndarray

# Forecasting
har_forecast(log_rv, refit_every=60, ridge_alpha=5.0) -> ForecastResult
vmd_har_forecast(log_rv,
                 K=4, alpha=1500,
                 window=1000, refit_vmd_every=20, refit_model_every=60,
                 edge_lag=5, ridge_alpha=5.0) -> ForecastResult

# Strategy
vol_target_backtest(returns, vol_forecast,
                    target_ann_vol=0.15, max_leverage=3.0,
                    cost_bps=2.0) -> BacktestResult
```

### 4.3 CLI Interface

A `chart-decompose` CLI **shall** be provided supporting at minimum:

```
chart-decompose decompose --method modwt --input prices.csv --level 6 --output result.npz
chart-decompose hurst    --input prices.csv
chart-decompose forecast --target log_rv --intraday returns.csv --model vmd-har
chart-decompose backtest --returns r.csv --forecast f.csv --target-vol 0.15
```

---

## 5. Validation and Test Requirements

### 5.1 Unit Tests

Each decomposition module **shall** have tests covering:

- **Round-trip:** sum of components reconstructs the input to within a documented tolerance (1e-10 for MODWT, 1e-6 for EMD, 0.2 relative error for VMD).
- **Translation invariance** (MODWT only): shifting the input shifts every component by the same amount.
- **Mode count and ordering:** VMD returns K modes sorted by ascending center frequency.
- **Edge robustness:** decompositions on series of length 100, 257, 1024, and 5000 all complete without error.

### 5.2 Statistical Validation

- **Hurst estimator** shall be validated on fractional Gaussian noise with H ∈ {0.3, 0.5, 0.7, 0.85}. Each test uses N = 4096 samples; estimation error must be ≤ 0.07 (95% confidence by replication over 50 seeds).
- **Wavelet coherence** shall be validated on a known-construction pair of series (shared slow factor + independent fast noise) with a deliberate decoupling window. The test must show R² > 0.5 at long scales outside the decoupling window and R² < 0.3 inside it.

### 5.3 Causality Tests

- **No-leakage test:** for every walk-forward forecast, swap the target series at time t with random noise for all t' < t and verify the predictions at t' do not change. Failure indicates the model is using post-t information.
- **Look-ahead detection:** the test suite shall include a deliberate non-causal forecaster and verify its OOS metrics are absurdly good (R² > 0.95), as a regression test against accidentally reintroducing leakage.

### 5.4 End-to-End Test

A reference end-to-end test **shall** generate a 2500-day Heston SV path, run the full pipeline (decomposition diagnostics → log-RV → HAR and VMD-HAR forecasts → vol-targeting backtest), and check:

- HAR achieves R² ≥ 0.85 on log-RV out-of-sample.
- HAR's vol-targeted strategy realizes 30-day rolling vol within ±30% of the target band on at least 70% of days.
- VMD-HAR's RMSE is within ±10% of HAR's RMSE (i.e. neither catastrophically worse, nor heroically better — guard against accidentally reintroducing look-ahead).

---

## Appendix A — Default Parameters

| Parameter | Default | Notes |
|---|---|---|
| MODWT wavelet | `'sym8'` | Approximate symmetry, good general purpose |
| MODWT level | 6 | ~64-128 day band as longest |
| CWT wavelet | `'cmor1.5-1.0'` | Complex Morlet, BW=1.5, center=1.0 |
| CWT scales | `geomspace(2, 256, 64)` | Log-spaced |
| EMD stop tolerance | 1e-3 | Cauchy criterion |
| EEMD n_trials | 100 | |
| EEMD noise width | 0.2 × std(x) | |
| VMD K | 5 | For exploratory; 4 for forecasting feature use |
| VMD alpha | 1500 | Moderate bandwidth constraint |
| Hurst wavelet | `'db4'` | |
| Hurst j_range | (2, 8) | Drops finest and coarsest scales |
| HAR ridge α | 5.0 | |
| VMD-HAR window | 1000 | Trailing window for VMD |
| Refit VMD every | 20 days | |
| Refit model every | 60 days | |
| Edge lag | 5 days | Distance from VMD right edge |
| Target ann vol | 0.15 | 15% |
| Max leverage | 3.0 | |
| Transaction cost | 2.0 bps | Per unit turnover |

---

## Appendix B — Known Limitations and Implementation Traps

**B1. Look-ahead leakage is the #1 trap.** Any decomposition computed on the full series and then "used to predict" past values is leaking future information. The implementation must structurally prevent this — for example by making the forecasting module accept only a function `(data_up_to_t) -> features`, not a precomputed feature matrix.

**B2. VMD mode reordering between refits.** When VMD is refit on a sliding window, the algorithm's local optima may reorder modes. The implementation must sort by center frequency at every refit, or the model's feature vector silently changes meaning.

**B3. EMD end effects.** Cubic-spline envelopes near the boundary are unstable. Recent IMF values may shift significantly when new data arrives. The forecasting module's `edge_lag` parameter exists for this reason; do not set it to 0 without explicit justification.

**B4. VMD reconstruction is approximate.** Unlike MODWT, VMD does not satisfy exact reconstruction. Treat its modes as a regularized decomposition, not an orthogonal one. Do not interpret variance shares as if they sum to 100%.

**B5. Returns are nearly unforecastable.** The forecasting module's target should be log-RV, not next-day return. Backtests forecasting return direction with decomposition features generally produce no edge once causality is enforced.

**B6. HAR is a brutal benchmark.** Most fancy decomposition-based forecasters will tie or slightly underperform HAR with ridge regression. Gains typically require nonlinear models or cross-asset features. The implementation must always report HAR side-by-side with any "improved" model.

**B7. Cone of influence is non-negotiable in time-frequency plots.** Users will misinterpret edge artifacts as real features. Every CWT scalogram, HHT spectrum, and coherence plot must show the COI.

**B8. Wavelet choice is not neutral.** Different mother wavelets give qualitatively different decompositions, particularly at short scales. The system should let users supply their own wavelet but document the default's properties and provide a sanity-check function that recomputes the decomposition with a different wavelet and reports the cross-correlation per band.

---

*End of document.*
