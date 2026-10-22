# SRS — EM-5 Phase A: the trendline engine, and whether slope earns anything

**Version:** 1.0 (Phase 1 design, **Phase A scope**)
**Date:** 2026-10-22
**Backlog:** `#65`
**Register:** `docs/implementation_plan_edwards_magee.md` § EM-5
**Status:** design only. Nothing is built.

---

## 0. Why this is scoped as "Phase A"

EM-5 is five separable deliverables: the line engine, the penetration test,
the return line/channel, the Three-Fan Principle, and a frontend overlay.
Full scope is **12–16 sessions** on this project's measured throughput, and
the frontend is only worth building if the engine earns it.

So **Phase A** is: the engine, its determinism and causality harnesses, and
**one pre-registered gate**. Phase B — fan, channel, authority wiring,
frontend — is built only if Phase A passes. The structure that closed EM-6 in
three sessions instead of nine.

**Phase A's gate is the question the previous five candidates have been
circling**, and it has never been asked directly:

> **Does the *slope* earn anything?**
>
> A trendline is a sloping level drawn through the same swing pivots that
> EM-2's horizontal levels come from. EM-2 established that levels are **real**
> (every arm beat a matched-distance null) and that **no elaboration beat
> counting touches**. EM-7 established that the throwback to a level is
> **real** and that the tactic built on it **loses money**.
>
> So: does a **trendline** break carry information that a **horizontal level
> through the same pivots** does not? If it does not, EM-5's engine is an
> elaborate re-derivation of EM-2's levels, and Phase B should not be built.

That is cheap, decisive, and novel — and it is a fair test rather than a
strawman, because the comparison arm is built from *identical* pivots.

## 1. What the book requires

**The draw rule (Ch 14).** Up trendlines across the minor-reaction
**bottoms**, down across the minor-rally **tops** — never bottom-to-top, never
through the price track.

**And a decisive instruction about which price to use:**

> Intraday breaks that don't close beyond the line are ignored — **"closing
> prices often make a better trendline than extreme lows, especially in thin
> erratic stocks."**

So the engine fits **closes**, not lows. That agrees with Dow tenet 11 (*only
closing prices used*) and with `market_context/dow.py`, which EM-6 D1 already
built on closes — one vocabulary for "where the trend turned", not two.

**Three tests of authority**, in E&M's own weighting:

> number of contacts **≫** length/duration **>** angle (flatter is more
> significant).

**Three tests of a valid penetration:**

1. **Extent** — a close beyond the line by about **3%** of price (2% in the
   averages). *"It need not happen in one day."*
2. **Volume** — **not required** for a downside break, but an intermediate
   up-trendline break is *"much more often than not"* attended by visibly
   increased activity, which helps in borderline cases.
3. **The pullback test** — a borderline break followed by a *"feeble,
   volume-less rally that rounds over under the line without closing above
   it"* makes the situation critical. And the counterpart: **beware the
   shakeout** — a high-volume crack that **closes back above** the line is
   usually a false move.

**Amendment rules**, which are the determinism problem in concrete form:

> If the original line rested on only **two** points and the third contact
> penetrates it indecisively, **redraw** across the first and third (or second
> and third) bottoms. If the line has already been **confirmed** by a third or
> fourth bottom, **disregard** the indecisive break.

**And the authors' own method, which is explicitly plural:**

> *"Draw every line the action permits, lightly; erase the useless, heavy the
> survivors. The quickest way — in fact, the only way — of acquiring the
> experience."*

**Origin rules:** major bull lines from the **second** intermediate bottom;
intermediate lines from the **right shoulder**, not the head.

### Deferred to Phase B, recorded so it is not lost

* **The Three-Fan Principle** (Ch 14, master-list item 96): a steep line
  breaks, a flatter second line is drawn **from the original high across the
  top of the first upthrust**, that breaks, a third flatter line forms — and
  *"when the third fan line is broken the low of the intermediate correction
  has been seen."* **Corrective moves only.** No analogue anywhere in this
  codebase, and the most interesting untested thing in the register.
* **Return line / channel**, whose best use is **negative** — a rally that
  fails to reach the return line signals deterioration — plus the symmetry
  rule, and the asymmetry that a **return line does not act as support** after
  an upside break.
* **Double trendlines / trend ranges** — two parallel lines a point apart,
  which E&M say define a trend better than one and most technicians miss.
* The **trendline throwback**, which EM-7 deferred here and E&M rate *more
  frequent and more exact* than the pattern version EM-7 refuted.

## 2. The determinism problem, stated before it bites

E&M's method is *"draw every line the action permits"* — plural and
judgmental by design. A chart admits many lines; the technician keeps the ones
that survive. The project's determinism harness requires a single reproducible
answer.

**This is Phase A's main risk and the most likely cause of a blown estimate.**
The resolution is not to pick one line by taste but to make the *enumeration*
total and the *ranking* explicit:

* enumerate **every** line admissible under the draw rule (each ordered pair
  of same-side confirmed pivots);
* discard any line the **price track violates** (E&M: never through the price
  track) — that is a hard, checkable rule and it does most of the pruning;
* rank survivors by E&M's own authority ordering, contacts first;
* the engine returns the **ranked set**, not a single line.

Returning a set rather than a line is faithful to the book *and*
deterministic, and it is what makes the authority ordering testable rather
than assumed.

## 3. Where it lands — a correction to the register

The register says *"most naturally in `analysis-service` beside the S/R
work."* **Phase A puts the engine in `decision-helper` in-process instead**,
for the reason EM-7's Phase 1 and EM-8's `M3` both established: the backtest
harness makes **no per-bar HTTP calls**, so anything that must clear a C4
benchmark needs an in-process path. An `analysis-service` home and the
frontend overlay belong to Phase B, once there is something worth drawing.

**No DB change.** Lines are derived from bars; nothing is persisted.

## 4. Functional requirements (Phase A only)

**FR-EM-L1 — Admissible lines.** For a given bar *t*, enumerate every line
through two **confirmed** same-side pivots (`dow.confirmed_pivots`, which
carries `index` and `confirmed_index` so a line is never anchored on a pivot
that was not yet knowable). Up lines through bottoms, down lines through tops.

**FR-EM-L2 — The price track is a hard constraint.** Discard any up line that
a close falls **below** between its anchors, and any down line a close rises
above. E&M: never through the price track.

**FR-EM-L3 — Closes, not extremes.** Anchors and violations are read on
**closing** prices (§1). Intraday breaks are ignored.

**FR-EM-L4 — Contacts, duration, angle.** Each surviving line reports its
**contact count** (closes within a tolerance of the line), its **duration**
in bars, and its **angle** normalised to ATR per bar so it is comparable
across symbols — the unit EM-9 and EM-2 S5/S6 established. Reported as
evidence; **nothing is scored into a single number in Phase A**, because
EM-2's finding was that elaborate composites do not beat simple counts and
`FR-EM-L8` makes that testable instead of assumed.

**FR-EM-L5 — Penetration.** A close beyond the line by `penetration_pct`
(default **3%**, the book's figure for a stock) counts; it *need not happen in
one day*. The threshold is also expressible in **ATR units** and both are
swept — the book's 3% is a 1940s NYSE figure and a legitimate default, not a
measured one (`CLAUDE.md` rule 3; EM-9 swept the pattern analogue and
recommended leaving it at 3%).

**FR-EM-L6 — The shakeout guard.** A crack that **closes back above** the
line is not a penetration. E&M call it *"usually a false move for that
moment"*, and recording it as a break would both overcount breaks and invert
their meaning.

**FR-EM-L7 — Amendment is explicit, not implicit.** A line resting on exactly
two anchors that is penetrated **indecisively** is redrawn across the first
and third (or second and third) anchors; a line already confirmed by a third
or fourth contact **disregards** the indecisive break. The engine records
which rule applied, so an amended line is never silently a different line.

**FR-EM-L8 — Authority is a hypothesis, not a weighting.** E&M's ordering
(contacts ≫ duration > angle) is itself a testable claim and is **measured**
in §6 rather than encoded. Nothing in Phase A consumes an authority score.

**FR-EM-L9 — Nothing ships enabled.** Phase A adds no signal and changes no
default. The `#82` discipline.

## 5. Edge cases

| ID | case | required behaviour |
|---|---|---|
| **EC-L1** | fewer than two confirmed same-side pivots | no lines — and the *frequency* of this is reported, not treated as an error |
| **EC-L2** | two anchors on the same bar, or an anchor pair spanning fewer than N bars | rejected: a line through adjacent pivots is noise with a slope |
| **EC-L3** | a vertical or near-vertical line (anchors at nearly the same bar) | rejected; E&M say flatter is more significant and a near-vertical line has no predictive content |
| **EC-L4** | the combinatorial blow-up — *k* pivots give *k(k−1)/2* lines | bounded by a lookback and by `EC-L2`; the bound is a **parameter** and the count is reported, because a silent cap would make the line set a function of the cap |
| **EC-L5** | a line admissible at bar *t* but not at *t+1* (a new close violates it) | it leaves the set; lines are **not** persisted across bars, so the set at *t* is always recomputed from bars ≤ *t* |
| **EC-L6** | non-positive prices (13 such bars exist in the vendor data, `#93`) | excluded from anchors and violations |

## 6. The gate

> **Pre-registered criterion (Gate A).** For each trendline break, compare the
> forward return against the break of a **horizontal level through the same
> pivots** — the same anchors, the same bars, the only difference being that
> one line has slope and the other does not. The trendline must beat the
> horizontal comparison at **two or more** of the 10/20/60-session horizons,
> clustered **by symbol**.
>
> **If it does not, Phase B is not built**, and EM-5 is recorded as what it
> would then be: a re-derivation of EM-2's levels with extra steps.

Clustered by symbol because a line is a per-symbol object — the level of
clustering follows the level the treatment is applied at, which EM-6 got right
by accident and EM-7 got right on purpose.

**Declared secondary before running**, so it cannot be promoted afterwards:

* **Authority ordering** (`FR-EM-L8`) — do lines with more contacts give
  better outcomes, and does the effect follow E&M's weighting
  (contacts ≫ duration > angle)? EM-2's prior says contacts will matter and
  the composite will not.
* **Slope sign** — up-line breaks versus down-line breaks. EM-7's Gate 1 found
  a 4.5pp direction asymmetry in level breaks, and `#85`/`#86` found a
  long/short asymmetry; so this is expected to be *present*, which makes it a
  weak test of anything and a reason to report it rather than act on it.

## 7. Harnesses

| ID | harness |
|---|---|
| **H-L1** | **Determinism.** The same bars give the identical ranked line set, every run. |
| **H-L2** | **Causality.** Appending future bars changes no line admissible at a past bar, and no anchor is ever a pivot whose `confirmed_index` is later than the bar in question. |
| **H-L3** | **Planted line.** A series constructed with three closes exactly on a line yields that line with contact count 3; a fourth touch raises it to 4. |
| **H-L4** | **The price-track constraint bites.** A line that would be admissible geometrically but is violated by an intervening close is **absent** — asserted with a fixture where the violating close is the only difference. |
| **H-L5** | **Closes, not extremes.** Perturbing highs and lows while holding closes fixed changes nothing (`FR-EM-L3`), the same guard EM-8 M1 used for the gap rule. |
| **H-L6** | **The shakeout is not a break** (`FR-EM-L6`), with a fixture whose crack closes back above. |
| **H-L7** | **Amendment is recorded** (`FR-EM-L7`): an amended line reports which rule applied, and the pre- and post-amendment anchors differ. |
| **H-L8** | **Bound-default guard**, mutation-checked. Tenth instance. |
| **H-L9** | **Line-count sanity** (`EC-L4`): the set size is reported and bounded, and a fixture asserts the bound is not silently doing the pruning that `FR-EM-L2` should do. |

## 8. The honest prior

**Poor, and specifically poor.** Of six candidates measured, one shipped a
feature. The two findings most relevant here both point the same way:

* **EM-2**: horizontal levels are real; **no elaboration of them beat counting
  touches.** A trendline is an elaboration of the same pivots.
* **EM-7**: the throwback to a level is real; **the tactic lost money**, and it
  lost because waiting filters out the best breakouts.

So Gate A is likely to fail, and it is designed to fail **cheaply** — before
the fan principle, the channel, the authority wiring and the frontend are
built.

**What would make it pass, and is worth taking seriously:** a trendline
encodes *acceleration* that a horizontal level cannot. E&M's whole argument
for flatter-is-more-significant is that a steep line is an unsustainable rate,
and a break of it says something about the *rate* changing rather than about a
price being reached. That is a genuinely different claim from EM-2's, which is
the reason to test it rather than assume the register's five candidates
already answered it.

**And one thing Phase A will deliver whether or not it passes:** the first
standalone, deterministic, causal trendline object in this codebase — which
the Three-Fan Principle, the channel, and EM-7's deferred trendline throwback
all need before any of them can be measured at all.
