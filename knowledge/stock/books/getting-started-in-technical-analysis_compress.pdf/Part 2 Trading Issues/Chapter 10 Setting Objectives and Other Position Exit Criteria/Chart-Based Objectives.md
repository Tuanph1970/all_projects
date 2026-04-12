---
title: Chart-Based Objectives
chapter: 10
concept_number: 1
tags:
  - exit-strategy
  - price-objectives
  - chart-patterns
  - position-management
related:
  - "[[Measured Move]]"
  - "[[Support and Resistance as Objectives]]"
  - "[[Head and Shoulders]]"
  - "[[Trading Ranges]]"
  - "[[Confirmation Conditions]]"
  - "[[Failed Signals]]"
  - "[[Stop-Loss Points]]"
schwager_reliability: Less reliable as objectives than as trade signals
---

# Chart-Based Objectives

## Definition

Chart-based objectives use the **geometric structure of chart patterns** to project minimum price targets after a breakout. The measured distance within the pattern (e.g., head-to-neckline in a Head-and-Shoulders) becomes the projected distance of the move beyond the breakout point.

> "Generally speaking, chart patterns are probably considerably less reliable as indicators of price objectives than as trade signals."
> — Schwager, Chapter 10

## Core Principle

The "energy" stored in a pattern — reflected by its vertical height — provides a rough estimate of the subsequent move's magnitude. Wider or taller patterns imply larger projected moves.

## Simple Analogy

**A ball thrown into the air.** The height you throw it (pattern height) gives you a rough idea of how far it will travel on the other side. Not exact — wind and spin vary — but a reasonable guideline.

## Pattern Objective Rules

| Pattern | Measured Distance | Target |
|---|---|---|
| **Head-and-Shoulders** | Head to neckline | Neckline breakout ± measured distance |
| **Double Top/Bottom** | Peaks to intervening reaction | Reaction level ± measured distance |
| **Rectangle** | Range high − range low | Breakout boundary ± range height |
| **Point-and-Figure** | Number of columns × box size | Added to breakout level |

## When It Works Best

- When **multiple pattern objectives converge** on the same price zone (confluence increases reliability)
- As a **guideline for partial profit-taking**, not an absolute exit
- Combined with [[Support and Resistance as Objectives]] for stronger target zones
- In markets with **clear geometric patterns** (not choppy, noisy price action)

## When It Fails

- Schwager explicitly warns these are **less reliable than trade signals** — the pattern may correctly signal direction but overshoot or undershoot the target
- In strongly trending markets where momentum carries price well beyond the measured target
- When using pattern objectives as the **sole** exit criterion (better combined with [[Trailing Stops]] or [[Change of Market Opinion]])

## Key Tradeoffs

- **Precision vs. utility**: Targets are approximate, not exact — useful as zones rather than specific prices
- **Early exit risk**: Taking profits at the target may cause you to miss a larger move
- **Confluence multiplier**: When 2+ pattern objectives cluster near the same price, the zone becomes significantly more reliable (see [[Measured Move]] for examples)

## Cross-References

### Within Chapter 10
- [[Measured Move]] — A specific, simpler form of chart-based projection
- [[Support and Resistance as Objectives]] — Often coincides with pattern targets for confluence
- [[Trailing Stops]] — Complementary: use pattern target for partial profit, trailing stop for remainder

### Within the Book
- [[Head and Shoulders]] (Chapter 5) — Primary pattern example Schwager uses
- [[Trading Ranges]] (Chapter 4) — Rectangle breakout objectives derive from range height
- [[Confirmation Conditions]] (Chapter 7) — Validates the breakout before measuring the objective
- [[Failed Signals]] (Chapter 11) — When the breakout fails, the pattern objective becomes irrelevant; reverse the trade
- [[Stop-Loss Points]] (Chapter 9) — Combine with objectives for risk-reward calculation

## Python Implementation

See `chart_based_objectives.py` for:
- `head_and_shoulders_objective()` — H&S top/bottom target projection
- `double_top_bottom_objective()` — Double top/bottom target
- `rectangle_breakout_objective()` — Trading range breakout target
- `ChartObjective.risk_reward_ratio(stop_price)` — R:R calculation using the projected target

## Key Takeaway

Chart-based objectives are **guideline zones, not exact targets**. Their value increases dramatically when multiple independent projections converge on the same area. Always combine with other exit methods ([[Trailing Stops]], [[Overbought Oversold Indicators as Exit Signals]]) rather than relying on pattern targets alone.
