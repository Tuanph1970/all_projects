# EM-8 M2 — are pattern objectives reached? A calibration

**Date:** 2026-10-21
**Backlog:** `#68` (question (a) of three)
**Harness:** `ai-insights-service/tests/em8_calibration.py` · **Tests:** `tests/test_em8_calibration.py` (23)
**Answer:** **No.** Not one of E&M's five measuring rules beats a matched
random entry at any horizon, and three are **significantly worse than chance**.
The only objective in the catalogue that does beat the null is one **E&M never
sanctioned**.

---

## What was measured

Every detector, run causally over the `#87` deep history — 92 symbols, 320,237
bars, 19.7 years — in a **250-bar window**, which is exactly what production
hands them (`decision-helper` requests `lookback_bars=250`; `insights_service`
does `df.tail(250)`). For each pattern episode: was the measured objective
touched within 10 / 20 / 60 sessions, and by how much was it exceeded when it
was.

**438,300 episodes**, 1,541 excluded as vacuous (`EC-M1`), 263 for a short
tail (`EC-M2`); inference runs on the non-overlapping sample, which is far
smaller (90–22,615 observations per cell).

> **Criterion, pre-registered.** Completion must **exceed** a matched
> random-entry null — same symbol, same direction, same objective
> **distance** — at **two or more** horizons, clustered by symbol, with Holm
> across families.

## Result: E&M's rules

| family | h | syms | obs | reached | null | edge | t | p | median overrun |
|---|---|---|---|---|---|---|---|---|---|
| Double (123) | 10 | 92 | 1,705 | 19.3% | 25.8% | **−6.5%** | −4.67 | <0.0001 | 1.58× |
| Double (123) | 20 | 92 | 883 | 27.6% | 34.0% | **−6.4%** | −3.20 | 0.0014 | 1.77× |
| Double (123) | 60 | 89 | 328 | 46.0% | 48.3% | −2.3% | −0.97 | 0.334 | 2.13× |
| Flag/Pennant (120) | 10 | 92 | 22,615 | 13.7% | 22.7% | **−9.0%** | **−18.80** | <0.0001 | 1.37× |
| Flag/Pennant (120) | 20 | 92 | 11,411 | 26.6% | 31.3% | **−4.7%** | −11.41 | <0.0001 | 1.52× |
| Flag/Pennant (120) | 60 | 92 | 3,791 | 47.3% | 47.1% | +0.2% | +0.19 | 0.849 | 1.94× |
| H&S (117) | 10 | 92 | 386 | 15.8% | 22.1% | **−6.3%** | −2.72 | 0.0065 | 1.77× |
| H&S (117) | 20 | 81 | 206 | 24.8% | 25.7% | −1.0% | −0.32 | 0.748 | 1.46× |
| H&S (117) | 60 | 57 | 90 | 36.7% | 38.8% | −2.1% | −1.54 | 0.124 | 2.07× |
| Runaway gap (121) | 10 | 86 | 627 | 29.7% | 27.0% | +2.7% | +1.51 | 0.131 | 1.76× |
| Runaway gap (121) | 20 | 79 | 339 | 37.2% | 33.1% | +4.1% | +1.23 | 0.220 | 1.95× |
| Runaway gap (121) | 60 | 63 | 115 | 53.0% | 48.5% | +4.5% | +0.81 | 0.417 | 2.40× |
| Triangle (118) | 10 | 92 | 1,248 | 21.2% | 22.4% | −1.3% | −0.87 | 0.387 | 1.98× |
| Triangle (118) | 20 | 90 | 626 | 27.5% | 28.7% | −1.2% | +0.48 | 0.629 | 1.96× |
| Triangle (118) | 60 | 79 | 223 | 45.7% | 43.8% | +2.0% | +1.21 | 0.228 | 1.95× |

**0 of 3 horizons for every family. The criterion fails five times over.**

### Three of them are reliably *worse* than chance

This is the part I did not expect. Flag/Pennant at **t = −18.80** on 22,615
observations across 92 symbols is not a power problem in either direction: a
flag's half-mast objective is reached **9 percentage points less often** than
a random entry aiming the same distance in the same direction. Double tops and
H&S are the same story at smaller scale.

E&M say of the flag that it *"carries with it a most explicit measuring rule,
and one which works out with amazing accuracy."* On VN data it works out worse
than a coin aimed at the same distance.

**A correction to my own output.** The first run printed "survives" in the
Holm column for Double, Flag/Pennant and H&S. That was a bug in the harness,
not a result: it fed the smallest p-value into Holm **regardless of sign**, so
a family that was significantly *worse* than chance printed as surviving. The
criterion is one-sided — completion must *exceed* the null — so the corrected
reading is **"no" for all five**, and the harness now only considers cells
with `t > 0`. A test pins it.

## Result: the objectives E&M never sanctioned

| family | h | obs | reached | null | edge | t | p | median overrun |
|---|---|---|---|---|---|---|---|---|
| **[ours] Trap** | 10 | 807 | 64.2% | 53.9% | **+10.3%** | **+5.21** | <0.0001 | 2.55× |
| **[ours] Trap** | 20 | 429 | 72.0% | 62.4% | **+9.6%** | **+4.53** | <0.0001 | 3.41× |
| **[ours] Trap** | 60 | 143 | 81.8% | 72.7% | **+9.1%** | **+3.89** | 0.0001 | 3.94× |
| [ours] Wide-Ranging Day | 10 | 1,033 | 36.5% | 34.7% | +1.8% | +0.57 | 0.569 | 1.59× |
| [ours] Wide-Ranging Day | 20 | 566 | 48.2% | 44.9% | +3.3% | +0.42 | 0.678 | 1.90× |
| [ours] Wide-Ranging Day | 60 | 170 | 63.5% | 57.4% | +6.1% | +1.81 | 0.070 | 2.49× |

**The bull/bear trap objective passes all three horizons and survives Holm** —
the only thing in the catalogue that does. Its target is a mean-reversion
projection from a level price has just falsely pierced
(`level ∓ (close − level)`), and it beats a distance-matched, direction-matched
null by 9–10 points at every horizon.

Keeping E&M's rules and ours in separate tables was `FR-EM-M4`, written before
any of this was measured. It is the reason this result is visible at all
rather than diluted into a pooled average.

## The overrun, and what it does and does not show

Median overrun is **1.4–3.9×** across every family: when an objective *is*
reached, price typically carries 50–290% further. That is consistent with
E&M's insistence that an objective is *"most emphatically … only a minimum"*.

**But it is not evidence for the rules**, and the distinction matters. The
overrun is measured only on the episodes that completed, and any path that
reaches its target has an excursion ≥ 1 by construction. A random entry that
reached the same distance would also overrun. The overrun describes the
objectives; it does not establish that patterns overrun *more* than chance,
and no null was run for it. Reported because `FR-EM-M5` required it, framed as
description.

## Caveats, including two of my own errors

1. **Episode identity is permissive.** Episodes are keyed on absolute key
   bars, so a detector whose fitted key bars drift by one bar registers a new
   episode — which is why 438,300 looks implausibly large against 320,237
   bars. It does not affect the inference, which runs on the non-overlapping
   sample, but the episode count should not be read as "438,300 distinct
   patterns".
2. **My runtime estimate was wrong by 6×.** I measured 5.5 ms/bar for
   detection and predicted ~30 minutes; the run took **2h53m**, because the
   timing excluded the null draws and outcome scoring. The estimate was used
   only to decide against a stride — which it still supports — but it was not
   a good estimate.
3. **The window is production's, not "all history".** The detectors search
   whatever frame they are handed, and a 200-bar slice disagrees with the full
   prefix on 76% of (symbol, bar) points. 250 bars is what production uses, so
   it is what was calibrated. A different window would give different numbers,
   and that is a property of the detectors rather than of this study.
4. **This measures completion, not profitability.** An objective reached less
   often than chance is not automatically a bad exit — question (c) asks that
   separately, which is why (a) was never a gate.

## What this means for the remaining work

Question (a) is answered: **E&M's measuring rules carry no information about
whether their objectives will be reached on this market, and the most
celebrated of them is actively worse than chance.**

That does not by itself retire `MEASURED_MOVE` — the plan was explicit that (a)
does not gate (c), because *"not special" is not "not useful"* and an objective
can be reached reliably and still be a poor exit. **M3 remains the gate**, and
it now runs with a strong prior: priority 1 in `target_module` is currently
occupied by projections that are reached less often than a random entry of the
same size.

Two things M3 should carry forward:

* The **trap objective** is the one measured positive, so the comparison
  should let it be visible rather than averaging it away.
* The **runaway gap** is the only E&M family positive at all three horizons
  (+2.7 / +4.1 / +4.5%, all ns) — and it is the one whose formula `M1` had
  just corrected. Suggestive only; n falls to 115 by the 60-session horizon.

| | |
|---|---|
| E&M's five measuring rules | **0 of 3 horizons each**; three significantly *worse* than chance |
| the flag's "amazing accuracy" | **−9.0% vs the null at t = −18.80** |
| our trap objective | **+9 to +10 points, all three horizons, survives Holm** |
| objectives as minima | **supported descriptively** (1.4–3.9× overrun), with no null |
| `MEASURED_MOVE` | still priority 1; **M3** decides |
