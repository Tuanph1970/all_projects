# SRS — EM-7: the throwback entry at a broken boundary

**Version:** 1.0 (Phase 1 design)
**Date:** 2026-10-22
**Backlog:** `#67`
**Register:** `docs/implementation_plan_edwards_magee.md` § EM-7
**Status:** design only. Nothing is built.

---

## 1. What the book requires

E&M treat the return to a broken boundary as a **second chance**, and they are
unusually specific about it.

**Ch 6 — the pullback is the entry, and the stop reference:**

> **Pullback** to the neckline after the break is common; whether it occurs
> depends largely on the general market. It is **the short-seller's second
> chance and his stop-placement reference.**

**Ch 33 — the tactic, stated as "whichever comes first":**

> Short sales after the breakout, on a recovery of **40%** of the distance
> from the right-shoulder top to the breakout low, *or* on a rally to a line
> drawn down across the head and right shoulder, *or* **on a pullback to the
> neckline — whichever comes first.** If the breakout continues for several
> days, compute the 40% on the whole move.

The bottom mirrors it, with a volume condition: *"new purchases on a 40%
reaction (which must be on decreasing volume), or … on a throwback to the
neckline."*

**Ch 13 — why it works, and this is the part that decides our design:**

> **Pattern resistance** — *the mechanism explains the patterns*: a broken
> descending-triangle demand line becomes resistance; a broken H&S neckline
> becomes resistance; a rectangle's supply line becomes support once
> decisively exceeded. **Throwbacks to a pattern boundary need no 10%-away
> rule — a conclusive breakout is enough.**

**Ch 14 — the best version of the effect, and an asymmetry:**

> After a decisive break of an intermediate up-trendline … expect a
> **pullback to the projected trendline** — one of the book's open mysteries:
> pullbacks follow trendline breaks **more frequently** than pattern breaks
> and stop **more exactly** at the old line. *"No one knows why."* Note the
> asymmetry: a **Return Line does not** function as support after prices
> break out above it.

### A frequency ordering that is testable

E&M make a **relative** claim across three boundary types, which is stronger
evidence than any single frequency because it predicts an ordering:

| boundary | claimed pullback frequency |
|---|---|
| broken **trendline** | most frequent, and stops most exactly |
| broken **H&S neckline** | *"common"*, market-dependent |
| broken **double top** | *"happen, but less often than with H&S"* |
| **broadening top** | *"at least 4 of 5 cases"*, retracing about half |
| **Return Line** (after an upside break) | **does not act as support** — a stated negative |

The Return Line line is the most useful of these: a named case where the
effect should be **absent**. A study that finds throwbacks everywhere,
including there, has measured something other than the effect.

## 2. Feasibility, decided first — because EM-8 just showed why

EM-8's M3 found `MEASURED_MOVE` to be **dead code**: it reads a key out of
`signal_evidence` that no shipped detector ever puts there, so the mechanism
could not be measured at all. EM-7 wants a *broken pattern boundary* at signal
time, which is the same class of dependency. So the anchor is chosen for
**reachability and measurability**, before anything else.

| option | boundary source | live | backtest (C4) | verdict |
|---|---|---|---|---|
| **A** | ai-insights `patterns_data`, already fetched at `orchestrator.py:119` | yes | **no** — the harness makes no per-bar HTTP calls, by design | **rejected**: the MEASURED_MOVE trap exactly. An unmeasurable mechanism cannot clear C4. |
| **B** | add `chart-decomp-lib` (it has `head_shoulders.py`, `double.py`, `triangle.py`) to decision-helper | yes | yes | **rejected**: production would run ai-insights' detector while the backtest measured chart-decomp-lib's. Two implementations of one pattern is how they drift — EM-6 D1 found exactly that, where a study's private copy of the swing rule was wrong on 906 of 5,672 bars. |
| **C** | **a broken S/R level, with role reversal**, computed in-process | yes | **yes** | **chosen** |

**Option C is not a compromise — it is Ch 13's own mechanism.** The book says
*"pattern resistance — the mechanism explains the patterns"*: a neckline works
as resistance *because* it is a broken support level, not because it is part
of an H&S. Anchoring on the level rather than on the pattern is therefore
closer to the stated cause, and it drops the pattern-detector dependency
entirely.

It also pairs with something already shipped: **`SR_BREAKOUT` fires when a
level breaks, and EM-7 fires when price returns to that same level.** One
level object, two entries, and the second is the register's *"second chance"*.

### What this costs, stated plainly

* **The trendline throwback is out of scope**, and it is the half E&M rate
  highest — *"more frequently … more exactly."* It needs a trendline engine,
  which is **EM-5 (`#65`), not built**. EM-7 therefore tests the *weaker* of
  the book's two claims, and the result must be reported as such rather than
  as a verdict on the throwback idea.
* **An in-process replica.** `market_features.py` exists for exactly this —
  *"the harness cannot make per-bar HTTP calls, so these functions replicate
  the same concepts from raw bars"* — so a replica is the established pattern
  here, not a novelty. But the harness's `compute_sr_levels` is a bare
  swing-cluster with `strength: 1`, carrying **none** of EM-2's break history
  or role reversal, so that logic has to be added. `FR-EM-T7` requires a
  consistency check against analysis-service's shipped version, because
  EM-2's `detect_breaks` is where role **alternation** was already got wrong
  once and fixed.

### Data

**No DB change.** Levels and breaks are derived from bars in-process; nothing
is persisted.

## 3. Functional requirements

**FR-EM-T1 — A broken level remembers that it was broken.** Extend the
in-process S/R computation so each level carries its break history: the bar at
which it was decisively penetrated, the direction, and its **effective type**
after the break (a broken support becomes resistance, and conversely). EM-2's
role **alternation** is the reference: a level must not be recorded as broken
in both directions by the same oscillation.

**FR-EM-T2 — The throwback detector.** A new signal in
`app/services/signal/trend/`: after a level is broken at bar *b*, price
returning to within a band of that level at bar *t > b* is an entry **in the
direction of the break**. Long on a throwback to a broken resistance; short
on a pullback to a broken support.

**FR-EM-T3 — No distance precondition.** *"Throwbacks to a pattern boundary
need no 10%-away rule — a conclusive breakout is enough."* The only
precondition is that the break was conclusive, which the existing penetration
filter already defines (`EM-9` swept it and recommended leaving it at 3%).

**FR-EM-T4 — The 40% rule, as a second trigger.** Entry also on a retracement
of **40%** of the move from the pre-break extreme to the post-break extreme,
**whichever comes first** with `FR-EM-T2`. Both are E&M's, and the book's own
wording makes them alternatives rather than a conjunction. 40% is a 1940s NYSE
figure and is swept, not trusted (`CLAUDE.md` rule 3).

**FR-EM-T5 — The staleness bound.** A throwback is a *second chance*, not a
standing offer. A level broken 200 bars ago and revisited is a different event
from one broken last week. The window is a parameter, measured.

**FR-EM-T6 — The Return Line is excluded, and that is testable.** E&M state
that a return line does **not** act as support after an upside break. The
in-process replica has no return lines (they need EM-5), so this requirement
is satisfied vacuously today — but it is written down so that whoever builds
EM-5 does not wire them in as if they were boundaries.

**FR-EM-T7 — The replica must agree with the service.** The in-process break
and role-reversal logic is checked against `analysis-service`'s shipped
`sr_volume.detect_breaks` on shared fixtures. Two implementations are
tolerated here only because the architecture requires it, so the agreement is
asserted rather than hoped for.

**FR-EM-T8 — Off by default.** The detector ships disabled behind a config
flag until the `§6` benchmark passes, which is the `#82` discipline: an
unmeasured signal that ships enabled distorts every statistic computed
afterwards.

## 4. Edge cases

| ID | case | required behaviour |
|---|---|---|
| **EC-T1** | the level is broken and price never returns | **no signal** — and the *frequency* of this is the headline measurement, not an error case |
| **EC-T2** | price returns and keeps going through the level | the throwback **failed**; no entry, and the level's role reverses again. This is `failed_signal.py`'s territory and must not be double-counted as both a throwback and a failure. |
| **EC-T3** | the same level is broken, retested, broken again | one throwback **episode** per break, not per bar of proximity |
| **EC-T4** | two levels within one band | the nearer governs; a single bar must not fire two throwbacks |
| **EC-T5** | the break and the throwback are the same bar | reject — a bar that pierces and closes back is a failed break, not a break plus a throwback |
| **EC-T6** | a throwback into a level that is also an untouched opposite-side level | no signal; contradictory evidence is not an entry |

## 5. Harnesses

| ID | harness |
|---|---|
| **H-T1** | **Causality.** The signal at *t* uses bars ≤ *t*; appending future bars changes no past signal. |
| **H-T2** | **Planted throwback.** A constructed break-and-return fires at the return bar, and only there. |
| **H-T3** | **Planted absence.** A break with no return fires nothing, however long the series runs. |
| **H-T4** | **Role reversal is alternating**, per EM-2's S5 fix: an oscillating series must not report a support as broken upward on every rally. |
| **H-T5** | **No double-count with `failed_signal`** (`EC-T2`). |
| **H-T6** | **Null-FPR.** On random-walk data the throwback rate must be reported against a matched random-entry null — a level is "returned to" often by chance, which is the whole risk of this idea. |
| **H-T7** | **Bound-default guard**, mutation-checked. Eighth instance. |
| **H-T8** | **Replica agreement** with `analysis-service` (`FR-EM-T7`). |

## 6. Mandatory benchmark (C4)

The register names it, and it is the right one:

> Entry quality versus **taking the breakout itself** — a better average entry
> price must not be paid for with a materially lower fill rate.

So the comparison is three arms on the same breakouts:

1. **enter at the break** (what `SR_BREAKOUT` does today);
2. **wait for the throwback** — better price when it fills, **no trade when it
   does not**;
3. **wait for the 40% retracement** (`FR-EM-T4`).

> **Pre-registered criterion.** The throwback arm must improve **net P&L per
> breakout opportunity** — counting the opportunities it declines as zero, not
> excluding them — with significance clustered **by symbol**. Reporting
> average entry price alone is invalid: a rule that only fills on the best 20%
> of setups will always show a better average fill while making less money.

**And the frequency question is a deliverable in its own right**, because it
is E&M's actual claim and it is cheap:

> How often does price return to a broken level within N bars, and how exactly
> does it stop there — measured against a matched random-entry null, and
> ordered across boundary types to test E&M's claim that trendline breaks
> pull back more often than pattern breaks?

The ordering is testable even without EM-5 for the *pattern* half: H&S-like
necklines versus double-top-like levels, which the book says differ.

## 7. Out of scope

* **Trendline throwbacks** — blocked on EM-5 (`#65`). The headline half.
* **Pattern-specific geometry** (the head-to-right-shoulder line, the third of
  E&M's three triggers) — it needs a pattern detector in-process, which §2
  rejected.
* **Return lines** — they need EM-5, and E&M say they do not work anyway.
* **Wiring ai-insights patterns into signal evidence.** EM-8 measured those
  objectives and three of five families are worse than chance; this SRS does
  not revisit it.

## 8. The honest prior

Better than EM-6's, worse than EM-1's.

**For:** the mechanism is Ch 13's and it is the one E&M explain rather than
merely assert; EM-2 already established that **levels are real** on this data
(every arm beat a matched-distance null significantly) even though no EM-2
*measure* beat counting touches; and the entry pairs with a signal that
already fires.

**Against:** price returns to a recently broken level **often by chance** —
that is what `H-T6` is for, and a throwback rule could look excellent on fill
quality while being indistinguishable from a random limit order. EM-2's
closing result is the direct warning: the levels were real, every elaboration
on them failed. EM-7 is another elaboration on the same levels.

**And the scope cost is real:** this tests the weaker of E&M's two throwback
claims, because the stronger one needs a module that does not exist.
