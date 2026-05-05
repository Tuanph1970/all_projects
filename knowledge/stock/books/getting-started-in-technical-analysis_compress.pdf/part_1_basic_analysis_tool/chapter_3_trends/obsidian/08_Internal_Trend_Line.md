---
chapter: 3
concept: Internal Trend Line
tags: [technical-analysis, trends, chapter-3]
source: "Schwager, Getting Started in Technical Analysis, Ch. 3, pp. 42-44"
---

# Internal Trend Line

## Definition

An **internal trend line** is a trend line drawn to best approximate the *majority* of relative highs or relative lows, ignoring extreme price excursions. The reasoning, advanced in the chapter: extreme highs and lows often represent emotional excesses (panic, euphoria) and may not faithfully represent the dominant trend. By fitting through the bulk of the pivots — and tolerating some that slightly penetrate the line — the analyst captures the "core" trajectory rather than its tantrums.

The trade-off vs. conventional trend lines: an internal trend line is more subjective (no extreme pivot anchors it), but in the author's experience it often does a better job of marking the levels where the market actually holds during declines and stalls during advances.

## Illustration

![[08_internal_trend_line.png]]

The dashed purple line is the **conventional** trend line, anchored at the extreme low spike (the highlighted dot). The solid orange line is the **internal** trend line, fitted through the majority of pivots while ignoring that one extreme excursion. Notice how the internal line tracks the visible "spine" of the price action much more naturally.

## Analogy

Imagine measuring the height of an ocean tide using a ruler stuck in the sand. If you read the ruler at the moment a freak wave hits, you'll get a wildly high number that doesn't reflect the actual tide. The smarter approach is to watch many waves over an hour and average them — ignoring the one freak wave. The "official" tide line is at the average, not at the freak. Internal trend lines do the same thing for price: they average through the noise of emotional spikes rather than letting one outlier set the slope.

## Numeric Example

Six pivot lows have been identified:

| Bar | Low price |
|----:|----------:|
| 10  | 48.10     |
| 20  | 43.60 ← extreme spike (panic) |
| 30  | 51.20     |
| 45  | 53.80     |
| 60  | 57.40     |
| 72  | 59.90     |

**Conventional uptrend line** anchored on the extreme low: passes through bar 20 at 43.60 and bar 72 at 59.90 → slope = (59.90 − 43.60) / (72 − 20) = **0.3135**, intercept ≈ 37.33.

**Internal trend line** (OLS regression, with z-score outlier trim):
- Initial fit through all 6 pivots: slope ≈ 0.260, intercept ≈ 44.7.
- Bar 20 has a residual of about −5.5 (way below the line) → trimmed.
- Refit through {10, 30, 45, 60, 72}: slope ≈ **0.232**, intercept ≈ **47.0**.

At bar 80 the two lines say very different things:
- Conventional: 37.33 + 0.3135 × 80 = **62.41**
- Internal: 47.0 + 0.232 × 80 = **65.56**

The internal line sits higher (a tighter, more current support); the conventional line sits low because it was dragged down by a single panic spike from months ago.

## Python Implementation

See [[04_internal_trend_line.py]]:

```python
from internal_trend_line import fit_internal_line

pivots = [10, 20, 30, 45, 60, 72]
line = fit_internal_line(closes, pivots, trim_outliers_z=1.0)

print(f"Slope: {line.slope:.4f}")
print(f"Used pivots: {line.used_indices}")
print(f"Rejected: {line.rejected_indices}")
print(f"Line value at bar 80: {line.value_at(80):.2f}")
```

The implementation does a two-pass fit:
1. OLS regression through all pivot points.
2. Trim points whose residual exceeds `trim_outliers_z` standard deviations.
3. Refit through the survivors.

## Relationships

**Within Chapter 3:**
- A philosophical opposite of [[06_TD_Line]]: TD lines anchor *exactly* on the most recent extreme pivots; internal lines deliberately *exclude* extremes.
- A refinement of [[03_Uptrend_Line]] / [[04_Downtrend_Line]] for noisy markets.
- More closely resembles the smoothing behavior of an [[08_Moving_Average]] than a conventional trend line — both are "best-fit" lines through the data rather than tangent lines to the extremes.
- Like all trend lines, defines a boundary between the trend regime and a possible reversal — same trading rules from [[06_Trend_Line_Rules]] apply, with one exception: the slight pivot penetrations are *expected*, not signals.

**Outside Chapter 3:**
- Internal lines often do a better job marking dynamic **support and resistance** than conventional lines (Ch. 4) — Schwager argues this is one of their main practical virtues.
- Connects to broader regression-based approaches in modern quantitative analysis: **linear regression channels**, **Bollinger-style envelopes** built around a regression line.
- Useful when designing **midtrend entry** strategies (Ch. 8) — the internal line is more reliable as a "buy zone."

## When does this concept work well?

| Market type | Effectiveness |
|---|---|
| Volatile market with occasional spikes | ✅ Internal line ignores the spikes correctly |
| Smooth, low-volatility trend | ⚠️ Same as conventional line — no advantage |
| Markets with persistent emotional extremes (commodities, crypto) | ✅ Particularly valuable here |
| Backtesting / systematic trading | ❌ Subjectivity is a problem unless trimming rule is fully specified |

## Comparison: TD Line vs. Internal Trend Line

| Aspect | TD Line | Internal Line |
|---|---|---|
| Anchor philosophy | Extreme recent pivots | Majority of pivots, excluding extremes |
| Number of anchor points | Exactly 2 | Many (best-fit) |
| Subjectivity | Low (rule-based) | Higher (depends on trim rule) |
| Reactivity | High — re-drawn at every new pivot | Lower — moves only as the pivot population shifts |
| Best for | Algorithmic trading, fast signals | Spotting durable support/resistance |

## Source

Schwager, *Getting Started in Technical Analysis*, Ch. 3, pp. 42-44 (Figures 3.15-3.17). The chapter notes that scientific testing of internal trend lines is difficult because of their subjectivity, but argues they merit inclusion in any chartist's toolkit.
