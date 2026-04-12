---
title: "Relative High Low Stops"
chapter: 9
concept_number: 6
tags:
  - technical-analysis
  - stop-loss
  - swing-points
  - relative-high
  - relative-low
  - schwager
  - chapter-9
related:
  - "[[Stop-Loss Principle]]"
  - "[[Trading Range Stops]]"
  - "[[Trailing Stops]]"
  - "[[Money Stops]]"
  - "[[Wide-Ranging Day Stops]]"
created: 2026-04-08
---

# Relative High/Low Stops

## Definition

Use the **most recent relative high or relative low** as the stop placement point. A relative low at index i is a day whose low is below the lows of the preceding AND succeeding N days. A relative high is the mirror: a day whose high is above the highs of both surrounding N-day windows.

Schwager: *"A reasonable range for N is between 5 and 15."*

This is the **most versatile stop reference** in Chapter 9 — it works for initial stop placement AND as the anchor for [[Trailing Stops]].

### The N Parameter

| N value | Effect | Use case |
|---------|--------|----------|
| 3–5 | Many swing points, close to price | Aggressive stops, short-term trades |
| 7–10 | Moderate filtering | Schwager's Walt Disney example (N=10) |
| 12–15 | Few but major structural turns | Conservative stops, position trades |

Higher N = fewer but more significant swing points = wider stop = lower false rate but higher risk.

## Key Quotes (Schwager)

> "If the implied risk is not too great, the most recent relative high or relative low can be used as a stop point."

> "A drop below this level would negate the validity of a long position."

> "The general definition of a relative low is a day whose low is below the lows of the preceding and succeeding N days."

Critical caveat:

> "Sometimes the risk implied by even the closest technically significant points may be excessive. In this case, the trader may decide to use a money stop."

(The lumber example: nearest relative high implied $15,000 risk per contract.)

## Analogy: Recent Known-Good State Rollback

Like the **most recent known-good deployment checkpoint**:

| Deployment | Relative low stop |
|------------|------------------|
| Each deploy that survives N days = "known-good" | Each low that holds for N days on each side = relative low |
| Rollback to most recent checkpoint | Stop at most recent relative low |
| Checkpoint too far back → lose too much progress | Stop too far away → use a [[Money Stops\|money stop]] instead |
| New successful deploys move checkpoint forward | New relative lows raise the [[Trailing Stops\|trailing stop]] |

The parameter N = how long a deploy must survive to be promoted to "stable."

## Dual Role: Initial Stop + Trailing Stop Anchor

This is the only stop type that explicitly serves both roles in Schwager's framework:

### As initial stop
Use the most recent relative low before entry. If it implies excessive risk → switch to [[Money Stops|money stop]].

### As trailing stop anchor (Walt Disney example)
The stop ratchets up to each new relative low as the market moves to new high ground. From the book:
1. Initial stop → October low (stop 1)
2. December rally to new highs → stop raised to December low (stop 2)
3. Successive new highs → stops raised to stop 3, stop 4
4. Stopped out on decline below stop 4

*"In this example, a relative low is defined as the lowest low of the past 10 days."*

## When It Works Best

- **Trending markets** with clear swing structure (higher lows in uptrend, lower highs in downtrend)
- When the most recent swing point is **reasonably close** to entry (risk is acceptable)
- As the foundation for a **trailing stop system** — the most natural way to ratchet profits
- Combined with [[Confirmation Conditions]] (e.g., require a close below the relative low, not just an intraday touch)

## When It Fails

- **Choppy markets** where swing points cluster close together — N=5 produces too many reference points
- When the nearest relative low is **too far away** — the risk becomes excessive. Schwager's explicit answer: use a [[Money Stops|money stop]] instead
- Very **smooth trends** with few pullbacks — fewer relative lows form, leaving the stop stale

## Backtest Results

500 simulated scenarios, entry at bar 55, uptrend with reversal at bar 65:

| N | Avg risk | Avg P&L | Worst | False stop rate |
|---|----------|---------|-------|-----------------|
| 3 | 3.7% | -1.4% | -19.2% | 45.9% |
| 5 | 5.2% | -1.8% | -20.3% | 40.1% |
| 7 | 6.8% | -2.1% | -25.0% | 35.1% |
| **10** | **7.7%** | **-2.3%** | **-25.0%** | **30.0%** |
| 12 | 8.1% | -2.4% | -25.0% | 27.6% |
| 15 | 8.3% | -2.1% | -22.3% | 26.3% |

Key insight: N=10 (Schwager's Walt Disney example) sits at a natural inflection — false rate has dropped from 46% to 30%, while risk only grew from 3.7% to 7.7%.

## Trailing Stop Demo (N=10)

```
Entry: 104.8 at bar 20
  Bar 59: stop → 100.4 (relative low at bar 35)
  Bar 72: stop → 107.3 (relative low at bar 69)  ← ratcheted UP
Exit: 110.2 at bar 79, P&L: +5.2%, held 59 bars
```

The stop raised from 100.4 → 107.3 as new relative lows formed after new high ground — locking in profit while staying technically grounded.

## Cross-References

- **[[Stop-Loss Principle]]** (Ch. 9, Concept 1) — Relative lows implement Rule 2 (exit at invalidation) and naturally support Rule 3 (stops only tighten via trailing)
- **[[Trailing Stops]]** (Ch. 9, Concept 8) — Schwager's primary example uses relative lows as the trailing reference
- **[[Money Stops]]** (Ch. 9, Concept 7) — The explicit fallback when the nearest relative low is too far away
- **[[Trading Range Stops]]** (Ch. 9, Concept 3) — Trading range boundaries often coincide with relative highs/lows
- **[[Wide-Ranging Day Stops]]** (Ch. 9, Concept 5) — WRD extremes often become the next relative high/low
- **[[Confirmation Conditions]]** (Ch. 7) — Requiring a close below (not just intraday touch) reduces false stops

## Python Implementation

See `relative_high_low_stops.py`:

- `find_relative_lows()` / `find_relative_highs()` — configurable N parameter
- `nearest_relative_low_stop()` — finds the nearest prior swing low and warns if risk is excessive
- `relative_low_trailing_stop()` — full implementation of Schwager's Walt Disney trailing stop, with stop history showing each ratchet event
- `evaluate_n_parameter()` — backtests across N=3 to N=15

## Summary

Relative high/low stops are the **structural backbone** of Schwager's stop framework. They identify the swing points where the market demonstrated genuine support or resistance, and a violation of those points means the structure has changed. The N parameter is the single tuning dial: small N = more stops, tighter, more noise; large N = fewer stops, wider, more significant. The unique power is dual use: a relative low is both a valid initial stop AND the natural anchor for a trailing stop that ratchets as the trade progresses. When the nearest swing point implies too much risk, Schwager doesn't abandon the framework — he switches to a [[Money Stops|money stop]] as a deliberate tradeoff.
