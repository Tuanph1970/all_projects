# Implementation plan — EM-6: Dow multi-index confirmation gate

**Phase:** 2 (plan)
**Date:** 2026-10-20
**Design:** `docs/SRS_edwards_magee_dow_gate.md` v1.0
**Backlog:** `#66`
**Prior measurement:** `decision-helper-service/tests/em6_witness_study.py`

One task per session. Each task writes its tests first, runs them, shows them
passing, and **stops**. Three tasks are **gates**: if the pre-registered
criterion fails, the work stops there and EM-6 is recorded as a measured
negative — the EM-2 ending, which is a legitimate outcome and the most likely
one here (SRS §9).

---

## 1. The SRS's ambiguity, resolved

`FR-EM-D4` and `FR-EM-D5` describe **two different mechanisms**, and v1.0 did
not say how they relate:

* **D4** confirms a **turn** — an event. *"A lead trend change at day t is
  confirmed if a witness holds the same state in `[t, t+k]`."*
* **D5** checks a **state** — at signal time, does the witness agree?

Implementing both independently would mean two gates with two meanings. They
compose instead, and E&M supply the joining rule — tenet 12, *a trend is
assumed to continue until reversal is definitely signalled*:

> **The witness governs how the market's primary trend is *adopted*; the gate
> then checks a signal against the adopted trend.**
>
> A lead turn at *t* is adopted only once a witness confirms it, at the day of
> confirmation, within `k` bars. If no witness confirms within `k`, **the turn
> is not adopted and the previous primary trend stands** — which is tenet 12
> exactly, not a special case invented for the code.

This is one mechanism, honours both tenets, and makes `k` meaningful in a way
the SRS's phrasing did not: `k` controls both the **lag** before a turn is
adopted and the **rate at which turns are rejected outright**. It is also
strictly better than a state check alone, because an unconfirmed turn leaves a
definite state behind rather than a hole.

`confirmed_primary_trend(lead, witnesses, k)` is therefore the single
primitive, and the gate is a comparison against its output.

## 2. The other three open questions, settled

**Q2 — which trend definition ships.** Neither is chosen on fidelity. Both are
built behind a `trend_rule` parameter and swept in D6, because the SRS's own
argument cuts both ways: the Dow swing rule is the book's rule but yields only
**15–33 state changes in 20 years** on VNINDEX, while the MA proxy is not
E&M's rule but is the shipped, tested instrument EM-4 already used. Measurement
decides. `FR-EM-D10` already made every default provisional.

**Q3 — do the gate and the penalty make each other unobservable?** Yes, if
combined, and that is the `#83` bug class: capping severities made `#82`'s
override structurally unreachable. **Settled by design: the modes are
mutually exclusive.**

| mode | meaning |
|---|---|
| `OFF` | default; pipeline byte-identical to today |
| `PENALTY` | disagreement reduces confidence, never blocks (`FR-EM-D6`) |
| `CONFIRM_2` | lead + ≥1 witness must agree, else the signal is rejected |
| `UNANIMOUS_3` | all three must agree |

Each is measured as its own arm. Combining `PENALTY` with a gate is possible
later **only if each earns it separately**, and a test asserts the modes do not
stack silently.

**Q4 — the 5% swing threshold.** Swept, but on a deliberately small grid
`{3%, 5%, 8%}` with 5% pre-registered as primary. The full grid is reported
whatever it shows; the decision reads **sign robustness across the grid**, not
the peak cell — `#84`'s lesson, where the sign held across 3–12% while
significance was fragile and 6% happened to be the peak.

## 3. The statistical trap this task carries, named before it bites

**A market-wide gate is one treatment applied on shared dates, not N
independent per-symbol treatments.** Every symbol is blocked on the same days.
So the effective sample size is closer to the number of *independent market
episodes* than to the trade count, and the naive trade-level t-statistic will
be badly overstated.

`#84` clustered by **symbol**, which was correct there: a per-symbol trailing
stop is a per-symbol treatment. **Clustering by symbol here would be wrong**
and would manufacture significance — the within-date correlation is exactly
what it would ignore.

Required instead, fixed now:

1. **Cluster by date**, not symbol.
2. A **block bootstrap over contiguous date blocks** (block length ≥ the
   median holding period) as the primary interval, since the gate's effect is
   serially correlated by construction.
3. Report the **number of independent gate episodes** alongside every p-value,
   the way `#87` reports n in the tail. A result resting on four bear markets
   must say so.

## 4. Tasks

### D0 — Roadmap rows and requirement wiring *(XS)*
`#66` to In Progress with the phase, `FR-EM-D*` IDs recorded. No code.

### D1 — The Dow swing-trend primitive *(S)* — **DONE 2026-10-20**
`app/services/market_context/dow.py`: `swing_trend_series(bars, pct)` →
`List[str]`, closes only, causal, incremental. Ported from the study script
into production shape, which means the study's version stops being the
reference.

Tests first:
* **H-D1** causality — append future bars, no past reading moves.
* **H-D4** determinism — repeated runs identical.
* **H-D6** planted — a constructed series with a known turn is classified at
  the right bar; a monotone series never turns.
* **tenet 12** — a turn that does not complete (one higher high, no higher
  low) leaves the state standing. This is the rule E&M stress most and the
  easiest to implement as a single-condition bug.
* **tenet 11** — intraday extremes do not participate: perturbing highs/lows
  while holding closes fixed changes nothing.
* **H-D5** the bound-default guard, mutation-checked as `#87` did.

**Outcome:** `app/services/market_context/dow.py` +
`tests/test_dow_trend.py` (20 tests, green). Two things worth recording:

1. **My first version of the "declared at the right bar" test had look-ahead
   in it.** It asserted the trend appears at the bar the fourth pivot *formed*
   on; it can only appear at the later bar that *confirmed* it. `Pivot` carries
   both `index` and `confirmed_index` precisely to keep those apart, and the
   test read the wrong one. Corrected, with the reason recorded in the test.
2. **The study script's copy of the rule was buggy**, and porting it exposed
   that: while the leg direction was unknown it reset the running extreme to
   the current close each bar rather than tracking a maximum, declaring
   VNINDEX's trend late on 906 of 5,672 bars. The duplicate is deleted, the
   study now delegates to the tested module, and the SRS §3 Dow-rule figures
   are corrected. **No verdict changed** — and VN30's "never confirms" fell
   from 33% to 7%, strengthening its exclusion.

### D2 — `confirmed_primary_trend` *(S)* — **DONE 2026-10-20**
The §1 composition: lead turns adopted only on witness confirmation within
`k`, otherwise the prior state stands.

Tests first:
* `k = 0` and `k` large bracket the behaviour, and `k` is read at call time.
* An unconfirmed turn leaves the **previous** state (not `UNDEFINED`).
* **EC-D1 fail-open** — witnesses missing ⇒ the lead's own trend is adopted
  unchanged, with a `SKIP` reason. Asserted as *equality with gate-off*, not
  as "roughly the same".
* **EC-D2** — a witness with no bar for day *t* carries its last state, and
  beyond a staleness bound is treated as unavailable (⇒ EC-D1).
* **EC-D5** — indices addressed from the allow-list constant, never a string
  heuristic.

**Outcome:** `app/services/market_context/dow_context.py` (`adopt_turns`,
`market_context_series`, `MarketContext`, the witness allow-list with its
exclusion reasons) + `tests/test_dow_context.py`, 30 tests, green. Split into
two layers so the confirmation rule is tested on literal trend sequences
rather than through bar fixtures. Four mutation checks run; the one that
survived turned out to be an equivalent mutation (clearing `pending` after
expiry is bookkeeping — the deadline guard does the work), and removing the
guard itself is caught.

**Two measured facts that change D6, found here rather than there:**

1. **`k` has no resolution below ~10 bars on this data.** The lag from a
   VNINDEX turn to its first witness agreement is strongly bimodal: **25 of 35
   turns confirm on day 0**, and the remainder at 6, 7, 13, 17, 20, 20, 30, 91
   bars or never (2). **No turn confirms in bars 1–5**, so `k ∈ [0, 5]` is
   literally one gate. A sweep over `{0, 1, 3, 5}` would read *flat — k does
   not matter*, which is the false-flatness shape this project keeps meeting.
   **D6 sweeps `k ∈ {0, 10, 20, 60}`.**

2. **Strictness is stickiness, not bearishness — and the strict/short corner
   is degenerate.** Adoption blocks *turns*, so a rejected DOWN turn leaves
   the previous UP standing. On the real series:

   | mode | k | adopted turns (20 yrs) | longest single state |
   |---|---|---|---|
   | ungated lead | – | 35 | – |
   | `CONFIRM_2` | 0–5 | 21 | 1,051 bars |
   | `CONFIRM_2` | 20–60 | 31–33 | 782 bars |
   | `UNANIMOUS_3` | 0–5 | **5** | **3,911 bars (~15 yrs)** |
   | `UNANIMOUS_3` | 20–60 | 17–19 | 1,422 bars |

   `UNANIMOUS_3` at `k ≤ 5` holds one reading for fifteen years. That is not a
   strict context, it is a **constant**, and a constant is as useless as an
   inert gate while looking like the opposite in a backtest — it produced
   *more* long exposure than no gate at all. So **D6 gains a degeneracy
   criterion** beside `H-D3`'s vacuity guard:

   > A configuration whose adopted trend changes fewer than ~10 times in 20
   > years, or holds one state for more than ~5 years, is **degenerate** and
   > does not ship whatever its P&L. Reported, not silently dropped.

### D3 — GATE 1: does the confirmed trend predict anything at all? *(S)*
The cheapest decisive test, and it runs **before** any pipeline work, because
it can kill EM-6 for a fraction of the cost. No `confirm()` changes, no
backtest: index and symbol bars only.

> **Pre-registered criterion.** Forward returns conditioned on the confirmed
> primary trend must separate: `TREND_UP`-confirmed days must beat
> `TREND_DOWN`-confirmed days at **two or more** of the 10/20/60-session
> horizons, with date-clustered significance (§3) and non-overlapping samples.
>
> **If this fails, stop.** A gate cannot improve signals by conditioning on a
> state that carries no information about forward returns, and no amount of
> wiring changes that. Record the negative and close `#66`.

Sampling follows `#87`'s correction: **every qualifying day with greedy
within-arm non-overlap**, never a fixed stride — the defect that produced
n = 0 on more data.

### D4 — Market-context provider with the shared cache *(S)*
`FR-EM-D7`. One reading per `(date, index)`, reused across the universe.

Tests first: evaluating M symbols issues **exactly 3 index fetches, not 3M** —
asserted by counting calls, since this is a quota constraint (`#49`) and not
an optimisation.

### D5 — Wire into `confirm()`, OFF by default *(M)*
Optional market-context argument; `BacktestConfig` gains `dow_gate_mode`,
`dow_gate_lag_bars`, `dow_trend_rule`, `dow_swing_pct`.

Tests first:
* **H-D2 no-op proof** — with the gate `OFF` or context absent, the
  accept/reject decision and final confidence are **identical** signal for
  signal to today's pipeline. The strongest form: run the existing
  confirmation suite unchanged.
* The four modes are **mutually exclusive** and do not stack (§2, Q3).
* A rejected signal carries a reason step naming the disagreeing indices.
* `dataclasses.replace` is used for config copies, not field-by-field — the
  bug `walk_forward.py` already shipped once, dropping five fields.

### D6 — GATE 2: the in-sample A/B sweep *(M)*
Modes × `k ∈ {0, 10, 20, 60}` (per D2's finding — a finer grid has no
resolution) × `trend_rule` × `swing_pct ∈ {3, 5, 8}%`, same universe and
window, through `backtest/harness.py`. Reports gross and net P&L per trade, hit rate, trade
count, **and the suppressed-signal count** — a gate that lifts hit rate by
discarding most trades has not helped.

Includes **H-D3, the vacuity guard**: a mode that changes < 5% of decisions is
inert and is reported as inert, whatever its P&L. This is the VN30 lesson
(SRS §3) as a test.

> **Pre-registered criterion.** At least one mode must improve **net P&L per
> trade** over `OFF` on a date-clustered test, **without total net P&L
> falling**. Point estimates alone do not pass.
>
> **If no mode passes, stop** — do not proceed to D7 to "check out of sample",
> which would be fishing after a null.

### D7 — GATE 3: walk-forward confirmation *(M)*
Only for a mode that passed D6. The `#84` machinery, with §3's correction:
walk-forward windows, **date**-clustered significance, a sign test across
independent market episodes for consistency, and the episode count reported
beside every p-value.

`#84`'s finding is the shape to expect and to report honestly: magnitude
confirmed, consistency not. Both claims are stated separately.

### D8 — Decision and write-up *(S)*
`docs/em6_dow_gate.md`: what was measured, what the criteria were, what
happened, and what ships. Default stays `OFF` unless D6 **and** D7 passed.
Register, roadmap and `USER_GUIDE` updated. Frontend work only if the gate
ships — no UI for an unshipped mechanism.

## 5. Pre-registered criteria, in one place

| gate | task | criterion | on failure |
|---|---|---|---|
| 1 | D3 | confirmed trend separates forward returns at ≥ 2 of 3 horizons, date-clustered | stop; close `#66` negative |
| 2 | D6 | a mode improves net P&L/trade vs `OFF`, date-clustered, with total net P&L not falling | stop; gate stays `OFF` |
| 3 | D7 | the D6 winner holds out of sample, date-clustered, episode count reported | gate stays `OFF`; record as EM-3-shaped (magnitude without consistency) |
| — | D6 | any mode changing < 5% of decisions is reported **inert** | that mode does not ship regardless of P&L |
| — | D6 | any config adopting < ~10 turns in 20 years, or holding one state > ~5 years, is **degenerate** (D2) | that config does not ship regardless of P&L |

## 6. Sequencing and effort

```
D0 (XS) → D1 (S) → D2 (S) → [GATE 1] D3 (S) → D4 (S) → D5 (M) → [GATE 2] D6 (M) → [GATE 3] D7 (M) → D8 (S)
```

Total **S–M**, and front-loaded so the cheapest kill comes third. D3 needs
only D1 and D2, so three small sessions decide whether the remaining five are
worth running.

## 7. What is deliberately not in this plan

* Populating `market_indices` (`#91` — dead table; EM-6 routes around it).
* The MEI as a fourth witness — `#87` showed breadth *level* carries nothing,
  so adding it now would build on a measured null.
* Acting on the hedge signal (sizing, shorting the index) — portfolio-level,
  and it belongs with EM-4's unbuilt governor.
* Re-pulling index history to 2004 (`#90`) — that is EM-4's re-test, not this.

## 8. Standing risks

1. **The honest prior is unfavourable** (SRS §9): a witness that eventually
   confirms 98% of turns, a cost of a fifth to two-thirds of long signals, and
   four straight E&M candidates that ended at or below their criteria. This
   plan is built to find that out cheaply rather than to avoid finding it.
2. **The date-clustering trap (§3)** is the most likely way to produce a false
   positive here, and it would look exactly like a success.
3. **Few independent episodes.** 20 years of VN data holds a handful of
   primary-trend cycles. If D3 or D6 passes on a point estimate with four
   episodes behind it, that must be said in the same sentence as the result.
