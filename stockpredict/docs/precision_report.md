# Single-Scale Precision Report (Task A6)

**Date:** 2026-06-11  
**Requirement:** L3 (false positives are the core problem)  
**Decision gate:** Do NOT proceed to Part B until single-scale FPR is under control.

---

## 1. Methodology

A null-FPR sweep (`null_detection_distribution`, n_null=500, seed=0) was run on
Gaussian random-walk surrogates (length=300, vol=0.01 per step). The 95th-percentile
null score (pct95) serves as the significance threshold: a real detection is
"noteworthy" only if its quality score strictly exceeds pct95.

Additionally, the full pipeline was run on 20 independent random-walk series of the
same length/vol to measure the noteworthy FPR (fraction of random-walk detections
that incorrectly survive the gate).

Measurements were taken **before and after** tolerance tuning. All planted-pattern
tests in `tests/test_patterns_planted.py` were verified to pass after each change.

---

## 2. Baseline Results (before tuning)

| Pattern | Null FPR (firings/surr) | pct95 | Gate status |
|---|---|---|---|
| Symmetric Triangle | 1.678 | 1.000 | **DEAD** — no real detection can pass |
| Ascending Triangle | 1.104 | 1.000 | **DEAD** |
| Descending Triangle | 1.132 | 1.000 | **DEAD** |
| Double Top | 0.182 | 0.999 | **DEAD** |
| Double Bottom | 0.066 | 0.998 | **DEAD** |
| Head & Shoulders | 0.238 | 0.921 | OK |
| Inverse H&S | 0.248 | 0.891 | OK |
| Bull Flag | 0.266 | 0.844 | OK |
| Bear Flag | 0.258 | 0.865 | OK |
| Bull Pennant | 0.086 | 0.878 | OK |
| Bear Pennant | 0.074 | 0.898 | OK |

**"DEAD" gate** means pct95 ≈ 1.0: since quality scores are clamped to [0, 1] and
the gate requires `score > pct95`, no real detection of that pattern can ever be
flagged as noteworthy. The detectors were firing too frequently on noise, with scores
reaching the maximum.

Precision on 20 random-walk series (baseline): 114 total detections, 2 noteworthy
(1.8% precision — nominally acceptable for random walks, but triangles/doubles
never flagged even on real series).

---

## 3. Root-Cause Analysis

### Triangles (Symmetric / Ascending / Descending)

With `min_pivots=4`, any 4-consecutive-swing window (2H + 2L) can satisfy the
slope classification. On a random walk with the default `order=10` swing extractor,
a 300-bar series yields ~12–18 swing pivots, producing many overlapping 4-pivot
windows. The shape-score components (`_sym_shape`, `_asc_shape`, `_desc_shape`)
saturate quickly — e.g. any moderately converging window gets `_sym_shape ≈ 1.0`.

**Fix:** Increase `min_pivots` from 4 to 6 (require 3H + 3L minimum pivot structure),
and tighten `flat_slope_eps` from 0.05 to 0.04 (stricter flat/rising/falling
classification). A 6-pivot window is still easily satisfied by genuine triangle
patterns (all planted-pattern tests use 3H + 3L).

### Double Top / Double Bottom (formula redesign — completed)

The original score formula `0.5 × similarity + 0.5 × depth_score` (with
`_DEPTH_REF = 0.1` relative to the local peak) saturated at pct95 ≈ 0.999 because:

1. **Depth saturation**: the swing extractor enforces a minimum swing height of 8%
   of the series range, which means null troughs have `depth_rng ≈ 0.25` (median)
   and `depth_rng ≈ 0.65` (p95). With `_DEPTH_REF = 0.1` relative to the local peak,
   86% of null cases had `depth_score = 1.0` (saturated).

2. **Two-leg linear R² was ineffective**: swing legs are monotone by construction
   (the swing extractor selects extrema), so two-leg R² was always high (p95 ≈ 0.91).

**Fix applied:** Formula redesigned with two changes:
- **`_DEPTH_REF_RANGE = 0.80`** (range-relative, calibrated so null p50 ≈ 0.31,
  null p95 ≈ 0.81 depth_score — no saturation)
- **Quadratic V-shape R²** replaces two-leg linear R²: fits a symmetric `a·t² + b`
  to the full inter-peak window. Genuine U/∩ shapes score R² ≈ 0.90–0.99; random-
  walk windows with extra wiggles score R² ≈ 0.10–0.55.  Null p95 ≈ 0.79.

New score: `0.4 × similarity + 0.3 × depth_score + 0.3 × traj_score` (weights sum 1.0)

---

## 4. Applied Changes

### Triangle tolerance (`chart_decomp/domain/value_objects.py` — `TriangleParams`)

| Parameter | Before | After | Rationale |
|---|---|---|---|
| `min_pivots` | 4 | **6** | Requires 3H+3L structure; reduces random-walk firing rate |
| `flat_slope_eps` | 0.05 | **0.04** | Tighter flat/rising/falling classification |

### Double Top/Bottom formula (`chart_decomp/infrastructure/patterns/double.py`)

| Change | Before | After |
|---|---|---|
| Depth denominator | local peak price | full series range |
| `_DEPTH_REF` constant | `0.1` (local-peak fraction) | `_DEPTH_REF_RANGE = 0.80` (range fraction) |
| Trajectory term | two-leg linear R² | quadratic V-shape R² (`a·t² + b` fit over full window) |
| Score weights | `0.5·sim + 0.5·depth` | `0.4·sim + 0.3·depth + 0.3·traj` |

No changes to `DoubleParams`, `HSParams`, or `FlagParams` filter parameters.

---

## 5. Post-Tuning Results

| Pattern | Null FPR | pct95 | Gate status |
|---|---|---|---|
| Symmetric Triangle | 0.954 | 0.942 | **OK** — genuine detections can pass |
| Ascending Triangle | 0.514 | 0.698 | **OK** |
| Descending Triangle | 0.558 | 0.700 | **OK** |
| Double Top | 0.182 | 0.999 | **DEAD** — formula redesign pending |
| Double Bottom | 0.066 | 0.998 | **DEAD** — formula redesign pending |
| Head & Shoulders | 0.238 | 0.921 | OK (unchanged) |
| Inverse H&S | 0.248 | 0.891 | OK (unchanged) |
| Bull Flag | 0.266 | 0.844 | OK (unchanged) |
| Bear Flag | 0.258 | 0.865 | OK (unchanged) |
| Bull Pennant | 0.086 | 0.878 | OK (unchanged) |
| Bear Pennant | 0.074 | 0.898 | OK (unchanged) |

Precision on 20 random-walk series (post-tuning): **79 total, 5 noteworthy (6.3%
FPR)**, close to the nominal 5% null rate. Triangle detection count on random walks
dropped from 74 to 43 (41% reduction), and all three triangle patterns now have a
meaningful significance threshold below 1.0.

---

## 6. Post-Formula-Redesign Results (Double Top / Bottom — completed in same session)

After the formula redesign (`_DEPTH_REF_RANGE = 0.80`, quadratic V-shape R²):

| Pattern | Null FPR | pct95 (before) | pct95 (after) | Gate |
|---|---|---|---|---|
| Double Top | 0.166 | 0.999 | **0.805** | **OK** |
| Double Bottom | 0.089 | 0.998 | **0.841** | **OK** |

(n=1000 surrogates, length=300, vol=0.01 per step)

All 11 pattern types now have pct95 < 0.95. Planted double top (score ≈ 0.92–0.99)
and planted double bottom clear the null gate in the mandatory gate tests
(`TestDoubleTopScoreRedesign::test_planted_clean_double_top_clears_null_gate` and
`TestDoubleBottomScoreRedesign::test_planted_clean_double_bottom_clears_null_gate`).

**Root cause of the initial 0.85 mis-prediction:** The original estimate assumed
random-walk troughs would be shallow and legs noisy. In reality, the swing extractor
(threshold=0.08) enforces minimum swing depths ≥ 8% of range, so random-walk troughs
have `depth_rng ≈ 0.25` (median) — deep enough to saturate the old `_DEPTH_REF = 0.10`.
Two-leg linear R² was similarly ineffective because swing legs are monotone by
construction. The quadratic V-shape fit (over the full inter-peak window) correctly
captures the extra noise in random-walk windows that lies *within* each leg.

---

## 7. Decision: Proceed to Part B

Single-scale false positives are now under control for all pattern types:

- All 11 of 11 patterns have pct95 < 0.95 — genuine detections can be distinguished
  from null firings
- The noteworthy FPR on random-walk data is ~6%, consistent with the 5% null target
- All 308+ library tests pass after all changes

**✓ Approved to proceed to Part B (multi-scale nesting).**

---

## 8. Production Baseline (A6.6) — n_null=1000, seed=0, length=300, vol=0.01

Applied in A6.6: service schema n_null default raised 100→500; `min_inter_pivot=15`
added to `SymmetricTriangleDetector` only (class-level default; Ascending/Descending
unchanged since their pct95 ≤ 0.70).

| Pattern | n_scores | FPR/surr | pct95 | Gate |
|---|---|---|---|---|
| Ascending Triangle | 522 | 0.522 | 0.698 | OK |
| Descending Triangle | 545 | 0.545 | 0.700 | OK |
| **Symmetric Triangle** | 94 | 0.094 | **0.914** | OK (was 0.932–0.942) |
| Double Top | 166 | 0.166 | 0.805 | OK |
| Double Bottom | 89 | 0.089 | 0.841 | OK |
| Head & Shoulders | 258 | 0.258 | 0.916 | OK |
| Inverse H&S | 256 | 0.256 | 0.917 | OK |
| Bull Flag | 265 | 0.265 | 0.841 | OK |
| Bear Flag | 287 | 0.287 | 0.857 | OK |
| Bull Pennant | 96 | 0.096 | 0.903 | OK |
| Bear Pennant | 73 | 0.073 | 0.898 | OK |

Stability verified (A6.6): seed=0 vs seed=1 at n_null=1000.  All Δpct95 ≤ 0.02
for high-FPR patterns (≥400 null scores: the three triangles); ≤ 0.05 for
low-FPR patterns (<400 scores).  See `tests/test_null_pct95_stability.py`.

318 library tests pass, 14 skipped (optional dependencies).

---

## 9. Known Limitations

1. **Symmetric Triangle pct95 = 0.914 is still above 0.90:** Genuine symmetric
   triangles scoring 0.70–0.91 remain below the gate.  Further reduction would
   require additional formula changes (apex proximity, convergence-ratio term).

2. **Rare-firing patterns have looser pct95 stability:** Pennants (FPR≈0.08),
   doubles (FPR≈0.09–0.17), and H&S (FPR≈0.26) accumulate only 70–260 null scores
   at n_null=1000.  Their pct95 SE ≈ 0.02–0.03; estimates are stable within ±0.05
   but not the strict ±0.02.  Users needing tighter estimates: set `n_null=2000`.

3. **n_null=500 (service default) is a speed/quality tradeoff:** Adequate for
   production (no dead gates, ±0.05 stability), but the test harness verifies at
   n_null=1000 for stricter confidence.
