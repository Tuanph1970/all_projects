---
title: "Bull Traps"
chapter: 11
concept: 2
tags:
  - failed-signals
  - bull-trap
  - reversal
  - breakout-failure
  - major-tops
  - schwager
  - chapter-11
aliases:
  - Bull Trap
  - False Upside Breakout
related:
  - "[[Failed Signals — The Overarching Principle]]"
  - "[[Bear Traps]]"
  - "[[Confirmation Conditions for Bull-Bear Traps]]"
  - "[[False Trend Line Breakouts]]"
  - "[[Ch4 — Trading Ranges and Support and Resistance]]"
  - "[[Ch5 — Chart Patterns]]"
  - "[[Ch9 — Choosing Stop-Loss Points]]"
---

# Bull Traps

## Definition

A **bull trap** is a major upside breakout from a consolidation range that is soon followed by an abrupt, sharp price reversal downward. The breakout *looks* like a legitimate buy signal but turns out to be false — trapping buyers who entered on the breakout.

> *"Bull and bear traps are major breakouts that are soon followed by abrupt, sharp price reversals, in stark contrast to the price continuation patterns that are expected to follow breakouts. In my experience, this type of counter-to-anticipated price action is among the most reliable indicators of major tops and bottoms."*
> — Schwager, Ch. 11

---

## Simple Analogy: The Fishing Lure

A bull trap works exactly like a fishing lure. The shiny lure (the breakout above resistance) attracts fish (buyers). They bite (enter long positions). Then the hook pulls them the opposite direction — trapped. The more attractive the lure looked, the more fish get caught, and the more violent the reversal.

The key insight: **the breakout itself was the bait.** Price rose just enough to trigger stop orders resting above resistance, but there was no genuine buying interest behind it.

---

## The Mechanism

Schwager describes the precise mechanics:

1. **Consolidation** → Price trades in a range, stops accumulate above resistance
2. **Breakout** → Price punches above resistance, triggering buy stops
3. **No follow-through** → After stops are swept, no additional buying support appears
4. **Reversal** → Without new buyers, trapped longs begin selling → price collapses

> *"Such price action is consistent with the market's rising just enough to activate stop orders lying beyond the boundary of the range, but uncovering no additional buying support after the breakout — an indication of a very weak underlying technical picture."*
> — Schwager, Ch. 11

---

## Confirmation Conditions

Schwager defines three progressively stricter confirmations (see also [[Confirmation Conditions for Bull-Bear Traps]]):

### 1. Initial Price Confirmation
- **Trigger**: Price retraces to the **midpoint** of the prior consolidation
- **Trade-off**: Better entry price, less certainty
- **Best for**: Aggressive traders willing to accept more whipsaws

### 2. Strong Price Confirmation
- **Trigger**: Price retraces to the **opposite boundary** (support / range low)
- **Trade-off**: More reliable signal, worse entry price
- **Best for**: Conservative traders who prioritize signal quality

### 3. Time Confirmation
- **Trigger**: Price fails to return to the breakout high within ~4 weeks
- **Usage**: Can be used alone or combined with either price confirmation
- **Note**: Schwager shows that time confirmation can occur before, after, or between the two price confirmations — the order is not fixed

---

## Invalidation Rules

A bull trap signal is **invalidated** if:

- **Primary**: Price returns to the breakout high → the breakout may be genuine
- **Sensitive** (after strong confirmation): Price returns to the top of the consolidation range after having broken below support

Once invalidated, exit the short position at the stop loss (the breakout high).

---

## Trading the Bull Trap

| Element | Rule |
|---|---|
| **Direction** | SHORT (sell) |
| **Entry** | At the confirmation level (midpoint for initial, support for strong) |
| **Stop loss** | At or slightly above the breakout high |
| **Target** | Hold until price objective, opposite trend reversal, or other exit criteria from [[Ch10 — Setting Objectives]] |
| **Position management** | If invalidation does not occur, hold the trade |

---

## When This Concept Works Best

- **After extended consolidation**: Longer ranges = more accumulated stops = more violent reversals
- **At record highs or multi-year highs**: Schwager's T-bond example was a six-year bull market peak. Bull traps at extremes tend to mark major tops
- **When volume diverges**: High volume on the breakout bar that immediately fades suggests stop-driven activity, not genuine demand
- **Multiple timeframe confluence**: If a higher timeframe chart shows price hitting major resistance, a lower-timeframe bull trap gains additional significance

---

## When to Be Cautious

- **Brief, shallow pullbacks after breakout are normal** — a slight dip back to resistance that then bounces is a healthy retest, not a bull trap
- **Strongly trending markets**: In a powerful uptrend, false breakouts are rarer; most breakouts follow through
- **The bull trap can itself fail**: Price drops to trigger initial confirmation, then reverses back up — this is a "failed failed signal." Always use the stop at breakout high
- **Don't anticipate**: Wait for at least initial price confirmation before entering; don't short just because a breakout "feels" extended

---

## Schwager's Key Example

**June 1994 T-bond** (Figure 11.2): The October 1993 upside breakout to new record highs above a seven-week trading range — at the peak of a six-year bull market — was immediately followed by a steep price break. This bull trap marked the major top.

---

## Cross-Chapter Links

- **[[Failed Signals — The Overarching Principle]]**: Bull traps are the most common specific application of the failed signal principle
- **[[Bear Traps]]**: The exact mirror image — failed downside breakout. Both share the same confirmation/invalidation framework
- **[[Confirmation Conditions for Bull-Bear Traps]]**: Detailed comparison of initial vs. strong vs. time confirmation trade-offs
- **[[Ch4 — Trading Ranges and Support and Resistance]]**: Consolidation ranges are where bull traps form; resistance is the breakout level
- **[[Ch5 — Chart Patterns]]**: Breakout patterns provide the "raw material" for bull traps
- **[[Ch9 — Choosing Stop-Loss Points]]**: The breakout high becomes the natural stop-loss for a bull trap short trade

---

## Python Implementation

See `bull_trap_detector.py` — specializes the base `failed_signal_detector.py` module:
- `detect_bull_trap()` — scans for consolidation → upside breakout → failure sequence
- Returns a `BullTrap` dataclass with all three confirmation flags
- `bull_trap_reward_risk()` — calculates reward-to-risk for the resulting short trade
- Includes invalidation logic (price exceeding breakout high)

---

## Key Takeaway

The bull trap is Schwager's poster child for failed signals. It's not just "the breakout didn't work" — it's that **the failure of the breakout is itself a high-conviction sell signal**. The novice sees a failed long trade. The skilled trader sees a short entry. That cognitive 180° turn is the core discipline of Chapter 11.
