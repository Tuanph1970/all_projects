# Implementation Plan — EM-1 Volume Validation of Chart Patterns

**Phase 2 artifact** (plan only — no code).
**Date:** 2026-10-12
**Inputs:** `docs/SRS_edwards_magee_volume.md` v1.0 (FR-EM-V*, EC-V*, NFR-V*, H1–H6),
`docs/implementation_plan_edwards_magee.md` (candidate EM-1)

---

## How to use this plan

- **One task per session.** Each task is PR-sized: write its tests (test-first where marked
  ⚠️), implement, show them green, then **STOP**. Do not start the next task without being asked
  (`CLAUDE.md`).
- Tasks are strictly ordered within a track. **Track V** is backend; **Track F** is frontend and
  starts only after `V7`. **Track S** (sweep + docs) closes the work.
- "∥" marks tasks with no dependency on each other.
- Every task closes by updating `ROADMAP.xlsx` (Feature Inventory / Backlog #61 status + a
  Sessions Log row).
- **No database work appears in this plan** because there is none — see SRS §2
  (`ai-insights-service` is stateless; `stock_prices.volume` already exists). Any task that seems
  to need a migration is a sign the SRS was misread.

### Test commands for this work

```bash
cd stock_microservices
pytest services/ai-insights-service/tests -v                    # the suite being extended
pytest services/ai-insights-service/tests/test_volume_rules.py -v   # new, from V1
./scripts/quick-test.sh                                         # fast feedback
cd ../stock_react_javascript/stock-react-app
npm test -- --watchAll=false PatternPanel                       # Track F
```

---

## Track V — Backend

### V0 — Roadmap rows
- **Files:** `ROADMAP.xlsx` (Feature Inventory + Backlog #61 + Sessions Log).
- **Do:** flip Backlog #61 `Candidate → In Progress`; add a Feature Inventory row for the volume
  layer pointing at `docs/SRS_edwards_magee_volume.md`; add the EM-1 task IDs (`V1`…`S2`).
- **Why first:** project bookkeeping per `CLAUDE.md`; listed as a task so it isn't forgotten.
- **Done when:** workbook saved, no code touched.

---

### V1 — The volume primitives  ⚠️ test-first
- **Satisfies:** `FR-EM-V1` (causal median-baseline `rvol`), `FR-EM-V2` (volume-trend measure),
  `EC-V1`, `EC-V2`, `EC-V4`, `EC-V5`.
- **Files:** NEW `services/ai-insights-service/app/services/patterns/volume.py`;
  NEW `services/ai-insights-service/tests/test_volume_rules.py`.
- **Do:**
  - `relative_volume(volume, i, baseline_window=50)` — median of bars strictly `< i`.
  - `volume_trend(rvol, start, end)` → `[-1, +1]`, rank-based so one outlier cannot flip it.
  - A neutral sentinel used everywhere unavailability is possible.
  - Nothing reads a DataFrame yet — plain arrays, so the tests are trivial and fast.
- **Tests (write first):** `H4` causality (append bars → no past value moves — this is the test
  that forbids whole-frame normalisation, so it goes in on day one); `H5` thin/missing/constant/
  zero volume → neutral, never a penalty; `EC-V5` single absurd print is bounded by the median;
  `H6` determinism.
- **Done when:** `test_volume_rules.py` green and `H4`/`H5` are named in the test titles.
- **Note:** no detector changes in this task. Primitives only — this is what keeps V2–V5 small.

### V2 — The volume-shuffle harness  ⚠️ test-first ∥ (with V3)
- **Satisfies:** `H1` — the core evidence test and the cheapest statement of the C4 benchmark.
- **Files:** NEW `services/ai-insights-service/tests/test_volume_shuffle.py`;
  a small shuffle/surrogate helper under `tests/` (test-support code, not shipped).
- **Do:** permute `volume` against price, re-run the detectors, and assert the two properties:
  mean `volume_score` over real detections **falls**, and `geometric_confidence` is
  **bit-identical**.
- **Sequencing:** written now, against the V1 primitives and a *stub* scorer, so it is failing
  and waiting before any detector rule exists. It then guards every rule added in V4/V5.
- **Done when:** the test exists, is red for the right reason (no scorer yet), and is wired into
  the suite.

### V3 — The local null-FPR harness  ∥ (with V2)
- **Satisfies:** `H2`.
- **Files:** NEW `services/ai-insights-service/tests/test_volume_null_fpr.py` + surrogate
  generators in the same test-support module as V2.
- **Do:** random-walk OHLCV matched in length and volatility, under **two** volume nulls as the
  SRS requires — a synthetic volume process **and** a block bootstrap of the real symbol's volume.
  Report detections-per-surrogate and the surrogate 95th-percentile confidence.
- **Why two nulls:** inventing a volume process is itself a modelling choice; the requirement must
  hold under both or the result is an artefact of the generator (SRS §6 H2 design note).
- **Do NOT:** import from `chart-decomp-lib` — different package, bare-series interface. This is
  deliberately a local harness.
- **Done when:** baseline numbers for the *current* geometry-only detectors are recorded in the
  test output and quoted in the Sessions Log. **These are the before-numbers of the benchmark** —
  capture them before V4 changes anything.

### V4 — `PatternMatch` composition + the asymmetry rule  ⚠️ test-first
- **Satisfies:** `FR-EM-V3` (asymmetry), `FR-EM-V7` (composition), `EC-V3`, `NFR-V1` isolation.
- **Files:** `app/services/patterns/base.py` (`PatternMatch` fields), `app/services/patterns/volume.py`
  (the scorer + factor bounds), `app/models/schemas.py` (pydantic mirror).
- **Do:**
  - Add `volume_score`, `volume_factor`, `volume_evidence`, `geometric_confidence` — all
    `Optional`, defaulted, so the change is additive.
  - `confidence = geometric_confidence × volume_factor`, clamped, with bounds `[0.5, 1.15]`.
  - The asymmetry: bullish breakouts **require** expansion; bearish breakouts treat it as
    corroboration only. Encode it as a direction-aware rule object, not an `if` in each detector.
  - Wrap volume evaluation so a failure degrades to `volume_factor = 1.0` and never drops a
    detection.
- **Tests:** `H3`'s asymmetry assertion (mirrored geometry + flat breakout volume → bullish scores
  lower than bearish); `EC-V3` a frame with no `volume` column behaves exactly as before;
  `_validate_ohlc` still requires only `{high, low, close}`; the existing suites stay green.
- **Done when:** V2's shuffle test goes **green for the first time**, and the full ai-insights
  suite is green.
- **Risk to watch:** `confidence` now moves. `PatternPanel.js` filters on `found` (unaffected),
  but `decision-helper`'s `target_module` / `failed_signal` read these patterns over HTTP — that
  comparison is task `S1`, not this one.

### V5 — Reversal-detector rules
- **Satisfies:** `FR-EM-V5` rows 1–4.
- **Files:** `app/services/patterns/reversal.py`; `tests/test_reversal_patterns.py` (extend).
- **Do:** H&S top (heavy left shoulder, decidedly lighter right shoulder, **head volume
  deliberately not scored** — E&M say it is not a tell); Inverse H&S (volume **builds**, burst on
  neckline penetration **required**, strongest penalty in the set — and explicitly *not* the top's
  rule inverted); Double Top (less volume on the second top); Double Bottom (dull second bottom +
  rising volume on the break of the intervening high, **required**).
- **Tests:** per-detector textbook-vs-adverse volume pairs; a test asserting the inverse H&S does
  **not** reuse the top's rule; `H1`/`H2` must not regress.
- **Done when:** green, and the H&S-bottom penalty is demonstrably the strongest in the set.

### V6 — Continuation + trap rules
- **Satisfies:** `FR-EM-V5` rows 5–12, `FR-EM-V4` (the suspect-volume rule).
- **Files:** `app/services/patterns/continuation.py`, `app/services/patterns/trap.py`;
  extend `tests/test_continuation_patterns.py`, `tests/test_trap_patterns.py`.
- **Do:**
  - Flag / Pennant: continuous drying-up required, pennant stricter; expansion **inside** the
    pattern is **suspect** (it inverts the pattern's meaning per Ch 11).
  - Triangles: diminishing toward the apex, expansion on upside breaks **required**; high-volume
    **downside** breaks **suspect** (Ch 8 shakeout) — the non-monotone case; symmetrical gets the
    heaviest weighting, being the book's ⚠ worst offender for false moves.
  - Trap: volume **raises** confidence here — a penetration *without* follow-through volume is the
    trap signature, the inverse of volume's role elsewhere.
  - Wide-Ranging Day / One-Day Reversal: needs the long baseline (open question 3 — decide and
    record here).
  - `GapDetector`: **open question 4 lands in this task** — whether volume may re-*classify* a gap
    (breakaway / runaway / exhaustion) rather than only score it. Recommended yes; if taken, it is
    the one place EM-1 changes a `pattern_name` the UI renders, so it needs its own test and a
    note for Track F.
- **Tests:** a dedicated non-monotonicity test (more volume on a downside triangle break must
  score *lower*) — the rule most likely to be "simplified" into wrongness by a later refactor.
- **Done when:** green; `H1`/`H2`/`H3` all hold.
- **Consider splitting** into V6a (flag/pennant/triangles) and V6b (gap/wide-day/trap) if the
  diff gets large — the gap re-classification alone may justify its own session.

### V7 — Climactic flag + API surface
- **Satisfies:** `FR-EM-V6`, `FR-EM-V8`.
- **Files:** `app/services/patterns/volume.py`, `app/models/schemas.py`, `app/api/routes.py`,
  `app/services/insights_service.py`; `tests/test_insights.py` (extend).
- **Do:** the climactic-bar flag as **evidence only** (it must not alter any signal or stop in
  this slice); surface the new fields and the `baseline_window` actually used on both pattern
  endpoints; confirm `volume_evidence` is renderable (ordered, labelled, carries its `rvol`
  figures).
- **Tests:** route tests for the additive fields; a response-shape test proving old clients are
  unaffected.
- **Done when:** green. **Track F unblocks here.**

---

## Track F — Frontend (starts after V7)

### F1 — PatternPanel volume verdict
- **Satisfies:** `FR-EM-V9`.
- **Files:** `src/components/Pages/DecisionConsole/PatternPanel.js`;
  `src/components/Pages/DecisionConsole/PatternPanel.test.js` (new or extend);
  i18n **en + vi**.
- **Do:** per card, a verdict chip (**confirms / neutral / contradicts / suspect**) with the
  `rvol` figures behind it, and geometric vs composite confidence shown distinctly enough that a
  user sees volume moved the number. A pattern with no volume evidence renders exactly as today —
  no empty row, no "—" clutter (`EC-V8` surfaces `thin_volume` as the reason).
- **Tests:** RTL — all four verdicts render; the no-evidence case renders unchanged; the thin-data
  marker explains itself.
- **Note:** `helperService.getPatterns` needs no change — the fields ride on the existing payload.

### F2 — AIInsights pattern section  ∥ (after F1)
- **Files:** `src/components/Pages/AIInsights.js` + its test; same i18n keys as F1.
- **Do:** the compact form of the verdict.
- **Done when:** green, and the frontend suite has no new warnings (Backlog #28 keeps CI
  informational — do not add to it).

### F3 — Deploy check
- **Do:** rebuild the frontend **Docker image** — a host `npm run build` alone does not update the
  running screen on this setup — then confirm the verdict renders against a live symbol.
- **Reference:** `./deploy-interactive.sh --auto`; local gateway is **:18004** (not 8004).

---

## Track S — Sweep, comparison, documentation

### S1 — Downstream before/after comparison
- **Satisfies:** SRS open question 5.
- **Do:** a **read-only** comparison of `decision-helper` output (targets from `target_module`,
  `failed_signal` verdicts) on a fixed symbol set, before vs after the composite-confidence
  change. Report it; change nothing in decision-helper in this task.
- **Why it is a task and not an afterthought:** `FR-EM-V7` deliberately changes `confidence`, and
  that number is consumed by another service. Shipping without measuring the effect would be
  exactly the kind of unverified claim `CLAUDE.md` forbids.

### S2 — Parameter sweep + documentation
- **Satisfies:** `FR-EM-V11`, SRS open questions 1–3.
- **Do:** sweep `baseline_window` (20 / 50 / 100), the `volume_factor` bounds, and each rule's
  threshold under `H1`/`H2`; record the chosen values **with their evidence**. Then update
  `docs/USER_GUIDE_chart_decomp_and_decision_tools.md` (bilingual VI/EN, per that file's
  convention) with what the verdict means and the behaviour change in `confidence`.
- **Done when:** the defaults in the code are results rather than inherited guesses, and the user
  guide explains the verdict to a trader.

---

## Dependency graph

```
V0 → V1 → ┬→ V2 ┐
          └→ V3 ┴→ V4 → V5 → V6 → V7 → F1 → F2 → F3
                                    └→ S1 ∥ S2
```

`V2` and `V3` are parallel and both precede `V4` — the harnesses exist, and `V3`'s baseline
numbers are captured, **before** any rule changes a score. That ordering is the whole point:
without it there is no before-measurement to compare against, and the C4 claim becomes
unfalsifiable.

---

## Mandatory-harness checklist (all must exist and pass before "done")

| Harness | SRS | Introduced in | Guards |
|---|---|---|---|
| `H1` volume-shuffle | §6 | V2 (test-first) | every rule in V4–V6 |
| `H2` null-FPR, two nulls | §6 | V3 | V4–V6 |
| `H3` planted recall + asymmetry | §6 | V4, grows through V5–V6 | regression wall |
| `H4` causality (C1) | §6 | V1 | forbids whole-frame normalisation |
| `H5` thin / missing data | §6 | V1 | EC-V1, V2, V4, V8 |
| `H6` determinism | §6 | V1 | NFR-V1 |

All assert **properties**. None asserts a magnitude from the book — E&M's 3 %, 40 %, ⅓/⅓/⅓ and
9:1 are defaults to be swept (`FR-EM-V11`), never expected values (`CLAUDE.md`).

---

## Suggested execution order (one per session)

`V0 → V1 → V2 → V3 → V4 → V5 → V6 → V7 → F1 → F2 → F3 → S1 → S2`

with `V2 ∥ V3` combinable in one session if the diff stays small, and `V6` splittable into
`V6a`/`V6b` if the gap re-classification grows.

**First session is `V0 + V1`** — bookkeeping plus the primitives and their causality/thin-data
tests. Small, self-contained, and it puts the C1 guard in place before anything can violate it.

---

## Explicitly not in this plan

- **Any database change.** SRS §2: `ai-insights-service` is stateless and
  `stock_prices.volume` already exists. No migration, no lifespan SQL, no seed data.
- **`chart-decomp-lib` detectors** — deferred as **EM-1b**; needs the
  `decomp_service.py:84` bare-series schema change first.
- **Acting on the climactic flag** (E&M's "cancel further commitments in that direction") — that
  is a decision-helper change and a separate candidate.
- **EM-2…EM-9** — still `Candidate` in `docs/implementation_plan_edwards_magee.md`.

---

*Plan only — no code. Next: Phase 3, task `V0 + V1`, tests first, then STOP.*
