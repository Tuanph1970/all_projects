# Implementation plan — EM-7: the throwback entry at a broken boundary

**Phase:** 2 (plan)
**Date:** 2026-10-22
**Design:** `docs/SRS_edwards_magee_throwback.md` v1.0
**Backlog:** `#67`

One task per session: tests first, run them, show them passing, **stop**.
**Two gates**, and the first one is cheap enough to close EM-7 in three
sessions if the effect is not there.

---

## 1. The four open questions, settled

**Q3 — do the two triggers make each other unobservable?** Yes, if combined,
and that is the `#83` bug class: capping severities made `#82`'s override
structurally unreachable. **Settled by design: the triggers are mutually
exclusive modes.**

| mode | trigger |
|---|---|
| `OFF` | default; pipeline unchanged |
| `BAND` | price returns to within a band of the broken level (`FR-EM-T2`) |
| `RETRACE_40` | price retraces 40% of the break move (`FR-EM-T4`) |
| `EITHER` | whichever comes first — **E&M's own wording** |

`EITHER` is the book's rule, so it is the one that would ship. But measured
alone it cannot say which half does the work, so all three are arms and
`EITHER` is justified only if it beats both singles.

**Q1 — the proximity band.** Measured, not chosen, and in **ATR units** rather
than percent, for the cross-symbol comparability EM-9 established and EM-2
S5/S6 reuse. Sweep `{0.25, 0.5, 1.0}` ATR, primary **0.5**.

**Q2 — the staleness window.** Sweep `{20, 60, 120}` bars, primary **60**.

> **The trap both of these carry, named now:** a wider band and a longer
> window each find more throwbacks **trivially**. So the null in `T2` must be
> matched on **band and window**, not merely on direction — the EM-2
> matched-distance lesson. An unmatched null would measure how generous the
> band is, not whether throwbacks exist.

**Q4 — the boundary ordering.** E&M's claim is trendline > H&S > double top.
**That ordering is not testable in this scope**, and no proxy is invented for
it: classifying a level into a pattern family needs a pattern detector, which
§2 of the SRS rejected, and the trendline arm needs EM-5. Saying so is the
honest answer.

Two orderings that *are* available in-process and are pre-registered instead:

* **by level strength** (touch count) — EM-2 established that touches are the
  thing that carries information about a level, so if throwbacks are a level
  phenomenon they should be stronger at better-tested levels;
* **by break direction** — support broken down versus resistance broken up.
  E&M's own Return-Line asymmetry suggests up and down are not mirrors, and
  `#85`/`#86` already found a long/short asymmetry in this system.

## 2. Tasks

### T0 — Roadmap rows *(XS)*
`#67` to In Progress with the phase and `FR-EM-T*` IDs. A Feature Inventory
row. No code.

### T1 — Break-aware levels, in-process *(S)* — **DONE 2026-10-22**
`FR-EM-T1`. Extend `backtest/market_features.py`'s S/R computation so each
level carries: the bar it was decisively penetrated, the direction, and its
**effective type** after the break.

Tests first:
* **H-T4 role alternation** — an oscillating series must not report a support
  as broken upward on every rally. This is EM-2 S5's bug, and it was found
  there only by building a genuinely quiet fixture instead of trusting an
  oscillating one; the same fixture discipline applies.
* **H-T1 causality** — appending future bars moves no past break.
* **H-T8 replica agreement** — the in-process logic agrees with
  `analysis-service`'s shipped `sr_volume.detect_breaks` on shared fixtures.
  Two implementations are tolerated only because the architecture forces it,
  so the agreement is asserted.
* **H-T7 bound-default guard**, mutation-checked. Eighth instance.

**Outcome:** `market_features.py` gains `BREAK_ATR_MULTIPLE` (0.5, the
service's value), `BREAK_ATR_PERIOD`, `atr_series` (Wilder, aligned, causal),
`detect_level_breaks` and `effective_level_type`; `compute_sr_levels` now
attaches `breaks`, `effective_type`, `broken_at` and `break_direction` to each
level, additively. `tests/test_level_breaks.py`, **29 tests**, and
`tests/em7_reference_breaks.py` as a subprocess helper.

**H-T8 actually ran, and the two implementations agree exactly** on all five
fixtures — including the quiet one, where both say zero. It runs in a
**subprocess** because both services define a top-level `app` package, so
putting analysis-service on `sys.path` inside the session would shadow
decision-helper's own and corrupt every later test. The same ATR series is
handed to both, which isolates the alternation logic from any difference in
ATR formulation.

Four mutations, all caught: dropping the alternation (9 failures), counting
penetrations in **either** direction — EM-2 S5's actual shipped bug — (11),
allowing a zero/NaN band (3), and reading the first break instead of the
latest (1).

**My quiet fixture was wrong first.** It placed the level at 100 inside an
oscillation spanning 98.8–102.4, where price genuinely *does* break down
through it, so the test failed against correct code. A quiet fixture has to be
quiet **relative to the level**. The level moved to 97, below the whole range,
and a second test now asserts the fixture still *would* fire a
both-directions rule 20+ times — so it cannot silently become vacuous.

One scoping note recorded in the code: `atr_series` is Wilder's and matches
the service, while the existing `compute_atr` is a simple average consumed by
the stop module. Changing that one would alter shipped stop behaviour and
needs its own measurement, so the two coexist deliberately.

### T2 — GATE 1: is a throwback more than a coincidence? *(M)* — **DONE 2026-10-22: PASS**
The cheapest decisive measurement, and it needs no detector and no pipeline
change — only `T1` and the `#87` deep history.

Two questions, both E&M's:

1. **Frequency.** How often does price return to a broken level within the
   window?
2. **Exactness.** *"Pullbacks … stop **more exactly** at the old line."*
   Measured as the distribution of **overshoot beyond the level** on the
   return, in ATR units. This is a second, independent reading of the same
   claim, and a cheap one.

> **Pre-registered criterion.** Against a **band- and window-matched**
> random-entry null — same symbol, same band, same window, random reference
> prices instead of broken levels — the return rate must be higher **and** the
> overshoot smaller, at the primary `(0.5 ATR, 60 bar)` setting, clustered
> **by symbol**.
>
> Clustering by symbol is right here and would have been wrong at EM-6: a
> level is a per-symbol object. The level of clustering follows the level the
> treatment is applied at.
>
> **If neither holds, stop.** A throwback that happens no more often than
> chance and stops no more precisely is a random limit order with a story
> attached, and the remaining three tasks are wasted. Record the negative and
> close `#67`.

Reports the full `band × window` grid whatever it shows, reading **sign
robustness across the grid** rather than the best cell (`#84`), plus the two
pre-registered orderings from §1 Q4.

**This task also produces the fill rate** that `T4`'s benchmark needs, which
is why it comes first for a second reason.

**Outcome:** `docs/em7_gate1.md`. **PASS on both halves in 9 of 9 cells.** At
the primary setting: return 82.3% vs a matched null of 72.3% (**+10.0pp**,
t = +22.67), and overshoot **0.23 ATR smaller** (t = −8.29), on 85,623 breaks
across 92 symbols.

The effect is **small and very consistent**, not large: a `t` of +22 on 92
clusters comes from low variance across symbols, and the edge is 10 points on
a **72% base rate** — price returns to a level it sits half an ATR from,
within 60 bars, nearly three times in four, with no break involved.

Orderings: strength directionally right but a whisper (83.4% vs 81.1%);
break **direction** larger at +4.5pp (downward 84.7% vs upward 80.2%),
descriptive only.

**The null was wrong first**, and it passed spectacularly — +75pp at t = +24.7
— because it matched only a *minimum* distance, so 2010 levels sat hundreds of
ATRs from 2024 prices and could never return. Now matched on the break's own
penetration distance. The fill rate `T4` needs is therefore **~82%**, not the
~100% an unmatched study would have implied.

### T3 — The throwback detector *(M)* — **DONE 2026-10-22**
`FR-EM-T2`, `T3`, `T4`, `T5`, `T8`. A new signal in
`app/services/signal/trend/`, `OFF` by default, with the four exclusive modes
from §1.

Tests first: **H-T2** planted throwback fires at the return bar and only
there; **H-T3** planted absence fires nothing however long the series runs;
**H-T5** no double-count with `failed_signal.py` (`EC-T2` — a throwback that
breaks straight through is a failure, not both); `EC-T3`–`EC-T6`; and the
no-op proof that with the detector `OFF` the existing suite is unchanged.

**Outcome:** `app/services/signal/trend/throwback.py` + `tests/test_throwback.py`
(25 tests), wired into `_run_signals` behind `BacktestConfig.throwback_mode`
(`OFF` by default) so the no-op proof is real and `T4` is purely a
measurement. Defaults are Gate 1's primary setting — 0.5 ATR, 60 bars — and
`DEFAULT_RETRACE_PCT = 0.40` is labelled as E&M's 1940s figure, not a measured
one.

**Confidence is a constant, deliberately**, and the docstring says why: Gate 1
measured which evidence relates to the return, and the touch count is a
whisper (+2.3pp) while break direction (+4.5pp) was reported as *descriptive
only*. Modulating on either would be acting on the data that generated the
observation. The evidence dict carries the raw facts so a later task can
measure what should weight them.

**Mutation checks: four of five caught.** The survivor is instructive —
changing `age <= 0` to `age < 0`, so a break on the current bar would be
eligible, broke nothing. Age 0 is **unreachable by construction**: a decisive
break puts the close at least one band beyond the level, so `BAND` cannot also
be true, and at the break bar the post-break extreme *is* that bar, so nothing
has been given back and `RETRACE_40` cannot be true. The guard is therefore
**defensive, not load-bearing**, and the test now asserts those two reasons
directly rather than pretending to exercise it — the `#89` lesson.

Also fixed before it could cost anything: the first version called
`compute_sr_levels` twice per bar, once inside the candidate loop. Harmless in
a unit test, ruinous for `T4`'s 92-symbol replay.

### T4 — GATE 2: does it beat taking the breakout? *(M)* — **DONE 2026-10-22: FAIL**
`§6` of the SRS. Three arms on the **same** breakouts: enter at the break
(today's `SR_BREAKOUT`), wait for the throwback, wait for the 40% retracement.

> **Pre-registered criterion.** Net P&L **per breakout opportunity** —
> counting the opportunities the rule declines as **zero**, not excluding them
> — improved over entering at the break, clustered by symbol, with the fill
> rate reported beside it.
>
> Average entry price alone is **invalid** and is not accepted as evidence: a
> rule that fills only on the best 20% of setups will always show a better
> average fill while making less money. This is written here because it is the
> number that will look most persuasive and mean least.

**Outcome:** `docs/em7_gate2.md`. **FAIL** — and the pre-registered metric is
exactly what caught it. On 85,033 opportunities the throwback gets a **2.81%
better entry price**, fills **82.3%** of the time (Gate 1 predicted 82.3%),
and earns **−0.375pp per opportunity** against taking the break, t = −2.86,
**30 of 92 symbols better**, sign p = 0.001. It fails on magnitude *and*
consistency.

**The mechanism is adverse selection, and it was measured rather than
asserted.** The BREAK return on opportunities the throwback *declined* exceeds
those it *filled* by **+14.17pp** at the 20-session horizon (t = +19.09). The
17.7% that never come back are the ones that **ran** — so the filter removes
the best breakouts, and *the second chance is offered precisely when the first
was not worth taking.*

**One limitation, logged not claimed:** the `RETRACE_40` arm does not
faithfully test E&M's rule. It fills 98.5% with 0.21% better entry — the same
trade a bar later — because the move is measured to the extreme *so far*, so
40% of a tiny move is given back immediately. E&M intend a developed move.
**Untested, not refuted.**

### T5 — Decision and write-up *(S)*
`docs/em7_throwback.md`. Default stays `OFF` unless both gates passed. Register,
roadmap, `USER_GUIDE` updated. No frontend unless it ships.

## 3. Criteria in one place

| gate | task | criterion | on failure |
|---|---|---|---|
| 1 | **T2** | higher return rate **and** smaller overshoot than a band/window-matched null, symbol-clustered, at the primary setting | **stop**; close `#67` negative |
| 2 | **T4** | net P&L per breakout **opportunity** beats entering at the break, declines counted as zero, symbol-clustered | detector stays `OFF`; record as measured |
| — | T2 | report the whole `band × window` grid; read **sign robustness**, not the best cell | — |
| — | T4 | average entry price is **not** evidence | — |

## 4. Sequencing

```
T0 (XS) → T1 (S) → [GATE 1] T2 (M) → T3 (M) → [GATE 2] T4 (M) → T5 (S)
```

Total **S–M**, front-loaded: `T2` needs only `T1`, so **two working sessions
decide whether the remaining three are worth running** — the structure that
closed EM-6 in three sessions instead of nine.

## 5. What is deliberately not here

* **Trendline throwbacks** — EM-5 (`#65`). The half E&M rate highest.
* **The head-to-right-shoulder line**, E&M's third trigger — needs a pattern
  detector in-process, which the SRS rejected on measurability grounds.
* **Return lines** — need EM-5, and E&M say they do not work anyway. Kept as
  `FR-EM-T6` so that whoever builds EM-5 does not wire them in as boundaries.
* **Wiring ai-insights patterns into signal evidence** — EM-8 measured those
  objectives; three of five families are worse than chance.

## 6. Standing risks

1. **This is another elaboration on EM-2's levels, and every previous one
   failed.** EM-2 closed on a documented negative: the levels were real —
   every arm beat a matched-distance null — and *no* EM-2 measure beat simply
   counting touches. `T2`'s null exists because that history says the base
   rate here is high.
2. **The band and window can manufacture the result.** Hence matching the
   null on both, and reading the grid rather than its best cell.
3. **The scope tests the weaker claim.** If `T2` returns a null, that is a
   null on *pattern-boundary* throwbacks, **not** on E&M's trendline claim,
   and the write-up must not overstate it.
4. **`EITHER` is the book's rule but the least interpretable arm.** If it wins
   while both singles fail, suspect the composition before believing it.
