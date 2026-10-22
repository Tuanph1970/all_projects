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

### T1 — Break-aware levels, in-process *(S)*
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

### T2 — GATE 1: is a throwback more than a coincidence? *(M)*
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

### T3 — The throwback detector *(M)* — only if GATE 1 passed
`FR-EM-T2`, `T3`, `T4`, `T5`, `T8`. A new signal in
`app/services/signal/trend/`, `OFF` by default, with the four exclusive modes
from §1.

Tests first: **H-T2** planted throwback fires at the return bar and only
there; **H-T3** planted absence fires nothing however long the series runs;
**H-T5** no double-count with `failed_signal.py` (`EC-T2` — a throwback that
breaks straight through is a failure, not both); `EC-T3`–`EC-T6`; and the
no-op proof that with the detector `OFF` the existing suite is unchanged.

### T4 — GATE 2: does it beat taking the breakout? *(M)*
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
