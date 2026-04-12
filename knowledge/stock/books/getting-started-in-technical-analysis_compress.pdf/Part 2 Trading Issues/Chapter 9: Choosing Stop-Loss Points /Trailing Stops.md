---
title: "Trailing Stops"
chapter: 9
concept_number: 8
tags:
  - technical-analysis
  - stop-loss
  - trailing-stop
  - profit-protection
  - relative-low
  - schwager
  - chapter-9
related:
  - "[[Stop-Loss Principle]]"
  - "[[Relative High Low Stops]]"
  - "[[Money Stops]]"
  - "[[CIC Anti-Pattern]]"
  - "[[Confirmation Conditions]]"
  - "[[Trading Range Stops]]"
created: 2026-04-09
---

# Trailing Stops

## Definition

A stop that **ratchets in the direction of profit** as the trade moves favorably. For a long position, the stop is raised intermittently as the market rises; for a short position, lowered as it falls. The stop never moves against the trade direction ([[Stop-Loss Principle|Rule 3]]).

This is a **phase transition** in the chapter: everything before it answers "how do I limit losses?" Trailing stops answer "**how do I keep what I've gained?**"

Schwager describes two flavors with explicitly different quality levels.

### Flavor 1: Chart-based trailing (preferred)

Keyed to [[Relative High Low Stops|relative lows]]. The stop advances to each new relative low after the market makes new high ground. Schwager's Walt Disney example is the definitive illustration.

### Flavor 2: Fixed-distance trailing (compromise)

A fixed dollar, percentage, or point value trail. Schwager is explicit about its limitation: *"This technique has the same implications as the simple money stop... It keeps risk at a known level... but may also liquidate a trade when there is no technical reason for doing so."*

## Key Quotes (Schwager)

> "Stops should be used not only to limit losses but also to protect profits. In the case of a long position, the stop should be raised intermittently as the market rises."

> "The trader plans to liquidate the long position following a close below the most recent relative low with the reference point being revised each time the market moves to new high ground."

> "The stop condition may often be more restrictive. For example, the trader might require a specified number of closes below a previous low, or a minimum penetration of that low to activate the stop."

> "A trailing stop could follow a position by a fixed dollar, percentage, or point value. This technique, however, has the same implications as the simple money stop."

## The Walt Disney Example (Schwager's Full Protocol)

Schwager walks through this step by step — it's the most complete worked example in the chapter:

| Step | Trigger | Action | Reference |
|------|---------|--------|-----------|
| Entry | November upside gap above trading range | Enter long | — |
| Stop 1 | Initial position | Stop at October low | N=10 relative low |
| Stop 2 | December rally to new highs | Raise stop to December low | New high ground → new ref |
| Stop 3 | Further new highs | Raise to next relative low | Same rule |
| Stop 4 | Another new high | Raise again | Same rule |
| Exit | Price declines below Stop 4 in May | Liquidate | Stop triggered |

**The protocol:**
1. Initial stop = most recent relative low before entry
2. **Only raise after new high ground** — no raise during sideways or pullback phases
3. New stop level = most recent relative low (N=10)
4. The stop never moves down
5. Optional confirmation: require N closes below the level, or minimum penetration

## Analogy: Autoscaling with a High-Water Mark

| Metric-driven autoscaling | Chart-based trailing |
|--------------------------|---------------------|
| Scale up when traffic hits new high-water mark | Raise stop when price makes new high ground |
| Baseline = most recent proven-stable load level | Stop = most recent relative low |
| Only raise baseline after sustained new level | Only raise after new high ground confirmed |
| Traffic below baseline → investigate | Price below stop → exit |

| Percentage headroom autoscaling | Fixed-distance trailing |
|-------------------------------|----------------------|
| Always keep capacity at 120% of peak | Always trail by fixed % below high |
| 20% buffer has no relationship to stability | % distance has no chart basis |
| May downscale during legitimate seasonal dip | May exit during normal pullback |

Both obey the same rule: **the baseline only moves in one direction**.

## Confirmation Conditions for Trailing Stops

Schwager explicitly notes these can tighten the trailing stop, connecting back to [[Confirmation Conditions]] from Chapter 7:

| Condition | Effect | Tradeoff |
|-----------|--------|----------|
| Require N closes below the relative low | Filters intraday whipsaws | May exit later, larger loss |
| Require minimum penetration below the low | Filters marginal violations | Same tradeoff |
| Both combined | Maximum filtering | Maximum delay |

These are the same filters used for breakout confirmation, applied to exit signals.

## Backtest Results (500 trials)

| Metric | Chart-based (N=10) | Fixed (5%) |
|--------|-------------------|------------|
| Avg P&L | **+5.3%** | +4.4% |
| Median P&L | **+3.3%** | +0.2% |
| Win rate | **55.6%** | 51.6% |
| Best case | **+66.1%** | +59.6% |
| Worst case | -33.9% | **-7.8%** |

### Why chart-based wins on average

Chart-based trailing stays in trades during **normal pullbacks** that don't violate a relative low. A 3% pullback in a healthy uptrend triggers a 5% fixed trail but doesn't violate the structural swing low. Chart-based trailing rides through the noise; fixed trailing exits on it.

### Why fixed wins on worst-case

Fixed trailing caps the maximum giveback to a known percentage. Chart-based trailing can give back large amounts if the swing low is far below the high-water mark — especially with large N values.

### The tradeoff in one sentence

Chart-based = **more trend capture, more tail risk**. Fixed = **less trend capture, bounded tail risk**.

## When It Works Best

- **Trending markets** with clear swing structure — chart-based trailing shines when higher lows form naturally
- **Long-duration position trades** — the ratchet has time to raise the stop through multiple relative lows
- Combined with [[Confirmation Conditions]]: requiring N closes below the relative low before triggering reduces whipsaw exits significantly
- As the natural continuation of any initial stop type — money stop, range stop, or swing stop all transition into trailing as the trade matures

## When It Fails

- **Choppy, range-bound markets** — relative lows form but don't trend higher, so the stop never ratchets meaningfully
- **V-shaped reversals** — price collapses without forming intermediate relative lows, so chart-based trailing can give back the entire move before the first stop level is hit
- **Large N values in fast markets** — the relative low is so far back that the trailing stop is nearly useless as profit protection

## The Trailing Stop Lifecycle

Every trade has a natural stop evolution:

```
Entry → Initial stop (chart or money) → Trade moves in favor →
  → First pullback forms relative low → Raise stop →
    → Next new high → Next pullback → Raise again →
      → Eventually: stopped out at a structurally meaningful level
```

This is the **ideal path** through the chapter's concepts: initial placement (Concepts 2-7) transitions into trailing protection (Concept 8), with CIC (Concept 9) as the failure mode at every step.

## Cross-References

- **[[Stop-Loss Principle]]** (Ch. 9, Concept 1) — Trailing stops implement Rule 3: "stops should only be changed in order to reduce risk"
- **[[Relative High Low Stops]]** (Ch. 9, Concept 6) — The natural anchor for chart-based trailing; Schwager's Walt Disney example uses N=10 relative lows exclusively
- **[[Money Stops]]** (Ch. 9, Concept 7) — Fixed trailing has the identical limitation: "keeps risk at a known level but may also liquidate a trade when there is no technical reason for doing so"
- **[[CIC Anti-Pattern]]** (Ch. 9, Concept 9) — The opposite of trailing: moving stops to increase risk. Every trailing stop raise is a one-way ratchet; CIC undoes the ratchet.
- **[[Confirmation Conditions]]** (Ch. 7) — Require multiple closes below or minimum penetration to filter false trailing stop triggers
- **[[Trading Range Stops]]** (Ch. 9, Concept 3) — A trade that enters on a range breakout transitions to trailing stops once in profit

## Python Implementation

See `trailing_stops.py`:

- `chart_based_trailing_stop()` — Full implementation of the Walt Disney method with relative lows, stop history, and raise counting
- `fixed_trailing_stop()` — Fixed percentage trail below high-water mark
- `compare_trailing_methods()` — Head-to-head backtest across 500 scenarios

## Summary

Trailing stops mark the **phase transition** in Chapter 9 from loss control to profit protection. Chart-based trailing (keyed to relative lows) produces better average results and higher win rates because it stays in trades during normal pullbacks. Fixed trailing provides tighter worst-case control but exits on noise. Schwager's preference is unambiguous: chart-based is the standard; fixed is the fallback with the "same implications as the simple money stop." The fundamental rule governing both: **the stop only moves in one direction.**
