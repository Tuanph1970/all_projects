# EM-1 / S1 — downstream effect of the composite confidence on decision-helper

**Answers:** SRS open question 5 — *"Does the composite-confidence change
(`FR-EM-V7`) shift `decision-helper`'s behaviour enough to need its own
before/after run?"*

**Answer: no, and not because the effect is small — because there is no effect.
`decision-helper` never reads pattern `confidence`.** Measured three
independent ways below, on the live stack against real market data.

Date: 2026-10-13. Read-only throughout; nothing in `decision-helper` was
changed, per the task definition.

---

## Why this task existed

`FR-EM-V7` deliberately changed `confidence` on every `PatternMatch`, and that
number goes out over HTTP to another service. Shipping that without measuring
the consequence would be exactly the unverified claim `CLAUDE.md` forbids. The
SRS flagged `target_module` and `failed_signal` as the likely consumers.

## 1. Static — what decision-helper actually reads from a pattern

Every pattern-field access across `decision-helper-service/app/`:

| field | reads | changed by EM-1? |
|---|---|---|
| `pattern_type` | 16 | **no** — `"bullish"` / `"bearish"` / `"neutral"`, untouched |
| `neckline` | 1 | **no** — geometric, asserted bit-identical by `H1` |
| `measured_move_target` | 1 | **no** — geometric, same |
| `status`, `break_direction`, `reliability_score`, `confirmation_level`, `implied_direction`, `breakout_level` | 1 each | n/a — **ai-insights does not send these at all** (see §4) |
| `confidence` | **0** | — |
| `pattern_name` | **0** | (EM-1 *can* change it — V6b re-labels a gap — but nothing reads it) |

`target_module.py` projects from `measured_move_target`. `failed_signal.py`
reads `pattern_type`. Neither mentions `confidence`.

The four `confidence` hits elsewhere in the service are unrelated: regime
confidence from analysis-service (`regime/classifier.py`), signal confidence
(`decision/orchestrator.py`), and the recommendation's own figure
(`scheduler.py`).

## 2. Empirical — do the consumed fields move?

For 16 symbols × 250 bars of real data, the full detector catalogue was run
twice on identical price series: once **with** the volume column (EM-1 active)
and once **without** it (`EC-V3`, geometry only), comparing exactly the fields
§1 shows decision-helper consumes.

```
symbols=16  patterns=119  confidence_moved_by_volume=115
symbols where the decision-helper-consumed fields are identical: 16/16
```

So EM-1 moved **115 of 119** confidences while changing **nothing**
decision-helper reads, on every symbol tested. No gap was re-labelled in this
sample (0 of 119), though V6b permits it.

## 3. End-to-end — decision-helper on the live stack

`POST /helper/recommend`, authenticated, `bar_date=2026-10-06`:

| symbol | action | signal | confirmed | entry | stop | target | confidence |
|---|---|---|---|---|---|---|---|
| VHM | BUY | SR_BREAKOUT | yes | 69.00 | 68.13 | 71.30 | 0.950 |
| TCB | BUY | SR_BREAKOUT | yes | 32.45 | 31.24 | 33.94 | 0.882 |
| POW | WAIT | — | no | — | — | — | 0.000 |
| STB | WAIT | — | no | — | — | — | 0.000 |

That `confidence` is `final_confidence` from `confirmation/layer.py`, built
from the signal's own confidence modulated by regime and RSI. **`layer.py`
contains zero references to patterns** — so the number a user sees on the
Decision Console's action card is not, and never was, downstream of pattern
confidence.

Note the targets come from `SR_BREAKOUT` signals, not from pattern evidence,
which is consistent with §1: `target_module` prefers a measured move when a
pattern supplies one and falls back to S/R or a fixed R:R otherwise.

## 4. What this investigation turned up instead

**`failed_signal.py`'s pattern-based detectors are dead code.** They require

```python
if p.get("pattern_type") not in ("FLAG_BULL", "FLAG_BEAR"): continue
if p.get("status") != "ACTIVE":                             continue
actual_break = p.get("break_direction")
```

but ai-insights sends `pattern_type` ∈ `{bullish, bearish, neutral}` — verified
live across 6 symbols — and sends **no** `status` or `break_direction` field at
all. Each of the three guards fails independently, so these detectors have
never fired. Logged as **Backlog #73**.

This is a pre-existing defect, unrelated to EM-1, and it is the reason the
SRS's worry was misplaced: the consumer it worried about was not wired up.

## Conclusion

1. **No before/after run of decision-helper is required**, because its inputs
   are provably unchanged — a stronger result than "the difference is small".
2. The composite confidence is visible only where EM-1 put it: the two UI
   screens (F1, F2) and the `/insights/patterns/` payload.
3. Any future consumer that *does* threshold on pattern `confidence` inherits
   the EM-1 behaviour change, so this document should be re-read before wiring
   one up. `geometric_confidence` is on the payload precisely so a consumer can
   opt out.
4. Fix Backlog #73 before claiming the pattern-based failed-signal detectors
   contribute anything — and note that fixing it **would** newly expose
   decision-helper to the pattern payload, at which point §1's table changes
   and this comparison must be redone.

## Reproducing

```bash
# §2 — the decisive comparison
cd stock_microservices/services/ai-insights-service   # see the Sessions Log
                                                      # entry for 2026-10-13 S1
# §3 — the live calls
./scripts/verify-em1-volume.sh                        # payload-level check
```

A throwaway account (`em1_s1_probe` / `em1.s1.probe@example.com`) was
registered on the **local** stack to obtain a token for §3. It has no
portfolio, holdings or preferences; delete it whenever convenient.
