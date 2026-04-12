---
title: Measured Move
chapter: 10
concept_number: 2
tags:
  - exit-strategy
  - price-objectives
  - measured-move
  - confluence
  - position-management
related:
  - "[[Chart-Based Objectives]]"
  - "[[Support and Resistance as Objectives]]"
  - "[[Trailing Stops]]"
  - "[[Trends]]"
  - "[[Trading Ranges]]"
  - "[[Continuous Futures Charts]]"
schwager_quote: "The underlying premise is that markets will move in approximately equal-size price swings."
---

# Measured Move

## Definition

The measured move projects that the **next price swing will approximate the size of the prior swing**. If a market rallies 30 cents and then reacts, the implication is that the next rally from the reaction low will also approximate 30 cents.

> "Although the measured move concept is so simple that it strains credibility, the approach offers reasonable guidelines more frequently than one might expect."
> — Schwager, Chapter 10

## Core Principle

**Markets tend to move in roughly symmetrical swings.** The "energy" of one swing carries forward into the next. Measure Swing 1 (start → end), then project that same distance from the reaction point (pullback) to get the target.

**Formula:**
```
Target = Reaction Point ± |Swing 1 size|
```
- `+` for upside projection (after an upswing reference)
- `−` for downside projection (after a downswing reference)

## Simple Analogy

**Skipping a stone across water.** Each skip covers roughly the same distance as the previous one. The stone doesn't know physics — it just has a certain energy, and each bounce uses about the same amount. If skip 1 was 10 feet, skip 2 will be roughly 10 feet. Not exact, but a surprisingly reliable guideline.

## Two Scales of Measurement

Schwager applies measured moves at **two simultaneous scales**:

| Scale | Label Style | Example |
|---|---|---|
| **Smaller swings** | Numbered (MM1, MM2, MM3...) | A 3-week rally within a trend |
| **Broader swings** | Lettered (MMA, MMB, MMC...) | The entire multi-month advance |

Both scales produce independent projections. When a small-swing and a broad-swing projection land in the same zone → **confluence**.

## Confluence: The Key Insight

> "When two or more of these objectives nearly coincide, it tends to enhance the reliability of the price area as an important objective zone."

This is the most actionable part of the concept. A single measured move target is a rough guideline. **Multiple independent targets converging** on the same price area transforms the guideline into a high-confidence zone.

### Schwager's Crude Oil Example (Figure 10.3)
Three independent upswings (Mar–May, June, Jun–Jul) all produced measured move targets that converged just below the actual August top. Three independent projections → one strong target zone.

### Schwager's Corn Example (Figure 10.2)
- MM4 (entire Jan–May decline) projected the November bottom almost exactly
- MM5 (Sep–Oct downswing) reinforced the same zone
- Together: "strong evidence that the market was near a major bottom"

## When It Works Best

- **Trending markets with clear swing structure** — alternating impulse and correction waves
- **When multiple independent projections converge** (confluence zones)
- **As a guideline for partial profit-taking** — take some off at the MM target, trail the rest
- **On continuous futures charts** rather than nearest futures (Schwager explicitly recommends this — see [[Continuous Futures Charts]])
- **Combined with [[Support and Resistance as Objectives]]** — MM target landing near S/R = doubly strong zone

## When It Fails

- In **choppy, trendless markets** where swing sizes are erratic
- When a single MM target is used as the sole exit criterion (use with [[Trailing Stops]])
- **MM4 in Schwager's Pepsico example** — coincided with the early May gap and was "significantly off-target" (his only miss in the illustration)

## Key Tradeoffs

- **Simplicity vs. precision**: The method is trivially simple but only approximate — treat targets as zones (±2–3%), not exact prices
- **Early exit risk**: Exiting at MM target may cause you to miss a larger trend extension
- **Scale multiplier**: Measuring at multiple swing scales simultaneously gives you more projection data, but also more noise — focus on zones where targets cluster

## Cross-References

### Within Chapter 10
- [[Chart-Based Objectives]] — Measured move is the simplest form of chart-based projection
- [[Support and Resistance as Objectives]] — Confluence multiplier when MM target hits S/R
- [[Trailing Stops]] — Complementary exit: partial at MM target, trail the rest

### Within the Book
- [[Trends]] (Chapter 3) — Swing structure is the foundation measured moves build on
- [[Trading Ranges]] (Chapter 4) — Breakout range height can also serve as a measured move reference
- [[Continuous Futures Charts]] (Chapter 2) — Schwager explicitly recommends these for MM analysis across contract rollovers
- [[Failed Signals]] (Chapter 11) — If price fails to reach the MM target and reverses sharply, treat as potential failed signal
- [[Multi-Timeframe Analysis]] (Chapter 7) — Measuring swings on both daily and weekly charts produces different-scale targets that may form confluence

## Python Implementation

See `measured_move.py` for:
- `measured_move()` — Single projection from one reference swing
- `find_confluence_zones()` — Detects price zones where multiple MM targets cluster
- `extract_swings()` — Zigzag swing extractor from raw price data
- `project_all_measured_moves()` — Batch projection from extracted swings

### Confluence Detection Algorithm
```python
targets = [
    measured_move(15.50, 18.20, 16.80, "MM1"),
    measured_move(16.80, 18.60, 17.40, "MM2"),
    measured_move(17.40, 19.10, 18.00, "MM3"),
]
zones = find_confluence_zones(targets, tolerance_pct=3.0)
# → Zone 19.22–19.72, center 19.47, 3 targets, high confidence
```

## Key Takeaway

The measured move is deceptively simple but "offers reasonable guidelines more frequently than one might expect." Its real power comes not from any single projection but from **confluence** — when multiple independent swings, measured at different scales, all point to the same target zone. That convergence is Schwager's signal that the zone deserves attention.
