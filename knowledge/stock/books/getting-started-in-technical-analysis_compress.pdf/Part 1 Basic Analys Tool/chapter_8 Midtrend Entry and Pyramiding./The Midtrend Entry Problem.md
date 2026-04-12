---
title: "The Midtrend Entry Problem"
aliases:
  - midtrend hesitation
  - late entry fear
  - too late to buy
chapter: 8
concept: 1
tags:
  - technical-analysis
  - schwager
  - psychology
  - entry-timing
  - trend-following
related:
  - "[[Percent Retracement Entry]]"
  - "[[Reversal of Minor Reaction]]"
  - "[[Continuation Pattern Breakouts]]"
  - "[[Reaction to Long-Term Moving Average]]"
  - "[[Pyramiding Rules]]"
  - "[[Confirmation Conditions]]"
  - "[[Failed Signals]]"
  - "[[Risk Control and Win Rate vs Profitability]]"
created: 2026-04-07
---

# The Midtrend Entry Problem

## Core idea

The midtrend entry problem is the psychological and tactical challenge of entering a trade **after price has already moved substantially**. Traders freeze because the prior move makes them feel "too late" — but Schwager shows this hesitation is often the real mistake, not the late entry itself.

> "Nobody can catch all the fluctuations." — Edwin Lefèvre

> "[Prices] are never too high to begin buying or too low to begin selling." — Edwin Lefèvre, *Reminiscences of a Stock Operator*

## Why traders hesitate

Schwager identifies three specific scenarios that leave a trader on the sidelines mid-trend:

1. **Not previously following the market** — the move was already underway before she noticed
2. **Waited for a pullback that never came** — she tried to get a better price and the market kept going
3. **Was skeptical, now convinced** — she doubted the sustainability of the trend but has changed her mind

In all three cases, the chart signals may be clearly bullish (breakout, flag pattern), but the magnitude of the existing move creates a psychological anchor: "it's overextended."

## The coffee example (1994)

Schwager's key illustration:

- By mid-May 1994, July coffee had broken above a **year-long trading range** and held new highs for two weeks
- Price had already risen **35% from the April low** in less than a month
- A trader would see textbook bullish signals but feel the move was "done"
- **Reality**: that 35% move was only **one-fifth** of the total advance
- The remaining **four-fifths** happened in just two more months

The lesson: a large prior move is **not evidence** that the trend is exhausted. It may be evidence that a powerful trend is *just getting started*.

## Software analogy

Think of joining an open-source project that already has 5,000 GitHub stars. It *feels* like you missed the window. But 5,000 stars is the **breakout from obscurity** — network effects are just kicking in. Most of the growth (to 50,000+ stars) happens *after* the project feels "already popular." Waiting for the project to "cool down" before contributing is the equivalent of waiting for a pullback that never comes.

## Key principle

The goals for midtrend entry are **identical** to any other entry:
1. **Favorable timing** — use pullbacks, consolidations, or reactions as entry points
2. **Risk control** — always define your stop-loss before entering

The existence of a prior move changes the *feeling* but should not change the *framework*. If the chart pattern is valid and you can define your risk, the entry is valid.

## Connection to pyramiding

Schwager explicitly states that midtrend entry and [[Pyramiding Rules|pyramiding]] are **the same problem** — both involve entering after a substantial move. The only difference is whether you already hold a position. All four midtrend strategies apply equally to pyramid timing.

## When this concept works best

- When you've identified a valid trend but feel "late" — use this as a mental check
- Before applying any of the four midtrend entry strategies (Concepts 2–5)
- When evaluating whether a breakout has "already run too far"
- As a framework for overcoming anchoring bias in trending markets

## When it does NOT apply

- In **range-bound/sideways** markets where there is no trend to join
- When the move is driven by a **one-time event** (earnings gap, regulatory action) with no structural follow-through expected
- When you cannot define a meaningful stop-loss level — the problem isn't hesitation, it's risk management

## Cross-references

### Within Chapter 8
- [[Percent Retracement Entry]] — Strategy 1 for solving the midtrend problem
- [[Reversal of Minor Reaction]] — Strategy 2
- [[Continuation Pattern Breakouts]] — Strategy 3
- [[Reaction to Long-Term Moving Average]] — Strategy 4
- [[Pyramiding Rules]] — Same problem, different context

### Other chapters
- [[Confirmation Conditions]] (Ch. 7) — Midtrend entry uses *less sensitive* confirmation than initial entries
- [[Failed Signals]] (Ch. 7) — A failed breakout mid-trend could reverse the thesis entirely
- [[Risk Control and Win Rate vs Profitability]] (Ch. 7) — Midtrend entries may have lower win rate but the trend's magnitude can still produce positive expected value
- [[Trading Ranges and Breakouts]] (Ch. 5) — The breakout from a range is often where the midtrend problem begins
- [[Continuation Patterns]] (Ch. 5) — Flags and consolidations within a trend are the natural entry points

## Python implementation

See `midtrend_entry_problem.py` — measures how far price has moved from a swing point, compares to historical trend magnitudes, and generates an assessment of whether "too late" hesitation is justified.

Key function: `assess_midtrend_position()` returns:
- Current move as % from swing
- Historical average/median/max trend sizes
- Estimated fraction of trend completed
- Human-readable assessment

## Key takeaway

> The magnitude of a prior move is not a reason to avoid a trade. It is a reason to **define your risk carefully** and use one of the four midtrend entry strategies to time the entry.
