# Backlog #108 — does `sentiment_score` mean anything?

**Status: ANSWERED WITHOUT RUNNING THE PRICE STUDY. The score is decorative by
construction. #106 must not consume it as-is.**

Date: 2026-10-30. Scope: `news_events.sentiment_score` (news-service, DB
`stock_news`) against observed market reaction, via `event-reaction-lib`.

---

## 1. The question, and why the answer arrived early

#108 asked whether the LLM's `sentiment_score` ranks the observed reaction —
standardised abnormal return (SAR) over `[0,+1]` and `[0,+3]`. The protocol was
pre-registered first (§4) so the criterion could not be fitted to the result.

It was never run. Two independent findings make running it meaningless today,
and both are facts about the *input*, not about the price data:

1. **The score carries no information beyond a 3-level label** — it is a
   hardcoded constant per label, not a model output, and its middle value is
   `+0.5` rather than `0` (§2a, §2b). These two are the disqualifying findings;
   two further arguments in the first draft of this document were overstated
   and are corrected in §2c and §2d.
2. **There are 11 independent observations** — not 209 (§3).

Finding 1 alone is disqualifying: a variable with three values, two of which are
fixed constants, cannot be "calibrated" against anything. Finding 2 means that
even a perfect score could not have been validated on this data.

## 2. What `sentiment_score` actually is

The chain, confirmed by reading and then *running* the code:

```
company_poller → NewsClassifier.classify()            news-service
    → POST /stock_helper/api/v2/ai/news-analysis       ai-insights-service
        → analyze_news() → _call_llm() → prose
        → _analyze_sentiment(prose) → "bullish"|"bearish"|"neutral"
        → sentiment_score = 0.5 if neutral else (0.8 if bullish else -0.8)
```

`services/ai-insights-service/app/services/insights_service.py:522`.
news-service only passes the number through (`classifier.py:129`), so this is
the sole origin of every stored value.

**Four defects, in descending order of severity.**

**(a) The score is three constants.** It is derived *from* the label by a
ternary, so it adds exactly zero information. Observed across all 209 scored
events: `-0.8` (7), `+0.5` (165), `+0.8` (37) — three distinct values, no
variation within a label. The backlog's premise that this is "an LLM score in
[-1,1], already better than the 5-point scale the owner proposed" is **wrong,
and that claim was mine**. It is in fact *worse* than a 5-point scale: fewer
levels, and the spacing below is unjustifiable.

**(b) `neutral` scores `+0.5`, not `0`.** Any consumer reading the field as a
signed polarity reads 165 of 209 neutral items — 79% of the corpus — as
moderately **good** news. The spacing is also non-monotone in a way no scale
survives: `bad → neutral` is a gap of 1.3, `neutral → good` a gap of 0.3. So it
is not a signed score, and not even an ordinal scale with meaningful distances.
This is precisely the trap #106 §(1) warned about — "a scale with 'normal' in
the middle" — except the middle is not in the middle.

**(c) The label is a keyword count over the LLM's prose, not the LLM's own
judgement.** `_analyze_sentiment` (`insights_service.py:457`) counts
`bullish|buy|positive|growth|upside|strong|outperform` against
`bearish|sell|negative|decline|downside|weak|underperform`, needing a **margin
of 2** to leave neutral. So the model reads the news, forms an explicit view,
writes it out — and the view is then re-derived by counting seven words in its
own prose. That indirection is the defect: the judgement already exists and is
discarded.

**This is weaker than the first version of this document claimed, and the
correction is mine.** I wrote that the counter is "near-blind on Vietnamese
news", citing a test where clearly-bad Vietnamese prose returned neutral. That
test fed Vietnamese text *directly* to `_analyze_sentiment`, which is a path the
pipeline never takes: measured against the live endpoint, the LLM answers in
**English regardless of input language**, so the counter always sees English
analysis prose. The claim tested a function in isolation and then described it
as a property of the system. What does survive, measured: a single bearish
English word returns neutral (margin-of-2), so a mildly negative analysis lands
in the same bucket as no view at all.

I also explained the 79% neutral rate by that blindness. **That explanation was
wrong.** Inspecting the corpus, it is dominated by routine regulatory filings —
listing notices, offering reports, charter amendments, licence changes — which
genuinely *are* neutral. The rate is mostly a property of the corpus, not of the
rule.

**(d) The template fallback is reachable, but is not what runs.** `_call_llm`
falls through to `_generate_template_response`, whose fixed text contains **no
word from either list**, so it yields `neutral` → `+0.5` deterministically for
every item (verified by running it). The first version of this document treated
that as a live possibility for the stored data, on the grounds that
`ANTHROPIC_API_KEY` is empty and `OPENAI_API_KEY` is 35 characters. **Measured
since: OpenAI answers, and answers well** — a bearish test item returned
`bearish`/−0.8 with substantive prose. So the stored corpus is real LLM output
scored by the crude counter, not template constants. The defect is now a
*silent-degradation* risk rather than a description of the data: if the key
lapses, every item silently becomes `+0.5` and nothing records that it happened.
That is what makes provenance (§5.4) worth having.

## 2.1 What the label gets right

Stated because the first version of this document under-reported it. Judged
against the titles, the three-level label tracks real good/bad at the extremes:

- `bad` — tax penalty and arrears, a share-price slump the company had to
  address, quarterly earnings-variance explanations, a branch closure, a
  regulator revoking an operating approval.
- `good` — profit results, a 20% dividend, construction contract and highway
  tender wins.

So the **label** is useful and should not be thrown away. The failure is
everything downstream of it: the ternary at :522 that turns it into a number,
and the choice of `+0.5` for the middle. One real labelling error is visible
too — routine administrative filings (sustainability report, amended charter,
licence change, signing an audit contract) are labelled `good` rather than
neutral, which inflates the positive class.

## 3. The data could not support the study either

209 scored events is misleading. Events on the same symbol and day share one
reaction window, so the unit of observation is the **symbol-day**:

| | count |
|---|---|
| scored company events | 209 |
| **distinct symbol-days** | **11** |
| distinct symbols | 4 (ACB, DPG, POW, VND) |
| calendar span | 2026-09-10 → 2026-10-29 (~7 weeks) |
| `bad` events, all symbols | 7 |

Worse, 4 of the 11 symbol-days carry exactly 50 events each (ACB 10-29, DPG
09-30, POW 09-10, VND 09-28) — backfill batches stamped with one timestamp. So
the set is 4 bulk days plus 7 singletons. With 4 symbols over 7 weeks the
market-model residuals are also heavily cross-correlated, so the effective N is
below 11.

No criterion on 11 clustered observations with 7 negative cases distinguishes
signal from noise. Reporting any correlation from this would be the "numbers that
look like results" failure the darts trainer's 50-window floor exists to prevent.

## 4. Pre-registered protocol (unchanged, for when the gate in §5 is met)

Recorded before any price data was touched, and deliberately left as-is:

- **Unit**: symbol-day. Multiple same-day items collapse to one observation;
  polarity aggregates as the mean score, intensity as the count.
- **Timestamp discipline**: `ts_utc` is publication time. An item at or after
  the close is attributed to the **next** trading session. Day 0 is that session.
- **Reaction**: market-model abnormal returns via
  `event_reaction.returns.abnormal_returns`, alpha/beta estimated on
  `[-120, -21]` relative to day 0, which ends strictly before the event window
  (EC1, no leakage). SAR = CAR / sigma_AR from the estimation window only.
- **Windows**: `[0, +1]` primary, `[0, +3]` secondary. Fixed in advance.
- **Criterion** (fixed before looking): Spearman rank correlation between
  aggregated score and SAR over `[0,+1]`, two-sided, with the symbol-clustered
  p-value. Declared meaningful only if |rho| ≥ 0.15 **and** p < 0.05 **and** it
  survives dropping any single symbol.
- **Benchmark (C4)**: the same test with score replaced by the prior day's
  return (lag-returns). The score must beat it; `abnormal_returns` also returns
  the placebo-CAR distribution from sliding windows across the estimation region
  as the null.
- **The trap, pre-registered**: SAR is derived from the outcome. Valid for
  *calibrating* a text model and for ranking which event categories matter.
  **Never** as a feature predicting the same window.

## 5. Gate before this is worth running

All four must hold:

1. `sentiment_score` is a genuine graded magnitude, not derived from the label
   by a ternary — i.e. defect (a) is fixed.
2. `neutral` maps to `0`, and polarity is stored separately from intensity
   (#106 §1), so the two are not conflated in one field.
3. ≥ 200 distinct symbol-days, ≥ 20 distinct symbols, ≥ 30 observations in each
   of the good and bad classes — enough that dropping one symbol cannot move the
   verdict.
4. A field recording *how* each row was scored (model id / template fallback),
   so a mixed corpus is detectable rather than silently pooled.

## 6. Consequences for #106

**#106 is blocked, which is the outcome #108 existed to determine.** Feeding
`sentiment_score` to a model today would supply a feature that takes three
values, is `+0.5` for 79% of rows, and is signed the wrong way for "no strong
view" — a feature whose dominant value says *mildly good* when it means
*nothing happened*. That rests on §2a and §2b alone and does not depend on the
two corrected arguments.

**But the label is worth keeping (§2.1).** The fix is therefore smaller than
"replace the sentiment pipeline": ask the LLM for a graded score and stop
re-deriving one from its prose.

#106's own design holds up and is unaffected: separate intensity from polarity,
decay the impulse, use publication time, past covariates only. **Intensity —
article count per symbol-day with exponential decay — needs no sentiment at all
and is untouched by every defect above.** If #106 proceeds in any form before
the score is fixed, it should ship intensity only, with polarity withheld until
§5(1) and §5(2) are met.
