# Design — Review Intelligence

> ⚠️ **SUPERSEDED 2026-08-27 — this design depends on a local chat model, and Ollama is being removed.**
> The deploy target cannot run a model (see [`05-price-intelligence.md`](./05-price-intelligence.md) §1–§2).
> It was never built. Aspect tagging by keyword lexicon is the deterministic substitute worth considering, since it needs no generation.
> Reopening it needs a hosted API or a deterministic substitute — both discussed in `05` §2.3.

**Status:** design only, no feature code written
**Date:** 2026-08-18
**Prerequisite reading:** [`00-codebase-assessment.md`](./00-codebase-assessment.md) §5, and **[`02-listing-optimizer.md`](./02-listing-optimizer.md) §3** for the shared `ai-service` foundation. This document covers only what is specific to review intelligence.
**Ranked:** #3 of six candidates (assessment §7)

---

## 1. Problem & seller value

A seller with sixty reviews across a dozen products has an average star rating and nothing else. The rating tells them buyers are moderately happy; it does not tell them that four separate people mentioned a mug arriving chipped, that the glaze colour reads differently from the photos, or that everyone who mentions packaging is delighted. Those themes are the actionable content, and they are buried in free text that nobody rereads. Review intelligence extracts per-review sentiment and aspects — quality, shipping, packaging, accuracy-to-photo, value, communication — then aggregates them per seller and per product into a ranked list of what buyers praise and what they complain about, with the actual review quotes behind each theme. It also flags reviews that warrant a reply and drafts one. The seller stops guessing which product to fix first.

**Why it ranks third:** the data structure is the cleanest in the schema, but the feature is worthless until reviews accumulate. It is cheap to build now and switches on by itself as volume arrives.

---

## 2. Data contract

### Reads (all existing)

| Source | Fields | Used for |
|---|---|---|
| `reviews` | `rating`, `title`, `comment`, `created_at`, `product_id`, `seller_id`, `is_verified_purchase`, `is_approved`, `seller_response`, `seller_response_at` | The corpus; response drafting |
| `products` | `name`, `category_id`, `material`, `technique` | Grouping themes by product and category |
| `users` | `full_name` | Addressing the reviewer in a drafted response |
| `orders` | `delivered_at` | Time-to-review, and separating delivery complaints from product complaints |

`reviews` is trustworthy in a way most review corpora are not: creation requires the reviewer to own the referenced `order_id`, and `is_verified_purchase` defaults true (`services/product/app/routers/reviews.py`). Every row is a real buyer of that item — no filtering for fake reviews is needed.

### New data to capture

One new table. Unlike the other two features, review analysis is **not** a suggestion the seller accepts, so `ai_suggestions` is the wrong shape for the analysis itself (it is still used for *drafted responses*).

```sql
CREATE TABLE review_analysis (
  id             BIGINT AUTO_INCREMENT PRIMARY KEY,
  review_id      INT          NOT NULL,

  sentiment      VARCHAR(20)  NOT NULL,   -- 'positive' | 'neutral' | 'negative' | 'mixed'
  sentiment_score DECIMAL(3,2) NULL,      -- -1.00 .. 1.00
  aspects        JSON         NOT NULL,   -- [{aspect, sentiment, quote}]
  summary        VARCHAR(255) NULL,       -- one-line gist
  needs_response BOOLEAN      NOT NULL DEFAULT FALSE,

  model          VARCHAR(80)  NOT NULL,
  prompt_version VARCHAR(20)  NOT NULL,
  created_at     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,

  UNIQUE KEY uq_review_analysis (review_id, prompt_version),
  INDEX ix_ra_review (review_id),
  INDEX ix_ra_sentiment (sentiment, created_at),
  INDEX ix_ra_needs_response (needs_response)
);
```

`aspects` JSON:

```jsonc
[
  { "aspect": "shipping",  "sentiment": "negative", "quote": "took nearly three weeks to arrive" },
  { "aspect": "quality",   "sentiment": "positive", "quote": "the glaze is beautiful" },
  { "aspect": "packaging", "sentiment": "negative", "quote": "only newspaper around it" }
]
```

Storing the **verbatim quote** with each aspect is what makes the feature credible rather than another opaque summary. Every theme in the UI drills into the buyer's own words, so a seller can verify any claim the panel makes.

**`UNIQUE (review_id, prompt_version)` is the key design decision.** A review's text never changes, so its analysis is computed **once and stored forever** — no repeated LLM cost, no cache expiry, no recomputation on every dashboard load. Bumping `prompt_version` re-analyses under a new key without destroying the old rows, so the two can be compared.

Aggregates are **not** stored. They are a `GROUP BY` over `review_analysis` joined to `reviews`, cached in Redis for minutes. Persisting aggregates would add invalidation logic for a query that is cheap.

**Migration:** `migrations/versions/2026_XX_XX_add_review_analysis.py`, chained after `ai_suggestions`. Model in `shared/models/ai.py`, registered in `shared/models/__init__.py`.

**Reliability class:** TELEMETRY-like — a failed analysis write must never break the reviews screen. It is retried on next view.

---

## 3. Architecture

Uses the `ai-service` from `02-listing-optimizer.md` §3, adding `routers/reviews.py`. `product-service`, which owns the reviews API, is **not modified**.

### Lazy batch — the pattern that works without a scheduler

There is no job runner (assessment §3), so analysis is triggered by seller demand:

```
seller opens the Reviews / Insights tab
        |
        v
GET /api/v1/ai/reviews/insights?seller_id=me
        |
        +-- Redis aggregate cache hit? -> return (typical case)
        |
        +-- miss:
              +-- find this seller's reviews with no row in review_analysis
              |     for the current prompt_version   (LEFT JOIN ... IS NULL)
              +-- analyse up to BATCH_MAX (default 25) of them, newest first
              +-- persist each to review_analysis
              +-- aggregate in SQL, cache, return
                    + `pending_analysis: N` if more remain
```

Cost is bounded per request and amortised across visits. A seller with 200 unanalysed reviews gets full coverage over several visits, with the newest — the ones they care about — done first. The response reports `pending_analysis` honestly rather than implying full coverage.

**When a scheduler exists** (see `01-instrumentation.md`), move analysis to review-creation time and this endpoint becomes a pure read. The lazy path stays as the backfill mechanism. The design is deliberately built so adding a scheduler is an optimisation, not a rewrite.

| Option | Verdict |
|---|---|
| **Lazy batch on seller view** | **Chosen.** No new infrastructure; cost follows actual usage. |
| Nightly cron | Blocked — no scheduler. Preferred once one exists. |
| Analyse synchronously on review creation | Rejected: would put a 3s LLM call in the buyer's review-submit path, in a service that must not depend on the AI service being up. |

---

## 4. Model & approach

**Self-hosted Ollama**, `qwen2.5:14b`, same client. Two distinct tasks:

### 4.1 Per-review extraction (the analytical core)

Classification and span extraction over one short text — comfortably within a 14B model, and the most reliable thing an LLM does here. `temperature=0.1`: this is extraction, not writing, and it must be reproducible.

The **aspect taxonomy is closed and fixed**:

```
quality · shipping · packaging · accuracy_to_photo · value_for_money ·
communication · craftsmanship · durability · other
```

A fixed taxonomy is what makes aggregation possible. An open-vocabulary model would return "delivery", "shipping", "postage", and "arrived late" as four distinct themes and the counts would be meaningless. `other` catches the genuine long tail without polluting the main axes.

Each aspect's `quote` must be a **verbatim substring of the review**. This is validated in post-processing — a quote that does not appear in the source text is dropped, which converts the most likely hallucination into a silent, harmless omission.

### 4.2 Response drafting (secondary)

For reviews flagged `needs_response` (negative or mixed sentiment, no existing `seller_response`), draft a reply the seller can post. Same suggest-draft pattern as the chat copilot, stored in `ai_suggestions` with `feature='review_intelligence'`, `entity_type='review'`. `temperature=0.4`.

### Cold start — handled explicitly, and it matters here

Themes extracted from four reviews are noise presented as insight. The endpoint therefore returns a **coverage state** the UI must respect:

| Analysed reviews | State | UI behaviour |
|---|---|---|
| 0 | `no_data` | "No reviews yet." Nothing else. |
| 1–9 | `insufficient` | Show individual review sentiment only. **No themes, no percentages, no trends.** |
| 10–24 | `emerging` | Themes shown, explicitly labelled provisional, with counts not percentages |
| 25+ | `sufficient` | Full theme ranking, trends, comparisons |

**This directly fixes a live problem.** `InsightsPanel.jsx` currently ships hardcoded fake insights as its fallback — literal strings like *"🚀 Your sales are trending upward this month with 15% growth"* and *"📉 Product views are down 8%"* — rendered whenever real data is unavailable. Worse, `sellerAnalyticsService.generateInsights()` fires *"📈 Low conversion rate. Consider improving product presentations."* for **every seller, always**, because it thresholds on `conversion_rate < 2` and `conversion_rate` is hardcoded to `0` server-side (assessment §5). Replacing that panel's contents with genuine, coverage-gated insight is part of this feature's scope, not a side effect.

Never fabricate a theme to fill space. An honest "not enough reviews yet" is the correct output and is what earns trust in the numbers once they do appear.

### Serving

Per-review analysis: batch, lazy, persisted once. Aggregates: SQL + Redis, TTL 15 minutes. Response drafts: realtime on demand.

---

## 5. New backend endpoints

Seller JWT required; every query scoped to `reviews.seller_id == current_user.id`.

### `GET /api/v1/ai/reviews/insights`

```
?days=90&product_id=<optional>
```

```jsonc
// 200
{
  "coverage": {
    "state": "sufficient",
    "reviews_total": 64,
    "reviews_analysed": 64,
    "pending_analysis": 0,
    "period_days": 90
  },
  "sentiment": { "positive": 47, "neutral": 9, "negative": 8, "average_rating": 4.3 },
  "themes": [
    {
      "aspect": "packaging",
      "sentiment": "negative",
      "mentions": 7,
      "trend": "up",
      "example_quotes": [
        { "review_id": 812, "quote": "only newspaper around it", "rating": 2 },
        { "review_id": 844, "quote": "arrived chipped, poorly wrapped", "rating": 3 }
      ],
      "affected_products": [ { "product_id": 42, "name": "Cobalt Blue Vase", "mentions": 4 } ]
    },
    {
      "aspect": "craftsmanship",
      "sentiment": "positive",
      "mentions": 31,
      "trend": "stable",
      "example_quotes": [ { "review_id": 790, "quote": "the glaze is beautiful", "rating": 5 } ],
      "affected_products": []
    }
  ],
  "needs_response": [
    { "review_id": 812, "rating": 2, "created_at": "2026-08-14T11:02:00Z", "summary": "Item arrived chipped due to thin packaging" }
  ]
}
```

Negative themes are returned first — the seller's scarce attention should land on what is broken.

### `GET /api/v1/ai/reviews/{review_id}/analysis`

Single-review sentiment, aspects and quotes. `202` with `{"status":"pending"}` if not yet analysed.

### `POST /api/v1/ai/reviews/{review_id}/draft-response`

```jsonc
// Response
{
  "suggestion_id": 3301,
  "review_id": 812,
  "draft": "I'm really sorry the vase arrived chipped, Mai...",
  "tone": "apologetic",
  "grounded_on": [ { "source": "review", "field": "comment" } ],
  "model": "qwen2.5:14b",
  "latency_ms": 3100
}
```

### `POST /api/v1/ai/reviews/suggestions/{suggestion_id}/resolve`

Same contract as the other features. **Does not post the response** — the client writes it through the existing `PUT /api/v1/reviews/{review_id}`, so `seller_response` and `seller_response_at` are set by the service that owns them.

---

## 6. Frontend touchpoints

| File | Change |
|---|---|
| `src/services/aiService.js` | Add `getReviewInsights`, `getReviewAnalysis`, `draftReviewResponse`. |
| `src/components/seller/InsightsPanel.jsx` | **Substantially rewritten.** Replace the hardcoded fallback strings with real, coverage-gated insight. When `state` is `no_data` or `insufficient`, render an honest empty state — **not** invented statistics. |
| `src/screens/seller/AnalyticsScreen.jsx` | Host the new review-themes section. |
| `src/components/seller/ReviewThemesCard.jsx` | **New.** Ranked themes, negative first, sentiment colour, mention counts, expand-for-quotes. |
| `src/components/seller/ReviewResponseSheet.jsx` | **New.** Drafted response with Use / Edit / Dismiss; posts via the existing review endpoint. |
| `src/services/sellerAnalyticsService.js` | Fix `generateInsights()` — the `conversion_rate < 2` branch fires for every seller because the backend hardcodes it to `0`. Either gate on real data (needs PR 3, `product_view_events`) or remove the branch. |
| `src/i18n/translations/{en,vi}.js` | New strings. |

**Note:** the quotes rendered in the UI are buyer-authored text. They are already shown publicly on product pages, so no new disclosure issue arises — but they must be rendered as text, never interpreted.

---

## 7. Guardrails

| Risk | Mitigation |
|---|---|
| **Fabricated themes from thin data** | Coverage gating (§4). Below 10 analysed reviews, no themes are shown at all. This is enforced server-side in the response, not left to the client. |
| **Hallucinated quotes** | Every `quote` must be a verbatim substring of the review; validated in post-processing and dropped otherwise. |
| **Misattributed sentiment** | Cross-check against the star `rating`. A 5-star review analysed as strongly negative (or vice versa) is flagged low-confidence and excluded from aggregates. The rating is ground truth the model cannot argue with. |
| **Delivery vs product confusion** | `shipping` and `packaging` are distinct aspects, and `orders.delivered_at` distinguishes "arrived late" from "made badly" — different fixes, different owners. |
| **Auto-posted responses** | **Never.** No endpoint in `ai-service` writes `seller_response`. Drafts only; the seller posts through the existing reviews API. |
| **Defensive or hostile drafts** | Response prompt constrains to acknowledge–apologise–offer-next-step. Post-filter blocks blaming the buyer, disputing the rating, or asking them to change it. Pressuring a reviewer is a marketplace-integrity issue, not just bad tone. |
| **Compensation promises** | Post-filter blocks generated refunds, replacements and discounts. The draft may say the seller will follow up; it may not commit money. |
| **Prompt injection in review text** | Review content is delimited untrusted data; extraction output is schema-validated. |
| **Cost** | Analysis is once-per-review-per-prompt-version, permanently. `BATCH_MAX` bounds per-request cost. Aggregates never call the model. |
| **Model down** | Insights endpoint returns already-analysed rows with a raised `pending_analysis`; the panel degrades to partial coverage rather than erroring. |

---

## 8. Rollout

### Flag

`AI_REVIEW_INTELLIGENCE_ENABLED`, default `false`, plus the Redis per-seller allowlist. When off, `InsightsPanel` keeps its current behaviour — **except** that the hardcoded fake insight strings should be removed regardless of this flag. Shipping invented statistics to sellers is a bug independent of this feature.

### Stages

1. **Internal, synthetic corpus** — seed 50–100 realistic ceramics reviews and verify the taxonomy is right and quote validation holds. This is the one feature that can be meaningfully evaluated pre-launch, because the corpus can be written by hand.
2. **Pilot, read-only insights** — no response drafting yet.
3. **Enable response drafting** — once theme quality is trusted.
4. **Default on** — automatic, since coverage gating means low-review sellers simply see an honest empty state.

### Measurement

| Metric | Source | Target |
|---|---|---|
| **Extraction precision** | Manual audit of 50 analysed reviews against a human label | **> 85%** aspect precision |
| Quote validity | Post-filter drop rate | **< 3%** dropped |
| Rating/sentiment agreement | `review_analysis.sentiment` vs `reviews.rating` | **> 90%** consistent |
| **Response draft acceptance** | `ai_suggestions.status` | **> 40%** |
| Seller response rate | % of negative reviews with `seller_response`, before vs after | The real outcome |
| Panel engagement | Theme expand events | Are themes read or ignored? |

Seller response rate on negative reviews is the business metric worth committing to: it is computable from existing columns (`reviews.seller_response_at`), needs no new instrumentation, and represents a genuine marketplace-health improvement rather than a proxy.

**Honest limitation:** precision requires a hand-labelled sample. Budget a few hours of human labelling — without it, "85% precision" is a claim rather than a measurement.

### Testing

`back_end/tests/ai/test_review_intelligence.py`, Ollama stubbed. Cover: coverage-state thresholds (especially that `insufficient` returns no themes), quote-substring validation, rating/sentiment cross-check exclusion, the blame and compensation denylists, `BATCH_MAX` bounding, idempotency of `UNIQUE (review_id, prompt_version)`, and seller scoping.

---

## 9. Open decisions

1. **Aspect taxonomy.** The nine aspects above are my proposal from the ceramics domain. Worth reviewing before implementation — changing it later means re-analysing the corpus under a new `prompt_version`. Should `gift_suitability` or `size_accuracy` be first-class?
2. **Coverage thresholds.** 10 / 25 reviews are judgement calls. Lower shows value sooner but risks noise; higher is more trustworthy but leaves early sellers with an empty panel for longer.
3. **Product-level vs seller-level default.** The endpoint supports both. Which should the panel open on? I lean seller-level with drill-down, since most sellers have few products.
4. **Buyer-facing review summaries.** The same analysis could produce "what buyers say" summaries on product pages — genuinely valuable, but it changes the risk profile completely (buyer-facing, public, affects purchasing). Explicitly **out of scope** here. Do you want it designed separately?
5. **Retroactive analysis at launch.** If there is a review backlog when this ships, the lazy path takes several seller visits to cover it. Acceptable, or worth a one-off backfill script?

---

## Cross-cutting note on the three features

All three share `ai-service`, the `ai_suggestions` table, the Ollama client, the flag mechanism, and the suggest-then-approve pattern. **Build them in the ranked order** — the listing optimizer establishes the foundation, and features 2 and 3 then add roughly a router, a prompt, and a schema each. Building any of them second-or-later is materially cheaper than building it first.

The single most important shared property: **`ai-service` has no write access to any business table.** It reads catalogue, chat and review data, and it writes only to its own `ai_suggestions` and `review_analysis` tables. Every change to a product, message or review still flows through the service that owns it, with that service's validation, authorisation and ledgers intact. That boundary is what makes all three features safe to ship behind a flag and trivial to switch off.
