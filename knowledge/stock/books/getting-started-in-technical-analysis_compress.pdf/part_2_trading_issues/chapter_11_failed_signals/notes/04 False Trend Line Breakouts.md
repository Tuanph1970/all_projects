# 04 False Trend Line Breakouts

**Parent:** [[00 Chapter 11 Index]] · **Master:** [[01 Failed Signals]]
**Tags:** #chapter11 #failed-signal #trendline

## Definition

A **false trend line breakout** is when price pierces a recognised trend line, *fails* to follow through, and then recloses on the original side of the line. Schwager argues that because trend lines are particularly prone to noisy breakouts, their *failures* are often **more reliable** than their successes — i.e., a false trend-line break is a higher-quality signal than a textbook trend-line break.

**Confirmation rule (typical):** for an uptrend line, two or more closes back **above** the line after a downside penetration confirm the false break. The trend line itself is then often redrawn through the new relative low, and the cycle can repeat (Schwager shows charts with three successive false-breakout signals on a single down-trend line).

## Illustration

![[04_false_trend_line_breakout.png]]

Compare with **Figure 11.6** (Allstate, false break of an uptrend line) and **Figure 11.7** (FCOJ, multiple false breaks of redrawn downtrend lines) in the book.

## Common-life analogy

A toddler peeks her head outside her bedroom door at 9 pm to see if the coast is clear for one more cookie. If she pulls her head back in within a few seconds — and stays in for the rest of the night — that's a false breakout: she briefly violated the rule but the original "in bed" trend remains intact. The two-close requirement is your way of waiting long enough to be sure she really stayed in bed before declaring the cookie raid abandoned.

## Numeric example

Uptrend line through three relative lows projects today at **$72.40**. Sequence of closes:

| Day | Close | Below line? | Above line? |
|----|-------|----|----|
| 1 | 72.10 | yes (–$0.30) | — |
| 2 | 71.80 | yes | — |
| 3 | 73.00 | — | yes |
| 4 | 73.40 | — | **yes (2nd close above)** ← false-break confirmed |
| 5 | 73.90 | — | — |

Long entry on Day 4 close at $73.40, stop just below Day 1's intraday low (say $71.40). Risk = $2.00; the prior trend implies plenty of room above for reward.

## Python sketch

```python
def false_trendline_break(closes, slope, intercept, x0, direction="up", k=2):
    """direction='up' for an uptrend line; we test failures of DOWNSIDE breaks.
       Yield indices where we get `k` consecutive closes back on the trend side."""
    on_wrong = 0          # consecutive closes on the broken side
    on_right = 0          # consecutive closes back on the trend side
    for t in range(x0, len(closes)):
        line = slope * (t - x0) + intercept
        wrong = closes[t] < line if direction == "up" else closes[t] > line
        if wrong:
            on_wrong += 1
            on_right = 0
        elif on_wrong > 0:
            on_right += 1
            if on_right >= k:
                yield t
                on_wrong = 0
                on_right = 0
```

## Relationships within the chapter

- A false trend-line breakout is the **trend-line analogue** of [[02 Bull and Bear Traps]] — same idea, sloped line instead of horizontal one.
- Uses [[03 Confirmation Conditions]] (specifically the "N closes back across the line" form of price confirmation).
- Sits alongside [[10 Penetration of Top and Bottom Formations]] and [[11 Breaking of Curvature]] as ways a structural reference (line, neckline, parabola) gets violated.

## When the concept works best

- **Long-standing trend lines** with three or more confirming touches before the break.
- **Steep markets** where small wiggles around a fast trend line are common — the false break is your edge over traders who are tricked by every nick.
- **Right after redrawing** an internal trend line (per Schwager, multiple false breaks often repeat on each redraw).

## Relationships outside the chapter

- Trend-line construction rules: [[Chapter 3 - Trends]] (especially "internal trend lines").
- Schwager classifies trend-line breaks as **low reliability** in their own right (they whipsaw a lot), which is exactly what makes their failures valuable — discussed in [[Chapter 7 - Is Chart Analysis Still Valid]].
- This pattern is referenced in **Rule #57** ("the false breakout of a trend line is often a meaningful signal") in [[Chapter 17 - Eighty-Two Trading Rules]].
