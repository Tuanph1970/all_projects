# EM-8 — measuring implications: what shipped, and what was retired

**Date:** 2026-10-21
**Backlog:** `#68` · fixes `#92`, `#93` · **closed**
**Design:** `SRS_edwards_magee_measuring.md` · **Plan:** `implementation_plan_em8_measuring.md`
**Studies:** `em8_calibration.md` (M2), `em8_target_mode_study.py` (M3)

EM-8 asked three questions. All three are answered, none of them the way the
register expected, and the two concrete deliverables are **a corrected formula
and a fixed crash** rather than a new feature.

---

## (a) Do E&M's objectives get reached? No — and the famous ones do worse than chance

Full result in `docs/em8_calibration.md`. 92 symbols, 320,237 bars, in the
250-bar window production uses.

**0 of 3 horizons for all five E&M families**, and three are *significantly
worse* than a distance- and direction-matched random entry — Flag/Pennant at
**−9.0%, t = −18.80** on 22,615 observations, of which E&M say the measuring
rule *"works out with amazing accuracy"*.

The only objective in the catalogue that beats the null is **ours**: the
bull/bear trap, +9 to +10 points at every horizon, surviving Holm. It is
visible only because `FR-EM-M4` kept E&M's rules and ours in separate tables
— a decision taken in the SRS before anything was measured.

## (c) Is a measured objective a good exit? The path has never run

`MEASURED_MOVE` is **dead code in both the live and backtest paths**:
`compute_target` reads `measured_move_target` out of a `RawSignal`, no shipped
detector puts that key in evidence, and `orchestrator.py:179` routes
ai-insights patterns to the **failed-signal** detectors instead. Measured:
**4,193 of 4,193** target computations carried no such key; `MEASURED_MOVE`
was **0%** of chosen targets.

So the planned `MEASURED_FIRST` vs `NO_MEASURED` comparison was two identical
arms, and building it would have produced a null that looked like evidence.
This is the `#73` shape in a new place — *"the five pattern detectors in this
module had never fired once."* `tests/test_target_mode.py` keeps it
dead-by-record: it fails the moment any detector starts emitting the key.

The branch is **dead, not broken** — handed the key, it behaves correctly — so
this is a wiring question, and `(a)` answers whether wiring it would be worth
it: **no**, except possibly for traps.

### The measurable half: targets as a class, versus a pure trailing stop

That is E&M's actual Ch 32 position — *prefer nearby progressive stops for
taking profits over limit orders*, because the overrun *"is itself an
unreasonable move"*. Targets do fire here, via S/R and fixed R:R.

| mode | trades | net / trade | total net | TARGET_HIT | STOP_HIT |
|---|---|---|---|---|---|
| `TARGETS_ON` (today) | 36,063 | −47.39 | −1,709,164 | 9,114 | 26,895 |
| `TRAILING_ONLY` | 27,225 | **−32.18** | **−876,149** | 0 | 27,155 |

| | |
|---|---|
| mean difference (ON − OFF) | **−16.97 per trade** |
| median difference | −1.00 |
| paired t, 92 symbols | **−2.27** |
| symbols where ON is better | **45 / 92 (49%)**, sign test p = 0.92 |

**The criterion fails, and significantly in the opposite direction.** The
trailing stop alone lost about half as much in total while taking 25% fewer
trades. E&M's preference is supported.

## (b) Does the cap help? Not built, and the reason is (c)

`M4` and `M5` were not built. The *"a reversal must have something to
reverse"* cap applies in `target_module` to `measured_move_target` — a field
that never arrives. Capping it would change nothing that runs.

---

## The decision: the default does **not** change

`TARGETS_ON` stays the default, and that is a deliberate application of this
project's own standard rather than a hedge.

**EM-3 is the precedent.** Its basing-point stop showed gross/trade
−16.51 → +22.80 at t = +2.02 in sample, confirmed out of sample on
**magnitude** (clustered t = +3.39, 66% of symbols) — and the default stayed
`ATR` because **consistency** failed the sign test. Here consistency is
*worse*: 49% of symbols, sign test p = 0.92, and a median difference of −1.00
against a mean of −16.97, which says the effect is a **tail of symbols**, not
a broad shift.

Flipping a shipped default on a tail-driven result that fails the same test
EM-3 was held to would be applying a looser standard to a conclusion I happen
to find congenial. The result is recorded, the switch is shipped so anyone can
run either arm, and the default stays where measurement has not earned a
change.

Two further reasons to hold:

1. **Both arms lose money.** −47.39 and −32.18 per trade. The harness is a
   measurement bench, not a strategy, so "better" here means "loses less". A
   default chosen between two negative expectancies is not a result worth
   acting on alone.
2. **My own 6-symbol smoke run pointed the other way** — +16.71 per trade
   *favouring* targets, at t = +0.76. Flagged as underpowered at the time, and
   the sign flipped on 92 symbols. The same shape `#87` found when EM-4's
   quintile result reversed. A result that moves this much with sample size
   warrants more than one measurement before it moves a default.

## What actually shipped

| | |
|---|---|
| **`#92`** | the gap objective: runaway subtype only, via E&M's halfway construction. Gap objectives fell **3,229 → 979** (30% retained) across 20 symbols; 70% of them had no basis in the book. A **second site** was found by measuring the blast radius — EM-1's volume relabel turned runaway into exhaustion without withdrawing the objective, so 61 of 488 exhaustion gaps carried a target pointing the way the move was *ending*. |
| **`#93`** | a non-positive price crashed `compute_initial_stop` on the live path. 13 zero/negative bars in 320,237 from the vendor. Two guards; the harness now declines the entry outright. |
| `target_mode` | `TARGETS_ON` / `TRAILING_ONLY` in `BacktestConfig`, default unchanged and byte-identical |
| the calibration | `em8_calibration.py` + 23 tests, reusable |
| the dead-path record | `test_target_mode.py` — `MEASURED_MOVE` cannot become live silently |

## What EM-8 recommends next, and what it does not

**Does not recommend:** wiring ai-insights objectives into signal evidence.
`(a)` measured them and three of five E&M families are worse than chance.

**Worth considering, separately:** the **trap** objective is the one measured
positive (+9 to +10 points, all horizons, Holm-surviving). If any objective
earns a wiring, it is that one — and it is *ours*, not the book's. It needs
its own pre-registered test before anything is built, because the hypothesis
came out of this study and should not be confirmed on the data that generated
it (the `#85` → `#86` discipline).

**Also open:** `TARGETS_ON` vs `TRAILING_ONLY` deserves a second look on
evidence this result did not come from, given the sign flipped between 6 and
92 symbols. Logged rather than acted on.

---

## Standing

| | |
|---|---|
| E&M's five measuring rules | **no information**; three significantly worse than chance |
| our trap objective | **the only one that beats the null** |
| `MEASURED_MOVE` | **dead code**, recorded as such; not wired, not removed |
| the cap (item 125) | **not built** — it would cap a field that never arrives |
| targets vs trailing stop | trailing wins on **magnitude** (t = −2.27), fails **consistency** (49%, p = 0.92) |
| the default | **unchanged**, by the same standard EM-3 was held to |
| `#92`, `#93` | **fixed and shipped** |

E&M's register is now five candidates measured to a conclusion: EM-1 shipped,
EM-2 negative, EM-3 real but tail-driven, EM-4's headline overturned, EM-6
negative, EM-8 two bug fixes and three answered questions. EM-5 (`#65`) and
EM-7 (`#67`) remain.
