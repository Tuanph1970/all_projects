# EM-2 Phase 2 — implementation plan: volume-weighted support & resistance

**Satisfies:** `docs/SRS_edwards_magee_sr_levels.md` (`FR-EM-S1`–`S10`).
**Phase:** 2 (plan). Date: 2026-10-14. No code yet.
**Discipline:** one task per session, tests first where practical, then stop
(`CLAUDE.md`).

---

## Open questions, now settled

### 1. Does `strength` change meaning, or does a new field arrive? — **NEW FIELD**

Settled with evidence rather than preference. `SRLevel.strength` is typed
`int`, and the one consumer whose arithmetic depends on it does:

```python
strength: int = int(lvl.get("strength", 1))
conf = min(0.4 + strength * 0.05 + bounce_depth / 0.01 * 0.1, 0.9)
```

So a volume ratio of `2.3` would be **silently truncated to 2** by that
`int()`, and any genuinely large figure would saturate the `0.9` cap
immediately. Repurposing `strength` would therefore not merely change a
number — it would corrupt it quietly.

**Decision:** `strength` keeps its meaning (touch count, `int`). The new
measure arrives as `volume_strength: Optional[float]`. `sr_bounce_breakout`
is updated **in the same slice** (task `S9`) to prefer `volume_strength` when
present, so nothing keeps reading the weaker measure once the better one
exists — which was the objection to a new field.

### 2. How wide is a "congestion"? — **ANSWERED at `S1`, and not as expected**

Both candidate definitions were implemented, then measured against real levels.
**Neither works when applied to a whole cluster**, because `_find_sr_levels`
groups every visit to a price across the entire window, so a cluster's touches
are scattered: FPT's strongest level spanned bars 114–220, TCB's spanned
21–243 — 226 of 250 bars. "The congestion is most of the year" is not a
congestion, and the strength that falls out of it carries no information:

| span basis | relative-volume readings | spread |
|---|---|---|
| per cluster (first→last touch) | 0.61× – 1.18× | 0.57 |
| **per touch** (one localised span per visit) | **0.48× – 2.44×** | **1.96** |

Per-touch is **3.4× more discriminating**. So a congestion is local to a visit,
and a level's strength is an **aggregate over its visits**.

`sr_volume.py` now encodes this: `MAX_CONGESTION_BARS = 30` makes a
cluster-wide call return `None` rather than a meaningless number — on the same
three symbols, 19 such calls are now refused while 123 per-touch readings
remain, spanning 0.48×–4.00×.

**`S4` must therefore call the primitives once per touch and aggregate.** How to
aggregate is now the open question `S4` inherits: sum of volume across visits
(E&M's "volume transacted there") or max of the per-visit readings (the
heaviest single visit). Sum is the closer reading of Ch 13; decide on `H-S1`.

A second distinction the measurement forced, now in the code: a scattered
*pivot spread* is refused, but a long contiguous *run* is **truncated, not
refused** — a wide sideways area is a strong level in E&M's terms, so declining
to measure it would discard exactly the information the slice is after.

### 3. Does the third-attack rule survive VN data? — **`S6` answers it**

`H-S3` is a study, not a tuning exercise. A negative result ships as a negative
result and the weighting is dropped.

### 4. Do round-figure levels ship? — **gated; `S8` may be dropped**

They carry zero volume strength by construction and three consumers rank by
strength, so they may be inert. `S8` measures first and is explicitly allowed
to end in "not shipped".

### 5. Unify the three S/R implementations first? — **no**

Log the debt (`FR-EM-S9`), ship on analysis-service, and let unification be its
own candidate once there is a demonstrably better level set worth unifying on.

---

## Track S — the level model (`analysis-service`)

### S0 — Roadmap rows
Per EM-1's `V0`. Feature Inventory row + Backlog #62 status + a Roadmap row
enumerating `S0`–`W2`. No code.

### S1 — Level volume primitives ⚠️ test-first
- **Satisfies:** `FR-EM-S1` groundwork, `FR-EM-S2`'s span question, `EC-S1`–`S3`.
- **Files:** NEW `analysis-service/app/services/sr_volume.py`; NEW tests.
- **Do:** `congestion_span()` (both candidate definitions from open question 2),
  `volume_weighted_price()`, `relative_level_volume()` — all **causal**: they
  read only bars at or before the level's own last pivot.
- **Tests FIRST:** `H-S4` causality (append future bars, assert no past level
  moves), `EC-S1` NULL/zero volume falls back and marks
  `volume_unavailable`, `EC-S2` thin ticker, `H-S6` determinism.
- **Reuse, do not reinvent:** EM-1's `patterns/volume.py` already solved the
  relative-volume problem (causal trailing median, `MIN_BASELINE_BARS`,
  `_usable`). Different service, so it cannot be imported — but the shape,
  the edge-case handling and the naming SHOULD be mirrored deliberately, and
  the divergence noted. Do not invent a second vocabulary for the same idea.
- **Done when:** green, and nothing in `_find_sr_levels` has changed yet.

### S2 — The `H-S1` three-arm harness, and the BEFORE numbers ⚠️ **before any model change**
- **Satisfies:** `H-S1`, and the `C4` benchmark of SRS §1.4.
- **Files:** NEW `analysis-service/tests/sr_hitrate_harness.py` (test-support,
  not shipped) + a committed baseline JSON.
- **Do:** for each level, causally measure whether price reversed within a
  stated proximity and horizon — scanning only bars up to the test date, the
  `C1` discipline `#79` followed. Three arms: **shipped touch-count levels**,
  **EM-2 levels** (stubbed for now), **random-level null** at matched distance
  from spot.
- **Capture and commit the shipped arm's numbers now.** This is the lesson EM-1
  paid for twice: without a before-measurement taken *before* the model
  changes, the C4 claim is unfalsifiable. EM-1's
  `em1_null_fpr_geometry_only.json` is the precedent, including its guard that
  refuses to regenerate once the code has moved on.
- **Done when:** the harness runs, the shipped and null arms have committed
  numbers, and the EM-2 arm is a failing `xfail(strict=True)` awaiting `S4`.

#### ⚠️ CORRECTED AT `S4` — read the `S4` section below before using any number here

The conclusion in this `S2` section is **wrong**, and the reason is sample
size. At the committed 12-symbol configuration the random null appeared to
match the shipped levels; at 32 symbols and step 5 — 5.4× the sample — the
shipped touch-count levels beat the null by **+1.10 pp at z = +2.35, which is
significant**. The "shipped levels add nothing" reading below was a power
artifact. The numbers in the table are reproducible at their own
configuration, so they stand as the committed regression baseline; the
*interpretation* does not.

#### MEASURED AT `S2` — the bar is not where the plan assumed

The before-numbers are in `tests/baselines/em2_hitrate_touchcount.json`, and
they change what `S4` has to clear:

| arm | real VN bars, 12 symbols | synthetic random walks |
|---|---|---|
| shipped touch-count levels | **54.6 %** | 46.8 % |
| matched-distance random null | **55.4 %** | 48.7 % |

*(4,180 and 4,265 resolved approaches respectively; a proportion near 0.5 at
that sample has a standard error of ±0.77 pp.)*

**The shipped touch-count levels do not beat a random price at matched
distance from spot.** The null's point estimate is in fact 0.8 pp *higher*,
which is inside noise — the honest statement is that the two are
indistinguishable, not that the null is better. Either way the shipped
level-selection adds nothing measurable over "a price this far from spot".

Three consequences, none of them optional:

1. **"Better than the shipped arm" is not evidence of anything.** `H-S1`
   already demanded EM-2 beat both arms; this says why that clause was load
   bearing. If the acceptance test had been written against the shipped arm
   alone, EM-2 could clear it by accident.
2. **Both real-data arms sit ~6 pp above both synthetic arms** (≈55 % vs ≈48 %).
   So real VN prices *do* mean-revert at these levels and horizons more than a
   random walk does — there is structure in the data; the touch-count model
   simply is not the thing that locates it. That is an encouraging result for
   EM-2 rather than a discouraging one.
3. **`S4`'s SUM-vs-MAX question** (inherited from `S1`'s per-touch finding) now
   has an evidence vehicle: run `H-S1` with each aggregation and let the hit
   rate decide, as the plan requires — on evidence, not preference.

A harness defect found and fixed in the same task, recorded because it would
have invalidated everything above: the first outcome rule counted an approach
whenever a bar's *high* reached the level, with the close anywhere below it.
That left the reversal threshold up to **19×** closer than the penetration
threshold, and every arm read in the 70s. The fix requires the *close* to sit
within the proximity band, and the null arm is what exposed it — a structureless
series must score a coin flip, and 73 % is not one. `test_the_rule_is_not_biased_towards_hits`
now pins that property.

### S3 — The `H-S2` volume-shuffle harness ⚠️ test-first ∥ (with S2)
- **Satisfies:** `H-S2`.
- **Do:** permute `volume` against price; assert `volume_strength` changes
  measurably while the shipped arithmetic-mean `price` is **bit-identical**.
- **Why it matters here:** it is the cheapest proof that the new strength reads
  the price–volume relationship rather than volume's level. EM-1's `H1`
  equivalent caught two real fixture defects.
- **Warning from EM-1:** a fixture whose volume column is constant is invariant
  under permutation, so this harness is satisfiable by a decorative
  implementation unless the fixtures carry **scripted** volume. Build them that
  way from the start.
- **Done when:** red for the right reason (no `volume_strength` yet), wired in.

### S4 — `volume_strength` + the centre of gravity ⚠️ test-first
- **Satisfies:** `FR-EM-S1`, `FR-EM-S2`, `NFR-S2`.
- **Files:** `analysis_service.py` `_find_sr_levels`; `schemas.py` `SRLevel`.
- **Do:** add `volume_strength: Optional[float]` and
  `price_cog: Optional[float]` (the volume-weighted close), both `Optional` and
  defaulted so the change is additive. `price` is **unchanged** in this task —
  moving the level price is a separate, larger behaviour change, and `S4` is
  already the task that flips `S2`'s and `S3`'s harnesses green.
- **Naming is a requirement, not a preference:** `NFR-S2` forbids "volume at
  price" anywhere. `price_cog` with a docstring saying it is a volume-weighted
  *close*, and why that is the honest substitute for daily bars.
- **Done when:** `S2`'s EM-2 arm and `S3` both go green, the `xfail` markers
  come off, and the existing analysis-service suite is unchanged.
- **Decide here:** whether `price` itself should later become `price_cog`
  (a `W1` sweep question), and record it.

#### MEASURED AT `S4` — the fields work; the claim they were built for does not

Both fields are implemented, causal, shuffle-responsive and tested (27 tests).
`S3` went green: `volume_strength` moves when volume is permuted while level
prices stay bit-identical, so the measure demonstrably reads the price-volume
relationship. **`H-S1` is a different question, and the answer is no.**

Run at two sample sizes, because the first answer looked too good:

| arm | 12 symbols, step 10 | **32 symbols, step 5** |
|---|---|---|
| `touch_count` (shipped) | 54.59 % | **55.46 %** |
| `touch_count_matched` (same selectivity) | 54.05 % | **55.74 %** |
| `em2_volume`, SUM + `price_cog` | 56.31 % | **54.90 %** |
| `em2_volume`, SUM + `price` | 54.40 % | **55.66 %** |
| `em2_volume`, MAX + `price_cog` | 54.99 % | **55.16 %** |
| `random_null` | 55.43 % | **54.36 %** |
| resolved approaches (shipped arm) | 4,180 | **22,470** |

| comparison | 12 symbols | 32 symbols |
|---|---|---|
| shipped vs null | −0.84 pp, z = −0.78 | **+1.10 pp, z = +2.35 → significant** |
| matched vs null | −1.38 pp, z = −1.08 | **+1.38 pp, z = +2.51 → significant** |
| EM-2 vs null | +0.88 pp, z = +0.70 | +0.54 pp, z = +0.97 |
| EM-2 vs matched | +2.26 pp, z = +1.57 | **−0.84 pp, z = −1.34** |

**Two findings, and the first one corrects `S2`.**

1. **The shipped touch-count levels do carry real information** — +1.10 pp over
   a matched-distance random null at z = +2.35. `S2` concluded the opposite,
   and `S2` was underpowered. The ⚠️ note above now flags that.
2. **The volume measures do not improve on them.** At the larger sample EM-2's
   best configuration sits *below* the matched-selectivity control. Decomposed:
   `volume_strength` as a **selector** is a wash against touch count (55.66 vs
   55.74), and `price_cog` as a **location** is slightly *worse* than `price`
   (54.90 vs 55.66). Nothing is significant in either direction.

So the `H-S1` xfail **stays red**, with the measurement in its reason. `C4`
admits an improvement only on significance, and there is none — this is the
`S6`-style negative result arriving early, and it is not a reason to tune.

**Decisions this settles:**

- **`price` must NOT become `price_cog`.** The plan listed that as a `W1`
  question and the SRS's "not in this plan" list flagged it as the larger
  behaviour change. The evidence now says it would make the level *worse*. It
  is off the table unless a later task produces contrary evidence, and `D1`
  should not spend a session evaluating it.
- **`SUM` is the default aggregation**, on evidence rather than preference
  (55.66 vs 54.90 at the larger sample with `price_cog`; the ordering is
  consistent but not significant, and SUM is also the closer reading of Ch 13).
  The open question `S4` inherited from `S1` is answered.
- **A matched-selectivity arm is mandatory** in any further comparison. EM-2
  scores a subset, and against the *full* shipped arm it would have looked
  better than it is — the plan's `W1` warning ("an improvement that comes from
  doing less is not an improvement") in its general form.
- **12 symbols at step 10 is too small for comparisons.** It is retained as the
  committed regression baseline, which is what the guard protects, but any
  comparative claim SHALL be run at 32 symbols / step 5 (≈3 min). `W1` should
  set the standard sample.

**What `S5`–`S7` now have to do.** They are no longer refinements to a measure
that is already winning; they are the remaining chances for EM-2 to beat a
benchmark that has turned out to be stronger than it looked. If role reversal,
attack count and decay also fail to clear it, the honest outcome for this
workstream is a documented negative result — E&M's Ch 13 claim not reproducing
on VN daily bars — and `S9`'s consumer switch should not ship.

### S5 — Role reversal and break history
- **Satisfies:** `FR-EM-S3`, `EC-S4`.
- **Do:** `breaks: List[SRBreak]` (direction, bar index, date, penetration
  size); the most recent penetration decides the current type. `FLIP` stays
  what it is — a pivot-composition tie — and the payload must let a consumer
  tell a reversed level from a flip level apart.
- **The penetration test:** in units comparable across symbols, per EM-9's
  finding that one percentage is wrong across kinds (median 0.56%–4.47%). ATR
  multiple or a percentile of the symbol's own move distribution; swept at `W1`.
- **Tests:** a level broken then re-approached from the other side reverses; a
  level broken twice in opposite directions resolves by recency (`EC-S4`).

#### MEASURED AT `S5` — the first EM-2 measure to beat the null

Break history, role alternation and `effective_type` are implemented, causal
and tested (21 tests). Measured at 32 symbols / step 5, as `S4` made mandatory:

| arm | hit rate | vs null | vs shipped |
|---|---|---|---|
| `random_null` | 54.36 % | — | — |
| `touch_count` (shipped) | 55.46 % | **+1.10 pp, z = +2.35** | — |
| `touch_count_matched` | 55.74 % | +1.38 pp, z = +2.51 | — |
| `em2_volume` (S4) | 54.90 % | +0.54 pp, z = +0.97 | −0.56 pp |
| **`em2_role` (S5)** | **55.86 %** | **+1.50 pp, z = +3.16** | +0.40 pp, z = +0.84 |

**`em2_role` is the first EM-2 measure to beat the random null with
significance.** It is also the first evidence in this workstream that an E&M
idea reproduces on VN daily bars at all.

It still does **not** clear `H-S1`, which requires beating *both* arms. Against
the shipped touch-count levels it is +0.40 pp at z = +0.84 — not significant.
And since the incumbent itself beats the null significantly, clearing the null
is no longer the hard half of the test. The xfail stays red, with both
measurements in its reason.

**The arm, and why it is kept separate.** `em2_role` keeps levels whose break
history *agrees with where they sit*: a level above spot must be acting as
resistance, one below must be acting as support. An unbroken support below
spot qualifies; so does a support broken downward that now sits above spot
acting as resistance — E&M's Ch 13 mechanic exactly. What it drops is the
incoherent case. It is a light filter, discarding ~5 % of observations. It is
reported **separately** from `em2_volume` so that a difference can be
attributed to `FR-EM-S3` or to `FR-EM-S1`, never to an unidentifiable mixture.

**A design flaw the tests caught.** The first implementation recorded a
penetration in either direction, which reported a *support* as "broken upward"
on every ordinary rally — price being above a support is where price lives,
not a break. Meaningless entries, and enough of them to swamp the real ones.
The fix is role **alternation**: a penetration counts only against the level's
current role, and the role flips when it happens. That is both the correct
reading of Ch 13 and what makes `EC-S4`'s "both directions" coherent — a
support can only be broken upward *after* it has become resistance. A
quiet-fixture test (one whose routine swing stays inside the ATR band)
surfaced it.

**Deliberate deviation from this plan's wording.** The plan said "the most
recent penetration decides the current type". `type` is left alone and the
answer surfaces as `effective_type` + `role_reversed` alongside it, because
`type` decides which of the supports/resistances lists a level lands in and
three live consumers read those lists. Switching them on a model that has not
yet cleared `H-S1` is the mistake this plan keeps avoiding; `S9`/`D1` can make
the switch with evidence. `FR-EM-S3`'s own requirement — that a reversed level
be distinguishable from a `FLIP` — needs the extra field either way.

**A performance regression, found and fixed.** Scoring breaks per level turned
the study from 3 s into 32 s, over `pytest.ini`'s own 30 s timeout. Two causes:
ATR recomputed per level when it is a property of the frame, and a per-bar
Python loop where a vectorised candidate search does. Both fixed (21 s), and
the study classes now carry an explicit `timeout(600)` because a study is not
a unit test and should not be governed by a unit test's budget.

### S6 — Attack count, and the third-attack study
- **Satisfies:** `FR-EM-S4`, `H-S3`.
- **Do:** `attacks: int` — approaches within proximity that reversed without
  breaking. Strength **decreases** with attack count.
- **Two things that must be tested, not assumed:**
  - **The direction.** This is the second non-monotone rule in the workstream
    after `FR-EM-V4`: more contact makes a level *weaker*, the opposite of the
    touch-count model being replaced. A dedicated test asserts more attacks
    score lower — the rule most likely to be "simplified" into wrongness.
  - **The prediction.** `H-S3` measures first/second/third-attack penetration
    rates on VN data against a coin flip. **If the third attack is not
    odds-on, the weighting does not ship** and the count stays as evidence.
    Report the number either way.

#### MEASURED AT `S6` — E&M's third-attack rule does NOT hold, and the weighting does not ship

`attacks` is implemented, causal and tested (17 tests). `H-S3` then measured
E&M's prediction on 43,316 levels and ~262,000 approaches of real VN daily bars
(`tests/sr_attack_study.py`):

| approach | n | penetrated | rate | vs 50% |
|---|---|---|---|---|
| 1st | 38,852 | 10,250 | **26.4 %** | z = −93.1 |
| 2nd | 33,205 | 13,347 | **40.2 %** | z = −35.7 |
| 3rd | 29,045 | 12,272 | **42.3 %** | z = −26.4 |
| 4th or later | 161,672 | 63,930 | **39.5 %** | z = −84.1 |

E&M: *"it is an odds-on assumption that a third attack at a Resistance Level
will succeed in penetrating it."* Odds-on means above 50 %. **The third attack
penetrates 42.3 % of the time — significantly *below* a coin flip.** The claim
as stated does not reproduce.

**So the weighting does not ship.** `FR-EM-S4` and this plan both
pre-registered that consequence, and it is honoured: `attacks` is carried as
evidence on the payload, nothing reads it, and `strength` and `volume_strength`
are provably unadjusted by it (three tests pin that).

**The tempting mistake, named so it is not made later.** The first three
ordinals are strongly monotone — 26.4 % → 40.2 % → 42.3 % — which looks like
support for E&M's *reasoning* ("each repelled attack consumes some of a level's
power") even as it refutes their *number*. It would be easy to decide after the
fact that the direction was the real claim and ship a weighting on that basis.
That is choosing the criterion after seeing the data, which is exactly what the
pre-registration existed to prevent. If the directional effect is worth
exploiting it needs its own candidate, its own pre-registered criterion and its
own out-of-sample test — not a reinterpretation of this one.

**A confound that must travel with these numbers.** The scan starts at the
level's first touch, so the pivots that *defined* the level sit inside the
scanned range — and a pivot is by construction a place price reversed. Early
approaches are therefore more likely to be the level's own defining touches,
which inflates the repulsion rate at low ordinals. The gradient above is, if
anything, **overstated**: removing the circularity would raise the penetration
rate at ordinals 1–2 and flatten it. The headline verdict is robust to this,
since the confound pushes the early ordinals down rather than pushing the third
one up, and the third would have to climb from 42.3 % to above 50 %. A clean
version would scan only after the last defining touch, which usually leaves no
third attack inside a 250-bar window — that limitation is why it was not done
here, and it should be stated wherever these numbers are quoted.

### S7 — Age decay and distance-away
- **Satisfies:** `FR-EM-S5`, `FR-EM-S6`.
- **Do:** decay with a **floor** — E&M are explicit that an old level "does not
  lose all of its potency", so decay-to-zero misreads the book. First consumer
  of the `age_bars` that `_find_sr_levels` has always computed and never used.
  Distance-away suppresses rather than drops.
- **Both thresholds swept at `W1`**, not trusted. The 10% is a 1950s NYSE
  figure.

#### MEASURED AT `S7` — parity with touch count, and Track S's verdict

Age decay (with the floor `FR-EM-S5` makes binding) and distance-away
suppression are implemented, causal and tested (25 tests). `age_bars` — computed
by `_find_sr_levels` since the field existed and never read — finally has a
consumer.

At 32 symbols / step 5:

| arm | hit rate | vs null | vs shipped | vs matched |
|---|---|---|---|---|
| `random_null` | 54.36 % | — | — | — |
| `touch_count` (shipped) | 55.46 % | +1.10 pp, z = +2.35 | — | — |
| `touch_count_matched` | 55.74 % | +1.38 pp, z = +2.51 | — | — |
| `em2_volume` (S4) | 54.90 % | +0.54 pp, z = +0.97 | −0.56 pp | — |
| `em2_role` (S5) | **55.86 %** | +1.50 pp, z = +3.16 | +0.40 pp, z = +0.84 | — |
| **`em2_adjusted` (S7)** | **55.84 %** | +1.48 pp, z = +2.66 | +0.38 pp, z = +0.68 | **+0.10 pp, z = +0.16** |

**S7 works, within EM-2.** It lifts the volume arm from 54.90 % to 55.84 %
(+0.94 pp, z = +1.49) on essentially the same number of observations — 12,322
against 12,405 — so the adjustment changed *which* levels rank top-half, not
how many. That is age and distance doing real work on EM-2's internal ranking,
and it is enough to carry the volume arm past the null significantly, which on
its own it never managed.

**S7 does not work against the incumbent.** The number that matters is the last
column: at matched selectivity, `em2_adjusted` and plain touch count differ by
**+0.10 pp at z = +0.16**. That is parity, not improvement. The whole EM-2
apparatus — volume-weighted strength, a centre of gravity, role reversal, age
decay, distance suppression — lands on the same accuracy as counting touches.

**Track S is now complete bar the gated `S8`, so this is the decision point the
plan pre-registered.** Recorded plainly:

* Three of E&M's Ch 13 criteria reproduce *directionally* — role coherence,
  age, distance — and one of their quantitative claims does not (the
  third-attack rule, `S6`, refuted at z = −26.4).
* Every EM-2 arm beats a matched-distance random null significantly, which
  says the levels are real.
* **No EM-2 arm beats the shipped touch-count model significantly**, which says
  the replacement is not justified.

So on the evidence, **`S9`'s consumer switch should not ship.** Three live
consumers read `strength`, and swapping them onto a measure that is at best at
parity would spend behaviour-change risk for no measured return. The fields
stay on the payload as evidence and as the basis for any future candidate; the
consumers keep reading touch count.

`S8` (round figures) was always gated and may be dropped; `D1`'s before/after
has nothing to compare if no consumer changes. The useful remaining work is
`W1`'s sweep — every threshold in EM-2 is still a default, and the plan requires
them swept — and that sweep is now the thing that could overturn this verdict,
since a badly-chosen `MAX_CONGESTION_BARS`, `BREAK_ATR_MULTIPLE`,
`AGE_HALFLIFE_BARS` or `DISTANCE_AWAY_PCT` would understate EM-2 across the
board.

**A limitation that bounds the age result specifically.** E&M's age claim is
about *years* — one-to-two versus four-to-five — and a 250-bar window spans
about one. `age_bars` can therefore only range over a fraction of the span the
book is describing, so the decay measured here is a weak version of the effect
E&M assert, not a test of it. Testing their actual claim needs multi-year
windows, which is its own slice.

### S8 — Round-figure levels ⚠️ may end in "not shipped"
- **Satisfies:** `FR-EM-S7`, open question 4.
- **Do:** measure whether a round-figure level ever outranks a congestion level
  given it carries zero volume strength by construction. If it cannot, say so
  and drop the task. An inert feature with a code path is worse than a
  documented decision not to build it.

### S9 — Schema surface + the consumer update
- **Satisfies:** `FR-EM-S8`.
- **Files:** `schemas.py`, the `/analysis/sr/{symbol}` route, and
  `decision-helper/signal/range/sr_bounce_breakout.py`.
- **Do:** surface the new fields (all `Optional`, additive); update
  `sr_bounce_breakout` to prefer `volume_strength` over `strength`, with the
  `int()`-truncation trap from open question 1 called out in a comment so
  nobody reintroduces it.
- **Tests:** a response-shape test pinning every pre-EM-2 field by name — the
  EM-1 `V7` precedent; and the bounce-confidence formula tested on both the new
  and the fallback path.

---

## Track D — downstream

### D1 — `H-S5` before/after on the three live consumers
- **Satisfies:** `H-S5`.
- **Do:** a **read-only** comparison of CHART stop prices, SR_LEVEL targets and
  bounce/breakout confidence on a fixed symbol set, before vs after. Report it;
  change nothing in those modules beyond `S9`'s deliberate update.
- **Why it is a task:** `S9` changes a number a live consumer reads. EM-1's
  `S1` is the precedent, and its finding — that the change provably did not
  reach the consumer — was only available because somebody measured instead of
  assuming.
- **Note the asymmetry from the SRS:** this reaches the live stop, target and
  bounce signals, and reaches **neither** trap detection **nor** the backtest.
  Do not claim otherwise.

---

## Track W — sweep and documentation

### W1 — `FR-EM-S10` sweep
- Sweep the congestion span, the penetration test, attack proximity, decay
  half-life and floor, and the distance-away threshold, under `H-S1`/`H-S2`.
  Record each choice **with its evidence**, as `docs/em2_s_sweep.md`.
- **Two traps already paid for in this workstream, do not pay again:**
  (a) a parameter read as a **default argument** is bound at definition time, so
  patching the module constant does nothing and the sweep comes back perfectly
  flat — this happened twice (EM-1 `S2`'s `confirm_rvol`, `#78`'s
  `MAX_PATTERN_AGE_BARS`). A flat sweep is a harness smell. (b) An improvement
  in a total that comes from *doing less* is not an improvement — EM-9's net
  P&L rose 37% purely on 35% fewer trades.

### W2 — User guide
- Bilingual VI/EN section in
  `docs/USER_GUIDE_chart_decomp_and_decision_tools.md`, matching that file's
  convention, explaining what a volume-weighted level means to a trader and
  that level strength no longer counts touches.

---

## Dependency graph

```
S0 → S1 → ┬→ S2 ┐
          └→ S3 ┴→ S4 → S5 → S6 → S7 → S8? → S9 → D1
                                                 └→ W1 ∥ W2
```

`S2` and `S3` are parallel and **both precede `S4`** — the harnesses exist, and
`S2`'s shipped-arm numbers are committed, *before* anything changes the model.
That ordering is the whole point: without it there is no before-measurement and
the `C4` claim cannot be falsified.

## Mandatory-harness checklist

| harness | SRS | introduced in | guards |
|---|---|---|---|
| `H-S1` three-arm forward hit-rate | §5 | `S2` | `S4`–`S7`, the C4 claim |
| `H-S2` volume shuffle | §5 | `S3` | `S4` |
| `H-S3` third-attack vs coin flip | §5 | `S6` | the rule's right to exist |
| `H-S4` causality (C1) | §5 | `S1` | forbids whole-series normalisation |
| `H-S5` downstream before/after | §5 | `D1` | the live consumers |
| `H-S6` determinism / thin data | §5 | `S1` | `EC-S1`–`S3` |

All assert **properties**. None asserts a magnitude from the book — E&M's 10%,
the third-attack claim and the one-to-two-year decay are defaults to be swept
or predictions to be tested, never expected values.

## Suggested execution order

`S0 → S1 → S2 → S3 → S4 → S5 → S6 → S7 → S8? → S9 → D1 → W1 → W2`

with `S2 ∥ S3` combinable in one session if the diff stays small, and `S8`
allowed to end as a documented non-decision.

**First session is `S0 + S1`** — bookkeeping plus the primitives and their
causality and thin-data tests, which puts the `C1` guard in place before
anything can violate it. Exactly how EM-1 started, for the same reason.

## Explicitly not in this plan

- **Moving `price` to the volume-weighted centre of gravity.** `S4` adds
  `price_cog` alongside; actually replacing `price` moves the number three live
  consumers trade off, and needs `D1`'s evidence first.
- **Unifying the three S/R implementations** (open question 5) — logged as debt.
- **`chart-decomp-lib`'s level code** — deferred as EM-2b.
- **Any database change.** The levels are computed per request from OHLCV
  already in hand; nothing is persisted.
