---
title: "Percent Retracement Entry"
aliases:
  - retracement entry
  - buy the dip
  - pullback entry
chapter: 8
concept: 2
tags:
  - technical-analysis
  - schwager
  - entry-strategy
  - retracement
  - midtrend
related:
  - "[[The Midtrend Entry Problem]]"
  - "[[Reversal of Minor Reaction]]"
  - "[[Continuation Pattern Breakouts]]"
  - "[[Reaction to Long-Term Moving Average]]"
  - "[[Pyramiding Rules]]"
  - "[[Confirmation Conditions]]"
  - "[[Trading Ranges and Breakouts]]"
created: 2026-04-07
---

# Percent Retracement Entry

## Core idea

Enter a midtrend position when price **retraces a specified percentage** (typically 35–65%) of the prior swing. The swing low (for longs) or swing high (for shorts) serves as the stop-loss reference point.

This capitalizes on the natural tendency of markets to partially retrace prior moves before continuing the trend.

## How it works

### Long entry (uptrend)
1. Identify a completed swing: **swing low → swing high**
2. Calculate the retracement level: `entry = swing_high - (swing_high - swing_low) × retracement%`
3. Enter when price pulls back to this level
4. Place stop at or near the **swing low**

### Short entry (downtrend)
1. Identify a completed swing: **swing high → swing low**
2. Calculate: `entry = swing_low + (swing_high - swing_low) × retracement%`
3. Enter when price rallies to this level
4. Place stop at or near the **swing high**

## The core tradeoff

| Deeper retracement (65%) | Shallower retracement (35%) |
|---|---|
| Better entry price | Worse entry price |
| Tighter stop / less risk | Wider stop / more risk |
| Fewer fills (may never reach) | More fills |
| Misses strong trends | Catches strong trends |

> Schwager: "The main advantage of this method is that it is capable of providing superior entry points. However, it is also subject to a major disadvantage: Frequently, the necessary retracement condition may not be fulfilled until the trend has carried much further, or possibly even reversed."

## Schwager's example: 3Com Corp

Schwager illustrates two entries on 3Com:
- First entry at a **65% retracement** — deeper pullback, excellent price
- Second entry at a **50% retracement** — moderate pullback, still good

Both provided favorable entries relative to the prior swing highs.

## Software analogy

Like setting a "buy the dip" price alert on a stock. You decide: "I'll buy NVDA if it drops 10% from its recent high." If it dips 12%, you get a great entry. But if the stock only dips 5% and then rallies 40%, your order never fills and you miss the entire move. The retracement percentage is your **patience parameter** — higher patience means better price but higher miss rate.

## When this works best

- Markets with **regular, rhythmic pullbacks** within trends (many stocks, indices)
- When you want a **defined, mechanical entry rule** (no subjectivity)
- When the trend has clear, measurable swing highs and lows

## When it does NOT work

- **Parabolic/momentum-driven moves** — pullbacks are too shallow to trigger (like 1994 coffee)
- **Choppy, range-bound markets** — swings don't produce reliable trends
- When the "pullback" turns out to be a full trend reversal

## Choosing the retracement percentage

Schwager recommends the **35–65% range** as reasonable. The choice is a risk/reward preference:

- **Conservative (35%)**: more signals, worse prices, larger stops
- **Moderate (50%)**: balanced tradeoff — the "Fibonacci-adjacent" sweet spot
- **Aggressive (65%)**: fewer signals, best prices, tightest stops, highest miss rate

> Note: Schwager does not invoke Fibonacci ratios (38.2%, 61.8%) here, though the range he recommends overlaps with them. The concept is empirical, not mystical.

## Cross-references

### Within Chapter 8
- [[The Midtrend Entry Problem]] — The psychological barrier this strategy helps overcome
- [[Reversal of Minor Reaction]] — Alternative approach: wait for the pullback to *end*, then enter
- [[Continuation Pattern Breakouts]] — Alternative: enter on breakout from a consolidation
- [[Reaction to Long-Term Moving Average]] — Alternative: use MA as the pullback target
- [[Pyramiding Rules]] — Retracement entries work for adding to winners too

### Other chapters
- [[Confirmation Conditions]] (Ch. 7) — Retracement percentage is itself a confirmation threshold
- [[Trading Ranges and Breakouts]] (Ch. 5) — Breakouts from ranges create the swings this strategy measures
- [[Risk Control and Win Rate vs Profitability]] (Ch. 7) — Deeper retracement = lower risk per trade = better R:R ratio

## Python implementation

See `percent_retracement_entry.py`:
- `retracement_entry_signals()` — generates BUY/SELL signals at a given retracement %
- `compare_retracement_levels()` — compares signal count and avg risk across multiple thresholds (35%, 50%, 65%)
- `find_swings()` — identifies alternating swing highs/lows

## Key takeaway

> The retracement entry gives you a better price and tighter risk — but only if the pullback actually reaches your level. In strong trends, it may not. **The tradeoff between entry quality and fill probability is the defining tension of this strategy.**
