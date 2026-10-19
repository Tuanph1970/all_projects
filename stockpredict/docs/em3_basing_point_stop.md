# EM-3 — the basing-point stop engine

**Date:** 2026-10-19
**Code:** `decision-helper-service/app/services/risk/basing_point.py`
**Study:** `tests/em3_basing_point_study.py` · **Tests:** `tests/test_basing_point_stop.py` (20)
**Verdict:** the first E&M candidate to beat its benchmark with significance — with one
qualification that matters, stated in full below.

---

## The rule

Edwards & Magee Ch 28, which Bassetti calls *"of absolutely basic importance"*,
as his four numbered rules:

1. A high is made, recognised by no higher prices for the moment.
2. Prices recede to a candidate low; watch each later day whose range lies
   **completely outside** the candidate's.
3. When **three such days** occur before a new low, the candidate becomes a
   **basing point** — raise the stop to x % under the low of that day.
4. When a new high exceeds the previous high by **3 %**, a new basing point is
   set at the low of that new-high day.

Stops are **never** lowered, even when a later low undercuts an old one.

### Why it is not the SWING stop already shipping

`stop_module`'s SWING stop sits at the nearest confirmed pivot — which is
*precisely* the obvious prior low E&M warn about. Bassetti quotes Bruce
Kovner, asked where he puts his stops: *"Where they're hard to get to."* And:
*"locals… know that the previous low is where investors and traders set their
stops… if they see an opportunity to take out an important low they will do
it."*

The basing point will not trust a low until **three full days have cleared
it**, and then sits a **filter** below. Both exist to put the stop somewhere a
probe does not look first.

---

## The benchmark

The bench is only now usable. `#80` fixed books that did not reconcile and a
cost model that dominated every result; `#82` switched off an override that
was closing two thirds of positions **before their stop was reached** — which
would have made a *stop rule* unevaluable, because the treatment was barely
being applied.

**Criterion, fixed before the run:** the basing-point stop earns its place if
**gross P&L per trade** beats the ATR trail's, on the same signals. Gross and
per-trade for `#80`'s reason — at ~3× fees an arm wins on net purely by
trading less, and a wider stop holds positions longer by construction.

### Result, 32 real VN symbols

| arm | trades | gross / trade | win rate | stop-outs | targets |
|---|---|---|---|---|---|
| ATR trail (shipped) | 3,701 | **−16.51** | 31.0 % | 76.9 % | 22.6 % |
| **Basing point, rules 1–3** | 2,720 | **+22.80** | 33.0 % | **66.8 %** | **32.4 %** |
| Basing point + rule 4 | 2,851 | +16.58 | 32.7 % | 68.4 % | 30.9 % |

| comparison | difference | Welch t | |
|---|---|---|---|
| rules 1–3 vs ATR | **+39.31** | **+2.02** | **significant** |
| rules 1–4 vs ATR | +33.09 | +1.76 | not significant |

**The swing is large enough to change the sign**: gross per trade goes from
−16.51 to +22.80, i.e. from a strategy that loses money before costs to one
that makes it.

### The mechanism E&M predicted is visible in the exit mix

Stop-outs fall from **76.9 % to 66.8 %** and target-hits rise from **22.6 % to
32.4 %**. That is exactly the claim — a stop placed where it is hard to get to
is taken out by a probe less often, so more positions survive to reach their
target. The result is not a statistical accident in search of a story; the
story is visible in how the trades end.

### Rule 4 is worse, exactly as E&M warned

The register carried E&M's own caveat: advancing the stop on new highs too can
force a premature exit on a mid-trend blow-off, which is why Bassetti teaches
a "simplified version" using only wave lows. Measured: rules 1–3 give +22.80,
rules 1–4 give +16.58. **The flag defaults off, and that default is now a
measurement rather than a precaution.**

### The sample behaved like a real effect

At 12 symbols the difference read +48.79 at t = +1.42; at 32 symbols it reads
+39.31 at t = +2.02. The point estimate held its sign and magnitude while the
significance grew with the sample — which is what a real effect does, and
pointedly not what happened in EM-2's `S4`, where the sign inverted when the
sample grew.

---

## The qualification, which matters

**This is an in-sample run, and `C4` asks for out-of-sample.** `CLAUDE.md`'s
standing bar is that a method improves only if it beats its benchmark **out of
sample** with significance. This A/B replays the whole available history for
both arms; it is not a walk-forward.

And **t = +2.02 is marginal** — just past 1.96, on one sample, with one
parameter set.

So the precise verdict is: **EM-3 clears its own pre-registered criterion and
is the first candidate in this workstream to do so, but it has not yet cleared
`C4`.** `walk_forward.py` already exists in the harness and is the natural
next step; until it runs, the honest claim is "promising and unconfirmed",
not "proven".

**The harness default therefore stays `ATR`.** Flipping it is a behaviour
change, and this workstream's whole record argues against making one on a
marginal in-sample result — EM-2 spent seven tasks establishing that
discipline. The mode is a config field, so the walk-forward can be run against
it without further surgery.

---

## What shipped

* `BasingPointTracker` — fed one bar at a time, holding no reference to the
  series, so it cannot read ahead even by accident (a test asserts `update()`
  contains no indexing, slicing or shifting).
* 20 tests covering all four rules, the never-lowered guarantee in both
  directions, the strict "completely outside" reading, the candidate reset
  that lets the stop advance across successive reaction lows, and the inert
  behaviour on an unknown direction.
* `BacktestConfig.trailing_stop_mode` (`"ATR"` | `"BASING_POINT"`), plus
  `basing_point_filter_pct` and `basing_point_new_high_rule`.

### A bug the tests caught

The first implementation never retired a confirmed candidate, so the stop was
pinned to the **first** basing point of the trade and could never advance.
E&M's procedure is a cycle — a high is made, prices recede, three days clear,
the stop rises, and then you wait for the *next* reaction low and repeat — so
a confirmed candidate is now retired and the next bar starts a new one.

---

## Next

1. **Walk-forward confirmation**, which is what `C4` actually requires and the
   only thing standing between this and a shipped default.
2. **Sweep the filter.** 6 % is the book's figure for 1950s NYSE issues and
   has not been swept; `FR-EM-S10`'s precedent applies.
3. If both hold, flip `trailing_stop_mode` and consider the live
   `stop_module` path — which is a user-visible change and needs its own
   decision, as `#82`/`#83` did.
