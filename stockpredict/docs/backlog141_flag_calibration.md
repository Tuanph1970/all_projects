# Backlog #141 — Shape-specific squeeze and MA thresholds for FLAG bases: RESULTS (Part 2)

**Date:** 2026-11-10
**Pre-registration:** `docs/backlog141_flag_calibration_preregistration.md` (Part 1),
committed as `f3cecc5f` **before** `tests/s2b_flag_calibration.py` existed. No
constant was changed after seeing any of what follows; the one deviation that did
occur is reported in §6 rather than quietly corrected.
**Reproduce:**
`PYTHONPATH=.:../../stock-common python3 tests/s2b_flag_calibration.py <bars.tsv>`
(~8 minutes, read-only.)

---

## 1. What was run

1,186 scan dates, 2021-03-15 → 2026-11-09, 93 symbols from `stock_prices`,
production `ScanConfig()` with `max_candidates=0` (the funnel, not the top-20
cut — S-5a's convention). The stored range now reaches 2026-11-09 rather than
Part 1's 2026-11-06; the three extra bars can only ever be dropped for want of a
forward window, so the difference is immaterial and is recorded rather than
smoothed over.

**481 flag windows** — symbol-days reaching the base stage with no flat base.
This cross-checks SRS §15.3, which found 87 over 242 sampled dates: 87 × (1186/242)
≈ 426, against 481 measured on the full calendar. The populations agree.

## 2. Arm counts

| arm | flag symbol-days admitted | episodes | TRAIN | TEST |
|---|---|---|---|---|
| **PPP** (production, today) | 20 | 19 | 6 | **13** |
| PPS | 68 | 52 | 13 | 39 |
| PSP | 26 | 23 | 7 | 16 |
| PSS | 74 | 57 | 18 | 39 |
| SPP | 18 | 16 | 6 | 10 |
| SPS | 48 | 41 | 16 | 25 |
| SSP | 28 | 23 | 8 | 15 |
| **SSS** (the only adoptable arm) | 71 | 59 | 24 | **35** |

Production admits **20 of 481** flag windows — 4%, matching §15.3's "two of 87"
at scale. The clause doing most of the rejecting is `ma_hugging`: every arm with
`S` in the third position (PPS, PSS, SPS, SSS) jumps to 48–74 admissions, and
every arm with `P` there stays at 18–28. **The fixed 8% MA bound was the binding
constraint, not the squeeze ratios.** That is the diagnostic the mixed arms exist
for, and it is consistent with the mechanical argument in Part 1 §4.3: a flag
sits immediately after a pole, which is exactly when price is furthest from MA20.

## 3. §5 TRAIN gate

`SSS` admits 24 TRAIN episodes against `PPP`'s 6. The arms are mechanically
distinguishable, so the study proceeded to the held-out comparison. No number was
chosen on TRAIN — Part 1 §4 had fixed them all.

## 4. TEST period (2024-07-01 → 2026-11-09)

Excess forward return against the same-date liquid-universe mean:

| horizon | SSS flags (n=35) | ARM-FLAT (n=154) | ARM-RANDOM (n=35) |
|---|---|---|---|
| +5 bars | −0.24% (median −0.61%) | −0.46% (median −1.31%) | +0.42% (median +0.37%) |
| +10 bars | **+1.42%** (median +0.31%) | −0.68% (median −1.47%) | +0.94% (median −0.06%) |
| +20 bars | **+0.46%** (median **−2.37%**) | −0.59% (median −2.30%) | +0.29% (median −0.02%) |

Breakout within 20 bars, measured on close:

| arm | rate |
|---|---|
| **SSS flags (own pivot)** | **57.1%** |
| ARM-FLAT (own pivot) | 40.9% |
| ARM-RANDOM (prior high) | 45.7% |

## 5. §9's pre-committed decision rule

| condition | result | verdict |
|---|---|---|
| n ≥ 20 flag episodes on TEST | n = 35 | **PASS** |
| pivot clearance ≥ ARM-FLAT | 57.1% vs 40.9% | **PASS** |
| mean excess 20-bar return ≥ 0 | +0.46% | **PASS** |
| mean excess 20-bar ≥ ARM-RANDOM | +0.46% vs +0.29% | **PASS** |

**VERDICT: ADOPT `SSS` for FLAG windows.** All four conditions pass, so the rule
fixed in advance says adopt, and it is being honoured as written.

### 5.1 Which of those four is actually carrying the result

Stated plainly, because the table above is more flattering than the evidence:

- **Condition 2 is the real finding, and it is the strongest kind available
  here.** 57.1% against ARM-FLAT's 40.9% is the mechanism test — a flag admitted
  by `SSS` clears its own pivot *more often than the flat bases the screen
  already produces*, on held-out data. That is the question "is this a setup or
  not" answered directly, and it is the one measure S-5a also found had content.
- **Condition 4 passes by 0.17 percentage points at n = 35 against n = 35.** That
  is noise, not a margin. It would be dishonest to present it as evidence of
  anything; it is a hurdle cleared, nothing more.
- **Condition 3 passes on a mean of +0.46% whose median is −2.37%.** The mean is
  carried by a tail: most `SSS` flag episodes lost to the market at 20 bars and a
  few won large. For a breakout method that asymmetry is the expected shape
  rather than a defect, but *the central episode was a loser* and that belongs in
  the record next to the mean. The rule pre-registered the mean, so the mean
  decides; had it pre-registered the median, this study would have said KEEP.
  Both numbers are printed so no later reader has to take the favourable one on
  trust.

So: adopt, on the strength of pivot clearance, with return evidence that is thin
and tail-driven. **This is not an edge claim.** S-5a's limits apply unchanged —
burst-correlated episodes, 5.5 years, one bear market — and 35 episodes is a
small sample that happens to sit above a floor chosen in advance.

## 6. One deviation, declared

The first run drew ARM-RANDOM at **10× size** for a tighter benchmark, where
§6.1 pre-registered a **same-size** draw. That was corrected to the registered
size before anything was recorded, and the correction *narrowed* the result
rather than helping it:

- 10× draw (not registered): ARM-RANDOM 20-bar excess **−0.50%**, so condition 4
  would have passed by 0.96pp.
- Same-size draw (registered, and what decides): **+0.29%**, condition 4 passes
  by 0.17pp.

The registered version is the one in §5. The 10× figure is a precision note and
decides nothing — recorded only so the direction of the fix is visible.

## 7. What was adopted, and what was not touched

Flag-only, per §9: `assess_base` takes the shape-specific values when
`window.shape == SHAPE_FLAG` and production values otherwise.

- `range_contraction`: last-third TR / **mean pole TR** ≤ 0.75
- `volume_dryup`: last-third volume / **mean pole volume** ≤ 0.80
- `ma_hugging`: MA10 and MA20 below price, and (close − MA20) / ATR20 ≤ 5.0

No flat threshold changed, and the flat-before-flag search order is untouched.
Verified empirically rather than asserted: the FLAT-only candidate set over all
1,186 scan dates is **861 rows, sha256 `c580bca5…`** before and after the change.

## 8. What this does NOT resolve

- **The flag shape is still a small contributor.** 71 symbol-days out of 481 flag
  windows and 123,007 bars. It adds names; it does not change the screen's
  character.
- **#135 still stands.** A funnel that returns nothing on today's market is still
  returning the correct answer. Admitting more flags does not change that, and
  this study is not licence to revisit the liquidity or advance floors.
- **S-5a's primary finding is unchanged.** Buying the base still does not pay.
  This study moved one shape's admission rule; it did not find an edge, and the
  breakout trigger plus the exits remain where any edge would have to come from.
- **The successor is VT-5**, on accumulating live runs — not another sweep of
  this same 5.5 years.
