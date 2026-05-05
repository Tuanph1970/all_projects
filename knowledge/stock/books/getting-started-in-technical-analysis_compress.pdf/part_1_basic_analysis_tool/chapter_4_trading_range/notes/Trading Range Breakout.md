# Trading Range Breakout

**Source:** Schwager, *Getting Started in Technical Analysis*, Ch. 4, pp. 54–58
**Parent:** [[Chapter 4 - Trading Ranges and Support and Resistance]]

## Definition

A **trading range breakout** is a price move that pushes through and stays beyond either the upper or lower boundary of an established [[Trading Range]]. A breakout is interpreted as a forecast that prices will continue to travel in the direction of the breakout — i.e., a new trend may be starting.

Three factors increase the reliability of a breakout signal:

1. **Duration of the prior range** — the longer the range, the more meaningful the eventual breakout
2. **Narrowness of the prior range** — narrow ranges produce especially clean signals because the implied stop loss (back into the range) is small
3. **Confirmation** — raw penetrations are unreliable; require a minimum number of closes beyond the boundary, a minimum percent penetration, or both

A penetration that fails (prices fall back into the range) is not just noise — it is itself a powerful signal in the opposite direction (covered in [[Chapter 11 - Most Important Rule]]).

## Illustration

![[02_breakout.png]]

*The price corridor (gray shaded region) holds for ~140 days. Around day 145 prices poke above the upper boundary but quickly return — a **false breakout**. Around day 165 prices break above and stay above for many sessions — a **confirmed breakout**, leading to an established uptrend.*

## Analogy

Think of a balloon being inflated inside a cardboard box. The box's walls hold the balloon for a while. Eventually pressure builds and the balloon punches through one wall.

But there's a catch: maybe the balloon just dented a wall, and once the dent springs back, the balloon is still inside the box. You only know it really got out when you see it sitting outside the box for a few minutes — *that's the confirmation rule*. Acting the moment you see the dent will burn you over and over.

## Numeric example

Stock ABC trades for 4 months in a range with **resistance = 50.00** and **support = 45.00**.

A trader uses two confirmation rules:
- **Rule A**: at least 3 consecutive daily closes above 50.00
- **Rule B**: penetration of at least 1% (i.e., a close above 50.50)

| Day | Close | Above 50? | Above 50.50 (1%)? | Action |
|----:|------:|:---:|:---:|:---|
| 87  | 50.20 | ✓ | ✗ | wait — only marginal |
| 88  | 49.80 | ✗ | ✗ | reset counter |
| 89  | 50.30 | ✓ | ✗ | wait |
| 90  | 49.50 | ✗ | ✗ | reset (false breakout!) |
| 91  | 50.60 | ✓ | ✓ | day 1 of 3 |
| 92  | 51.10 | ✓ | ✓ | day 2 of 3 |
| 93  | 51.40 | ✓ | ✓ | **day 3 — buy signal** |

The trader buys at the close of day 93 (~51.40). The implied stop is at 49.50 (just back inside the range). Risk per share = $1.90.

## Code

See [[code/breakout.py]] — `detect_breakouts()` accepts a price series, range upper/lower boundaries, a number of confirmation days, and a minimum percentage penetration. It returns confirmed breakout signals.

```python
from breakout import detect_breakouts

signals = detect_breakouts(
    prices,
    range_upper=50.0,
    range_lower=45.0,
    confirm_days=3,
    min_pct_penetration=0.01,   # 1%
)
for s in signals:
    print(s)   # day, direction, breakout_price, ...
```

## Within-chapter relationships

- **vs. [[Trading Range]]** — a breakout is the resolution event; without a prior range identification, "breakout" is meaningless.
- **vs. [[Support and Resistance]]** — once a breakout is confirmed, the *broken boundary* immediately becomes S/R in the opposite role: a former ceiling becomes a floor, a former floor becomes a ceiling. This is the role-reversal rule that connects the two concepts.
- **vs. [[Price Envelope Bands]]** — both involve "prices leaving a corridor", but envelope bands are dynamic; touching a band is normally an *overbought/oversold* signal, not a "trend starting" signal as with a range breakout.

When does breakout-trading work well?

- Markets coming off long, narrow consolidations
- Markets with a fundamental story building (the chart catches up to the story)
- High-volatility regimes where moves are sustained once initiated

When does it work poorly?

- Choppy, low-volatility ranges where every "breakout" is a head-fake
- During major news days, where the spike that triggers the signal is also where mean-reversion kicks in
- When too many traders are watching the same level (stops cluster just outside the range, get triggered, and fade)

## Cross-chapter relationships

- [[Chapter 11 - Most Important Rule]] — when a breakout *fails* (price returns into the range), it becomes a [[Bull Trap]] or [[Bear Trap]] — a particularly powerful counter-signal. This is a recurring theme in the book.
- [[Chapter 14 - Trend-Following Systems]] — the breakout system (buy on N-day high, sell on N-day low) is the canonical implementation of this concept as an automated rule.
- [[Chapter 9 - Stop-Loss Points]] — the "back into the range" point is one of the cleanest natural stop locations.
- [[Chapter 5 - Chart Patterns]] — many specific patterns (e.g. ascending triangles, rectangles) are essentially special-shaped trading ranges, and "breakout from the pattern" is the same idea applied at a smaller scale.

## Tags

#technical-analysis #chapter-4 #breakout #signal #confirmation
