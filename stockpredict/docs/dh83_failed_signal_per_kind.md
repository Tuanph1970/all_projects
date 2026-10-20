# Backlog #83 — do the live failed-signal verdicts predict anything?

**Date:** 2026-10-20
**Study:** `decision-helper-service/tests/dh83_failed_signal_per_kind_study.py`
**Answer:** **No kind is validated. One is backwards.** The live path can no
longer act on any of them.

---

## The exposure

Ten verdict kinds reach `decision/orchestrator.py` and shape what a user is
shown. Before today:

* `#79` measured the two **pattern-based** kinds over 6,797 causal scans.
  Neither predicted anything, and `HS_TARGET_FAILURE / SHORT` was
  significantly **backwards**. Both were demoted below `OVERRIDE_THRESHOLD`.
* `#82` measured the rest **as a group** inside the backtest, found them no
  better than nothing, and switched the override off there. But that was a
  pooled verdict on a measurement bench — not the live path, and silent on
  *which* kinds carried it.

## Method, following #79

Causal — the frame is sliced *before* scanning, and S/R levels are recomputed
from that same slice. Non-overlapping — samples spaced at least `horizon` bars
apart per symbol. Against the **no-verdict baseline on the same sampled
dates**, not an unconditional average over a different population.

And **signed by each verdict's own claim**: a LONG verdict is right when price
rises, a SHORT verdict when it falls, so the *edge* is
`(mean − baseline) × (+1 LONG, −1 SHORT)`. Positive means the verdict added
value in the direction it implied.

### Criterion, fixed before the run

| outcome | test | consequence |
|---|---|---|
| **KEEP** | edge positive and significant at **>1 horizon** | validated, stays |
| **REMOVE** | edge significantly **negative** at any horizon | actively misleading |
| **UNVALIDATED** | indistinguishable from baseline | not evidence; stop acting on it |

"Indistinguishable" is deliberately not a pass. A verdict shown to a user
asserts something; one that cannot be shown to assert anything is noise with a
label.

---

## Result

Baselines: +0.16% at 10 sessions (n=716), +0.95% at 20 (n=331), +2.75% at 60
(n=111).

| kind / direction | edge@10 | t | edge@20 | t | edge@60 | t | verdict |
|---|---|---|---|---|---|---|---|
| BEAR_TRAP / LONG | +0.55 | +1.31 | −0.55 | −0.70 | −2.61 | −0.85 | unvalidated |
| BULL_TRAP / SHORT | +0.21 | +0.54 | +1.54 | +1.84 | +3.06 | +1.23 | unvalidated |
| FALSE_TL_BREAK / LONG | −0.46 | −0.71 | −1.68 | −1.47 | −2.65 | −0.76 | unvalidated |
| FALSE_TL_BREAK / SHORT | +0.17 | +0.31 | +2.09 | +2.00 | −1.28 | −0.31 | unvalidated |
| FILLED_GAP / LONG | +0.52 | +1.62 | −0.36 | −0.53 | +0.06 | +0.03 | unvalidated |
| FILLED_GAP / SHORT | −0.09 | −0.30 | +0.03 | +0.05 | +1.72 | +1.00 | unvalidated |
| **OPPOSITE_BREAKOUT / LONG** | −0.38 | −0.95 | **−1.81** | **−2.12** | **−4.46** | **−2.06** | **BACKWARDS** |
| OPPOSITE_BREAKOUT / SHORT | −0.53 | −1.56 | −0.08 | −0.09 | +0.73 | +0.24 | unvalidated |
| RETURN_TO_SPIKE / LONG | +0.84 | +1.33 | −0.68 | −0.58 | +25.47 | +1.59 | unvalidated (n=5) |
| RETURN_TO_SPIKE / SHORT | −0.78 | −0.84 | −1.16 | −0.79 | +7.01 | +2.97 | unvalidated (n=5) |
| WRD_RETURN / LONG | +2.12 | +1.71 | +0.71 | +0.35 | −7.65 | −1.58 | unvalidated |
| WRD_RETURN / SHORT | +0.21 | +0.15 | −2.42 | −0.75 | +4.90 | +0.97 | unvalidated |

**Nothing is KEEP.** Not one of the twelve pairs clears the bar.

Note `RETURN_TO_SPIKE / SHORT` at 60 sessions: edge +7.01 at t = +2.97, which
*is* significant — on **n = 5**. The two-horizon requirement is what stops that
being read as a finding, which is why it was pre-registered rather than
decided afterwards.

### Completeness

Seven kinds are pattern-independent and all fired; their twelve
(kind, direction) pairs are the table above. **Five kinds are
pattern-dependent** and cannot fire without the ai-insights pattern payload:
`DOUBLE_TOP_BREAK` and `HS_TARGET_FAILURE` (both already measured and demoted
by `#79`), plus `COUNTER_ANTICIPATED_FLAG`, `ROUNDING_BREAK` and
`FUTURE_RELIABILITY` — **still unmeasured**, because reaching them needs the
two-phase cross-service scan `#79` used. Logged as **#89**.

---

## What changed

Following `#79`'s precedent rather than inventing a mechanism:

* **`OPPOSITE_BREAKOUT / LONG` is suppressed**, not capped. A capped-but-visible
  verdict still tells a user something, and this one tells them something
  false.
* **Every other kind is capped at `UNVALIDATED_SEVERITY_CAP = 0.45`**, below
  `OVERRIDE_THRESHOLD = 0.5`, so none can change a recommendation on its own.
  They are still *returned* — "a recent formation failed" is a legitimate
  reason to look — and the cap is recorded on the evidence rather than applied
  silently.
* **Not inverted.** Inverting a signal because it measured backwards on one
  32-symbol sample is fitting to the sample. Suppression asserts only what the
  measurement supports: showing it is worse than showing nothing.

### An interaction that had to be resolved, not papered over

Capping inside `detect_failed_signals` made `#82`'s backtest override
**structurally unreachable** — switching it on would have done nothing. That
is precisely the silent no-op this codebase has paid for three times (EM-1's
sweep, `#78`, `#84`'s walk-forward).

So the policy is scoped to where the risk is: `apply_validation_policy`
defaults to **on**, protecting the live path, and the backtest passes `False`
when its override is explicitly enabled — because the point of that flag is to
re-measure the override as it was. A test asserts the opt-out actually changes
the output, so it cannot quietly become a no-op either.

12 tests pin the policy; decision-helper 751 passed, 9 skipped.

## What would change the answer

1. **The three unmeasured pattern-dependent kinds** (#89) — they may contain
   the one that works, and #83 cannot say.
2. **More history.** Every edge here is estimated over 5.3 years on 32
   symbols, and the 60-session rows run to n = 5 for the rarer kinds.
3. **A severity recalibration.** These severities were hand-set (`0.45 +
   strength × 0.05 + …`). `#79` set its two from measurement; nothing here has
   been calibrated against outcomes, only capped.
