# Software Requirements Specification — Volume-Weighted Support & Resistance

**Candidate:** EM-2 (Backlog #62) · **Phase:** 1 (design) · **Date:** 2026-10-14
**Source:** Edwards & Magee, *Technical Analysis of Stock Trends* (9th ed.), Ch 13 and Ch 30.
**Requirement prefix:** `FR-EM-S*` — distinct from EM-1's `FR-EM-V*`, which this
document builds on but does not modify.

Phase 2 (the task plan) and Phase 3 (implementation) are separate sessions, per
`CLAUDE.md`'s one-phase-per-session rule. Nothing here is implemented yet.

---

## 1. Purpose

### 1.1 The problem

`analysis_service.py:203` `_find_sr_levels` clusters swing pivots within 2% and
sets `strength = len(cluster)` — **a touch count**. Verified by reading it, not
assumed.

E&M spend an entire chapter arguing that this is the wrong measure. Ch 13's
claim is that a level's power comes from **the volume that changed hands there**
— the supply trapped above a buyer's cost — and not from how often price has
since visited. A level touched five times on thin trade is weaker, in their
account, than one touched twice on heavy trade.

The level set is also missing everything Ch 13 says modulates that power: role
reversal after penetration, decay with age, and the consumption of a level by
repeated attack.

### 1.2 Scope — in

- Volume as the basis of level strength (`FR-EM-S1`).
- The level price as a volume-weighted centre of gravity (`FR-EM-S2`).
- Role reversal on penetration (`FR-EM-S3`).
- Attack count and the third-attack rule (`FR-EM-S4`).
- Age decay (`FR-EM-S5`).
- Distance-away suppression (`FR-EM-S6`).
- Round-figure levels (`FR-EM-S7`).
- Surfacing all of it without breaking the three live consumers (`FR-EM-S8`).

### 1.3 Scope — out, with reasons

- **True volume-at-price.** Requires intraday or tick data. The repo has daily
  OHLCV only. `FR-EM-S2` therefore defines an explicit approximation and
  `NFR-S2` requires it be labelled as one everywhere it surfaces.
- **Unifying the three S/R implementations.** See §2.2 — it is a real problem,
  but it is a refactor with its own blast radius and belongs in its own slice.
- **`chart-decomp-lib`'s swing/level code.** Separate package, bare-series
  interface. Deferred as EM-2b, exactly as EM-1 deferred EM-1b.

### 1.4 What this is measured against (C4)

`CLAUDE.md` requires a benchmark, and for this candidate it is unusually
important because the claim is comparative — E&M say volume beats touch count.

> A volume-weighted level earns its place only if price reverses at it
> **measurably more often** than at the current touch-count level, out of
> sample, and more often than at a random level of the same distance from
> spot.

Three arms, not two: the shipped implementation, the new one, and a random-level
null. §6 turns this into harnesses.

---

## 2. Current state, verified

### 2.1 What `_find_sr_levels` does today

| aspect | today |
|---|---|
| level price | arithmetic mean of clustered pivot prices |
| strength | `len(cluster)` — touch count |
| typing | whichever of highs/lows dominates; `FLIP` on a tie |
| age | `age_bars` computed, but **never used** to weight anything |
| volume | absent entirely |
| break history | absent |
| attack count | absent |

The `ohlc` frame passed in **already carries `volume`**, and every cluster
retains its pivots' `bar_index`. So EM-2 needs **no new data source** — the
volume at each pivot bar is already in hand. That is the single most important
feasibility fact in this document.

### 2.2 The register's leverage claim is overstated — corrected here

The register says *"four shipped consumers read that level set — one improvement
propagates to all four."* Measured:

| consumer | reads analysis-service levels? | uses `strength`? |
|---|---|---|
| `decision-helper/risk/stop_module.py` | **yes** (live, via `fetch_sr_levels`) | only in a reason string |
| `decision-helper/risk/target_module.py` | **yes** (live) | only in a reason string |
| `decision-helper/signal/range/sr_bounce_breakout.py` | **yes** (live) | **yes** — `conf = 0.4 + strength*0.05 + …` |
| `ai-insights/patterns/trap.py` | **no** — builds its own `_build_sr_levels` | no |

So it is **three** live consumers, not four, and only **one** currently lets
`strength` change a number. There are in fact **three independent S/R
implementations** in the repo:

1. `analysis-service::_find_sr_levels` — clustered pivots, touch-count strength
2. `ai-insights::trap.py::_build_sr_levels` — its own clusters, no strength
3. `decision-helper::backtest/market_features.py::compute_sr_levels` — raw
   pivots with `strength` hardcoded to `1`

**Consequences that shape this slice.** (a) Improving (1) does nothing for trap
detection or for the backtest harness, so EM-2 must not claim it does. (b) The
backtest cannot be EM-2's benchmark even setting aside Backlog #80, because it
does not consume the levels under test. The C4 benchmark must therefore be a
direct forward hit-rate study — which is what §1.4 specifies. (c) Divergence
between the three will widen as EM-2 improves one of them; `FR-EM-S9` records
that debt rather than silently accepting it.

---

## 3. The level model

### FR-EM-S1 — Strength is volume, not touch count

A level's `strength` SHALL be derived from the **volume transacted at the
level**, specifically the sum of volume on the bars forming its congestion, and
SHALL NOT be the count of touches.

- It SHALL be expressed **relative to the symbol's own recent volume**, never as
  an absolute share count — the same reasoning as `FR-EM-V1`: *"high" means high
  for that stock in that period* (Ch 6).
- Touch count SHALL remain on the payload as a separate field. It is what three
  consumers and the UI read today, and `FR-EM-S8` forbids breaking them.

### FR-EM-S2 — The level price is a volume-weighted centre of gravity

E&M: the precise level is the **volume-weighted average of the old congestion's
closes**.

- The level price SHALL be `Σ(close_i × volume_i) / Σ(volume_i)` over the bars
  of the congestion, replacing the arithmetic mean of pivot prices.
- **This is an approximation and SHALL be documented as one** (`NFR-S2`). E&M
  assumed a volume-at-price distribution that daily bars cannot supply; a
  volume-weighted *close* is the closest honest substitute. Calling it "volume
  at price" in code, docs or UI is forbidden.
- The congestion's bar span SHALL be defined explicitly (the pivot bars plus a
  stated neighbourhood), not left implicit.

### FR-EM-S3 — Role reversal

Ch 13: *"a former Top, once surpassed, becomes a Bottom zone; an old Bottom,
once penetrated, becomes a Top zone."*

- A level SHALL carry its **break history**: whether price has closed decisively
  through it, in which direction, and when.
- A penetrated level SHALL have its type reversed, not discarded. The existing
  `FLIP` type is a tie-break on pivot composition and is **not** the same
  concept; `FR-EM-S8` requires the two be distinguishable on the payload.
- "Decisively" SHALL reuse EM-9's finding rather than inventing a number: EM-9
  measured that a single percentage threshold is wrong across signal kinds
  (median penetration spans 0.56%–4.47%), so the penetration test here SHALL be
  expressed in units comparable across symbols — an ATR multiple or a percentile
  of that symbol's own move distribution — and swept (`FR-EM-S10`).

### FR-EM-S4 — Attack count and the third attack

Ch 13: each repelled attack consumes some of a level's power, and *"it is an
odds-on assumption that a third attack at a Resistance Level will succeed in
penetrating it."*

- A level SHALL carry `attacks` — the number of approaches that came within a
  stated proximity and then reversed without breaking.
- Strength SHALL **decrease** with attack count. This is the second
  non-monotone rule in the E&M workstream, after `FR-EM-V4`: more contact makes
  a level *weaker*, which is the opposite of the touch-count model it replaces,
  and a test SHALL assert the direction explicitly.
- The third-attack claim is a **falsifiable prediction**, not a parameter, and
  §6 `H-S3` measures it against a coin flip. If VN data does not support it, the
  rule SHALL be reported as unsupported and not shipped as a weighting.

### FR-EM-S5 — Age decay

Ch 13: a one-to-two-year-old level beats a four-to-five-year-old one, *"but the
latter does not lose all of its potency by any means."*

- Strength SHALL decay with age, and the decay SHALL have a **floor** — the
  quoted caveat is explicit that an old level retains power, so decay to zero
  would misread the book.
- `age_bars` already exists and is computed but unused; this requirement is the
  first consumer of it.

### FR-EM-S6 — Distance-away suppression

Ch 13: expect little real supply from an old bottom unless price later fell
**more than 10%** under it.

- A level whose price sits within a stated distance of spot without the
  intervening excursion SHALL be suppressed rather than dropped.
- The 10% is E&M's figure for 1950s NYSE issues and SHALL be swept, not trusted
  (`FR-EM-S10`).

### FR-EM-S7 — Round-figure levels

Ch 13: round figures (20, 30, 50, 100) create levels *"with no vested interest
behind them"*, especially in new high ground.

- A round-figure level SHALL be emitted where no pivot congestion exists, and
  SHALL be marked as round-figure so a consumer can weight it differently.
- It SHALL carry **zero volume strength** by construction — that is the point of
  the quote — and SHALL therefore never outrank a genuine congestion level.

### FR-EM-S8 — The payload stays backward compatible

Three live consumers read these levels.

- `price`, `type`, `strength`, `age_bars` and `touches` SHALL keep their names
  and types. New fields SHALL be `Optional` with defaults.
- **`strength` changes meaning**, which is a behaviour change with a live
  consumer: `sr_bounce_breakout.py` computes `conf = 0.4 + strength*0.05 + …`,
  so a strength that is no longer a small integer count would distort signal
  confidence. The SRS therefore requires **either** that `strength` keep a
  count-like scale and the volume measure arrive as a new field, **or** that
  `sr_bounce_breakout` be updated in the same slice. Phase 2 SHALL choose, and
  the choice SHALL be stated in the plan — this is open question 1.
- A before/after comparison of the three live consumers is mandatory
  (`H-S5`), for the same reason EM-1's `S1` existed.

### FR-EM-S9 — Record the divergence, do not hide it

The slice SHALL log the three-implementation divergence (§2.2) as explicit tech
debt with the consequence spelled out: a level improvement reaches the live
stop, target and bounce/breakout signals, and reaches neither trap detection nor
the backtest.

### FR-EM-S10 — Every number is swept

Per `FR-EM-V11`'s precedent and `CLAUDE.md`: the congestion neighbourhood, the
penetration test, the attack proximity, the decay half-life and floor, and the
distance-away threshold are **defaults pending a sweep**, never trusted
constants. E&M's figures are 1940s–60s NYSE rules.

---

## 4. Edge cases

| ID | case | required behaviour |
|---|---|---|
| `EC-S1` | `volume` NULL or 0 on congestion bars | fall back to touch count for that level and mark it `volume_unavailable`; never treat 0 as "no interest" |
| `EC-S2` | a thin ticker where all volume is lumpy | the `FR-EM-V1` precedent: relative measures only, and a `thin_volume` marker |
| `EC-S3` | fewer bars than the congestion neighbourhood | emit the level with the bars available, above a stated minimum |
| `EC-S4` | a level penetrated more than once in both directions | break history is a list, not a flag; the most recent penetration decides the current type |
| `EC-S5` | corporate action inside the window | prices are restated and volume rescaled; the level is a *price* so a split invalidates it — Backlog #60 applies, and the slice SHALL document rather than silently handle it |
| `EC-S6` | spot exactly at a level | the existing support/resistance split is by side of spot; ties SHALL be deterministic |

---

## 5. Validation requirements (all mandatory)

Per `CLAUDE.md`, each harness ships **with** the code it validates.

### H-S1 — Forward hit-rate, three arms · MANDATORY

The C4 benchmark of §1.4. For each level, measure whether price reversed within
a stated proximity and horizon, causally — scanning only bars up to the test
date, the `C1` discipline that EM-1's `#79` study followed.

Three arms: shipped touch-count levels, EM-2 volume-weighted levels, and a
**random-level null** at matched distance from spot. A method improves only if
it beats *both*.

### H-S2 — Volume-shuffle · MANDATORY

The `H1` precedent from EM-1, and the cheapest statement that the strength
measure reads what it claims. Permute `volume` against price and assert that
level **strength** changes measurably while level **prices** under the current
arithmetic mean stay identical.

### H-S3 — The third-attack rule as a falsifiable prediction · MANDATORY

Measure, on VN data, the penetration rate of a first, second and third attack.
E&M predict the third is odds-on. Report the rate against a coin flip. **A
negative result is a publishable outcome**, not a reason to tune until the rule
appears.

### H-S4 — Causality (C1) · MANDATORY

Level construction reads only bars at or before the level's own date. No
full-series normalisation of volume. The EM-1 no-leakage test shape: append
future bars, assert no past level moves.

### H-S5 — Downstream before/after · MANDATORY

The three live consumers — CHART stop, SR_LEVEL target, bounce/breakout
confidence — compared before and after on a fixed symbol set. `FR-EM-S8`'s
`strength` question makes this non-optional.

### H-S6 — Determinism and thin data

Identical input, identical output. `EC-S1`–`EC-S3` exercised.

---

## 6. Open questions for Phase 2

Recorded rather than guessed. None blocks the plan.

1. **Does `strength` change meaning in place, or does the volume measure arrive
   as a new field?** `FR-EM-S8`. In place is cleaner and breaks
   `sr_bounce_breakout`'s arithmetic; a new field is safe and leaves a
   misleading `strength` as the thing consumers read. Recommendation: new field
   `volume_strength`, plus updating `sr_bounce_breakout` in the same slice so
   nothing reads the weaker measure once the better one exists.
2. **How wide is a "congestion"?** `FR-EM-S2` needs a bar span. Candidates: the
   pivot bars only; pivot ± N; or the contiguous run where price stayed within
   the cluster tolerance. The third is closest to E&M's "congestion area" and
   costs the most to compute.
3. **Does the third-attack rule survive VN data?** `H-S3` answers it. If not,
   `FR-EM-S4` keeps the attack count as evidence and drops the weighting.
4. **Should the round-figure levels (`FR-EM-S7`) ship at all,** given they
   carry zero volume strength by construction and three consumers rank by
   strength? They may be inert in practice. Decide with a measurement.
5. **Is the right fix to §2.2 to unify the three implementations first?** That
   would make EM-2 reach trap detection and the backtest too. It is also a
   bigger, riskier slice. Recommendation: no — ship EM-2 on analysis-service,
   log the debt (`FR-EM-S9`), and let the unification be its own candidate once
   there is a demonstrably better level set worth unifying on.

---

## 7. Traceability

| requirement | E&M | lands in | harness |
|---|---|---|---|
| `FR-EM-S1` strength = volume | Ch 13 | `_find_sr_levels` | `H-S1`, `H-S2` |
| `FR-EM-S2` centre of gravity | Ch 13 | `_find_sr_levels` | `H-S1`, `H-S4` |
| `FR-EM-S3` role reversal | Ch 13 | `_find_sr_levels` + schema | `H-S1`, `EC-S4` |
| `FR-EM-S4` attack count | Ch 13 | `_find_sr_levels` + schema | **`H-S3`** |
| `FR-EM-S5` age decay | Ch 13 | `_find_sr_levels` | `H-S1` |
| `FR-EM-S6` distance-away | Ch 13 | `_find_sr_levels` | `H-S1` |
| `FR-EM-S7` round figures | Ch 13 | `_find_sr_levels` | open question 4 |
| `FR-EM-S8` compatibility | — | schema + `sr_bounce_breakout` | **`H-S5`** |
| `FR-EM-S9` divergence debt | — | ROADMAP | — |
| `FR-EM-S10` sweep everything | — | a sweep script | `H-S1` |
