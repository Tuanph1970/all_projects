---
title: "Reversal of Minor Reaction"
aliases:
  - minor reaction reversal
  - reaction-resumption entry
  - N-day X-day entry
chapter: 8
concept: 3
tags:
  - technical-analysis
  - schwager
  - entry-strategy
  - midtrend
  - two-phase-signal
related:
  - "[[The Midtrend Entry Problem]]"
  - "[[Percent Retracement Entry]]"
  - "[[Continuation Pattern Breakouts]]"
  - "[[Reaction to Long-Term Moving Average]]"
  - "[[Pyramiding Rules]]"
  - "[[Confirmation Conditions]]"
created: 2026-04-07
---

# Reversal of Minor Reaction

## Core idea

A **two-phase** midtrend entry strategy:
1. **Detect a counter-trend reaction** (price exceeds an N-day extreme against the trend)
2. **Confirm trend resumption** (price closes beyond an X-day extreme in the trend direction)

The stop is placed at the **reaction extreme** — the highest point of a rally in a downtrend, or the lowest point of a dip in an uptrend.

## Mechanism (downtrend example)

### Phase 1 — Detect the reaction
- A **minor reaction** in a downtrend = price makes a new **N-day high**
- This means price has risen above the highest high of the previous N days
- The reaction is now "active" — we track the highest point reached

### Phase 2 — Confirm the resumption
- While the reaction is active, watch for trend resumption
- Resumption = price **closes below the X-day low** (lowest low of previous X days)
- When this triggers: **SELL signal**, stop placed at the reaction high

### Uptrend (reversed)
- Reaction = new N-day low (price dips below lowest low of N prior days)
- Resumption = close above X-day high
- **BUY signal**, stop at the reaction low

## Two independent parameters

This is what distinguishes this strategy from [[Percent Retracement Entry]] (which has one parameter):

| Parameter | Controls | Larger value = | Smaller value = |
|---|---|---|---|
| **N** (reaction window) | How big the counter-move must be to count as a "reaction" | Requires bigger counter-move; fewer false reactions | Triggers on small wiggles; more noise |
| **X** (resumption window) | How strong the trend resumption must be to trigger entry | Requires stronger resumption; fewer false entries, delayed reentry | Jumps in fast; more whipsaws |

> Schwager: "Larger or smaller values of N and X would change the sensitivity of the approach. For example, changing the trend resumption requirement to a close below the seven-day low would probably remove some false signals at a cost of delaying trend reentry."

## Schwager's specific example: Motorola (downtrend)

- **N = 10**: reaction defined as a new 10-day relative high
- **X = 3**: trend resumption defined as a close below the 3-day low
- Stop placed at the reaction high

He shows multiple sell signals generated in a sustained Motorola downtrend, each catching a re-entry after a counter-trend bounce.

## Critical distinction: sensitivity vs. trend-following

Schwager explicitly connects this method to the **breakout system in Chapter 17**, but notes a key difference:

> "The number of days (three) used in the example to define a trend resumption is much smaller, and thus more sensitive, than would typically be used in a trend-following system."

| Context | Typical X value | Purpose |
|---|---|---|
| **Midtrend re-entry** (this strategy) | 3–5 days | Re-enter a trend you already believe exists |
| **Trend identification** (Ch. 17) | 20–40 days | Identify a *new* trend from scratch |

You can afford higher sensitivity because you have a **prior belief** that the trend is intact — you're not discovering it, you're rejoining it.

## Software analogy

Think of a **circuit breaker pattern** in microservices:

| Circuit breaker | Minor reaction strategy |
|---|---|
| Error rate spikes above threshold | Price exceeds N-day counter-trend extreme |
| Circuit trips → stop sending traffic | Reaction detected → stop looking for entries |
| Wait for health checks to pass | Wait for X-day trend resumption confirmation |
| Resume traffic | Enter the trade |
| N = error threshold sensitivity | N = reaction detection sensitivity |
| X = health check count required | X = resumption confirmation sensitivity |

Too sensitive on both = constant flapping / whipsaw trades. Too conservative = slow recovery / missed re-entries. The art is tuning N and X independently.

## When this works best

- **Sustained trends with regular counter-trend bounces** — the strategy catches each re-entry after a bounce fades
- When you want a **fully mechanical, parameterized** approach (no chart pattern subjectivity)
- When you need **independent control** over reaction detection and resumption confirmation
- For [[Pyramiding Rules|pyramiding]] — adding to winners after each pullback

## When it does NOT work

- **Choppy, range-bound markets** — constant false reactions and false resumptions
- **V-shaped reversals** — the reaction and resumption happen too fast for the N/X windows to catch
- When the "reaction" turns out to be a genuine trend reversal, not a minor counter-move

## Sensitivity comparison (from Python demo)

| N | X | Total sensitivity | Signals | Avg risk |
|---|---|---|---|---|
| 5 | 3 | 8 (high) | 9 | 3.85 |
| 8 | 5 | 13 (medium) | 5 | 4.46 |
| 12 | 7 | 19 (low) | 4 | 5.00 |

The pattern is clear: higher sensitivity → more signals but smaller avg risk per trade. Lower sensitivity → fewer, more selective signals but larger stops (because the reaction has more room to run before resumption triggers).

## Cross-references

### Within Chapter 8
- [[The Midtrend Entry Problem]] — The framework this strategy solves
- [[Percent Retracement Entry]] — Alternative with one parameter (% level), no resumption confirmation
- [[Continuation Pattern Breakouts]] — Alternative using chart patterns, more subjective
- [[Reaction to Long-Term Moving Average]] — Alternative using MA as pullback reference
- [[Pyramiding Rules]] — This strategy works well for pyramid timing

### Other chapters
- [[Confirmation Conditions]] (Ch. 7) — The X parameter is itself a confirmation condition on the resumption
- [[Failed Signals]] (Ch. 7) — If the "resumption" immediately fails, that's a potential failed signal / trend reversal
- [[Multi-Timeframe Analysis]] (Ch. 7) — Use a higher timeframe to confirm the trend is still intact before applying this strategy
- Breakout Systems (Ch. 17) — Same concept, less sensitive parameters, for trend identification rather than re-entry

## Python implementation

See `reversal_minor_reaction.py`:
- `reversal_of_minor_reaction()` — generates BUY/SELL signals with configurable N and X
- `sensitivity_comparison()` — compares signal count and risk across N/X combinations
- Tracks reaction extremes for stop placement
- Works for both long (uptrend) and short (downtrend) directions

## Key takeaway

> The reversal of minor reaction gives you **two independent knobs** (N and X) to tune the tradeoff between signal frequency and quality. Unlike percent retracement, it waits for the counter-move to **actually reverse** before entering — you don't buy blind at a price level, you buy on evidence that the trend is resuming. The cost: slightly worse entry price than the retracement low.
