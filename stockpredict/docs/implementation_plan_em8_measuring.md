# Implementation plan — EM-8: objective-completion calibration and the cap

**Phase:** 2 (plan)
**Date:** 2026-10-21
**Design:** `docs/SRS_edwards_magee_measuring.md` v1.0
**Backlog:** `#68`, and `#92` (the gap defect) is folded in as M1

One task per session: tests first, run them, show them passing, **stop**.

---

## 1. What gates what — and what does not

EM-6's structure was a chain: one gate could kill everything downstream. EM-8
is not that shape, and pretending otherwise would stop the wrong work.

The SRS asks three questions, and **two of them are independent**:

* **(a) Is E&M's measuring claim true on VN data?** A question about the book.
* **(c) Is `MEASURED_MOVE` a good exit?** A question about our code.
* **(b) Does the cap help?** Only meaningful if (c) says a measured target is
  worth having at all.

**(a) does not gate (c).** An objective reached only at chance rates could
still be a perfectly serviceable profit-taking level — "not special" is not
the same as "not useful". And (a) passing would not make `MEASURED_MOVE` the
right exit either, because E&M's own argument against it is about the
**overrun**, not the completion rate: an objective can be reached reliably and
still cost you the larger part of the move.

So there is exactly **one hard gate: (c) gates the cap.** (a) is reported
either way, because a null on the most-quoted measuring rules in the book is
a result this project publishes rather than buries.

That also fixes the order. The cap is the **largest** change here — it touches
two services — and it is the only one that can be made unnecessary by a
measurement. It goes last.

## 2. Tasks

### M1 — Fix the gap target (`#92`) *(S)*
Unconditional, and first: it is a **correctness** fix against the source, not
a bet on a statistic, so it is worth doing whatever the rest of EM-8
concludes. `FR-EM-M2`.

* Emit an objective for the **runaway/continuation** subtype only. `None` for
  breakaway, common and exhaustion — the last of which currently projects a
  target *in the direction the move is ending*.
* Compute E&M's halfway rule: project beyond the gap the distance already
  travelled **from the start of the move to the gap**.

Tests first: **H-M5** (scope — no objective for the three subtypes that have
no rule; and the halfway construction recovered exactly on a planted move),
plus the existing gap tests must still pass or be restated with a reason.

> **The one open question M1 must settle: what is "the start of the move"?**
> E&M say it by eye. Mechanically it needs to be deterministic and causal.
> Candidates: (i) the most recent confirmed swing pivot in the opposite
> direction before the gap; (ii) the start of the unbroken run of
> same-direction bars; (iii) a fixed N-bar extreme. **(i) is the default** —
> it is closest to "the move" as E&M draw it, and `base.py` already has pivot
> machinery. Whichever is chosen, the choice is recorded in the code with its
> reason, and a test pins that two different definitions do not silently
> coexist.

### M2 — The calibration harness, and question (a) *(M)*
`FR-EM-M1`, `M4`, `M5`, `M6`. In **ai-insights-service**, over the `#87` deep
history (92 symbols, 320,237 bars, 19.7 years).

For every detection: the objective, whether it was reached within
N ∈ {10, 20, 60} sessions, and **by how much it was exceeded when reached**
(`FR-EM-M5` — "reached 60% of the time and overrun 3×" is a different object
from "reached 60% and overrun 1%", and only the overrun distinguishes them).

E&M-sanctioned families and our own (Wide-Ranging Day, both traps) are
reported in **separate** sections and never pooled (`FR-EM-M4`).

Handles `EC-M1`–`EC-M4`: vacuous objectives excluded and counted, short tails
excluded and counted, one observation per pattern **episode**, non-overlapping
outcome windows per symbol taken greedily over every qualifying day.

> **Criterion for (a), pre-registered.** For each E&M family, the completion
> rate must exceed a **matched random-entry null** at **two or more** of the
> three horizons, symbol-clustered.
>
> **Multiplicity is handled, not ignored:** six families × three horizons is
> eighteen tests, and some will clear 0.05 by chance. The ≥2-of-3 requirement
> is itself a consistency filter; on top of it, **Holm correction across
> families** applies to any headline claim, and the full table is published
> whatever it shows.
>
> **This is not a stop.** Either result is reported and the work continues to
> M3.

**The null, specified now** (EM-2's matched-distance construction, which is
why it is reused rather than invented): for each real observation — symbol,
direction, objective **distance** `d`, horizon `N` — draw random dates in the
*same symbol* and ask whether price moved at least `d` in the same direction
within `N` sessions. Matching on distance is essential: a nearer objective
completes more often, so an unmatched null would measure the targets'
*nearness* rather than the patterns' *information*.

### M3 — GATE: should a measured objective be a target at all? *(M)*
Question (c), and the only hard gate. Needs no new measurement machinery —
`trailing_stop_mode` and EM-3's basing-point stop are already built and
measured (`#84`, `#85`) — just a `BacktestConfig` switch over the target path:
`MEASURED_FIRST` (today), `NO_MEASURED` (fall through to S/R, then fixed R:R),
`TRAILING_ONLY` (no profit target; exit on the trailing stop).

> **Criterion, pre-registered.** `MEASURED_MOVE` keeps priority 1 only if
> `MEASURED_FIRST` beats both alternatives on **net P&L per trade**,
> out-of-sample, **symbol-clustered**, with the trade count reported beside
> it.
>
> **On failure:** `MEASURED_MOVE` is demoted or removed, **M4 and M5 are not
> built**, and EM-8 ends at M6 with a retirement rather than a feature.

### M4 — The "something to reverse" cap *(M)* — only if M3 passed
`FR-EM-M3`. Two services, in this order:

1. **ai-insights** — the four reversal detectors emit the preceding move's
   extent. Reversals only: a continuation pattern has nothing to reverse, so
   the cap is undefined for it and must not be fabricated.
2. **decision-helper** — `target_module` applies
   `min(measured, preceding)` when the field is present.

Tests first: **H-M4** (the capped objective is never further than either the
uncapped objective or the preceding move), **H-M7** (the **no-op proof** —
with no extent in evidence, `compute_target` returns exactly what it returns
today, demonstrated by the existing suite passing unchanged), `EC-M5`,
`EC-M6` (a cap landing behind entry is **not** a target — fall through rather
than emit an inverted one), **H-M6** bound-default, mutation-checked.

### M5 — GATE: does the cap help? *(S)* — only if M4 was built
> **Criterion, pre-registered.** The cap must improve **expectancy**, not
> completion rate.
>
> Stated as a criterion because the obvious metric is invalid: **completion
> rate is gameable by shrinking the target.** A cap mechanically raises
> completion, since a nearer objective is easier to reach, so a higher rate is
> evidence of *nothing*. Only what the position earns can judge it.

### M6 — Decision and write-up *(S)*
`docs/em8_measuring.md`: the criteria, what happened, what ships. Register,
roadmap and `USER_GUIDE` updated. Frontend only if something shipped.

## 3. Method notes fixed in advance

**The outcome window starts at the DETECTION bar, never at the pattern's key
bar.** A detector run on `bars[:t+1]` may return a pattern whose head or
neckline sits well before `t`. Measuring the outcome from the key bar would
credit the pattern with moves that happened before it was knowable — the exact
look-ahead that EM-6 D1's first test contained, where I read `Pivot.index`
instead of `confirmed_index`. The signal bar is `t`.

**Clustering is by symbol** (SRS §6a). A pattern objective is a per-symbol
treatment, unlike EM-6's market-wide gate where symbol clustering would have
manufactured significance. The level of clustering follows the level the
treatment is applied at.

**Report the sample at every level**: detections, episodes, usable
observations after non-overlap, and exclusions by reason (`EC-M1`, `EC-M2`).
`#87`'s lesson is that a silently shrinking sample is what misleads, and
`#66`'s is that the honest n is the number of independent events.

## 4. The engineering risk, named

`base.py:208`'s `_find_pivots` scans the **whole** frame it is given, so
calling 13 detectors at every bar of a 3,500-bar frame for 92 symbols is
~4.2M detector calls over quadratic pivot work. That will not finish, and this
project has met it before — EM-2 S5 took the suite from 12s to over 120s and
was fixed by hoisting and vectorising.

**Mitigation:** pass a **trailing slice** (detectors have bounded lookbacks —
60 bars for triangles, plus `swing_window`), not the full history. Because
that is an optimisation that could change results, M2 must **assert
equivalence** on a sample rather than assume it — the same self-check the
EM-6 witness study carries for its trailing regime window.

If it is still too slow, the universe is reduced and **the reduction is stated
in the report**, never quietly applied.

## 5. Criteria in one place

| question | task | criterion | on failure |
|---|---|---|---|
| (a) is the claim true | M2 | completion beats a matched random-entry null at ≥2 of 3 horizons per family, symbol-clustered, Holm across families | **reported, not a stop** |
| (c) is it a good exit | **M3 — GATE** | `MEASURED_FIRST` beats `NO_MEASURED` and `TRAILING_ONLY` on net P&L/trade OOS, symbol-clustered | demote/remove `MEASURED_MOVE`; **skip M4+M5** |
| (b) does the cap help | **M5 — GATE** | the cap improves **expectancy** (never completion) | the cap does not ship |
| — | M1 | correctness against the source; no statistic | n/a — unconditional |

## 6. Sequencing

```
M1 (S, unconditional fix)
  → M2 (M, answers (a), reports either way)
    → [GATE] M3 (M, answers (c))
       ├─ pass → M4 (M) → [GATE] M5 (S) → M6 (S)
       └─ fail → M6 (S): retirement
```

Total **S–M**. The largest task (M4, two services) is last and conditional,
which is the opposite of the order the register implied — the register led
with the cap because it reads as the "feature", but it is the part most easily
made unnecessary by a measurement.

## 7. Out of scope

* New detectors (rectangle, diamond, rounding turn) — and item 124 **forbids**
  giving a rounding turn a formula.
* Semi-log measurement, though E&M note the gap rule *"works particularly well
  on semi-log"*. It changes every formula's arithmetic and deserves its own
  measurement.
* The 3-week flag caution — a detector-validity rule, not a measuring rule.
* `market_indices` (`#91`) and the EM-4 history gap (`#90`) — unrelated.

## 8. Standing risks

1. **Drift will flatter the objectives.** A "minimum" objective in the
   direction of an established move gets reached by drift alone, which is why
   (a)'s null is matched on distance and direction. If (a) passes without the
   matched null also rising, suspect the matching before believing the result.
2. **(c) is the one that can change shipped behaviour**, and the book expects
   our code to lose it: Ch 32 prefers progressive stops *because* the overrun
   is unbounded. A retirement is a real deliverable, and cheaper to act on
   than a feature.
3. **The cap cannot be judged on the metric everyone will reach for.** Written
   into M5 rather than left to be remembered.
