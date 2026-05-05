---
chapter: 3
concept: TD Line (DeMark)
tags: [technical-analysis, trends, chapter-3, demark]
source: "Schwager, Getting Started in Technical Analysis, Ch. 3, pp. 39, 41-42; citing Tom DeMark, The New Science of Technical Analysis (1994)"
---

# TD Line (DeMark)

## Definition

A **TD line** is an objective, rule-based trend line invented by Thomas DeMark. Where conventional trend-line drawing is subjective, the TD method specifies *exactly* two anchor points:

- **TD uptrend line:** connects the most recent relative low to the most recent earlier relative low that is *lower* than the most recent one.
- **TD downtrend line:** connects the most recent relative high to the most recent earlier relative high that is *higher* than the most recent one.

A relative low (with parameter N) is a bar whose low is lower than the lows of the N preceding and N succeeding bars. The choice of N controls the trade-off: larger N produces fewer but more significant lines that signal more slowly; smaller N produces more lines and faster signals. Because TD lines are anchored to the *most recent* qualifying pivots, they are continuously redefined and emphasize recent price action over historical price action.

## Illustration

![[07_td_line.png]]

Both red dots are N-bar relative lows (here N = 4). The earlier low is *lower* than the later one — this is what qualifies them to anchor a TD uptrend line. The orange line is the TD uptrend line itself.

## Analogy

Picture a Wi-Fi signal-strength meter on your phone. The meter's current "trend" is determined entirely by the two most recent stable readings — not by historical readings from last week. The instant a new stable reading appears, the meter recalculates the trend using just the latest two valid samples. TD lines work the same way: only the two most recent qualifying pivots define "the line." Yesterday's pivot that mattered yesterday is irrelevant the moment a new qualifying pivot appears.

## Numeric Example

A series of relative-low pivots (N = 4):

| Pivot index | Bar | Low price |
|---|----:|----------:|
| 1 | 12  | 48.00 |
| 2 | 28  | 50.50 |
| 3 | 47  | 49.20 |
| 4 | 65  | 51.80 |

Building the TD uptrend line at the most recent point (bar 65):
- Anchor B = pivot 4 at bar 65, price 51.80.
- Walk backward for the most recent earlier *lower* pivot: pivot 3 at bar 47 has 49.20 < 51.80. ✅
- Slope = (51.80 − 49.20) / (65 − 47) = **0.1444 per bar**
- Line value at bar 80 = 49.20 + 0.1444 × (80 − 47) = **53.97**

If a new low appears at bar 73 with value 50.10, the line is redrawn: anchor B becomes that new pivot, and the system again searches backward for the most recent lower pivot.

## Python Implementation

See [[03_td_lines.py]]:

```python
from td_lines import td_uptrend_line, relative_lows

# Find all N-bar relative lows
pivots = relative_lows(lows, n=4)
print(f"{len(pivots)} qualifying lows")

# Build the current TD uptrend line
line = td_uptrend_line(lows, n=4)
if line:
    print(f"Anchored at bars {line.a_index} ({line.a_price:.2f}) "
          f"and {line.b_index} ({line.b_price:.2f})")
    print(f"Line value at current bar: {line.value_at(current_bar):.2f}")

# Increase N for fewer, slower, more significant lines:
slow_line = td_uptrend_line(lows, n=8)
```

## Relationships

**Within Chapter 3:**
- A formalization of the [[03_Uptrend_Line]] / [[04_Downtrend_Line]] anchor-selection process.
- Eliminates the subjectivity that the standard trend lines are criticized for.
- Stands in contrast to [[07_Internal_Trend_Line]]: TD anchors on **extreme** pivots; internal lines deliberately *avoid* extreme pivots. Two opposite philosophies.
- N parameter parallels the lookback parameter in an [[08_Moving_Average]] — both control the smoothing/lag trade-off.

**Outside Chapter 3:**
- DeMark's broader work covers many objective indicators (TD Sequential, TD Combo) — TD lines are just one piece of his system.
- TD lines feed naturally into systematic / algorithmic trading because they are deterministic.
- The concept of a **continuously redefined trend line** anticipates modern adaptive indicators discussed in Ch. 14.
- Penetration of a TD line is treated similarly to penetration of a conventional trend line — confirmation rules from Ch. 11 still apply.

## When does this concept work well?

| Market type | Effectiveness |
|---|---|
| Algorithmic / systematic trading | ✅ Fully objective — no human judgment required |
| Cleanly trending market | ✅ Pivots are spaced and unambiguous |
| Very low-volatility / flat market | ❌ Pivots barely qualify; line is fragile and re-drawn constantly |
| Extreme spike followed by reversal | ⚠️ Latest pivot may be an unrepresentative outlier |

## Choosing N

| N value | Effect |
|--------:|--------|
| 2-3 | Many pivots, very reactive, many false signals |
| 4-5 | Balanced — good default for daily charts |
| 8-10 | Few but high-quality pivots, slower signals |

## Source

Schwager, *Getting Started in Technical Analysis*, Ch. 3, pp. 39, 41-42, citing Thomas DeMark, *The New Science of Technical Analysis* (John Wiley & Sons, 1994).
