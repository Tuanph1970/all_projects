# Backlog #141 — Shape-specific squeeze and MA thresholds for FLAG bases: PRE-REGISTRATION (Part 1)

**Date:** 2026-11-10
**Status:** Part 1 — parameters, variants and the decision rule fixed. Written and
committed **BEFORE** the study script exists.
**Scope:** `docs/SRS_momentum_scanner.md` §15.4; Backlog #141.
**Subject:** `services/decision-helper-service/app/services/scanner/base.py` —
`squeeze_max_ratio`, `dryup_max_ratio`, `ma_proximity_pct` as applied to
`SHAPE_FLAG` windows.

---

## 0. Why this document exists before the code

Same rule as S-5a and `tests/em4_universe_thickness.py`: *nothing here may be
tuned against its own output.* It matters more for this study than for any
before it, because **#141 is the one question in the scanner where the tempting
answer and the correct answer point in opposite directions.**

The flag shape currently contributes ~0 candidates. The three clauses after
`base_found` reject 85 of the 87 flags the detector finds (SRS §15.3). Loosening
those three numbers until flags survive would make the feature *look* productive
immediately, and would convert a working filter into a decorative one — Backlog
#135's trap exactly. A screen that always has rows is not a better screen.

So the thresholds below are **candidate hypotheses with a pre-committed decision
rule**, not a search for values that let flags through. If the rule says keep the
status quo, the status quo is kept and the flag shape stays at ~0 contribution.
That is a permitted outcome of this study and, given §15.3, a likely one.

## 1. The question, stated narrowly

Each clause was calibrated on a 10–60 bar flat base. A flag is 3–15 bars sitting
immediately after a sharp pole. **Is each clause measuring the wrong thing on a
flag, or measuring the right thing and correctly saying "not a setup"?**

That is a question about the MEASURE, not only about the cut-off — which is why
§4 pre-registers one re-specified measure per clause rather than a grid of looser
numbers. A looser number on a degenerate measure is noise with a friendlier face.

**NOT being tested:** whether flags are a real pattern (they are; the detector is
tested from both sides of every threshold and cross-checked against ai-insights'
`FlagDetector`, EC-S3). **NOT being tested:** anything about FLAT bases. No flat
threshold, and not the flat-before-flag search order, may be touched by this
study — the order is load-bearing and `test_scanner_base.py` asserts it.

## 2. Data and universe — unchanged from S-5a

- The 93 symbols in `stock_prices`, 2021-03-15 → 2026-11-06.
- `ScanConfig()` defaults with `seam_allowlist=KNOWN_PROVIDER_SEAMS`. The ONLY
  parameters this study varies are the three named above, and only on windows
  with `shape == SHAPE_FLAG`. A FLAT window is assessed by production rules in
  every arm.
- Read-only: no DB writes, no service change, no scheduler change.
- Scan dates: every trading date with ≥ 200 prior bars, not a sample. §15.3's 242
  sampled dates are why n was small enough to be fragile; the full 1,185 dates
  are available and cost nothing extra.

### 2.1 One instrumentation change, declared in advance

The pole-relative variants (§4) need the pole's bounds, and `BaseWindow` does not
carry them. `detect_flag_base` will gain `pole_start_index` / `pole_end_index` as
**optional fields, `None` for FLAT**. This is instrumentation: it adds no clause,
changes no threshold and must not change a single verdict. The commit that adds
it ships a test asserting the full 1,185-date candidate set is **byte-identical**
before and after (the VT-2 reproducibility harness already does this comparison).
If it is not identical, the change is wrong and is reverted, not accepted.

## 3. Episodes, not candidate-days — EPISODE_GAP_BARS = 20

Unchanged from S-5a §3, for comparability: an episode is the first date a symbol
becomes a candidate after ≥ 20 trading bars of not being one. A flag resolves
faster than a flat base, so this will group less aggressively here; that is a
property of the shape, not a reason to change the constant mid-study.

## 4. The variants — one re-specified measure per clause, fixed now

Each clause gets exactly **two** settings: production (`P`) and one shape-specific
alternative (`S`). One alternative each, chosen from mechanism and written down
before any ratio distribution is inspected. A grid of three or four values per
clause would be 27–64 combinations against a few hundred episodes, which is how a
sweep finds a winner that does not exist.

### 4.1 `range_contraction`

- **P:** last-third TR / first-third TR ≤ 0.75, thirds of the base window.
- **S:** last-third TR / **mean pole TR** ≤ 0.75.
- *Why:* on a 5-bar flag a "third" is one bar, so P compares one bar's range to
  one other bar's and calls the result contraction. The mechanism being looked
  for is *the pause is quieter than the thrust that preceded it* — and the thrust
  is the pole, which P never looks at. S states that directly and is better
  defined on a short window.

### 4.2 `volume_dryup`

- **P:** last-third volume / base-mean volume ≤ 0.80.
- **S:** last-third volume / **mean pole volume** ≤ 0.80.
- *Why:* "khối lượng kiệt quệ" describes weeks of supply being absorbed. A
  four-day pause cannot dry up relative to its own four-day mean — the quantity P
  computes is close to 1 by construction on a short window regardless of what the
  stock is doing. Supply withdrawal after a thrust means *quiet relative to the
  thrust*. Same cut-off, better denominator; the cut-off is deliberately NOT
  loosened, so if flags still fail this it is a fact about flags.

### 4.3 `ma_hugging`

- **P:** MA10 and MA20 both below price and within 8.0% of it.
- **S:** MA10 and MA20 both below price (**trend intact, no upper bound**), and
  `(close − MA20) / ATR20 ≤ 5.0`.
- *Why:* a flag sits immediately after a pole, which is precisely when price is
  furthest from MA20. A fixed 8% bound asks a flag to look like a base whose
  averages have had weeks to catch up. The thing worth bounding is *extension*,
  which scales with the stock's own volatility — hence ATR units. 5.0 is a
  stated prior, not a fitted value, and it is not re-chosen after seeing results.

### 4.4 Arms

Primary comparison, pre-designated: **`PPP` (production, today's behaviour)**
versus **`SSS` (all three shape-specific)**. The six mixed arms are reported for
diagnosis — which clause moves the count — and are **not** eligible for adoption.
Adopting a mixed arm after seeing eight results is the multiplicity this design
exists to avoid. Eight arms are run; one is adoptable.

## 5. Train / test split by time — fixed now

- **TRAIN:** 2021-03-15 → 2024-06-30.
- **TEST:** 2024-07-01 → 2026-11-06 (held out).

TRAIN exists only to confirm the arms are mechanically distinguishable — that
`SSS` admits more flags than `PPP` at all. **No number is chosen on TRAIN**,
because there is nothing left to choose: §4 fixed every value. The split is here
so the outcome comparison is reported on data not used to notice anything.

If `SSS` admits no more flags than `PPP` on TRAIN, the study stops there and
reports that the re-specified measures do not change the verdict — a clean
negative, and the cheapest possible outcome.

## 6. Measures — identical to S-5a §4, for comparability

Entry at the **close of the episode date**. Not at the pivot: a breakout can lock
at trần with no fill.

- **PRIMARY — excess forward return.** `excess = episode_return(h) −
  mean(liquid_universe_return(h))` on the same date, `h ∈ {5, 10, 20}` bars.
- **SECONDARY — pivot clearance.** Does any **close** in the next 20 bars exceed
  the episode's pivot? On close, not high, for the trần reason above.

### 6.1 Benchmarks (C4 — mandatory)

1. **ARM-FLAT** — FLAT-shape episodes on the same dates. *This is the benchmark
   that decides the question:* flags are only worth admitting if they are not
   worse than the candidates the screen already produces.
2. **ARM-LIQ** — every symbol passing the liquidity floor on that date.
3. **ARM-RANDOM** — same-size random draw from ARM-LIQ, seeded `20261110`.

A result is reported for all arms or not at all.

## 7. Power floor — MIN_EPISODES = 20, and what a thin cell means here

`MIN_EPISODES = 20` on the TEST period, double S-5a's floor, because this study's
whole purpose is to decide whether to change production behaviour and §15.3 says
the population is small.

**A TEST cell below the floor means DO NOT ADOPT.** Not "adopt provisionally",
not "adopt and watch". This is the single most important clause in the document:
the most likely way #141 goes wrong is a handful of flag episodes with a
flattering mean, adopted because the alternative felt like inaction. If `SSS`
yields fewer than 20 TEST episodes, the finding is *"the flag population in this
universe is too small to calibrate on"* — which is itself an answer, and points
at universe depth (#142-blocked) rather than at thresholds.

No p-values: burst-correlated episodes make them wrong in the direction that
flatters the method. Report n, mean, median, IQR, and state the comparison is
directional.

## 8. Exclusions, fixed in advance

- An episode whose forward window runs past the last stored bar is **dropped**,
  not truncated.
- An episode whose forward window contains a price seam (`|overnight| > 15%`) is
  **dropped** — a share-count event is not a return.
- Nothing else. No symbol, date or outlier removed for being inconvenient.

## 9. THE DECISION RULE — pre-committed

`SSS` is adopted as the shape-specific setting for FLAG windows **only if ALL of
the following hold on the TEST period**:

1. `n ≥ 20` flag episodes (§7).
2. Pivot clearance for flag episodes **≥** ARM-FLAT's.
3. Mean excess 20-bar return for flag episodes **≥ 0**.
4. Mean excess 20-bar return for flag episodes **≥** ARM-RANDOM's.

Any single failure → **keep production thresholds unchanged**, record the flag
shape as contributing ~0 in this universe, and leave #141 closed-negative in the
register the way EM-4 through EM-7 are. A negative here costs nothing: the
detector stays, tested, behind a shape that admits almost nothing, exactly as
today.

Adoption, if it happens, is **flag-only** — `assess_base` takes the
shape-specific values when `window.shape == SHAPE_FLAG` and production values
otherwise. No flat verdict changes. The VT-2 byte-identical harness is re-run
restricted to FLAT episodes to prove it.

## 10. What would count as this study being run badly

Stated now so it cannot be renegotiated:

- Any threshold in §4 changed after a result is seen.
- A mixed arm adopted (§4.4).
- A TEST cell under the floor adopted anyway (§7).
- The TRAIN/TEST boundary moved.
- Flat-base thresholds or the flat-before-flag order touched (§1).

## 11. Output

`docs/backlog141_flag_calibration.md` — Part 2, written from the script's output
after it runs, numbers unedited, including the ones this document hopes not to
see. The script lands at
`services/decision-helper-service/tests/s2b_flag_calibration.py`.
