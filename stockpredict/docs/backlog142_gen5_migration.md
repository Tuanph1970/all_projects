# Backlog #142 — the gen-5 call-style migration

**Date:** 2026-11-10
**Status:** Done, deployed. One step of option (a); the broker adapter still
needs a broker API registration.
**Code:** `services/stock-data-service/app/services/stock_service.py`
**Harness:** `services/stock-data-service/tests/gen5_equivalence.py`

---

## 1. Why this step, and why before the adapter

The vendor's transition notice asks gen-4 code to move to the gen-5 call style
and says **gen 6 keeps that style**. Doing it before writing the broker adapter
means the adapter is written once, against the call style that survives, rather
than against a shape that is already deprecated.

It also needed no broker key, so it was the only #142 work available while the
registration is outstanding.

Backlog #144 made it cheap: all 29 vendor call sites had already been funnelled
through one guarded path, so this touched that path plus the call sites' local
variable, not 29 scattered constructions.

## 2. What actually changed

| gen-4 | gen-5 (`vnstock.api.*`) |
|---|---|
| `Vnstock().stock(s, src).quote` | `Quote(symbol=s, source=src)` |
| `… .company` | `Company(symbol=s, source=src)` |
| `… .finance` | `Finance(symbol=s, source=src)` |
| `… .trading` | `Trading(symbol=s, source=src)` |
| `… .listing` | `Listing(source="KBS")` — **not** the configured source, see §3 |
| `… .company.data_source` | `Company(…).provider` |

`StockService` gained `_quote / _company / _finance / _trading / _listing`, all
over one guarded, cached `_component(kind, symbol, source)`. Call sites bind
`vn_quote`, `vn_listing`, … (§5 explains the prefix).

Note these are `vnstock.api.*`, which are **not** the `vnstock.common.data.*`
classes `StockComponents` builds — that module emits a DeprecationWarning
pointing here. `vnstock.Company is vnstock.common.data.Company` is `False`.

## 3. The trap: `listing` was never the configured source

`StockComponents._initialize_components` hardcodes `Listing(source="KBS")` even
when the components' own source is VCI. The naive migration — passing
`settings.VNSTOCK_DATA_SOURCE` — would silently re-point every listing consumer,
the scanner's universe included. Measured 2026-11-10:

```
Listing("KBS").all_symbols()            1,517 rows
Listing("VCI").all_symbols()            1,757 rows
Listing("KBS").symbols_by_industries()    700 rows
Listing("VCI").symbols_by_industries()  8,262 rows
```

So the migration **preserves KBS** (`LISTING_SOURCE`, with a test asserting it).
Whether VCI's wider coverage is better is a real question and a separate,
measured decision — not a side effect of a call-style change.

## 4. Equivalence, measured per endpoint

`tests/gen5_equivalence.py` calls each endpoint both ways and compares a
fingerprint (row count, column hash, data hash). Results for FPT @ VCI:

| endpoint | verdict |
|---|---|
| `quote.history` | **identical** on a closed window (45 bars, same hash) |
| `company.overview` / `shareholders` / `events` / `trading_stats` / `news` | same |
| `finance.ratio` / `income_statement` | same |
| `listing.all_symbols` | same 1,517 symbols, **different row order** (§4.1) |
| `listing.symbols_by_industries` / `symbols_by_group` | same |
| `listing.industries_icb` | raises on both — KBS has no ICB, already handled (§4.2) |
| `trading.price_board` | same shape; data moves (live) |
| `finance.balance_sheet` / `cash_flow` | transient vendor timeouts, never a shape difference |

On the first sweep `quote.history` showed as DIFFERS and that was **today's live
bar moving between the two calls**, not a difference: re-run over a closed window
(2026-09-01 → 2026-10-31) the two are byte-identical. Any run at 2s spacing also
produces spurious ERROR rows — the vendor throttles, and the harness defaults to
6s for that reason.

### 4.1 Row order is not stable, and nothing depends on it

`all_symbols()` returns the same 1,517 symbols in a different order. Checked all
five consumers before accepting it: every one is either an exact-symbol filter
(`df[df["symbol"] == X]`) or a full `iterrows()` loop. No `head`, no `iloc[0]`.

### 4.2 `industries_icb` has always failed here

KBS raises `NotImplementedError: KBS không cung cấp ICB classification`, and
because gen-4 pinned listing to KBS, this call has never succeeded at our
configuration. It is not a new break: `get_all_industries_live` already tries it,
logs a warning and falls back to `symbols_by_industries()`, and its docstring
says so. Gen-5 wraps the same error in a `RetryError`; both are caught.

## 5. The win beyond "the vendor asked"

Gen-4 built **every** component eagerly, so a caller that only wanted
`listing.all_symbols()` still paid `Finance.__init__`'s handshake — the network
call #144 identified as #134's real cause. Constructing components individually
means only finance paths pay it. Measured in the deployed container:

```
VnListing(source="KBS")        0.005s
VnCompany(...)                 0.000s
VnTrading(...)                 0.000s
VnQuote(...)                   0.630s first call, 0.000s after   (lazy import)
VnFinance(...)                 0.757s every time                 (_handshake)
gen-4 Vnstock().stock(...)     0.897s every time                 (builds Finance)
```

A listing-only path went from ~0.9s to ~0.005s and from one handshake to none.

## 6. The variable prefix, and why it is not cosmetic

Call sites bind `vn_listing`, `vn_company`, … rather than `listing`, `company`.
`listing` and `company` are ordinary words that already name unrelated locals in
this 3,700-line module — one function binds
`listing = item.get("listingInfo", {})`. Unprefixed component variables would
risk shadowing, and they made #144's structural AST guard match plain
dictionaries. The prefix is what lets that guard stay exact rather than
heuristic.

## 7. Tests

385 pass (was 372 before #144, 383 after). Two structural guards updated and one
added: gen-5 classes may only be constructed inside `_component`, and
`LISTING_SOURCE` must stay KBS.

**The suite hung before it failed, and that is worth recording.** Fifteen test
files mocked `StockService.vnstock` — the gen-4 facade — which after this change
intercepts nothing, so those tests began making real network calls and timing
out at 30s. The fix is one adapter in `conftest.py`,
`patch_vendor_components(fake_vnstock)`, which maps the existing fakes onto
gen-5 construction. The fakes already described the vendor surface correctly;
only who constructs each component changed, so rewriting fifteen fixtures would
have thrown away accurate descriptions to chase a plumbing change.

That adapter serves `listing` from the fake's **primary** sheet, not from a
`source="KBS"` lookup: source-aware fakes give KBS a sheet carrying only
`finance.ratio`, because they model gen-4's object graph where `.listing` hung
off the primary components object with the KBS pinning hidden inside. Passing
KBS through broke one test, and it was a fixture artefact, not a behaviour change.

## 8. Verified live

Rebuilt and deployed. `/health` reports pacing and component state.
`GET /companies/FPT/financials` returns 200 with ratios (PE 15.91, ROE 28.3),
all three statements, and `company_name` resolved through the KBS listing —
which exercises `_finance`, `_listing` and the supplementary KBS ratio path
together. `industries` returns 200 through the documented ICB fallback.

## 9. What is still owed on #142

- **A broker API registration.** The adapter cannot start without it; this is
  the critical path.
- The adapter itself, behind `_component`, covering the 16 endpoints.
- Re-verify vnstock before each step. It still served data on 2026-11-10,
  including that day's bar, and the decree took effect 2026-11-11.
