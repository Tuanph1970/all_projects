# Design — Listing Optimizer

**Status:** ✅ **backend implemented 2026-08-18** (foundation + listing optimizer, 33 tests passing). ✅ **frontend implemented 2026-08-19** (§6), covering both the create and edit paths.
**Not yet built:** the phase-2 vision model.
**Date:** 2026-08-18
**Prerequisite reading:** [`00-codebase-assessment.md`](./00-codebase-assessment.md) §5, [`01-instrumentation.md`](./01-instrumentation.md)
**Ranked:** #1 of six candidates (assessment §7)

> **This document also defines the shared `ai-service` foundation** — service boundary, auth, Ollama client, the `ai_suggestions` table, flags, and rate limits — because the listing optimizer ships first. [`03-chat-copilot.md`](./03-chat-copilot.md) and [`04-review-intelligence.md`](./04-review-intelligence.md) reference this section rather than repeating it.

---

## 1. Problem & seller value

A Mercai seller is a ceramic artisan, not a copywriter. They upload a photo, type "blue vase", set a price, and move on — leaving `material`, `technique`, `dimensions`, and `tags` empty, writing a two-line description, and picking a single dim photo. Those empty fields are exactly what the search endpoint matches against (`advanced_search` filters on `name`, `description`, `tags`, `material`, `technique`), so a sparse listing is close to invisible: it cannot be found by anyone filtering on material or technique, and it ranks on nothing. The optimizer takes the listing the seller actually wrote and returns a concrete, side-by-side improvement — a sharper title, a structured description, filled-in attributes, suggested tags, and a plain-language report on the photos — which the seller accepts, edits, or rejects field by field. The value is immediate and pre-launch: it works on the very first listing, before a single order or view exists, which is true of no other candidate feature.

**Why it ranks first:** it needs no historical data. It reads one product row and its images. Every other candidate needs behaviour we have not yet accumulated.

---

## 2. Data contract

### Reads (all existing)

| Source | Fields | Used for |
|---|---|---|
| `products` | `name`, `description`, `price`, `tags`, `material`, `color`, `technique`, `dimensions`, `weight`, `minimum_order_quantity`, `category_id`, `seller_category_id` | The listing to improve |
| `product_images` | `image_url`, `is_primary`, `order_index` | Photo quality report |
| `seller_categories` | `name`, `path`, `get_full_path_name()` | Taxonomy context in the prompt |
| `categories` | `name` | Global category context |
| `seller_profiles` | `store_name`, `store_tagline`, `specialties`, `about_us` | Brand voice, so suggestions sound like the seller |
| `products` (peers) | `name`, `tags`, `material`, `technique` of other **active** products in the same category | Vocabulary grounding — what this marketplace actually calls things |

Peer sampling is a deliberate cheap substitute for a trained model: sampling ~20 sibling listings in the same `category_id` gives the LLM the marketplace's real vocabulary ("stoneware", "raku", "wheel-thrown") instead of generic e-commerce filler.

### New data to capture

One new table, **shared by all three AI features**. It exists to answer the only rollout question that matters: *are sellers accepting these suggestions?*

```sql
CREATE TABLE ai_suggestions (
  id             BIGINT AUTO_INCREMENT PRIMARY KEY,
  seller_id      INT          NOT NULL,
  feature        VARCHAR(40)  NOT NULL,  -- 'listing_optimizer' | 'chat_copilot' | 'review_intelligence'
  entity_type    VARCHAR(40)  NOT NULL,  -- 'product' | 'chat_room' | 'seller'
  entity_id      INT          NULL,

  input_hash     CHAR(64)     NOT NULL,  -- sha256 of normalised input; cache key + dedupe
  suggestion     JSON         NOT NULL,  -- the full structured proposal
  status         VARCHAR(20)  NOT NULL,  -- 'proposed'|'accepted'|'partially_accepted'|'rejected'|'expired'
  accepted_fields JSON        NULL,      -- which fields the seller actually took

  model          VARCHAR(80)  NOT NULL,  -- e.g. 'qwen2.5:14b'
  prompt_version VARCHAR(20)  NOT NULL,  -- bump to invalidate cache + segment metrics
  latency_ms     INT          NULL,
  error          VARCHAR(255) NULL,      -- set when generation failed

  created_at     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  resolved_at    DATETIME     NULL,

  INDEX ix_ai_sugg_seller_feature (seller_id, feature, created_at),
  INDEX ix_ai_sugg_entity (entity_type, entity_id),
  INDEX ix_ai_sugg_hash (input_hash),
  INDEX ix_ai_sugg_status (feature, status, created_at)
);
```

`seller_id` carries **no foreign key**, matching the `search_logs` precedent from PR 1: these rows are analytics that should outlive the account, and the table takes high-frequency writes.

**Migration:** `migrations/versions/2026_XX_XX_add_ai_suggestions.py`, `down_revision = '2026_08_17_search_logs'` (the current head). Model in `shared/models/ai.py`, registered in `shared/models/__init__.py` so `create_all()` picks it up — the same pattern PR 1 used.

**Reliability class:** TELEMETRY for the `proposed` write (a failed insert must never block a suggestion being shown), but LEDGER for the `accepted` transition — acceptance is the metric the whole rollout is judged on, so it is written in the same transaction as the seller's action. See `01-instrumentation.md` for the distinction.

### Deliberately not captured

No copy of the product row is stored in the suggestion. `entity_id` + `created_at` is enough, and duplicating listing content into a JSON blob would create a second source of truth that immediately goes stale.

---

## 3. Architecture

### Service boundary

A **sixth microservice, `ai-service`, on port 8006**, behind Traefik at `PathPrefix('/api/v1/ai')`. It is the only service that talks to an LLM, and no existing service is modified to add AI logic.

```
                     +------------------------------+
  React Native  ---> | Traefik  :8002 -> :80        |
                     +------+-----------------------+
                            |  /api/v1/ai/*
                            v
                     +------------------------------+
                     | ai-service          :8006    |
                     |  routers/  listing.py        |
                     |            chat.py           |
                     |            reviews.py        |
                     |  services/ ollama_client.py  |
                     |            prompts/          |
                     +---+----------------------+---+
                         | SQLAlchemy           | HTTP
                         v                      v
                    MySQL (shared)      Ollama (host:11434)
                    Redis (cache)
```

**Why a separate service, concretely:** LLM calls are 3–10s and memory-hungry; putting them in `product-service` would tie up its thread pool and couple catalogue latency to model latency. The AI service also has a different dependency set (an HTTP client, prompt assets), a different scaling profile, and a different failure mode — it must be allowed to be down without taking the catalogue with it.

**Consistent with the existing topology, deliberately:** like every other service it reads the shared MySQL database directly via `shared/models` rather than calling sibling services over HTTP. That is the established pattern (assessment §3 — the `*_SERVICE_URL` env vars exist but no service actually calls another), and inventing a different one here would leave the codebase with two conventions instead of one. The trade-off is noted as an open decision in §9.

### Talking to it: synchronous, client-initiated

The React Native app calls `ai-service` **directly through Traefik**, exactly as it already calls `seller-service`. No existing FastAPI service calls the AI service at all in phase 1.

| Option | Verdict |
|---|---|
| **Sync HTTP, client-initiated** | **Chosen.** The seller taps "Improve this listing" and waits with a spinner. 3–10s is acceptable for an explicit, opt-in action. No new infrastructure. |
| Queue (Celery/Redis) | Rejected for phase 1. No queue exists (assessment §3); adding one to serve a single synchronous interaction is unjustified. Needed later for batch and proactive work. |
| Service-to-service call from `product-service` | Rejected. Would couple product-write latency to model latency and give the catalogue a new failure mode. |

### Compose entry

Follows the existing service definitions exactly:

```yaml
  ai-service:
    build:
      context: .
      dockerfile: services/ai/Dockerfile
    container_name: mercai_ai_service
    restart: unless-stopped
    extra_hosts:
      - "host.docker.internal:host-gateway"   # reaches Ollama on the host
    environment:
      - SERVICE_NAME=ai-service
      - SERVICE_PORT=8006
      - DB_HOST=${DB_HOST:-db}
      # ... same DB/Redis/SECRET_KEY block as the other five ...
      - OLLAMA_BASE_URL=${OLLAMA_BASE_URL:-http://host.docker.internal:11434}
      - OLLAMA_MODEL=${OLLAMA_MODEL:-qwen2.5:14b}
      - OLLAMA_TIMEOUT_SECONDS=${OLLAMA_TIMEOUT_SECONDS:-45}
      - AI_LISTING_OPTIMIZER_ENABLED=${AI_LISTING_OPTIMIZER_ENABLED:-false}
    depends_on:
      redis: { condition: service_healthy }
      db:    { condition: service_healthy }
    volumes:
      - ./services/ai/app:/app/app
      - ./shared:/app/shared
    networks: [mercai_network]
    labels:
      - "traefik.enable=true"
      - "traefik.project=mercai"
      - "traefik.http.routers.mercai-ai.rule=PathPrefix(`/api/v1/ai`)"
      - "traefik.http.routers.mercai-ai.entrypoints=web"
      - "traefik.http.services.mercai-ai.loadbalancer.server.port=8006"
      - "traefik.http.routers.mercai-ai.middlewares=ai-ratelimit@file"
```

New settings go in `shared/config.py` beside the existing `*_SERVICE_URL` block: `AI_SERVICE_URL`, `OLLAMA_BASE_URL`, `OLLAMA_MODEL`, `OLLAMA_TIMEOUT_SECONDS`, and one `AI_<FEATURE>_ENABLED` flag per feature.

**New dependency:** `httpx` (already pinned at `0.27.0` in `shared/requirements.txt`, currently unused at runtime) for the Ollama call. Nothing else — no LangChain, no vector store, no `numpy`.

---

## 4. Model & approach

**Self-hosted Ollama**, per the decision already taken. Default `qwen2.5:14b`.

The task is structured rewriting of a single short record, which a 14B instruct model handles well and which needs no fine-tuning. There is no training step and no dataset — this is prompt engineering plus schema validation, not machine learning.

### Serving: realtime, on demand

Seller-initiated, one product at a time, cached. There is no batch mode and no scheduler dependency.

**Structured output is mandatory.** The prompt requires a strict JSON object and the response is parsed into a Pydantic model; a response that fails validation is retried once at `temperature=0`, then reported as a failure. Free-text output is never shown to the seller, because every field has to map onto a specific form input.

```
POST {OLLAMA_BASE_URL}/api/generate
{
  "model": "qwen2.5:14b",
  "format": "json",          # Ollama-enforced JSON mode
  "stream": false,
  "options": { "temperature": 0.4, "num_predict": 900 },
  "prompt": "<system + listing + peer vocabulary + schema>"
}
```

`temperature=0.4` — high enough that descriptions do not read as boilerplate, low enough to stay factual about the object.

### Prompt structure

1. **Role** — an assistant helping a ceramics seller improve a marketplace listing; never invent facts about the object.
2. **Seller voice** — `store_name`, `store_tagline`, `specialties` from `seller_profiles`.
3. **The listing** — every current field, with empty ones explicitly marked `null` so the model knows what is missing rather than guessing it was omitted deliberately.
4. **Category vocabulary** — names/tags/materials/techniques sampled from ~20 sibling products.
5. **Output schema** — the exact JSON keys, each with a `rationale` string.

The **anti-fabrication rule is the most important line in the prompt**: the model may only propose `material`, `technique`, `dimensions`, or `weight` when the seller's own text or existing fields support it. Otherwise it must return `null` and add an `ask_seller` prompt — "What clay body is this?" — rather than inventing "stoneware". A marketplace that auto-fills wrong material data is worse than one with empty fields, because buyers filter on it and the seller never notices the lie.

### Images: deterministic first, vision model later

Phase 1 uses **Pillow only** (already a dependency, already used by `image_service.py`) for checks that need no model and cannot be wrong:

| Check | Rule |
|---|---|
| Resolution | Warn under 1000px on the long edge |
| Aspect ratio | Warn outside 0.6–1.7 (crops badly in `ProductCard`) |
| Count | Warn under 3 images |
| Primary set | Warn if no `is_primary` image |
| Brightness | Warn if mean luminance is outside a sane band |
| File weight | Warn over ~2MB (mobile data cost) |

**Phase 2 (open decision, §9):** a vision model (`qwen2.5-vl` or `llava`) for alt-text generation and subjective quality. Deliberately deferred — it roughly doubles model footprint and latency for a smaller share of the value than the text fields deliver.

### Cold start

There is none for the seller-facing path: the feature reads one product row. The only degradation is peer vocabulary — with fewer than ~5 sibling products the prompt omits that block and relies on general ceramics knowledge. That is a quality taper, not a failure.

### Caching

Redis, keyed on `sha256(product fields + prompt_version + model)`, TTL 24h, following the existing `CacheKeys` conventions in `shared/cache.py`. A seller who taps "Improve" twice without editing gets the cached suggestion instantly and burns no GPU. `prompt_version` in the hash means shipping a new prompt invalidates every cached entry automatically.

---

## 5. New backend endpoints

All under `ai-service`, all requiring a seller JWT via the existing `shared.security.get_current_user`, all enforcing `product.seller_id == current_user.id`.

### `POST /api/v1/ai/listing/suggest`

```jsonc
// Request
{ "product_id": 42, "fields": ["title","description","tags","attributes","images"] }  // fields optional, default all
```

```jsonc
// 200 Response
{
  "suggestion_id": 1381,
  "product_id": 42,
  "model": "qwen2.5:14b",
  "prompt_version": "v1",
  "cached": false,
  "latency_ms": 4120,
  "suggestions": {
    "name": {
      "current": "blue vase",
      "proposed": "Cobalt Blue Stoneware Vase - 24cm Hand-Thrown",
      "rationale": "Adds the material, size and technique buyers filter on."
    },
    "description": {
      "current": "a nice vase",
      "proposed": "A hand-thrown stoneware vase finished in a deep cobalt glaze...",
      "rationale": "Expands to cover form, glaze, care and dimensions."
    },
    "tags": {
      "current": "vase",
      "proposed": "vase,stoneware,cobalt,hand-thrown,home-decor",
      "rationale": "Matches vocabulary used across this category."
    },
    "attributes": {
      "material":  { "current": null, "proposed": "Stoneware", "rationale": "Stated in the seller's description." },
      "technique": { "current": null, "proposed": null, "ask_seller": "Was this wheel-thrown or slip-cast?" }
    }
  },
  "image_report": {
    "score": "needs_work",
    "findings": [
      { "severity": "warn", "code": "low_resolution", "message": "Main photo is 640px wide; aim for 1000px+.", "image_id": 91 },
      { "severity": "info", "code": "too_few_images", "message": "Listings with 3+ photos convert better. You have 1." }
    ]
  }
}
```

Every proposal carries `current` alongside `proposed` so the client renders a diff without re-fetching, and a `rationale` so the seller can judge it rather than trust it.

### `POST /api/v1/ai/listing/suggestions/{suggestion_id}/resolve`

Records the outcome. **Does not write to `products`** — the client applies accepted fields through the existing `PUT /api/v1/products/{id}`, so all validation, ownership checks, cache invalidation and the new `price_history` ledger keep working untouched.

```jsonc
// Request
{ "status": "partially_accepted", "accepted_fields": ["name","tags"] }
// Response
{ "suggestion_id": 1381, "status": "partially_accepted", "resolved_at": "2026-08-18T09:12:44Z" }
```

Separating *suggest* from *apply* is the core safety property: the AI service has **no write access to the catalogue**.

### `GET /api/v1/ai/health`

`{ "status": "healthy", "service": "ai", "ollama": "reachable", "model": "qwen2.5:14b" }` — used by the compose healthcheck and by the client to hide AI affordances when the model is down.

---

## 6. Frontend touchpoints

| File | Change |
|---|---|
| `src/services/aiService.js` | **New.** `suggestListing`, `resolveSuggestion`, `getAvailability` / `isListingOptimizerAvailable`, wrapping the existing `apiClient` (inherits auth, refresh, base-URL detection). |
| `src/constants/config.js` | Add `AI: '/api/v1/ai'` to `ENDPOINTS`. |
| `src/screens/seller/AddProductScreen.jsx` | Add an "Improve this listing" button, enabled once name + description are non-empty. On success open the review modal; accepted fields are merged into the existing `formData` state — the seller still presses Save, so nothing bypasses the existing submit path. **This one screen is the whole surface:** it is dual-purpose (`isEditMode = !!productId`), so the same affordance serves creating and editing. The request differs by mode — `{ product_id }` for a saved listing, `{ draft }` for one still being typed. Also gains `material`, `color`, `technique` and `dimensions` inputs: buyers filter on them and the optimizer proposes them, so the form has to be able to hold them. |
| `src/components/seller/ListingSuggestionModal.jsx` | **New.** Per-field diff cards (current vs proposed, rationale, Accept / Edit / Skip), an "Accept all" action, and the image report. Uses `react-native-paper`, consistent with existing seller components. |
| `src/components/seller/ImageQualityReport.jsx` | **New.** Renders `image_report.findings` with severity colours. |
| `src/i18n/translations/{en,vi}.js` | New strings — the app is fully bilingual and AI copy must not be the exception. |

**No new Redux slice.** Seller screens already hold their data in local `useState` (assessment §4); a suggestion is short-lived, screen-local state and adding a slice would break the established pattern for no benefit.

**Correction — `ProductFormScreen.jsx`.** An earlier draft of this table listed that file as the edit screen and gave it its own row. It was not the edit screen. It was registered in `MainNavigator` as `ProductForm` but **nothing in the repo ever navigated to it**, and it had drifted from the live screen (called `sellerService` directly, used `name` where the live form uses `title`, kept its own `errors` state) with no test covering it. Editing has always gone through `AddProduct` with a `productId` param (`ProductManagementScreen.jsx`). Wiring the optimizer into it would have added an LLM call to a screen no seller can open, so the file and its navigator entry were deleted instead. Kept here because a dead screen that looks live is exactly what misled this document.

---

## 7. Guardrails

**Human-in-the-loop is structural, not a setting.** The AI service cannot write to `products` at all — it has no such endpoint. Every change reaches the catalogue through the seller pressing Save on a form they can edit. There is no "auto-apply" mode and no config flag that could create one.

| Risk | Mitigation |
|---|---|
| **Fabricated attributes** | Prompt forbids unsupported values; must return `null` + `ask_seller`. Post-validation rejects any `material`/`technique` not present in the seller's text or the category vocabulary set. |
| **Hallucinated claims** ("dishwasher safe", "food safe") | Post-filter blocks a denylist of regulatory/safety claims from generated descriptions. Food-safety claims about ceramics carry real legal weight. |
| **Price manipulation** | `price` is not a field the optimizer may return. Pricing is a separate feature with a separate risk profile. |
| **Prompt injection via seller text** | Seller content is delimited and the system prompt states that content inside the delimiters is data, never instructions. Output is schema-validated, so an injected instruction cannot change the response shape. |
| **Cost / abuse** | Per-seller quota in Redis (default **20 suggestions/hour**, 100/day), returning `429` with `retry_after`. Plus a dedicated Traefik `ai-ratelimit` middleware — the existing `ratelimit` allows 1000/min, which is nonsense for LLM calls. |
| **Model down or slow** | `OLLAMA_TIMEOUT_SECONDS=45`, one retry, then `503` with a clear message. The button shows a disabled state driven by `/ai/health`. **A dead AI service must never block product creation or editing** — it is an additive affordance on an otherwise unchanged form. |
| **Concurrency** | A single Ollama instance serialises requests. Cap in-flight generations (semaphore, default 4) and shed load with `429` rather than queueing behind a long timeout. |

---

## 8. Rollout

### Flag

`AI_LISTING_OPTIMIZER_ENABLED`, default `false`, read from `shared/config.py`. When off, endpoints return `404` and `/ai/health` reports the feature as disabled so the client hides the button.

**Per-seller allowlist** for the pilot: a Redis set `mercai:ai:allowlist:listing_optimizer` of seller IDs. Redis is already a dependency and this needs no schema. (A per-seller flag *table* is the more durable answer — flagged as an open decision in §9.)

### Stages

1. **Internal** — allowlist of test sellers, seeded catalogue. Judge output against a rubric; there is no traffic to measure conversion against yet.
2. **Pilot** — 10–20 real sellers at launch. Watch acceptance rate.
3. **Default on** — if acceptance holds above target and there are no fabrication reports.

### Measurement

Everything below comes from `ai_suggestions` — which is why it is part of the feature, not an afterthought.

| Metric | Source | Target |
|---|---|---|
| **Acceptance rate** | `accepted` + `partially_accepted` over total proposed | **> 50%** |
| Field-level acceptance | Unnest `accepted_fields` | Identifies which suggestion types are weak |
| Listing completeness lift | % non-null `material`/`technique`/`dimensions`/`tags` for products with an accepted suggestion vs without | Direction positive |
| Failure rate | rows with non-null `error` | **< 2%** |
| p95 latency | `latency_ms` | **< 12s** -- *not met: measured 12.6s mean warm, see 8b* |
| Cache hit rate | `cached: true` share | Cost control |

```sql
SELECT prompt_version,
       COUNT(*)                                                        AS proposed,
       SUM(status IN ('accepted','partially_accepted'))                AS taken,
       ROUND(100 * SUM(status IN ('accepted','partially_accepted')) / COUNT(*), 1) AS pct,
       ROUND(AVG(latency_ms))                                          AS avg_ms
FROM ai_suggestions
WHERE feature = 'listing_optimizer'
GROUP BY prompt_version;
```

Because `prompt_version` is stored per row, prompt changes are measurable as a segment rather than a confound — the closest thing to an A/B test available without traffic.

**Honest limitation:** acceptance measures whether sellers *like* the suggestions, not whether listings *sell better*. Conversion lift needs `product_view_events` (PR 3, not yet built) plus real traffic. Do not claim conversion impact from acceptance data.

### Testing

Extends the pytest suite from PR 2 — `back_end/tests/ai/`, using the `load_service()` fixture (every service exposes a top-level `app` package, so only one is importable at a time). The Ollama client is stubbed; no test hits a model. Cover: schema validation, the anti-fabrication post-filter, the claims denylist, quota enforcement, cache-hit behaviour, and graceful `503` when Ollama is unreachable.

---

## 8b. Measured against a live model (2026-08-19)

Prompt **v3**, `qwen2.5:14b-instruct-q4_K_M`, idle RTX 3060 (12GB), 8 generations.

| Failure mode | Result |
|---|---|
| **Echo the input** (v1 failure) | **0 / 8** — fixed |
| **Fabricate a property or use** (v2 failure) | **1 / 4** on the sparsest listing |
| Latency (warm) | mean **12.6s**, range 10.4-14.3s |
| Latency (cold, model load) | ~20s first call |

**Echoing is solved.** v1 returned the seller's own text as its "improvement",
which the no-op filter then dropped, leaving nothing. v3 never did this.

**Fabrication is reduced but not eliminated, and it is common on sparse input.**
An initial 4-sample check suggested roughly 1 in 4; a larger 10-sample run showed
that estimate was far too low. Across sparse generations of
`"small bowl" / "earthenware bowl"`, **most invented something** -- *"perfect for
everyday use"*, *"simple yet elegant"*, *"crafted for everyday use"*. The 6-run
block scored **5/6 (83%)**.

The pattern is what the design predicted: with almost nothing true to say, the
model pads. Treat invention on near-empty listings as the **normal case**, not an
edge case.

Two measurement notes, because the first run overstated the problem:
- A naive "any word not in the input" check flags connectives like *standing*
  and *capacity* as fabrication. They assert nothing. The detector now separates
  neutral framing from **claim words** (uses, occasions, aesthetics, finishes).
- That claim-word denylist is directly reusable as the runtime free-text guard
  this document left open (see below).

### Guard verification (2026-08-19, end-to-end, live model)

The unsupported-claim guard was then run through the real pipeline -- prompt,
model, `validate_and_filter` -- rather than against hand-written strings.

| Input class | Runs | Flagged | Reading |
|---|---|---|---|
| **Sparse** (`"small bowl"` / `"earthenware bowl"`) | 6 | **5 (83%)** | Catches invention where it happens |
| **Rich** (full material, size, technique, finish) | 4 | **0** | **Zero false positives** |

The zero is the important half. A guard that fires on good output trains sellers
to dismiss every warning, and this one stayed silent on all four well-filled
listings -- including *"featuring a matte white glaze"*, which is not flagged
because the seller wrote "matte white glaze" themselves.

So the guard is well calibrated: it fires on invention and stays quiet on
legitimate rewording. **Flag rather than block remains correct** -- blocking a
sparse listing's description would delete the sentence and leave the seller with
nothing, whereas the flag hands them a specific claim to keep or cut.

**Follow-up worth considering:** the guard treats the symptom. The cause is that
the model is asked to write a description when there is almost nothing true to
say. A prompt rule returning *no* description below a content threshold -- with
an `ask_seller` question instead -- would address it at the source.

**The p95 < 12s target in section 8 is not met** at 12.6s mean warm. Either
revise the target to ~15s or accept that a 14B on this card sits just above it.
A 7B variant would likely meet it; quality at 7B is unmeasured.

---

## 9. Decisions taken

Confirmed 2026-08-18 — the recommended default was accepted for each. Any of
these can still be changed: 2 and 3 are config, 1 and 5 are additive, and only
the review taxonomy (see `04-review-intelligence.md`) gets expensive later.

| # | Decision | Taken |
|---|---|---|
| 1 | Vision model for images | **Phase 1 = Pillow heuristics only.** Deterministic checks that cannot hallucinate; a VLM is deferred. |
| 2 | Feature-flag mechanism | **Env var + Redis allowlist.** No schema. An *empty* allowlist means everyone, so flipping the global flag on visibly works. |
| 3 | Model | **`qwen2.5:14b`**, configurable via `OLLAMA_MODEL`. **Superseded 2026-08-22:** the running default is now `qwen2.5:3b-instruct-q4_K_M`, because the deploy target is RAM-constrained and the 14B (9.0GB) needs a GPU to be usable — 110s per suggestion CPU-only, past Cloudflare's 100s edge limit. The 3B is 1.9GB and 32s CPU-only, but is measurably weaker: on the same test listing it repeated the 14B's `vuốt tay` → "hand-built" error and promoted it into the product title. Revert when the hardware allows. |
| 4 | Ollama placement | **Docker host via `host.docker.internal`**, matching the `extra_hosts` pattern the other services already use for host MySQL. |
| 5 | Output language | **English only in phase 1.** Vietnamese generation needs quality verification before it is promised; the UI strings are still bilingual. |
| 6 | Shared-database access | **Yes — `ai-service` reads MySQL directly**, consistent with all five existing services. |

### Still genuinely open

- Vietnamese generation quality (blocks decision 5 being revisited).
- Whether a 7B variant is acceptable for lower latency — measure once real prompts run against the host.

## 9b. Original analysis (kept for reference)

1. **Vision model for images?** Phase 1 is Pillow-only heuristics. Adding `qwen2.5-vl` enables alt-text and subjective quality assessment, at roughly double the model footprint and latency. **Ship phase 1 first and decide on real feedback** — recommended.
2. **Feature-flag mechanism.** Env var + Redis allowlist is proposed because it needs no schema. A `feature_flags` table is more durable and auditable but is new surface area. Which do you want as the long-term answer?
3. **Model choice.** `qwen2.5:14b` is assumed from your prior benchmarking (3.7s/page). Worth confirming it is the model on this host, and whether a 7B variant is acceptable for lower latency.
4. **Ollama placement.** Assumed on the Docker host, reached via `host.docker.internal` (the pattern existing services already use for host MySQL). If it lives on another machine, `OLLAMA_BASE_URL` covers it — but GPU capacity and concurrency limits need confirming.
5. **English-only or bilingual output?** The app ships `en` and `vi`. Generating Vietnamese descriptions is a prompt change, but quality in Vietnamese needs checking before it is promised. Should the optimizer follow the seller's app language?
6. **Shared-database access.** `ai-service` reading MySQL directly matches every existing service. The stricter alternative — HTTP calls to `product-service` — would be a better boundary but would be the *only* place in the codebase doing it. Confirm you want consistency over purity here.

### Incidental finding

The Traefik `cors` middleware allowlists only `Content-Type`, `Authorization`, `X-Requested-With`. PR 1 introduced an `X-Anon-Id` request header. It works today because the services set `allow_headers=["*"]` at the FastAPI level and the `cors` middleware is not attached to the product router — but if that middleware is ever applied, anonymous search logging breaks silently at preflight. Worth adding `X-Anon-Id` to the list pre-emptively.
