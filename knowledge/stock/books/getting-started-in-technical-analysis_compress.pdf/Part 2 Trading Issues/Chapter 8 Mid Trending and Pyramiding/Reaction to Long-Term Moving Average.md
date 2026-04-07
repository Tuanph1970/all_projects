---
title: "Reaction to Long-Term Moving Average"
aliases:
  - MA pullback entry
  - moving average reaction
  - buy at the moving average
  - mean reversion entry
chapter: 8
concept: 5
tags:
  - technical-analysis
  - schwager
  - entry-strategy
  - midtrend
  - moving-average
  - sensitivity
related:
  - "[[The Midtrend Entry Problem]]"
  - "[[Percent Retracement Entry]]"
  - "[[Reversal of Minor Reaction]]"
  - "[[Continuation Pattern Breakouts]]"
  - "[[Pyramiding Rules]]"
  - "[[Confirmation Conditions]]"
created: 2026-04-07
---

# Reaction to Long-Term Moving Average

## Core idea

Enter a midtrend position when **price pulls back to a long-term moving average**. The MA acts as a dynamic support level (uptrend) or resistance level (downtrend).

- **Uptrend**: Buy when price declines to or below the MA
- **Downtrend**: Sell short when price rallies to or above the MA

Schwager uses a **40-day moving average** in his Dell Computer example, noting multiple buy opportunities as price repeatedly dipped to the MA during a sustained uptrend.

## How it works

The moving average represents the **average consensus price** over the lookback period. In a healthy uptrend:

1. Price normally stays above the MA (recent buyers are profitable)
2. Periodic pullbacks bring price back to the MA (mean reversion)
3. These pullbacks are entry opportunities — the trend hasn't changed, price just returned to "fair value"
4. Entry triggers when price **crosses below** (or touches) the MA
5. If the trend is genuine, price rebounds and moves higher

## The sensitivity principle (Schwager's key insight)

This section contains the most conceptually important passage in Chapter 8. Schwager explains that **the same tool** — moving average crossover — serves **opposite purposes** at different sensitivity levels:

### Countertrend re-entry (this strategy, Chapter 8)
- **Price** vs. **one MA**
- Price has **no smoothing** — reacts instantly
- Deliberately **high sensitivity** — catches every pullback
- ~20 signals per year (from demo data)

### Trend identification (Chapter 14)
- **MA** vs. **MA** crossover
- **Both** series are smoothed — filters noise
- Deliberately **low sensitivity** — avoids whipsaws
- ~3–7 signals per year

> Schwager: "We deliberately defined crossover points based on the price series itself (which is more sensitive than a moving average since it contains no smoothing of the data) and one moving average. In other words, we would use more sensitive definitions of moving average crossovers for countertrend applications than we would for trend-identification applications."

### Why this makes sense

You can afford high sensitivity for re-entry because you have a **prior belief** that the trend exists. You're not discovering a new trend (where false signals are costly) — you're rejoining one you already trust (where missing a pullback is the real cost).

This is the **same principle** from [[Reversal of Minor Reaction]]: X=3 for re-entry vs. X=20+ for trend identification in Chapter 17.

## Choosing the MA period

| Period | Sensitivity | Signals | Best for |
|---|---|---|---|
| **20-day** | High | Many | Active traders, frequent re-entries |
| **40-day** | Medium | Moderate | Schwager's example, balanced approach |
| **60-day** | Low | Few | Swing traders, only deep pullbacks |

From the Python demo:
- 20-day MA → 24 signals, avg entry $115.0
- 40-day MA → 20 signals, avg entry $118.3
- 60-day MA → 15 signals, avg entry $118.5

Shorter period = more signals but catches shallower pullbacks (potentially more noise).

## Schwager's example: Dell Computer

Schwager superimposes a 40-day MA on a Dell stock chart during an uptrend. Multiple arrows mark where price pulled back below the MA — each was a buy opportunity. The key observation: the stock kept trending higher despite these temporary pullbacks below the average.

## Software analogy

Think of the MA like a **load balancer health threshold**. Normal traffic (price) fluctuates around the rolling average response time (the MA). In a healthy system (uptrend):
- Traffic spikes that push response time briefly above the threshold aren't emergencies — they're opportunities to scale up (buy)
- The system reverts to normal because the underlying health is intact
- You only worry when response time stays above the threshold persistently (trend reversal)
- The MA period is your rolling window: 10-second catches every hiccup, 5-minute only catches sustained degradation

## When this works best

- **Smooth, steady trends** where price has a clear relationship with the MA
- Markets that exhibit **regular mean-reversion** to the average
- When combined with other evidence the trend is intact (higher timeframe, volume, fundamentals)
- **Simple to implement** — one parameter (MA period), fully mechanical, easy to backtest

## When it does NOT work

- **Volatile, gappy markets** — price may blow through the MA on news and not revert
- **Flat/sideways markets** — price crosses the MA constantly, generating false signals
- **Parabolic trends** — price stays so far above the MA that pullbacks never reach it
- When the trend is **actually reversing** — the MA pullback becomes the start of a new downtrend

## No contradiction with Chapter 14

Schwager anticipates the reader's confusion: "There is no contradiction." The same MA tool serves different purposes:
- **Chapter 8**: Price crossing below MA = countertrend entry opportunity (high sensitivity, one MA)
- **Chapter 14**: MA crossing below MA = trend reversal signal (low sensitivity, two MAs)

The difference is entirely in **what you're comparing** and **how much smoothing** is applied.

## Cross-references

### Within Chapter 8
- [[The Midtrend Entry Problem]] — The framework this strategy solves
- [[Percent Retracement Entry]] — Uses a fixed % level; this uses a dynamic level (the MA)
- [[Reversal of Minor Reaction]] — Similar sensitivity principle (small X for re-entry)
- [[Continuation Pattern Breakouts]] — Pattern-based alternative; more subjective
- [[Pyramiding Rules]] — MA reaction entries work well for adding to winners

### Other chapters
- Moving Average Crossovers (Ch. 14) — Same tool, low sensitivity, for trend reversal signals
- Breakout Systems (Ch. 17) — Same sensitivity principle: tight for re-entry, wide for identification
- [[Confirmation Conditions]] (Ch. 7) — MA period choice is a form of confirmation threshold
- [[Multi-Timeframe Analysis]] (Ch. 7) — Use weekly MA for trend direction, daily MA for entry timing

## Python implementation

See `reaction_to_ma.py`:
- `ma_reaction_signals()` — generates BUY/SELL signals on price-vs-MA crossovers
- `compare_ma_periods()` — compares signal count across 20/40/60-day periods
- `sensitivity_comparison_table()` — demonstrates Schwager's key insight: price-vs-MA (high sensitivity) vs. MA-vs-MA (low sensitivity) signal counts

## Key takeaway

> The moving average is a **dual-purpose tool**. At high sensitivity (price vs. MA), it catches midtrend pullbacks for re-entry. At low sensitivity (MA vs. MA), it identifies trend reversals. Schwager's critical insight: **you deliberately use more sensitive settings for re-entry than for identification**, because the cost of missing a pullback is higher than the cost of a false signal when you already trust the trend.
