---
chapter: 3
concept: Uptrend Line
tags: [technical-analysis, trends, chapter-3]
source: "Schwager, Getting Started in Technical Analysis, Ch. 3, pp. 34, 39"
---

# Uptrend Line

## Definition

An **uptrend line** is a straight line drawn on a chart that connects a series of higher lows. It acts as a moving floor that rises diagonally with the trend. As long as price stays above the line, the uptrend is presumed intact; a close beneath the line is treated as a warning that the trend may be ending. A line with two anchor points is the minimum; the more lows it touches, the more significant the line becomes.

## Illustration

![[03_uptrend_line.png]]

The orange line is fitted through three successive higher lows (red dots). Notice how price repeatedly tests the line during pullbacks but generally respects it as support.

## Analogy

Picture a kite string angling up to the sky. The kite (price) bobs above the string, sometimes dipping toward it but tugged upward each time. The string itself doesn't pull the kite up — it just marks the angle of the climb. As long as the kite stays above the string, the wind is still lifting it. When the string finally goes slack — the kite has fallen through it — you know the lift is gone.

## Numeric Example

Two anchor lows: bar 12 at price 50.00, bar 38 at price 53.50.

- Slope = (53.50 − 50.00) / (38 − 12) = **0.1346 per bar**
- Line value at bar 70 = 50.00 + 0.1346 × (70 − 12) = **57.81**
- If close at bar 70 = 58.40 → above the line → uptrend intact
- If close at bar 70 = 56.90 → below the line → potential sell signal (Rule 2)

## Python Implementation

See [[02_trend_lines.py]]:

```python
from trend_lines import fit_uptrend_line, near_trend_line, trend_line_signal

line = fit_uptrend_line(closes, pivot_lows_idx=[12, 38])
print(f"Slope: {line.slope:.4f}, value at bar 70: {line.value_at(70):.2f}")

if near_trend_line(line, closes[70], 70, tolerance_pct=0.01):
    print("Buy zone (Rule 1)")

sig = trend_line_signal(line, closes, current_bar=70, confirm_closes=2)
if sig == "sell":
    print("Trend-line break (Rule 2)")
```

## Relationships

**Within Chapter 3:**
- A geometric encoding of the [[01_Uptrend]] pivot pattern — converts the discrete RH/RL sequence into a continuous boundary.
- Often paired with a parallel upper line to form a [[05_Trend_Channel]].
- Together with [[04_Downtrend_Line]] forms the symmetric "trend line" toolkit.
- Trading actions are governed by [[06_Trend_Line_Rules]].
- [[06_TD_Line]] is a *deterministic* recipe for which two lows to anchor.
- [[07_Internal_Trend_Line]] argues that *extreme* lows (the natural anchors of conventional lines) may not represent the dominant trend.
- [[08_Moving_Average]] is an alternative way to draw a trend boundary — curved instead of straight.

**Outside Chapter 3:**
- An uptrend line is itself a form of dynamic **support** (Ch. 4).
- Trend-line breaks are confirmation signals for many **chart patterns** (Ch. 5).
- The slope of the line informs **price-objective** projections (Ch. 10).
- A note from the chapter: trend lines work better in **hindsight** than in real time. Penetrations are common and often false; this links to the discussion of false signals in Ch. 11.

## When does this concept work well?

| Market type | Effectiveness |
|---|---|
| Sustained, steady uptrend | ✅ Line holds for long stretches |
| Steepening parabolic move | ⚠️ Line will need re-drawing repeatedly |
| Choppy market | ❌ Many false breaks; line redrawn every few bars |
| Hindsight chart review | ✅ Always looks great — beware of overconfidence |

## Source

Schwager, *Getting Started in Technical Analysis*, Ch. 3, pp. 34, 39. Note the chapter's caution: "trend lines often need to be redrawn as a bull or bear market is extended" — penetration is more often a redraw signal than a reversal signal.
