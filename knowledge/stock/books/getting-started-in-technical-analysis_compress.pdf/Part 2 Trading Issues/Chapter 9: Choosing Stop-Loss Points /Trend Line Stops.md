---
title: "Trend Line Stops"
chapter: 9
concept_number: 2
tags:
  - technical-analysis
  - stop-loss
  - trend-lines
  - schwager
  - chapter-9
related:
  - "[[Stop-Loss Principle]]"
  - "[[Trading Range Stops]]"
  - "[[Confirmation Conditions]]"
  - "[[Trailing Stops]]"
  - "[[CIC Anti-Pattern]]"
created: 2026-04-08
---

# Trend Line Stops

## Definition

Place a sell stop below an uptrend line (for longs) or a buy stop above a downtrend line (for shorts). The stop price moves with the trend line — it is dynamic, not static. This is the **highest-sensitivity stop type**: it fires earliest, limiting loss size, but it also produces the most false exits because trend lines are frequently redefined during a trend's evolution.

## Key Quotes (Schwager)

> "The penetration of a trend line will usually be one of the first technical signals in a trend reversal. Thus, this type of stop point will strongly limit the magnitude of the loss or surrendered open profits."

> "This attribute comes at a steep price: Trend line penetrations are prone to false signals. As discussed in Chapter 3, it is common for trend lines to be redefined in the course of a bull or bear market."

From Chapter 3:

> "Trend lines tend to be penetrated, sometimes repeatedly, during their evolution, which is equivalent to saying that trend lines are frequently redefined as they extend."

## Analogy: Aggressive Health Check Timeout

Like setting a **very short timeout** (50ms) on a microservice health check:

| Short timeout (trend line stop) | Long timeout (range/swing stops) |
|---|----|
| Catches failures fast | Catches only genuine outages |
| Fires on normal latency spikes | Misses early warning signs |
| Many unnecessary failovers | Fewer false alarms |
| Limits blast radius | More damage when it does fire |

The tradeoff is identical: **sensitivity vs. specificity**. Every stop type in this chapter sits somewhere on this spectrum.

## The Tradeoff

| Dimension | Trend line stop |
|-----------|----------------|
| Speed of exit | Fastest of all chart-based stops |
| Loss size when correct | Smallest |
| False signal rate | Highest |
| Requires redefinition? | Yes — trend lines get redrawn mid-trend |
| Dynamic or static? | Dynamic — stop moves with the line |

## When It Works Best

- **Strong, clean trends** with well-defined swing lows/highs
- When you want **maximum capital preservation** and accept more whipsaws
- Combined with [[Confirmation Conditions]] (buffer, time delay, minimum penetration) to filter false signals
- As a first filter that gets replaced by tighter stops ([[Trailing Stops]]) once the trade moves into profit

## When It Fails

- **Choppy or range-bound markets** where price oscillates around trend lines
- Steep trend lines — the steeper the line, the more easily price touches it on normal pullbacks
- Early in a trend when only two anchor points define the line (easily redefined by a third touch)

## Mitigation: Buffer Levels

Adding a percentage buffer below the trend line reduces false signals at the cost of larger losses when the stop is real:

| Buffer | Effect |
|--------|--------|
| 0% (exact line) | Most false signals, smallest losses |
| 0.5–1% | Filters noise, moderate improvement |
| 2%+ | Few false signals, but approaches [[Trading Range Stops]] territory |

## Cross-References

- **[[Stop-Loss Principle]]** (Ch. 9, Concept 1) — The three rules this stop type implements
- **[[Trading Range Stops]]** (Ch. 9, Concept 3) — Lower sensitivity, higher specificity alternative
- **[[Confirmation Conditions]]** (Ch. 7) — Time delay, minimum penetration, and thrust days can reduce false trend line signals
- **[[Trailing Stops]]** (Ch. 9, Concept 8) — Trend line stops naturally function as trailing stops since the line moves with time
- **[[CIC Anti-Pattern]]** (Ch. 9, Concept 9) — Canceling a trend line stop because price approaches it

## Python Implementation

See `trend_line_stops.py`:

- `TrendLine` — dataclass with `price_at()` projection and `is_penetrated()` check
- `compute_trend_line()` — fits a line through the most recent swing lows or highs
- `evaluate_trend_line_stop()` — tests a trend line stop on price data and flags false signals
- `compare_buffer_levels()` — shows the sensitivity/specificity tradeoff at different buffer percentages

**Demo result** (uptrend with reversal at bar 80):
- 0% buffer: stopped at bar 42, -5.2% — **false signal** (price recovered)
- 0.5% buffer: stopped at bar 83, +6.9% — survived the whipsaw

## Summary

Trend line stops are the **smoke detector** of stop-loss types: they go off at the first hint of trouble, which is great when the house is actually on fire but annoying when you're just cooking dinner. Schwager frames this explicitly as a tradeoff, not a flaw. The right question isn't "are trend line stops good?" but "is the false signal rate acceptable for this particular trade?" — and the answer depends on how clean the trend is, how steep the line is, and whether you're using confirmation filters.
