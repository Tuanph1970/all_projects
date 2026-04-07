# Conventional Trend Lines

## Description

The most widely used trend line method. An uptrend line connects the **extreme lows** (RLs) to define support; a downtrend line connects the **extreme highs** (RHs) to define resistance. Two anchor points is the minimum, with significance increasing proportionally to the number of touches.

Schwager is candid about the limitations: the process is "unavoidably subjective," lines frequently need redrawing (see [[10 - Trend Line Redrawing]]), and penetrations often produce [[11 - False Penetrations|false signals]]. Despite this, conventional lines remain useful as reference structures — especially for identifying failed signals in Ch.11.

## Simple Analogy

Imagine stretching a rubber band along the bottom of a bouncing ball's path. The band touches the lowest points of each bounce. As long as each bounce goes higher, the band angles upward — that's the uptrend support line. The moment the ball drops below the band, something has changed. But sometimes the ball just grazes through and bounces right back — that's a false penetration.

## Key Properties

| Property | Value |
|---|---|
| Anchor points | Extreme RLs (uptrend) or RHs (downtrend) |
| Minimum points | 2 (more = more significant) |
| Subjectivity | High — which lows/highs to connect? |
| Codeable? | Partially — via [[01 - Relative Highs and Relative Lows]] detection |
| Main weakness | Frequent redrawing, false penetrations |
| Main strength | Precise reference levels for stops and failed signals |

## Illustration

**Chart:** `assets/charts/trend_lines_comparison.png` (panel 1 of 6)

**Book references:** Figure 3.4 (Amoco uptrend), Figure 3.5 (IBM uptrend), Figure 3.6 (Motorola downtrend), Figure 3.7 (Xerox 7-year uptrend)

## Python Code

**File:** `assets/code/trend_lines.py` → function `conventional_trend_lines()`

```python
def conventional_trend_lines(df, n=10) -> list[TrendLine]:
    """Connect successive higher RLs (uptrend) or lower RHs (downtrend)."""
    data = detect_swing_points(df, n)
    lines = []
    # Uptrend: pairs of RLs where each successive RL is higher
    # Downtrend: pairs of RHs where each successive RH is lower
    ...
    return lines
```

## Connections

- **Depends on:** [[01 - Relative Highs and Relative Lows]], [[02 - Uptrend and Downtrend]]
- **Compare with:** [[04 - Internal Trend Lines]] (ignores extremes), [[05 - TD Lines (DeMark)]] (objective)
- **Used by:** [[06 - Trend Channels]], [[07 - Trend Line Rules]], [[10 - Trend Line Redrawing]], [[11 - False Penetrations]]
- **Resolves weakness:** Ch.11 Failed Signals (turns false breaks into signals)
- **Source:** Schwager pp.34-42

---
*Tags: #trend-line #subjective #schwager-ch3 #codeable*
