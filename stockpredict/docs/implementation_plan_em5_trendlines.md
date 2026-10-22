# Implementation plan — EM-5 Phase A: the trendline engine and Gate A

**Phase:** 2 (plan), **Phase A scope**
**Date:** 2026-10-23
**Design:** `docs/SRS_edwards_magee_trendlines.md` v1.0
**Backlog:** `#65` — the last candidate in the E&M register

One task per session: tests first, run them, show them passing, **stop**.
**One gate**, and it now arrives at task 4 of 6 rather than task 5 — see §3.

---

## 1. The four open questions, settled

**Q1 — the contact tolerance.** How near a close must sit to the line to count
as a contact. **In ATR units**, not percent, for the cross-symbol
comparability EM-9 established and EM-2's S5/S6 reuse. Primary **0.25 ATR**,
sweep `{0.1, 0.25, 0.5}`.

> Tighter than EM-7's 0.5 ATR band, and deliberately. A *band* asks whether
> price came back to a level; a *contact* asks whether price arrived **at the
> line**. A loose tolerance inflates every line's contact count equally and
> would **saturate** the measure — which would make `FR-EM-L8`'s authority
> ordering untestable rather than merely weak. The tolerance is therefore
> chosen to protect the secondary test, and the sweep reports whether that
> choice mattered.

**Q2 — the anchor-span minimum** (`EC-L2`). Two anchors must be at least
**10 bars** apart, sweep `{5, 10, 20}`. E&M's second authority test *is*
length/duration, so a line needs enough span to have duration at all; a line
through adjacent pivots is noise with a slope.

**Q3 — the lookback bound** (`EC-L4`). **250 bars**, which is what production
hands its detectors (`lookback_bars=250`, `df.tail(250)`) — the EM-8 `M2`
lesson that a windowed detector must be measured in **production's** window,
not an invented one.

> But the bound is **not** how the line set is kept sane. `FR-EM-L2`'s
> price-track constraint is, and `L1` **measures the surviving-line count
> distribution** so the number is known rather than assumed. If a cap were
> doing the pruning, the line set would be a function of the cap rather than
> of the price action — which is why §3 puts the constraint before the
> enumeration is allowed to grow.

**Q4 — penetration: 3% or ATR?** **3% of price is primary**, because it is the
book's figure for a stock and because EM-9 swept the pattern analogue and
recommended leaving it at 3%. An **ATR-unit equivalent is a declared
alternative arm**, swept and reported. Both are published whatever they show.

## 2. The comparison that *is* Gate A

The gate needs a precise "horizontal level through the same anchors", so it is
fixed here rather than at measurement time.

A line is anchored on two confirmed pivots at prices `p₁` (earlier) and `p₂`
(later). The horizontal counterfactual is **`p₂`, the most recent anchor's
price** — because that is exactly the level EM-2 and EM-7 actually use: a
horizontal level sitting at a pivot. Same pivots, same bars, **slope the only
difference**.

* **Arm T** — breaks of the trendline, detected per `FR-EM-L5`/`L6`.
* **Arm H** — breaks of the horizontal level at `p₂`, via EM-7 T1's shipped
  `detect_level_breaks` (role-alternating, already cross-checked against
  `analysis-service`).
* Robustness arm: the horizontal at the **mean** of `p₁` and `p₂`.

Compared on **forward return after the break**, at 10/20/60 sessions,
**clustered by symbol** — paired per symbol, not per event, because the two
arms break on different bars and there is no honest event-level pairing.

> **Event counts are reported for both arms, prominently.** A trendline has
> more ways to be broken than a horizontal level and may well break far more
> often, or far less; either would make the comparison underpowered in a way
> that a mean return hides. This is the `#87` habit: the honest *n* goes beside
> the result.

## 3. Tasks

### L0 — Roadmap rows *(XS)*
A Feature Inventory row for EM-5 with the Phase A/B split and the anchor
decision recorded. `FR-EM-L*` IDs wired. No code.

### L1 — The admissible-line enumerator *(S–M)*
`FR-EM-L1`, `L2`, `L3`. Lines through pairs of **confirmed** same-side pivots
(`dow.confirmed_pivots`, which already carries `index` vs `confirmed_index`,
so no line is anchored on a pivot that was not yet knowable); closes only;
**and the price-track constraint built in the same task, not after it.**

Tests first: **H-L1** determinism, **H-L2** causality (including that no
anchor's `confirmed_index` postdates the bar), **H-L4** the price-track
constraint bites — a fixture where a single intervening close is the only
difference between admissible and not — **H-L5** closes-not-extremes
(perturb highs and lows, nothing moves), **H-L9** line-count sanity.

**Deliverable beyond the code:** the **surviving-line count distribution** on
real data, which settles Q3 empirically and tells the next task whether the
enumeration is tractable.

### L2 — Penetration, the shakeout guard, and amendment *(M)*
`FR-EM-L5`, `L6`, `L7`. A close beyond by 3% (need not be in one day); a crack
that closes back above is **not** a break; and the amendment rule recorded
explicitly so an amended line is never silently a different line.

Tests first: **H-L6** the shakeout fixture, **H-L7** amendment recorded with
pre- and post-amendment anchors differing, **H-L8** bound-default guard
mutation-checked (**tenth** instance).

### L3 — GATE A: does the slope earn anything? *(M)*
§2's comparison. No pipeline change, no signal — a study over the `#87` deep
history, as `T2` and `M2` were.

> **Pre-registered criterion.** Arm T must beat Arm H at **two or more** of the
> 10/20/60-session horizons, clustered by symbol, with event counts reported
> for both arms.
>
> **On failure: stop.** `L4` is not built, and EM-5 is recorded as what it
> would then be — a re-derivation of EM-2's levels with extra steps. Phase B
> (fan principle, channel, frontend) is not built either.

### L4 — Authority: contacts, duration, angle *(S)* — only if Gate A passed
`FR-EM-L4`, and the secondary from the SRS: do lines with more contacts give
better outcomes, and does the effect follow E&M's weighting
(contacts ≫ duration > angle)? Reported as an **ordering**, with EM-2's prior
stated: contacts will probably matter and the composite probably will not.

**H-L3** planted line (three closes exactly on a line give contact count 3;
a fourth raises it to 4).

### L5 — Decision and write-up *(S)*
`docs/em5_trendlines.md`. Register, roadmap, `USER_GUIDE` updated. Phase B is
recommended **only** if Gate A passed, and the recommendation names which of
its four pieces the result actually supports.

## 4. Why authority moved behind the gate

The SRS listed contacts/duration/angle before the measurement, and that
ordering was wrong. **Gate A does not need them**: it compares a sloping line
against a horizontal one through the same anchors, and neither arm uses an
authority score. Contacts are needed only for the **secondary** ordering test.

So authority moves to `L4`, behind the gate, and **Gate A arrives at task 4 of
6 instead of 5 of 6**. If it fails, Phase A costs four sessions and still
leaves the engine behind — which the Three-Fan Principle, the channel and
EM-7's deferred trendline throwback all need before they can be measured at
all.

## 5. Criteria in one place

| gate | task | criterion | on failure |
|---|---|---|---|
| **A** | **L3** | Arm T beats Arm H at ≥ 2 of 3 horizons, symbol-clustered, event counts reported | **stop**; no `L4`, no Phase B; record as a re-derivation of EM-2 |
| — | L1 | surviving-line count **measured and reported**, not capped into shape | — |
| — | L3 | the whole penetration grid (3% and ATR) published, read for **sign robustness** not best cell | — |
| — | L4 | authority reported as an **ordering**; nothing consumes a score in Phase A | — |

## 6. Sequencing

```
L0 (XS) → L1 (S–M) → L2 (M) → [GATE A] L3 (M) → L4 (S) → L5 (S)
```

**4 sessions to the go/no-go**, 6 if it passes. Reuse that is already built
and tested: `dow.confirmed_pivots` (EM-6 D1), `atr_series` and
`detect_level_breaks` (EM-7 T1), and EM-7's Gate 1/Gate 2 study scaffolding —
deep history, matched comparisons, symbol clustering, paired tests.

## 7. Standing risks

1. **The prior is poor and specific.** EM-2: no elaboration of these pivots
   beat counting touches. EM-7: the tactic built on them lost money. A
   trendline is another elaboration of the same pivots, and Gate A is built to
   find that out in four sessions.
2. **Underpowered for a boring reason.** If trendline breaks are far rarer
   than level breaks, the comparison could fail on *n* rather than on effect —
   hence event counts beside every number.
3. **The determinism risk is in `L1`**, not later. If the admissible set turns
   out to be large and unstable bar to bar, the engine is not usable and that
   is worth knowing at the first task rather than the fourth.
4. **A pass would be interesting and should be treated carefully.** It would
   mean slope carries something a level does not, which is a genuinely new
   claim for this project — and therefore exactly the kind of result to
   re-check before believing, as `#87` had to re-check EM-4's quintiles.
