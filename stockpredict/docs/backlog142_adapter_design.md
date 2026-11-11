# Backlog #142 — TCBS adapter: design sketch (manual daily prime)

**Date:** 2026-11-11
**Status:** Sketch. No code. Written against the PESSIMISTIC auth assumption so
it can only get simpler if the probe says otherwise.
**Depends on:** `tests/tcbs_auth_probe.py` step 3, still unrun.

---

## 1. The assumption, stated so it can be retired

**Assumed:** a JWT can only be minted with a human-supplied Smart OTP, and lives
≤ 8 hours. So a person primes a token once a day and the service runs on it
until it expires.

**Known, not assumed** (probe, 2026-11-10):

- `apikey/info` answers with the API key alone — no OTP, no bearer. This key
  expires **2027-11-10**. Key-expiry monitoring is unattended today.
- The key→JWT exchange rejects a request with no `otp`
  (HTTP 400, `203002 Missing required inputs`).

**Not yet known:** whether an existing token can be renewed without a fresh OTP.
If it can, §4 collapses to a background refresh loop and most of §5 disappears.
Everything else in this sketch stands either way.

## 2. The finding that actually shapes this

The container runs **UTC** (`TZ` unset) and the two scheduled jobs are:

| job | UTC | ICT (UTC+7) |
|---|---|---|
| stock-data daily company/price sync | 01:00 | 08:00 |
| momentum scanner (#133) | 09:15 | 16:15 |

**They are 8h15m apart. The token lives 8h. One prime cannot cover both — it
misses by fifteen minutes.**

That is not a rounding error to wave at; it is the difference between "prime
once each morning" and "prime twice a day, forever". Three ways out, and the
choice belongs to the owner:

- **(A) Move the daily sync later**, e.g. 01:30 UTC / 08:30 ICT. One prime at
  ~08:15 ICT then covers both jobs with ~15 min of slack. Cheapest, and it
  changes nothing about what the sync does.
- **(B) Move the scanner earlier.** Worse: it is scheduled after the close for a
  reason, and FR-SCAN-SCHED requires it to run after the price refresh and the
  seam sweep.
- **(C) Two primes a day.** Honest, and the one to pick only if A is impossible —
  a daily chore that is easy to forget is an outage waiting to happen, and #143
  already showed this project can be silently broken for four days.

**Recommendation: (A).** It costs one constant.

## 3. Where the adapter sits

`StockService._component(kind, symbol, source)` is already the single guarded
seam (#144), and the gen-5 migration (#142) put every call site behind it. The
adapter does **not** replace that seam — it becomes a *source* selected inside
it.

```
_component(kind, …)
   ├── source == TCBS  → TcbsClient  (plain HTTP, no vendor library)
   └── source == VCI   → vnstock gen-5 classes   (unchanged)
```

Per-endpoint selection, not a global switch, because **TCBS does not cover
everything**: it documents OHLCV, symbol/price info and index components, and
documents **no** company profile and **no** financial statements. So:

| endpoint group | source after this work |
|---|---|
| `quote.history` | TCBS |
| `listing.all_symbols`, index components | TCBS |
| `company.*`, `finance.*` | **vnstock/VCI, unchanged** |

This is also why the adapter must be able to fail *to* vnstock rather than fail
outright (§5).

## 4. Token lifecycle

**The token must survive a container restart.** In-memory only would mean a
restart at 03:00 silently drops ingestion until someone notices — exactly #143's
failure shape. Stored in **Redis** (already in the stack, already shared) with a
TTL set from the token's own `exp` claim, so it expires itself rather than
relying on us to clean up.

Not MySQL: this is short-lived credential material, not a record, and it should
vanish on its own.

```
tcbs:token          -> the JWT            (TTL = exp - now - safety margin)
tcbs:token:exp      -> ISO8601, readable for /health without decoding the JWT
```

**Safety margin:** treat the token as dead ~10 minutes before `exp`. A job that
starts at 07:58 and runs 20 minutes must not have the token die mid-run; better
to refuse at the start than to fail halfway through a 93-symbol sweep with
partial writes.

## 5. Degradation — the part most likely to be got wrong

When there is no usable token, the adapter **must not** take the platform down.
Order of preference, per call:

1. **TCBS**, if a live token exists.
2. **vnstock/VCI**, while it still answers. It did on 2026-11-10 including that
   day's bar, and it remains the only source for fundamentals anyway.
3. **Serve from MySQL and say so.** 123,007 bars are already stored; the scanner
   reads MySQL, not the vendor, so a missing token degrades *ingestion*, not the
   product. What stops is new bars.

The one thing it must never do is **fail silently**. A missing token is a
loud condition: a warning log per affected job, and a visible field on `/health`.

## 6. Visibility, because silence is this project's failure mode

`/health` already reports vnstock pacing and component reuse (#144). It gains:

```json
"tcbs": {
  "api_key_expires": "2027-11-10T15:27:23+07:00",
  "token_present": true,
  "token_expires": "...",
  "token_seconds_left": 21600,
  "needs_prime": false
}
```

`api_key_expires` can be refreshed unattended from `apikey/info` — that is
already proven — so the one-year key cannot quietly lapse either.

**`needs_prime: true` is the alert.** Whatever watches this should shout before
the token dies, not after ingestion has already missed a day.

## 7. The prime endpoint

```
POST /stock_helper/api/v2/stocks/tcbs/prime   {"otp": "123456"}
```

- **Admin-gated** by the existing JWT check used for `/companies/sync` and
  `/priceboards/refresh` (SECURITY_AUDIT HIGH #4). An unauthenticated endpoint
  that spends an OTP and mints a credential is not acceptable.
- **One attempt, no retry.** An unconfirmed report puts the token endpoint at 10
  exchanges/day and TCBS publishes no figure; a retry loop could spend a budget
  we cannot see.
- **Never logs the OTP or the token.** Reports length and `exp`, like the probe.
- Returns `expires_at` so the operator can see what they bought.

A thin page on the existing admin surface would beat curl, but the endpoint
comes first.

## 8. Key renewal — different clock, different trap

The **API key** (1 year, expires 2027-11-10) is separate from the **JWT** (8h).
Renewal via `apikey/extend` needs an OTP too, and the new term runs **from the
moment of extension rather than adding to the remainder** (*"không cộng dồn vào
thời hạn cũ"*). So renewing early **throws away** the time left, and an expired
key cannot be extended at all — it has to be recreated in TCInvest.

Therefore: do **not** auto-renew on a schedule. Alert when under ~30 days and
let a human do it deliberately.

## 9. Phasing

- **P0 — auth.** Probe step 3, pick (A)/(B)/(C) from §2, Redis token store,
  prime endpoint, `/health` fields. No data endpoints yet. Nothing in the
  platform changes behaviour.
- **P1 — price path.** `quote.history` through TCBS behind a flag defaulting
  OFF, compared against vnstock on the same symbols and dates the way
  `gen5_equivalence.py` compares call styles. Flip the default only when they
  agree.
- **P2 — universe.** `all_symbols` and index components. Note the open question
  already recorded: our listing is pinned to KBS (1,517 symbols) and VCI returns
  1,757 — TCBS will return a third number, and *that* is a universe change
  needing its own pre-registration, not a side effect.
- **P3 — fundamentals.** Separate decision. Prices go stale daily; financial
  statements go stale quarterly, so this half has months of slack and should not
  hold up P1.

## 10. Deliberately not decided here

- Whether TCBS costs anything. TCBS publishes no pricing; absence of a published
  price is not evidence of a zero price. Ask before relying on it.
- The daily token-exchange cap, if any.
- Whether TCBS OHLCV is back-adjusted the way VCI's is. `adjusted_close()` in
  `stock_service.py` assumes the series is already adjusted, on evidence from
  TCB's 2024 bonus issue. **If TCBS adjusts differently, every stored return is
  affected** — this must be measured in P1, not assumed, and it is the single
  most dangerous hidden difference between the two sources.
