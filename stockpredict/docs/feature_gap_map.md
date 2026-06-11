# Feature Gap Map — Null-FPR + Multi-Scale Implementation Plan

**Purpose:** Resolves every placeholder path in `docs/implementation_plan_fpr_multiscale.md`
to the real files/functions already in this codebase. Also records what is already
partially or fully built so tasks can skip or adapt rather than duplicate.

**Surveyed commit:** HEAD (branch `main`, 2026-06-11)
**Library root:** `stock_microservices/chart-decomp-lib/`
**Service root:** `stock_microservices/services/chart-decomp-service/`
**UI root:** `stock_react_javascript/stock-react-app/src/`

---

## 1. Denoising (`k_drop` / drop-finest-bands logic)

**Placeholder in plan:** `<denoise_module>`, `<stats_or_validation_module>`

### Real location

| Symbol | File | Signature |
|---|---|---|
| `WaveletDenoiser` | `chart_decomp/infrastructure/denoise/wavelet_denoiser.py:29` | class |
| `WaveletDenoiser.denoise` | `…/wavelet_denoiser.py:40` | `(self, series: TimeSeries, params: DenoiseParams) -> np.ndarray` |
| `DenoiseParams` | `chart_decomp/domain/value_objects.py:222` | `@dataclass(frozen=True)` with fields `wavelet`, `level`, `k_drop: int = 1`, `method: Literal["drop","soft","hard"] = "drop"` |

The `k_drop` / drop-finest-bands logic lives in `wavelet_denoiser.py:52–57`:

```python
if params.method == "drop":
    denoised = modwt.approximation.copy()
    for j, d in enumerate(modwt.details):
        if j >= params.k_drop:          # keep bands k_drop…J, drop 0…k_drop-1
            denoised = denoised + d
    return denoised
```

Larger `k_drop` → more bands dropped → coarser ("scale-up") denoising. This is
the knob the multi-scale sweep varies (`scales = [1, 2, 3]` in FR-MS-1).

A calibration use-case that already sweeps `k_drop` is at:
`chart_decomp/application/denoise_swings_usecase.py:99` →
`DenoiseSwingtUseCase.calibrate(x, k_drop_values, threshold_values, ...) -> CalibrationResult`.
It is useful as a reference for how to loop `k_drop` without duplicating denoise logic.

---

## 2. Swing extraction

**Placeholder in plan:** `<swing_module>`

### Real location

| Symbol | File | Signature |
|---|---|---|
| `SwingExtractor` | `chart_decomp/infrastructure/swings/swing_extractor.py:27` | class |
| `SwingExtractor.extract` | `…/swing_extractor.py:34` | `(self, series: TimeSeries, params: SwingParams) -> list[Swing]` |
| `SwingParams` | `chart_decomp/domain/value_objects.py:251` | `@dataclass(frozen=True)` with `order`, `threshold_mode`, `threshold`, `atr_period`, `min_gap` |
| `Swing` | `chart_decomp/domain/entities.py:188` | `@dataclass` with `index: int`, `price: float`, `kind: str` |
| `SwingSkeleton` | `chart_decomp/domain/entities.py:203` | wrapper with `.swings`, `.indices`, `.prices`, `.kinds` |

The extractor returns a **strictly-alternating H/L pivot list** (FR-SW-2). The
pipeline converts it to a `SwingSkeleton` before passing to detectors.

---

## 3. Pattern detectors and the detector registry

**Placeholder in plan:** `<detectors_module>`, `<detector_registry>`

### Registry

| Symbol | File | Signature |
|---|---|---|
| `PatternDetectorRegistry` | `chart_decomp/factories/pattern_detector_factory.py:22` | class |
| `default_registry` | `…/pattern_detector_factory.py:91` | module-level singleton |
| `register_detector` | `…/pattern_detector_factory.py:94` | `(detector, name=None) -> None` |
| `detect_patterns` | `…/pattern_detector_factory.py:99` | `(skeleton: SwingSkeleton, x: np.ndarray, detectors: Union[str, Iterable[str]] = "all", params: Optional[dict] = None) -> list[Detection]` |

Pass `detectors="all"` or a list of registered names (strings). The registry sorts
output by `start_index`.

### Built-in detectors (auto-registered at import)

| Class | File | Registered name |
|---|---|---|
| `HeadAndShouldersDetector` | `…/patterns/head_shoulders.py` | `"Head & Shoulders"` |
| `InverseHeadAndShouldersDetector` | `…/patterns/head_shoulders.py` | `"Inverse Head & Shoulders"` |
| `DoubleTopDetector` | `…/patterns/double.py` | `"Double Top"` |
| `DoubleBottomDetector` | `…/patterns/double.py` | `"Double Bottom"` |
| `BullFlagDetector` | `…/patterns/flag_pennant.py` | `"Bull Flag"` |
| `BearFlagDetector` | `…/patterns/flag_pennant.py` | `"Bear Flag"` |
| `SymmetricTriangleDetector` | `…/patterns/triangle.py` | `"Symmetric Triangle"` |
| `AscendingTriangleDetector` | `…/patterns/triangle.py` | `"Ascending Triangle"` |
| `DescendingTriangleDetector` | `…/patterns/triangle.py` | `"Descending Triangle"` |

### Base class

`PatternDetectorBase` in `…/patterns/base.py:16` — interface: subclasses set `name: str`
and implement `detect(skeleton, x, params) -> list[Detection]`.

### Tolerance parameter value objects

`HSParams`, `FlagParams`, `TriangleParams`, `DoubleParams` are all in
`chart_decomp/domain/value_objects.py:281–338`. These are the knobs for Task A6.

---

## 4. The `Detection` type

**Placeholder in plan:** `<detection_types_module>`

### Real location

`chart_decomp/domain/entities.py:229`

```python
@dataclass
class Detection:
    pattern: str
    start_index: int
    end_index: int
    pivots: list[int]
    score: float
    null_percentile: Optional[float] = None   # ← already exists (see §6)
    confirmed: bool = True
    details: dict = field(default_factory=dict)
```

Also in same file at line 255:

```python
@dataclass
class PatternPipelineResult:
    raw: np.ndarray
    denoised: np.ndarray
    swings: list[Swing]
    detections: list[Detection]
    fpr_by_pattern: dict
```

The JSON transport schema mirror lives in:
`services/chart-decomp-service/app/api/schemas.py:342` → `DetectionInfo` (Pydantic).

---

## 5. End-to-end pipeline that produces detections

**Placeholder in plan:** `<pipeline_module>`

There are **two** orchestration layers — use the library use-case for new
algorithmic work; the service wrapper is only for HTTP transport.

### Library use-case (canonical)

`chart_decomp/application/run_pattern_pipeline_usecase.py:53` →
`RunPatternPipelineUseCase.execute`

```python
def execute(
    self,
    x: np.ndarray,
    *,
    denoise_params: Optional[DenoiseParams] = None,
    swing_params: Optional[SwingParams] = None,
    detectors: Union[str, Iterable[str]] = "all",
    compute_fpr: bool = True,
    fpr_params: Optional[NullFPRParams] = None,
) -> PatternPipelineResult
```

Orchestrates: denoise → swings → detect → right-edge confirmation flag → (optional)
null FPR annotation. Module-level `_edge_lag(params)` at line 37 computes the
right-edge COI half-width.

The use-case instantiates its own `WaveletDenoiser` and `SwingExtractor`; it calls
`detect_patterns` (the registry facade) and `null_fpr` (the validator).

### Service wrapper (HTTP only — do not call from library code)

`services/chart-decomp-service/app/services/decomp_service.py:406` →
`run_pattern_pipeline(req: PatternPipelineRequest) -> PatternPipelineResponse`

Internally calls `_build_detect_response` + `null_fpr` directly (duplicates some
logic from the use-case). For multi-scale work, extend the **library use-case**,
then add a new service endpoint and schema.

### Helper: internal `_build_detect_response`

`decomp_service.py:366` → `_build_detect_response(req) -> (denoised, swings, dets)`
— a private helper that runs denoise + extract + detect without FPR. The
multi-scale sweep (`detect_multiscale`) can mirror its pattern for each `k_drop`
level by calling the library use-case directly with `compute_fpr=False`.

---

## 6. Detection Report table / "Null pct95" column

**Placeholder in plan:** `<report_module>`, `<ui/table_component>`

### React component

`components/Pages/ChartDecomp/index.js:879` → `PatternTab` function component.

The Detection Report table is rendered inline at **lines 1038–1081**:

```jsx
// Header columns (line 1047)
['col_pattern','col_start','col_end','col_score','col_confirmed','col_null_pct']

// "Null pct95" cell (line 1074)
{d.null_percentile != null ? `${(d.null_percentile*100).toFixed(0)}%` : '—'}
```

The column key `col_null_pct` maps to i18n key `chart_decomp.patterns.col_null_pct`.
The cell renders `—` (em-dash) when `d.null_percentile` is null — which is the
**current always-on state** because `compute_fpr: false` is hardcoded in the `run()`
call at line 892:

```js
const resp = await chartDecompService.patternPipeline({
  series,
  k_drop: kDrop,
  threshold,
  compute_fpr: false,   // ← this makes null_percentile always null
});
```

Task A5 must change this to `compute_fpr: true` (or add a UI toggle) and also add
the "noteworthy" badge logic alongside the existing `d.null_percentile` value.

### Service JS client

`services/chartDecompService.js` — wraps `POST /stock_helper/api/v2/chart-decomp/patterns/pipeline`.

---

## 7. Existing surrogate / null / Monte-Carlo / validation code

**Placeholder in plan:** `<stats_or_validation_module>`, `<validation_module>`

### Already fully implemented

| Symbol | File | Signature | Notes |
|---|---|---|---|
| `random_walk_surrogates` | `chart_decomp/infrastructure/validation/surrogates.py:19` | `(length, volatility, n=1000, *, seed=None, start=0.0) -> Iterator[np.ndarray]` | Gaussian only (`method='gaussian'` equivalent). **No `method='shuffle'` yet.** |
| `estimate_volatility` | `…/surrogates.py:64` | `(x: np.ndarray) -> float` | `std(diff(x))` |
| `null_fpr` | `chart_decomp/infrastructure/validation/null_fpr.py:64` | `(length, volatility, detectors="all", params=None, swing_params=None) -> NullFPRResult` | Runs the full pipeline on `n_null` surrogates. |
| `is_noteworthy` | `…/null_fpr.py:139` | `(detection: Detection, null_result: NullFPRResult) -> bool` | `score > pct95`, unconditionally True if pattern never appeared in null. |
| `NullFPRResult` | `…/null_fpr.py:41` | `@dataclass` with `fpr_by_pattern`, `score_pct95_by_pattern`, `n_null`, `length`, `volatility` | |
| `NullFPRParams` | `chart_decomp/domain/value_objects.py:342` | `@dataclass(frozen=True)` with `n_null=1000`, `noteworthy_pct=95.0`, `seed=None` | |

### Test coverage (already written)

| Test file | What it tests |
|---|---|
| `tests/test_surrogates.py` | Shape, volatility match, reproducibility, validation |
| `tests/test_null_fpr.py` | Structure, determinism, FPR ceiling (H&S < 1.0), `is_noteworthy` unit, planted-H&S noteworthy |

### No caching exists

The `null_fpr()` function reruns from scratch on every call. Task A2's cache
(keyed by `(length, rounded_volatility, detector_params_hash)`) does **not** exist
yet and must be added alongside `null_detection_distribution()`.

---

## 8. What is ALREADY partially built (tasks can reuse)

This is the most important section for avoiding duplication.

### A1 — Surrogate generator: **~80% done**

`random_walk_surrogates` (`surrogates.py:19`) already implements the Gaussian
random-walk path (corresponding to `method='gaussian'` in the plan). It is lazy
(generator), seeded, validated, and tested.

**Gap:** The plan additionally requires `method='shuffle'` (permute the real
returns to preserve the fat-tail distribution). Add a new
`make_surrogate(returns, method='shuffle'|'gaussian', seed=None) -> np.ndarray`
wrapper that reuses `random_walk_surrogates` for the Gaussian case and adds the
shuffle case. The new function signature should accept `returns` (not `length +
volatility`) so both methods share the same call site.

### A2 — Null detection sweep: **~60% done**

`null_fpr()` (`null_fpr.py:64`) already runs the sweep and collects per-pattern
scores and counts. It returns `score_pct95_by_pattern` and `fpr_by_pattern`.

**Gaps:**
1. It does not expose the **raw score arrays** (only the pre-aggregated pct95).
   Task A2 needs the full array so A3 can compute arbitrary percentiles and the
   raw count arrays.
2. No **caching** layer exists.
3. The surrogate source is only Gaussian; once A1 adds `method='shuffle'`, A2
   should accept a `method` parameter and pass it through.

Recommended approach: add `null_detection_distribution()` as a thin wrapper
around a refactored `null_fpr()` that also returns the raw arrays, then keep the
existing `null_fpr()` for backward compatibility.

### A3 — Null thresholds: **fully done as an inline step**

`null_fpr.py:124–127` already computes:
```python
score_pct95 = {
    p: float(np.percentile(scores, params.noteworthy_pct))
    for p, scores in all_scores.items()
}
```
The `noteworthy_pct` parameter defaults to 95 (matching FR-FPR-2).

**Gap:** No standalone `null_thresholds()` function is exposed. Task A3 can
simply extract this logic into a public function once A2 exposes the raw arrays.
The sentinel for "never appeared" (pct95 = None) is already handled by
`is_noteworthy()` returning `True` unconditionally.

### A4 — Annotate detections: **field exists, population is wrong**

`Detection.null_percentile` (`entities.py:249`) already exists as
`Optional[float] = None`.

**Critical gap — semantic mismatch:** The pipeline currently sets
`d.null_percentile = pct95.get(d.pattern)` (run_pattern_pipeline_usecase.py:139),
which stores the **null's 95th-percentile score threshold** in the field, NOT the
detection's percentile rank within the null distribution. The field name implies
the latter.

Task A4 must decide the field's intended value and fix one of:
- Rename to `null_pct95_threshold` (the threshold a detection must exceed), or
- Compute the actual rank: `percentileofscore(null_scores[pattern], d.score)` and
  store that (0–100) as `null_percentile`.

The plan (A4) says "compute the percentile of its score within its pattern type's
null score distribution" — so A4 should fix the field to store the rank (requires
A2's raw score arrays). A `noteworthy: bool` derived field does **not** exist yet
on `Detection` or `DetectionInfo` and must be added.

### A5 — Surface in UI: **column exists, always shows `—`**

The "Null pct95" column is rendered in `PatternTab` at `index.js:1074`. It is
already wired to `d.null_percentile`.

**Gap:** `compute_fpr: false` is hardcoded at `index.js:892`. The column will fill
automatically once A4 populates `null_percentile` correctly AND the UI switches to
`compute_fpr: true`. The "noteworthy" badge is absent and must be added alongside.

### B1 — Multi-scale Detection fields: **none exist yet**

The plan's new fields (`detection_id`, `scale`, `also_seen_at_scales`, `parent_id`,
`children_ids`, `nesting_depth`, `directional_bias`, `relation_to_parent`) are all
absent from `Detection`. `MultiScaleResult` does not exist. These are pure additions
with defaulted fields (backward-compatible).

### Tasks B2–B7: **not started**

No `detect_multiscale`, `build_nesting_forest`, or `annotate_relations` functions
exist anywhere in the codebase.

---

## 9. Concrete module-path substitutions for the implementation plan

Replace every placeholder in the plan with these real paths:

| Placeholder | Real path |
|---|---|
| `<denoise_module>` | `chart_decomp/infrastructure/denoise/wavelet_denoiser.py` |
| `<swing_module>` | `chart_decomp/infrastructure/swings/swing_extractor.py` |
| `<detectors_module>` | `chart_decomp/infrastructure/patterns/` (per-pattern files) |
| `<detector_registry>` | `chart_decomp/factories/pattern_detector_factory.py` |
| `<detection_types_module>` | `chart_decomp/domain/entities.py` |
| `<pipeline_module>` | `chart_decomp/application/run_pattern_pipeline_usecase.py` |
| `<stats_or_validation_module>` | `chart_decomp/infrastructure/validation/surrogates.py` |
| `<validation_module>` | `chart_decomp/infrastructure/validation/null_fpr.py` |
| `<nesting_module>` (new) | `chart_decomp/application/multiscale_pipeline_usecase.py` (to be created) |
| `<report_module>` | `services/chart-decomp-service/app/api/schemas.py` + `app/services/decomp_service.py` |
| `<ui/table_component>` | `components/Pages/ChartDecomp/index.js` → `PatternTab` at line 879 |
| `<ui/chart_component>` | `components/Pages/ChartDecomp/index.js` → panels in `PatternTab` (lines 952–1036) |
| `<bias_table>` | add as a `dict` constant in the new nesting module |

---

## 10. Recommended new files

| Plan task | Suggested file | Why new |
|---|---|---|
| A1 (shuffle surrogate) | extend `surrogates.py` | small addition to existing module |
| A2 (distribution + cache) | extend `null_fpr.py` | new `null_detection_distribution()` alongside `null_fpr()` |
| A3 (thresholds fn) | extend `null_fpr.py` | trivial extraction once A2 raw arrays exist |
| B1 (`MultiScaleResult`) | extend `entities.py` | part II domain model |
| B2–B6 (multiscale sweep, dedup, nesting forest, annotation, spurious FPR) | **new** `chart_decomp/application/multiscale_pipeline_usecase.py` | new orchestration layer; keeps single-scale usecase unchanged |
| B7 (report + viz) | extend `decomp_service.py` + `index.js` | add endpoint + UI columns |

---

*End of gap map.*
