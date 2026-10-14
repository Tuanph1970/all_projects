# Backlog #78 — calibrating the revived failed-signal detectors

Backlog #73 made three pattern-based failed-signal detectors reachable for the
first time. They then fired on **100% of symbols**, which is the same as
carrying no information. This is what was measured and changed.

Date: 2026-10-14. Sample: 20 real VN symbols, 250 bars each, patterns from the
live `/ai/insights/patterns/{symbol}` scan.

## The baseline was indefensible

| detector | fired on |
|---|---|
| `DOUBLE_TOP_BREAK` | **20/20 (100%)** |
| `COUNTER_ANTICIPATED_FLAG` | 14/20 (70%) |
| `HS_TARGET_FAILURE` | 14/20 (70%) |
| **any of the three** | **20/20 (100%)** |

Two separate causes, one of them mine.

## Cause 1 — stale formations

ai-insights returns every pattern it finds across the lookback window, and the
detectors judged all of them. Age of the triggering formation, measured from
its last key bar:

| pattern | n | median age | p90 | max |
|---|---|---|---|---|
| Head and Shoulders | 12 | **86 bars** | 142 | 201 |
| Inverse H&S | 15 | 39 | 175 | 202 |
| Double Top | 20 | 17 | 37 | 138 |
| Double Bottom | 20 | 14 | 68 | 87 |
| Flag | 14 | **0** | 0 | 0 |

`_hs_target_failure` fires when an H&S exists and price is back above its
neckline. The neckline sits *below* the formation, so anything that did not
subsequently collapse satisfies it — and at a median age of 86 bars the verdict
means "an H&S from four months ago did not reach its target". True, and useless
today.

**Fix:** drop formations older than `MAX_PATTERN_AGE_BARS`, measured **inside
ai-insights' own frame** via `lookback_bars`. Using decision-helper's bar index
would be wrong whenever the two services hold different history — with 500
local bars against a 250-bar scan, every pattern would look 250 bars old.

### The sweep

| age limit | HS_TARGET | DOUBLE_TOP | FLAG | any |
|---|---|---|---|---|
| 3 | 0/20 | 1/20 | 0/20 | 5% |
| 5 | 0/20 | 5/20 | 0/20 | 25% |
| **10** | **1/20** | **6/20** | **0/20** | **30%** |
| 15 | 3/20 | 13/20 | 0/20 | 65% |
| 20 | 3/20 | 14/20 | 0/20 | 70% |
| 30 | 5/20 | 15/20 | 0/20 | 85% |
| 60 | 8/20 | 18/20 | 0/20 | 100% |
| 250 (no limit) | 14/20 | 20/20 | 0/20 | 100% |

**10 bars chosen.** Two trading weeks, so the verdict is about a live
situation, and it sits at the knee: 10 → 15 more than doubles the rate
(30% → 65%) as stale formations flood back in. 3 and 5 are defensible too; 10
was preferred as the longest limit still well clear of that cliff.

## Cause 2 — a false-break inference, which was my own bug

The #73 adapter derived `break_direction` from the last close against the
neckline when EM-1 had located no penetration. For a bull flag trading below
its upside breakout level that reads as "broke downward", when the truth is
"has not broken at all" — so `_counter_anticipated_flag` labelled every
unresolved bull flag a failure.

**Fix:** `break_direction` is set only from a located penetration. Never
inferred.

## And a correction to #73: two of five, not three

`_counter_anticipated_flag` is **unreachable**, and the Flag row above is why:
across 14 real flags the last key bar was the final bar of the scan **every
time**. `FlagDetector` reports flags that are still forming, so within one scan
the flag has not broken yet and a counter-break is unobservable — whatever the
age limit. Its earlier firings were entirely the false inference above.

Detecting a genuine counter-break needs the flag's lower boundary or a
subsequent bar, and the payload carries neither. So the honest tally from #73
is **two** detectors revived, not three:

| detector | state | why |
|---|---|---|
| `_hs_target_failure` | **live** | — |
| `_double_top_break` | **live** | — |
| `_counter_anticipated_flag` | unreachable | flags are reported mid-formation |
| `_rounding_break` | unreachable | ai-insights has no rounding detector |
| `_future_reliability` | unreachable | `reliability_score` is never sent |

## Live effect

Same symbols, same `bar_date=2026-10-06`:

| symbol | after #73 | after #78 |
|---|---|---|
| VHM | HS_TARGET_FAILURE · REVERSE | HS_TARGET_FAILURE · REVERSE |
| TCB | COUNTER_ANTICIPATED_FLAG · REVERSE | DOUBLE_TOP_BREAK · REVERSE |
| FPT | HS_TARGET_FAILURE · HOLD | **None** · HOLD |
| VNM | COUNTER_ANTICIPATED_FLAG · WAIT | DOUBLE_TOP_BREAK · WAIT |
| DPG, VND | None | None |
| STB, POW | BULL_TRAP | BULL_TRAP |

Every `COUNTER_ANTICIPATED_FLAG` is gone — those were the false positives.
FPT's verdict is gone because its H&S was stale. The verdicts that remain come
from formations completed within the last ten bars.

## What is still not established

The firing rate is now 30% rather than 100%, which makes the detectors
informative. It does **not** establish that they are *right*. Nobody has
checked whether a `DOUBLE_TOP_BREAK` verdict predicts anything, because these
detectors were dead for their whole existence and there is no outcome study.

`VHM` and `TCB` still resolve to **REVERSE** on the strength of a pattern
failure. Treat that as "a recent formation failed" — a reason to look, not a
validated signal. An outcome study against forward returns, of the kind EM-1's
`C4` benchmark demands of its own rules, is the next honest step and is not
done here.
