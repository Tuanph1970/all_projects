---
title: Support and Resistance as Objectives
chapter: 10
concept_number: 3
tags:
  - exit-strategy
  - price-objectives
  - support-resistance
  - position-management
  - temporary-objective
related:
  - "[[Chart-Based Objectives]]"
  - "[[Measured Move]]"
  - "[[Trailing Stops]]"
  - "[[Trading Ranges]]"
  - "[[Overbought Oversold Indicators as Exit Signals]]"
schwager_quote: "Support and resistance levels usually represent only temporary rather than major objectives."
---

# Support and Resistance as Objectives

## Definition

Using **prior support and resistance levels as profit-taking zones** rather than (only) as entry signals. Prior highs define support zones for downside objectives on short positions; prior significant highs define resistance zones for upside objectives on long positions.

> "Generally speaking, support and resistance levels usually represent only temporary rather than major objectives. Consequently, in using this approach, it is advisable to seek to reenter the position at a better price if a reaction does develop."
> — Schwager, Chapter 10

## Core Principle

Price has **memory**. Levels where price previously reversed (prior highs, prior lows, range boundaries) tend to act as barriers again. When your profitable position is approaching one of these historical barriers, it's a natural place to take some profits — because price is likely to at least pause there.

But Schwager is clear: these are **rest stops, not final destinations**.

## Simple Analogy

**A hiking trail with rest stops.** When walking downhill, you know there are flat spots (prior high ground) where the trail levels off. Those are natural places to pause and catch your breath. But they're not the bottom of the mountain — they're temporary plateaus. A smart hiker pauses, reassesses, and decides whether to keep going.

## Three Scenarios

### 1. Short position → downside support objective
Prior relative highs below the current price form a support zone. When price falls to this zone, expect a temporary bounce. Take partial profits here.

**Schwager's example**: Figure 10.4 (December 1994 wheat) — objective zone based on support at two prior relative highs.

### 2. Long position → upside resistance objective
A prior significant high above the current price forms resistance. When price rises to this level, expect selling pressure. Take partial profits here.

**Schwager's example**: Figure 10.5 (GTE Corp) — objective based on resistance from a prior significant high.

### 3. Role reversal re-entry (Chapter 4 principle)
Once a resistance level is broken to the upside, it becomes support — and vice versa. The broken level serves as a **re-entry zone** after taking profits at the initial objective.

This connects directly to [[Trading Ranges]] Chapter 4: "Once a trading range is established, the upper and lower boundaries tend to define support and resistance areas."

## When It Works Best

- **Markets with clear prior highs and lows** — the more touches a level has, the stronger the objective
- **As a first/partial exit** — take some off at S/R, trail the rest with [[Trailing Stops]]
- **When S/R aligns with other objectives** — S/R target near a [[Measured Move]] target = confluence zone with much higher reliability
- **In moderately trending markets** — where price respects levels rather than blasting through them
- **For re-entry planning** — the temporary nature means you should plan the re-entry simultaneously with the exit

## When It Fails

- In **strongly trending markets** where momentum carries price straight through S/R levels
- When using S/R as the **sole exit criterion** — Schwager explicitly says these are temporary objectives
- If the S/R level is **old and untested** — levels lose relevance over time
- When there are no clear prior highs/lows nearby (choppy, trendless price action)

## Key Tradeoffs

| Decision | Tradeoff |
|---|---|
| Exit fully at S/R | Risk of missing trend continuation |
| Exit partially at S/R | Reduced position but still exposed to continuation |
| Wait for S/R to break | Gives back the profit from S/R reaction |
| Plan re-entry after exit | More complexity, but captures both the reaction and the continuation |

## Role Reversal (Chapter 4 Cross-Reference)

The S/R role reversal principle is one of the most reliable in technical analysis:
- **Broken resistance → new support**: When price breaks above a resistance level, that level becomes support on pullbacks
- **Broken support → new resistance**: When price breaks below support, that level becomes resistance on bounces

For objectives, this means: after your long position hits resistance and you take profits, if price breaks through that resistance, the old resistance level becomes your **re-entry zone** (new support).

## Cross-References

### Within Chapter 10
- [[Chart-Based Objectives]] — S/R levels often coincide with pattern-based targets for confluence
- [[Measured Move]] — MM target landing near S/R = doubly reliable zone
- [[Trailing Stops]] — Complementary: partial exit at S/R, trail the remainder
- [[Overbought Oversold Indicators as Exit Signals]] — Can confirm S/R reaction with oscillator readings

### Within the Book
- [[Trading Ranges]] (Chapter 4) — The foundational chapter for S/R concepts; range boundaries define S/R
- [[Trends]] (Chapter 3) — Trendline S/R provides dynamic (sloped) objective levels
- [[Stop-Loss Points]] (Chapter 9) — S/R objectives combined with stops for R:R calculation
- [[Confirmation Conditions]] (Chapter 7) — Penetration rules help determine if S/R is truly broken or just tested
- [[Failed Signals]] (Chapter 11) — If price fails to reach S/R and reverses, may signal a failed pattern

## Python Implementation

See `sr_as_objectives.py` for:
- `find_sr_levels()` — Automated S/R detection from OHLC data (clusters local highs/lows)
- `find_objectives()` — Finds nearest S/R levels as profit targets for long/short positions
- `detect_role_reversals()` — Identifies broken levels with reversed roles (re-entry zones)
- `SRObjective.risk_reward()` — R:R calculation using S/R target and stop price

### Example: Partial Exit Strategy
```python
levels = find_sr_levels(highs, lows, closes)
objectives = find_objectives(entry_price, 'long', levels)

# First objective (nearest resistance) → take 50% off
# Second objective (next resistance) → take 25% off
# Remainder → trail with trailing stop
```

## Key Takeaway

S/R levels are **the most intuitive but least ambitious** objective method. Schwager positions them as temporary rest stops — natural places to take partial profits and plan re-entries. Their real value multiplies when they coincide with [[Measured Move]] targets or [[Chart-Based Objectives]], creating confluence zones. Never use S/R as your only exit — always pair with a trailing mechanism for the portion you keep.
