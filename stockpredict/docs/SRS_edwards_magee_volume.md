# Software Requirements Specification — Volume Validation of Chart Patterns

**EM-1 · Edwards & Magee validation layer**

**Phase 1 artifact** (design only — no plan, no code).
**Version:** 1.0
**Date:** 2026-10-12
**Inputs:**
- `docs/implementation_plan_edwards_magee.md` (Phase-0 register, candidate EM-1)
- `docs/edwards-magee-technical-analysis-of-stock-trends-9th-edition.md` — Ch 6, 7, 8, 9, 10, 11, 12, 28
- the shipped detectors: `services/ai-insights-service/app/services/patterns/`

**Requirement ID prefix:** `FR-EM-V*` (functional), `EC-V*` (edge cases), `NFR-V*` (non-functional).

---

## 1. Purpose and scope

### 1.1 The problem

Eleven chart-pattern detectors ship in `ai-insights-service` and score every formation on
**geometry alone**. `grep -rn volume` over `app/services/patterns/` returns nothing;
`patterns/base.py:115` `_validate_ohlc` requires only `{high, low, close}`.

Meanwhile `insights_service.py:691` `_fetch_historical_prices` builds its DataFrame directly
from the stock-data-service history payload — which **includes `volume`** — and hands that same
frame to all eleven detectors at `insights_service.py:1988-1990`. The column is in memory at the
detector boundary and discarded.

For Edwards & Magee this is not a missing nicety. Volume is the **condition of validity** on the
majority of their patterns, and *"volume goes with the trend"* is one of the twelve Dow tenets.
A head-and-shoulders without the volume sequence is, in their treatment, a drawing.

### 1.2 Scope — in

- A causal, relative volume model (`FR-EM-V1`).
- A per-pattern volume rule set covering all eleven shipped detectors (`FR-EM-V3`…`FR-EM-V6`).
- Composition of volume evidence into the existing `confidence` (`FR-EM-V7`).
- Exposure of the evidence through the API and the Decision Console pattern panel
  (`FR-EM-V8`, `FR-EM-V9`).
- Six mandatory validation harnesses (§6).

### 1.3 Scope — out (deferred, with reasons)

| Deferred | Why |
|---|---|
| The same gate in `chart-decomp-lib` detectors | `chart-decomp-service` accepts a bare close series (`app/services/decomp_service.py:84`, `np.asarray(req.series)`). Adding volume there is a request-schema change plus a frontend change on the ChartDecomp page — a second slice, registered as **EM-1b**. |
| Intraday / tick volume, volume-at-price histograms | Daily bars only; the data layer has no intraday distribution. Relevant to EM-2, not here. |
| On-balance volume, volume oscillators, A/D line | Already partly present in `analysis-service` as indicators, and not Edwards & Magee — they use raw relative volume and nothing else. |
| New patterns (rounding bottom, broadening, wedge, diamond, island) | EM-1 validates what exists. New detectors are separate candidates. |
| Open-interest analysis (App C four-case table) | No derivatives data. |

### 1.4 What this is measured against (C4)

`CLAUDE.md` requires a benchmark. The benchmark for EM-1 is **the current geometry-only
detector**, and the acceptance criterion is stated as a property, never as a magnitude:

> The volume layer earns its place only if (a) shuffling volume against price measurably
> degrades the volume score on real detections — proving the signal is in the price-volume
> *relationship* and not in volume's marginal distribution — and (b) it does not reduce recall
> on the existing planted-pattern suite.

§6 turns this into six harnesses.

---

## 2. Database impact

**None. No schema change, no migration, no seed data.**

Established by inspection:

- `ai-insights-service` is **stateless**: there is no `app/models/domain.py`, no `__tablename__`
  anywhere under `app/`, and no `get_db`/`AsyncSession` dependency in `app/api/routes.py`. It
  computes per request and persists nothing.
- The volume data already exists upstream: `stock-data-service/app/models/domain.py:103` and
  `:155` declare `volume = Column(BigInteger, nullable=True)`, and the history response schema
  already carries `volume: Optional[int]`.
- Therefore nothing in the lifespan SQL blocks (`WEBAPI_TABLES_SQL` / `MIGRATION_SQL` /
  `SEED_DATA_SQL`) is touched, and the `prediction-service` dual-schema rule in `CLAUDE.md` does
  not apply.

**The one data caveat that follows from this**: `volume` is `nullable=True`, so NULL and 0 are
both reachable in real rows. `EC-V1` and `EC-V2` below make handling them a requirement rather
than an accident.

---

## 3. The volume model

### FR-EM-V1 — Relative volume (`rvol`), computed causally

Edwards & Magee are explicit that volume is judged **relative**: *"high" means high for that
stock in that period*, never an absolute share count (Ch 6). The system SHALL therefore never
compare raw volumes across symbols or across distant windows.

- The system SHALL compute, for each bar `i`, a **trailing baseline** from a window of
  `baseline_window` bars strictly **before** `i`.
- The baseline SHALL be the **median**, not the mean. A single climax day (which E&M care about
  precisely because it is extreme) would inflate a mean baseline and mask the next one.
- `rvol[i] = volume[i] / baseline[i]`, undefined where the baseline is unusable (`EC-V1`).
- Default `baseline_window` = 50 bars. This is a tunable default, not a finding; `FR-EM-V11`
  requires it be swept.

**Causality (C1) is binding here.** The baseline at bar `i` reads only bars `< i`. There SHALL be
no full-series normalisation — no `volume / volume.mean()` over the whole frame, no z-score
against a global σ. `H4` tests this by appending bars and asserting no past value moves.

### FR-EM-V2 — Volume-trend measure

Several E&M rules are about a *direction* of volume over a span, not a single bar's level
("volume diminishes continuously through the flag", "activity must build through the head").

- The system SHALL expose a monotone-trend measure over a bar span, computed from `rvol` within
  that span, normalised to `[-1, +1]`: negative = drying up, positive = expanding.
- It SHALL be robust to a single outlier day (a rank-correlation or a median-split slope, not an
  OLS slope on raw volume).

---

## 4. The per-pattern rule set

### FR-EM-V3 — The asymmetry rule (the governing principle)

This is the single most important requirement in this document, and the one a naive
"volume confirms everything" implementation gets wrong.

Edwards & Magee, Ch 7:

> **"It takes buying to put stocks up, but they can fall of their own weight."** A low-volume
> break *down* through a top's neckline is trusted; a low-volume break *up* from a bottom is not.

Restated as requirements. For a breakout/penetration event:

- **Bullish direction (upside break):** a volume expansion is **required** evidence. Its absence
  SHALL penalise the detection. For the head-and-shoulders *bottom* E&M go further — *"there must
  be a conspicuous burst of volume on the neckline penetration. Without it, don't trust the
  breakout"* — so the penalty there SHALL be the strongest in the rule set.
- **Bearish direction (downside break):** a volume expansion is **optional** corroboration. Its
  absence SHALL **not** penalise the detection.

The system SHALL NOT apply a symmetric volume requirement to bullish and bearish patterns. A test
SHALL assert the asymmetry directly: the same geometry mirrored, with the same flat breakout
volume, must score *lower* bullish than bearish.

### FR-EM-V4 — The suspect-volume rule (a negative volume condition)

E&M, Ch 8, on triangles: *"upside breaks require volume confirmation, downside breaks do not"*,
and then the inversion that no conventional indicator encodes —

> **"A high-volume downside break is suspect"** — especially out near the apex, it is often a
> 2–3 day shakeout.

So volume evidence is **not monotone**: for a downside triangle break, *more* volume can be
*worse*. The system SHALL support rules in which an expansion reduces the score, and SHALL apply
this to the downside-break case of the three triangle detectors.

The same shape of rule applies elsewhere and SHALL be encoded:

- **Flag / pennant** (Ch 11): *"High or irregular volume inside the pattern turns it into a minor
  reversal area"* — i.e. expansion inside the consolidation inverts the pattern's meaning rather
  than merely weakening it.
- **Minor-move exhaustion** (Ch 28): of the three expected volume peaks in a minor move (breakout
  day · the day price passes the last minor top · the day the move completes), *"extra heavy
  volume on any other day during a move in the Primary Direction is likely to indicate that the
  move is at an end."*

### FR-EM-V5 — Per-detector conditions

The system SHALL implement, for each shipped detector, the conditions below. "Required" means
absence penalises; "corroborating" means presence rewards and absence is neutral; "suspect" means
presence penalises (`FR-EM-V4`).

| Detector (file) | E&M | Condition |
|---|---|---|
| `HeadAndShouldersDetector` (reversal.py) | Ch 6 | Left shoulder on heavy volume; right shoulder on **decidedly less**; breakout volume **corroborating** only (bearish). E&M warn volume at the *head* is not a tell — roughly ⅓ of confirmed cases are heavier on the left shoulder, ⅓ equal, ⅓ heavier on the head — so the head's volume SHALL NOT be scored. |
| `InverseHeadAndShouldersDetector` | Ch 7 | Volume must **build** through head and right-shoulder rally; conspicuous burst on neckline penetration **required** (strongest penalty in the set). The price pattern is the top inverted; **the volume pattern is not** — this detector SHALL NOT reuse the top's rule. |
| `DoubleTopDetector` | Ch 9 | **Less volume on the second top** required as the distinguishing evidence; confirmation on the valley break is corroborating (bearish). |
| `DoubleBottomDetector` | Ch 9 | Second bottom *"conspicuously dull and rounded"* (low volume); the test is **not proven until prices exceed the intervening rally high on rising volume** — so breakout expansion is **required** (bullish). |
| `FlagDetector` (continuation.py) | Ch 11 | Volume shrinking **markedly and continuously** through the flag is required; the mast shows a volume spurt; expansion inside the flag is **suspect** (inverts to a reversal area). |
| `PennantDetector` | Ch 11 | As the flag, but *"volume dries up even faster, sometimes to almost nothing"* — a stricter drying-up threshold. |
| `SymmetricalTriangleDetector` | Ch 8 | Volume *"diminishes irregularly but noticeably toward the apex, then expands on the breakout"*. Upside break: expansion **required**. Downside break: **suspect** near the apex (`FR-EM-V4`). This is also the book's **⚠ worst offender for false moves**, so its volume weighting SHALL be the heaviest of the three triangles. |
| `AscendingTriangleDetector` | Ch 8 | As symmetrical; resolution is ~9:1 upside, so breakout expansion is **required**. |
| `DescendingTriangleDetector` | Ch 8 | As symmetrical; downside resolution — breakout volume **corroborating**, and high-volume breaks **suspect**. |
| `GapDetector` | Ch 12 | Gap *classification* is partly a volume question, which is why this detector gains the most: **breakaway** — *"false moves are seldom attended by gaps"*, volume corroborates; **exhaustion** — recognised by *"extraordinary volume with price failing to advance commensurately"* on the day after, which is a volume rule the current classifier cannot express; **closure odds** — heavy volume at the takeoff but little beyond the gap ≈ 50-50 it fills, heavy volume **beyond** the gap → unlikely to fill. The system SHALL use volume to separate breakaway / runaway / exhaustion rather than scoring a pre-assigned class. |
| `WideRangingDayDetector` | Ch 10, 10.1 | A **One-Day Reversal** requires *"volume exceeding anything for months"* — a long-lookback relative measure, not the 50-bar baseline. Without that volume it is an ordinary wide day and SHALL score low. |
| `TrapDetector` (trap.py) | Ch 13, 17.1, 35 | A genuine break through support/resistance is *"nearly always followed by sudden acceleration and a marked volume pickup"* **after** penetration. A penetration without that follow-through volume is the trap signature, so volume **raises** trap confidence here — the inverse of its role elsewhere. |

### FR-EM-V6 — Climactic-volume flag

Independent of any pattern, the system SHALL flag a bar as **climactic** when `rvol` is extreme
against a long baseline and price progress is not commensurate (Ch 10 selling climax, Ch 28
*"prepare to retire into your shell"*, Ch 12 exhaustion gap).

The flag SHALL be returned as evidence on the scan response. It SHALL NOT, in this slice, alter
any signal or stop — the consuming decision (E&M's "cancel further commitments in that
direction") belongs to decision-helper and is a separate candidate.

---

## 5. Composition, API and UI

### FR-EM-V7 — How volume enters `confidence`

**Decision: volume weights the score; it does not gate the detection.**

Rationale, in order of weight:

1. **The book.** E&M never reject a formation for volume alone — patterns are *"not infallible …
   but the odds are definitely in their favor"*, and volume moves the odds. The one near-absolute
   is the H&S-bottom breakout burst, and `FR-EM-V3` handles it as the strongest penalty rather
   than a veto.
2. **The contract.** `found: bool` is consumed by `PatternPanel.js` (which filters `p.found`),
   by `AIInsights.js`, and by `decision-helper`'s `failed_signal.py:459`. Flipping `found` to
   false on volume grounds would read as patterns *disappearing* — a regression in a live feature.
3. **The benchmark needs a continuous score.** A gate cannot be swept; a multiplier can
   (`FR-EM-V11`).

Requirements:

- `PatternMatch` SHALL gain `volume_score: Optional[float]` in `[0, 1]`, `volume_factor:
  Optional[float]`, `volume_evidence: dict`, and SHALL preserve the pre-volume value as
  `geometric_confidence: Optional[float]`.
- `confidence` SHALL become the **composite** `geometric_confidence × volume_factor`, clamped to
  `[0, 1]`. Downstream consumers that threshold on `confidence` therefore inherit the improvement
  with no change — **this is an intended behaviour change and SHALL be called out in the release
  notes and the user guide.**
- `volume_factor` SHALL be bounded by a floor and ceiling (defaults 0.5 and 1.15) so that no
  volume judgment can either erase a geometrically excellent pattern or manufacture a
  geometrically poor one. Volume is corroboration, not the finding.
- When volume evidence is unavailable, `volume_factor` SHALL be exactly `1.0` and
  `volume_score` SHALL be `None` — never `0.0` (`EC-V1`–`EC-V3`).
- `volume_evidence` SHALL be human-readable enough to render: which conditions were tested, which
  passed, and the `rvol` figures behind them. E&M's rules are the product feature here; a bare
  number would hide them.

### FR-EM-V8 — API

- `GET|POST /insights/patterns/{symbol}` and `GET /insights/patterns/reversal/{symbol}` SHALL
  return the new fields. Both are additive and `Optional`, so existing clients are unaffected.
- The response SHALL carry the `baseline_window` actually used, so a reading is reproducible.
- No new endpoint. No change to the route prefix or Traefik labels.

### FR-EM-V9 — Frontend

- `src/components/Pages/DecisionConsole/PatternPanel.js` SHALL render, per pattern card, a
  volume verdict (**confirms / neutral / contradicts / suspect**) with the `rvol` figures, and
  SHALL show the geometric and composite confidence distinctly enough that a user can see volume
  moved the number.
- The pattern section of `src/components/Pages/AIInsights.js` SHALL show the verdict in compact
  form.
- Strings SHALL be i18n'd in **en + vi** per project convention.
- A pattern with no volume evidence SHALL render as today, with no empty row and no "—" clutter.

### NFR-V1 — Non-functional

- **Performance:** volume evaluation is `O(n)` per detector over the lookback window, on a frame
  already in memory. No new HTTP calls, no new DB reads. The added latency on a scan SHALL be
  negligible against the existing upstream history fetch.
- **Determinism:** identical input SHALL produce identical output (`H6`).
- **Failure isolation:** the existing `try/except` around each detector
  (`reversal.py:386`, `continuation.py:789`) means a volume bug must not 500 a scan. A failure
  inside volume evaluation SHALL degrade that detector to `volume_factor = 1.0`, not drop the
  detection.

---

## 6. Validation requirements (all mandatory)

Per `CLAUDE.md`, each harness ships **with** the code it validates, not after. All assert
**properties**; none asserts a magnitude from the book.

### H1 — Volume-shuffle test (the core evidence test) · MANDATORY

Shuffle the `volume` column against price (a permutation, preserving volume's marginal
distribution and destroying only its alignment with price). Then:

- mean `volume_score` over real detections SHALL fall measurably, and
- `geometric_confidence` SHALL be **bit-identical**.

This is the test that distinguishes a real rule from a decorative one: if the score does not care
whether volume lines up with price, it is not measuring what E&M describe. It is also the cheapest
possible statement of the C4 benchmark.

### H2 — Null-FPR on surrogates · MANDATORY

`ai-insights` has no null harness today (the one in
`chart-decomp-lib/chart_decomp/infrastructure/validation/{surrogates,null_fpr}.py` is a different
package and operates on a bare series). This slice SHALL add a **local** surrogate harness for
the OHLCV detectors: random-walk OHLCV with a plausible volume process, matched in length and
volatility to the target.

Requirement: EM-1 SHALL NOT increase detections-per-surrogate, and SHALL reduce the count of
detections surviving a confidence threshold at the surrogate 95th percentile.

*Design note, recorded because it is a real limitation:* the correct null for a price-volume rule
needs a volume process, and inventing one is itself a modelling choice. The harness SHALL
therefore report under **two** nulls — a synthetic volume process and a block-bootstrap of the
real symbol's volume — and the requirement must hold under both.

### H3 — Planted-pattern recall · MANDATORY

- The existing suites (`tests/test_reversal_patterns.py`, `test_continuation_patterns.py`,
  `test_trap_patterns.py`) SHALL stay green. Where a fixture has no volume column, the detector
  SHALL behave exactly as before (`EC-V3`) — these tests are the regression wall.
- New: a planted pattern carrying **textbook** volume SHALL score higher than the identical
  geometry carrying **adverse** volume.
- New: the asymmetry of `FR-EM-V3` SHALL be asserted directly (mirrored geometry, flat breakout
  volume → bullish scores lower than bearish).

### H4 — Causality · MANDATORY (C1)

Compute scores on bars `0..t`; append bars `t+1..n`; recompute. Every value at or before `t`
SHALL be unchanged. This is the volume analogue of the no-leakage test the chart system already
ships, and it is what forbids whole-frame normalisation.

### H5 — Thin and missing data · MANDATORY

Covers `EC-V1`–`EC-V4`: NULL volume, zero volume, constant volume, and a baseline window shorter
than `baseline_window`. In every case `volume_factor == 1.0` exactly and no exception escapes.
E&M's own **Dormant Bottom** (Ch 7) — *"weeks of no sales, a fly-specked chart"* — is a real VN
small-cap shape, and it must read as *unknown*, never as *bearish*.

### H6 — Determinism · MANDATORY

Repeated runs on identical input produce identical output, including dict ordering in
`volume_evidence`.

---

## 7. Edge cases

| ID | Case | Required behaviour |
|---|---|---|
| `EC-V1` | `volume` is NULL on some/all bars (column is `nullable=True` upstream) | Treat as unknown. Baseline from available bars; if too few, `volume_factor = 1.0`, `volume_score = None`. Never impute zero. |
| `EC-V2` | `volume` is `0` for a run of bars (halt, or a genuinely dormant thin ticker) | Zero is **data**, not missing — but a zero baseline makes `rvol` undefined. Fall back to the nearest usable baseline; if none, neutral. |
| `EC-V3` | The frame has no `volume` column at all (existing tests, synthetic fixtures) | Detector behaves exactly as today. `_validate_ohlc` SHALL continue to require only `{high, low, close}`; volume is strictly optional. |
| `EC-V4` | Fewer than `baseline_window` bars before the pattern | Use what exists down to a stated minimum; below it, neutral. |
| `EC-V5` | A single absurd volume print (bad vendor row) | The median baseline and the rank-based trend measure (`FR-EM-V2`) bound its effect by construction. No outlier rejection is specified — robust statistics instead of a cleaning step. |
| `EC-V6` | Corporate action restating the series | Back-adjustment rewrites prices and can rescale volume. Volume rules are **relative within a trailing window**, so a split's level shift largely cancels; a split *inside* the window is a known distortion and SHALL be documented, not silently handled. Related: Backlog #60. |
| `EC-V7` | Non-trading gaps / holidays | Bar-indexed throughout, never calendar-indexed — consistent with `call_scorer`'s session-step convention. |
| `EC-V8` | Thin ticker where every day is lumpy | `H5`'s neutral path. A `thin_volume: true` marker SHALL appear in `volume_evidence` so the UI can say *why* there is no verdict. |

---

## 8. Open questions for the plan

Recorded deliberately rather than guessed. None blocks the plan; each is a task-level decision.

1. **`baseline_window` = 50?** Picked as a plausible default, not a result. `FR-EM-V11`: sweep it
   (20 / 50 / 100) under `H1`/`H2` and record the choice in the user guide.
2. **`volume_factor` bounds (0.5 / 1.15)?** Deliberately asymmetric — E&M's volume evidence is
   better at discrediting than at promoting. To be confirmed by the sweep.
3. **Does the One-Day Reversal's *"exceeding anything for months"* warrant a second, longer
   baseline?** Probably yes (≈ 120 bars). Decide in its task.
4. **Should `GapDetector` be allowed to *re-classify* a gap on volume evidence** (breakaway vs
   exhaustion), given that changes `pattern_name` and therefore the UI label? Recommended yes —
   it is the detector that gains most from volume — but it is the only place where EM-1 changes an
   existing *label* rather than a score.
5. **Does the composite-confidence change (`FR-EM-V7`) shift `decision-helper`'s behaviour enough
   to need its own before/after run?** Recommended yes, as a read-only comparison, since
   `target_module` and `failed_signal` consume these patterns.

### FR-EM-V11 — Parameter sweep is part of the work

Every default named in this document (`baseline_window`, the factor bounds, each rule's
threshold) SHALL be swept over a range and the choice recorded with its evidence. Per `CLAUDE.md`,
E&M's figures are 1940s–60s NYSE rules: legitimate **defaults**, never trusted constants, and
never test assertions.

---

## 9. Traceability

| Requirement | E&M | Lands in | Harness |
|---|---|---|---|
| `FR-EM-V1` rvol, causal median baseline | Ch 6 (volume is relative) | new `patterns/volume.py` | H4, H5 |
| `FR-EM-V2` volume-trend measure | Ch 8, 11 | `patterns/volume.py` | H1, H6 |
| `FR-EM-V3` asymmetry rule | Ch 7, 8 | `patterns/volume.py` + each detector | H3 |
| `FR-EM-V4` suspect-volume rule | Ch 8, 11, 28 | triangle + flag detectors | H1, H3 |
| `FR-EM-V5` per-detector conditions | Ch 6–12 | `reversal.py`, `continuation.py`, `trap.py` | H3 |
| `FR-EM-V6` climactic flag | Ch 10, 12, 28 | `patterns/volume.py` | H1 |
| `FR-EM-V7` composition | Ch 6 ("odds in their favor") | `patterns/base.py` `PatternMatch` | H3, H5 |
| `FR-EM-V8` API | — | `app/models/schemas.py`, `app/api/routes.py` | route tests |
| `FR-EM-V9` UI | — | `PatternPanel.js`, `AIInsights.js`, i18n en+vi | RTL tests |
| `FR-EM-V11` sweep | `CLAUDE.md` | a sweep script + the user guide | H1, H2 |
| **No DB change** | — | §2 | — |

---

*Phase 1 artifact — design only. Next: Phase 2 writes the task plan
(`docs/implementation_plan_em1_volume.md`), one PR-sized task per session, backend before
frontend. No code until the plan exists.*
