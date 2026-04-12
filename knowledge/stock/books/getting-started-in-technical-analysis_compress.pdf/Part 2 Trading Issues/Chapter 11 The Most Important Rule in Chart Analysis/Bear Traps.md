---
title: "Bear Traps"
chapter: 11
concept: 3
tags:
  - failed-signals
  - bear-trap
  - reversal
  - breakout-failure
  - major-bottoms
  - schwager
  - chapter-11
aliases:
  - Bear Trap
  - False Downside Breakout
related:
  - "[[Failed Signals — The Overarching Principle]]"
  - "[[Bull Traps]]"
  - "[[Confirmation Conditions for Bull-Bear Traps]]"
  - "[[False Trend Line Breakouts]]"
  - "[[Ch4 — Trading Ranges and Support and Resistance]]"
  - "[[Ch5 — Chart Patterns]]"
  - "[[Ch9 — Choosing Stop-Loss Points]]"
---

# Bear Traps

## Definition

A **bear trap** is a major downside breakout from a consolidation range that is soon followed by an abrupt reversal upward. It is the exact mirror image of a [[Bull Traps|bull trap]]. The breakout looks like a legitimate sell signal but turns out to be false — trapping short sellers.

> *"In the case of a bear trap the market falls just enough to trigger resting stops below the low end of a trading range, but fails to uncover any additional selling pressure after the breakout — an indication of substantial underlying strength."*
> — Schwager, Ch. 11

---

## Simple Analogy: The Trapdoor Floor

Imagine people standing on a floor (the support level). A section of the floor suddenly drops open — a trapdoor. Everyone panics and jumps down, thinking the whole floor is collapsing. But there's a trampoline right underneath. The few who jumped through the trapdoor immediately bounce back up, higher than before. Meanwhile, those who sold in panic are now watching from below as prices fly past them.

The trapdoor opening was the **breakout below support**. The trampoline is the **underlying strength** that the breakout failed to overcome. The bounce is the **bear trap reversal**.

---

## The Mechanism (Mirror of Bull Trap)

| Step | Bull Trap | Bear Trap |
|---|---|---|
| 1 | Buy stops above resistance | Sell stops below support |
| 2 | Upside breakout triggers stops | Downside breakout triggers stops |
| 3 | No genuine buying after stops swept | No genuine selling after stops swept |
| 4 | Reversal DOWN — sell signal | Reversal UP — buy signal |
| 5 | Marks major TOPS | Marks major BOTTOMS |

The key asymmetry: bear traps often mark the end of extended downtrends, where exhaustive selling has dried up all genuine supply. The breakout below support is the "last gasp" of selling pressure.

---

## Confirmation Conditions

Same three levels as bull traps, mirrored (see also [[Confirmation Conditions for Bull-Bear Traps]]):

### 1. Initial Price Confirmation
- **Trigger**: Price rebounds to the **midpoint** of the prior consolidation
- **Trade**: BUY here, stop at breakout low
- **Trade-off**: Better entry price (buy lower), less certainty

### 2. Strong Price Confirmation
- **Trigger**: Price rebounds to the **opposite boundary** (resistance / range high)
- **Trade**: BUY here, stop at breakout low
- **Trade-off**: More reliable signal, worse entry (buy higher)

### 3. Time Confirmation
- **Trigger**: Price fails to return to the breakout low within ~4 weeks
- **Usage**: Standalone or combined with either price confirmation
- **Key note**: In Schwager's silver example, time confirmation came **before** both price confirmations — the order varies

---

## Invalidation

A bear trap signal is **invalidated** if price returns to the breakout low. At that point, the downside breakout may be genuine — exit the long position at the stop.

More sensitive invalidation: after strong price confirmation, if price falls back below support (range low), the bear trap interpretation is abandoned.

---

## Trading the Bear Trap

| Element | Rule |
|---|---|
| **Direction** | LONG (buy) |
| **Entry** | At confirmation level (midpoint or resistance) |
| **Stop loss** | At or slightly below the breakout low |
| **Target** | Hold until price objective, trend reversal evidence, or exit criteria from [[Ch10 — Setting Objectives]] |
| **Key discipline** | If you were short and got trapped, the skilled response is to reverse to long — Schwager's "180-degree turn" |

---

## When This Concept Works Best

- **At the end of extended downtrends**: Schwager's silver example was a six-year downtrend. The longer the prior decline, the more significant the bear trap
- **When the breakdown is sharp but brief**: A two-day plunge that immediately stalls = classic bear trap velocity
- **Multiple range violations**: The silver example broke below both a narrow 3-month range AND a broader 6-month range simultaneously — and still failed
- **"Holding in midair"**: Schwager's specific phrase — when prices don't even try to continue lower after the breakdown, they just hang sideways. This stall is the telltale sign

---

## When to Be Cautious

- **Genuine breakdowns** in strong downtrends with sustained volume may not be traps
- **Shallow breakouts**: A minor dip below support is less significant than a dramatic plunge
- **Failed bear traps exist**: The reversal can itself fail — always maintain stop at breakout low
- **Don't front-run**: Wait for confirmation; buying during the breakdown hoping for a bear trap is riskier

---

## Schwager's Key Example

**July 1993 Silver** (Figure 11.3): Culmination of a six-year downtrend. In February 1993, a sharp two-day plunge below both a narrow three-month trading range and a broader six-month trading range. Instead of continuing lower, prices held in midair, moved sideways, then eventually rebounded back into the range. This bear trap preceded a dramatic rally.

Notable: Time confirmation came **before** both price confirmations in this case — illustrating that the three confirmation types have no fixed order.

---

## Bull Trap vs. Bear Trap — Side by Side

| Attribute | Bull Trap | Bear Trap |
|---|---|---|
| Breakout direction | Upside (above resistance) | Downside (below support) |
| Stops triggered | Buy stops above range | Sell stops below range |
| Failure indication | Weak underlying picture | Strong underlying picture |
| Trading direction | SHORT | LONG |
| Typically marks | Major tops | Major bottoms |
| Initial confirmation | Retrace to midpoint (sell) | Rebound to midpoint (buy) |
| Strong confirmation | Retrace to support (sell) | Rebound to resistance (buy) |
| Invalidation | Return to breakout high | Return to breakout low |

---

## Cross-Chapter Links

- **[[Failed Signals — The Overarching Principle]]**: Bear traps are one of the most common applications
- **[[Bull Traps]]**: Exact mirror image — same framework, opposite direction
- **[[Confirmation Conditions for Bull-Bear Traps]]**: Shared confirmation/invalidation framework
- **[[Ch4 — Trading Ranges and Support and Resistance]]**: Support levels are where bear traps form
- **[[Ch5 — Chart Patterns]]**: Breakout patterns provide the raw material
- **[[Ch3 — Trends]]**: Bear traps often mark the end of extended downtrends

---

## Python Implementation

See `bear_trap_detector.py` — mirrors `bull_trap_detector.py`:
- `detect_bear_trap()` — scans for consolidation → downside breakout → failure
- Returns a `BearTrap` dataclass with all three confirmation flags
- `bear_trap_reward_risk()` — calculates reward-to-risk for the long trade
- Invalidation: price falling below breakout low

---

## Key Takeaway

Bear traps are the mirror of bull traps, but with one psychological asymmetry: **fear is stronger than greed.** Downside breakouts tend to be sharper and more panic-driven than upside breakouts, which means bear traps can spring more violently. The silver example — a six-year downtrend ending in a two-day plunge that immediately stalled and reversed — is the archetype. The key skill is the same: recognizing the failure and having the discipline to trade in the opposite direction.
