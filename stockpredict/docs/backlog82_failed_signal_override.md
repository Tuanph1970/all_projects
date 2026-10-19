# Backlog #82 — does the failed-signal override belong in the backtest?

**Date:** 2026-10-19
**Study:** `decision-helper-service/tests/failed_signal_override_study.py`
**Answer:** No. It is **off by default in the harness** from this change.
**Scope:** the backtest only. The live recommendation path is untouched — see
the last section.

---

## Why it was asked

`#80` measured that this override closed **66 % of all backtest trades at a
median holding period of one day**, and that the churn guards it added halved
the override's *count* without moving its *share*. A component that ends two
thirds of every position means the ATR stop each trade was **sized** for
almost never decides the outcome — which also makes `EM-3` unevaluable, since
basing-point stops are a stop rule and cannot be judged on a bench where
something else closes the position first.

## What #79 did and did not settle

`#79` measured the two **pattern-based** verdicts over 6,797 causal scans and
found neither predicts anything — `HS_TARGET_FAILURE/SHORT` is significantly
*backwards* (t = +2.34: it implies SHORT and the stock then outperforms by
1.4 %). It then set both severities **below** `OVERRIDE_THRESHOLD`, so neither
can drive an override any more.

**So #79 does not answer this question**, and the backlog entry for #82 —
which I wrote — leaned on it as though it did. The override in the harness is
driven by the *other ten* verdict kinds: `BULL_TRAP`, `BEAR_TRAP`,
`FALSE_TL_BREAK`, `FILLED_GAP`, `OPPOSITE_BREAKOUT`, `RETURN_TO_SPIKE`,
`WRD_RETURN`, `ROUNDING_BREAK`, `COUNTER_ANTICIPATED_FLAG`,
`FUTURE_RELIABILITY` — and none of those had ever been measured. This study is
that correction.

## The criterion, fixed before the run

> The override exists to **cut losses early**. It earns its place if removing
> it makes results **worse** — specifically if **gross P&L per trade** is
> higher with the override on, on the same bars. If removing it leaves results
> the same or better, it is not earning its place and should default off.

**Gross, and per trade.** `#80` established why: with fees at ~3× gross an arm
wins on net purely by trading less, and switching the override off reduces
turnover *by construction*. Net and totals would therefore have flattered the
"off" arm automatically. Gross-per-trade is the one statistic that cannot be
gamed by trading less.

A secondary reading, reported but not decisive: the **exit mix**.

---

## Result, on 12 real VN symbols

| | override **ON** (as shipped) | override **OFF** |
|---|---|---|
| trades | 2,581 | **1,345** |
| bars per trade | 4.64 | **8.91** |
| median holding period | 2 d | **6 d** |
| win rate | 36.1 % | 31.3 % |
| gross P&L | −52,795 | **−15,888** |
| **gross per trade** | **−20.46** | **−11.81** |
| exits | `FAILED_SIGNAL` 1,653 · `STOP` 741 · `TARGET` 183 | `STOP` 1,046 · `TARGET` 291 |

Difference in gross per trade: **+8.64 in favour of switching it off**, Welch
**t = −0.44** — not significant.

So on the pre-registered criterion the override is **no better and probably
worse**, while ending almost two thirds of every position. "Same or better
without it" was the stated condition for dropping, and it is met.

### The exit mix is the clinching secondary reading

With the override off, **78 % of positions end at their stop and 22 % at their
target.** The ATR stop that each trade was *sized* for finally decides the
outcome, instead of being pre-empted. The target-hit *rate* rises from 7.1 %
to 21.6 % — on half as many trades, more than half again as many targets are
actually reached, which is what "let the plan run" looks like in a ledger.

### A number worth not over-reading

Win rate is *higher* with the override on (36.1 % vs 31.3 %) while gross per
trade is *worse*. That is the signature of cutting winners early: more trades
end slightly green, and the ones that would have run are gone. It is a good
illustration of why win rate was not the criterion.

---

## Decision

`BacktestConfig.failed_signal_enabled` defaults to **False**.

It is a **default, not a deletion** — the override is still reachable, so the
measurement can be repeated, and a different market or signal set can reach a
different answer. Five tests pin the decision, including one that asserts the
override still works when switched on.

`#80`'s churn-guard tests were corrected in the same change: they compared
"legacy" against "current defaults", which after this would have conflated the
cooldown and grace window with the override being dropped. They now hold the
override **on** in both arms, so each test moves one variable.

### What this does NOT change

The **live recommendation path** (`decision/orchestrator.py`) still consults
these verdicts. #82 was scoped to the harness, and changing what a user sees
in a recommendation is a different decision with a different blast radius.

But the study bears on it directly, and the implication should not be left
implicit: ten verdict kinds drive user-visible behaviour and **none of them has
been validated**, while the two that *were* measured turned out to predict
nothing and one to be backwards. Logged as **Backlog #83**.

### What would change this answer

* **A validated subset.** The study treats the override as one thing. If one
  or two of the ten kinds carry real information, gating on those alone could
  beat both arms here. That needs a per-kind outcome study of the shape #79
  ran, not a backtest.
* **A different exit discipline.** The override is a *substitute* for a stop
  that is too wide. If stop placement changes — which is exactly what `EM-3`
  proposes — the trade-off is worth re-measuring.

---

## Consequence for EM-3

`EM-3` (basing-point stops) now has a clean bench. Before this change, two
thirds of positions were closed by something other than their stop, so a stop
rule could not have been evaluated: the treatment would barely have been
reached. With the override off, 78 % of exits are stop-hits, which is the
population a stop rule actually acts on.

Combined with `#80` — books that reconcile, costs that scale with turnover —
the harness can now arbitrate EM-3, under #80's standing condition that any
verdict reads **gross and per-trade expectancy alongside net**.
