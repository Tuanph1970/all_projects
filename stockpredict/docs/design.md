# Design — Chart Decomposition & Pattern Detection System

**Phase 1 artifact** (design only — no implementation).
**Date:** 2026-05-30
**Inputs:** `docs/SRS_master_chart_system.md` v3.0, `docs/srs_gap_analysis.md`
**Targets:** the NOT / PARTIALLY implemented requirements from the gap analysis.

---

## 1. Scope & guiding principles

This design covers the integration of everything the gap analysis marked **NOT** or
**PARTIAL**:

- **Primary (the real work): Part II — Pattern Detection System.** The entire two-layer
  pipeline (FR-DN-*, FR-SW-*, FR-PAT-*, FR-SCORE-1, FR-FPR-1/2, FR-VIZ-1/2) plus its
  mandatory test harnesses (II.5.1–II.5.4).
- **Secondary (Part I clean-ups):** broken `chart-decompose` CLI, DM-stat wiring
  (FR-FCST-EVAL), Hurst stationary-input guard (FR-HURST/Exp 5), backtest/viz plotting
  decision (FR-BT-METRICS, FR-VIZ), NFR-U2 notebooks, NFR-RP2 version provenance.

**Principles (from CLAUDE.md, binding):**

1. **Fit the existing architecture.** Part II slots into the *same* DDD layers as Part I
   (`domain / application / infrastructure / factories` inside `chart-decomp-lib`), not a
   bolt-on feature folder. The SRS §II.4 signatures are illustrative; we adapt them to the
   project's frozen-dataclass + Protocol + factory idiom.
2. **Reuse, don't duplicate.** Layer 1 denoising reuses the existing MODWT engine and the
   band-drop logic already living in `HybridPipelineUseCase.hybrid_a`. Geometry rules are
   harvested from `ai-insights-service/patterns` but re-expressed on the SRS swing skeleton.
3. **The binding constraints win over convenience.** Causality (C1), mode-ordering (C3),
   mandatory benchmark/null (C4, L3), cone-of-influence (C2, B6), and stationary-input Hurst
   (FR-HURST) are preserved by construction — see §10.

---

## 2. Where Part II lives — decision (resolves gap-analysis Conflict B)

**Decision: build Part II as a new capability *inside* `chart-decomp-lib/chart_decomp/`,
reusing Part I. Leave the `ai-insights-service` OHLC detectors untouched.**

Rationale:
- The SRS Part II is univariate (a close-price array) and explicitly *reuses Part I's
  wavelet engine as a denoiser* — that engine is in `chart-decomp-lib`. Co-locating keeps
  the reuse a direct import, not a cross-service dependency.
- The `ai-insights-service` detectors have a **live consumer** (decision-helper) and a
  different contract (OHLC `pandas` → Schwager `PatternMatch` with measured-move targets).
  Refactoring them into the SRS shape would be a risky, out-of-scope change. They remain as
  is; we *harvest their geometry maths* (tolerances, neckline projection, slope
  classification, ATR) into the new pure-NumPy detectors.
- The new pipeline is then exposed through `chart-decomp-service` (new `/patterns/*`
  endpoints), consistent with how Part I is already served.

A future bridge (decision-helper consuming the SRS pipeline's `Detection` + null-FPR
percentile) is left as a deliberate non-goal for this effort.

---

## 3. Module layout (new files, matching existing conventions)

```
chart-decomp-lib/chart_decomp/
  domain/
    entities.py          (+) Swing, Detection, PatternPipelineResult, SwingSkeleton
    value_objects.py     (+) DenoiseParams, SwingParams, DetectorParams (+ per-pattern),
                             NullFPRParams; PriceSeries note (reuse TimeSeries)
    interfaces.py        (+) IDenoiser, ISwingExtractor, IPatternDetector, INullEvaluator
    exceptions.py        (reused as-is)
  infrastructure/
    denoise/
      __init__.py
      wavelet_denoiser.py            FR-DN-1 (band-drop + threshold modes)
    swings/
      __init__.py
      swing_extractor.py             FR-SW-1/2/3 (argrelextrema + alternation + prominence)
    patterns/
      __init__.py
      base.py                        shared geometry helpers (line fit, range-frac, scoring base)
      head_shoulders.py              FR-PAT-HS (+ inverse)
      double.py                      FR-PAT-DT (double top/bottom)
      flag_pennant.py                FR-PAT-FLAG
      triangle.py                    FR-PAT-TRI (asc/desc/symmetric)
    validation/
      __init__.py
      surrogates.py                  random-walk surrogate generator (seeded)
      null_fpr.py                    FR-FPR-1/2 (null FPR + 95th-pct gate)
  application/
    denoise_swings_usecase.py        FR-DN-2 joint calibration sweep
    run_pattern_pipeline_usecase.py  end-to-end: denoise → swings → detect → score → FPR
  factories/
    pattern_detector_factory.py      FR-PAT-EXT registry (mirrors decomposer_factory.py)
  __init__.py            (+) facade fns: denoise, extract_swings, register_detector,
                             detect_patterns, null_fpr, run_pattern_pipeline,
                             calibrate_denoise_swings
  tests/
    test_denoise.py
    test_swings.py
    test_patterns_planted.py     II.5.1 planted-pattern (MANDATORY)
    test_patterns_fpr.py         II.5.2 false-positive + 95th-pct gate (MANDATORY)
    test_threshold_robustness.py II.5.3 quiet vs volatile regime
    test_pattern_determinism.py  II.5.4 seeded null reproducibility
```

This is the *same* grouping Part I uses (e.g. `infrastructure/decomposition/`,
`infrastructure/time_freq/`, `factories/decomposer_factory.py`). New code is additive; no
existing Part I file changes except small, surgical edits in §11.

---

## 4. Data types (reconciling SRS §II.4 with existing entities)

New entities in `domain/entities.py` (plain dataclasses, matching the existing style — see
`MODWTResult`, `ForecastResult`). SRS field names adopted where no conflict exists
(Conflict C resolution from gap analysis):

```python
@dataclass
class Swing:
    index: int
    price: float
    kind: str            # 'H' | 'L'

@dataclass
class SwingSkeleton:
    swings: list[Swing]                 # strictly alternating H/L
    # convenience views computed lazily:
    @property
    def indices(self) -> np.ndarray: ...
    @property
    def kinds(self) -> list[str]: ...

@dataclass
class Detection:
    pattern: str                        # 'Head & Shoulders', 'Bull Flag', ...
    start_index: int
    end_index: int
    pivots: list[int]                   # constituent swing indices
    score: float                        # [0,1] geometric quality (FR-SCORE-1)
    null_percentile: float | None = None  # where score sits vs the null (FR-FPR-2)
    confirmed: bool = True              # False if it touches the right-edge COI (B6)
    details: dict = field(default_factory=dict)

@dataclass
class PatternPipelineResult:
    raw: np.ndarray
    denoised: np.ndarray
    swings: list[Swing]
    detections: list[Detection]
    fpr_by_pattern: dict[str, float]    # populated when compute_fpr=True
```

Parameter value objects in `domain/value_objects.py` (frozen, `__post_init__`-validating,
exactly like `MODWTParams` / `HARParams`):

```python
@dataclass(frozen=True)
class DenoiseParams:
    wavelet: str = "sym8"
    level: int = 4
    k_drop: int = 1
    method: Literal["drop", "soft", "hard"] = "drop"   # FR-DN-1 alt thresholding

@dataclass(frozen=True)
class SwingParams:
    order: int = 10                      # argrelextrema comparison window (FR-SW-1)
    threshold_mode: Literal["range_frac", "atr", "absolute"] = "range_frac"  # FR-SW-3 (L4)
    threshold: float = 0.08              # 8% of range default
    atr_period: int = 14                 # used when threshold_mode == "atr"
    min_gap: int = 8

@dataclass(frozen=True)
class HSParams:        tol_shoulder=0.35; tol_neckline=0.50
@dataclass(frozen=True)
class FlagParams:      pole_min=0.40; retr_max=0.60
@dataclass(frozen=True)
class TriangleParams:  flat_slope_eps=...; min_pivots=...
@dataclass(frozen=True)
class DoubleParams:    tol_equal=0.03

@dataclass(frozen=True)
class NullFPRParams:
    n_null: int = 1000
    noteworthy_pct: float = 95.0
    seed: int | None = None
```

**Reuse:** the existing `TimeSeries` value object (1-D, finite, min-length validation) is
the input wrapper for the price series — no new "PriceSeries" type. `InputValidationError`
and friends are reused.

**No conflict** with Part I entities — these are new names. The SRS `PipelineResult` is
renamed `PatternPipelineResult` to avoid ambiguity with any future Part I pipeline result.

---

## 5. Layer 1 — Denoising (FR-DN-1, FR-DN-2)

**FR-DN-1 `wavelet_denoiser.py`.** Implements `IDenoiser.denoise(series, params) -> np.ndarray`.
- `method="drop"`: run MODWT (reuse `MODWTDecomposer`), zero the finest `k_drop` detail
  bands, reconstruct, trim to N. **This logic already exists** in
  `HybridPipelineUseCase.hybrid_a` (lines 82–86); factor it into the denoiser and have
  `hybrid_a` call the new denoiser (removes the duplicated dead block at lines 71–79 — a
  small bonus clean-up).
- `method="soft"|"hard"`: universal threshold `σ·√(2 ln N)` on detail coefficients
  (`σ` via MAD of finest band), using `pywt` soft/hard thresholding. New code.

**FR-DN-2 `denoise_swings_usecase.py`.** A `calibrate(series, k_drop_grid, threshold_grid,
labels=None)` routine that sweeps `(k_drop × swing threshold)`, returning a small table of
`{k_drop, threshold, n_swings, recall?}` so the user can pick a coupled operating point
(addresses **L1**). Recall column populated only when planted/labeled locations are passed.
Exposed via facade `calibrate_denoise_swings(...)`.

---

## 6. Layer 2a — Swing extraction (FR-SW-1/2/3) — fixes L2 & L4

`swing_extractor.py` implements `ISwingExtractor.extract(series, params) -> list[Swing]`.

Pipeline (all on the **denoised** series):
1. **Extrema via vetted primitive (FR-SW-1, L2):** `scipy.signal.argrelextrema` with
   `order=params.order` for maxima and minima. **No hand-rolled comparison loops** — this is
   the explicit fix for the ai-insights L2 violation.
2. **Alternation enforcement (FR-SW-2):** merge consecutive same-kind extrema, keeping the
   more extreme (higher H / lower L), to guarantee strict H/L/H/L.
3. **Prominence filter (FR-SW-3, L4):** drop a pivot whose price distance to the previous
   retained pivot is below the scale-robust threshold. **Threshold modes:**
   - `range_frac` (default): `threshold × (max(x) − min(x))`.
   - `atr`: `threshold × ATR(atr_period)` at the pivot (reuse the ATR formula harvested from
     `ai-insights .../continuation.py::_rolling_atr`, re-expressed for a close-only series).
   - `absolute`: a raw price distance.
   Percent-of-price is deliberately **not** offered as the only mode (L4).
4. **Minimum spacing:** enforce `min_gap` index distance between retained pivots.

Output: ordered, strictly alternating `list[Swing]` (and a `SwingSkeleton` wrapper exposing
the piecewise-linear connection for visualization).

---

## 7. Layer 2b — Detectors + registry (FR-PAT-HS/FLAG/TRI/DT, FR-PAT-EXT)

**Detector contract (`IPatternDetector`, adapts SRS `(piv, kinds, x, params)->list[Detection]`
to the project's Protocol style):**

```python
@runtime_checkable
class IPatternDetector(Protocol):
    name: str
    def detect(self, skeleton: SwingSkeleton, x: np.ndarray, params) -> list[Detection]: ...
```

**Registry (FR-PAT-EXT) — `pattern_detector_factory.py`** mirrors `DecomposerFactory`'s
name→constructor registry exactly:

```python
register_detector(name, detector)          # add/override
detect_patterns(skeleton, x, detectors="all", params=None) -> list[Detection]
```

`detect_patterns` runs all registered detectors and aggregates. The registry being a plain
dict means an **ML detector (FR-ML-1)** can be slotted in later with no framework change —
satisfying the SRS "leave room for it" requirement.

**Detectors (geometry harvested from `ai-insights-service/patterns`, re-expressed on the
swing skeleton, scale-robust tolerances):**

| File | Patterns | Rule summary | Score (FR-SCORE-1) |
|---|---|---|---|
| `head_shoulders.py` | H&S, inverse H&S | label seq `H L H L H` over 5 pivots; head strictly highest; shoulders within `tol_shoulder`; troughs (neckline) within `tol_neckline` | shoulder symmetry × neckline flatness × head prominence |
| `double.py` | Double top/bottom | `H L H` with the two H within `tol_equal` and a sufficient intervening trough | peak similarity × trough depth |
| `flag_pennant.py` | Flag, pennant | pole = L→H advance > `pole_min` (range-frac); consolidation retraces `0<r<retr_max`; fit upper/lower bounds → **parallel ⇒ flag, converging ⇒ pennant** | pole steepness × consolidation tightness |
| `triangle.py` | Asc/desc/symmetric | linear-fit highs and lows over a pivot window; classify slope pair (flat-high+rising-low ⇒ ascending, etc.) | fit R² × slope separation |

All thresholds are range-fraction or volatility-normalized by default (L4). All scores are
documented per detector (NFR-U1).

---

## 8. Layer 2c — Scoring & null-FPR (FR-SCORE-1, FR-FPR-1/2) — the L3 core

This is the part the existing implementation lacks entirely and the SRS marks **MANDATORY**.

**`surrogates.py`.** `random_walk_surrogates(length, volatility, n, seed) -> Iterator`:
seeded (NFR-RP1) random-walk paths matched to the target's length and per-step volatility.

**`null_fpr.py`.** `INullEvaluator`:
- `null_fpr(length, volatility, detectors, params) -> dict[str, float]`: run the **full
  pipeline** (denoise → swings → detect) on `n_null` surrogates; report per-pattern
  detections-per-series (**FR-FPR-1**).
- `score_thresholds(...) -> dict[str, float]`: the 95th-percentile null score per pattern,
  used to set `Detection.null_percentile` and the "noteworthy" gate (**FR-FPR-2**).

**Discipline mirror:** this is the pattern-world analogue of Part I's `improves_on_har`
benchmark gate (C4). A detection summary that does not carry its null FPR is, per B3,
"not interpretable" — so `run_pattern_pipeline` computes FPR by default (`compute_fpr=True`).

---

## 9. End-to-end pipeline, facade, and live-use safety

**`run_pattern_pipeline_usecase.py`** orchestrates denoise → extract_swings →
detect_patterns → (null_fpr + significance gate) → `PatternPipelineResult`. Facade adds:

```python
denoise(x, wavelet='sym8', level=4, k_drop=1, method='drop') -> np.ndarray
extract_swings(x, order=10, threshold_mode='range_frac', threshold=0.08, min_gap=8) -> list[Swing]
register_detector(name, detector); detect_patterns(skeleton, x, detectors='all') -> list[Detection]
null_fpr(length, volatility, detectors='all', n_null=1000, seed=None) -> dict[str, float]
run_pattern_pipeline(x, denoise_kw=None, swing_kw=None, detectors='all', compute_fpr=True) -> PatternPipelineResult
calibrate_denoise_swings(x, ...) -> list[dict]
```

**Live-use safety (B6 / C2).** Right-edge denoising suffers the same boundary problem as
Part I time-frequency views. A detection whose constituent pivots fall inside the
right-edge cone (within the MODWT `coi_widths` of the finest retained band) is flagged
`confirmed=False`. This is the Part II analogue of Part I's `edge_lag`. No new COI maths —
reuse `MODWTResult.coi_widths`.

---

## 10. How the binding constraints are preserved

| Constraint | Where preserved |
|---|---|
| **C1 causality** | Part II is diagnostic (operates on a supplied historical series), not a forecaster, so the no-future-data rule maps to the **live-edge `confirmed` flag** (§9) rather than walk-forward. No Part II code feeds the forecasting path. |
| **C2 cone-of-influence** | `confirmed=False` for right-edge detections, derived from `coi_widths`. Denoiser documents edge contamination. |
| **C3 mode-ordering** | N/A to patterns (no data-adaptive mode reuse); unchanged for Part I. |
| **C4 benchmark gating → L3 null** | `null_fpr` + 95th-pct `noteworthy` gate is mandatory and on-by-default; the pattern-world equivalent of HAR gating. |
| **FR-HURST stationary input** | Unchanged by Part II; addressed as a Part I clean-up in §11. |
| **L1 denoise↔swing coupling** | `calibrate_denoise_swings` joint sweep (FR-DN-2). |
| **L2 vetted primitives** | `argrelextrema`, never hand-rolled loops. |
| **L4 scale-robust thresholds** | range-frac / ATR / absolute modes; percent-of-price not the sole option. |

---

## 11. Part I clean-ups (PARTIAL items)

Small, surgical, each independently shippable:

1. **CLI repair (BROKEN).** `chart-decomp-service/cli.py` calls stale APIs. Fix to the real
   facade: `cd.modwt(x, wavelet=..., level=...)`, `result.H` (not `.hurst`),
   `cd.cwt_scalogram(x, scales=...)` (drop `n_scales`/params-object misuse). Add the
   SRS-listed subcommands it lacks (`decompose --method`, `forecast --model vmd-har`,
   `backtest`). Covered by a smoke test.
2. **DM wiring (FR-FCST-EVAL).** Keep forecasters pure; add an optional `baseline` arg to
   the forecast use-case / `/forecast/compare` path that populates `metrics["dm_vs_har"]`.
   The logic (`diebold_mariano`, `improves_on_har`) already exists — this is wiring only.
3. **Hurst stationary-input guard (FR-HURST / Exp 5).** Add a non-binding warning in
   `hurst_wavelet` when the input looks non-stationary (e.g. large lag-1 autocorrelation /
   monotone drift), pointing the user to pass returns. Cheap insurance against the #1 bug.
4. **NFR-RP2 provenance (optional).** Attach `{lib_version, pywt, numpy, scipy}` versions to
   result entities or a sidecar dict when results are serialized.
5. **NFR-U2 notebooks (optional, see §12).**

---

## 12. Visualization & notebooks — decision (resolves Conflict A)

**Decision: do NOT add `matplotlib` to the service/library. Rendering stays in React.**

- Part I and Part II both already return *plot-ready data* (power/coi/periods/variances for
  TF; raw/denoised/swings/detections/fpr for patterns). The React `ChartDecomp` pages render
  these; a new `PatternPanel`-style page will render the FR-VIZ-1 three-panel and the
  FR-VIZ-2 detection report (table with score + null-FPR percentile).
- FR-VIZ-1/2 and FR-BT-METRICS plots are therefore satisfied **by the data contract + the
  frontend**, consistent with the established architecture.
- **NFR-U2 (3 notebooks)** literal compliance is the one open item this trades off. *Proposed
  resolution:* ship an **optional `chart_decomp.viz` extra** (matplotlib) plus the three
  notebooks (decomposition tour, forecasting walkthrough, pattern detection) written against
  the real facade — only if the user wants literal NFR-U2 compliance. Flagged in §15.

---

## 13. Service / API layer

New endpoints in `chart-decomp-service` (same thin-route → `decomp_service` → facade idiom,
same `MODWTRequest`/`MODWTResponse` Pydantic style; prefix
`/{API_PREFIX}/api/v2/chart-decomp`):

```
POST /patterns/denoise           DenoiseRequest  -> DenoiseResponse
POST /patterns/swings            SwingRequest    -> SwingResponse
POST /patterns/detect            DetectRequest   -> DetectResponse
POST /patterns/pipeline          PipelineRequest -> PipelineResponse   (denoise+swings+detect+fpr)
POST /patterns/null-fpr          NullFPRRequest  -> NullFPRResponse
```

Gateway: add a Traefik label / `/chart-decomp` row already exists; the new routes live under
the existing chart-decomp prefix, so **no new gateway service** is needed (the CD
Architecture sheet's gateway-map note already anticipated `/chart-decomp`). Frontend:
`chartDecompService.js` gains pattern methods; a sidebar entry + i18n keys per the existing
`ChartDecomp` page pattern.

---

## 14. Test strategy (where each mandatory harness lives)

All under `chart-decomp-lib/tests/`, reusing `conftest.py` fixtures (`rng`, `brownian`,
`ar1_series`, `sinusoidal`) and adding planted-pattern + surrogate generators.

| Harness (SRS) | File | Asserts (PROPERTIES, not synthetic numbers) |
|---|---|---|
| **II.5.1 Planted-pattern (MANDATORY)** | `test_patterns_planted.py` | construct series with planted H&S / flag / triangle / double-top at known indices; assert each detected within a tolerance window of its true location. Catches over-smoothing (missed plants) and detector bugs. |
| **II.5.2 False-positive (MANDATORY)** | `test_patterns_fpr.py` | on pure random walks, per-pattern detection rate below a documented ceiling (e.g. < 0.5 H&S per 500-pt walk at defaults); planted scores exceed the 95th-pct null score. |
| **II.5.3 Threshold-robustness** | `test_threshold_robustness.py` | series with a quiet + a volatile regime, each with a planted pattern; assert **both** detected — verifies the scale-robust threshold isn't dragged to a single global value (L4). |
| **II.5.4 Determinism** | `test_pattern_determinism.py` | fixed seed ⇒ identical `null_fpr` across runs (NFR-RP1). |
| Denoise round-trip / no-overshoot | `test_denoise.py` | denoised series length == N; dropping 0 bands ≈ identity; energy reduced monotonically with `k_drop`. |
| Swing correctness | `test_swings.py` | strict H/L alternation; min-gap respected; prominence filter removes sub-threshold pivots; argrelextrema used (no bespoke loop). |

**Test-first discipline (Phase 3):** for FR-FPR, write the null-FPR test against a stub and
confirm it flags a deliberately random input *before* implementing the real evaluator (so the
test is meaningful), per the CLAUDE.md harness rule and the prompt-pack note.

The existing Part I harnesses (round-trip, translation-invariance, fGn-Hurst, coherence,
no-leakage, look-ahead, e2e Heston) are untouched and remain green.

---

## 15. Open decisions for the user (flagged, not silently chosen)

1. **NFR-U2 notebooks / matplotlib extra (§12).** Ship an optional `chart_decomp.viz` extra +
   3 notebooks for literal SRS compliance, or treat the React frontend as satisfying the
   visualization intent and skip notebooks? *Design default: skip the extra unless asked.*
2. **Part I clean-up scope (§11).** Include CLI fix / DM wiring / Hurst guard / NFR-RP2 in
   this effort, or split them into a separate small PR series after Part II? *Design default:
   CLI fix + Hurst guard are cheap and worth folding in; DM wiring and NFR-RP2 optional.*
3. **decision-helper bridge.** Out of scope here (§2). Confirm that's acceptable.

---

## 16. Conflicts carried from gap analysis — final resolutions

| Conflict | Resolution (this design) |
|---|---|
| A — plotting vs service+SPA | No matplotlib in service; return plot-ready data, render in React; optional viz extra for notebooks only (§12). |
| B — Part II location/consumer | Build in `chart-decomp-lib`, reuse Part I, leave ai-insights detectors as-is (§2). |
| C — field names (`.H` vs `.hurst`) | Keep `.H`; fix CLI; adopt SRS field names for new Part II entities (§4, §11). |
| D — detector interface | New `IPatternDetector` Protocol + factory registry adapted to project style; do not retrofit ai-insights (§7). |
| E — Hurst stationary input | Add non-binding warning in `hurst_wavelet` (§11.3). |
| F — DM not in metrics | Surface via use-case/API with optional `baseline`; forecasters stay pure (§11.2). |

*Design only — no implementation performed. Next: Phase 2 (`docs/implementation_plan.md`),
an ordered, dependency-aware, PR-sized task list with the harness-introduction points marked.*
