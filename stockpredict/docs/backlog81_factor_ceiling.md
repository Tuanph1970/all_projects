# Backlog #81 — should `volume_factor` be able to promote a pattern?

**Date:** 2026-10-20
**Study:** `ai-insights-service/tests/em1_factor_ceiling_study.py`
**Answer:** No. `FACTOR_CEILING` is now **1.0** — volume can only discredit.

---

## The question

`FR-EM-V7` chose deliberately asymmetric bounds, `[0.5, 1.15]`, reasoning that
E&M's volume evidence *"discredits better than it promotes"* — so 1.15 was
already the smaller half. `#70` then made the significance gate well-posed and
the tail cost became visible: against a bar set at the **geometry-only** 95th
percentile, a lucky volume reading lifted null survivors from **4.6 % to
21.7 %**.

That was never a contradiction — the mean comparison still passed, so volume
lowers noise confidence *on average*. It was an upper-tail effect, and the
question was whether that tail bought anything.

## The criterion, fixed before the run

> A ceiling above 1.0 earns its place only if it **increases detection power
> at a fixed false-positive rate**. For each candidate ceiling, set the gate at
> that configuration's **own** null 95th percentile per pattern — which holds
> the false-positive rate at 5 % by construction — and measure the share of
> planted patterns clearing it.

One point on a ROC curve at a fixed FPR, which is the only fair comparison:
comparing raw confidences across ceilings would reward a ceiling for inflating
every number.

## Result

| ceiling | planted cleared | TPR | null mean confidence |
|---|---|---|---|
| **1.00** | 9 / 13 | **69.2 %** | 0.6358 |
| 1.05 | 9 / 13 | 69.2 % | 0.6426 |
| 1.15 *(shipped)* | 8 / 13 | 61.5 % | 0.6562 |
| 1.30 | 8 / 13 | 61.5 % | 0.6730 |
| 1.60 | 4 / 13 | **30.8 %** | 0.6959 |

**Power never rises and eventually collapses.** The shipped 1.15 was *worse*
than no ceiling at all.

The mechanism is in the same table's last column. The ceiling lifts noise and
signal alike, but noise is far more numerous — about 1,400 null detections
against 13 planted — so the gate climbs faster than a planted pattern's
confidence does, and patterns that used to clear it stop clearing it. Raising
the ceiling is, in effect, raising the bar.

### The caveat that travels with the number

Only **13 planted patterns** are tested, so TPR moves in steps of 7.7 % and
69.2 % vs 61.5 % is literally one pattern. What carries the decision is not
that one step: it is that the direction is **monotone across five settings**,
that **no setting above 1.0 improves anything**, and that the null mean
confidence rises monotonically, confirming the mechanism independently.

---

## What changed

`FACTOR_CEILING = 1.0`, with the measurement written into the constant so the
next reader does not have to find this file. `FR-EM-V7`'s original 1.15 is
superseded by measurement, which is what `FR-EM-V11` reserved the right to do
for every default in EM-1.

Three tests needed restating, and two of them were encoding a stronger claim
than the SRS ever required:

* **`test_a_bullish_break_on_expanding_volume_is_rewarded`** asserted
  `volume_factor > NEUTRAL_FACTOR`, reasoning that "present expansion must
  help, or the rule would only ever be a penalty and `H1` would be satisfiable
  by a constant". `FR-EM-V3` only ever required that **absence penalises** —
  and the reasoning does not survive the change anyway: discrimination is
  intact either way, because a break *with* expansion sits at neutral while one
  *without* is penalised below it, and `H1` reads `volume_score`, which the
  factor bounds never touched. Restated as the relative claim — good volume
  must score better than bad — which is strictly stronger than an offset.
* **`test_a_pierce_with_no_follow_through_volume_confirms_the_trap`** likewise:
  a confirming verdict now withholds a penalty rather than granting a bonus.
  The discrimination it cared about is asserted by its sibling test, which is
  where it belongs.
* **`test_bounds_bracket_neutral`** is now deliberately false and is replaced
  by `test_volume_can_only_discredit`.

The EM-1 null baseline was regenerated, deliberately: confidences moved, so
the stored gates no longer matched them. Afterwards:

| | |
|---|---|
| gate pass rate | **5.1 % and 5.5 %** against a 5 % gate — still well-posed |
| mean confidence vs mean geometric | 0.630 vs 0.736 — volume lowers noise by ~14 % |
| detections tied at the gate | 0 → **17 (1.2 %)** |

That last row is a small, honest side-effect: with the ceiling at neutral, a
*neutral* factor of exactly 1.0 leaves `confidence == geometric_confidence`,
so exact ties reappear where `#70` had removed them. At 1.2 % it is far under
`TestTheGateIsNowUsable`'s 2 % guard, and nothing like the 29 % cliff #70
fixed — but it is the reason that guard is a threshold rather than a zero.

## Consequence for the earlier finding

`#70` reported that EM-1 moved null survivors 4.6 % → 21.7 % against a
geometry-only gate, and recorded the survivor count as *reported, not
asserted*, because any fixed gate either measured one arm against its own
distribution or against a foreign one. With the ceiling at neutral,
`confidence <= geometric_confidence` for every detection by construction, so
that promotion cannot happen at all and the count metric is now well-defined
in the one direction that matters.

Restoring it as an assertion is a small follow-up rather than part of this
change, and it is noted in `test_volume_null_fpr.py` where the decision lives.
