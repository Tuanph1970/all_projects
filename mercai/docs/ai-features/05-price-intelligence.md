# Design — Price Intelligence (scraper-based, no LLM)

**Status:** design. Supersedes the LLM-extraction approach recorded in the project notes.
**Date:** 2026-08-27
**Prerequisite reading:** [`00-codebase-assessment.md`](./00-codebase-assessment.md) §3 and §5, [`01-instrumentation.md`](./01-instrumentation.md) (the ledger/telemetry distinction and `price_history`, which this feature reads).

**Two decisions from the product owner drive this document:**

1. **No chat model, anywhere.** The remote server this stack is moving to cannot run Ollama. The dependency is removed from the codebase, not merely disabled.
2. **Prices are collected by a scraper**, from **URLs sellers paste themselves**. No automated multi-site crawling in this design.

---

## 1. What changes, and why the old plan cannot simply be ported

The previous approach was: fetch a competitor page, strip it to 2–4K tokens, hand the HTML to `qwen2.5` on Ollama, and get back structured JSON. Its selling point was that *one* extractor covered every site, so a new source never meant new selector code. It was benchmarked at 3.7s/page warm on a 12GB RTX 3060.

None of that survives contact with the new hardware. The already-deployed listing optimizer is the evidence: the 14B model does not fit the deploy target at all, and the 3B that replaced it takes **32s per call on CPU** and gets Vietnamese ceramics terminology wrong non-deterministically (`PLAN_WEEK_2026_08_24.md`, Finding 2). A price parser inherits every one of those properties, and price is a field where "confidently wrong, differently each time" is the single worst outcome — a fabricated competitor price is entirely plausible-looking and would drive a seller to change a real price.

So the LLM is not being swapped out reluctantly. On this hardware it was going to be slow, unavailable under memory pressure, and unauditable. **A deterministic parser fails the same way every time, which is the property that actually matters here.**

### The objection the LLM was answering, and the real answer

The original objection to scrapers was legitimate: *every new source means new selectors*. The answer is not a language model. It is **ordering the extraction so that the site-agnostic strategies run first** (§4). Four of the five tiers work on any site that follows a public standard — `schema.org` JSON-LD, Open Graph, embedded framework state — and only the fifth is per-site. In practice the long tail of Vietnamese storefronts (Shopify, WooCommerce, Haravan, Sapo) emits JSON-LD `Product` markup by default, because Google Shopping requires it.

Per-site work is therefore the exception, and when it *is* needed it is **a YAML file, not Python** (§4.5). Adding a source is a data change reviewable in a diff, not a deploy of new code.

### What this costs, stated plainly

| | LLM extraction | Extraction ladder |
|---|---|---|
| Runtime footprint | 1.9–9.0 GB model resident | ~50 MB RSS, two new pip deps |
| Latency per page | 3.7s warm / 32s on CPU / 110s for 14B | 0.3–1.5s, dominated by the remote site |
| Availability | Degrades under GPU or RAM contention | No shared resource to contend for |
| Auditability | Prompt + sampling; not reproducible | Every price traces to a literal substring |
| Coverage of an unknown site | High — reads the page like a person | Good where standards markup exists, **zero where it does not** |
| Failure mode | Plausible wrong number | Honest "could not read this page" |

**The last two rows are the whole trade.** We give up coverage on non-standard, JS-rendered pages and buy back a system that never invents a price. Given that the consumer of this data is a seller deciding what to charge, that is the correct direction — but §12 says what we do about the coverage we lose.

---

## 2. Phase 0 — removing Ollama — ✅ DONE 2026-08-27

This is a deletion, and it must land before any new code, or the new module inherits a dead dependency.

**Verified after the change:** all 9 containers healthy; `intel-service` reports
`{"status":"healthy","database":"connected","cache":"connected","features":{"price_intel":false}}`
both directly and through Traefik at `/api/v1/intel/health`; the old
`/api/v1/ai/health` route returns 404; `pytest tests/` is 37 passing (24
pre-existing + 13 new). No container has a route to the Docker host any more.

Two things came out differently from the plan below, both deliberate:

- **The optimizer's 33 tests were replaced, not just deleted.** They mocked
  `check_quota` and `consume_quota` out rather than exercising them, so the
  fail-open-on-Redis-outage behaviour that protects sellers was asserted
  *nowhere*. `tests/intel/test_guardrails.py` now asserts it, along with the
  empty-allowlist-means-everyone rule and hash stability across ruleset
  versions. Net test count fell from 57 to 37; net *meaningful* coverage of the
  surviving code went from zero to thirteen.
- **`image_report.py` is kept but currently unreachable** — it lost its only
  caller with the optimizer's router. Phase 1 mounts it alongside the price
  position router. Keeping Phase 0 a pure deletion is what made it safe to do
  in one pass.


### 2.1 What goes

| Path | Action |
|---|---|
| `services/ai/app/services/ollama_client.py` | **Delete.** The only file in the repo that talks to a model. |
| `services/ai/app/services/listing_optimizer.py` | **Delete.** |
| `services/ai/app/prompts/listing.py`, `prompts/` | **Delete.** |
| `services/ai/app/routers/listing.py` | **Delete.** |
| `services/ai/app/schemas/listing.py` | **Delete.** |
| `services/ai/app/services/guardrails.py` | **Keep, trim.** `feature_enabled`, `check_quota`, `consume_quota`, `input_hash` are model-agnostic and are reused verbatim by this feature. The claim post-filters (`find_blocked_claims`, `find_unsupported_claims`, `strip_blocked_sentences`) only make sense against generated copy — delete them with the optimizer. |
| `services/ai/app/services/image_report.py` | **Keep, unchanged.** It is Pillow-only ("these checks cannot hallucinate: every finding is a measurement") and has no model dependency. It is the one piece of seller value the ai-service can keep shipping today. |
| `shared/config.py` — `OLLAMA_BASE_URL`, `OLLAMA_MODEL`, `OLLAMA_TIMEOUT_SECONDS`, `AI_MAX_CONCURRENT_GENERATIONS` | **Delete.** |
| `shared/config.py` — `AI_LISTING_OPTIMIZER_ENABLED`, `AI_CHAT_COPILOT_ENABLED`, `AI_REVIEW_INTELLIGENCE_ENABLED` | **Delete.** All three features they gate are LLM designs (§2.3). |
| `docker-compose.yml` — the `OLLAMA_*` env block, `extra_hosts: host.docker.internal` | **Delete.** The container no longer needs a route to the host. |
| `back_end/scripts/fix-ollama-host-binding.sh` | **Delete.** Its entire purpose was reaching the host's Ollama. The snap-vs-native lesson it encodes is recorded in the project notes and does not need to live in this repo. |
| `front_end/src/services/aiService.js`, the `AI_LISTING_*` entries in `constants/config.js`, and the suggestion UI in `screens/seller/AddProductScreen.jsx` | **Delete.** Nothing is published yet, so no client in the field breaks. |

The `ai_suggestions` table **stays**. It holds the optimizer's real rollout history, it is feature-keyed and generic, and this feature writes to it (§7.3). Dropping it would throw away the only evidence of what sellers did with the suggestions they were shown.

### 2.2 Rename `ai-service` → `intel-service`

Recommended, and this is the cheapest moment it will ever be: nothing is published, the mobile app has never been built against the live hostname, and the service is about to lose the only thing that made "ai" accurate.

Leaving a service called `ai-service` that contains no AI is a naming lie every future reader pays for. The change is mechanical and confined:

- `back_end/services/ai/` → `back_end/services/intel/` (Dockerfile path, `COPY services/ai/app` lines)
- `docker-compose.yml`: service key, `container_name`, `SERVICE_NAME`, the three Traefik labels, and the `ai-ratelimit@file` middleware reference
- `traefik/` dynamic config: rename the `ai-ratelimit` middleware
- `shared/config.py`: `AI_SERVICE_URL` → `INTEL_SERVICE_URL`, `http://intel-service:8006`
- `front_end/src/constants/config.js`: `/api/v1/ai` → `/api/v1/intel`
- `back_end/scripts/health_check.py`

Port 8006 and the container's health endpoint pair (`/health` for orchestration, `/api/v1/intel/health` for the client) are unchanged.

**If the churn is not wanted, the whole design works unchanged under the existing name and prefix.** Everything below refers to `intel-service`; substitute `ai-service` throughout and nothing else moves.

### 2.3 The consequence nobody should discover later

`02-listing-optimizer.md`, `03-chat-copilot.md` and `04-review-intelligence.md` are **all** LLM designs, and all three name the Ollama client as their shared foundation. Dropping the model does not shelve one feature — it shelves the entire designed AI roadmap.

That is a real cost and it should be recorded as one. Each of the three docs gets a status banner pointing here. Two honest paths remain open for them later, and neither needs deciding now:

- a **hosted API** (network call, no local hardware, per-token cost, data leaves the host) — the `ollama_client.py` seam was well-drawn and a hosted client would slot into the same shape;
- **deterministic substitutes** for the parts that do not need generation — review *aspect* tagging by keyword lexicon rather than a model, listing completeness checks by rule rather than by rewrite. Weaker, free, and they never hallucinate.

Price intelligence is unusual among the four in that it **never needed generation in the first place**. It needs extraction, arithmetic, and a ranking. That is why it is the one that survives this decision intact, and why it is the right next feature.

---

## 3. The feature

**For a seller looking at one of their own products: where does my price sit, and who moved?**

Three panels on one screen:

1. **Market position** — median, p25 and p75 of comparable prices, the seller's own price marked against them, and a plain-language label (*below market* / *in range* / *above market*).
2. **Comparables** — the competitor listings this position was computed from: internal Mercai listings, plus any external URLs this seller pasted, each with its price, when it was last checked, and how confident we are that we read it correctly.
3. **Movement** — the seller's own price history (exact, from the `price_history` ledger) and each comparable's observed prices over time.

**Framing is a design constraint, not copy.** The screen says *"here is the market"*, never *"you are overpriced"*. Artisan sellers price on materials, hours and reputation, and a system that scolds them for being above median is wrong about their business and will be switched off. The label is positional; the interpretation stays with the seller. The feature is opt-in per seller and gated by the existing allowlist machinery.

---

## 4. The extraction ladder

The replacement for the model. Given fetched HTML, produce `(price, currency, confidence, evidence)` or an honest failure.

All applicable tiers run, then results are **reconciled** (§4.6). Running them all is affordable — the whole ladder is microseconds against a page we already paid a network round-trip for — and cross-tier agreement is the cheap ensemble that buys back much of the LLM's judgement.

### 4.1 Tier 1 — JSON-LD (`schema.org/Product`) · base confidence 95

Parse every `<script type="application/ld+json">`, walk the graph for `@type: Product`, read `offers.price` and `offers.priceCurrency`. Handle `offers` as object, array, or `AggregateOffer` (`lowPrice`/`highPrice` → a range, §5.3).

This tier alone covers Shopify, WooCommerce, Haravan, Sapo, most Nuxt/Next storefronts, and anything whose owner wants Google Shopping placement. It is a published contract, it is machine-authored, and it is the single highest-yield strategy — which is exactly why it runs first.

### 4.2 Tier 2 — Microdata and meta tags · base confidence 90

In order: `<meta property="product:price:amount">`, `og:price:amount`, `<meta itemprop="price">`, `[itemprop=price][content]`. Currency from the sibling `*:currency` tag, else the adapter default.

Nearly free once the DOM is parsed, and it catches an older generation of templates that predate JSON-LD.

### 4.3 Tier 3 — Embedded framework state · base confidence 75 (90 with a configured key path)

Extract and parse `__NEXT_DATA__`, `window.__NUXT__`, `window.__INITIAL_STATE__`, and `application/json` script payloads. Then either follow an adapter-supplied key path, or — with no adapter — walk the object for keys matching `^(final_|sale_|current_|selling_)?price(_min|_max)?$` at a bounded depth.

**This tier is where a silent wrong price is most likely**, because a blind key walk will happily return `originalPrice`, `shippingFee`, or a variant that is out of stock. Two rules contain it:

- keys matching `original|list|msrp|compare_at|strike|before|shipping|fee|tax` are excluded outright;
- an unconfigured walk never scores above 75, which is **below the alert threshold** (§8.3). It can be displayed, with its evidence visible; it cannot make the system tell a seller they are being undercut.

### 4.4 Tier 4 — Adapter CSS selectors · base confidence 90

A CSS selector from the host's adapter file. Precise where it exists, and the natural place to encode a site whose markup we have actually looked at.

### 4.5 Tier 5 — Visible-text currency regex · base confidence 55

Last resort. Scan text nodes for Vietnamese price patterns (§5), preferring matches near the `<h1>` and discarding anything inside a `<del>`, `<s>`, or an element whose class matches `original|old|strike|compare`.

**Never used alone to fire an alert.** It is there so the screen can show *something* with a visible "we are not sure we read this correctly" marker, rather than a blank.

### 4.6 Reconciliation

```
candidates = [t for t in (T1..T5) if t.matched]

if not candidates:                      -> failure: no_price_found
if len(candidates) == 1:                -> that candidate, at its base confidence
if the top two agree within 0.5%:       -> higher-precedence one, confidence = 99
if they disagree:                       -> higher-precedence one,
                                           confidence = base - 25, flag `tier_conflict`
```

Two independent standards-based tiers agreeing is strong evidence. Disagreement usually means a sale price versus a list price, which is precisely the case where an alert should not fire.

### 4.7 Evidence — verbatim grounding, kept

The LLM design's most important rule survives, because it turns out not to have been an LLM rule at all: **whatever number we return, we must be able to point at the literal substring of the fetched bytes that produced it.** Every observation stores `raw_snippet` (±80 chars around the match), the tier, and the JSON path or selector.

Against the model this was anti-hallucination. Against the ladder it is diagnosis: when a seller reports a wrong price, the snippet says immediately whether the parser grabbed a shipping fee, a strike-through, or a variant. Without it, a wrong price is a mystery. The check is nearly free and it should be an assertion in code, not a convention.

### 4.8 Layout

```
services/intel/app/services/
  fetcher.py            SSRF-safe GET, robots, per-host rate limit
  money.py              Vietnamese price string -> (Decimal, currency)
  adapters.py           loads adapters/*.yml; derives the host allowlist
  extract/
    __init__.py         run_ladder(html, url, adapter) -> Extraction
    jsonld.py  meta.py  state.py  selectors.py  text.py
services/intel/app/adapters/
  _defaults.yml  tiki.vn.yml  ...
```

An adapter is data:

```yaml
host: tiki.vn
currency: VND
tiers: [jsonld, meta, state, selectors, text]   # order, and what to skip
state_paths:
  - props.pageProps.initialData.product.price
selectors:
  price: ".product-price__current-price"
  title: "h1.title"
  unavailable: ".out-of-stock"
```

**New dependencies: `beautifulsoup4` and `lxml`.** Nothing else — JSON-LD is `json.loads`, robots is `urllib.robotparser`, address checks are `ipaddress` and `socket`, all stdlib. Deliberately small, because the server is the constraint that started this redesign.

---

## 5. Normalising Vietnamese prices

Its own module with its own tests, because this is where quiet, systematic errors live.

### 5.1 The separator trap

`1.250.000` is 1,250,000 dong. `float("1.250.000")` raises; `float("1.250")` returns **1.25**, an error of one thousand times that looks like a plausible number in some other currency. Rule:

- both `.` and `,` present → the **last** separator is the decimal point, the other is grouping;
- one separator type, in groups of exactly three → grouping;
- one separator, not in threes → decimal point;
- VND is quoted without minor units in practice, so a VND result carrying a fractional part is a parse failure, not a price.

### 5.2 Shorthand

`250k` → 250,000. `1,2 triệu` / `1.2tr` → 1,200,000. `35 nghìn` → 35,000. Common in seller-written listings and in social commerce, absent from structured markup — so this only ever fires in Tier 5, where confidence is already low.

### 5.3 Ranges

`₫250.000 - ₫500.000` and `AggregateOffer` both mean a variant range. Store `price_min` and `price_max`; set `price` to the **minimum**, which is the number the buyer sees first and the one a competitor is effectively advertising. Mark the observation `is_range` so the UI can show it as a band rather than a point.

### 5.4 Sanity band

Reject and record as `implausible`: non-positive; below 1,000 VND; above 1,000,000,000 VND; or more than 20× / less than 1/20th the median of that comparable's own last five observations. The last check is the one that catches a site redesign silently repointing a selector at the wrong element — the failure mode most likely to survive everything above.

---

## 6. Fetching, and the rules that keep it safe

Sellers supply the URLs. **That makes this an SSRF surface, and it is the most serious security consideration in the design** — an unguarded fetcher will happily retrieve `http://169.254.169.254/latest/meta-data/`, `http://db:3306`, or `http://traefik:8080/api/`.

`fetcher.py` enforces, in order:

1. **Scheme** — `http` or `https` only.
2. **Host allowlist** — the URL's registrable host must have an adapter file or appear in `INTEL_ALLOWED_HOSTS`. Anything else is refused *at add-time* with a message naming the sources we support. This is both the SSRF backstop and the legal posture: we fetch from sources we have deliberately chosen.
3. **Address check** — resolve the host; reject if **any** resolved address is loopback, private, link-local, multicast, or reserved. Connect to the resolved address.
4. **Redirects** — max 3, and steps 2–3 re-run on every hop. Skipping this is the classic bypass.
5. **robots.txt** — fetched and cached 24h, evaluated for our own User-Agent. Disallowed → refuse at add-time and say so. Cheap, and it materially improves where we stand.
6. **Identification** — a real User-Agent naming Mercai with a contact URL. If someone wants us to stop, they should be able to tell us.
7. **Budget** — 5s connect, 10s read, 2 MB body cap (streamed, aborted on exceed), gzip only.
8. **Per-host rate limit** — Redis token bucket, default 1 request / 5s and 500/day per host, shared across all sellers. A seller cannot make us hammer a site by tapping refresh.
9. **Per-seller quota** — the existing `check_quota` / `consume_quota`, feature key `price_intel`.

### 6.1 The failure taxonomy is part of the contract

Every fetch resolves to exactly one status, stored on the observation and surfaced to the seller as plain language:

| Status | Seller sees |
|---|---|
| `ok` | the price |
| `host_not_allowed` | "We don't support this site yet." |
| `blocked_robots` | "This site asks us not to read its pages." |
| `js_required` | "This page builds its price in the browser, so we can't read it." |
| `no_price_found` | "We couldn't find a price on this page." |
| `http_error` / `timeout` | "That page didn't respond." |
| `implausible` | "We read a price that doesn't look right, so we're ignoring it." |

`js_required` is detected, not guessed: no tier matched, the body is small, and the document contains a framework mount point or an empty root element. **Shopee and Lazada land here, and that is the expected outcome.** They are hostile to fetching by design; the honest answer is to say we cannot read them rather than to ship a fragile scraper that will break silently and price a seller wrongly in the meantime.

---

## 7. Data model

Three new tables. All are additive, and per `01-instrumentation.md` §P0 they will auto-create via `create_all()` — but **write the migration by hand anyway**, and read any autogenerated file before applying it, because the six orphan tables described there will still be proposed for dropping.

### 7.1 `tracked_comparables` — what a seller asked us to watch

```sql
CREATE TABLE tracked_comparables (
  id                    INT AUTO_INCREMENT PRIMARY KEY,
  seller_id             INT          NOT NULL,
  product_id            INT          NOT NULL,          -- the seller's own product
  url                   VARCHAR(1000) NOT NULL,
  url_hash              CHAR(64)     NOT NULL,          -- sha256 of the normalised URL
  source_host           VARCHAR(255) NOT NULL,
  label                 VARCHAR(255) NULL,              -- seller's own note
  is_active             BOOLEAN      NOT NULL DEFAULT TRUE,
  last_fetched_at       DATETIME     NULL,
  last_status           VARCHAR(30)  NULL,
  consecutive_failures  INT          NOT NULL DEFAULT 0,
  created_at            DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_tc_product_url (product_id, url_hash),
  INDEX ix_tc_product (product_id, is_active),
  INDEX ix_tc_seller  (seller_id)
);
```

`url_hash` normalises before hashing — lowercase host, strip fragment, strip `utm_*` and other tracking params — so the same listing pasted twice with different campaign tags is one row, not two. `consecutive_failures` reaching 5 auto-deactivates and tells the seller, so a dead URL stops consuming the host's rate budget forever.

**`product_id` is the whole matching story in Phase 1.** The seller states which of their products the URL is a comparable for, so the fuzzy-matching stage from the reference architecture is **not needed and is not built**. It existed to solve a problem seller-pasted URLs do not have.

### Why porting that matcher would have been worse than skipping it

Worth recording, because "we already have a matcher" is the obvious next move and it is a trap. `FuzzyMatchingService.cs` is documented as *"Levenshtein distance and TF-IDF cosine similarity"*. **It implements neither.** There is no Levenshtein, and there is no IDF — every term gets the same weight `1/n`:

```csharp
double tf1 = words1.Length > 0 ? 1.0 / words1.Length : 0;   // uniform. no IDF anywhere.
```

Substitute that into the cosine and the whole function collapses to `|A∩B| / √(|A|·|B|)` — the Ochiai coefficient over binary word sets. It is a set-overlap ratio wearing a vector-space name.

That distinction is not pedantry, and it decides whether the matcher can work here at all:

- **In the reference project** it matched *US ↔ Vietnam* products across unrelated catalogues. Shared vocabulary between an American and a Vietnamese listing is genuinely informative, so overlap alone carries signal.
- **In Mercai** it would match ceramics against ceramics. `bát`, `gốm`, `sứ`, `Bát Tràng`, `cao cấp` appear in nearly every title. **IDF is precisely the mechanism that discounts terms appearing everywhere** — and it is the part that isn't there. Two unrelated bowls would score high, confidently, and a seller would be shown a competitor price for a different product.

The failure is systematically *worse* the narrower the catalogue, which is the opposite of what anyone would assume from the reference project's results. If per-listing matching is ever built (§13, phase 4), it needs real IDF fitted over Mercai's own corpus — not this function.

### Matching difficulty is category-dependent — and Mercai is no longer one category

The rename was precisely about not being ceramics-only, so a matching design tuned to ceramics is tuned to the hard half of the catalogue. Measured 2026-08-27 against real Tiki audio titles:

| Title | Model token extracted |
|---|---|
| `Bộ Amplifier Đèn Mini Bluetooth Nobsound MS-10D MKIII Cao Cấp` | `MS-10D` |
| `Ampli đèn Nobsound MS-10D MKIII chính hãng, bảo hành 12 tháng` | `MS-10D` |
| `Khuếch Đại FX-Audio XL-2.1BL Bluetooth 4.0 Amplifier` | `XL-2.1BL` |
| `FX Audio XL-2.1BL - ampli mini bluetooth 2.1 công suất lớn` | `XL-2.1BL` |
| `JOYO JBA-10 & JBA-35 – Loa Amplifier Guitar Bass` | `JBA-10`, `JBA-35` |
| `Bát ăn cơm gốm sứ Bát Tràng men lam cao cấp 15cm` | — none — |
| `Bát Tô Nông D20 Gốm sứ GOMIE CERAMIC men chảy hỏa biến` | — none — |

Three of four amplifiers joined **exactly** across completely differently-worded listings, with no scoring, no threshold and no labels. Zero of three ceramics titles produced a token at all.

That asymmetry is a design instruction, not a curiosity. **Mercai needs two matchers, and neither of them is a fuzzy scorer:**

1. **Model-token match** — an alphanumeric identifier carrying ≥2 letters and ≥2 digits (`MS-10D`, `XL-2.1BL`, `YX015`). A shared token of that shape is essentially never coincidence, so a match on it is exact and needs no confidence threshold. This covers electronics, audio, appliances, tools — every category where manufacturers assign part numbers. Implemented and unit-tested in `scripts/spike_price_sources.py::model_tokens`.
2. **Seller-declared** — the pasted URL (§7.1 above), for everything with no model number: ceramics, textiles, food, anything handmade or one-off.

Between them there is no gap that a fuzzy scorer is needed to fill. Missing a model token is cheap — it falls back to case 2. Inventing one is not, which is why the extractor is deliberately strict and why two known misses are accepted rather than loosened away: names without digits (`JBL Grip JBLGRIP`) and models spaced from their series (`Redmi Buds 8 Active`).

**One thing from the reference is worth copying exactly:** `ProductMatch` carries `MatchStatus.Pending` with explicit `Confirm()` / `Reject()` and a `MatchConfirmation` audit trail. That architecture already treats a match as a *proposal a human ratifies*, never as fact. Keep that, and every ratification becomes a labelled pair — which is what makes the matcher measurable in the first place.

### 7.2 `comparable_observations` — the time series

```sql
CREATE TABLE comparable_observations (
  id             BIGINT AUTO_INCREMENT PRIMARY KEY,
  comparable_id  INT           NOT NULL,
  observed_at    DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
  status         VARCHAR(30)   NOT NULL,          -- the §6.1 taxonomy
  price          DECIMAL(12,2) NULL,
  price_min      DECIMAL(12,2) NULL,
  price_max      DECIMAL(12,2) NULL,
  currency       CHAR(3)       NULL,
  is_range       BOOLEAN       NOT NULL DEFAULT FALSE,
  availability   VARCHAR(20)   NULL,              -- in_stock | out_of_stock | unknown
  title_seen     VARCHAR(500)  NULL,
  extractor_tier VARCHAR(20)   NULL,              -- jsonld|meta|state|selectors|text
  confidence     TINYINT       NULL,              -- 0-99
  evidence       VARCHAR(500)  NULL,              -- raw_snippet + path/selector
  http_status    SMALLINT      NULL,
  content_hash   CHAR(64)      NULL,              -- sha256 of the fetched body
  INDEX ix_co_comparable_time (comparable_id, observed_at),
  INDEX ix_co_status (status, observed_at)
);
```

**Append-only, and it records failures as rows.** A failed fetch is a fact about the market — "this competitor has been unreadable for two weeks" is information, and a table that only stores successes cannot express it.

`content_hash` lets a re-fetch that returns byte-identical HTML skip re-parsing, and distinguishes "the price did not change" from "we did not check".

**Reliability class: telemetry.** A failed observation insert must not fail the seller's request. It is not a ledger — unlike `price_history`, it describes the outside world and is already approximate.

### 7.3 Reusing `ai_suggestions`

Price alerts are proposals a seller acts on or ignores, which is the exact shape that table already models. Feature key `price_intel`, `entity_type='product'`. `model` and `prompt_version` are `NOT NULL`, so write `model='rules'` and `prompt_version` = the ruleset version — that is honest and it keeps acceptance measurable on the same query as every other feature. Do not widen the schema for this.

---

## 8. Computing the position

### 8.1 Internal comparables need no network at all

Mercai's own catalogue is already a multi-seller market. For a product in category *C*: all active products from **other** sellers in *C*, → p25 / median / p75 / n. Zero fetching, zero legal exposure, zero parsing risk — and it is the foundation, not the fallback.

### 8.1a Compute the quartiles in Python, not in SQL

**MySQL 8.0.46 has no `PERCENTILE_CONT`** — verified against the running
container on 2026-08-27, it is a syntax error. Neither does SQLite, which is
what the test suite runs on (`tests/conftest.py`), so a SQL-side implementation
would need two dialect-specific paths *and* could not be unit-tested where
everything else is.

Sort the category's prices and interpolate in Python. The row counts are a
single category's products — tens, not millions — so there is nothing to
optimise here, and it keeps one implementation working identically against
MySQL in production and SQLite in tests. Revisit only if a category ever grows
past the point where fetching its prices is the slow part, which is a long way
off and will be visible when it happens.

### 8.2 Never show a statistic computed from fewer than five listings

`MIN_COMPARABLE_N = 5`, and it is not a tuning knob:

- with three listings the median is noise and the quartiles are meaningless;
- in a thin category, showing "the market median" over two competitors **discloses a specific competitor's price** to someone who can trivially work out whose it is. That is a privacy problem, not a statistics problem, and it is the reason this is a hard floor rather than a warning.

### 8.3 The never-empty ladder

Artisan and one-off pieces frequently have no true comparable. A screen that is blank for those sellers teaches them the feature is broken. Fall through:

1. Explicit comparables (pasted URLs, `confidence ≥ 75`) + **model-token matches** (§7.1) + internal same-category — if combined `n ≥ 5`;
2. internal same-category alone, `n ≥ 5`;
3. internal **parent** category, `n ≥ 5`, labelled as the broader benchmark it is;
4. no market view: show the seller's own `price_history` and a clear invitation to add a comparable URL.

Step 4 is a real state with real content, not an error. It will be the common case for genuine one-offs and the copy should treat it as normal.

### 8.3a A known weakness of rung 3, stated rather than hidden

The parent-category fallback broadens by *catalogue structure*, which is not
the same as broadening by *comparability*. Observed on the seeded data:

> `Ampli đèn Nobsound MS-10D MKIII` at 3,589,000₫ falls back to `Âm thanh`,
> whose median is 890,000₫ — because that parent mixes amplifiers
> (290k–3.6m) with speakers (260k–9m).

The label is honest (the client says "the broader category, because your own
has too few to compare"), but a seller reading past the label gets a benchmark
that is not really about their product. This is the *cost* of never showing an
empty screen, and it is the right trade at this stage — but it should not be
described as equivalent to rung 1.

Two refinements worth considering once there is real traffic, neither of them
phase 1:

- **suppress rung 3 when the fallback set is too dispersed** — if `p75/p25`
  exceeds some ratio, the benchmark carries no information and the honest
  answer is the no-market-view state;
- **narrow by price band rather than by category** — comparable listings within
  ±50% of the seller's own price, which for the case above would compare the
  amplifier against other expensive audio rather than against everything.

### 8.4 Labels and alerts

Position from quartiles, never the mean — one 8,000,000₫ display piece should not drag the whole category's average. *Below market* < p25, *in range* p25–p75, *above market* > p75.

An **undercut alert** requires all of:

- confidence ≥ 90 (so Tier 5 and unconfigured Tier 3 walks can never fire one);
- observation age ≤ 48h;
- ≥ 5% below the seller's price;
- **the same direction in two consecutive observations** — one reading is a flash sale, two is a move.

With no scheduler (§9), alerts are evaluated at read time, when the seller opens the screen. That is a real limitation and the UI states it: *"checked when you last opened this."*

### 8.5 Trend, told honestly

The seller's own line comes from `price_history` and is **exact** — every change, ledger-written in the same transaction (`01-instrumentation.md` PR 2).

Competitor lines come from irregular, seller-triggered fetches. Render them as **observed points with a stepped line**, never a smooth interpolation, and grey anything older than seven days. Drawing a confident curve through four scattered observations would imply a continuous record we do not have, and it is the sort of chart that gets a real pricing decision made on imaginary data.

---

## 9. There is still no scheduler

`grep` across the backend finds no Celery, no APScheduler, no cron, no worker. It was flagged as absent in the assessment and it still is. Phase 1 is designed around that: everything is on-demand, driven by a seller opening a screen or tapping refresh.

The consequence is that competitor history is only as dense as sellers make it. If the trend proves valuable enough to be worth a background refresh, the smallest honest addition is a single `intel-worker` container running an asyncio loop over `tracked_comparables` ordered by `last_fetched_at`, respecting the same per-host budget. That is deliberately out of scope here, and it is also the natural home for the `search_logs` retention purge and the stock-ledger drift check, both of which are currently documented but unscheduled.

---

## 10. API surface

All under `/api/v1/intel`, seller auth, behind `feature_enabled('price_intel', seller_id)`.

| Method | Path | Notes |
|---|---|---|
| `POST` | `/comparables` | `{product_id, url, label?}`. Validates ownership, allowlist, robots, then **fetches once synchronously** and returns the first observation. Adding a URL that cannot be read must fail *now*, with a reason — not silently produce a row that never yields a price. |
| `GET` | `/comparables?product_id=` | Comparables with their latest observation. |
| `DELETE` | `/comparables/{id}` | Soft delete (`is_active = false`); observations are kept. |
| `POST` | `/comparables/{id}/refresh` | Re-fetch. Quota-consuming, host-rate-limited; returns `429` with `Retry-After`, matching the existing convention. |
| `GET` | `/products/{id}/price-position` | The screen payload: position, stats, `n`, which ladder rung produced them, comparables with confidence and staleness, both trend series, alerts. |
| `GET` | `/health` · `/api/v1/intel/health` | Unchanged shape, minus `ollama`. `features.price_intel` reflects the flag alone — there is no model to be unreachable. |

The `features` block keeps its existing contract: the client uses it to decide whether to render the affordance at all, so a disabled feature hides its buttons rather than showing a control that fails when tapped.

---

## 11. External marketplace sources — what is already known

**This section is evidence, not analysis.** `~/TuanPH/crossmarket_price_analyzer`
already implemented Shopee, Lazada and Tiki scrapers and ran them. Its
`TODO.md` checkpoint (2026-04-28, commit `b4fc1bb`) records what happened. That
settles most of what this design would otherwise have had to guess.

| Source | Method tried | Result | Where |
|---|---|---|---|
| **Tiki** | Plain HTTP `GET /api/v2/products?q=&limit=` — undocumented, no auth | ✅ **Works.** Clean JSON, no browser | `TikiScraper.cs` |
| **Shopee** | Playwright + stealth, intercepting `/api/v4/search/search_items` | ❌ **`error 90309999`** | `ShopeeApiClient.cs:15-30` |
| **Lazada** | Playwright + DOM scraping of `data-qa-locator="product-item"` | ❌ **SPA shell, no product grid** | `TODO.md` |

Three things follow, and they matter more than any argument in §1:

**1. Tiki is a working external source today, at zero infrastructure cost.**
A plain `httpx.get` returns structured JSON. No Playwright, no +400 MB Chromium
layer in the image, no proxy budget — exactly the fetcher this design already
specifies. Re-verified 2026-08-27 via `scripts/spike_price_sources.py`:
HTTP 200, 20 priced items, first response 541 ms.

**2. Shopee's refusal is server-side and stealth did not beat it.** The class
comment is explicit: detection is TLS fingerprint (JA3) and/or datacenter IP
reputation, so `navigator.webdriver` patches never get a chance to matter — the
request is rejected before any JavaScript runs. Writing a fourth scraper against
Shopee is not the missing piece; **access is**, and the reference project already
ranked the three ways to buy it:

| Route | Cost | Lead time | Note |
|---|---|---|---|
| **Shopee Affiliate API** | free | ~1–2 weeks approval | Open enrolment, *designed for price-comparison sites* — the intended door |
| VN residential proxies | ~$50–200/mo | immediate | Ongoing cost, and still adversarial |
| Shopee Open Platform | free | ~4 weeks | Needs a registered business entity; may not approve this use case |

The Affiliate API is the one worth starting, because approval time is the long
pole and it costs nothing to begin. **Start that application before writing any
Shopee code** — if it lands, the scraper is never needed.

**3. The most important line in that checkpoint is a hypothesis that was never
tested.** Both refusals came from one network, and the note reads: *"Likely
cause: home/office firewall or geo/IP reputation, not a bug in the scrapers.
Test from a different network before any more code changes."* That test was
never run.

That is what `back_end/scripts/spike_price_sources.py` is for. It probes all
three sources over plain HTTP and — critically — **distinguishes "they refused
us" from "we never left the building"**, because a blackholed DNS entry surfaces
as an instant connection refusal that looks exactly like a block. Getting that
attribution wrong is the difference between buying proxies and moving to a
different Wi-Fi.

```bash
python3 back_end/scripts/spike_price_sources.py --keyword "bát gốm sứ"
python3 back_end/scripts/spike_price_sources.py --urls real_urls.txt   # the §13 gate
```

### A trap the spike found: diacritics decide relevance

Tiki keyword search is close to useless without Vietnamese tone marks, and it
fails *silently* — it returns twenty confident, irrelevant results rather than
an error:

| Query | Top result |
|---|---|
| `bat gom su` | *"Dây chuyền vòng cổ chuỗi flash chain…"* — a necklace |
| `bat gom bat trang` | *"Sách Luyện Nói Tiếng Trung Quốc…"* — a Chinese textbook |
| `bát gốm sứ` | *"Bát Tô Nông D20 Gốm sứ GOMIE CERAMIC men chảy…"* — correct |
| `gốm sứ bát tràng` | *"Bộ Ấm Chén Trà Sứ Trắng Viền Vàng…"* — correct |

A category benchmark built from unaccented queries would be **statistically
confident nonsense** — a median over necklaces and textbooks, presented to a
seller as the market for their bowl. Two consequences for §8:

- any keyword sent to an external source must carry diacritics, and Mercai
  product names cannot be assumed to have them;
- prefer **category identifiers over free-text search** wherever the source
  exposes them. A category id cannot silently drift into the wrong department.

### Tested again on audio and electronics, 2026-08-27

Ceramics is not the catalogue, so the sources were re-probed with `amply bluetooth`,
`loa bluetooth`, `amplifier` and `tai nghe`. Three results, and the second is
structural:

**1. Tiki is not a ceramics source — it carries real audio gear.** Fender, JBL,
Nobsound, FX-Audio, JOYO, Redmi, USAMS, at prices from 88,000₫ to 8,999,000₫.
Its relevance problem persists beyond diacritics, though: `đầu CD` returned five
books, because `đầu` also means "beginning". **Free-text search on Tiki is not
safe for building a benchmark in any category** — use category identifiers.

**2. Across every ordinary VN retailer tested, listing pages render client-side
but product pages carry JSON-LD.**

| Host | Search / listing page | Product page |
|---|---|---|
| `fptshop.com.vn` | client-side, no prices in raw HTML | ✅ **JSON-LD, confidence 99** (4/4 tested) |
| `dienmayxanh.com` | client-side, zero product links in raw HTML | untested — no URLs harvestable |
| `thegioididong.com` | client-side | untested — same reason |
| `sendo.vn` | connection timeout | untested |

This is the single strongest argument for the seller-pasted design, and it was
not anticipated. **Crawling needs listing pages; sellers paste product pages.**
The page type that a cheap fetcher can read is exactly the one this design asks
for, and the page type it cannot read is exactly the one an automated crawler
would depend on. Building the crawler first would have hit the wall that pasting
walks around.

It also validates the ladder's honesty on the wrong page type: category and
brand-facet pages returned tier-5 text matches at confidence 55, never a false
90+. On `fptshop.com.vn/phu-kien/tai-nghe/samsung` it read `500.000₫` — a price
*filter* facet — and correctly refused to be confident about it.

**3. Lazada could not be re-tested.** `lazada.vn`, `www.lazada.vn` and
`m.lazada.vn` all resolve to `0.0.0.0` from the machine this was run on, as does
`shopee.vn`. Nothing here says anything about either marketplace. Run this
yourself from an unfiltered network:

```bash
python3 back_end/scripts/spike_price_sources.py --keyword "amply bluetooth" --all-hosts
```

If Lazada does answer, its own product pages are worth testing with `--urls`
before writing any DOM adapter — the fptshop result above suggests VN product
pages are far more likely to carry JSON-LD than their listing pages are.

### What this means for the sequence

Marketplace scraping earns a place in the plan — but the source that works today
is Tiki, not the two that were asked about. Shopee and Lazada are an *access*
problem with a paperwork solution already identified, not a coding problem, and
neither should block anything.

## 12. What we lose, and what we do about it

**Coverage.** Pages that render prices only in JavaScript are unreadable. §11 sharpens this considerably: the two largest Vietnamese marketplaces were *already* unreadable to a full Playwright browser with stealth patches, so the ladder is not what loses them — they were never available to the previous design either, LLM or not. What the ladder actually gives up is the narrow band of sites that render server-side but emit no standards markup and have no adapter yet.

Mitigations, in order of honesty:

1. Say so. `js_required` is a first-class status with a plain-language message.
2. **Log every failure by host.** `comparable_observations` grouped by `source_host` and `status` is a ranked, evidence-based worklist of which adapter to write next. This is the loop that replaces the LLM's generality: instead of one extractor that handles everything at unknown accuracy, a measured queue of the sources sellers actually paste.
3. Internal comparables are unaffected — they are a database query — so the screen still works for every seller regardless of external coverage.
4. **Tiki is confirmed reachable over plain HTTP** (§11), so external data is not hypothetical even before any of the above.
5. Shopee is an access problem with a paperwork route already identified, not a parsing problem. A headless browser remains available later for a small set of high-value hosts, but it is the *worst* of the three options and the +400 MB image weight lands on a server that is already the binding constraint.

**Attribute extraction.** The LLM would also have read titles, variants and specs. Two-thirds of that need disappears with seller-declared matching (§7.1); the remainder — normalising "bát men xanh 15cm" against a competitor's title — is not required for a price comparison and is deferred.

---

## 13. Phasing

| Phase | Work | Effort |
|---|---|---|
| ~~**0**~~ | ~~Strip Ollama, rename the service, keep `image_report`, banner docs 02–04~~ | ✅ **done** |
| **0.5** | **Start the Shopee Affiliate API application** (§11) — approval is the long pole and it costs nothing to begin | 1 h |
| ~~**0.75**~~ | ~~Seed a real catalogue~~ — `scripts/seed_catalogue.py` | ✅ **done** |
| ~~**1**~~ | ~~Internal market position: stats, ladder, labels, screen~~ | ✅ **done** |
| **1.5** | **Validation gate** — `spike_price_sources.py --urls`, 20 real Vietnamese URLs, **from a non-filtered network** | 0.5 d |
| **2** | `fetcher.py`, extraction ladder, adapters, `POST /comparables`, on-demand fetch | 3–4 d |
| **2.5** | **Tiki category aggregates** — the one external source confirmed working, and it needs no matching | 1–2 d |
| **3** | Observation history, trend, staleness, read-time alerts | 1–2 d |
| **3.5** | **Model-token matching** (§7.1) — exact, no threshold, no labels needed. Only worth building once a non-artisan category has volume | 1 d |
| **4** | Deferred: `intel-worker`; Shopee via Affiliate API *if approved*; fuzzy scoring **only** if a category defeats both matchers, and then with real IDF | — |

**Phase 0.75 — ✅ done 2026-08-27.** `back_end/scripts/seed_catalogue.py`,
idempotent, run with
`docker exec mercai_intel_service python /app/scripts/seed_catalogue.py`.

It builds 24 active products across 5 sellers and two contrasting category
trees, shaped so that every rule in §8 has a case to exercise:

| Category | Products | Sellers | Exercises |
|---|---|---|---|
| `Gốm sứ / Bát đĩa` | 8 | 3 | quartiles with a real spread; no model numbers anywhere |
| `Gốm sứ / Ấm chén` | 3 | 3 | **below `MIN_COMPARABLE_N`** → the parent-category fallback (§8.3 rung 3) |
| `Âm thanh / Ampli` | 7 | 3 | model tokens shared across sellers (§7.1) |
| `Âm thanh / Loa` | 6 | 2 | same, plus a wide price range |

Two products are deliberate outliers so the labels have cases: a signed artist
bowl at 450,000₫ (**above market**) and a guitar practice amp at 290,000₫
(**below market**). The artist piece is the more useful of the two — it is a
legitimate price, and it is exactly the listing the screen must not scold the
seller about.

`price_history` gets an origin row per product plus five real changes, so the
trend line is not empty on day one. Verified end to end: the seeded sellers
authenticate through the gateway (`POST /api/v1/auth/login`, username not
email), products return through `/api/v1/products/`, and the quartile
computation puts both outliers in the right bucket:

```
Bát đĩa   n=8  p25=138,750   median=175,000    p75=235,000
Ampli     n=7  p25=1,174,500 median=1,859,000  p75=3,070,000
```

The original justification follows, because it is the reason this phase exists
at all. Checked against the running stack on 2026-08-27, before seeding:

```
sellers with active products   0
active products                0
categories in use              0
price_history rows             0
```

`back_end/seed_test_data.sql` inserts `cart_items` and nothing else — there is no
catalogue seed anywhere in the repo. Phase 1 computes quartiles over `products`,
so with an empty table **every seller sees the "no market view" state and a
working implementation is indistinguishable from a broken one.** The seed needs
at least five active products from two or more sellers in the same category, and
it should cover **two contrasting categories** — one artisan (no model numbers)
and one electronics/audio (model numbers) — so that §7.1's two matchers can both
be exercised when their phases arrive.

**Phase 0.5 is an hour of paperwork that can save weeks.** If the Affiliate API
is approved, Shopee arrives as a supported, ToS-clean JSON source and no scraper
is ever written for it. Starting it late is the only way to lose that option.

**Phase 2.5 is where the "big marketplace" instinct gets paid.** Tiki works over
plain HTTP today, and aggregate benchmarks — *"ceramic bowls 15–18cm, n=340,
median 185,000₫"* — need no per-listing matching at all. One bad row cannot move
a median over 340 items, which is why the aggregate is more robust than the 1:1
comparison it replaces. It also fills the never-empty ladder (§8.3) for exactly
the artisan sellers who have no true comparable.

### Phase 1 — ✅ done 2026-08-27

Shipped as designed, with no migration and no new table.

| Piece | Where |
|---|---|
| Stats engine, fallback ladder, quartiles | `services/intel/app/services/position.py` |
| `GET /api/v1/intel/products/{id}/price-position` | `services/intel/app/routers/position.py` |
| `GET /api/v1/intel/products/{id}/image-report` | `services/intel/app/routers/images.py` — gives `image_report.py` a caller again |
| Seller screen | `front_end/src/screens/seller/PricePositionScreen.jsx` |
| Client | `front_end/src/services/intelService.js` |

**Verified against the seeded catalogue through the gateway**, not just in
tests — every rung and label has a real case:

| Listing | Own price | Result |
|---|---|---|
| `BAT-001` bowl | 85,000₫ | `below_market`, `own_category` (n=5) |
| `BAT-008` artist bowl | 450,000₫ | `above_market`, `own_category` (n=6) |
| `AMP-001` amplifier | 3,589,000₫ | `above_market`, **`parent_category`** — its owner holds 3 of 7 Ampli, leaving only 4 rivals |
| `AMC-001` teaware | 320,000₫ | `above_market`, **`parent_category`** — 3 in category |
| another seller's product | — | `403 Not authorized` |

61 tests pass (24 pre-existing, 13 guardrails, 18 position, 6 router).

**Phase 1 ships seller value with zero scraping risk**, on data the platform already owns — and it needs **no migration and no new table**, because it reads only `products` and the `price_history` ledger, both of which already exist. If external coverage turns out worse than hoped, the feature still stands on its own.

### The validation gate, and why it is cheap now

The old plan's open risk was LLM accuracy on real Vietnamese pages, and the proposed test was 5–10 URLs. Keep the test, raise the sample, and change what it measures:

> Fetch 20 real product URLs across the intended hosts. For each, record which tier fired, the extracted price, and the true price read by eye.

**Gate:**
- ≥ 70% of URLs on allowlisted hosts yield a price at confidence ≥ 90;
- **zero wrong prices at confidence ≥ 90.** Not a target — a blocker. A missing price is a gap the seller can see; a wrong price at high confidence is a bad pricing decision with our name on it.

This is a far better test than the LLM equivalent, because a deterministic parser that passes on 20 URLs will keep passing on those hosts until their markup changes — and §5.4's magnitude check is there to catch it when it does. The model version would only ever have told us about its mood that afternoon.

---

## 14. Standing risks

- **A site redesign silently repoints a selector.** The most likely cause of a wrong price in production. Defence is layered: cross-tier reconciliation (§4.6), the magnitude check against the comparable's own history (§5.4), and the stored evidence snippet that makes it diagnosable in one query.
- **SSRF via seller-supplied URLs** (§6). The allowlist plus post-redirect address re-validation are both required; either alone is insufficient.
- **Legal posture.** Fetching public pages a seller already opened in their own browser, at one request per five seconds, honouring robots.txt, identifying ourselves, from an allowlist we chose deliberately. That is a defensible position and each of those clauses is doing work — none should be dropped as an optimisation.
- **Seller reaction to being told they are above market.** Mitigated by framing and opt-in (§3), and worth measuring directly: `ai_suggestions` acceptance for `price_intel` will show whether sellers act on it or turn it off.
- **Designing for ceramics alone.** Mercai is deliberately no longer one category, and the two halves of the catalogue need different matchers (§7.1). A rule validated only on bowls will be wrong about amplifiers, and vice versa.
- **Reaching for the existing matcher.** It is the obvious shortcut and it is measurably wrong for this catalogue (§7.1). Anyone porting it should be sent to that section first.
- **A source that works today is not a source.** Tiki's API is undocumented and unversioned; it can change or close without notice. Treat it as a bonus over the internal catalogue, never as the foundation — which is why phase 1 requires no network at all.
- **Thin categories.** `MIN_COMPARABLE_N = 5` will suppress the market panel for a lot of Mercai's catalogue early on. That is correct behaviour, and §8.3 step 4 is what those sellers see.
