---
title: "False Trend Line Breakouts"
chapter: 11
concept: 5
tags:
  - failed-signals
  - trend-lines
  - false-breakout
  - reversal
  - schwager
  - chapter-11
aliases:
  - False Trend Line Breakout
  - Failed Trend Line Penetration
  - False Trendline Break
related:
  - "[[Failed Signals — The Overarching Principle]]"
  - "[[Bull Traps]]"
  - "[[Bear Traps]]"
  - "[[Confirmation Conditions for Bull-Bear Traps]]"
  - "[[Ch3 — Trends]]"
  - "[[Ch9 — Choosing Stop-Loss Points]]"
---

# False Trend Line Breakouts

## Definition

A **false trend line breakout** occurs when price penetrates a trend line but then quickly reverses back through it in the original trend direction. The failed breakout is confirmed when a specified number of closes (e.g., two or three) occur back on the original side of the trend line.

> *"In my opinion, false trend breakout signals are considerably more reliable than conventional trend breakout signals."*
> — Schwager, Ch. 11

This is one of Schwager's strongest claims in the book: the failure of a trend line breakout is a **better** signal than the breakout itself.

---

## Simple Analogy: The Rubber Band Fence

Imagine a fence made of rubber bands (the trend line). Someone pushes through it — it stretches. But the rubber bands pull them right back. And now they snap back even harder to the other side, with the stored elastic energy from the stretch.

The "push through" is the breakout. The rubber bands pulling you back are the **original trend reasserting itself**. The snap-back past the fence is the **continuation of the trend** — accelerated by the energy of trapped breakout traders being forced out.

The fence was never broken. It was just tested and proven strong.

---

## The Mechanism

### False breakout of a downtrend line (most common scenario)

1. **Downtrend line** connects successive lower highs
2. Price **breaks above** the trend line → appears to signal trend reversal
3. Breakout buyers enter long positions
4. Price **falls back below** the trend line — no follow-through
5. Confirmation: **N consecutive closes below** the trend line (Schwager uses 2)
6. **Trade: SELL** — the downtrend is intact and now has trapped longs as fuel

### False breakout of an uptrend line (mirror)

1. **Uptrend line** connects successive higher lows
2. Price **breaks below** the trend line → appears to signal trend reversal
3. Breakout sellers enter short positions
4. Price **rebounds above** the trend line — no follow-through
5. Confirmation: **N consecutive closes above** the trend line
6. **Trade: BUY** — the uptrend is intact and now has trapped shorts as fuel

---

## Confirmation Rule

Schwager's confirmation is simple and mechanical:

| Parameter | Rule |
|---|---|
| **Trigger** | Price closes beyond the trend line (breakout) |
| **Failure** | Price returns back through the trend line |
| **Confirmation** | N consecutive closes (e.g., 2 or 3) on the original side |
| **Trade** | In the original trend direction |

The choice of N involves the usual sensitivity trade-off:
- **N = 2**: Earlier confirmation, more signals, some may be premature
- **N = 3**: Later confirmation, fewer signals, higher reliability

---

## Multiple False Breakouts and Trend Line Redefinition

This is a key insight unique to this concept. Schwager shows (Figure 11.7, July 1992 FCOJ) that **multiple successive false breakouts** can occur as the trend line is repeatedly redefined:

1. **Trend line I** → false upside breakout → confirmed → SELL
2. The false breakout creates a new high → **Trend line II** (redrawn using new high)
3. **Trend line II** → another false upside breakout → confirmed → SELL
4. New high → **Trend line III** (redrawn again)
5. **Trend line III** → yet another false breakout → confirmed → SELL

Each successive false breakout provides a **fresh sell signal** at a progressively lower level as the downtrend continues. This iterative redefinition is practically unique to false trend line breakouts among the failed signal types.

---

## When This Concept Works Best

- **Trend lines with many touches**: The more swing highs/lows the trend line connects, the more significant a false breakout becomes. Schwager's Allstate example (Figure 11.6) had four prior relative lows defining the uptrend line
- **After extended trends**: A trend line that has held for months has accumulated many believers — a false breakout traps more of them
- **When the breakout is brief and shallow**: A penetration that lasts only 1-3 bars before reversing is more likely a false breakout than a genuine trend change
- **In conjunction with other failed signals**: If a false trend line breakout coincides with a [[Bull Traps|bull trap]] or [[Filled Gaps as Failed Signals|filled gap]], the combined signal is stronger

---

## When to Be Cautious

- **Slight penetrations that don't close beyond the line**: Schwager notes in the Allstate example that an October penetration "did not close below the trend line, discounting its importance." The close is what matters, not the intraday touch
- **Rapidly accelerating breakouts**: If the breakout gains momentum over multiple bars with increasing volume, it may be genuine rather than false
- **Trend lines drawn through many redefinitions**: A trend line that has been redrawn 4+ times may be losing its analytical value — at some point the trend genuinely changes
- **Conflicting higher-timeframe signals**: A false breakout of a daily trend line that aligns with a breakout on the weekly chart may not be false at all

---

## Schwager's Key Examples

### Allstate Corp. (Figure 11.6)
False breakout of an **uptrend line** defined by four prior relative lows. The September downside breakout was soon followed by a break above the line. Confirmed by two closes above the line = BUY signal. October and January penetrations also occurred, with the October one being too shallow (no close below the line) to qualify.

### July 1992 FCOJ (Figure 11.7)
Three successive false breakouts of a **downtrend line**, each triggering a confirmed sell signal. The trend line was redefined three times (I → II → III) as each false breakout created a new relative high. This example demonstrates the iterative redefinition pattern.

---

## Key Contrast: Trend Line Breakouts vs. Range Breakouts

| Attribute | False Range Breakout (Bull/Bear Trap) | False Trend Line Breakout |
|---|---|---|
| Structure broken | Horizontal support/resistance | Diagonal trend line |
| Confirmation | Price retrace to midpoint or opposite boundary | N closes back on original side of line |
| Redefinition | Range doesn't change | Trend line redrawn after each false breakout |
| Multiple signals | Typically one trap per range | Multiple successive false breakouts possible |
| Source chapter | Ch 4 (trading ranges) | Ch 3 (trends) |
| Schwager's reliability | "Most reliable indicators of major tops/bottoms" | "Considerably more reliable than conventional trend breakouts" |

---

## Cross-Chapter Links

- **[[Failed Signals — The Overarching Principle]]**: False trend line breakouts are a specific application
- **[[Ch3 — Trends]]**: Schwager explicitly cross-references Ch 3, noting trend lines are "particularly prone to false breakouts" and "frequently redefined as they extend"
- **[[Bull Traps]]** / **[[Bear Traps]]**: Conceptually similar (failed breakout → trade opposite), but applied to horizontal ranges rather than diagonal trend lines
- **[[Ch9 — Choosing Stop-Loss Points]]**: The breakout extreme becomes the natural stop-loss level

---

## Python Implementation

See `false_trendline_breakout_detector.py`:

- `TrendLine` dataclass with `price_at(idx)` method for interpolation/extrapolation
- `find_downtrend_line()` / `find_uptrend_line()` — find best-fitting trend lines from swing points
- `detect_false_trendline_breakout()` — scans for breakout → N consecutive closes back on original side
- `scan_multiple_false_breakouts()` — iteratively finds successive false breakouts with automatic trend line redefinition (Schwager's FCOJ pattern)

---

## Key Takeaway

False trend line breakouts are Schwager's strongest example of a failed signal being more valuable than the original signal. The reason is structural: trend lines represent the equilibrium between supply and demand along a slope. A breakout that fails proves the slope is steeper than the market thought — and now has the added fuel of trapped breakout traders. The iterative redefinition pattern (multiple false breakouts in sequence) is unique to this concept and can generate a series of profitable trades from a single ongoing trend.
