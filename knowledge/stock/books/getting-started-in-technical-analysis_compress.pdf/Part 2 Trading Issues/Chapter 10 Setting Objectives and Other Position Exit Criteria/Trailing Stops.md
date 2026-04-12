---
title: Trailing Stops
chapter: 10
concept_number: 6
tags:
  - exit-strategy
  - trailing-stop
  - risk-management
  - position-management
  - trend-following
related:
  - "[[Stop-Loss Points]]"
  - "[[Overbought Oversold Indicators as Exit Signals]]"
  - "[[Support and Resistance as Objectives]]"
  - "[[Measured Move]]"
  - "[[Trends]]"
  - "[[Trading Ranges]]"
  - "[[Wide-Ranging Days]]"
schwager_quote: "The use of trailing stops may be among the least glamorous, but most sensible, methods of determining a trade exit point."
---

# Trailing Stops

## Definition

A trailing stop is a **dynamically adjusted stop-loss** that moves in the direction of the trade as price advances, locking in progressively more profit while allowing the trade to continue running. The stop **only moves to reduce risk, never to increase it.**

> "Although one will never sell the high or buy the low using this method, the approach comes closest to the ideal of permitting a profitable trade to run its course."
> — Schwager, Chapter 10

## Core Principle

Schwager calls this the **"most sensible"** exit method and the one **"closest to the ideal."** This is his highest endorsement in the entire chapter. The logic: you accept that you will *never* exit at the perfect price, but by ratcheting the stop upward with each new high, you capture the bulk of every move while being automatically removed when the trend reverses.

The critical behavioral rule from Chapter 9:
> "Stops should only be changed in order to reduce risk. Revising the stop to allow greater risk defeats the entire purpose of the stop."

A stop that gets cancelled when price approaches it is a **"CIC (cancel if close) order"** — Schwager's derisive term for self-sabotage.

## Simple Analogy

**Walking a dog on a retractable leash.** The dog (price) runs ahead, and you let the leash extend. As it gets farther ahead, you reel in slack — but you never pull the dog backward. The leash only shortens (stop only moves in your favor). If the dog turns around and runs past you (price reverses through the stop), the leash snaps taut and the walk is over. You didn't catch the dog at its farthest point, but you captured most of the ground it covered.

## Schwager's Five Stop Reference Points (Chapter 9)

| Reference Point | How It Works | Tradeoff |
|---|---|---|
| **Relative lows/highs** | Stop at N-bar low; raised each time price makes new high | Best balance of technical significance and profit capture |
| **Trend lines** | Stop below uptrend line | Earliest reversal signal but prone to false triggers |
| **Trading range boundaries** | Stop at midpoint or far side of range | Wider stop = more room but more risk |
| **Flags/pennants** | Stop at opposite end of formation | Pattern-specific; only applies when formations appear |
| **Wide-ranging days** | Stop at opposite extreme of WRD | Powerful when available; see [[Wide-Ranging Days]] |

Plus the non-technical option:
| **Fixed %/dollar (money stop)** | Stop trails by fixed amount | "No technical significance" — may exit without technical reason |

## The Ratchet Principle

The trailing stop works like a **ratchet mechanism** — it clicks forward and cannot go backward:

1. **New high made** → calculate new stop level → if higher than current stop → raise stop (ratchet up)
2. **No new high** → stop stays at current level (never lowered)
3. **Price hits stop** → exit immediately

The number of ratchet points tracks how actively the stop is engaging with the trend. More ratchets = a strong trend being captured step by step.

## Three Implementation Methods

### 1. Relative Low (Schwager's Preferred)
Stop = lowest low of last N bars. Schwager uses N=10 in his Walt Disney example (Figure 9.6). Produces a staircase pattern — stop jumps up discretely when old lows rotate out of the lookback window.

**Strengths**: Technically meaningful; each stop level sits at actual market structure. N=5 to 15 is Schwager's recommended range.

### 2. Fixed Percentage Trail
Stop = highest price × (1 − trail%). Smooth and simple.

**Schwager's caveat**: *"This technique has the same implications as the simple money stop: it keeps risk at a known level but may also liquidate a trade when there is no technical reason for doing so."*

### 3. ATR Multiple Trail
Stop = highest price − (ATR × multiple). Adapts to market volatility — wider stops in volatile markets, tighter in calm ones. Not in Schwager's original text but a natural extension of his ATR discussion in the Appendix.

## When It Works Best

- **Trending markets** — this is the trailing stop's natural habitat. While [[Overbought Oversold Indicators as Exit Signals]] fail in trends, trailing stops excel
- **As the "second half" of a combined exit strategy** — take partial profits at a [[Measured Move]] target or [[Support and Resistance as Objectives]] level, trail the remainder
- **When discipline matters** — the mechanical nature removes emotional decision-making from the exit
- **Long-duration trades** — trailing stops let profits compound across extended moves

## When It Fails

- **Trading range markets** — price oscillates and triggers stops repeatedly without trending; this is the mirror image of the OB/OS problem
- **With lookback too short** (N < 5) — normal market noise triggers the stop prematurely
- **With lookback too long** (N > 20) — too much profit surrendered before stop catches the reversal
- **When the trader manually overrides** — Schwager's "CIC order" problem

## The Regime Complement

This is the key structural insight connecting Concepts 4 and 6:

| Market Regime | OB/OS Oscillators | Trailing Stops |
|---|---|---|
| **Trading range** | **Work well** | Fail (whipsawed) |
| **Strong trend** | Fail (premature exits) | **Work well** |

The two methods are **exact complements**. Each excels where the other fails. The optimal strategy: use a regime detector to choose, or combine both — partial exit at OB/OS level, trail the remainder.

## Cross-References

### Within Chapter 10
- [[Overbought Oversold Indicators as Exit Signals]] — The structural opposite: excels in ranges, fails in trends. Together they cover all regimes
- [[Measured Move]] — Take partial at MM target, trail the rest
- [[Support and Resistance as Objectives]] — Take partial at S/R, trail the rest
- [[Contrary Opinion]] — Extreme sentiment + trailing stop = belt-and-suspenders exit
- [[Change of Market Opinion]] — The subjective version of the same "let it run until something changes" principle

### Within the Book
- [[Stop-Loss Points]] (Chapter 9) — Full treatment of all stop placement methods; trailing stops are the profit-protection application
- [[Trends]] (Chapter 3) — Trailing stops are built for trend-following
- [[Trading Ranges]] (Chapter 4) — The regime where trailing stops get whipsawed
- [[Wide-Ranging Days]] (Chapter 5/9) — One of Schwager's specific stop reference points
- [[Risk Control and Win Rate vs Profitability]] (Chapter 7) — Trailing stops maximize the reward side of R:R by letting winners run
- [[Confirmation Conditions]] (Chapter 7) — The lookback N has the same sensitivity tradeoff as confirmation time delays

## Python Implementation

See `trailing_stops.py` for:
- `trailing_stop_relative_low()` — Schwager's preferred method (Ch. 9 Figure 9.6)
- `trailing_stop_percentage()` — Fixed percentage trail (with Schwager's caveat)
- `trailing_stop_atr()` — Volatility-adaptive trail (ATR multiple)
- `compare_trailing_methods()` — Side-by-side comparison on same price data

### Combined Exit Strategy Pattern
```python
from trailing_stops import trailing_stop_relative_low
from measured_move import measured_move
from sr_as_objectives import find_objectives

# Step 1: Set measured move target
mm = measured_move(swing_start, swing_end, reaction_point)

# Step 2: At MM target, take 50% off
# Step 3: Trail the remaining 50%
trail = trailing_stop_relative_low(prices, entry_idx, lookback=10)

# This captures both the measured target AND any trend extension
```

## Key Takeaway

Trailing stops earn Schwager's highest praise in Chapter 10 — **"most sensible"** and **"closest to the ideal."** They solve the fundamental problem of letting winners run without surrendering all profits on the reversal. The tradeoff is explicit and honest: you will *never* exit at the peak, but you will capture the bulk of every trend. Combined with the price-target methods (Concepts 1–3) for partial exits, trailing stops form the backbone of a complete exit strategy. And critically, they are the **regime complement** to OB/OS oscillators — together, they cover both trending and range-bound markets.
