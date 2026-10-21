# SRS — EM-8: objective-completion calibration and the "something to reverse" cap

**Version:** 1.0 (Phase 1 design)
**Date:** 2026-10-21
**Backlog:** `#68`
**Register:** `docs/implementation_plan_edwards_magee.md` § EM-8
**Status:** design only. Nothing is built.

---

## 1. What the book requires — including its own scepticism

Ch 32 answers *"how far do you think it will go?"* with *"You don't know.
Nobody knows."* That is the chapter EM-8 descends from, and reading it
honestly changes the task.

**The rules that work** (master-list items 117–125):

| # | pattern | minimum objective |
|---|---|---|
| 117 | Head-and-Shoulders | head-top → neckline, projected from the break |
| 118 | Triangle | parallel to the opposite boundary from the first rally top; Ch 32 words it as *the height of the triangle measured along its first reaction* |
| 119 | Rectangle | its height |
| 120 | Flag / Pennant | the pre-flag move duplicated — *"the Flag flies at half mast"* |
| 121 | Runaway Gap | **~the halfway point**: *"prices will travel as far beyond the gap as they already have from the start of the move to the gap"* |
| 122 | Diamond | its greatest width |
| 123 | Double / Triple Top | at least peak-to-valley, below the valley |
| 124 | **Rounding turns, H&S consolidations** | **no usable formula** — and must not be given one |
| 125 | **"A reversal must have something to reverse"** | take the **smaller** of the measured objective and the preceding move |

**And the qualifications, which matter as much as the formulas:**

* Every objective is a **minimum** — H&S *"most emphatically … only a
  minimum"*. Some H&S implying three or four points *"marked the start of a
  decline eventually running to hundreds of points."*
* **Reactions** can be estimated *"fairly closely seven or eight times out of
  ten"*. **Moves in the direction of the trend cannot** — a bull move *"may,
  and often does, overrun the upper trendline by running up as far again"*.
  The reason is structural: the overrun *is itself an unreasonable move*.
* Therefore the book **prefers nearby progressive stops for taking profits
  over limit orders** at trendlines or resistance.
* Breakaway gaps have **no measuring implication**; the measuring-gap rule
  *"should be used for purposes of 'getting out' rather than 'getting in'"*.
* Bassetti: *"I have always been extremely chary of measuring moves… Always
  better to observe closely what the situation is when the price arrives at
  the measured point. **Decisions should always be made in the here and now,
  not in the I measured it then.**"*

So EM-8 is not "implement E&M's targets". The book's own position is that
measured objectives are floors, routinely overrun, and **inferior to a
trailing stop as an exit mechanism** — which is precisely the comparison this
system can run, because `trailing_stop_mode` and the basing-point stop are
already built and measured (EM-3, `#84`, `#85`).

## 2. The audit — our formulas against the book

All **13** detectors emit `measured_move_target`. The register says *"only
some detectors do"*; that is out of date, and the correction matters because
it means every one of them is making a claim.

| detector | our formula | E&M | verdict |
|---|---|---|---|
| Head and Shoulders | `neckline_at_rs − head_height` | 117 | **matches** |
| Inverse H&S | `neckline_at_rs + head_depth` | 117 | **matches** |
| Double Top | `trough − height` | 123 | **matches** |
| Double Bottom | `peak + height` | 123 | **matches** |
| Flag | `breakout + pole_move` | 120 half-mast | **matches** |
| Pennant | `breakout + pole_move` | 120 | **matches** |
| Symmetrical Triangle | `breakout_h + height`, height measured between the boundaries **at the first pivot** | 118 | **defensible** — it is Ch 32's "height along the first reaction"; the "parallel to the opposite boundary" construction is a different geometry of similar magnitude. Not a defect; noted because the two are not identical. |
| Ascending Triangle | `resistance + height` | 118 | defensible, as above |
| Descending Triangle | `support − height` | 118 | defensible, as above |
| **Gap** | `neckline ± gap_size` | 121 | ❌ **wrong, twice** — see below |
| Wide-Ranging Day | `close ± bar_range` | **none** | ours, not the book's |
| Bull Trap | `level − (close − level)` | **none** | ours |
| Bear Trap | `level + (level − close)` | **none** | ours |

### 2.1 The gap target is wrong in two independent ways

`continuation.py:696` — `target = neckline + gap_size if gap_up else neckline - gap_size`.

1. **Wrong quantity.** E&M's runaway-gap rule projects *the distance already
   travelled from the start of the move to the gap*. We project **the gap's
   own height**, which is a different measurement and typically a small
   fraction of it — a gap is one day's jump, the move may be weeks. The
   detector computes `gap_size / ra` for confidence (correctly, after `#70`)
   and then reuses `gap_size` as a price projection, which it is not.
2. **Wrong scope.** The target is emitted for **every** gap subtype. The book
   gives a measuring rule to the **runaway/continuation gap only**:
   breakaway gaps have *"no measuring implication"*, common gaps none, and an
   **exhaustion gap marks the END of a move** — so a target projected in the
   trend direction is not merely unsupported there, it points the wrong way.

This is the kind of defect that cannot be found by testing the detector
against itself, only by reading it against the source. It is logged as its own
fix (`FR-EM-M2`) and is independent of whether the calibration passes.

## 3. Where it lands — and a correction to the register

The register says *"the cap in `target_module.py`"*. That is only half
possible. `compute_target(direction, entry_price, stop_price, signal_kind,
signal_evidence, sr_levels)` **receives no bars**, so it cannot measure the
preceding move itself. The cap therefore needs two changes:

* **ai-insights-service** — detectors emit the preceding move's extent
  alongside the target (they already hold the bars and the pivots).
* **decision-helper-service** — `target_module` applies
  `min(measured, preceding)` when the field is present, and behaves exactly as
  today when it is absent.

The calibration runs in **ai-insights-service**, not in decision-helper:
that is where the detectors live, they are stateless and pure, and
`tests/test_phase_k.py` already documents that ai-insights pattern code is
**not importable** from decision-helper's test environment. The register's
suggestion to reuse `news-service/call_scorer.py`'s forward-return machinery
is a third service again; the machinery is a dozen lines and is reproduced
rather than imported across a service boundary.

**No DB change.** Detectors are stateless (established at EM-1), the
calibration reads the `#87` deep-history dump from disk, and the report is a
document.

## 4. Functional requirements

**FR-EM-M1 — The objective-completion calibration.** For each pattern family,
measure the share of detected objectives **reached within N sessions** of the
signal bar, at N ∈ {10, 20, 60}, on the deep history, causally — the detector
sees bars up to the signal bar only, and the outcome is read after it.

**FR-EM-M2 — Fix the gap target.** Emit a measured objective for the
**runaway/continuation** subtype only, computed as E&M's halfway rule
(distance from the move's start to the gap, projected beyond it). Emit
**none** for breakaway, common and exhaustion gaps. §2.1.

**FR-EM-M3 — The "something to reverse" cap.** Reversal detectors (H&S,
inverse H&S, double top, double bottom) emit the extent of the preceding move;
`target_module` takes the smaller of that and the measured objective. Item
125. Applies to **reversal** patterns only — a continuation pattern has
nothing to reverse, so the cap is not defined for it.

**FR-EM-M4 — Separate the book's rules from ours.** Wide-Ranging Day and the
two traps carry targets E&M never sanctioned. They are reported in their own
section of the calibration and are **never** quoted as evidence for or against
E&M's measuring rules.

**FR-EM-M5 — Objectives are minima, and the report must say so.** Completion
is measured as *"price reached at least the objective"*, and the **overrun
distribution** is reported beside it. A rule whose objective is reached 60% of
the time and exceeded by 3× when reached is a different object from one
reached 60% of the time and exceeded by 1%.

**FR-EM-M6 — Causality (C1).** The detector runs on `bars[:t+1]`; the outcome
window is `bars[t+1:t+1+N]`. No full-series detection then sliced.

**FR-EM-M7 — Defaults stay as they are until measured.** `target_module`'s
MEASURED_MOVE priority, `MIN_RR` and `FIXED_RR` are unchanged by this work
unless §6 says otherwise.

## 5. Edge cases

| ID | case | required behaviour |
|---|---|---|
| **EC-M1** | the objective is already behind price at the signal bar | the objective is **vacuous**; excluded from the completion rate and counted separately. Including it would score a free success. |
| **EC-M2** | fewer than N bars remain after the signal | excluded, and the exclusion count reported — the `#87` lesson that a silently shrinking sample is the thing that misleads |
| **EC-M3** | the same pattern is re-detected on consecutive bars | one observation per pattern **episode**, not per bar, or a long-lived pattern dominates its family's rate |
| **EC-M4** | overlapping outcome windows within one symbol | non-overlapping sampling per symbol, greedy, every qualifying day (`#79`, `#87`) |
| **EC-M5** | the preceding move is unmeasurable (pattern at the start of the series) | emit no extent; `target_module` then behaves exactly as today |
| **EC-M6** | `min(measured, preceding)` falls below the entry price | the capped objective is **not a target**; fall through to the S/R or fixed-R:R path rather than emitting an inverted target |

## 6. The measurement, and its pre-registered criteria

Three questions, in increasing order of what they can change.

**(a) Are the objectives reached more often than chance?**

> **Criterion.** For each pattern family with an E&M formula, the completion
> rate within N sessions must exceed a **matched random-entry null** — same
> symbol, same horizon, same direction, random signal dates, the same
> objective *distance* applied — with significance clustered **by symbol**,
> at two or more of N ∈ {10, 20, 60}.

Clustering by symbol is right here and would have been wrong at EM-6: a
pattern objective is a **per-symbol** treatment, where the Dow gate was one
market-wide treatment on shared dates (`#66`, plan §3). The level of
clustering follows the level the treatment is applied at, not habit.

**(b) Does the cap help?**

> **Criterion.** `min(measured, preceding)` must improve **expectancy** in the
> backtest, not completion rate.

Stated explicitly because the obvious metric is invalid: **completion rate is
gameable by shrinking the target.** A cap mechanically raises completion
because a nearer objective is easier to reach, so a higher completion rate is
evidence of nothing at all. Only expectancy — what the position actually earns
with that exit — can judge it.

**(c) Should a measured objective be a target at all?**

> **Criterion.** MEASURED_MOVE stays priority 1 in `target_module` only if a
> measured-move exit beats the shipped trailing stop on net P&L per trade,
> out-of-sample, symbol-clustered. If it does not, MEASURED_MOVE is demoted
> or removed.

This is the question with teeth, and the book is on the side of the trailing
stop: Ch 32 prefers *"nearby progressive stops for taking profits"* precisely
because the overrun is unreasonable and unbounded, and Bassetti would rather
decide *"in the here and now"*. The system already has the comparison arm
built — `trailing_stop_mode`, plus EM-3's basing-point stop.

## 7. Deliberately out of scope

* **New detectors** (rectangle, diamond, rounding turn). EM-8 calibrates what
  exists. And item 124 forbids giving a rounding turn a formula at all.
* **Semi-log measurement.** E&M note the gap rule *"works particularly well on
  semi-log"*. Logged, not built — it changes every formula's arithmetic and
  deserves its own measurement.
* **Frontend.** Nothing until (a) and (c) are answered.
* **The 3-week flag caution** (*"if the congestion continues or sags for more
  than about 3 weeks, sell"*) — a detector-validity rule, not a measuring
  rule. Belongs with EM-1's volume work.

## 8. Harnesses

| ID | harness |
|---|---|
| **H-M1** | **Causality.** Appending future bars leaves every past detection and objective unchanged. |
| **H-M2** | **Planted completion.** A constructed series that reaches a known objective on a known bar is scored complete at that bar; one that stops just short is scored incomplete. |
| **H-M3** | **The vacuous-objective guard** (`EC-M1`) — an objective behind price must not be counted as reached. |
| **H-M4** | **The cap is a cap.** The capped objective is never further than the uncapped one, and never further than the preceding move. |
| **H-M5** | **Gap scope.** No objective is emitted for breakaway, common or exhaustion gaps; the runaway objective equals the halfway construction on a planted move. |
| **H-M6** | **Bound-default guard**, mutation-checked. Seventh instance in this project. |
| **H-M7** | **No-op proof.** With no `preceding_move_extent` in evidence, `compute_target` returns exactly what it returns today — the existing suite unchanged. |

## 9. The honest prior

Unlike EM-6, this one is not expected to be a flat null, because it is
mostly **measurement of something already shipped and in use** rather than a
new mechanism — the register called it the highest information-per-hour item
for that reason, and `FR-EM-M2`'s gap defect is a result already, independent
of any statistic.

But two outcomes are more likely than "E&M's targets work":

1. **The objectives are reached often, and it means less than it looks.** A
   "minimum" objective in the direction of an established move will be reached
   at a decent rate by drift alone — which is exactly why the criterion is a
   *matched random-entry null* and not a bare percentage.
2. **The trailing stop wins (c).** That is the book's own expectation, and
   this project has already measured that a basing-point stop carries a real
   if tail-driven edge. If so, EM-8's deliverable is the retirement of a
   shipped code path, which is a result worth having and cheaper to act on
   than a new feature.
