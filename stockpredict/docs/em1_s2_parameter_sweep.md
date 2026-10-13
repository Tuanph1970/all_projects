# EM-1 / S2 — parameter sweep and the evidence behind each default

**Satisfies:** `FR-EM-V11`, and SRS open questions 1–3. Resolves Backlog #72.

`CLAUDE.md` is blunt about why this exists: every magnitude in the SRS is
illustrative, E&M's own figures are 1940s–60s NYSE rules, and *a default that
has not been swept is an inherited guess*. This records what was measured, what
changed, and — just as important — what was left alone and why.

Reproduce with `python3 -m tests.sweep_params` from the ai-insights service.
Date: 2026-10-13.

## Metrics

Three, all stated as properties rather than magnitudes:

| metric | meaning | better |
|---|---|---|
| **H1 separation** | mean `volume_score` with volume aligned to price, minus the same with volume permuted | higher — it is the degree to which the rule reads the price–volume *relationship* rather than volume's level |
| **textbook − adverse** | the same statement on hand-built pairs: identical geometry, opposite volume script | higher |
| **H2 suppression** | `(mean composite − mean geometric) / mean geometric` over random-walk surrogates | more negative — confidence withdrawn from noise |
| **real spread** | verdict distribution over 18 real symbols | a *veto*: a setting that says the same thing about everything carries no information, however well it scores above |

---

## Open question 1 — `baseline_window`: **50 → 100** (changed)

| window | H1 separation | textbook − adverse | H2 suppression | top-verdict share |
|---|---|---|---|---|
| 20 | 0.1622 | 0.5546 | −13.10% | 52% |
| 50 | 0.1853 | 0.5974 | −13.13% | 52% |
| **100** | **0.1981** | **0.5987** | −12.86% | **48%** |

The margin over 50 is modest, so it was tested for robustness rather than
accepted from one sample — across **12 independent shuffle seeds**:

| window | mean | std | min | max |
|---|---|---|---|---|
| 20 | 0.1634 | 0.0322 | 0.1027 | 0.2140 |
| 50 | 0.1795 | 0.0325 | 0.1213 | 0.2335 |
| 100 | 0.1929 | 0.0330 | 0.1310 | 0.2420 |

Paired difference (100 − 50): **+0.0135 ± 0.0080, and 100 won on 12 of 12
seeds.** Consistent, so the change is justified.

Two things were checked before changing it, because a longer window could cost
availability:

- **It does not.** At the 100-bar lookback the UI actually requests
  (`helperService.getPatterns(symbol, lookbackBars = 100)`), **100% of
  detections still score** at every window tested — `_baseline_from` degrades
  to whatever history exists above `MIN_BASELINE_BARS` rather than failing.
- It is also the better reading of E&M's *"high for that stock in that
  period"*: ~5 months rather than ~2.5.

H2 is flat across the change (−12.20% / −11.77% after, vs −12.08% / −11.80%
before), so the gain is in H1 and costs nothing on the null.

## Open question 2 — `volume_factor` bounds: **(0.5, 1.15) kept**

The bounds scale the *factor*, not the score, so they cannot change H1
separation or any verdict label. The only question they settle is **how much
authority volume gets over the final number**.

| floor | ceiling | H2 suppression | max downgrade | max upgrade |
|---|---|---|---|---|
| 0.4 | 1.10 | −15.20% | 60% | 10% |
| **0.5** | **1.15** | **−11.70%** | **50%** | **15%** |
| 0.6 | 1.20 | −8.26% | 40% | 20% |
| 0.5 | 1.30 | −9.90% | 50% | 30% |
| 0.7 | 1.10 | −6.76% | 30% | 10% |

A floor of 0.4 suppresses noise best, and is still rejected: letting volume cut
a confidence by **60%** is more authority than *"volume is corroboration, not
the finding"* (`FR-EM-V7`) allows. Note also that raising the ceiling actively
*hurts* suppression — 1.30 gives −9.90% against 1.15's −11.70% — because a
higher ceiling upgrades noise too. The asymmetry the SRS guessed at is
confirmed: the floor should sit further from neutral than the ceiling.

## Open question 3 — the One-Day Reversal's long baseline: **confirmed at 120 bars**

Decided at V6b and left unchanged: `LONG_BASELINE_WINDOW = 120` compared
against the **98th percentile** rather than the maximum, for `EC-V5`'s reason —
one absurd vendor print as the window maximum would suppress every later
one-day reversal, permanently and silently. See §Backlog #72 below, which
sweeps the same window's thresholds.

## The governing rule threshold — `confirm_rvol`: **1.5 kept**

| `confirm_rvol` | H1 separation | textbook − adverse |
|---|---|---|
| 1.25 | 0.1869 | **0.6031** |
| **1.50** | 0.1958 | 0.5979 |
| 1.75 | **0.1971** | 0.5902 |
| 2.00 | **0.1971** | 0.5785 |

**The two metrics disagree**: H1 mildly prefers a higher threshold, the
textbook/adverse gap prefers a lower one. The H1 gain from 1.5 to 1.75 is
0.0013 — inside the 0.033 seed-to-seed noise measured above — while the
textbook gap loses 0.0077. So 1.5 sits at the knee and stays.

*A sweep bug worth recording:* the first run of this curve was perfectly flat
at every value, which read as "this parameter does not matter". It was not —
`PATTERN_RULES` captures `BreakoutRule` **objects** at import, so patching
`volume.BULLISH_BREAKOUT` reached nothing. The sweep now rebuilds the registry
with `dataclasses.replace`. A flat curve is a reason to check the harness
before concluding anything about the parameter.

---

## Backlog #72 — the climax flag: **rvol 2.5 → 2.0, progress 0.6 → 1.0** (changed)

At F3 the flag fired on **0 of 16 symbols**. Swept over **9,646 real bars
across 18 symbols**:

| rvol ≥ | progress ≤ | bars flagged | symbols |
|---|---|---|---|
| 1.5 | 0.6 | 9 | 5 |
| 1.5 | 1.0 | 12 | 8 |
| 1.5 | 1.5 | 17 | 11 |
| 2.0 | 0.6 | 1 | 1 |
| **2.0** | **1.0** | **2** | **2** |
| 2.0 | 1.5 | 5 | 5 |
| 2.5 | 0.6 | **0** | 0 |
| 2.5 | 1.0 | **0** | 0 |
| 2.5 | 1.5 | **0** | 0 |

**This corrects the F3 write-up.** F3 concluded the *progress* gate was
binding; the sweep shows it was **rvol**: at 2.5 the flag yields nothing at
*any* progress threshold, so it was unreachable rather than merely strict.

`rvol ≥ 2.0, progress ≤ 1.0` was chosen: 2 bars across 18 symbols over ~5
years is the once-in-years event E&M describe, where `1.5` (12 bars, 8 symbols)
is too common to call a climax. Confirmed live afterwards:

```
MSN  bar 133  rvol=2.29  progress=0.497
SSB  bar 539  rvol=2.418 progress=0.667
symbols with a climax: 2/18   (was 0/16)
```

Both are the right shape — enormous volume, price going nowhere.

**An important nuance for anyone wondering why the banner is never on screen.**
Both of those bars are *historical* — MSN's is index 133 and SSB's index 539 of
a ~1,326-bar series — and the flag reports the most recent climax **within the
requested window**. The Decision Console fetches 100 bars and this sweep used
250, so neither falls inside. Verified through the live API:

```
SSB  lookback=250  -> no        SSB  lookback=1000 -> YES rvol=2.418 prog=0.667
MSN  lookback=250  -> no        MSN  lookback=1000 -> no   (its bar 133 is trimmed)
```

So the threshold is now **reachable** rather than unreachable, which is what
#72 asked for — but a genuine E&M climax stays a once-in-years event, and the
banner will be absent on almost every screen. A flag that appeared often would
not be measuring a climax. This is also why the verification script *warns*
rather than fails when no climax is found.

---

## What was deliberately NOT swept

Honesty about coverage matters more than a longer table:

- **Each individual per-detector threshold** (the shoulder ratio 0.75, the
  double-top ratio 0.8, the drying thresholds 0.1/0.25, the suspect bands).
  Sweeping twelve rules jointly is a combinatorial exercise that the current
  harness — 6 planted frames and 4 adverse pairs — cannot resolve: the gradient
  per rule is smaller than the seed noise. They keep their E&M-derived defaults
  and are documented as such.
- **`anchor_window`** (3), which is deliberately tied to the detectors' own
  `swing_window` so a shoulder is read over the bars the detector called a
  shoulder. Sweeping it independently would break that correspondence.
- **`LONG_BASELINE_PERCENTILE`** (98). Settled on principle at V6b (`EC-V5`)
  rather than by metric, and the climax sweep above varied the thresholds it
  feeds rather than the percentile itself.

A future sweep wanting the per-rule gradients needs a larger planted corpus —
ideally labelled real formations rather than synthetic ones.

## Net effect of S2

| | before S2 | after S2 |
|---|---|---|
| H1 separation | 0.1853 | **0.1981** |
| H2 suppression | −12.08% / −11.80% | −12.20% / −11.77% |
| climax flag on real data | 0 / 16 symbols | **2 / 18 symbols** |
| full test suite | 477 passed | 477 passed |

One test needed changing, and it was coupled to the old default rather than
wrong: `test_none_inside_the_window_is_skipped_not_imputed` asserted
`bars_used == 40` with a comment reading *"50-bar window minus 10 holes"*. It
now derives the expectation from `DEFAULT_BASELINE_WINDOW`, so it keeps
expressing its property — holes are skipped, not imputed — through any future
sweep.
