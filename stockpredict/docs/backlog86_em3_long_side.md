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

---

# Part 2 — the result (appended 2026-10-27, after the run)

Part 1 is unedited. 61 held-out symbols, median ~16 years, three arms each.

## The pre-registered criterion

| | | |
|---|---|---|
| 1. LONG: basing point beats ATR, t > +1.96 | t = **+9.13** | **PASS** |
| 2. SHORT: basing point does **not** beat ATR, ≤ 0 | edge = **+8.54** | **FAIL** |

### **HYPOTHESIS NOT SUPPORTED.**

This is pre-stated reading #2: the advantage is not long-specific, it is
unconditional, and my reading of *why* EM-3 works was wrong.

Gross P&L per trade, paired by symbol, 61 symbols, none dropped:

| comparison | side | edge | t | symbols positive |
|---|---|---|---|---|
| B − A | LONG | **+73.42** | **+9.13** | 56/61 |
| B − A | SHORT | +8.54 | +1.01 | 35/61 |
| B − A | all | **+47.28** | **+7.08** | 52/61 |
| C − A | LONG | +75.29 | +10.15 | 57/61 |
| C − A | all | +43.58 | +8.35 | 55/61 |
| C − B | all | −3.69 | −0.93 | 28/61 |

## Why it failed, and the distinction #86 conflated

Two separate claims were bundled into one hypothesis, and the held-out data
splits them:

* **"The advantage is concentrated on the long side"** — *true, and starkly
  so.* +73.42 against +8.54, eight and a half times; 56 of 61 symbols positive
  on longs against 35 of 61 on shorts, which is a coin flip.
* **"The short-side mirror is harmful"** — *false.* It is **neutral**:
  +8.54 at t = +1.01. #85's TREND_DOWN figure of **−7.32 does not replicate**.
  On 61 unseen symbols the short side is mildly positive and indistinguishable
  from zero.

So the mirror is not a defect, and there is nothing to remove. **#86's hypothesis
was built on a −7.32 from 12 symbols that did not survive contact with 61 new
ones** — which is precisely the outcome #86 was written to make possible, and
the reason it refused to test itself on #85's data.

**The proposed remedy therefore buys nothing, and may cost.** Arm C against arm
B is a wash on the full history (−3.69 per trade, t = −0.93; +1,136 total,
t = +1.18) and **significantly worse post-2021** (−13.84 per trade, t = −2.07,
only 19 of 61 symbols better). Long-only should **not** ship.

## The finding that outgrew the question

EM-3's basing-point advantage **replicates out of sample, broadly, on 61
symbols no EM-3 study has seen**: +47.28 per trade at clustered **t = +7.08**,
against +39.31 at t = +2.02 in-sample (#63) and clustered t = +3.39 (#84).

Before publishing that I checked the confound that could have manufactured it:
**arm B takes 23% fewer trades** (18,586 against 24,225), and a per-trade mean
rewards a rule for trading less. `#80` fixed the metric at gross-per-trade for
an unrelated reason — commission was 1.8× the result it was measuring — so this
had never been addressed.

**Total gross P&L per symbol** — same period, same starting equity, the
economically meaningful quantity (post-hoc diagnostic, not a criterion):

| comparison | side | total edge per symbol | t | symbols positive |
|---|---|---|---|---|
| B − A | LONG | **+11,666** | **+7.77** | 54/61 |
| B − A | SHORT | +783 | +0.98 | 33/61 |
| B − A | all | **+12,449** | **+6.60** | 51/61 |
| C − B | all | +1,136 | +1.18 | 34/61 |

The two views agree, so the edge is not an artefact of trade count. And it is
not an artefact of sitting out either — **arm B is in the market 11% *more*
days** (213,033 against 191,300) while taking 23% fewer trades, so it earns
more in total from more exposure spread over fewer, longer positions. Exactly
what E&M's "put stops where they're hard to get to" is supposed to do.

### Consistency, which #84 could not demonstrate

`#84` found the edge magnitude-driven and inconsistent: 54% of windows, **66%
of symbols** (≈21 of 32), sign test never significant. On the held-out set it
is **51–52 of 61 symbols (84–85%)**, which under a fair coin is about one in
ten million. Same statistic, three times the symbols, and a far stronger
answer.

This does **not** overturn #84's window-level result — a symbol can be net
positive while only half its sub-periods are, and those are different
granularities. What is new is that at **symbol** level the edge is broad rather
than tail-driven, where #84's 21/32 could not separate itself from chance.

## The secondary: it is not a period artefact

The held-out symbols carry ~16 years each against the original 32's 5.3, so
Part 1 pre-committed to reporting the post-2021 subperiod. Same direction,
smaller:

| comparison | side | per trade | t | total/symbol | t |
|---|---|---|---|---|---|
| B − A | LONG | +50.43 | +4.61 | +2,335 | +4.54 |
| B − A | SHORT | +17.11 | +1.33 | +460 | +1.23 |
| B − A | all | +38.59 | +4.38 | +2,796 | +4.11 |

Criterion 1 passes, criterion 2 fails again — and the short-side estimate is
*larger* here (+17.11), so the long-side reading does not improve on recent
data. The replication is a symbol effect, not a period effect.

## Standing

| | |
|---|---|
| #86's hypothesis | **refuted** out of sample — shorts are neutral, not harmful |
| long-only arm (C) | **do not ship** — a wash overall, significantly worse post-2021 |
| #85's TREND_DOWN −7.32 | **did not replicate**; it was 12 symbols of noise |
| EM-3's edge, out of sample | **replicates strongly and broadly** — +12,449 total per symbol, t = +6.60, 51/61 |
| EM-3's consistency | **demonstrated at symbol level**, where #84 could not |
| the shipped default | still ATR — see below, this is not mine to change |

## Two things this does NOT establish, and one new item

**1. Everything above is GROSS.** `#80` fixed the metric at gross because
commission was 1.8× the result it measured. A shipping decision needs **net**,
and I did not measure it. The direction is favourable — arm B takes 23% fewer
trades, so fewer commission legs — but "favourable direction" is not a number,
and this project has been burned four times by exactly that kind of inference.
Registered as **#101**, not asserted here.

**2. Changing the default is a user-visible decision, not a measurement.**
`harness.py` already notes that the live recommendation path consults these
verdicts and that changing it "needs its own decision — see Backlog #83". The
evidence for revisiting ATR is now much stronger than when #63 concluded
"default stays ATR", and that is what #101 carries: the net figure plus the
owner's call. I am not flipping a shipped stop rule on a gross backtest.

Also unchanged: this is one market and one era. 61 symbols of Vietnamese
equities 2004–2026 is a strong replication *within* that market, not evidence
about E&M's procedure in general.

## Reproducing

```bash
cd stock_microservices/services/decision-helper-service
PYTHONPATH=. python3 tests/em3_long_side_study.py     # ~60 min, 61 symbols x 3 arms
PYTHONPATH=. python3 -m pytest tests/test_long_only_basing_point.py -q
```
