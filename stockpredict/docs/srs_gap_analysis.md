# SRS Gap Analysis — Chart Decomposition & Pattern Detection System

**Phase 0 artifact** (survey only — no implementation).
**Date:** 2026-05-30
**Spec surveyed:** `docs/SRS_master_chart_system.md` v3.0
**Codebase surveyed:** `stock_microservices/chart-decomp-lib/`, `stock_microservices/services/chart-decomp-service/`, `stock_microservices/services/ai-insights-service/app/services/patterns/`

---

## 0. Executive summary

**Part I (Frequency Decomposition System) is essentially fully implemented** in a
dedicated, well-architected library `chart-decomp-lib/chart_decomp/` (DDD layout:
domain / application / infrastructure / factories) wrapped by a FastAPI service
`chart-decomp-service`. Every Part I functional requirement has a concrete
implementation, the data models match SRS §I.4.1 closely, and the **four mandatory
Part I validation harnesses already exist and are wired into the test suite**
(round-trip, translation-invariance, fGn-Hurst recovery, coherence known-construction,
no-leakage swap, look-ahead regression, e2e Heston).

**Part II (Pattern Detection System) is NOT implemented per the SRS.** A *parallel,
non-conforming* pattern-detection capability exists in `ai-insights-service`
(`app/services/patterns/`), but it is a different paradigm built for a different
consumer (the decision-helper / Schwager flow), and it violates several of the SRS's
*binding* design lessons (L2 hand-rolled swing loops, L3 no null-FPR, L4 percent-of-price
thresholds). None of the Part II SRS deliverables — wavelet denoising layer, vetted
swing extraction, null-FPR machinery, planted-pattern / FPR / threshold-robustness
tests — exist.

**Headline gaps to plan around (Phases 1–3):**
1. The entire **Part II two-layer pipeline** (FR-DN-*, FR-SW-*, FR-PAT-EXT,
   FR-SCORE-1, FR-FPR-1/2, FR-VIZ-1/2) and its mandatory test harnesses (II.5.1–II.5.4).
2. **Visualization / plotting helpers** (Part I scalogram/coherence/Hurst/backtest plots,
   Part II three-panel) — currently no `matplotlib` anywhere; rendering is delegated to
   the React frontend. This is an architecture decision to ratify, not necessarily code to write.
3. **NFR-U2 Jupyter notebooks** — none exist.
4. **The `chart-decompose` CLI is broken / out of sync** with the library facade
   (calls `cd.modwt(x, params)` and `result.hurst`; the facade takes keyword args and the
   entity field is `.H`). A real bug, not just a gap.
5. **DM statistic is implemented but not surfaced into `ForecastResult.metrics`** for the
   candidate model (the slot is hard-coded `None`); C4 gating lives in a use-case helper.

---

## 1. Part I — Frequency Decomposition System

### 1.1 Decomposition

| Req ID | Status | Evidence (file:symbol) & public interface |
|---|---|---|
| **FR-DECOMP-MODWT** | ✅ ALREADY IMPLEMENTED | `infrastructure/decomposition/modwt_decomposer.py`; facade `chart_decomp.modwt(x, wavelet='sym8', level=6, boundary='symmetric') -> MODWTResult`. Returns approximation + details `[D_1…D_J]`, `coi_widths`, energy-preserving SWT, pad-to-pow2-then-trim. Round-trip + translation-invariance + edge-robustness tested in `tests/test_decomp.py::TestMODWT`. |
| **FR-DECOMP-EMD** (EMD + EEMD) | ✅ ALREADY IMPLEMENTED | `infrastructure/decomposition/emd_decomposer.py`; facade `emd(x, max_imfs, stop_tol, seed)` and `eemd(x, n_trials=100, noise_width=0.2, seed)` -> `EMDResult` (imfs `(K,N)`, residue last row, `dominant_periods` via zero-crossing, `n_sift_iters`). PyEMD optional dep. Tested `tests/test_decomp.py::TestEMD`. |
| **FR-DECOMP-VMD** | ✅ ALREADY IMPLEMENTED | `infrastructure/decomposition/vmd_decomposer.py`; facade `vmd(x, K=5, alpha=1500, tol=1e-7) -> VMDResult` (modes sorted by ascending center freq **per C3**, `series_mean`, `reconstruction_error`). vmdpy optional dep. Ordering + recon-error tested `tests/test_decomp.py::TestVMD`. |

### 1.2 Time-Frequency Views

| Req ID | Status | Evidence |
|---|---|---|
| **FR-TF-CWT** | ✅ ALREADY IMPLEMENTED | `infrastructure/time_freq/cwt_analyzer.py`; facade `cwt_scalogram(x, scales=None, wavelet='cmor1.5-1.0') -> TimeFreqResult` with `power`, `frequencies`, `periods`, `coi`, optional `phase`. COI presence asserted `tests/test_time_freq.py::TestCWT::test_coi_is_mandatory`. **Plotting function (log-period axis + dashed COI) NOT in the library** — see §1.9. |
| **FR-TF-HHT** | ✅ ALREADY IMPLEMENTED | `infrastructure/time_freq/hht_analyzer.py`; facade `hilbert_spectrum(components, n_freq_bins=120, smoothing=(1.5,4.0)) -> TimeFreqResult`. Gaussian smoothing configurable. Tested `tests/test_time_freq.py::TestHHT`. |
| **FR-TF-MODWT-HHT** | ✅ ALREADY IMPLEMENTED | Exposed as Hybrid C — `hybrid_modwt_hilbert(x)` (`application/hybrid_pipeline_usecase.py`). |

### 1.3 Long-Memory Estimation

| Req ID | Status | Evidence |
|---|---|---|
| **FR-HURST** | ✅ ALREADY IMPLEMENTED | `infrastructure/long_memory/wavelet_hurst.py`; facade `hurst_wavelet(x, wavelet='db4', j_range=(2,8)) -> HurstResult` (`H`, `slope`, `intercept`, `variances`, `scale_mask`). **fGn-recovery harness present** — `tests/test_hurst.py::TestHurstFGN::test_fgn_estimation_error` over H∈{0.3,0.5,0.7,0.85}, error ≤ 0.07 (uses `fbm` dev dep). **Caveat:** the stationary-input requirement (estimate on returns, not price — Exp 5 bug) is *documented in the facade docstring* but **not enforced** in code; worth a guard/warning (see §4, Conflict E). |

### 1.4 Bivariate Analysis

| Req ID | Status | Evidence |
|---|---|---|
| **FR-COH** | ✅ ALREADY IMPLEMENTED | `infrastructure/coherence/wavelet_coherence.py`; facade `wavelet_coherence(x, y, scales=None) -> CoherenceResult` (`r_squared`∈[0,1], `phase`, `frequencies`, `coi`). **Known-construction harness present** — `tests/test_coherence.py::TestCoherenceStatistical::test_shared_factor_coupling`. Phase-arrow heatmap plotting NOT in library (§1.9). |

### 1.5 Hybrid Pipelines

| Req ID | Status | Evidence |
|---|---|---|
| **FR-HYB-A** (wavelet-denoise → EMD) | ✅ ALREADY IMPLEMENTED | `hybrid_wavelet_emd(x, k_drop=2)` — `application/hybrid_pipeline_usecase.py`. |
| **FR-HYB-B** (EMD → CWT-per-IMF) | ✅ ALREADY IMPLEMENTED | `hybrid_emd_cwt(x) -> list[TimeFreqResult]`. |
| **FR-HYB-C** (MODWT → Hilbert) | ✅ ALREADY IMPLEMENTED | `hybrid_modwt_hilbert(x) -> TimeFreqResult`. |

### 1.6 Realized Volatility

| Req ID | Status | Evidence |
|---|---|---|
| **FR-RV** | ✅ ALREADY IMPLEMENTED | `infrastructure/realized_vol/rv_calculator.py`; facade `realized_variance(returns, annualization=252) -> (rv, vol, log_rv)` and `realized_vol(...)`. Accepts 2-D intraday and 1-D daily (1-D path warns it is a high-noise estimator). Tested `tests/test_forecast.py::TestRealizedVol` (`test_2d_input`, `test_1d_warns`). |

### 1.7 Forecasting

| Req ID | Status | Evidence |
|---|---|---|
| **FR-FCST-HAR** | ✅ ALREADY IMPLEMENTED | `infrastructure/forecasting/har_forecaster.py`; facade `har_forecast(log_rv, refit_every=60, ridge_alpha=5.0) -> ForecastResult`. Ridge, 3 HAR features, refit cadence, **causality enforced structurally** (features built from `log_rv[0:t+1]`, `_check_causality`, NFR-R2 `CausalityViolationError`). |
| **FR-FCST-VMD-HAR** | ✅ ALREADY IMPLEMENTED | `infrastructure/forecasting/vmd_har_forecaster.py`; facade `vmd_har_forecast(...)`. **Causal trailing-window VMD (C1)**, **mode sort by center freq every refit (C3)**, **edge_lag read-back (C2/B3)**, 3+3K features. Look-ahead guard `tests/test_e2e_heston.py::TestVmdHarLookAheadGuard` (RMSE within ±10% of HAR). |
| **FR-FCST-EVAL** | ⚠️ PARTIALLY IMPLEMENTED | RMSE/MAE/R²/QLIKE computed in `HARForecaster._compute_metrics`. **Diebold-Mariano with Newey-West HAC (bandwidth ≥22) IS implemented**: `application/run_forecast_usecase.py::RunForecastUseCase.diebold_mariano` + `improves_on_har` (enforces ΔRMSE>0 ∧ ΔQLIKE>0 ∧ DM>1.96 — the full C4 gate). **Gap:** `ForecastResult.metrics["dm_vs_har"]` is hard-coded `None` inside both forecasters, so the candidate's DM is *not attached to its own result*; it must be requested separately via the use-case/`/forecast/compare`. Minor wiring gap, not a logic gap. |

### 1.8 Vol-Targeting Backtest

| Req ID | Status | Evidence |
|---|---|---|
| **FR-BT-POS** | ✅ ALREADY IMPLEMENTED | `infrastructure/backtest/vol_target_backtest.py`; facade `vol_target_backtest(returns, vol_forecast, target_ann_vol=0.15, max_leverage=3.0, cost_bps=2.0) -> BacktestResult`. Leverage clip tested `tests/test_forecast.py::TestBacktest::test_position_clipped_to_max_leverage`. |
| **FR-BT-PNL** | ✅ ALREADY IMPLEMENTED | Same module: gross/turnover/cost/net accounting. |
| **FR-BT-METRICS** | ⚠️ PARTIALLY IMPLEMENTED | Metrics dict (ann_ret, ann_vol, sharpe, maxdd, avg_leverage, ann_turnover, cost_drag) present and tested. Rolling-vol-within-band checked in e2e (`test_rolling_vol_within_band`). **The three mandated plots (cum PnL vs B&H/naive, 30-day rolling vol vs target, position over time) are NOT produced by the library** (§1.9). |

### 1.9 Visualization (Part I) — ⚠️ PARTIALLY / architecturally relocated

The SRS embeds plotting obligations in FR-TF-CWT (scalogram on log-period axis + dashed
COI), FR-COH (phase-arrow heatmap), FR-HURST (log-log variance-vs-scale diagnostic plot),
and FR-BT-METRICS (3 backtest plots).

- **Status: NOT IMPLEMENTED as library functions.** There is **no `matplotlib` import
  anywhere** in `chart-decomp-lib` or `chart-decomp-service`, and no `def plot*`.
- The library returns the *data* needed to plot (power, coi, periods, variances,
  pnl arrays, positions). Rendering is delegated to the **React frontend**
  (`stock_react_javascript/.../components/Pages/ChartDecomp/`,
  `services/chartDecompService.js`).
- **This is an architecture conflict with the SRS** (which assumes an in-library
  matplotlib/notebook workflow). Recommended resolution in §4, Conflict A.

### 1.10 Non-Functional (Part I)

| Req | Status | Note |
|---|---|---|
| NFR-P1..P4 (perf budgets) | ❓ UNVERIFIED | No perf benchmark tests; algorithms are standard and likely within budget but unmeasured. |
| NFR-R1 (validate input len/dtype/NaN) | ✅ | `domain/value_objects.py::TimeSeries` validates 1-D, finite, min length; raises `InputValidationError`. |
| NFR-R2 (fail loud on future data) | ✅ | `CausalityViolationError` in forecasters. |
| NFR-U1 (docstrings w/ pitfalls) | ✅ (mostly) | Facade + forecasters have rich docstrings incl. Pitfalls/Trap references. |
| **NFR-U2 (3 Jupyter notebooks)** | ❌ NOT IMPLEMENTED | No `.ipynb` anywhere in repo. |
| NFR-RP1 (seed args) | ✅ | EMD/EEMD/VMD-HAR accept `seed`. |
| NFR-RP2 (log lib + dep versions into results) | ❌ NOT IMPLEMENTED | Results carry no version provenance. |
| **CLI (I.4.3)** | 🐞 BROKEN / OUT OF SYNC | `services/chart-decomp-service/cli.py` exists with `modwt/hurst/har/cwt` subcommands but calls **stale APIs**: `cd.modwt(x, params)` (facade takes kwargs, not a params object), `result.hurst` (entity field is `.H`), `CWTParams(n_scales=...)` (no such field — would `TypeError`). Needs repair, not greenfield. No `decompose --method`, `forecast --model vmd-har`, or `backtest` subcommands. |

### 1.11 Validation harnesses (Part I) — ✅ all mandatory ones present

| Harness (SRS §I.5) | Status | Location |
|---|---|---|
| Round-trip reconstruction | ✅ | `test_decomp.py::TestMODWT::test_round_trip`, `TestEMD::test_round_trip`, VMD recon-error |
| Translation invariance (MODWT) | ✅ | `test_decomp.py::TestMODWT::test_translation_invariance` |
| Mode count & ordering (VMD) | ✅ | `test_decomp.py::TestVMD::test_ascending_center_freq` |
| Edge robustness (len 100/257/1024/5000) | ✅ | `test_decomp.py` edge_robustness across methods |
| fGn-Hurst recovery (≤0.07) | ✅ | `test_hurst.py::TestHurstFGN::test_fgn_estimation_error` |
| Coherence known-construction | ✅ | `test_coherence.py::TestCoherenceStatistical::test_shared_factor_coupling` |
| No-leakage swap | ✅ | `test_causality.py::TestHARCausality::test_no_leakage_swap` |
| Look-ahead regression (absurd R²) | ✅ | `test_causality.py::TestLookAheadDetector::test_lookahead_achieves_high_r2` |
| End-to-end Heston | ✅ | `test_e2e_heston.py` (HAR R²≥0.85, rolling-vol band, VMD-HAR ±10%) |

---

## 2. Part II — Pattern Detection System

> **Bottom line: the SRS Part II pipeline does not exist.** What exists is a separate
> OHLC/Schwager pattern detector in `ai-insights-service` that is *not* the SRS
> deliverable and *violates the SRS's binding design lessons*. Treat Part II as
> greenfield, with the existing detectors as a source of geometry rules to harvest.

### 2.1 What exists today (the parallel implementation)

`services/ai-insights-service/app/services/patterns/`:
- `base.py` — `PatternDetector` base + `PatternMatch` dataclass (pattern_name, type,
  found, confidence, key_bars, measured_move_target, neckline, details). Swing helpers
  `_find_swing_highs/_find_swing_lows` are **hand-rolled comparison loops** over a
  fractal window.
- `reversal.py` — `HeadAndShoulders`, `InverseHeadAndShoulders`, `DoubleTop`,
  `DoubleBottom` detectors + `run_reversal_detectors`.
- `continuation.py` — `Flag`, `Pennant`, `Symmetrical/Ascending/Descending Triangle`,
  `Gap`, `WideRangingDay` + `run_continuation_detectors`.
- `trap.py` — `TrapDetector` (Bull/Bear trap) + `run_trap_detectors`.

It consumes a **pandas OHLC DataFrame**, returns Schwager-style measured-move targets,
and feeds the decision-helper-service. It has unit tests under
`ai-insights-service/tests/test_*patterns*.py`.

### 2.2 Requirement-by-requirement

| Req ID | Status | Notes |
|---|---|---|
| **FR-DN-1** (wavelet denoise layer) | ❌ NOT IMPLEMENTED | No denoising precedes the existing detectors; they run on raw OHLC. The SRS wants MODWT/DWT denoise (drop `k_drop` finest bands or universal-threshold) — Part I's MODWT engine is available to reuse but isn't wired in. |
| **FR-DN-2** (joint denoise↔swing calibration sweep) | ❌ NOT IMPLEMENTED | No calibration routine exists (L1). |
| **FR-SW-1** (extrema via vetted primitive `argrelextrema`, alternation, prominence, min-gap) | ❌ NOT IMPLEMENTED | Existing swings use **hand-rolled loops** — the SRS L2 explicitly forbids this ("two distinct reset-logic bugs"). No alternation-enforcement / prominence / min-gap pass. |
| **FR-SW-2** (ordered alternating `(index,kind)` + skeleton) | ⚠️ PARTIAL/DIVERGENT | Existing code yields high/low pivot index lists but not a single strictly-alternating H/L skeleton object. |
| **FR-SW-3** (scale-robust thresholds: range-frac / ATR / absolute) | ❌ NOT IMPLEMENTED | Existing detectors use **percent-of-price tolerances** (`shoulder_tolerance_pct`, etc.) — the SRS L4 forbids percent-of-price as the *only* option. (ATR is computed in `continuation.py` for WRD but not used as a swing threshold mode.) |
| **FR-PAT-HS** (H&S + inverse) | ⚠️ PARTIAL (geometry exists, wrong layer) | `reversal.py::HeadAndShouldersDetector` / `InverseHeadAndShouldersDetector` implement the 5-pivot geometry & tolerances, but on raw OHLC without denoise/null-FPR. Reusable as a geometry reference. |
| **FR-PAT-FLAG** (flag vs pennant via parallel/converging fit) | ⚠️ PARTIAL | `continuation.py::FlagDetector`/`PennantDetector` exist with pole+consolidation logic. |
| **FR-PAT-TRI** (asc/desc/symmetric via slope-pair) | ⚠️ PARTIAL | `continuation.py` three triangle detectors via `_linreg` slope classification. |
| **FR-PAT-DT** (double top/bottom) | ⚠️ PARTIAL | `reversal.py::DoubleTop/DoubleBottom`. |
| **FR-PAT-EXT** (detector registry `(piv,kinds,x,params)->list[Detection]`) | ❌ NOT IMPLEMENTED | Current dispatch is hard-coded `run_*_detectors` lists; signature is `detect(ohlc)->Optional[PatternMatch]`, not the SRS registry contract. |
| **FR-SCORE-1** (per-detection quality score ∈[0,1]) | ⚠️ PARTIAL | A `confidence` float exists, but it is an ad-hoc geometry score, not calibrated against a null. |
| **FR-FPR-1** (null random-walk FPR — **MANDATORY**) | ❌ NOT IMPLEMENTED | No surrogate generation, no per-pattern FPR. This is the single biggest Part II gap (L3). |
| **FR-FPR-2** (95th-pct null significance gate) | ❌ NOT IMPLEMENTED | — |
| **FR-VIZ-1** (three-panel plot) | ❌ NOT IMPLEMENTED | — (frontend `PatternPanel.js` renders something, but not the SRS three-panel). |
| **FR-VIZ-2** (detection report w/ null-FPR percentile) | ❌ NOT IMPLEMENTED | — |
| **FR-ML-1** (window classifier) | ❌ NOT IMPLEMENTED (explicitly out of scope for v2.0) | Registry must leave room for it. |

### 2.3 Non-functional & validation (Part II) — all ❌

| Item | Status |
|---|---|
| NFR-R1 (vetted primitives, not bespoke loops) | ❌ violated by current hand-rolled swings |
| NFR-R2 (scale-robust thresholds default) | ❌ |
| NFR-RP1 (null generator seedable) | ❌ (no null generator) |
| **II.5.1 Planted-pattern tests (MANDATORY)** | ❌ NOT IMPLEMENTED |
| **II.5.2 False-positive tests (MANDATORY)** | ❌ NOT IMPLEMENTED |
| II.5.3 Threshold-robustness (quiet vs volatile regime) | ❌ NOT IMPLEMENTED |
| II.5.4 Determinism (fixed seed → identical null FPR) | ❌ NOT IMPLEMENTED |

---

## 3. Existing code to reuse

| Capability needed | Reuse from | How |
|---|---|---|
| Wavelet denoising layer (FR-DN-1) | `chart_decomp.modwt` + the Hybrid-A denoise step in `application/hybrid_pipeline_usecase.py` | The drop-finest-bands reconstruction already exists for Hybrid A; factor it into a reusable `denoise()` and call it from the Part II layer. |
| Input validation / value objects | `domain/value_objects.py` (`TimeSeries`, frozen param dataclasses) | New Part II params (`SwingParams`, `DenoiseParams`, detector params) should follow this frozen-dataclass + `__post_init__` validation idiom. |
| Result-entity style | `domain/entities.py` | New `Swing`, `Detection`, `PipelineResult` entities should be plain dataclasses here, matching SRS §II.4 but adapted to the existing naming/typing. |
| Strategy/Protocol + factory pattern | `domain/interfaces.py`, `factories/` | The FR-PAT-EXT detector registry maps naturally onto a `IPatternDetector` Protocol + a registry/factory mirroring `decomposer_factory.py`. |
| Geometry rules for H&S / DT / flag / triangle | `ai-insights-service/app/services/patterns/{reversal,continuation}.py` | Harvest the tolerance logic and measured-move maths; re-express on the SRS swing skeleton (close-price array, not OHLC) with scale-robust thresholds. |
| ATR computation | `ai-insights-service/.../patterns/continuation.py::_rolling_atr` | Reuse for the ATR threshold mode of FR-SW-3. |
| DM / benchmark-gating discipline | `application/run_forecast_usecase.py` (`diebold_mariano`, `improves_on_har`) | Mirror this "always compare to a null/benchmark before claiming" discipline for the null-FPR gate (FR-FPR-2). |
| Service/route + schema wiring | `chart-decomp-service/app/api/{routes,schemas}.py`, `services/decomp_service.py` | New `/patterns/*` endpoints should follow the existing request/response-schema + thin-service pattern; or live in the same service. |
| Test fixtures (synthetic generators) | `tests/conftest.py`, `tests/test_e2e_heston.py::_heston_path` | Reuse RNG fixtures and the Heston/AR1/Brownian generators; add random-walk surrogate + planted-pattern generators alongside. |

---

## 4. Conflicts between SRS illustrative interfaces and existing code

**Rule (per CLAUDE.md): the SRS §I.4/§II.4 signatures are illustrative — match the existing
project conventions, do not copy them verbatim.**

**Conflict A — Plotting/notebooks vs service+SPA architecture.**
SRS assumes in-library matplotlib plots and three Jupyter notebooks (NFR-U2). The project is
a microservice backend feeding a React SPA that does the rendering. *Recommended resolution:*
treat FR-TF/FR-COH/FR-BT/FR-VIZ plotting requirements as **satisfied by returning
plot-ready data** (already done) plus the React components; do **not** add matplotlib to the
service. Optionally provide a thin optional `chart_decomp.viz` module (matplotlib as an
extra) for notebook users, and ship the 3 notebooks against the real facade API to satisfy
NFR-U2 if we want literal compliance. Flag for the user to decide compliance level.

**Conflict B — Part II location & consumer.**
SRS Part II is a univariate (close-price array) library pipeline; the existing detectors are
OHLC/pandas and serve the decision-helper. *Recommended resolution:* build the SRS Part II
pipeline as a **new module inside `chart-decomp-lib`** (`chart_decomp` pattern subpackage),
reusing Part I's MODWT denoise and harvesting geometry from the ai-insights detectors. Leave
the ai-insights OHLC detectors in place (they have a live consumer); do not refactor them into
the SRS shape in this effort. Decide later whether to bridge.

**Conflict C — Data-model field names.**
SRS §I.4.1 `HurstResult.H`; the CLI already (incorrectly) expects `.hurst`. Existing entity
uses `.H` (matches SRS). *Resolution:* keep `.H`; **fix the CLI** to match. For Part II,
adopt SRS field names (`Swing.index/price/kind`, `Detection.score/null_percentile`) since no
conflicting entity exists yet.

**Conflict D — Detector interface signature.**
SRS FR-PAT-EXT wants `(piv, kinds, x, params) -> list[Detection]`; existing detectors are
`detect(ohlc) -> Optional[PatternMatch]`. *Resolution:* for the new Part II module adopt a
Protocol close to the SRS (adapted to project typing), registered via a factory like
`decomposer_factory.py`. Do not retrofit the ai-insights interface.

**Conflict E — Hurst stationary-input not enforced.**
SRS FR-HURST + Exp 5 mark price-input as the #1 Hurst bug. Current code documents but does
not guard. *Resolution (small, optional):* add a heuristic non-stationarity warning (e.g. flag
if input looks like a price level / has a unit-root-ish trend) — non-binding, but cheap insurance.

**Conflict F — DM not attached to candidate metrics.**
`ForecastResult.metrics["dm_vs_har"]` is `None` even though `diebold_mariano` exists.
*Resolution:* leave the forecasters pure; surface DM/gating at the use-case/API layer (already
done in `/forecast/compare`). Optionally populate the field when a baseline is supplied.

---

## 5. Dependencies

### 5.1 Current declared set

`chart-decomp-lib/pyproject.toml`:
- Core: `numpy>=1.26`, `scipy>=1.12`, `scikit-learn>=1.4`, `PyWavelets>=1.4`.
- Extras: `emd=[EMD-signal>=1.6]`, `vmd=[vmdpy>=0.1]`, `dev=[pytest>=8, pytest-asyncio, fbm>=0.3]`, `all`.

`chart-decomp-service/requirements.txt` pins the same core + FastAPI stack and installs
`EMD-signal` / `vmdpy` non-optionally for the service container.

### 5.2 SRS additions vs existing pins

The SRS (§I.2.4) requires exactly: NumPy, SciPy, Matplotlib, scikit-learn, PyWavelets,
EMD-signal (PyEMD), vmdpy. **All are already present except `matplotlib`**, which is
intentionally absent (see Conflict A). No version conflicts: the lib is an isolated,
`pip install -e` package with its own pyproject, built into its own service image, so its
pins do **not** clash with other services (e.g. `ai-insights-service` uses numpy/pandas
independently in its own container).

### 5.3 New deps Part II would need

- **None mandatory.** FR-SW-1's vetted primitive is `scipy.signal.argrelextrema` (SciPy
  already pinned). Null-FPR, planted patterns, scoring are pure NumPy/SciPy.
- `fbm` (already a dev extra) is handy for surrogate generation in tests.
- `matplotlib` only if we choose literal FR-VIZ-1 / NFR-U2 compliance (optional extra).
- FR-ML-1 (future) would add scikit-learn (present) and optionally a DL backend (out of scope).

---

## 6. Consolidated status board

| Area | Done | Partial | Not impl |
|---|---|---|---|
| Part I decomposition (MODWT/EMD/EEMD/VMD) | ✅✅✅ | | |
| Part I time-freq (CWT/HHT/MODWT-HHT) | ✅✅✅ | | |
| Part I Hurst | ✅ (enforce-stationary = optional gap) | | |
| Part I coherence | ✅ | | |
| Part I hybrids A/B/C | ✅✅✅ | | |
| Part I realized vol | ✅ | | |
| Part I forecasting HAR / VMD-HAR | ✅✅ | FR-FCST-EVAL (DM wiring) | |
| Part I backtest | ✅ (pos/pnl) | FR-BT-METRICS (plots) | |
| Part I viz / notebooks / NFR-RP2 | | viz (data only) | plots, notebooks, version-provenance |
| CLI | | | broken — needs repair |
| Part II denoise (DN) | | | FR-DN-1/2 |
| Part II swings (SW) | | FR-SW-2 (divergent) | FR-SW-1/3 (vetted primitive, scale-robust thresholds) |
| Part II detectors (PAT) | | HS/FLAG/TRI/DT geometry exists in wrong layer | FR-PAT-EXT registry |
| Part II scoring/FPR | | FR-SCORE-1 (uncalibrated) | FR-FPR-1/2 (mandatory) |
| Part II viz (VIZ) | | | FR-VIZ-1/2 |
| Part II validation harnesses | | | II.5.1–II.5.4 (planted, FPR, threshold-robust, determinism) |

---

## 7. Recommended focus for Phases 1–3 (informational — not a plan)

1. **Part II is the real work.** Design a two-layer pipeline in `chart-decomp-lib` reusing
   Part I's MODWT denoise, vetted `argrelextrema` swings, scale-robust thresholds, a detector
   registry, and — most importantly — the **mandatory null-FPR machinery and the planted /
   FPR / threshold-robustness / determinism test harnesses** (L3 is the spec's loudest lesson).
2. **Cheap Part I clean-ups** worth folding in: fix the broken CLI (Conflict C/§1.10), attach
   DM to candidate metrics or document the use-case path (Conflict F), optional Hurst
   stationary-input guard (Conflict E), and decide the plotting/notebook compliance level
   (Conflict A) before committing to matplotlib.
3. **Verify, don't assume, NFR-P perf budgets** if performance compliance is in scope.

*Survey only — no implementation performed. Next: Phase 1 (`docs/design.md`).*
