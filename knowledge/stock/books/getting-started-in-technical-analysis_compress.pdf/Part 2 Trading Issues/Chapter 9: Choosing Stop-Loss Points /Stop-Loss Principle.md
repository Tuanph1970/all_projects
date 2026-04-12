---
title: "Stop-Loss Principle"
chapter: 9
concept_number: 1
tags:
  - technical-analysis
  - risk-management
  - stop-loss
  - schwager
  - chapter-9
related:
  - "[[Risk Control and Win Rate vs Profitability]]"
  - "[[Trading Range Stops]]"
  - "[[Trend Line Stops]]"
  - "[[Flag and Pennant Stops]]"
  - "[[Wide-Ranging Day Stops]]"
  - "[[Relative High Low Stops]]"
  - "[[Money Stops]]"
  - "[[Trailing Stops]]"
  - "[[CIC Anti-Pattern]]"
  - "[[Confirmation Conditions]]"
created: 2026-04-08
---

# Stop-Loss Principle

## Definition

The foundational rule governing all stop-loss placement: **define the exit before the entry, place it where the technical picture would change, and never widen it.**

Schwager's three rules:

1. **Pre-determine before entry** — A precise stop-loss point should be determined before initiating a trade. The most disciplined approach is placing a GTC (good-till-canceled) stop order simultaneously with the trade.
2. **Liquidate at technical invalidation** — The position should be liquidated at or before the point at which price movement causes a transition in the technical picture.
3. **Stops only reduce risk** — Stops should only be changed in order to reduce risk. Revising the stop to allow greater risk defeats the entire purpose.

## Key Quotes (Schwager)

> "The success of chart-oriented trading is critically dependent on the effective control of losses."

> "A precise stop-loss liquidation point should be determined before initiating a trade."

> "The position should be liquidated at or before the point at which price movement causes a transition in the technical picture."

> "Stops should only be changed in order to reduce risk. Revising the stop to allow greater risk defeats the entire purpose of the stop."

## Analogy: Circuit Breaker Pattern

Maps directly to the **circuit breaker pattern** in distributed systems:

| Trading | Software |
|---------|----------|
| Define stop before entry | Configure failure threshold before deploy |
| Exit where technical picture changes | Trip circuit on genuine dependency failure |
| Never widen stop under pressure | Never raise threshold during an incident |
| Without: account ruin | Without: cascading failure |

**Core insight in both domains:** exit conditions are design-time decisions, not runtime decisions made under stress.

## When It Works Best

- **Every trade** — this is not situational; it is the universal foundation
- Especially critical in volatile markets where "holding for recovery" can mean catastrophic loss
- Most valuable psychologically: pre-commitment removes the need for real-time emotional decision-making

## Technical Reference Points for Stops

Schwager lists five chart-based locations (each is a separate concept in this chapter):

1. **[[Trend Line Stops]]** — earliest signal, most false positives
2. **[[Trading Range Stops]]** — opposite side or midpoint of the range
3. **[[Flag and Pennant Stops]]** — opposite end after breakout
4. **[[Wide-Ranging Day Stops]]** — return past opposite end
5. **[[Relative High Low Stops]]** — most recent swing high/low

When these imply excessive risk → use a **[[Money Stops|money stop]]** (fixed dollar risk, no technical basis).

As the trade moves in your favor → use a **[[Trailing Stops|trailing stop]]** to protect profits.

## Cross-References

- **[[Risk Control and Win Rate vs Profitability]]** (Ch. 7) — The *why* behind stops: you don't need >50% win rate if losses are controlled
- **[[Confirmation Conditions]]** (Ch. 7) — Filters that reduce false breakouts, affecting where entry occurs relative to the stop
- **[[Failed Signals]]** (Ch. 7) — A failed breakout may itself be a high-reliability signal in the opposite direction, requiring a stop on the original position
- **[[CIC Anti-Pattern]]** (Ch. 9) — The specific failure mode of violating Rule 3

## Python Implementation

See `stop_loss_principle.py`:

- `StopLossOrder` — dataclass enforcing the three rules (pre-defined stop, risk calculation, `tighten()` method that rejects CIC behavior)
- `validate_stop_placement()` — checks if a proposed stop is at a technically meaningful level
- `backtest_stop_discipline()` — statistical comparison of disciplined vs. "hope and hold"

**Backtest result (1,000 trials, 5% stop, bearish drift):**

| Metric | Disciplined | Hope & Hold |
|--------|------------|-------------|
| Mean P&L | -3.3% | -8.9% |
| Worst case | -10.7% | -78.8% |

The worst-case compression is the point: discipline turns a potential -79% disaster into a -11% manageable loss.

## Summary

The stop-loss principle is not a technique — it is the **precondition** for all other techniques in this chapter to work. Every chart-based stop, money stop, and trailing stop is an implementation of these three rules. Without them, no amount of pattern recognition or confirmation filtering produces a viable trading approach.
