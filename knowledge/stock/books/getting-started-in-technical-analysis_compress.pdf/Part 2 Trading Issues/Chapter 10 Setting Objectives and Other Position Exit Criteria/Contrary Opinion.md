---
title: Contrary Opinion
chapter: 10
concept_number: 5
tags:
  - exit-strategy
  - sentiment
  - contrary-opinion
  - position-management
  - market-psychology
related:
  - "[[Overbought Oversold Indicators as Exit Signals]]"
  - "[[Trailing Stops]]"
  - "[[Change of Market Opinion]]"
  - "[[Trading Ranges]]"
  - "[[Trends]]"
  - "[[Failed Signals]]"
schwager_quote: "Although contrary opinion is undoubtedly a sound theoretical concept, the Achilles' heel of this approach is the difficulty of measuring market sentiment accurately."
---

# Contrary Opinion

## Definition

The theory that when a **large majority of speculators are bullish**, those who want to be long are already long. There will be a paucity of potential new buyers, making the market vulnerable to a downside reaction. The reverse applies when the majority is bearish.

> "Contrary opinion measures are based either on surveys of recommendations contained in market letters or on trader surveys, and implicitly assume that these opinions represent a reasonable proxy for overall market sentiment."
> — Schwager, Chapter 10

## Core Principle

This is a **supply-and-demand argument about remaining participants**, not a claim that the crowd is "wrong." When most potential buyers have already bought, the fuel for further price increases is exhausted. The next marginal order is more likely to be a sell, making the market vulnerable.

| Sentiment Extreme | What It Means | Market Implication |
|---|---|---|
| **80%+ bullish** | Most who want to buy already have | Few new buyers → vulnerable to decline |
| **20%- bullish** | Most who want to sell already have | Few new sellers → vulnerable to rally |

## Simple Analogy

**A crowded elevator.** When nearly everyone who wants to go up is already packed inside, there's nobody left in the lobby to press "up." The elevator can't go higher. The next move is probably down — people getting off. But the catch: you can't see exactly how many people are still in the lobby. Sometimes it looks empty but there's a long queue around the corner. That's why extreme sentiment *suggests* a reversal but doesn't guarantee one.

## Schwager's Two-Sided Assessment

### The Strength
> "Contrary opinion measures provided by existing services have frequently signaled major turning points."

Extreme sentiment readings *do* cluster around significant market tops and bottoms. The theoretical logic is sound and has empirical support at major turning points.

### The Achilles' Heel (Two Failure Modes)

**1. Measurement problem:**
> "The Achilles' heel of this approach is the difficulty of measuring market sentiment accurately."

Sentiment surveys measure *opinions*, not *positions*. Someone can be bullish in a survey without being long. Newsletter recommendations may not reflect actual trading. The map isn't the territory.

**2. Persistence problem:**
> "It is also not unusual for a contrary opinion index to stay high while the market continues to climb, or to stay low as the market continues to slide."

This is structurally identical to the OB/OS persistence problem from [[Overbought Oversold Indicators as Exit Signals]] — both fail during strong trends because the "extreme" condition can sustain itself as new participants enter the market.

## When It Works Best

- **At major turning points** — Schwager says this is where contrary opinion "frequently" works
- **When combined with technical confirmation** — Chapter 14 describes contrary opinion as a countertrend input "contingent on confirmation by a very sensitive technical indicator"
- **As a caution flag**, not a trade trigger — extreme sentiment says "be alert for reversal signals," not "reverse now"
- **In conjunction with other exit methods** — contrary opinion reading at extreme + RSI overbought + price at [[Measured Move]] target = strong confluence exit
- **At the end of extended moves** — after a long trend, the pool of remaining participants is genuinely thin

## When It Fails

- **During strong trends** — new participants keep entering, refilling the "empty lobby"
- **As a standalone system** — Schwager explicitly: *"as long as it is not used as the sole trading guideline"*
- **When measurement is poor** — small survey samples, self-selected respondents, or surveys that measure intent rather than positioning
- **In markets with large institutional participation** — surveys of retail newsletter writers may not capture institutional flows

## Connection to Chapter 14: Countertrend Systems

Schwager references contrary opinion again in Chapter 14 as an input for **countertrend trading systems**:

> "A countertrend system might use contrary opinion as an input in timing trades. For example, once the contrary opinion rose above a specified level, a short position would be indicated contingent on confirmation by a very sensitive technical indicator."

This is the practical implementation: sentiment extreme → *wait for* technical confirmation → then act. The sentiment reading is the alert; the technical signal is the trigger.

## Cross-References

### Within Chapter 10
- [[Overbought Oversold Indicators as Exit Signals]] — Same structure: both measure "extremes" that work in ranges but persist in trends. RSI measures price momentum extremes; contrary opinion measures participation extremes. Combining them creates stronger confluence.
- [[Trailing Stops]] — The trending-market complement; when sentiment stays extreme, trailing stops protect profits where contrary opinion fails
- [[Change of Market Opinion]] — The subjective equivalent; rather than measuring crowd sentiment, the trader evaluates their own market thesis
- [[Support and Resistance as Objectives]] — Contrary opinion extreme near an S/R level = doubly strong exit zone

### Within the Book
- [[Oscillators]] (Chapter 6) — OB/OS oscillators and contrary opinion measure different kinds of "overextension" (price momentum vs. participant sentiment) but share the same structural weakness
- [[Failed Signals]] (Chapter 11) — A failed signal at a sentiment extreme is especially significant; the market had every reason to continue but didn't
- [[Trends]] (Chapter 3) — The regime where contrary opinion persistence causes false signals
- [[Trading Ranges]] (Chapter 4) — The regime where mean-reversion (including sentiment mean-reversion) works better
- [[Risk Control and Win Rate vs Profitability]] (Chapter 7) — Premature exits from false contrary signals hurt the reward side of R:R

## Python Implementation

See `contrary_opinion.py` for:
- `detect_sentiment_extremes()` — Crossing detection for bullish/bearish extremes
- `assess_contrary_signals()` — Forward-looking quality check with persistence detection
- `simulate_sentiment()` — Generate realistic sentiment data from prices (for backtesting)
- `contrary_with_confirmation()` — Schwager's Ch. 14 approach: sentiment + RSI dual confirmation

### Sentiment + RSI Confirmation Pattern
```python
# Ch. 14 approach: require BOTH sentiment AND technical confirmation
from contrary_opinion import contrary_with_confirmation
from obos_exit_signals import calculate_rsi

rsi = calculate_rsi(prices)
confirmed = contrary_with_confirmation(
    prices, sentiment, rsi,
    bullish_threshold=75, bearish_threshold=25,
    rsi_confirm_ob=70, rsi_confirm_os=30
)
# Confirmed signals filter out persistence cases
```

## Key Takeaway

Contrary opinion is the most **theoretically elegant** exit concept in Chapter 10 — the supply/demand logic about remaining participants is genuinely insightful. But Schwager is careful to balance admiration with caution. The measurement problem (you can't directly observe positioning) and the persistence problem (extremes can sustain through trends) mean it's best used as **one voice in a chorus**, not a solo. Pair it with technical confirmation (Chapter 14's approach), combine with other exit methods, and treat extreme sentiment as a yellow light — slow down and look carefully — not a red light.
