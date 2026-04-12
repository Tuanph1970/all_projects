---
title: "Wide-Ranging Day Stops"
chapter: 9
concept_number: 5
tags:
  - technical-analysis
  - stop-loss
  - wide-ranging-day
  - volatility
  - true-range
  - schwager
  - chapter-9
related:
  - "[[Stop-Loss Principle]]"
  - "[[Flag and Pennant Stops]]"
  - "[[Trading Range Stops]]"
  - "[[Relative High Low Stops]]"
  - "[[Confirmation Conditions]]"
created: 2026-04-08
---

# Wide-Ranging Day Stops

## Definition

A wide-ranging day (WRD) is a single price bar whose **true range significantly exceeds** the average true range of recent bars (typically 2x or more). After a WRD establishes a directional move, the return to the **opposite end** (the true low for a bullish WRD, the true high for a bearish WRD) signals that the entire conviction behind that move has been unwound — and serves as the stop placement point.

Schwager explicitly parallels this with flag/pennant stops: same invalidation logic, but compressed into a single bar.

### True Range (Welles Wilder)

The stop uses **true low/true high**, not just bar low/high, to account for gaps:

- **True high** = max(high, previous close)
- **True low** = min(low, previous close)
- **True range** = true high − true low

### Mathematical Definition

> "A wide-ranging day might be defined as a day whose range is more than two times the average range of the preceding N bars."

## Key Quotes (Schwager)

> "Similar to flags and pennants, after a breakout in one direction, the return to the opposite end can be used as a signal of a price reversal, and hence a point for placing stops."

> "Note how the return of prices back to below the true low of the wide-ranging up day... led to a major price collapse."

From Chapter 5 (definition):

> "A wide-ranging day is exactly what it sounds like: a daily price bar that is significantly bigger than the days preceding it. This is another way of describing a day whose volatility significantly exceeds the average volatility of recent trading days."

## Analogy: Load Test Baseline Regression

Like a **load test result** that dramatically exceeded the previous baseline:

| Load test | WRD stop |
|-----------|----------|
| System handles 3,000 RPS after optimization (vs 1,000 baseline) | True range is 2-3x the average range |
| Deploy based on the exceptional result | Enter trade based on the WRD's conviction |
| Throughput drops below pre-optimization baseline | Price returns to the WRD's opposite end |
| Rollback — the optimization didn't work in production | Stop triggered — the move has been invalidated |

## The "One-Bar Flag" Concept

A WRD stop follows identical logic to a [[Flag and Pennant Stops|flag/pennant stop]], just compressed in time:

| Dimension | Flag/pennant | Wide-ranging day |
|-----------|-------------|------------------|
| Duration | 1-3 weeks (multiple bars) | Single bar |
| Information content | High (multiple price interactions) | Lower (one bar's noise) |
| Stop reference | Opposite boundary | True low/high (opposite end) |
| False signal rate | Low (~10% at 4% width) | High (~84% at 2x multiplier) |
| Risk per trade | Narrow (3-8%) | Variable (depends on bar size) |

Key insight: **WRD stops have much higher false signal rates** than multi-bar patterns because a single bar carries more noise. This is the fundamental limitation.

## When It Works Best

- After **extreme WRDs** (3x+ ATR) where the bar clearly represents a regime change, not just noise
- When the WRD **closes near its extreme** (strong close for up WRD, weak close for down WRD) — this indicates directional conviction
- Combined with other technical context: WRD occurs at a key support/resistance level, or after breaking out of a pattern
- In trending markets where WRDs punctuate established moves

## When It Fails

- **Marginal WRDs** (1.5-2x ATR) — too close to normal volatility; high false signal rate
- In **choppy/volatile markets** where large ranges are common — the WRD loses its exceptional quality
- When the WRD is **news-driven** and the news effect dissipates — the return to the opposite end is mechanical, not meaningful
- **Earnings releases and other scheduled events** produce WRDs by definition, but the stop logic may not apply

## Backtest Results

500 simulated scenarios per multiplier (bullish WRD injected at bar 40):

| Multiplier | Detected | Avg risk | Avg P&L | Worst | False stop rate |
|-----------|----------|----------|---------|-------|-----------------|
| 1.5x | 100% | 2.9% | +2.5% | -5.0% | **86.0%** |
| 2.0x | 100% | 3.9% | +2.7% | -13.8% | **83.6%** |
| 2.5x | 98.6% | 6.2% | +0.5% | -16.8% | 56.1% |
| 3.0x | 91.4% | 7.9% | -1.0% | -16.8% | 36.2% |

Key insights:
- False stop rates are **much higher** than multi-bar patterns (flags: 10%, ranges: 38%)
- Even at 3.0x multiplier, false stops are 36% — single bars carry more noise than patterns
- The risk-vs-false-signal tradeoff is steep: higher multipliers mean fewer false signals but larger risk per trade

## Cross-References

- **[[Stop-Loss Principle]]** (Ch. 9, Concept 1) — WRD stops implement Rule 2: exit where the technical picture changes
- **[[Flag and Pennant Stops]]** (Ch. 9, Concept 4) — Schwager explicitly parallels these; WRDs are "one-bar flags" with the same opposite-end logic
- **[[Trading Range Stops]]** (Ch. 9, Concept 3) — WRDs have wider risk and more noise than range-based stops
- **[[Relative High Low Stops]]** (Ch. 9, Concept 6) — WRD extremes often coincide with relative highs/lows
- **[[Confirmation Conditions]]** (Ch. 7) — Adding minimum penetration or time delay filters can reduce the high false signal rate

## Python Implementation

See `wide_ranging_day_stops.py`:

- `OHLC` — bar dataclass with range, body ratio, direction
- `true_high()`, `true_low()`, `true_range()` — Welles Wilder's formulas
- `detect_wide_ranging_days()` — finds bars exceeding k × ATR
- `evaluate_wrd_stop()` — backtests WRD stops at different multipliers

## Summary

Wide-ranging day stops are the **most noise-prone** of Schwager's chart-based stops. The logic is sound — return to the opposite end invalidates the move — but a single bar carries far less information than a multi-bar pattern. The false stop rate (~84% at 2x ATR) is roughly double that of trading range stops and eight times that of flag stops. Use WRD stops when the bar is truly exceptional (3x+ ATR) and confirmed by other technical context, not as a standalone signal.
