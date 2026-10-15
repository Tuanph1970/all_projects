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

### S7 — Age decay and distance-away
- **Satisfies:** `FR-EM-S5`, `FR-EM-S6`.
- **Do:** decay with a **floor** — E&M are explicit that an old level "does not
  lose all of its potency", so decay-to-zero misreads the book. First consumer
  of the `age_bars` that `_find_sr_levels` has always computed and never used.
  Distance-away suppresses rather than drops.
- **Both thresholds swept at `W1`**, not trusted. The 10% is a 1950s NYSE
  figure.

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
