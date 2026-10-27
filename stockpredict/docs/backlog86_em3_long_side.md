# Backlog #86 — is EM-3's basing-point edge a LONG-SIDE effect?

**Part 1, the pre-registration, is committed BEFORE the long-only arm is
implemented or run.** Part 2 is appended later and may not change a word of
Part 1.

---

# Part 1 — pre-registration (committed 2026-10-27, before any output)

## The hypothesis, and where it came from

`#85` tested whether EM-3's basing-point advantage concentrates in trending
markets. It does not — the point estimate in RANGE (+65.86) came out *higher*
than in trend (+47.69), so the pre-registered regime gate was refuted and not
built.

While reading that table I noticed something it was not testing:

| regime at entry | advantage |
|---|---|
| TREND_UP | +92.68 |
| RANGE | +65.86 |
| TREND_DOWN | **−7.32** — the only negative bucket |

**Hypothesis: the basing-point advantage is a LONG-SIDE effect, not a trend
effect.** Mechanism: E&M's Ch 28 procedure is written for an *advance* — "a
high is made, prices recede, a reaction low forms" — and Bassetti's worked
example is a bull market. The short-side mirror is **our** translation, not a
rule the book validates. If the mirror is simply wrong, the one negative
bucket should be the one full of shorts.

`#86` was raised rather than tested, and the register says why: *"having just
refuted one pre-registered hypothesis, generating a second from the same data
and testing it on the same data is how a finding gets manufactured."* That
still holds. This document exists to test it on evidence it did not come from.

## Two premise checks, done before committing to the test

**1. Are TREND_DOWN entries actually mostly shorts?** The mechanism depends on
it, and #86 asserted it without measuring. Measured, on #85's own sample:

| regime at entry | LONG | SHORT | short % |
|---|---|---|---|
| TREND_UP | 466 | 100 | 17.7% |
| TREND_DOWN | 85 | 331 | **79.6%** |
| RANGE | 245 | 118 | 32.5% |
| all | 796 | 549 | 40.8% |

**Confirmed.** The one negative bucket is 80% shorts; the most positive is 18%
shorts. The hypothesis is at least coherent with its own mechanism.

**2. How much data is the hypothesis resting on?** Less than its own write-up
says. `docs/backlog85_em3_regime_gate.md` reports its table as **"32
symbols"**. It is **12**: `em3_regime_gate_study.py` imports `MAX_SYMBOLS`
from `failed_signal_override_study`, where `#82` set it to 12 on 2026-10-19 —
the day *before* #85 ran — while `em3_walk_forward_study.py` defines its own
`MAX_SYMBOLS = 32`. Re-running #85 today reproduces its published table to the
last decimal on `['ACB','BCM','BID','BVH','CTG','DPG','FPT','GAS','GVR',
'HDB','HPG','MBB']`, which settles it.

This does not change #85's verdict — both criteria failed, and criterion 2
failed on a point estimate that does not depend on power. It does mean the
TREND_DOWN figure driving this hypothesis is 416/320 trades from **12**
symbols, so #86 was resting on a third of the evidence advertised. It is a
cross-study shared-constant trap, the fifth time this project has paid for a
bound default (EM-1 S2, `#78`, `W1`, `#84`, now this). The doc is corrected
in the same commit as this one.

## The sample: 61 symbols that no EM-3 study has ever seen

`#86` asked for the test to run "ideally on symbols or a period not used in
#84/#85". `#87`'s deep pull makes that possible for the first time. Of the 92
symbols in the deep dump, 31 overlap the 32-symbol shallow file used by #63,
#84 and #85. The remaining **61 are held out completely**:

```
AGG ANV ASM BWE CII CMG DBC DCM DGC DGW DIG DPM DXG ELC EVF FRT GEX HAG HCM
HDC HDG HHV HSG HT1 IDC KBC KDC KDH LPB MIG MSH NLG NT2 NVL OCB PAN PC1 PDR
PHR PNJ PPC PTB PVD PVS PVT REE SBT SCS SIP SJS SZC TCH TLG TNH VCI VGC VHC
VIX VOS VPI VTP
```

Median 4,043 bars (~16 years) against the shallow file's 5.3. All 61 clear the
`WARMUP + 90` minimum, so none is dropped and the set is fixed here, before
any result exists.

**Contamination, stated plainly.** I have seen #85's regime table and the
short-composition table above, so I am not naive about the *hypothesis*. I
have seen no result on any of these 61 symbols. That is exactly the separation
#86 was raised to obtain, and it makes this a genuinely out-of-sample test —
cleaner than #99's, where no held-out data existed.

**One difference I am flagging now rather than discovering later:** the
held-out symbols carry ~16 years each, including the GFC, where the original
32 carried 5.3 years from 2021. A result could therefore differ by *period*
rather than by *symbol*. So the post-2021 subperiod of the held-out set is
**also reported**, as a secondary diagnostic and not a criterion, so the two
can be told apart.

## The arms

| arm | longs | shorts |
|---|---|---|
| **A** | ATR 2× trail (the shipped default) | ATR |
| **B** | basing point | basing point (the mirror #63/#84 tested) |
| **C** | basing point | **ATR** — the long-only rule this item proposes |

`basing_point_filter_pct` is fixed at its default **6.0**, which is #84's
primary value, and `basing_point_new_high_rule` stays at its default. No sweep:
a sweep here would be a search.

## The metric and the inference

Gross P&L per trade, per `#80`. Clustered by symbol, per `#84`: for each
symbol take the mean gross P&L per trade in each arm, difference them, and run
a **paired t across the 61 symbols**. One observation per symbol, 61
independent units — against #85's unpaired per-trade Welch, which treated
~1,300 trades from 12 symbols as independent draws.

A symbol contributing fewer than **2 trades on the relevant side** in either
arm is excluded from that comparison, and the count of exclusions is reported.

## CRITERION, fixed before the run

Both, or the hypothesis does not hold:

1. **On LONG trades, arm B beats arm A** — clustered paired t > **+1.96**.
2. **On SHORT trades, arm B does not beat arm A** — point estimate **≤ 0**.

Together these say the advantage is real on longs and absent or harmful on
shorts, which is the claim. Criterion 2 is deliberately a point estimate
rather than a significance test: the hypothesis is that the mirror adds
*nothing*, and demanding significance for a null would make it unfalsifiable.

## All three readings, pre-stated so the framing cannot be chosen later

* **Both pass** → the hypothesis is supported out of sample, and arm C is the
  form EM-3 should ship in. #63 would move from Partial toward a real
  recommendation.
* **1 passes, 2 fails** (shorts also positive) → the advantage is *not*
  long-specific. It is unconditional, exactly as #84 found, and #86's
  distinction is refuted. The rule still works; my reading of why was wrong.
* **1 fails** → the EM-3 edge does not replicate on 61 unseen symbols at all.
  That is a **bigger and more important negative result than #86 asked for**,
  it supersedes this hypothesis entirely, and it would mean #63's
  "first E&M candidate to beat its benchmark with significance" rested on 12
  to 32 symbols of one 5.3-year window. I commit now to reporting that outcome
  as the headline if it occurs, rather than burying it under the long/short
  split.

## Also reported, not criteria

* arm C vs arm A, and arm C vs arm B, on **all** trades — the shipping
  question, which follows from the criteria but should be measured.
* the post-2021 subperiod, per the period caveat above.
* long and short trade counts per arm, because a stop rule changes when trades
  exit and therefore how many there are.

## What this cannot settle

61 symbols of VN data is one market and one era. A long-side-only rule that
works here is still a claim about Vietnamese equities 2004-2026, not about
E&M's procedure in general. And EM-3's edge was already known to be
**tail-driven and inconsistent** (#84: 54% of windows, sign test never
significant); nothing here changes that, so even a pass leaves a rule that
wins by magnitude rather than by reliability.
