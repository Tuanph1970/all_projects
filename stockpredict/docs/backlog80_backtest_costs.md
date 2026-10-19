# Backlog #80 — backtest turnover and fee realism

**Date:** 2026-10-19
**Code:** `decision-helper-service/app/services/backtest/{harness,slippage}.py`
**Tests:** `tests/test_backtest_costs.py` (20), `tests/test_pyramiding.py`

---

## What #80 asked

> Investigate why re-entry is so immediate (a `k_delay` / cooldown issue, or
> the state machine returning to FLAT too eagerly), and make the fee model
> proportional rather than flat per trade.

Both done. The investigation found **three** defects rather than one, and the
headline symptom — "commission is 1.8× the gross result" — turns out **not** to
be fixed by making fees realistic. That is the most useful thing in this
report, so it is stated plainly below rather than buried.

---

## Defect 1 — the books did not reconcile

The flat `commission` was deducted from equity **at entry** and subtracted
again inside `net_pnl` **at close**, but `TradeRecord.commission` recorded only
the exit leg. So:

* `total_commission` reported **half** the fees actually charged;
* `total_net_pnl` was **overstated by one commission leg per trade**;
* the end-of-period force-close then charged the entry leg a **second** time.

On a 151-trade synthetic replay the equity curve ended 1,490 below what the
headline net claimed. **Every A/B comparison run through this harness was
comparing a number that did not describe the account.** That is the defect
that most directly blocked EM-3, and it is independent of fee realism.

`TradeRecord.commission` is now the round-trip cost, equity is charged each
leg exactly once, and three tests assert that ledger, stats and equity curve
describe one set of books.

## Defect 2 — the fee model was flat per trade

Wrong for the market this platform trades. Vietnamese brokerage is a
percentage of turnover (typically 0.15–0.35 % per side) and the sell side pays
a transfer tax on proceeds (0.1 %). A flat fee charges a 50,000 account and a
500,000 one the same amount, which makes fees look negligible at size and
ruinous when small — neither of them true.

`trade_cost()` is now proportional, with the tax applied to disposals only.
The flat model stays expressible (`commission_pct=0`, `commission=10`) so the
before/after is measurable rather than remembered, and so a broker with a
genuine fixed fee can still be configured.

## Defect 3 — the harness churned, and here is why

Measured on the reference replay before any change:

| | |
|---|---|
| bars per trade | **2.52** |
| exits by `FAILED_SIGNAL` | **99 of 151 (66 %)** |
| median holding period | **1 day** |
| exits followed by a new entry on the **same bar** | **103 of 150** |

Two mechanisms, both of them "the state machine returning to FLAT too
eagerly" rather than a `k_delay` problem:

1. **Same-bar re-entry.** The position closes in step 2 or 3, `pos` goes FLAT,
   and the entry block re-opens it *in the same bar iteration* — because the
   signal that justified the first entry is **level-triggered** and still true.
2. **The failed-signal override.** It closed two thirds of all trades at a
   median holding period of one day: the confirmation layer approved an entry
   on bar N and the failed-signal detector declared it failed on bar N+1. That
   is not two components disagreeing about the market so much as about each
   other — and Backlog #79 separately found those verdicts predict nothing.

Both now have guards: `reentry_cooldown_bars` (default 1) and
`failed_signal_grace_bars` (default 2). Setting both to 0 restores the old
behaviour exactly, so this is a default and not a silent redefinition.

---

## Results, on 12 real VN symbols

| config | trades | bars/trade | gross | commission | net | comm ÷ \|gross\| |
|---|---|---|---|---|---|---|
| old: flat fee, no guards | 4,858 | 2.47 | −28,561 | 97,160 | −125,721 | **3.40×** |
| **new defaults** | **2,581** | **4.64** | −52,795 | 172,327 | −225,122 | **3.26×** |
| new, fees set to zero | 2,581 | 4.64 | −57,711 | 0 | −57,711 | — |

**Turnover halved** — 4,858 trades to 2,581, and bars-per-trade from 2.47 to
4.64. The churn guards do what they were built for.

**The fee-to-gross ratio barely moved: 3.40× → 3.26×.** Realistic proportional
fees are *larger* than the unrealistically cheap flat 10, so making them
correct did not make them smaller.

### Why the ratio stays high, and why that is not a harness defect

The ratio is large because **gross is near zero**, not because fees are
absurd: −57,711 gross across 2,581 trades is about −22 per trade on a 100,000
account, which is noise. Any strategy without a gross edge will show fees
dominating its net, and that is the correct answer rather than a bug. The
harness's job is to report that, not to hide it behind a cost model cheap
enough to flatter the result — which is precisely what the flat 10 was doing.

---

## So is the harness A/B-able now? Yes, with one condition

EM-3 and every other backtest-arbitrated candidate needs the harness to
resolve a difference between two arms. It now can, for three reasons:

1. **The books reconcile.** Previously the headline net was wrong by one
   commission leg per trade, so A/B comparisons were comparing a number that
   did not describe the account. This was the blocking defect.
2. **Costs scale with turnover**, so an arm that trades less is correctly
   rewarded. Under the flat model turnover was under-penalised at size and
   over-penalised when small.
3. **The cost model is identical across arms**, so it adds drag but no bias.

**The condition:** read **gross P&L and per-trade expectancy alongside net**.
With fees at 3× gross, an arm can win on net purely by trading less — and the
plan's own `W1` warning applies directly: *an improvement in a total that comes
from doing less is not an improvement*. Both numbers are reported; a verdict
that quotes only net is not a verdict.

---

## Two things deliberately not done

**The failed-signal override is still the dominant exit.** The guards halve
its *count* (99 → 51 on the reference replay) but not its *share* — 66 % before
and after, because the cooldown removes trades roughly uniformly across every
exit reason rather than selectively removing the pathological ones. So the
grace window postpones the override without displacing it. Combined with #79's
finding that these verdicts predict nothing, the real question is whether the
override belongs in the harness at all — which is a change to what the
strategy *is*, not to how it is costed, and so belongs in its own slice.

**The strategy's lack of gross edge is untouched.** #80 is about measurement.
That the thing being measured loses money gross is now visible rather than
obscured, which is the point.
