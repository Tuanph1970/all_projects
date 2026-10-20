# Backlog #89 — the verdict catalogue, counted honestly

**Date:** 2026-10-20
**Code:** `decision-helper-service/app/services/signal/failed_signal.py`
**Tests:** `tests/test_failed_signal_catalogue.py` (9)
**Outcome:** **no study was needed. #89's premise was wrong, and the error was
mine.**

---

## What #89 asked for, and why it was the wrong question

`#89` said three verdict kinds — `COUNTER_ANTICIPATED_FLAG`,
`ROUNDING_BREAK`, `FUTURE_RELIABILITY` — "remain unmeasured because they need
the ai-insights pattern payload", and asked for the two-phase cross-service
scan `#79` used in order to measure them.

They are not unmeasured pending a scan. They are **unreachable by
construction**, and `#73` and `#78` had already established exactly that —
with `TestDetectorsStillUnreachable` asserting it and the adapter's docstring
spelling out each reason:

| kind | why it cannot fire |
|---|---|
| `ROUNDING_BREAK` | needs `pattern_type` `ROUNDING_TOP`/`ROUNDING_BOTTOM`, and **ai-insights has no rounding detector**, so nothing maps onto it. |
| `FUTURE_RELIABILITY` | reads `reliability_score`, which the payload does not carry and which is not derivable from it, so the adapter does not invent one. |
| `COUNTER_ANTICIPATED_FLAG` | needs a flag that has already broken counter to its direction, but `FlagDetector` reports flags **still forming** — across 14 real flags the last key bar was the final bar of the scan every time. Inferring the break from price against the neckline labelled every unresolved bull flag a downward break, which is the false positive `#78` removed. |

No scan reaches them. Building the two-phase harness would have measured
nothing and taken a day to find that out.

## The error, and where it came from

I wrote #89's premise in #83, from the fact that the three did not fire in my
single-phase study. The inference — "they need the other harness" — was
plausible and wrong, and the codebase already contained the answer.

The same mistake produced a second, more visible one. `#82` and `#83` both
describe **"ten verdict kinds driving live recommendations"**. That figure
came from counting detector functions. The honest accounting:

| | count | |
|---|---|---|
| kinds defined | 12 | |
| **unreachable** | **3** | `#73`, `#78` |
| **reachable** | **9** | |
| of which measured at `#83` | 7 | pattern-independent, per kind and per direction |
| of which measured at `#79` | 2 | 6,797 causal scans |
| **unmeasured** | **0** | |

So **the catalogue is fully measured**, and the answer is uniform: none of it
predicts anything. Seven were unvalidated and one backwards at `#83`; the two
at `#79` predicted nothing and one was backwards there too.

### Why the miscount happened, which is the part worth keeping

It was not carelessness. The shape of this work invited it: each study
returned "nothing here", and each time the unmeasured remainder was the only
place left where the signal might be hiding. Three times I wrote up a null
result and pointed at what had not been covered yet — correctly at `#79`
(which led to `#82`) and `#82` (which led to `#83`), then incorrectly at
`#83`.

## What changed

No measurement. The accounting is now **machine-readable** instead of living
in prose:

* `ALL_KINDS` — declared, rather than discovered by grepping for `kind=`.
* `UNREACHABLE` — kind → upstream reason, each citing where it was
  established.
* `reachable_kinds()` — the nine. Any statement about what influences
  behaviour should read this; counting detector functions overstates it by
  three.
* `MEASURED_BY` — kind → the backlog item that measured it, asserted to cover
  every reachable kind.

Nine tests pin it, including one that runs the detectors over real bars with a
real adapted payload and fails if an "unreachable" kind ever fires — which is
the signal that the registry, and this accounting, have gone stale.

## Why the three are kept rather than deleted

They are dead code today, and deleting dead code is usually right. Not here:
each one documents a **real upstream gap** — no rounding detector, no
reliability score, flags reported mid-formation — and deleting them would
delete the only machine-checked record of those gaps.

If ai-insights ever grows a rounding detector, `ROUNDING_BREAK` becomes live
and `test_none_of_them_appears_with_a_full_pattern_payload` starts failing.
That is the signal to measure it, and it arrives automatically.

What the registry removes is the *cost* of keeping them: they can no longer
inflate a count of what drives live behaviour, which is the only harm they
were actually doing.
