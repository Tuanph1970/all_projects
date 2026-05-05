# Trading Range

**Source:** Schwager, *Getting Started in Technical Analysis*, Ch. 4, pp. 51–54
**Parent:** [[Chapter 4 - Trading Ranges and Support and Resistance]]

## Definition

A **trading range** is a horizontal corridor on a price chart inside which prices oscillate for a sustained period (commonly at least a month or two on a daily chart, but ranges can stretch for years). The corridor has a roughly flat upper boundary (acting as a ceiling) and a roughly flat lower boundary (acting as a floor), and individual swings stay between the two without producing a sustained trend in either direction.

Two practical points worth internalizing:

- Markets statistically spend the **majority** of their time in trading ranges.
- Ranges are nonetheless **difficult to trade profitably**. The author's advice is that the best strategy for most technical traders in ranging markets is to *minimize their participation*.

## Illustration

![[01_trading_range.png]]

*Simulated 200-day price series oscillating between ~90 (support) and ~110 (resistance) — a classic trading range. The dashed lines mark the corridor boundaries.*

## Analogy

Imagine a tennis ball bouncing back and forth inside a long hallway. The ceiling and the floor of the hallway define the boundaries; the ball will sometimes drift higher or lower, sometimes hit the ceiling, sometimes hit the floor, but it never escapes the hallway — until something punches a hole through the wall and the ball can finally roll outside. While the ball is in the hallway, watching every little bounce in detail rarely tells you anything about which wall it will eventually break through.

## Numeric example

Consider stock XYZ over 6 months. Each week's high and low are recorded:

| Week | High | Low |
|------|------|-----|
| 1    | 109  | 95  |
| 2    | 108  | 92  |
| 3    | 110  | 94  |
| 4    | 107  | 91  |
| ...  | ...  | ... |
| 24   | 109  | 93  |

- Highest high over 24 weeks: **110**
- Lowest low over 24 weeks: **91**
- Mid-price: 100.5
- Width: 19 / 100.5 ≈ **18.9%**

If during all 24 weeks no close breaks above 110 or below 91, this qualifies as a 6-month trading range with **resistance ≈ 110** and **support ≈ 91**.

## Code

See [[code/trading_range.py]] — `detect_trading_ranges()` slides a window over a price array and flags windows whose (max−min)/mean is below a configurable threshold. Overlapping windows are merged into one range object.

```python
from trading_range import detect_trading_ranges
import numpy as np

prices = np.array([...])  # closing prices
for tr in detect_trading_ranges(prices, window=30, max_pct_spread=0.10):
    print(tr)
# TradingRange(days 0-79, 91.0-110.0, width=18.9%, duration=80)
```

## Within-chapter relationships

- **vs. [[Trading Range Breakout]]** — a range is a *state*; a breakout is the *event* that ends the state. You must identify the range first to even talk about a breakout from it.
- **vs. [[Support and Resistance]]** — the boundaries of a range are the cleanest, most "obvious" S/R levels in technical analysis. Every other S/R technique in this chapter is a generalization of "the floor and ceiling of a range".
- **vs. [[Price Envelope Bands]]** — both are containment patterns, but a range is *static* (fixed price boundaries) while an envelope band is *dynamic* (boundaries that walk with a moving average). Envelope bands work even when prices are slowly drifting; ranges only describe truly horizontal markets.

When does the trading-range concept work well?

- Long-duration markets (months or years) where no fundamental catalyst has emerged
- Sideways consolidation phases between major trends
- Markets dominated by short-term mean-reverting flow (e.g., low-vol periods)

When is it misleading?

- In strong trending markets — a "range" you draw will keep getting violated
- On too-short windows — you'll mistake a brief pause in a trend for a range

## Cross-chapter relationships

- [[Chapter 3 - Trends]] — a range is essentially "the absence of a trend". The two concepts are complementary opposites.
- [[Chapter 5 - Chart Patterns]] — most chart patterns (gaps, flags, etc.) lose their predictive value when they form *inside* a trading range, because the range itself dominates price behavior.
- [[Chapter 6 - Oscillators]] — oscillators (RSI, stochastics) are designed for ranging markets and tend to print clean overbought/oversold signals against range boundaries.
- [[Chapter 11 - Most Important Rule]] — failure of a "breakout" of a range (a [[Bull Trap]] or [[Bear Trap]]) is among the most powerful chart signals, and these only exist in the context of a prior range.
- [[Chapter 14 - Trend-Following Systems]] — trend-following systems systematically *lose money* during ranging markets; the diagnosis "we are in a range" implies switching off (or counter-balancing) the trend follower.

## Tags

#technical-analysis #chapter-4 #range #consolidation
