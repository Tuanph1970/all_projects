# Sub-Module Specification: Multi-Scale Nested Pattern Detection

## An Extension to Part II (Pattern Detection System) of the Master SRS

**Document version:** 1.0
**Date:** 2026-05-29
**Status:** Draft
**Extends:** `SRS_master_chart_system.md`, Part II (§II.3 Specific Requirements, §II.4 Data Models)
**New requirement IDs:** FR-MS-1 … FR-MS-6
**Module section number (when merged):** II.3.8 (placed after II.3.7 Non-Functional Requirements)

---

## MS.1 Purpose and Motivation

The base Part II pipeline denoises the series **once** (a single `k_drop`) and detects patterns at that single scale. Real charts contain patterns at **multiple scales simultaneously**: a large formation traced by the major swings, with smaller formations nested inside its individual legs.

The relationship is **nesting, not superposition.** Patterns do not add together the way sine waves do — there is no additive, unique, orthogonal decomposition of a chart into patterns. Instead, the same calendar range can be described by a large-scale pattern and, within one of its legs, a small-scale pattern at finer resolution. The two coexist at different zoom levels, like bays containing coves containing inlets along a coastline.

This sub-module specifies how to detect patterns across several scales and organize the results into a **nesting tree** (parent → child by date-range containment), so that a single date range yields a structured set of detections tagged by scale and nesting relationship rather than a single flat label.

### MS.1.1 Explicit non-goal

This sub-module does **not** attempt to "add" or "superpose" patterns into a composite shape. Any framing that treats patterns as an additive basis (analogous to a Fourier sum) is out of scope and is, per the empirical findings in Part III, conceptually incorrect. Patterns are geometric shape-labels, not basis functions.

---

## MS.2 Concept

The wavelet denoising layer (Part II Layer 1, FR-DN-1) already controls which scale of swings survives, via the number of finest detail bands dropped (`k_drop`):

- **Aggressive denoising** (large `k_drop`, e.g. drop D1–D3) removes small wiggles; only major swings survive → the swing extractor returns few, large pivots → detectors find **large-scale** patterns.
- **Gentle denoising** (small `k_drop`, e.g. drop D1 only) retains medium/small swings → the extractor returns many pivots → detectors find **small-scale** patterns.

Running the existing single-scale pipeline at several `k_drop` levels therefore surfaces patterns at several scales. A small-scale detection whose date range falls within the date range of a large-scale detection (and within one of its legs) is **nested** inside it. Collecting these containment relationships yields a forest of nesting trees.

---

## MS.3 Specific Requirements

### FR-MS-1 Multi-scale detection sweep
- The system SHALL provide a routine that runs the existing detection pipeline (denoise → swing extraction → detectors, per Part II §II.3.1–II.3.3) at an ordered set of denoising levels `k_drop ∈ scales` (default `scales = [1, 2, 3]`, coarsest last).
- Each resulting detection SHALL be tagged with the `scale` (the `k_drop` value) at which it was found.
- All other per-scale parameters (swing `order`, `min_prominence`, detector tolerances) MAY be specified per scale or inherited from a single default; if scale-dependent, the chosen values SHALL be recorded on each detection's provenance.
- The sweep SHALL reuse the existing single-scale pipeline unchanged; it is a loop and reconciliation layer on top, not a reimplementation.

### FR-MS-2 Cross-scale de-duplication
- The same pattern may be detected at adjacent scales (e.g. a medium head-and-shoulders surviving both `k_drop=1` and `k_drop=2`). The system SHALL merge near-duplicate detections that (a) are the same pattern type, (b) overlap in date range beyond a configurable Jaccard threshold (default 0.7), and (c) differ in scale by at most one level.
- When merging, the detection with the higher quality `score` SHALL be retained; its `scale` SHALL record the coarsest level at which it survived, and a `also_seen_at_scales` list SHALL record the others.

### FR-MS-3 Nesting relationship construction
- After de-duplication, the system SHALL construct parent → child links by date-range containment: detection *C* is a **child** of detection *P* if and only if:
  1. *P* was found at a strictly coarser scale than *C* (`P.scale > C.scale`), AND
  2. *C*'s `[start_index, end_index]` is contained within *P*'s `[start_index, end_index]` (with a small tolerance, default 2 samples), AND
  3. *C* lies within a single **leg** of *P* (between two consecutive pivots of *P*), not spanning *P*'s defining pivots.
- Each child SHALL have exactly one parent: the **smallest-range** containing detection that satisfies the above (the immediate encloser). Detections with no enclosing parent are **roots**.
- The result is a forest of trees. Cycles are impossible by construction (parents are strictly coarser-scale).

### FR-MS-4 Conflict / agreement annotation
- For each parent → child relationship, the system SHALL annotate whether the nested pattern's directional bias **agrees** with or **conflicts** with the enclosing pattern's bias (e.g. a bullish flag nested in the right shoulder of a bearish head-and-shoulders is a CONFLICT; a bull flag nested in the up-leg of an ascending triangle is AGREEMENT).
- Directional bias per pattern type SHALL be defined in a lookup table (e.g. H&S → bearish, inverse H&S → bullish, bull flag → bullish, double top → bearish). Patterns without a clear directional bias (symmetric triangle, broadening formation) SHALL be annotated NEUTRAL.
- This annotation is advisory metadata, not a trading signal; it carries no predictive claim (consistent with Part II constraint L3 and Part III findings).

### FR-MS-5 Null-FPR per scale (MANDATORY)
- The mandatory null-FPR comparison (Part II FR-FPR-1) SHALL be computed **per scale**, because false-positive rates differ across denoising levels (gentler denoising yields more pivots and more spurious patterns).
- The system SHALL additionally report the false-positive rate of **spurious nesting**: the rate at which the multi-scale pipeline reports parent → child links on random-walk null series. Nesting that occurs no more than the null rate is not noteworthy.

### FR-MS-6 Output and visualization
- The multi-scale routine SHALL return a `MultiScaleResult` (see MS.4) containing the flat detection list (scale-tagged, de-duplicated) and the nesting forest.
- Visualization SHALL extend Part II FR-VIZ-1 with a scale-stratified view: each scale's denoised series and detections on its own row, with nested children visually linked to their parents (e.g. bracket or color inheritance).
- The detection report (FR-VIZ-2) SHALL be extended to show, per detection: scale, parent (if any), nesting depth, and agreement/conflict annotation.

---

## MS.4 Data Model Extensions

The existing `Detection` dataclass (Part II §II.4) is extended with scale and nesting fields. New fields are optional with defaults so existing single-scale code continues to work unchanged.

```python
@dataclass
class Detection:
    pattern: str
    start_index: int
    end_index: int
    pivots: list[int]
    score: float
    null_percentile: float | None = None
    # --- multi-scale extension fields ---
    detection_id: int | None = None          # unique handle within a run
    scale: int | None = None                 # k_drop level it was found at
    also_seen_at_scales: list[int] = field(default_factory=list)
    parent_id: int | None = None             # immediate enclosing detection, or None if root
    children_ids: list[int] = field(default_factory=list)
    nesting_depth: int = 0                    # 0 for roots, 1 for their children, ...
    directional_bias: str | None = None       # 'bullish' | 'bearish' | 'neutral'
    relation_to_parent: str | None = None      # 'agreement' | 'conflict' | 'neutral' | None

@dataclass
class MultiScaleResult:
    raw: np.ndarray
    denoised_by_scale: dict[int, np.ndarray]   # k_drop -> denoised series
    detections: list[Detection]                 # flat, de-duplicated, scale-tagged
    roots: list[int]                            # detection_ids with no parent
    fpr_by_pattern_by_scale: dict[int, dict[str, float]]
    spurious_nesting_fpr: float                  # null rate of parent->child links
```

### MS.4.1 Public API

```python
# Multi-scale sweep + nesting reconciliation
detect_multiscale(
    x,
    scales=(1, 2, 3),                  # k_drop levels, fine -> coarse
    denoise_kw=None,                   # per-scale or shared denoise params
    swing_kw=None,                     # per-scale or shared swing params
    detectors='all',
    dedup_jaccard=0.7,                 # FR-MS-2 overlap threshold
    containment_tol=2,                 # FR-MS-3 date-range tolerance (samples)
    compute_fpr=True,                  # FR-MS-5
    n_null=1000,
    seed=None,
) -> MultiScaleResult

# Helpers (may be public or internal)
build_nesting_forest(detections, containment_tol=2) -> list[Detection]   # sets parent/child/depth
annotate_relations(detections, bias_table=None) -> None                  # sets directional_bias, relation_to_parent
```

---

## MS.5 Validation and Test Requirements

### FR-MS-TEST-1 Nested-plant test (MANDATORY)
- Construct a synthetic series with a **large** pattern (e.g. head-and-shoulders) whose right shoulder contains a **small** pattern (e.g. a bull flag) at a finer scale.
- Assert that `detect_multiscale` returns BOTH patterns, that the small one's `parent_id` points to the large one, that `nesting_depth` is 0 for the large and 1 for the small, and that the small pattern's date range lies within a single leg of the large one.

### FR-MS-TEST-2 No-spurious-superposition test
- Construct a series that is a single clean large pattern with NO nested sub-pattern.
- Assert the pipeline does NOT invent a nested child inside it beyond the per-scale null-FPR rate.

### FR-MS-TEST-3 De-duplication test
- Construct a medium pattern that survives two adjacent denoising levels.
- Assert it appears as ONE detection after de-duplication, with `also_seen_at_scales` populated, not as two separate detections.

### FR-MS-TEST-4 Conflict-annotation test
- Plant a bullish small pattern inside the reversal leg of a bearish large pattern.
- Assert `relation_to_parent == 'conflict'`.

### FR-MS-TEST-5 Spurious-nesting null test (MANDATORY)
- Run `detect_multiscale` on random-walk nulls and assert `spurious_nesting_fpr` is reported and that no nesting relationship is flagged "noteworthy" unless it exceeds the null rate.

---

## MS.6 Default Parameters

| Parameter | Default | Notes |
|---|---|---|
| `scales` (k_drop levels) | (1, 2, 3) | fine → coarse; extend to (1,2,3,4) for long series |
| De-dup Jaccard threshold | 0.7 | merge same-type overlapping detections across adjacent scales |
| Containment tolerance | 2 samples | slack when testing date-range containment |
| Null surrogates per scale | 1000 | FR-MS-5 |
| Directional bias table | H&S→bearish, invH&S→bullish, bull flag→bullish, bear flag→bearish, double top→bearish, double bottom→bullish, asc triangle→bullish, desc triangle→bearish, sym triangle→neutral, broadening→neutral | configurable |

---

## MS.7 Known Limitations and Traps (Sub-Module Specific)

**MS-B1 — Scale count vs cost.** Each added scale is a full pipeline run plus a full null-FPR sweep. Cost is roughly linear in `len(scales)`. Three scales is a sensible default; do not sweep dozens.

**MS-B2 — Containment is necessary but not sufficient for true nesting.** A small pattern whose dates fall inside a large one is only *genuinely* nested if it sits within a single leg (FR-MS-3 condition 3). A "child" that straddles the large pattern's defining pivots is an artifact of overlapping windows, not a real nesting, and MUST be rejected.

**MS-B3 — Nesting is not superposition (reiterated).** The nesting tree records "this small shape appears inside that leg of this big shape." It does NOT mean the two patterns sum to the observed price. Do not document or present it as an additive decomposition.

**MS-B4 — The agreement/conflict annotation is descriptive, not predictive.** Per Part II L3 and Part III, the system makes no claim that a conflict resolves in either direction. The annotation only flags that a shorter-scale bias differs from a longer-scale one, which a human may weigh.

**MS-B5 — Edge effects compound across scales.** Coarser denoising has a wider cone of influence (Part I §C2). A large pattern detected near the right edge is even less reliable than a small one there. The right-edge caution applies most strongly to the coarsest scale.

---

## MS.8 Integration Notes (for merging into the master SRS)

- Insert §MS.3 as **§II.3.8 Multi-Scale Nested Detection**, after §II.3.7.
- Extend the `Detection` dataclass in **§II.4** with the fields in MS.4; add `MultiScaleResult` alongside `PipelineResult`.
- Add the `detect_multiscale` entry to the §II.4 public API listing.
- Append FR-MS-TEST-1 … FR-MS-TEST-5 to **§II.5** validation requirements (FR-MS-TEST-1 and -5 are MANDATORY, matching the existing mandatory-test convention).
- Add the MS.6 defaults to the **§II.A** parameter table and the MS.7 traps to **§II.B**.
- Cross-reference: this sub-module depends on the cone-of-influence handling (Part I §C2), the null-FPR discipline (Part II FR-FPR), and the no-predictive-claim constraint (Part II L3, Part III principles).

---

*End of sub-module specification.*
