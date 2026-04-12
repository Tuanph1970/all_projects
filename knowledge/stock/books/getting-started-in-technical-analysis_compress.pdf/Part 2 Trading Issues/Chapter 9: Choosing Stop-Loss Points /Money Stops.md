---
title: "Money Stops"
chapter: 9
concept_number: 7
tags:
  - technical-analysis
  - stop-loss
  - money-stop
  - risk-management
  - schwager
  - chapter-9
related:
  - "[[Stop-Loss Principle]]"
  - "[[Relative High Low Stops]]"
  - "[[Trailing Stops]]"
  - "[[Risk Control and Win Rate vs Profitability]]"
  - "[[Trading Range Stops]]"
  - "[[Flag and Pennant Stops]]"
  - "[[CIC Anti-Pattern]]"
created: 2026-04-09
---

# Money Stops

## Definition

A **fixed-dollar or fixed-percentage stop** with no technical significance, used as a fallback when the nearest chart-based stop implies excessive risk. The stop level is determined purely by the trader's desired maximum loss per trade, not by any chart pattern or technical reference point.

Schwager presents this as a **pragmatic concession**, not a preferred approach. It is the only stop type where the question shifts from "where is my thesis wrong?" to "how much can I afford to lose?"

## Key Quotes (Schwager)

> "Sometimes the risk implied by even the closest technically significant points may be excessive. In this case, the trader may decide to use a money stop — that is, a protective stop-loss point with no technical significance that is determined by the desired dollar risk level."

> "The closest meaningful stop point — the contract high (which is the nearest relative high) — would imply a risk of nearly $15,000 per contract!"

> "Risk can sometimes be reduced if the trader waits for a reaction before entering the market, such a retracement may not occur until the market moves substantially lower."

> "In a situation in which the nearest meaningful stop point implies a very large risk, a market order accompanied by a money stop may represent the most viable trading approach."

On trailing money stops:
> "This technique keeps risk at a known level and frees the trader from overly risky stop points based on chart patterns, but may also liquidate a trade when there is no technical reason for doing so."

## Analogy: Generic Timeout on Unknown API

Like calling a **brand-new third-party API** with no historical latency data:

| API call | Trade |
|----------|-------|
| Derive timeout from P99 latency percentiles | Derive stop from chart-based technical levels |
| No baseline data for this API | No chart reference close enough for acceptable risk |
| Set generic 5-second timeout | Set money stop at fixed % risk |
| May timeout during slow-but-valid response | May exit when trade would have recovered |
| Thread never hangs indefinitely | Loss never reaches catastrophic levels |

**Bounded risk with no informational basis is strictly better than unbounded risk.**

## The Three Options When Chart Risk Is Excessive

Schwager implies three choices:

| Option | Advantage | Disadvantage |
|--------|-----------|--------------|
| **A: Money stop** | Participate now with bounded risk | Stop has no technical meaning |
| **B: Wait for retracement** | Better entry price, tighter stop | Retracement may never come — miss the move |
| **C: Skip the trade** | No risk at all | Opportunity cost if thesis was correct |

## The Tradeoff (Backtest: 500 trials)

| Metric | Chart stop (15%) | Money stop (5%) |
|--------|-----------------|-----------------|
| Avg P&L | +1.4% | **+1.8%** |
| Worst case | -19.3% | **-10.8%** |
| False stop rate | **5.0%** | 40.1% |
| Times stopped | 199/500 | 349/500 |

Key insights:
- Money stop compresses worst-case by ~8-9 percentage points
- The cost is ~35% more false exits
- Money stop actually has higher avg P&L here because it prevents the deep losses from dragging down the average

## Position in the Chapter Hierarchy

Three different questions, three different stop roles:

1. **Chart-based stops** (Concepts 2-6): "Where does my thesis become wrong?"
2. **Money stops** (Concept 7): "How much can I afford to lose?"
3. **Trailing stops** (Concept 8): "How do I keep what I've gained?"

Money stops are the **only type where question 1 has no answer** but question 2 still provides protection.

## Transition Pattern: Money Stop → Chart-Based Stop

Money stops should be **temporary** whenever possible. As the trade develops, new chart structures form and provide technical references:

1. Enter trade with money stop (no chart reference close enough)
2. Trade moves in favor, pullback forms a [[Relative High Low Stops|relative low]]
3. Replace money stop with chart-based stop at the new relative low
4. Continue with [[Trailing Stops|trailing stop]] keyed to successive relative lows

This progression is the ideal path — the money stop is a placeholder, not a permanent solution.

## When It Works Best

- When the nearest chart stop implies **catastrophic risk** (Schwager's lumber: $15,000/contract)
- **New positions** in fast-moving markets where chart structures haven't formed yet
- As a **temporary stop** until chart-based references develop through natural price action
- When combined with aggressive **position sizing** — if your money stop is 5% but you size the position so that 5% = 1% of account, the arbitrary stop level matters less
- When the trader has **high conviction** in direction but no nearby chart level to anchor the stop

## When It Fails

- In all cases where a chart-based stop is available at acceptable risk — Schwager clearly prefers technical stops
- **Tight money stops in volatile markets** produce excessive whipsaws (40%+ false stop rate)
- When the money stop level happens to sit at a technically meaningless price that gets swept by normal noise
- Schwager's own words: *"may also liquidate a trade when there is no technical reason for doing so"*

## Cross-References

- **[[Stop-Loss Principle]]** (Ch. 9, Concept 1) — Money stops satisfy Rule 1 (pre-determine) and Rule 3 (only tighten), but sacrifice Rule 2 (exit at technical invalidation)
- **[[Relative High Low Stops]]** (Ch. 9, Concept 6) — The trigger for switching to money stops: when the nearest swing point implies excessive risk
- **[[Trailing Stops]]** (Ch. 9, Concept 8) — A trailing money stop (fixed %) has the same limitation: known risk, no technical basis. Chart-based trailing is preferred.
- **[[Trading Range Stops]]** (Ch. 9, Concept 3) — Wide ranges can push the chart stop too far, triggering the money stop fallback
- **[[Flag and Pennant Stops]]** (Ch. 9, Concept 4) — Flag entries often avoid the money stop problem because their narrowness keeps chart-based risk small
- **[[Risk Control and Win Rate vs Profitability]]** (Ch. 7) — Money stops enforce the expected value framework by capping the loss side of the equation
- **[[CIC Anti-Pattern]]** (Ch. 9, Concept 9) — Even a money stop is infinitely better than a canceled stop

## Python Implementation

See `money_stops.py`:

- `MoneyStop` — dataclass computing stop price from a fixed risk budget
- `should_use_money_stop()` — decision function: compares chart-based risk to max acceptable risk, returns a recommendation
- `compare_money_vs_chart_stop()` — backtests both approaches side by side across 500 scenarios

## Summary

Money stops are the **escape valve** in Schwager's stop hierarchy — used only when the chart gives no acceptable reference point. They answer a different question than chart-based stops: not "where is my thesis wrong?" but "how much can I afford to lose?" The tradeoff is explicit: bounded risk at the cost of no technical grounding and a ~40% false stop rate. Ideally, money stops are temporary — as the trade develops, new chart structures provide technical references to replace the arbitrary level. But even an arbitrary stop is infinitely better than no stop ([[CIC Anti-Pattern|CIC]]).
