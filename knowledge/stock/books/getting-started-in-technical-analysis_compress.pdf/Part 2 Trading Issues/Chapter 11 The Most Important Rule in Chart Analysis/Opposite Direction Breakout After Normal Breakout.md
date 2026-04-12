---
title: "Opposite Direction Breakout After Normal Breakout"
chapter: 11
concept: 10
tags:
  - failed-signals
  - flag
  - pennant
  - reversal
  - two-phase-failure
  - schwager
  - chapter-11
aliases:
  - Opposite Direction Breakout
  - Flag Reversal After Normal Breakout
  - Two-Phase Flag Failure
related:
  - "[[Failed Signals — The Overarching Principle]]"
  - "[[Counter-to-Anticipated Flag Pennant Breakout]]"
  - "[[Bull Traps]]"
  - "[[Bear Traps]]"
  - "[[Ch5 — Chart Patterns]]"
  - "[[Ch9 — Choosing Stop-Loss Points]]"
---

# Opposite Direction Breakout After Normal Breakout

## Definition

In some cases, a flag or pennant is followed by a breakout in the **expected** direction, but price then reverses and **closes beyond the opposite extreme** of the flag/pennant. This two-phase price action is a failed signal — the anticipated continuation breakout is followed by a reversal rather than follow-through.

> *"This combined price action provides another example of a failed signal, since the anticipated breakout of the flag or pennant is followed by a price reversal instead of a price follow-through."*
> — Schwager, Ch. 11

---

## Simple Analogy: The False Start in a Race

A sprinter (the trend) gets into position, the gun fires (the flag breakout), and they launch forward — correctly, in the expected direction. But after a few strides, they stumble and fall backward past the starting line.

If the sprinter can't sustain momentum even with a proper start and a clear track, something is fundamentally wrong. That information is more damning than if they'd simply refused to leave the blocks (which would be Concept 9 — a direct counter breakout).

The two-phase failure reveals more: the market **tried** to continue and **demonstrably couldn't**.

---

## The Two-Phase Mechanism

### Phase 1: Normal breakout (looks correct)

1. Flag/pennant forms in a trend
2. Price breaks out in the **expected** direction — continuation appears to be underway
3. Breakout traders enter positions in the trend direction

### Phase 2: Reversal (the failure)

4. Breakout stalls — only lasts a few bars with limited follow-through
5. Price reverses back through the flag
6. **Close beyond the opposite end** of the flag/pennant = **confirmed failed signal**

The confirmation requires a **close**, not a mere intraday touch:

> *"A close beyond the opposite end of the flag or pennant is required to confirm a failed signal, rather than a mere intraday penetration."*
> — Schwager, Ch. 11

---

## Trading Rules

### Uptrend flag: normal UP breakout → reversal → SELL

| Element | Rule |
|---|---|
| **Phase 1** | Close above flag upper boundary (normal breakout) |
| **Phase 2** | Close below flag **lower** boundary (reversal) |
| **Direction** | SHORT |
| **Confirmation** | Close below lower boundary required |

### Downtrend flag: normal DOWN breakout → reversal → BUY

| Element | Rule |
|---|---|
| **Phase 1** | Close below flag lower boundary (normal breakout) |
| **Phase 2** | Close above flag **upper** boundary (reversal) |
| **Direction** | LONG |
| **Confirmation** | Close above upper boundary required |

---

## Concept 9 vs. Concept 10

Both involve flags breaking the "wrong" way, but the sequence differs fundamentally:

| Attribute | Concept 9 (Counter Breakout) | Concept 10 (Opposite After Normal) |
|---|---|---|
| **Phases** | One — flag breaks directly wrong | Two — breaks correctly, then reverses |
| **Normal breakout?** | Never occurs | Occurs first, then fails |
| **Information content** | Trend couldn't even start | Trend tried and failed |
| **Signal strength** | Strong | Arguably **stronger** — demonstrated failure |
| **Trapped traders** | Those who expected continuation | Those who entered ON the breakout — more committed |
| **Schwager's examples** | Cotton, cocoa, soybean oil | DuPont, coffee, heating oil |

The two-phase nature makes Concept 10 arguably the more informative signal: the market generated a "correct" buy/sell signal, lured traders in, then reversed. Those trapped breakout traders now become forced sellers/buyers, adding fuel to the reversal.

---

## When This Concept Works Best

- **Brief, unconvincing normal breakouts**: Schwager's DuPont example — the upside breakout lasted only three days, with only two closes above the flag boundary. The shorter and weaker the normal breakout, the more suspicious it is
- **At trend extremes**: Flag near the top of a four-month advance (DuPont) or after an extended price slide (coffee, heating oil). The trend had already traveled far
- **Combined with Concept 9 on the same chart**: Schwager's heating oil example (Fig 11.26) contains both a Concept 10 at the bottom (downside breakout → rebound above flag = BUY) and a Concept 9 counter breakout at the market top — two flag failure types on one chart
- **When the reversal is swift**: If the market takes only 4-7 bars to go from normal breakout to opposite-end close, the failure is emphatic

---

## When to Be Cautious

- **Extended normal breakouts**: If the normal breakout lasts many bars and travels significantly, a pullback through the flag may be part of normal price volatility rather than a genuine reversal
- **Very wide flags**: A flag with a wide range means the "opposite end" is far from the breakout — the reversal needs to be large to confirm, which increases the risk on entry
- **Intraday penetrations without closes**: Schwager is explicit — require a close beyond the opposite end. Intraday touches alone create too many false alarms

---

## Schwager's Key Examples

### DuPont (Figure 11.24)
A flag near the top of a four-month advance. Upside breakout occurred as anticipated — but prices moved higher for only three days (only two closed above the flag's upper boundary). Within four more days, prices retreated below the flag's lower end. The earlier upside breakout was confirmed as a failed signal.

### December 1992 Coffee (Figure 11.25)
After an extended price slide, a flag broke downside (expected). The breakout led to little further downside movement. Prices soon rebounded above the top of the pennant — confirming a failed signal and presaging a large advance.

### April 1992 Heating Oil (Figure 11.26)
A rebound above the top of a flag after an initial downside breakout confirmed a relative low and led to a large advance. **Notably**, this same chart also contains a Concept 9 counter-to-anticipated breakout at the market top — both flag failure types on one chart.

---

## Cross-Chapter Links

- **[[Failed Signals — The Overarching Principle]]**: Two-phase flag failure is a specific application
- **[[Counter-to-Anticipated Flag Pennant Breakout]]**: The sister concept (Concept 9) — direct counter breakout without a prior normal breakout. Both concepts apply to the same flag/pennant patterns from Ch 5
- **[[Bull Traps]]** / **[[Bear Traps]]**: Structurally similar — a signal that initially appears correct then reverses. Bull/bear traps operate on ranges; this operates on flags
- **[[Ch5 — Chart Patterns]]**: Defines flags and pennants as continuation patterns
- **[[Ch9 — Choosing Stop-Loss Points]]**: The normal breakout extreme can serve as an additional reference level

---

## Python Implementation

See `opposite_direction_breakout_detector.py`:
- `detect_opposite_direction_breakout()` — implements the full two-phase detection: normal breakout (close beyond expected boundary) → reversal (close beyond opposite boundary). Tracks how many bars and closes the normal breakout lasted
- `scan_for_both_flag_failures()` — checks for **both** Concept 9 and Concept 10 at a single flag location (replicating Schwager's heating oil example where both types appear on one chart)
- Builds on `counter_flag_breakout_detector.py` for shared flag/pennant detection

---

## Key Takeaway

The opposite-direction breakout after a normal breakout is the **most deceptive** failed signal in Chapter 11. Unlike other failed signals where the original pattern never "works," here it *does* work — briefly. The normal breakout looks correct, traders enter with confidence, and then the rug is pulled. It's a two-act play: Act 1 builds trust, Act 2 betrays it. That betrayal, because it follows a genuine-looking signal, traps the most committed participants — those who acted on a "confirmed" breakout — and their forced liquidation provides the fuel for the reversal. This is why Schwager requires the stricter close-based confirmation: the two-phase nature already provides powerful information, so the slightly delayed confirmation is worth the reduced false alarm rate.
