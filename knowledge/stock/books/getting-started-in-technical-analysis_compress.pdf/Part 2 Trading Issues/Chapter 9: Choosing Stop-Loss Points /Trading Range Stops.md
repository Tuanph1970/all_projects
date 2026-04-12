---
title: "Trading Range Stops"
chapter: 9
concept_number: 3
tags:
  - technical-analysis
  - stop-loss
  - trading-range
  - breakout
  - schwager
  - chapter-9
related:
  - "[[Stop-Loss Principle]]"
  - "[[Trend Line Stops]]"
  - "[[Flag and Pennant Stops]]"
  - "[[Confirmation Conditions]]"
  - "[[Money Stops]]"
  - "[[Failed Signals]]"
created: 2026-04-08
---

# Trading Range Stops

## Definition

After a breakout from a trading range, place the stop-loss **within the range itself**, using the range's internal structure as reference. Schwager defines three zones with distinct implications:

| Zone | Location | Schwager's verdict |
|------|----------|--------------------|
| Near boundary | Breakout side of range | **Do NOT stop here** — retracements this far are common |
| Midpoint to far boundary | Middle of range to opposite side | **Recommended** — valid breakouts shouldn't retreat this deep |
| Far boundary | Opposite side of range | **Absolute maximum** — reaching here totally transforms the picture |

The guiding principle: *"If the breakout is a valid signal, prices should not retreat too deeply into the range."*

## Key Quotes (Schwager)

> "The opposite side of a trading range can be used as a stop point. Frequently, the stop can be placed closer because if the breakout is a valid signal, prices should not retreat too deeply into the range."

> "The stop might be placed somewhere in the zone between the midpoint and the more distant boundary of the range."

> "The near end of the trading range would not be a meaningful stop point. In fact, retracements to this area are so common that many traders prefer to wait for such a reaction before initiating a position."

> "The protective sell stop should be placed no lower than the lower boundary of the trading range, since the realization of such a price would totally transform the chart picture."

## Analogy: Canary Deployment Rollback Thresholds

Like setting rollback thresholds in a canary deployment:

| Canary deploy | Trading range stop |
|---------------|-------------------|
| A few 4xx errors in first minute (normal) | Price retraces to near boundary (common) |
| Error rate climbs to 2-3% | Price retreats to midpoint — something wrong |
| Error rate hits 10%+ | Price reaches far boundary — catastrophic failure |
| Don't rollback for noise | Don't stop at the near boundary |
| Rollback at meaningful degradation | Stop at midpoint to far boundary |

You don't wait for total system failure to rollback, just as you don't wait for price to break the far boundary.

## When It Works Best

- After a **clear breakout** from a well-defined consolidation range
- When the range has been in place for **many bars** (more time in range = more significance)
- **Wider ranges** give more room for the stop — you can place it closer (in % terms) because the midpoint is further from the breakout
- Pairs well with [[Confirmation Conditions]] to filter false breakouts before entry

## When It Fails

- Very **narrow ranges** where the midpoint is barely below entry — risk may be too small to be meaningful, or too large relative to the narrow range width
- **Nested ranges** (range within a range) where it's unclear which boundaries to use
- When the breakout itself was on low volume or without conviction — consider [[Failed Signals]]

## Delayed Entry Strategy

Schwager notes an alternative: *"Many traders prefer to wait for such a reaction [to the near boundary] before initiating a position."* This is the delayed-entry approach — you wait for price to retrace into the range and then enter.

**Tradeoff:**
- Waiting: better entry price, stop is closer → better reward/risk
- Not waiting: you don't miss moves that never retrace

This is a matter of personal choice, not a rule.

## Backtest Results

500 simulated breakout scenarios (65% bullish, 12% range width):

| Zone | Risk/trade | Avg P&L | Worst | False stop rate | Never stopped |
|------|-----------|---------|-------|-----------------|---------------|
| Near boundary (0%) | 0.0% | +1.6% | -6.0% | **76.6%** | 12.8% |
| 25% into range | 2.8% | +2.5% | -8.8% | 56.5% | 25.0% |
| **Midpoint (50%)** | **5.7%** | **+3.3%** | **-12.5%** | **38.1%** | **39.6%** |
| 75% into range | 8.5% | +4.1% | -15.3% | 21.2% | 51.0% |
| Far boundary (100%) | 11.3% | +4.3% | -16.2% | 10.9% | 59.8% |

Key insight: moving from near boundary to midpoint cuts false stop rate in half (76.6% → 38.1%) while only increasing risk from 0% to 5.7%.

## Cross-References

- **[[Stop-Loss Principle]]** (Ch. 9, Concept 1) — Trading range stops implement Rule 2: liquidate where the technical picture changes
- **[[Trend Line Stops]]** (Ch. 9, Concept 2) — Higher sensitivity but more false signals; trading range stops are a lower-sensitivity, higher-specificity alternative
- **[[Flag and Pennant Stops]]** (Ch. 9, Concept 4) — Flags and pennants are small trading ranges within a trend; same zone logic applies
- **[[Confirmation Conditions]]** (Ch. 7) — Time delays and minimum penetration help validate the breakout before entry, affecting where the entry sits relative to the range
- **[[Money Stops]]** (Ch. 9, Concept 7) — Fallback when even the far boundary implies excessive dollar risk
- **[[Failed Signals]]** (Ch. 7) — A failed breakout from a trading range may signal a move in the opposite direction

## Python Implementation

See `trading_range_stops.py`:

- `TradingRange` — dataclass with `stop_at_zone()`, `classify_zone()`, midpoint/width properties
- `detect_trading_range()` — finds the most recent consolidation in a price series
- `evaluate_zone_performance()` — backtests all five zone levels across hundreds of scenarios

## Summary

Trading range stops sit at the **center of Schwager's sensitivity-specificity spectrum**. They're less sensitive than [[Trend Line Stops]] (more false signals get through) but far more specific (when they fire, the trade is more likely genuinely wrong). The midpoint is the practical sweet spot: it cuts the false stop rate roughly in half compared to the near boundary while keeping risk manageable. The far boundary is the absolute maximum — a backstop, not a target.
