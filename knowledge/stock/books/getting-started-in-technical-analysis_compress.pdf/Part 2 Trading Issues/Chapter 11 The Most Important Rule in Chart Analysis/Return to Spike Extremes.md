---
title: "Return to Spike Extremes"
chapter: 11
concept: 7
tags:
  - failed-signals
  - spikes
  - penetration
  - reversal
  - schwager
  - chapter-11
aliases:
  - Spike Penetration
  - Return to Spike High
  - Return to Spike Low
related:
  - "[[Failed Signals — The Overarching Principle]]"
  - "[[Return to Wide-Ranging Day Extremes]]"
  - "[[Filled Gaps as Failed Signals]]"
  - "[[Ch5 — Chart Patterns]]"
  - "[[Ch9 — Choosing Stop-Loss Points]]"
---

# Return to Spike Extremes

## Definition

A **spike** (a day whose high or low sharply exceeds its neighbors) frequently marks an important price reversal. When price later **returns to and penetrates** that spike extreme, the original spike is transformed into a failed signal — implying a substantial further move in the direction of the penetration.

> *"The return of prices to a prior spike extreme can be viewed as transforming the original spike into a failed signal. The more extreme the spike, the greater the significance of its penetration."*
> — Schwager, Ch. 11

---

## Simple Analogy: The High-Jump Record

Imagine a high jumper sets a record (the spike) — everyone says "that bar will never be cleared again." Months later, another jumper clears it. The psychological effect is enormous: the old "impossible" barrier is now broken, and multiple jumpers rush to clear it too.

A price spike works the same way. It sets a psychological ceiling (or floor) that the market "agrees" is the limit. When that limit is later broken, the breakthrough releases pent-up energy as all the participants who respected that level now must reposition.

The longer the record stood (more time elapsed), and the more dramatic it was (higher magnitude), the more explosive the breakthrough.

---

## The Mechanism

### Spike High Penetration → BUY

1. A spike high forms during an advance — a single day with a high sharply above neighboring days
2. Price reverses and trades lower, "confirming" the spike as a top
3. Weeks or months later, price rallies back and **closes above** the spike high
4. The "proven ceiling" is broken → expect **substantial further advance**

### Spike Low Penetration → SELL

1. A spike low forms during a decline — a single day with a low sharply below neighboring days
2. Price reverses and trades higher, "confirming" the spike as a bottom
3. Weeks or months later, price declines and **closes below** the spike low
4. The "proven floor" is broken → expect **substantial further decline**

---

## Two Significance Factors

| Factor | Description | Impact |
|---|---|---|
| **Spike magnitude** | How far the spike protrudes beyond neighboring bars' highs/lows | Greater protrusion = more significant when penetrated |
| **Time elapsed** | Duration between spike formation and penetration | Several weeks minimum; several months preferred. Longer = stronger signal |

Both factors compound: a huge spike penetrated after months is the most powerful version of this signal.

---

## Negation Rule: The "Failed Failed Signal"

Schwager explicitly addresses what happens when a spike penetration itself fails — his cocoa example (Figure 11.15):

> *"A close beyond the opposite extreme of the spike can be viewed as negating the failed signal."*

| Scenario | Negation Condition |
|---|---|
| Spike high penetrated (long trade) | Close below the **low** of the spike day |
| Spike low penetrated (short trade) | Close above the **high** of the spike day |

In the cocoa example, the October spike low was penetrated (bearish signal), but the market closed above the **high** of the spike low day just four days later — negating the signal. This is a "failed failed signal" — one of the few places Schwager explicitly addresses recursive failure.

---

## Trading Rules

| Element | Spike High Penetrated | Spike Low Penetrated |
|---|---|---|
| **Direction** | LONG (buy) | SHORT (sell) |
| **Entry** | Close above spike high | Close below spike low |
| **Stop / Negation** | Close below spike day's low | Close above spike day's high |
| **Minimum time** | Several weeks after spike | Several weeks after spike |
| **Hold** | Until price objective or reversal | Until price objective or reversal |

---

## When This Concept Works Best

- **Spikes that were widely recognized as major turning points**: The more "proven" a spike top/bottom is, the more significant its eventual penetration
- **After several months**: Schwager's soybean oil example (Fig 11.13) — four months elapsed between the July spike high and its penetration. That duration gave the market plenty of time to "agree" the spike was the top
- **Combined with volume expansion**: A spike penetration on increasing volume confirms genuine participation rather than a stop-driven fluke
- **When the spike was an isolated event**: A single sharp spike stands out more than gradual highs/lows — making its penetration more meaningful

---

## When to Be Cautious

- **Spikes penetrated too quickly**: If price returns to the spike extreme within just a few days, the spike was never established as a meaningful level. Schwager says "at least several weeks"
- **Marginal penetrations**: A close barely beyond the spike by a tiny amount may be noise rather than signal. Look for a decisive close
- **The cocoa warning — recursive failure**: Spike penetrations can themselves fail. Always monitor the negation level (opposite extreme of the spike day) and respect the stop
- **Multiple spike clusters**: If several spikes cluster at similar levels, the "spike level" becomes more of a range boundary than a single-day event — more suited to [[Bull Traps|bull/bear trap]] analysis

---

## Schwager's Key Examples

### March 1994 Soybean Oil (Figure 11.13)
Return to the July spike high **four months later** led to a substantial extension on the upside. Classic example of time-enhanced significance.

### March 1992 Cotton (Figure 11.14)
Penetration of a downside spike — prices slid sharply following the event. Demonstrates the sell-signal version.

### March 1994 Cocoa (Figure 11.15)
Two events on one chart: the July spike high was penetrated (bullish, worked). But the October spike low penetration proved misleading — a "failed failed signal." The market closed above the opposite extreme of the spike low day just four days after the penetration, negating the bearish signal.

---

## Relationship to Other Day-Level Failed Signals

| Concept | Original Signal | Failed Signal Trigger |
|---|---|---|
| **Spike Penetration** (this concept) | Spike marks a reversal | Price closes beyond spike extreme |
| [[Return to Wide-Ranging Day Extremes]] | WRD implies continuation | Price closes beyond WRD opposite extreme |
| [[Filled Gaps as Failed Signals]] | Gap implies continuation | Gap is filled (price retraces through it) |

All three are "day-level" failed signals — single-day patterns that get negated by subsequent price action. They differ in what the original single-day event looks like, but share the same logic: when a dramatic single-day claim is later contradicted, the contradiction is more informative than the original claim.

---

## Cross-Chapter Links

- **[[Failed Signals — The Overarching Principle]]**: Spike penetration is a specific application
- **[[Ch5 — Chart Patterns]]**: Defines spikes and their significance factors (wide difference between spike and neighbors, close near opposite end, occurring after a trend)
- **[[Return to Wide-Ranging Day Extremes]]**: Sister concept — same logic applied to wide-ranging days instead of spikes
- **[[Filled Gaps as Failed Signals]]**: Another day-level failed signal; gaps and spikes often coincide
- **[[Ch9 — Choosing Stop-Loss Points]]**: The opposite extreme of the spike day serves as the natural stop

---

## Python Implementation

See `spike_penetration_detector.py`:
- `detect_spikes()` — finds spike highs and lows with configurable protrusion threshold and neighbor window
- `detect_spike_penetration()` — monitors for price closing beyond spike extreme after minimum elapsed bars
- `check_penetration_negated()` — implements Schwager's negation rule (close beyond opposite extreme)
- Significance scoring based on normalized magnitude + time elapsed (0.0–1.0 scale)

---

## Key Takeaway

Spike penetration is the most **time-dependent** failed signal in Chapter 11. Unlike bull/bear traps (which play out in days) or false trend line breakouts (which can be immediate), spike penetrations gain their power from the **duration** the spike level has stood unchallenged. The longer a spike "holds" as a proven reversal point, the more explosive it is when finally broken. Schwager's inclusion of the "failed failed signal" (cocoa example) is a rare admission that even his most important rule has exceptions — and a reminder to always use stops.
