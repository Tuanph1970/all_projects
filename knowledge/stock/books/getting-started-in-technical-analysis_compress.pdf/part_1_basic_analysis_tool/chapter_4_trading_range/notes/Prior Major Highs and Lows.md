# Prior Major Highs and Lows

**Source:** Schwager, *Getting Started in Technical Analysis*, Ch. 4, pp. 58–67
**Parent:** [[Chapter 4 - Trading Ranges and Support and Resistance]]

## Definition

A **prior major high** is a previous distinct peak in the price series — a price level the market reached, then turned away from. A **prior major low** is the analogous trough. These specific points act as future [[Support and Resistance]]:

- A prior major **high** stands as future **resistance** until it is decisively broken.
- A prior major **low** stands as future **support** until it is decisively broken.

A penetration of a prior major high (with confirmation, e.g., several closes above and/or a minimum percent move) can be read as a **buy signal**; a penetration of a prior major low can be read as a **sell signal**. After a sustained penetration, the role-reversal rule kicks in: the broken high becomes support, the broken low becomes resistance.

## Illustration

![[04_prior_highs_lows.png]]

*The earlier peak (red dot) becomes a ceiling; rallies later in the chart stall just below it. The earlier trough (green dot) becomes a floor; the later decline halts just above it. Single, well-defined extremes can produce remarkably clean S/R behavior.*

## Analogy

Imagine you're hiking and reach a particular ridge before turning back. Years later, you return to the same trail. That same ridge feels significant — not because the ridge is physically different, but because *you remember* hitting it before. Many other hikers feel the same way. The ridge becomes a natural reference point: people stop and rest there, take photos there, decide whether to push on or turn back there.

Markets behave the same way. Old peaks and troughs are remembered by traders who lived through them. Stops cluster there. Profit targets cluster there. Self-fulfilling memory turns yesterday's turning point into tomorrow's S/R.

## Numeric example

Stock GHI's history:

| Date     | Event                              | Price  |
|:---------|:-----------------------------------|-------:|
| Jan 2022 | Prior major high                   | 85.00  |
| Aug 2022 | Prior major low                    | 52.00  |
| Mar 2023 | Rally peaks at...                  | 84.20  |
| Sep 2023 | Decline bottoms at...              | 53.10  |
| Today    | Price                              | 78.00  |

Reading off this history:

- **84–85 is a resistance zone**. Two distinct rallies (Jan-22 and Mar-23) failed there.
- **52–53 is a support zone**. Two distinct declines (Aug-22 and Sep-23) held there.
- **Trading plan**: a confirmed close above 85.00 (e.g., 3 daily closes ≥ 85.85, a 1% buffer) opens up a long position with a stop just below 84. Alternatively, on the long side, prices approaching 84 should be expected to hesitate.

## Code

See [[code/support_resistance.py]] — the helpers `find_relative_extremes()` and `major_highs_lows()` find the candidates; `levels_at_now()` classifies each one as support or resistance from the perspective of a given day.

```python
from support_resistance import major_highs_lows

highs, lows = major_highs_lows(prices, n=10, top_k=3)
print("Top 3 prior peaks (days):", highs)
print("Top 3 prior troughs (days):", lows)
```

A relative high is defined as a bar that is the maximum within ±N bars; the most extreme of those become the "major" highs.

## Within-chapter relationships

- **vs. [[Trading Range]] boundaries** — range boundaries are *flat* S/R defined by repeated touches; prior major highs/lows are *single-event* S/R defined by isolated extremes. Both produce identical role-reversal behavior on penetration.
- **vs. [[Concentrations of Relative Highs and Lows]]** — this concept uses **single peaks/troughs**; the next concept generalizes to *clusters* of less extreme relative highs/lows. Clusters tend to be more reliable than single points but are harder to spot.
- **vs. [[Price Envelope Bands]]** — prior highs/lows are *static* (the level is fixed at the historical price); envelope bands are *dynamic* (they walk with a moving average). They serve different time horizons.

When does this work well?

- After a clean, sharp peak or trough that wasn't part of a noisy congestion area
- On longer timeframes (weekly, monthly) where major extremes are well-defined
- In markets followed by many participants — where the prior level is collectively remembered

When is it less reliable?

- When the prior extreme is "fuzzy" (not a single sharp point but a messy congestion)
- When too much time has passed and the prior level is no longer in market memory
- During regime changes (post-split, post-merger, dramatic fundamentals shift)

## Cross-chapter relationships

- [[Chapter 5 - Chart Patterns]] — double tops and triple tops are essentially "rallies that stall at a prior major high"; the pattern is the chart manifestation of this concept.
- [[Chapter 9 - Stop-Loss Points]] — placing a stop just beyond a prior major high or low is one of the canonical stop-placement methods.
- [[Chapter 10 - Setting Objectives]] — the next major high above a long position is a natural profit target.
- [[Chapter 11 - Most Important Rule]] — the *failure* of a breakout above a prior high (a [[Bull Trap]]) is one of the most powerful reversal signals in chart analysis.

## Tags

#technical-analysis #chapter-4 #support #resistance #peaks #troughs
