# EM-4 — the Magee Evaluative Index

**Date:** 2026-10-20
**Code:** `decision-helper-service/app/services/breadth/mei.py`
**Study:** `tests/em4_mei_study.py` · **Tests:** `tests/test_mei.py` (13)
**Verdict:** the measure ships as evidence. **E&M's bottoms claim is untestable
on this data, and the exposure governor the register proposed is weakly
contra-indicated — it points the wrong way.**

---

## What was built

Magee's construction, verbatim in method (Ch 38): keep daily charts on a
universe, mark each **+** or **−** by its major trend, total them — *"if 75
are plus, the market looks 75% Bullish to you."* His premise is a statistical
demolition of the averages: of ~700 stocks around 1929, *"only 27% of the
stocks acted the way everybody knows all stocks acted."*

`compute_regime` stands in for his eye — TREND_UP is his **+**. That
substitution is deliberate and it changes the measure's character: mechanical
and reproducible where his was expert and personal. He said as much himself —
the index *"is a reflection of the judgment and opinion of the person who is
maintaining it."*

Causal by construction: day *i*'s reading uses each symbol's bars up to day
*i* only, and a test appends future bars to assert no past reading moves. The
percentile window is strictly the past, because an "extreme" is only definable
against a distribution and using the whole series would be look-ahead.

Series: **1,282 readings, 2021-08-20 → 2026-10-13**, range 0–100%, mean 42.6%.

---

## (1) The measure behaves — descriptive, n = 1 event

| | |
|---|---|
| lowest readings | **0.0%** across 2022-05-30 → 2022-06-08 (0 of 32 bullish, 31–32 bearish) |
| proxy's actual low | 2022-11-15, with MEI at **3.1%** |

So breadth collapsed to nothing during the 2022 VN bear market and was still
at 3.1% at the basket's true low. E&M's descriptive claim is **consistent**
with what happened here.

One caveat visible in the same numbers: MEI first hit 0% in **early June
2022**, five months before the November low. That is E&M's own "too late /
too early" problem from the Dow-Theory chapters, now on the other foot — an
extreme reading marks a zone, not a date.

## (2) E&M's bottoms claim is untestable on 5.3 years

Forward proxy returns after a bottom-decile reading, non-overlapping samples
(consecutive days' forward windows overlap almost entirely, the trap `#79`
documented):

| horizon | n low | after low MEI | unconditional | edge | Welch t | |
|---|---|---|---|---|---|---|
| 10 | 11 | +0.28% | +0.37% | −0.10% | −0.08 | ns |
| 20 | 5 | +0.46% | +0.85% | −0.40% | −0.13 | ns |
| 60 | **2** | +8.53% | +2.71% | +5.81% | +2.00 | SIG |

**Criterion fails — 1 of 3 horizons, and that one has n = 2.** A significant t
on two observations is not evidence and is not quoted as any.

**This is underpowered, not refuted**, and the distinction matters. E&M's own
evidence was *"over 20 years, all major bottoms"* — a handful of events. 5.3
years of VN data contains **one** major bear market, so there is at most one
genuine major bottom to test against. Non-overlapping sampling then leaves 2
to 11 observations in the tail. The claim cannot be settled here either way,
and a longer history is the only thing that would settle it.

## (3) The better-powered question, and the finding that matters

An exposure governor scales commitments *with the reading*, so what it needs
is not a rare extreme but whether the reading carries information **across its
whole range**. Every observation is used instead of a tail, which makes a null
here informative rather than merely underpowered.

Forward proxy return by breadth quintile, non-overlapping:

| | MEI range | n | forward 60 sessions |
|---|---|---|---|
| Q1 | 3.1 – 6.2% | 3 | **+11.10%** |
| Q2 | 12.5 – 25.0% | 3 | +7.75% |
| Q3 | 31.2% | 3 | +5.99% |
| Q4 | 37.5 – 62.5% | 3 | −2.99% |
| Q5 | 71.9 – 87.5% | 5 | **−3.88%** |
| | top vs bottom | | **−14.99%, Welch t = −2.08 SIG** |

**Monotone decreasing across all five buckets.** Low breadth predicts *high*
forward returns; high breadth predicts *negative* ones. At 20 sessions it is
noise (top vs bottom −2.60%, t = −0.95, non-monotone).

### This contradicts the application the register proposed

The register's EM-4 entry, following Ch 38's **Use 1**, says to *"scale total
commitments to the reading — larger long exposure at 80% than at 53%"*. The
data points the **opposite** way: the periods that paid were the ones where
almost nothing was advancing.

E&M contain both readings and do not reconcile them:

* **Ch 38, Use 1** — pro-cyclical. Commit more when more charts are plus.
* **Ch 38, the 1985 market letter** — contrarian. *"All major stock market
  Bottoms have corresponded with extremely low MEI readings"*, and in the
  renewed-upswing regime *"Tops more extremely overbought"*.

The weak evidence available favours the **contrarian** reading, which is the
one the register did not propose building.

**So the exposure governor is not built.** Building the pro-cyclical version
would be shipping a mechanism the only available evidence argues against, and
building the contrarian version on 17 observations with n = 3 per bucket would
be worse — that is a monotone pattern across five tiny buckets at a marginal
t, exactly the shape that does not survive more data.

---

## Standing

| | |
|---|---|
| the measure | **built, causal, tested** (13 tests), ships as evidence |
| E&M's bottoms claim | **untestable** here — one bear market, 2–11 tail observations |
| the measure's behaviour | **consistent** with the claim descriptively, 0% through the 2022 decline |
| breadth → forward returns | **contrarian and monotone at 60 sessions**, marginal (t = −2.08, n = 3/bucket); noise at 20 |
| the register's exposure governor | **not built** — the proposed direction is contra-indicated |

Nothing consumes the MEI. It is a measurement, available on the payload of
whatever surfaces it next, and the first breadth measure the system has.

## What would change the answer

1. **More history.** The binding constraint on every number above. E&M spoke
   of 20 years; a VN series back to 2012 would give several bear markets
   instead of one.
2. **The real VN-Index**, cap-weighted, instead of an equal-weighted basket of
   the same 32 symbols the MEI is built from — the proxy and the measure are
   not independent, so this is currently a test of internal consistency, the
   weaker form of the claim.
3. **A wider universe.** Magee kept ~100 charts; 32 VN30 names in a market
   dominated by a few large caps is a thin reading of "the market", and the
   register flagged this risk before the work started.
