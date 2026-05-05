---
chapter: 3
concept: Downtrend Line
tags: [technical-analysis, trends, chapter-3]
source: "Schwager, Getting Started in Technical Analysis, Ch. 3, pp. 34, 36"
---

# Downtrend Line

## Definition

A **downtrend line** is a straight line drawn on a chart that connects a series of lower highs. It acts as a moving ceiling that descends diagonally with the trend. As long as price stays below the line, the downtrend is presumed intact; a close above the line is treated as an early warning that the trend may be over.

## Illustration

![[04_downtrend_line.png]]

The orange line is fitted through three successive lower highs (green dots). Each rally fails just below the line, confirming overhead supply.

## Analogy

Imagine a heavy lid pressing down on a pot of boiling water. Steam (price) tries to rise, but every time it pushes up, it bumps the lid and slides back down — and the lid itself is being lowered slightly each time. As long as the lid stays in contact with the rising steam, the pressure stays contained. The day the steam finally lifts the lid off, you've got a real change.

## Numeric Example

Two anchor highs: bar 15 at price 75.00, bar 40 at price 71.00.

- Slope = (71.00 − 75.00) / (40 − 15) = **−0.16 per bar**
- Line value at bar 70 = 75.00 + (−0.16) × (70 − 15) = **66.20**
- If close at bar 70 = 65.80 → below the line → downtrend intact
- If close at bar 70 = 67.50 → above the line → potential buy signal

## Python Implementation

See [[02_trend_lines.py]]:

```python
from trend_lines import fit_downtrend_line, trend_line_signal

line = fit_downtrend_line(closes, pivot_highs_idx=[15, 40])
print(f"Slope: {line.slope:.4f}, value at bar 70: {line.value_at(70):.2f}")

sig = trend_line_signal(line, closes, current_bar=70, confirm_closes=2)
if sig == "buy":
    print("Downtrend-line break (Rule 2)")
```

## Relationships

**Within Chapter 3:**
- Geometric encoding of the [[02_Downtrend]] pattern.
- Mirror of [[03_Uptrend_Line]] — same math, opposite direction.
- Combined with a parallel lower line yields a downward [[05_Trend_Channel]].
- Anchor-point selection is formalized by [[06_TD_Line]].
- Re-drawn often: Schwager shows in figures 3.11–3.12 how the same downtrend line had to be redefined twice as the market continued to fall.

**Outside Chapter 3:**
- The downtrend line itself is dynamic **resistance** (Ch. 4).
- A confirmed break above the line is the entry signal for several **bottoming patterns** (Ch. 5).
- For a short trader, the trend-line break is also a stop trigger (Ch. 9).
- Downtrend-line slopes tend to be steeper than uptrend slopes — a behavioral artifact of fear unfolding faster than greed.

## When does this concept work well?

| Market type | Effectiveness |
|---|---|
| Sustained bear move | ✅ Line caps every rally cleanly |
| Sharp panic decline | ⚠️ Line may need to be re-drawn steeper |
| Bottoming/basing | ❌ Multiple false breakouts; line keeps getting redrawn |

## Source

Schwager, *Getting Started in Technical Analysis*, Ch. 3, pp. 34 and 36 (Figures 3.6, 3.11, 3.12).
