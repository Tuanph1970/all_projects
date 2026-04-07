# Internal Trend Lines

## Description

A trend line drawn to best approximate the **majority** of relative highs or relative lows, deliberately ignoring extreme points. Schwager (p.42): "Extreme highs and lows represent emotional excesses in the market, and as such may not represent the dominant trend."

Internal lines sit closer to where price *actually* holds during normal pullbacks, making them more useful for identifying support/resistance. However, they are "unavoidably arbitrary, perhaps even more so than [[03 - Conventional Trend Lines|conventional trend lines]]." Schwager admits his evidence is anecdotal and a scientific test would be "very difficult to construct."

## Simple Analogy

If conventional lines are like drawing a fence around the *outermost* fence posts (the extremes), internal lines are like drawing a path through the **center of the herd** — ignoring the few stragglers who wandered too far. The path represents where the majority of the herd is walking, which is more useful for predicting where they'll go next than the outlier positions.

In code terms: conventional = `max()`/`min()` anchors; internal = `median()` or `robust_fit()`.

## Key Properties

| Property | Value |
|---|---|
| Anchor points | Best-fit through majority of RLs or RHs |
| Extreme handling | Deliberately ignored |
| Subjectivity | Very high — no anchor rule at all |
| Codeable? | Yes — via RANSAC/iterative outlier removal or linear regression |
| Main weakness | Arbitrary, hard to test scientifically |
| Main strength | Better support/resistance prediction than conventional |

## Illustration

**Charts:**
- `assets/charts/trend_lines_comparison.png` (panel 2 of 6 — shows internal vs conventional faded overlay)
- `assets/charts/conventional_vs_internal.png` — Detailed 3-panel comparison: conventional alone, internal alone, both overlaid

**Book references:** Figures 3.15 (Cotton), 3.16 (Canadian Dollar), 3.17 (Japanese Yen) — each shows both conventional and internal lines on the same chart

## Python Code

**File:** `assets/code/trend_lines.py` → function `internal_trend_line()`

```python
def internal_trend_line(df, n=10, direction="up") -> Optional[TrendLine]:
    """
    RANSAC-like approach: fit through all swing points,
    iteratively remove worst outlier until 70% remain.
    This approximates what a human does when eyeballing
    a best-fit line ignoring spikes.
    """
    # 1. Detect all RLs (uptrend) or RHs (downtrend)
    # 2. Fit least-squares through all points
    # 3. Remove point with largest residual
    # 4. Repeat until target inlier fraction reached
    ...
```

## Connections

- **Depends on:** [[01 - Relative Highs and Relative Lows]]
- **Compare with:** [[03 - Conventional Trend Lines]] (anchored to extremes), Linear Regression (algorithmic equivalent)
- **Relationship:** Internal lines are the *conceptual bridge* between subjective conventional lines and objective regression lines
- **Source:** Schwager pp.42-45

---
*Tags: #trend-line #subjective #schwager-ch3 #codeable*
