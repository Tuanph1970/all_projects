---
title: "Confirmation Conditions for Bull-Bear Traps"
chapter: 11
concept: 4
tags:
  - failed-signals
  - confirmation
  - trade-entry
  - risk-management
  - schwager
  - chapter-11
aliases:
  - Confirmation Conditions
  - Initial Price Confirmation
  - Strong Price Confirmation
  - Time Confirmation
related:
  - "[[Failed Signals — The Overarching Principle]]"
  - "[[Bull Traps]]"
  - "[[Bear Traps]]"
  - "[[Ch7 — Confirmation Conditions]]"
  - "[[Ch9 — Choosing Stop-Loss Points]]"
  - "[[Ch10 — Setting Objectives]]"
  - "[[Ch7 — Risk Control and Win Rate vs Profitability]]"
---

# Confirmation Conditions for Bull/Bear Traps

## Definition

Confirmation conditions are the **rules that determine when a suspected bull or bear trap is officially "confirmed"** — meaning you have enough evidence to enter the trade. Schwager defines three conditions, each representing a different point on the certainty-vs-entry-quality spectrum.

The central question: *"How much of a pullback is required to indicate that a bull or bear trap has occurred?"*

---

## Simple Analogy: The Three Alarm Levels

Imagine a fire alarm system with three levels:

- **Smoke detector** (Initial Price): Triggers early at the first whiff. You get out fast, but sometimes it's just burnt toast — false alarm
- **Heat sensor** (Strong Price): Only triggers when the temperature actually rises dangerously. Very reliable, but by the time it goes off, the fire has spread further
- **Timer alarm** (Time): If the smoke hasn't cleared after 10 minutes, assume the worst. Independent of how much smoke or heat — it's purely about elapsed time

Each alarm tells you the same thing ("there's a fire") but at different confidence levels. You can also combine them: "if ANY two alarms fire, evacuate" is a reasonable multi-factor rule.

---

## The Three Confirmation Conditions

### 1. Initial Price Confirmation

| Attribute | Detail |
|---|---|
| **Trigger** | Price retraces to the **midpoint** of the consolidation |
| **Reliability** | Moderate — some will whipsaw back |
| **Entry quality** | Best of the three — closest to the breakout |
| **Speed** | Fast — usually fires within a few bars |
| **Best for** | Aggressive traders; wide ranges where midpoint is already a significant retrace |

### 2. Strong Price Confirmation

| Attribute | Detail |
|---|---|
| **Trigger** | Price retraces to the **opposite boundary** (support for bull trap, resistance for bear trap) |
| **Reliability** | Highest — the entire breakout has been erased |
| **Entry quality** | Worst — large distance from entry to stop (breakout extreme) |
| **Speed** | Moderate — requires a full retrace through the range |
| **Best for** | Conservative traders; narrow ranges where stop distance stays manageable |

### 3. Time Confirmation

| Attribute | Detail |
|---|---|
| **Trigger** | Price fails to return to the breakout extreme within ~4 weeks |
| **Reliability** | Good — exhaustion is a genuine signal |
| **Entry quality** | Variable — depends on where price is when time expires |
| **Speed** | Slowest — must wait the full time window |
| **Best for** | Combining with price confirmations; situations where price drifts sideways without triggering either price level |

---

## The Core Trade-Off

> *"The trade-off between initial and strong price confirmations is that the former will provide better entry levels in trading bull and bear traps, whereas the latter will provide more reliable signals."*
> — Schwager, Ch. 11

This is the fundamental tension in ALL confirmation systems (see also [[Ch7 — Confirmation Conditions]]): **certainty costs money**. Every moment you wait for more evidence, price moves further from the optimal entry.

```
Less restrictive ←──────────────────→ More restrictive
Better entry price                    Better signal quality
More false positives                  More missed opportunities
Initial Price ────── Time ────── Strong Price
```

There is no "correct" choice — it depends on:
- Your risk tolerance (how many whipsaws can you absorb?)
- The range width (narrow range → strong confirmation has manageable risk)
- Whether other confirming factors exist (volume, multi-timeframe alignment)

---

## Sequence Is Not Fixed

A critical insight from Schwager's examples:

> *"The time confirmation can occur after both price confirmation conditions (as is the case in Figure 11.4), before both price confirmation conditions (as is the case in Figure 11.5), or at any point between."*

This means the three confirmations are **independent dimensions**, not a fixed progression. In the T-bond example, both price confirmations fired before time. In the silver example, time confirmation came first. Design your system to track all three simultaneously.

---

## Invalidation Rules

### Primary Invalidation
- **Bull trap**: Price returns to the breakout high → trap is invalidated, exit short
- **Bear trap**: Price returns to the breakout low → trap is invalidated, exit long

### Sensitive Invalidation (after strong confirmation)
- **Bull trap**: After price broke below support (strong confirmation), if it returns to the **top** of the consolidation → invalidated
- **Bear trap**: After price broke above resistance (strong confirmation), if it returns to the **bottom** of the consolidation → invalidated

> *"More sensitive conditions could be used to invalidate bull or bear trap signals once the market has moved sufficiently in the direction of the signal."*
> — Schwager, Ch. 11

### After Confirmation (no invalidation)
If invalidation does not occur, hold the trade until:
- A price objective is met ([[Ch10 — Setting Objectives]])
- An opposite-direction trend reversal occurs
- Any other trade liquidation condition is triggered

---

## Multi-Factor Scoring

A practical approach not explicitly in Schwager but consistent with his framework:

| Confirmations Fired | Confidence | Action |
|---|---|---|
| 0 of 3 | None | No trade — still pending |
| 1 of 3 | Moderate | Enter with reduced position |
| 2 of 3 | High | Enter with full position |
| 3 of 3 | Very high | Full position + consider pyramiding |

Weight the confirmations: strong price (45%) > time (30%) > initial price (25%), reflecting Schwager's emphasis on strong price as "more reliable."

---

## Connection to Chapter 7 Confirmation Conditions

In [[Ch7 — Confirmation Conditions]], Schwager introduces the same trade-off concept in a broader context: time delays, minimum percent penetration, and thrust days as general confirmation tools. Chapter 11's three confirmation types are a **specific application** of that general framework to the failed-signal context.

The key principle is identical: *"The less restrictive the conditions, the greater the number of false signals; the more restrictive the conditions, the greater the surrendered profit potential due to late entry."*

---

## When This Concept Works Best

- **Any time you've identified a potential bull or bear trap** — the confirmations answer "when do I actually pull the trigger?"
- **In volatile markets** where breakouts and reversals happen quickly — confirmations prevent premature entry on noise
- **When building systematic rules** — these three conditions translate directly into code (see Python implementation)

---

## When to Be Cautious

- **Don't wait for strong confirmation in fast-moving markets** — by the time price reaches the opposite boundary in a crash, you've missed most of the move
- **Time confirmation alone can be misleading** — price drifting sideways for 4 weeks might just be a low-volatility consolidation, not a failed signal
- **Combining all three doesn't guarantee success** — even 3/3 confirmed traps can reverse (a "failed failed signal")

---

## Cross-Chapter Links

- **[[Failed Signals — The Overarching Principle]]**: Confirmations validate the parent concept
- **[[Bull Traps]]** / **[[Bear Traps]]**: The specific patterns these confirmations apply to
- **[[Ch7 — Confirmation Conditions]]**: The general theory that Chapter 11 specializes
- **[[Ch7 — Risk Control and Win Rate vs Profitability]]**: Confirmation trade-offs affect win rate vs. reward-to-risk ratio (stricter = higher win rate but worse R:R)
- **[[Ch9 — Choosing Stop-Loss Points]]**: Breakout extreme as the natural stop level
- **[[Ch10 — Setting Objectives]]**: What happens AFTER confirmation — exit criteria

---

## Python Implementation

See `confirmation_conditions.py`:
- `evaluate_confirmations()` — tracks all three conditions simultaneously, checks invalidation first
- `ConfirmationState` dataclass with `.count`, `.confidence_score`, and `.first_confirmation_date`
- `derive_trade_params()` — converts confirmation into entry/stop/target with reward-to-risk
- `compare_confirmations()` — side-by-side comparison of all fired confirmations for decision support

---

## Key Takeaway

Confirmation conditions are the **bridge between observation and action**. Seeing a potential bull or bear trap is step one. The confirmation rules tell you *when* and *at what price* to act — and every choice on that spectrum trades entry quality for signal reliability. There is no free lunch; the best you can do is pick the trade-off that matches your risk profile and apply it consistently.
