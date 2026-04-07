# Moving Averages

## Description

A smoothing technique that creates a cleaned version of the price series. A simple moving average (SMA) is the average close of the past N days. Unlike trend lines that draw straight lines through anchor points, the MA creates a **curve** that traces the smoothed trajectory of price itself.

Schwager's key insight (p.48): "The basic definition of a rising moving average is equivalent to the simple condition that today's close is higher than the close N days ago." The entire smoothing apparatus reduces to a single comparison.

The fundamental trade-off: smoothing removes noise but introduces **lag**. "Turning points in moving averages will always lag the corresponding transitions in the price series" (p.49).

## Simple Analogy

A moving average is like a **7-day weather forecast average**. If you average the last 7 days of temperature, today's average won't spike just because one day was unusually hot — the spike gets diluted across the other 6 days. This smoothing makes the seasonal trend visible (warming or cooling), but the average always runs behind the actual temperature. You know summer has arrived only after several warm days have already passed.

Longer window (40-day MA) = more dilution = smoother curve = more lag. Like averaging a whole month vs a whole week.

## Key Properties

| Property | Value |
|---|---|
| Input | Closing prices (or OHLC average) |
| Parameter | N (number of days) |
| Output | Smoothed price curve |
| Objectivity | Fully objective — same N, same data = same MA |
| Lag | Inherent — turning points always trail the price |
| Best in | Trending markets (see [[09 - Moving Average Signals]]) |
| Worst in | Sideways markets — oscillates without direction |

## Formula

```
SMA(N) at bar t = (close[t] + close[t-1] + ... + close[t-N+1]) / N

Rising MA equivalence:
  MA[t] > MA[t-1]  ⟺  close[t] > close[t-N]
```

## Illustration

**Chart:** `assets/charts/trend_lines_comparison.png` (panel 5 of 6)

**Book references:** Figure 3.18 (Gillette — 40-day MA in trending market), Figure 3.19 (Cocoa — 40-day MA in sideways market)

## Python Code

**File:** `assets/code/trend_lines.py` → function `moving_average_trend()`

```python
def moving_average_trend(df, period=40, threshold=0.0) -> pd.DataFrame:
    """
    SMA with Schwager's direction-change signal logic.
    Buy: MA turns up by threshold from its low.
    Sell: MA turns down by threshold from its high.
    """
    close = df["close"].values
    ma = np.full(n, np.nan)
    for i in range(period - 1, n):
        ma[i] = np.mean(close[i - period + 1 : i + 1])
    ...
```

## Other MA Types (Appendix)

- **Linearly Weighted MA (LWMA):** Recent days weighted more heavily
- **Exponentially Weighted MA (EWMA):** Weights decay exponentially
- Schwager (Ch.14): "No strong empirical evidence that weighted MAs provide consistent improvement over simple MAs"
- **Crossover system** (Ch.14): Two MAs (fast + slow) — a "far more meaningful improvement"

## Connections

- **Used by:** [[09 - Moving Average Signals]], Ch.8 Midtrend Entry (reaction to MA), Ch.14 Trading Systems
- **Complementary to:** Ch.6 Oscillators (work where MAs fail — see [[12 - Trending vs Sideways Markets]])
- **Source:** Schwager pp.45-50

---
*Tags: #moving-average #objective #schwager-ch3 #codeable #parametric*
