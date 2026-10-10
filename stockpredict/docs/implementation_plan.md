# Implementation Plan — Chart Decomposition & Pattern Detection System

**Phase 2 artifact** (plan only — no code).
**Date:** 2026-05-30
**Inputs:** `docs/design.md`, `docs/srs_gap_analysis.md`, `docs/SRS_master_chart_system.md`

---

## How to use this plan

- **One task per Phase-3 session.** Each task is PR-sized: implement, write its tests
  (test-first where marked), show them green, then STOP.
- Tasks are grouped into two tracks. **Track A** (Part II pattern system) is the main line
  and is strictly ordered by dependency. **Track B** (Part I clean-ups) is independent and
  can interleave at any time.
- "**∥ parallel**" marks tasks with no dependency on each other (can be done in any order or
  by different sessions).
- Every task closes by updating `roadmap_version_2.xlsx` (CD Tasks status + a Session Log
  row) per CLAUDE.md.

### Sequencing rules honored (from the prompt pack / SRS)

1. **Decomposition engine before the pattern layer.** Part I's MODWT engine already exists
   (CD-1 Done), so the Layer-1 denoiser (A2) can reuse it immediately — the ordering
   constraint is satisfied by A2 depending on the existing engine, and all detectors
   depending on A2/A3.
2. **Each validation harness ships with the code it validates** — the planted-pattern test
   grows inside the detector tasks (A6–A9); the null-FPR test is written *test-first against
   a stub* in A11; threshold-robustness and determinism land with the pipeline (A14/A15).
3. The mandatory L3 null-FPR machinery is sequenced as early as the detectors allow, not
   bolted on at the end.

### Adopting this plan into the roadmap

Before A1, add **CD-6xx rows** to the `CD Tasks` sheet of `roadmap_version_2.xlsx` (one per
task below) and point its header at `docs/SRS_master_chart_system.md`. *(This is a workbook
edit, listed here as task A0 so it isn't forgotten.)*

---

## Track A — Part II Pattern Detection System

### A0 — Roadmap rows for Part II
- **Files:** `roadmap_version_2.xlsx` (CD Tasks + CD Overview).
- **Satisfies:** project bookkeeping (CLAUDE.md).
- **Done when:** CD-601…CD-6xx rows exist mapping 1:1 to A1–A17; CD Tasks header references the master SRS.
- **Deps:** none.

### A1 — Part II domain types
- **Creates/modifies:** `domain/entities.py` (+`Swing`, `SwingSkeleton`, `Detection`,
  `PatternPipelineResult`); `domain/value_objects.py` (+`DenoiseParams`, `SwingParams`,
  `HSParams`, `FlagParams`, `TriangleParams`, `DoubleParams`, `NullFPRParams`);
  `domain/interfaces.py` (+`IDenoiser`, `ISwingExtractor`, `IPatternDetector`,
  `INullEvaluator`).
- **Satisfies:** SRS §II.4 data models; FR-PAT-EXT contract; gap-analysis Conflict C/D.
- **Tests (`tests/test_pattern_domain.py`):** frozen-param validation (`__post_init__`
  raises on bad values), `Detection`/`Swing` construction, `SwingSkeleton.indices/kinds`
  views; reuse of existing `TimeSeries` for input validation.
- **Deps:** none (pure dataclasses).

### A2 — Layer 1: wavelet denoiser  ∥ (with A4)
- **Creates:** `infrastructure/denoise/wavelet_denoiser.py`.
- **Modifies:** `application/hybrid_pipeline_usecase.py` — factor the band-drop logic
  (current lines 82–86) into the denoiser and call it from `hybrid_a`; remove the dead
  duplicate block (lines 71–79).
- **Satisfies:** FR-DN-1 (band-drop `method="drop"` + universal-threshold `soft`/`hard`).
- **Reuses:** `MODWTDecomposer`, `MODWTResult`, `pywt` thresholding.
- **Tests (`tests/test_denoise.py`):** output length == N; `k_drop=0` ≈ identity (≤1e-10);
  energy decreases monotonically with `k_drop`; soft/hard reduce high-freq variance;
  `hybrid_a` still passes its existing tests (no regression).
- **Deps:** A1.

### A3 — Layer 2a: swing extractor
- **Creates:** `infrastructure/swings/swing_extractor.py`.
- **Satisfies:** FR-SW-1 (argrelextrema, **not** hand-rolled — L2), FR-SW-2 (alternating
  skeleton), FR-SW-3 (range-frac / ATR / absolute threshold modes — L4).
- **Reuses:** `scipy.signal.argrelextrema`; ATR formula harvested from
  `ai-insights .../continuation.py::_rolling_atr` (re-expressed close-only).
- **Tests (`tests/test_swings.py`):** strict H/L alternation; `min_gap` respected;
  sub-threshold pivots removed; each threshold mode behaves (range-frac vs ATR differ on a
  two-regime series); asserts `argrelextrema` is the primitive (no bespoke loop).
- **Deps:** A1 (operates on a denoised array; A2 not strictly required to test on raw input,
  but pipeline use is post-denoise).

### A4 — Random-walk surrogate generator  ∥ (with A2)
- **Creates:** `infrastructure/validation/surrogates.py`.
- **Satisfies:** prerequisite for FR-FPR-1; NFR-RP1 (seeded).
- **Tests (`tests/test_surrogates.py`):** length & per-step volatility match target; fixed
  seed → identical output (determinism); different seed → different output.
- **Deps:** A1.

### A5 — Detector base + registry/factory
- **Creates:** `infrastructure/patterns/base.py` (shared geometry: line fit, range-frac,
  scoring base), `factories/pattern_detector_factory.py` (`register_detector`,
  `detect_patterns`, default registry).
- **Satisfies:** FR-PAT-EXT (registry; leaves room for FR-ML-1).
- **Reuses:** mirrors `factories/decomposer_factory.py` registry style.
- **Tests (`tests/test_pattern_registry.py`):** register/override; `detect_patterns` runs
  all and aggregates; empty/short skeleton returns `[]` (no exception).
- **Deps:** A1.

### A6 — Head & Shoulders detector (+ inverse)
- **Creates:** `infrastructure/patterns/head_shoulders.py`.
- **Satisfies:** FR-PAT-HS, FR-SCORE-1 (shoulder symmetry × neckline flatness × prominence).
- **Reuses:** geometry harvested from `ai-insights .../reversal.py` H&S, re-expressed on the
  swing skeleton with scale-robust tolerances.
- **Tests:** **introduces `tests/test_patterns_planted.py` (II.5.1 MANDATORY)** with a planted
  H&S + inverse H&S; assert detected within a tolerance window of the true location.
- **Deps:** A3, A5.

### A7 — Double top / bottom detector  ∥ (with A6, A8, A9)
- **Creates:** `infrastructure/patterns/double.py`.
- **Satisfies:** FR-PAT-DT, FR-SCORE-1.
- **Tests:** extend `test_patterns_planted.py` with planted double-top/bottom (II.5.1).
- **Deps:** A3, A5.

### A8 — Flag / Pennant detector  ∥ (with A6, A7, A9)
- **Creates:** `infrastructure/patterns/flag_pennant.py`.
- **Satisfies:** FR-PAT-FLAG (pole + consolidation; parallel⇒flag, converging⇒pennant via
  bound-line slope fit), FR-SCORE-1.
- **Tests:** extend `test_patterns_planted.py` with a planted flag (II.5.1); a parallel vs
  converging consolidation classifies correctly.
- **Deps:** A3, A5.

### A9 — Triangle detector (asc / desc / symmetric)  ∥ (with A6, A7, A8)
- **Creates:** `infrastructure/patterns/triangle.py`.
- **Satisfies:** FR-PAT-TRI (slope-pair classification), FR-SCORE-1.
- **Tests:** extend `test_patterns_planted.py` with a planted triangle (II.5.1).
- **Deps:** A3, A5.

### A10 — Default registry population
- **Modifies:** `factories/pattern_detector_factory.py` to register A6–A9 under `"all"`.
- **Satisfies:** FR-PAT-EXT default set.
- **Tests:** `detect_patterns(..., "all")` runs every detector; consolidated planted series
  (all four patterns present) detects all four (II.5.1 end-to-end).
- **Deps:** A6, A7, A8, A9.

### A11 — Null-FPR evaluator + significance gate  ⚠️ test-first
- **Creates:** `infrastructure/validation/null_fpr.py`.
- **Satisfies:** FR-FPR-1 (per-pattern FPR on random-walk null), FR-FPR-2 (95th-pct
  noteworthy gate).
- **Test-first (per CLAUDE.md / prompt pack):** in `tests/test_patterns_fpr.py`, first write
  the FPR test against a **stub** detector and confirm it flags a deliberately random input
  (the test must be meaningful before the real evaluator exists); then implement until green.
- **Tests (`tests/test_patterns_fpr.py`, II.5.2 MANDATORY):** per-pattern detection rate on
  pure random walks below a documented ceiling (e.g. < 0.5 H&S per 500-pt walk at defaults);
  planted-pattern score > 95th-pct null score for the same pattern.
- **Deps:** A4 (surrogates), A10 (full detector set), A2/A3 (pipeline pieces).

### A12 — End-to-end pipeline use-case + facade
- **Creates:** `application/run_pattern_pipeline_usecase.py`.
- **Modifies:** `chart_decomp/__init__.py` (facade: `denoise`, `extract_swings`,
  `register_detector`, `detect_patterns`, `null_fpr`, `run_pattern_pipeline`).
- **Satisfies:** end-to-end FR-DN→FR-SW→FR-PAT→FR-FPR flow; **B6/C2 live-edge
  `confirmed=False`** flag derived from `MODWTResult.coi_widths`.
- **Tests (`tests/test_pattern_pipeline.py`):** `run_pattern_pipeline` returns a populated
  `PatternPipelineResult` (raw/denoised/swings/detections/fpr); `compute_fpr=True` by
  default; right-edge detections flagged `confirmed=False`.
- **Deps:** A2, A3, A10, A11.

### A13 — Joint denoise↔swing calibration  ∥ (after A12)
- **Creates:** `application/denoise_swings_usecase.py`; facade `calibrate_denoise_swings`.
- **Satisfies:** FR-DN-2 (L1 coupling).
- **Tests:** sweep returns a `{k_drop, threshold, n_swings}` table; `recall` column
  populated when planted locations are supplied.
- **Deps:** A2, A3.

### A14 — Threshold-robustness harness
- **Creates:** `tests/test_threshold_robustness.py`.
- **Satisfies:** II.5.3 (L4 verification).
- **Tests:** two-regime series (quiet + volatile), each with a planted pattern; assert
  **both** detected — the scale-robust threshold isn't dragged to one global value.
- **Deps:** A12.

### A15 — Determinism harness
- **Creates:** `tests/test_pattern_determinism.py`.
- **Satisfies:** II.5.4 / NFR-RP1.
- **Tests:** fixed seed ⇒ identical `null_fpr` results across runs.
- **Deps:** A11.

### A16 — Service API: `/patterns/*` endpoints
- **Creates/modifies:** `chart-decomp-service/app/api/schemas.py` (+pattern request/response
  models), `app/api/routes.py` (+`/patterns/denoise|swings|detect|pipeline|null-fpr`),
  `app/services/decomp_service.py` (+thin handlers calling the facade).
- **Satisfies:** SRS service exposure; FR-VIZ data contract (returns plot-ready arrays).
- **Reuses:** existing `MODWTRequest`/`MODWTResponse` idiom; existing
  `/{API_PREFIX}/api/v2/chart-decomp` prefix (no new gateway service).
- **Tests:** route smoke tests (FastAPI `TestClient`) for each endpoint; schema validation.
- **Deps:** A12.

### A17 — Frontend: pattern panel  ∥ (after A16)
- **Creates/modifies:** `stock-react-app/src/services/chartDecompService.js` (+pattern
  methods), a `ChartDecomp` pattern page (FR-VIZ-1 three-panel: raw/denoised, swing
  skeleton, detections shaded; FR-VIZ-2 detection report table with score + null-FPR
  percentile), `Sidebar.js` entry, `en.json`/`vi.json` i18n keys, `constants/api.js`
  endpoints.
- **Satisfies:** FR-VIZ-1, FR-VIZ-2 (render-in-React per Conflict A).
- **Tests:** component render/smoke (`npm test -- --watchAll=false`).
- **Deps:** A16.

---

## Track B — Part I clean-ups (independent; interleave anytime)

### B1 — Repair the `chart-decompose` CLI  🐞
- **Modifies:** `chart-decomp-service/cli.py`.
- **Satisfies:** SRS §I.4.3 (BROKEN today). Fix stale calls (`cd.modwt(x, wavelet=…)`,
  `result.H`, `cd.cwt_scalogram(x, scales=…)`); add `decompose --method`, `forecast --model
  vmd-har`, `backtest` subcommands.
- **Tests:** `tests/test_cli.py` smoke test per subcommand on a tiny CSV.
- **Deps:** none. *(Recommended to include — cheap, and it's a real bug.)*

### B2 — Hurst stationary-input guard
- **Modifies:** `infrastructure/long_memory/wavelet_hurst.py` (or the facade) to warn when
  input looks non-stationary (high lag-1 ACF / monotone drift), per FR-HURST / Exp 5.
- **Tests:** passing a price-like (random-walk levels) series emits the warning; passing
  returns does not. **Non-binding** (warning, not error).
- **Deps:** none. *(Recommended — guards the #1 documented Hurst bug.)*

### B3 — DM-stat wiring into forecast metrics  ∥
- **Modifies:** `application/run_forecast_usecase.py` and/or `/forecast/compare` so a
  candidate's `metrics["dm_vs_har"]` is populated when a `baseline` is supplied; forecasters
  stay pure.
- **Satisfies:** FR-FCST-EVAL completeness (logic already exists).
- **Tests:** compare path returns DM, ΔRMSE, ΔQLIKE and the 3-condition `improves_on_har`
  verdict. *(Optional.)*

### B4 — NFR-RP2 version provenance  ∥
- **Modifies:** result serialization to attach `{lib, pywt, numpy, scipy}` versions.
- **Satisfies:** NFR-RP2. *(Optional.)*

### B5 — Notebooks + optional `viz` extra  🔶 decision-gated
- **Creates:** `chart_decomp.viz` (matplotlib, optional extra) + 3 notebooks (decomposition
  tour, forecasting walkthrough, pattern detection) written against the real facade.
- **Satisfies:** NFR-U2 (literal compliance).
- **Gate:** only if the user opts for literal NFR-U2 compliance (design.md §15.1 / §12).
  *Default: skip.*
- **Deps:** A12 (pattern notebook needs the pipeline).

---

## Dependency graph (Track A)

```
A1 ──┬─ A2 ─┐
     ├─ A3 ─┼──────────────┐
     ├─ A4 ─┤              │
     └─ A5 ─┴─ A6 ┐        │
               A7 ┤        │
               A8 ┼─ A10 ─ A11 ─ A12 ─┬─ A13
               A9 ┘                   ├─ A14
                                      ├─ A15 (also needs A11)
                                      └─ A16 ─ A17
```
Parallelizable clusters: **{A2, A4}**; **{A6, A7, A8, A9}**; **{A13, A14, A15}** (after A12;
A15 after A11); all of **Track B** against Track A.

---

## Mandatory-harness checklist (must all exist & pass before "done")

| Harness | SRS | Introduced in |
|---|---|---|
| Planted-pattern | II.5.1 | A6 (grows through A7–A10) |
| Null-FPR / false-positive + 95th-pct gate | II.5.2, FR-FPR-1/2 | A11 (test-first) |
| Threshold-robustness | II.5.3 | A14 |
| Determinism | II.5.4 | A15 |
| *(Part I harnesses already green — untouched)* | I.5.* | existing |

All assert **properties**, never the SRS's synthetic magnitudes (CLAUDE.md).

---

## Suggested execution order (one per session)

`A0 → A1 → A2 → A3 → A4 → A5 → A6 → A7 → A8 → A9 → A10 → A11 → A12 → A13 → A14 → A15 → A16 → A17`,
slotting `B1`, `B2` (and optionally `B3`/`B4`) wherever convenient; `B5` last if chosen.

*Plan only — no code. Next: Phase 3 (implement one task at a time, starting at A1 or A0).*

---

## Follow-on candidate register (not part of this plan)

`docs/implementation_plan_edwards_magee.md` (2026-10-10) registers the **Edwards & Magee
validation layer** — candidates `EM-1`…`EM-9` drawn from
`docs/edwards-magee-technical-analysis-of-stock-trends-9th-edition.md` and audited against the
shipped code. Four of them (`EM-1` volume validation, `EM-2` volume-weighted S/R, `EM-8`
objective calibration, `EM-9` penetration filter) touch the Part II detectors this plan built, so
read that register before extending Track A. It is a **Phase-0 artifact**: no design, no plan, no
code, nothing started.
