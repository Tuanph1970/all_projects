# Implementation Plan — Null-FPR + Multi-Scale Nesting

**Extends:** an existing single-scale Part II pattern-detection implementation
**Specs:** `docs/SRS_master_chart_system.md` (Part II) + `docs/SRS_submodule_multiscale_nesting.md`
**Format:** PR-sized tasks. Run each with the Phase 3 prompt from `claude_code_prompts.md`,
one at a time. Substitute the task number. Each task ends with "STOP."

> NOTE TO CLAUDE CODE: file paths below are PLACEHOLDERS. During Phase 0 gap analysis you
> mapped the real locations of the denoise, swing-extraction, detector, pipeline, and
> report/UI code. Use those real paths. Where a placeholder says `<detectors_module>`,
> substitute the actual module. Reuse existing code; do not duplicate it. Assert PROPERTIES
> in tests, never the spec's synthetic magnitudes.

---

## SEQUENCING OVERVIEW

```
PART A  (null-FPR — build the significance filter first)
  A1 → A2 → A3 → A4 → A5
PART A.5 (precision gate — decide before going multi-scale)
  A6
PART B  (multi-scale nesting — on top of a working filter)
  B1 → B2 → B3 → B4 → B5 → B6 → B7
```

Do not start Part B until A6's decision is made.

---

# PART A — Populate the Null-FPR Column

## Task A1 — Surrogate (null) series generator
- **Files:** `<stats_or_validation_module>` (new function), `tests/test_null_surrogates.py`
- **Requirement IDs:** FR-FPR-1 (supporting)
- **Do:** Implement `make_surrogate(returns, method='shuffle', seed=None) -> np.ndarray`
  returning a cumulated price path. `method='shuffle'` permutes the real returns (preserves
  return distribution incl. fat tails); `method='gaussian'` draws fresh N(0, std). Match the
  real series length.
- **Tests:**
  - Same seed → identical output; different seed → different output.
  - Shuffled surrogate has the same sorted return multiset as the input (within fp tolerance).
  - Output length equals input length.
- **Depends on:** none.

## Task A2 — Surrogate detection sweep + cache
- **Files:** `<validation_module>`, `tests/test_null_sweep.py`
- **Requirement IDs:** FR-FPR-1
- **Do:** Implement `null_detection_distribution(length, volatility, detector_params,
  n_null=1000, seed=None)` that, for each surrogate, runs the EXISTING
  denoise→swing→detect pipeline and collects, per pattern type: (a) the array of quality
  scores produced, (b) the count of detections per surrogate. Return a structure keyed by
  pattern type. Cache the result keyed by (length, rounded volatility, detector_params hash)
  so repeated chart loads reuse it.
- **Tests:**
  - Returns a per-pattern-type score array and a per-pattern detection-count array.
  - With `n_null` small (e.g. 20) and a fixed seed, output is deterministic.
  - Cache hit returns the same object without re-running (assert via a call counter / spy).
- **Depends on:** A1, existing pipeline.

## Task A3 — Null thresholds (pct95 + FPR)
- **Files:** `<validation_module>`, `tests/test_null_thresholds.py`
- **Requirement IDs:** FR-FPR-1, FR-FPR-2
- **Do:** From A2's distributions compute, per pattern type: `null_pct95` = 95th percentile of
  noise scores, and `fpr` = mean detections per surrogate. Expose
  `null_thresholds(...) -> dict[pattern -> {pct95, fpr}]`.
- **Tests:**
  - pct95 lies within [min, max] of the score array and equals `np.quantile(scores, 0.95)`.
  - A pattern type never produced on nulls yields a sentinel (e.g. pct95=None, fpr=0), handled
    without error.
- **Depends on:** A2.

## Task A4 — Annotate real detections with significance
- **Files:** `<detection_types_module>`, `<pipeline_module>`, `tests/test_significance_annotation.py`
- **Requirement IDs:** FR-FPR-2
- **Do:** Ensure `Detection.null_percentile` is populated: for each real detection, compute the
  percentile of its score within its pattern type's null score distribution, and set a derived
  `noteworthy = score > null_pct95[pattern]`. Thread both through the pipeline result.
- **Tests (MANDATORY — this is the null-FPR gate):**
  - **The known-junk test:** construct/insert a detection with a deliberately low score
    (e.g. the 25%-score descending-triangle case from real output) and assert it is marked
    NOT noteworthy.
  - A detection with a score above the pattern's null pct95 is marked noteworthy.
  - `null_percentile` is in [0, 100] for every annotated detection.
- **Depends on:** A3.

## Task A5 — Surface null-FPR in the report + UI
- **Files:** `<report_module>`, `<ui/table_component>`, `tests/test_report_fpr_column.py`
- **Requirement IDs:** FR-VIZ-2
- **Do:** Fill the "Null pct95" column with the per-pattern pct95 (or the detection's
  `null_percentile`, whichever the column is meant to show — match existing column intent).
  Add a visual "noteworthy" marker (bold / badge / filter toggle). Em-dashes only remain where
  a pattern type had no null distribution.
- **Tests:**
  - Report rows expose a non-dash value when a null distribution exists.
  - Noteworthy flag renders for above-threshold detections.
- **Depends on:** A4.

---

# PART A.5 — Precision Gate (decision task)

## Task A6 — Measure single-scale precision; tune tolerances if needed
- **Files:** `docs/precision_report.md` (new), possibly `<detectors_module>` (tolerance tweaks)
- **Requirement IDs:** L3 (false positives are the core problem)
- **Do:** Run the now-working null filter on a representative real series. Report how many
  detections survive the noteworthy bar vs how many are filtered. If the large majority are
  filtered (the screenshot's 20-detection case suggests loose tolerances), TIGHTEN the detector
  tolerances (e.g. shoulder/neckline/equality thresholds) and re-measure, until single-scale
  precision is acceptable. Write findings + chosen tolerances to `docs/precision_report.md`.
- **Decision rule:** Do NOT proceed to Part B until single-scale false positives are under
  control. Multi-scale will multiply whatever precision problem exists at one scale.
- **Tests:** none new (this is a measurement/tuning task); existing detector tests must still pass
  after any tolerance change.
- **Depends on:** A5.

---

# PART B — Multi-Scale Nesting

## Task B1 — Extend the Detection type (backward-compatible)
- **Files:** `<detection_types_module>`, `tests/test_detection_fields.py`
- **Requirement IDs:** FR-MS (data model, sub-module §MS.4)
- **Do:** Add defaulted fields to `Detection`: `detection_id`, `scale`, `also_seen_at_scales`,
  `parent_id`, `children_ids`, `nesting_depth=0`, `directional_bias`, `relation_to_parent`.
  Assign a unique `detection_id` to every detection at creation. Add the `MultiScaleResult` type.
- **Tests:**
  - Existing single-scale code constructs `Detection` without passing new fields (defaults work).
  - Every detection from the pipeline has a unique `detection_id`.
- **Depends on:** A4 (keeps significance fields intact).

## Task B2 — Multi-scale detection sweep (with per-scale null-FPR)
- **Files:** `<pipeline_module>`, `tests/test_multiscale_sweep.py`
- **Requirement IDs:** FR-MS-1, FR-MS-5 (per-scale FPR)
- **Do:** Implement `detect_multiscale(x, scales=(1,2,3), ...)` that runs the EXISTING pipeline
  at each `k_drop` in `scales`, tags each detection with its `scale`, and computes the null-FPR
  (Part A machinery) SEPARATELY per scale. Return partial `MultiScaleResult` (flat detections +
  per-scale fpr; nesting filled in later tasks).
- **Tests:**
  - Detections carry the correct `scale` tag.
  - Coarser scales yield fewer detections than finer scales on the same series (sanity).
  - `fpr_by_pattern_by_scale` has an entry per scale.
- **Depends on:** B1, A3.

## Task B3 — Cross-scale de-duplication
- **Files:** `<pipeline_module>` or `<nesting_module>`, `tests/test_dedup.py`
- **Requirement IDs:** FR-MS-2
- **Do:** Merge detections that are (a) same pattern type, (b) overlap beyond Jaccard
  `dedup_jaccard=0.7`, (c) differ by ≤1 scale. Keep the higher score; record merged scales in
  `also_seen_at_scales`; set `scale` to the coarsest surviving level.
- **Tests (MANDATORY for B — de-dup test):**
  - A medium pattern present at two adjacent scales appears as ONE detection with
    `also_seen_at_scales` populated, not two.
  - Two genuinely different same-type patterns far apart are NOT merged.
- **Depends on:** B2.

## Task B4 — Build the nesting forest
- **Files:** `<nesting_module>` (new), `tests/test_nesting_forest.py`
- **Requirement IDs:** FR-MS-3
- **Do:** Implement `build_nesting_forest(detections, containment_tol=2)`. C is a child of P iff
  `P.scale > C.scale` AND C's range is within P's range (±tol) AND C lies within a SINGLE LEG of
  P (between two consecutive pivots of P), NOT straddling P's defining pivots. Assign each child
  to its smallest containing parent; set `parent_id`, `children_ids`, `nesting_depth`. Parentless
  detections are roots.
- **Tests (MANDATORY — nested-plant test):**
  - Plant a small pattern (e.g. bull flag) inside the right-shoulder LEG of a large H&S; assert
    the small one's `parent_id` is the large one, `nesting_depth` 0 (large) and 1 (small).
  - **Single-leg guard:** a small detection that straddles a parent's defining pivot is NOT made
    a child (rejected as artifact).
  - No cycles; each non-root has exactly one parent.
- **Depends on:** B3.

## Task B5 — Agreement/conflict annotation
- **Files:** `<nesting_module>`, `<bias_table>`, `tests/test_relation_annotation.py`
- **Requirement IDs:** FR-MS-4
- **Do:** Implement a directional-bias lookup (H&S→bearish, invH&S→bullish, bull flag→bullish,
  bear flag→bearish, double top→bearish, double bottom→bullish, asc triangle→bullish,
  desc triangle→bearish, sym triangle→neutral, broadening→neutral). Set `directional_bias` per
  detection and `relation_to_parent` ∈ {agreement, conflict, neutral} per child. Mark in code/docs
  as DESCRIPTIVE metadata, not a trading signal.
- **Tests:**
  - Bullish child inside bearish parent → `relation_to_parent == 'conflict'`.
  - Bearish child inside bearish parent → `'agreement'`.
  - Neutral-bias pattern → `'neutral'`.
- **Depends on:** B4.

## Task B6 — Spurious-nesting null rate
- **Files:** `<validation_module>`, `tests/test_spurious_nesting.py`
- **Requirement IDs:** FR-MS-5
- **Do:** Run `detect_multiscale` + `build_nesting_forest` on random-walk surrogates (Part A
  machinery) and measure the rate of parent→child links arising by chance;
  set `MultiScaleResult.spurious_nesting_fpr`. A nesting relationship is "noteworthy" only above
  this rate.
- **Tests (MANDATORY — spurious-nesting null test):**
  - `spurious_nesting_fpr` is reported and in [0, ∞) (links per surrogate).
  - On pure-noise input, nesting links are not flagged noteworthy unless above the null rate.
- **Depends on:** B4, A2.

## Task B7 — Report + visualization for nesting
- **Files:** `<report_module>`, `<ui/table_component>`, `<ui/chart_component>`,
  `tests/test_nesting_report.py`
- **Requirement IDs:** FR-MS-6, FR-VIZ-1/2
- **Do:** Add `scale` and `nested in` (parent) columns to the Detection Report; indent/bracket
  children under parents; show `relation_to_parent` (agreement/conflict) and the noteworthy flag.
  Minimum chart change: stratify or color-link nested detections to parents. (Full scale-stratified
  per-row view is a stretch goal.)
- **Tests:**
  - Report renders parent/child indentation and the scale column.
  - A nested child row references its parent's id/label.
- **Depends on:** B5, B6, A5.

---

## Mandatory test checklist (must exist and pass before "done")

| Test | Task | Why |
|---|---|---|
| Surrogate determinism + distribution preserved | A1 | null is honest |
| Known-junk detection marked NOT noteworthy | A4 | the null filter actually works |
| Single-leg guard rejects straddling "children" | B4 | no fake nestings |
| Nested-plant: small-in-large with correct parent link | B4 | nesting works |
| De-dup: same pattern across scales counted once | B3 | no duplicate nodes |
| Spurious-nesting null rate reported + gates noteworthy | B6 | nesting isn't noise |

## Reminders
- Reuse existing denoise/swing/detect/report code (from Phase 0 gap analysis). Don't duplicate.
- Per-scale null-FPR, not one global threshold (FR-MS-5).
- Nesting is containment within a single leg, NOT superposition (sub-module §MS-B2, §MS-B3).
- Agreement/conflict is descriptive metadata, never a trading signal (§MS-B4).
- Commit after each green task.
