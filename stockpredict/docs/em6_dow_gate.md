# EM-6 — the Dow multi-index confirmation gate: a measured negative

**Date:** 2026-10-20
**Backlog:** `#66` — **closed, not built**
**Design:** `docs/SRS_edwards_magee_dow_gate.md` · **Plan:** `docs/implementation_plan_em6_dow_gate.md`
**Code built:** `app/services/market_context/dow.py`, `dow_context.py` (50 tests)
**Study:** `tests/em6_gate1_study.py`
**Verdict:** **GATE 1 fails, 0 of 3 horizons, under every arm.** The pipeline
work (D4–D8) was never started, which is what the gate was for.

---

## The claim under test

E&M's tenet 8 is the one they call *most questioned, most durable*: **no valid
trend-change signal from one average alone.** Bassetti's 9th-edition revision
applies it to our exact problem — a narrow index cannot represent an economy,
so read the broad trend from three indices together and treat disagreement as
a hedge signal.

The plan made D3 a gate, ahead of any pipeline wiring, on one argument: **a
gate cannot improve signals by conditioning on a state that carries no
information about forward returns.** If the confirmed trend does not separate
forward returns, no amount of wiring changes that, and the remaining five
tasks are wasted.

> **Pre-registered criterion.** `TREND_UP`-confirmed days must beat
> `TREND_DOWN`-confirmed days at **two or more** of the 10/20/60-session
> horizons, date-clustered and non-overlapping. Significance requires **both**
> `|Welch t| > 1.96` **and** an episode-bootstrap CI excluding zero.
>
> On failure: stop, record the negative, close `#66`.

## Result

Universe of 92 symbols, 320,237 bars; lead VNINDEX 5,672 bars from 2004-01-05;
witnesses HNXINDEX and UPCOMINDEX.

**Primary — the confirmed (gated) trend, universe forward returns:**

| h | n up / dn | episodes | up | down | edge | Welch t | episode 95% CI | |
|---|---|---|---|---|---|---|---|---|
| 10 | 228 / 271 | 10 / 10 | +0.68% | +0.47% | +0.21% | 0.39 | [−1.04%, +0.99%] | ns |
| 20 | 117 / 138 | 10 / 10 | +1.10% | +1.02% | +0.08% | 0.08 | [−2.56%, +1.69%] | ns |
| 60 | 41 / 50 | 9 / 10 | +5.06% | +2.87% | +2.19% | 0.58 | [−5.86%, +7.42%] | ns |

**0 of 3. GATE 1 FAILS.** Not marginal — the largest `t` is 0.58, and every
interval straddles zero by several times the edge.

### And it is not the Dow rule's fault

Five further arms, all declared before running:

| arm | separates |
|---|---|
| ungated VNINDEX Dow trend, universe returns | **0 of 3** (edges *negative*: −0.07 / −0.45 / −1.80%) |
| gated Dow trend, VNINDEX's own returns | **0 of 3** (edges negative: −0.86 / −1.44 / −3.10%) |
| ungated Dow trend, VNINDEX's own returns | **0 of 3** |
| gated MA-regime proxy, universe returns | **0 of 3** (+0.15 / −0.01 / −0.30%) |
| ungated MA-regime proxy, universe returns | **0 of 3** (+0.97 / +1.31 / +0.97%, t = 1.65 / 1.12 / 0.30) |

So the negative is **not specific to Dow's rule**, which the plan's Q2 left
open: the shipped MA proxy fails too, and it fails with far more episodes
(46–53 against 9–10), so it is not merely underpowered.

### The finding that answers EM-6 directly

Compare the last two rows. The **ungated** MA regime carries the only hint of
separation in the whole study — +0.97% / +1.31% / +0.97%, consistent in sign,
`t = 1.65` at the shortest horizon. Requiring multi-index confirmation
**destroys it**: +0.15% / −0.01% / −0.30%, and the episode count falls from
~50 to ~36.

**Confirmation made it worse, not better.** That is a cleaner answer to EM-6's
question than a flat null would have been. The witnesses are not adding a
filter; they are removing turns that were, if anything, mildly informative.

## Why this is a real null and not just thin data

The honest constraint was named in the SRS before any of this ran, and it held:
**episodes, not observations, are the sample size.** The adopted trend changes
~21 times in 20 years, so the primary test rests on 9–10 episodes per arm, and
every p-value is reported beside that count.

But three things stop this being merely underpowered:

1. The MA arms carry **46–53 episodes** and still separate at 0 of 3.
2. The **signs are inconsistent** across arms — the ungated Dow trend's edges
   are negative, the ungated MA's positive. Noise looks like this; a real
   effect being missed for want of power does not.
3. The effect would have to be large to matter at all, because the gate's
   measured cost is a fifth to two-thirds of long signals (SRS §3.1). An
   effect too small to detect here is too small to pay for that.

## One tension worth recording rather than burying

In the *secondary* arm — gated Dow trend against VNINDEX's own returns — the
episode bootstrap excluded zero at h = 10 and h = 20 ([−1.77%, −0.22%] and
[−3.10%, −0.44%]) while `|Welch t|` stayed below 1.96. The two inference
methods disagreed.

It is reported `ns` because requiring both was pre-registered, and that rule
was fixed for exactly this situation. Three further reasons not to chase it:
it is a secondary arm, it rests on 10–11 episodes, and its **sign is
contrarian** — confirmed-UP preceding *lower* index returns. Building a
trend-confirmation gate on a contrarian reading would be incoherent, and
`#87` has already shown what happens to a contrarian finding from ten-ish
observations: EM-4's quintile result reversed outright on more data.

## What was built, and what it is good for

D1 and D2 shipped with 50 tests, and they stay — they are the measurement
apparatus, not dead code:

* `dow.py` — Dow's primary trend from successive confirmed swing highs *and*
  lows, closing prices only, tenet 12 honoured.
* `dow_context.py` — confirmation-gated adoption, the witness allow-list with
  its exclusion reasons, fail-open on an outage.

Nothing consumes them. `confirm()` is untouched, `BacktestConfig` is
unchanged, and no mode was added to the live pipeline — the default was `OFF`
and it never moved.

## What the detour was worth

Three things that outlive the null:

1. **The witness question, settled by measurement.** The register proposed
   VN30 as the second average. It is 0.965-correlated with VNINDEX and
   confirms with a median lag of 0 bars — it would have gated nothing.
   VNINDEX + HNXINDEX + UPCOMINDEX are pairwise 0.45–0.47 across three
   exchanges, which is the real structure and is recorded in the code.
2. **`k` has no resolution below ~10 bars on this market** — 25 of 35 turns
   confirm on day 0 and none in bars 1–5. A `{0,1,3,5}` sweep would have read
   "flat, the parameter does not matter".
3. **Strictness is stickiness.** `UNANIMOUS_3` at short `k` adopts five turns
   in twenty years and holds one state for ~15 years, producing *more* long
   exposure than no gate. A degeneracy criterion now sits beside the vacuity
   guard.

## Standing

| | |
|---|---|
| E&M tenet 8 on VN data | **no measurable separation**, at any horizon, under either trend rule |
| multi-index confirmation | **actively removed** what little the raw regime had |
| the gate | **not built** — D4–D8 never started |
| D1 + D2 | **shipped and tested** (50 tests), consumed by nothing |
| `#66` | **closed as a measured negative**, as EM-2 was |

Four E&M candidates have now been measured to a conclusion: EM-1 shipped,
EM-2 closed negative, EM-3 real but tail-driven and not consistent, EM-4's
headline overturned by more data, and EM-6 closed negative. The register's
remaining candidates are EM-5, EM-7 and EM-8 — and `#68` (EM-8) is the one
that measures machinery already shipped and in use.
