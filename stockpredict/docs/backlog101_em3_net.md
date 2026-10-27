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
