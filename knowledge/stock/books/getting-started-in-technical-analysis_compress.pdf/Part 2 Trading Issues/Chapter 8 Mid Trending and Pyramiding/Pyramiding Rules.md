---
title: "Pyramiding Rules"
aliases:
  - pyramiding
  - adding to winners
  - scaling into positions
  - pyramid position sizing
chapter: 8
concept: 6
tags:
  - technical-analysis
  - schwager
  - position-management
  - risk-control
  - pyramiding
related:
  - "[[The Midtrend Entry Problem]]"
  - "[[Percent Retracement Entry]]"
  - "[[Reversal of Minor Reaction]]"
  - "[[Continuation Pattern Breakouts]]"
  - "[[Reaction to Long-Term Moving Average]]"
  - "[[Risk Control and Win Rate vs Profitability]]"
created: 2026-04-07
---

# Pyramiding Rules

## Core idea

Pyramiding is the process of **adding new positions to an existing winning trade** as the market continues in your favor. Schwager frames it as **the same problem** as midtrend entry — both involve entering after a substantial prior move — but with three additional safety rules.

> "The problem of midtrend entry is identical to the problem of pyramiding, the process of adding new positions to an existing open trade (i.e., initially buying a stock at $30 and then purchasing additional lots at $35, $45, and so on, as the market continues to rise)."

## Schwager's three rules

### Rule 1: Last unit must show a profit

> "One should not add to any existing position unless the last unit placed shows a profit."

Don't add to a position where your most recent entry is underwater. If you bought at $45 and price is now $43, don't add — the market is telling you the timing on that last entry was wrong.

**Why it matters**: If your latest unit is losing, the trend may be weakening or your entry timing was poor. Adding more exposure amplifies the problem.

### Rule 2: Stop must not imply a net loss

> "One should not add to an existing position if the intended stop point would imply a net loss for the entire position."

Before each addition, calculate: "If I get stopped out at my stop price, does the total position (all units combined) still break even or better?"

**Why it matters**: As you add units at higher prices, your average cost rises. A stop that was comfortable for the base position may produce a net loss once you've added expensive units on top. This rule forces you to either:
- Raise the stop (tighter risk)
- Add fewer shares
- Skip the addition entirely

This is the **most quantitatively important** rule — it directly constrains position sizing.

### Rule 3: Pyramid units must be no larger than base position

> "Pyramid units should be no greater than the base (initial) position size."

The position shape must **taper**: largest at the bottom (cheapest price), progressively smaller or equal as you add higher. Never invert the pyramid.

**Why it matters**: If you add more shares at higher prices than at lower prices, your average cost rises dangerously fast. A small pullback can wipe out all gains. The tapering shape ensures the bulk of your exposure is at the most favorable prices.

## Schwager's example

| Unit | Price | Shares | Cost |
|---|---|---|---|
| Base | $30 | 100 | $3,000 |
| P1 | $35 | 80 | $2,800 |
| P2 | $45 | 60 | $2,700 |
| **Total** | **Avg $35.42** | **240** | **$8,500** |

At current price $50: P/L = +$3,500
At stop $32: P/L = -$820 — **Rule 2 FAILS**

This means the stop must be raised above $35.42 (the avg cost) for the pyramid to be safe.

## Connection to midtrend strategies

All four midtrend entry strategies apply to pyramid timing:

| Strategy | Pyramid application |
|---|---|
| [[Percent Retracement Entry]] | Add on pullbacks of 35-65% of the last swing |
| [[Reversal of Minor Reaction]] | Add when N-day counter-move reverses |
| [[Continuation Pattern Breakouts]] | Add on breakouts from consolidations within the trend |
| [[Reaction to Long-Term Moving Average]] | Add when price returns to the MA |

The only difference: pyramid additions must also pass the three rules above.

## Software analogy

Pyramiding is like **autoscaling a cloud deployment**:

| Cloud autoscaling | Pyramiding |
|---|---|
| Base deployment handles initial load | Base position at initial entry |
| Scale up as traffic grows | Add units as price moves favorably |
| Only add if last batch handles load OK | Rule 1: last unit profitable |
| Never scale to where a drop causes net cost > revenue | Rule 2: stop doesn't imply net loss |
| Each new batch is equal or smaller than original | Rule 3: units must be no larger than base |
| A rollback with inverted scaling is catastrophic | An inverted pyramid amplifies losses |

## The inverted pyramid anti-pattern

What happens if you violate Rule 3 (add larger units at higher prices):

| Unit | Price | Shares |
|---|---|---|
| Base | $30 | 50 |
| P1 | $40 | 100 |
| P2 | $50 | 150 |

Average cost = $43.33 on 300 shares. A pullback to $42 (only -16% from $50) produces a loss of -$400. The bulk of the position is at the worst prices. This is why the taper rule exists.

## When pyramiding works best

- **Strong, sustained trends** with multiple identifiable pullback opportunities
- When the trend has been validated by [[Multi-Timeframe Analysis]] (higher timeframe bullish)
- When each addition has a **clear stop level** that satisfies Rule 2
- When you have the discipline to **check all three rules before every addition**

## When NOT to pyramid

- **Late-stage trends** where the move is already extended
- When you **cannot define a stop** that satisfies Rule 2
- In **volatile, choppy markets** where stops get hit frequently
- When the last unit is underwater (**Rule 1 violation** — the trend may be turning)

## Cross-references

### Within Chapter 8
- [[The Midtrend Entry Problem]] — Same problem, different context
- [[Percent Retracement Entry]] — Use for pyramid timing
- [[Reversal of Minor Reaction]] — Use for pyramid timing
- [[Continuation Pattern Breakouts]] — Use for pyramid timing
- [[Reaction to Long-Term Moving Average]] — Use for pyramid timing

### Other chapters
- [[Risk Control and Win Rate vs Profitability]] (Ch. 7) — Pyramiding increases position size, so risk per trade must be managed carefully
- [[Confirmation Conditions]] (Ch. 7) — Each pyramid addition should have confirmation that the trend is intact
- Choosing Stop-Loss Points (Ch. 9) — Directly governs Rule 2 compliance
- Setting Objectives and Exit Criteria (Ch. 10) — When to stop adding and start taking profits

## Python implementation

See `pyramiding_rules.py`:
- `PyramidPosition` class — manages units, checks all three rules, computes P/L
- `can_add_unit()` — pre-flight check before adding a pyramid unit
- `add_unit()` — adds a unit if rules pass (or force-adds for testing)
- `summary()` — full position report with per-unit P/L and rule status
- `build_example_pyramid()` — Schwager's $30/$35/$45 example

## Key takeaway

> Pyramiding lets you **maximize exposure to winning trades** — but only if you follow three rules that prevent the additions from turning a winner into a loser. The most critical rule is Rule 2: **never add if the stop implies a net loss**. This single check prevents the most common pyramid disaster: a profitable trade that reverses and produces a larger loss than the original position would have.
