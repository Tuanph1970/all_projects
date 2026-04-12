---
title: "Continuation Pattern Breakouts"
aliases:
  - continuation pattern entry
  - flag breakout
  - trading range breakout midtrend
  - consolidation breakout
chapter: 8
concept: 4
tags:
  - technical-analysis
  - schwager
  - entry-strategy
  - midtrend
  - chart-patterns
  - subjectivity
related:
  - "[[The Midtrend Entry Problem]]"
  - "[[Percent Retracement Entry]]"
  - "[[Reversal of Minor Reaction]]"
  - "[[Reaction to Long-Term Moving Average]]"
  - "[[Pyramiding Rules]]"
  - "[[Continuation Patterns]]"
  - "[[Trading Ranges and Breakouts]]"
  - "[[Confirmation Conditions]]"
created: 2026-04-07
---

# Continuation Pattern Breakouts

## Core idea

Use **consolidation pauses within a trend** — flags, pennants, triangles, and narrow trading ranges — as midtrend entry points. These patterns are expected to resolve in the direction of the prior trend, creating natural entry opportunities with defined stop levels.

Schwager requires a **minimum of 5 trading days** for a consolidation to qualify as a continuation pattern.

## Two entry approaches

### 1. Wait for breakout (conservative)

Enter when price **closes above the pattern high** (uptrend) or **below the pattern low** (downtrend). You have confirmation that the pattern resolved in the expected direction.

- **Advantage**: Confirmation — you know the pattern worked
- **Disadvantage**: Worse entry price; the move has already started
- Stop: pattern low (uptrend) or pattern high (downtrend)

### 2. Enter within pattern (aggressive)

Enter **inside the consolidation** near its favorable extreme — near the low in an uptrend, near the high in a downtrend. You're anticipating the breakout before it happens.

- **Advantage**: Better price, tighter stop, smaller risk
- **Disadvantage**: No confirmation — the pattern might break the wrong way
- Stop: just beyond the pattern extreme

> Schwager: "Once a trend is considered established, it is not absolutely necessary to wait for penetrations of continuation patterns as confirmation of trade entry signals. By definition, these patterns are expected to be resolved by price swings in the same direction as the price moves that preceded their formation."

This is a remarkably aggressive statement — he's saying that if you trust the trend, you can front-run the breakout because the outcome is structurally expected.

## The subjectivity problem

This strategy is fundamentally different from [[Percent Retracement Entry]] and [[Reversal of Minor Reaction]] in one critical way: **it is subjective**.

> Schwager: "Since to some extent chart patterns are in the eye of the beholder, this approach will reflect a degree of subjectivity."

Two traders may disagree on:
- Whether a congestion phase is a continuation pattern or a distribution/accumulation zone
- Where to draw the boundaries of the pattern
- Whether 5 days of sideways action is "consolidation" or just noise
- Whether a triangle is symmetrical, ascending, or descending

The algorithmic implementation (in the Python code) uses a mechanical proxy — price range staying within X% for Y days — but this is an *approximation* of what a chart reader does visually.

## Types of continuation patterns (from Chapter 5)

| Pattern | Shape | Typical duration | Resolution |
|---|---|---|---|
| **Flag** | Narrow band, slight counter-trend slope | 1–3 weeks | Trend direction |
| **Pennant** | Converging lines, triangular | 1–3 weeks | Trend direction |
| **Symmetrical triangle** | Converging lines, symmetric | 2–8 weeks | Usually trend direction |
| **Ascending triangle** | Flat top, rising bottom | 2–8 weeks | Upward (hypotenuse slope) |
| **Descending triangle** | Flat bottom, falling top | 2–8 weeks | Downward (hypotenuse slope) |

Note: Schwager warns in Chapter 5 that the **direction of the actual breakout** is more important than the pattern type. A descending triangle can break upward.

## Schwager's example: March 1995 cotton

He shows multiple continuation patterns forming during a cotton uptrend, each producing buy signals when price closed above the consolidation. Each pattern's low served as a stop reference.

## Software analogy

Like a **deployment queue** in a CI/CD pipeline. Your main branch (the trend) is moving forward. Commits pile up in staging (the consolidation) — direction is clear but progress is paused. You can either:
- **Wait for the green build** (breakout confirmation) before deploying
- **Start provisioning infrastructure during the build** (enter within pattern) because you trust the pipeline

The first approach is safer. The second saves time but risks a rollback if the build fails.

## Breakout vs. anticipate: empirical comparison

From the Python demo on simulated trending data:

| Entry mode | Signals | Avg risk | Avg entry price |
|---|---|---|---|
| Breakout | 4 | $9.12 | $126.63 |
| Anticipate | 5 | $2.65 | $115.74 |

The anticipate mode gets **3.4× tighter risk** and a **better entry price**, but carries the risk of pattern failure.

## When this works best

- **Clear, established trends** with visible consolidation pauses
- Markets that form **well-defined flags and triangles** (many stocks do this)
- When combined with [[Multi-Timeframe Analysis]] — higher timeframe confirms the trend, lower timeframe identifies the pattern
- Traders comfortable with **visual pattern recognition** (some subjectivity acceptable)

## When it does NOT work

- **Choppy markets** — consolidation-like patterns form constantly but don't resolve cleanly
- Traders who require **fully mechanical, parameter-driven rules** — use [[Reversal of Minor Reaction]] instead
- When the "continuation" pattern turns out to be a **reversal pattern** (distribution top / accumulation bottom)
- Extremely short consolidations (<5 days) — too little structure to be meaningful

## Cross-references

### Within Chapter 8
- [[The Midtrend Entry Problem]] — The framework this strategy solves
- [[Percent Retracement Entry]] — Mechanical alternative based on % pullback
- [[Reversal of Minor Reaction]] — Mechanical alternative with N/X parameters
- [[Reaction to Long-Term Moving Average]] — Alternative using MA as reference
- [[Pyramiding Rules]] — Pattern breakouts are natural pyramid entry points

### Other chapters
- [[Continuation Patterns]] (Ch. 5) — Full treatment of flags, pennants, triangles
- [[Trading Ranges and Breakouts]] (Ch. 5) — Breakout mechanics in detail
- [[Confirmation Conditions]] (Ch. 7) — Breakout confirmation filters apply here too
- [[Failed Signals]] (Ch. 7) — A continuation pattern that breaks the *wrong* way is a powerful failed signal

## Python implementation

See `continuation_pattern_breakouts.py`:
- `detect_consolidation_zones()` — finds price congestion periods meeting min duration and max range criteria
- `classify_trend_before_zone()` — determines if the pre-zone trend was up, down, or neutral
- `continuation_breakout_signals()` — generates BUY/SELL signals in either `breakout` or `anticipate` mode
- `compare_entry_modes()` — side-by-side comparison of both approaches

## Key takeaway

> Continuation patterns offer visually intuitive midtrend entries with natural stop levels. The core decision is **breakout vs. anticipate** — confirmation vs. price. Schwager leans aggressive: if the trend is established, you can enter within the pattern. But unlike the previous two strategies, **pattern identification is inherently subjective**, which makes this approach harder to automate and backtest cleanly.
