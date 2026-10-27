# Backlog #101 — EM-3 net of costs, and what it licenses

**Part 1 is committed BEFORE the run.** Part 2 is appended after and may not
change a word of Part 1.

---

# Part 1 — pre-registration (committed 2026-10-27, before any output)

## Why one more number

`#86` tested the basing-point trail on 61 symbols no EM-3 study had seen and
found it beats the ATR trail by **+47.28 gross per trade** (clustered
t = +7.08) and **+12,449 total gross P&L per symbol** (t = +6.60), 51 of 61
symbols positive. That is the project's strongest E&M result.

Every one of those figures is **gross**. `#80` pinned the metric at gross for a
good reason — a flat commission came to 1.8× the result it was measuring, so
A/B runs were being arbitrated by the cost model rather than by the thing under
test. But that reasoning makes gross the right metric for **isolating the stop
rule**, not for **deciding what to ship**. A user keeps net.

So: the same comparison, the same symbols, the same clustering, with
`net_pnl` in place of `gross_pnl`. Nothing else changes.

## The trap this measurement walks into, named in advance

`#82` already recorded it, in the harness itself: at these fee levels *"an arm
wins on net by trading less"*. The basing-point arm trades **23% less by
construction** (18,586 against 24,225). So a net win is **partly guaranteed**
and is **not**, on its own, evidence that the stop rule is better.

Gross and net therefore answer different questions and both are reported:

* **gross** — is the rule better? (`#86`: yes, +47.28/trade, t = +7.08)
* **net** — would a user have made more money? (this item)

To keep the second honest, commission paid per arm is printed too, so the net
figure can be **decomposed** — net edge = gross edge − commission difference —
rather than quoted as though it were independent evidence.

## Method, inherited unchanged from #86

| | |
|---|---|
| sample | the same 61 held-out symbols, full history |
| arms | A = ATR, B = basing point both sides, C = long-only |
| inference | total P&L per symbol, paired t across 61 symbols |
| cost model | the config defaults as repaired by `#80`: `commission_pct` 0.15 per side, `sell_tax_pct` 0.10 on sells, flat `commission` 0.0, slippage 5 bps |
| `basing_point_filter_pct` | 6.0, not swept |
| the only change | `gross_pnl` → `net_pnl` |

`net_pnl = gross_pnl − (entry_cost + exit_cost)`, both legs, which `#80` made
reconcile with the equity curve exactly. The gross figures are printed
alongside and **must reproduce #86**; if they do not, the run is wrong and
nothing in it may be quoted.

## THRESHOLD, fixed before the run

> The basing-point trail wins on net if **total net P&L per symbol is positive
> AND the clustered paired t exceeds +1.96** — #86's inference, unchanged.

## The three readings, pre-stated

* **Net positive and significant** → the BACKTEST default may change on
  evidence alone. The LIVE path is still an owner decision, because
  `harness.py` records that the recommendation path consults these verdicts
  and changing it is user-visible (the `#83` gate). I will not flip the live
  rule myself.
* **Net positive but not significant** → not enough. Default stays ATR, and
  the honest summary is that the rule survives costs without clearing the bar.
* **Net negative** → the gross result was a cost illusion, the default stays
  ATR, and **#86's headline needs a caveat written into it** rather than left
  standing.

In all three cases the commission decomposition is reported, so a reader can
see how much of the net result is the stop rule and how much is simply lower
turnover.

## What this still cannot settle

A cost model is an assumption. 0.15% per side plus 0.10% sell tax is
representative of Vietnamese retail brokerage, but a different broker, a
different size, or market impact beyond the flat 5 bps of slippage would all
move the number. This is one cost scenario, not a guarantee — and no part of
it speaks to whether the live recommendation path should change, which stays
with the owner either way.

---

# Part 2 — the result (appended 2026-10-27, after the run)

Part 1 is unedited. Same 61 held-out symbols, same arms, same clustering.

**The gross column reproduced #86 exactly** — +47.28/trade at t = +9.13,
+12,449 total per symbol at t = +6.60, 51/61 — so the run is valid and every
difference below is the metric and nothing else.

## THE THRESHOLD IS MET

| | | |
|---|---|---|
| total **net** P&L per symbol, basing point vs ATR | **+16,383** | |
| clustered paired t | **+8.97** | |
| symbols positive | **54 / 61** | |
| positive **and** t > +1.96 | **YES** | threshold met |

Net is **larger** than gross (+16,383 against +12,449), which is the direction
Part 1 expected and the reason it insisted on a decomposition.

| comparison | side | gross | **net** | t net | positive |
|---|---|---|---|---|---|
| B − A | LONG | +11,666 | **+14,038** | +9.38 | 55/61 |
| B − A | SHORT | +783 | **+2,345** | **+3.02** | 42/61 |
| B − A | all | +12,449 | **+16,383** | +8.97 | 54/61 |
| C − B | all | +1,136 | **−1,436** | −1.63 | 27/61 |

## The decomposition, which is the point of the exercise

Commission paid across all 61 symbols:

| arm | commission | per trade | trades |
|---|---|---|---|
| A (ATR) | 1,603,027 | 66.17 | 24,225 |
| B (basing point) | **1,363,017** | **73.34** | 18,586 |
| C (long-only) | 1,519,927 | 73.48 | 20,685 |

Arm B saved **240,010** in commission, or **3,935 per symbol** — and the
accounting closes exactly:

```
net edge  =  gross edge  +  commission saved
 +16,383  =    +12,449   +      +3,934
```

| | gross (the rule) | commission saved (less turnover) |
|---|---|---|
| LONG | **83.1%** | 16.9% |
| SHORT | 33.4% | **66.6%** |
| **all** | **76.0%** | 24.0% |

So the `#82` trap Part 1 named is **real but a minority**: about a quarter of
the net advantage is simply trading less. **Three quarters is the stop rule.**
The net win is not a cost illusion.

Note also that arm B is **not cheap per trade** — it pays *more* (73.34 against
66.17), because it holds longer and exits at better prices, so its exit leg
carries a larger notional. The saving is purely frequency: 23% fewer trades.
That is worth stating plainly, because "it wins because it's cheaper" would be
the wrong summary.

## This refines #86 on the short side

`#86` concluded the short-side mirror is **neutral** (gross +783, t = +1.01).
On net it is **positive and significant** (+2,345, t = +3.02). But the
decomposition says not to read that as the rule working on shorts: **67% of
the short-side net advantage is commission saved**, because arm B takes 22%
fewer short trades. Only a third is the rule.

So the honest statement is unchanged in substance and sharper in form: the
basing-point rule earns its keep **on longs** (83% merit); on **shorts** it
roughly pays for itself, mostly by trading less. `#86`'s refutation of the
long-side *hypothesis* stands — the mirror is not harmful — and `#101` adds
that it is not where the money comes from either.

## Long-only is now clearly the wrong arm

`#86` found arm C a wash on gross (+1,136, t = +1.18). On net it **flips
negative**: −1,436 overall and **−1,393 at t = −2.80 (significant) post-2021**,
with only 19 of 61 symbols better. C trades more than B, so it pays more
commission for no gross gain. **Long-only should not ship**, now on two metrics
rather than one.

## Secondary: post-2021

| comparison | side | gross | net | t net | positive |
|---|---|---|---|---|---|
| B − A | LONG | +2,335 | +3,439 | +6.69 | 50/61 |
| B − A | SHORT | +460 | +1,223 | +3.22 | 38/61 |
| B − A | all | **+2,796** | **+4,662** | **+6.98** | 49/61 |
| C − B | all | −604 | −1,393 | **−2.80** | 19/61 |

Threshold met here too. One drift worth recording: the turnover share of the
net advantage rises from **24% to 40%** in the recent period, because the gross
edge is smaller there while fees are not. Still 60% merit, still t = +6.98.

## What I probed before recommending anything

**Flipping `BacktestConfig.trailing_stop_mode` to `"BASING_POINT"` breaks
nothing** — 963 passed. That sounds reassuring and is actually a finding:
**nothing in the suite pinned the shipped default**, so it could have moved in
any commit without a single failure.

The first probe did break exactly one test — **mine**,
`test_the_mode_is_read_at_call_time_not_frozen_at_import` from `#86`, and for a
bad reason: its `_ledger` helper omitted `trailing_stop_mode` for the ATR arm
and leaned on the default, so with the default flipped two of its three arms
became the same run. That is the bound-default pattern this project has paid
for five times, in a test I wrote the day before. Fixed to pass the mode
explicitly, and a guard added
(`test_the_shipped_backtest_default_is_still_the_ATR_trail`) so the default
cannot move silently again.

## Recommendation, and what I am NOT doing

**The evidence supports switching the backtest default to the basing-point
trail.** It wins on gross (+12,449/symbol, t = +6.60) and on net
(+16,383/symbol, t = +8.97), on 61 symbols no EM-3 study had seen, broadly
(54/61), with three quarters of the net advantage attributable to the rule
rather than to lower turnover, and the same direction in the recent
subperiod.

**I have not changed either default.** Two reasons, and the second is the
binding one:

1. Changing `BacktestConfig`'s default silently redefines "baseline" for every
   other study in this service. Past published numbers stay valid, but future
   runs would quietly compare against a different control, and this workstream
   has been damaged by exactly that kind of drift five times.
2. The **live** recommendation path consults these verdicts, and `harness.py`
   records that changing it is user-visible and needs its own decision — the
   `#83` gate. That is the owner's call, not a measurement's.

So `#101`'s deliverable is complete: the number exists, it clears the
pre-registered threshold, and it is decomposed honestly. The flip itself is
one line plus the guard test, and it is waiting on an owner decision.

## What this still does not settle

One cost scenario. 0.15% per side plus 0.10% sell tax is representative VN
retail brokerage; a different broker, a larger size, or market impact beyond
the flat 5 bps of modelled slippage would all move the number. And `#84`'s
window-level inconsistency is untouched: this rule still wins by magnitude
spread over many symbols, not by being reliable within any one of them.

## Reproducing

```bash
cd stock_microservices/services/decision-helper-service
PYTHONPATH=. python3 tests/em3_long_side_study.py   # ~60 min; prints gross AND net
```
