---
title: "Penetration of Top and Bottom Formations"
chapter: 11
concept: 11
tags:
  - failed-signals
  - double-top
  - double-bottom
  - head-and-shoulders
  - reversal
  - schwager
  - chapter-11
aliases:
  - Failed Double Top
  - Failed Double Bottom
  - Failed Head and Shoulders
  - Failed H&S
related:
  - "[[Failed Signals — The Overarching Principle]]"
  - "[[Bull Traps]]"
  - "[[Bear Traps]]"
  - "[[Breaking of Curvature]]"
  - "[[Ch5 — Chart Patterns]]"
  - "[[Ch4 — Trading Ranges and Support and Resistance]]"
  - "[[Ch9 — Choosing Stop-Loss Points]]"
---

# Penetration of Top and Bottom Formations

## Definition

When patterns normally associated with major tops and bottoms — double tops, double bottoms, and head-and-shoulders formations — are **penetrated**, it constitutes a failed signal. Price has neglected to respect the support or resistance level implied by the formation.

> *"The penetration of patterns that are normally associated with major tops and bottoms represents another important type of failed signal in that price has neglected to respect the support or resistance level implied by such formations."*
> — Schwager, Ch. 11

---

## Simple Analogy: The Prison Wall That Cracks

A double top or H&S pattern is like a prison wall — it holds the price in, and everyone agrees it's strong enough to keep holding. Guards (sellers at resistance, buyers at support) are stationed there. But then someone punches a hole through it.

If the wall was tested twice (double top) and held, and now it breaks — it means the force on the other side has grown stronger than what everyone believed was impenetrable. Once the wall cracks, there's nothing behind it to stop the escape. The more "tested" and "proven" the wall, the more dramatic the breakout when it finally fails.

---

## Three Sub-Patterns

### 1. Failed Double Top → BUY

| Element | Rule |
|---|---|
| **Original pattern** | Two peaks at approximately the same level = resistance |
| **Failed signal** | Price closes above the double top level |
| **Trade** | LONG (buy) |
| **Significance** | Good signals, but relatively rare |

Schwager's coffee example (Fig 11.27-28): a double top formed in July-September 1993 was penetrated approximately seven months later. The result was an immense rally. Schwager notes a key hindsight lesson: what looked like a major double top at the time was later dwarfed by the towering proportions of the subsequent rally — context changes everything.

### 2. Failed Double Bottom → SELL

Mirror of the double top. Two troughs at approximately the same level = support. Price closing below this level = the "proven" floor has failed → SELL.

### 3. Failed Head-and-Shoulders → BUY/SELL

Schwager considers failed H&S patterns **more common** and **often providing excellent indicators** compared to double top/bottom penetrations.

**Confirmation criterion**: prices retracing beyond the **most recent (right) shoulder**.

| H&S Type | Failed Signal Trigger | Trade |
|---|---|---|
| **H&S Top** | Close above the right shoulder | LONG (buy) |
| **H&S Bottom** (inverted) | Close below the right shoulder | SHORT (sell) |

---

## The Retracement Strategy

Schwager explicitly recommends considering a **wait-for-retracement** approach with failed H&S patterns:

> *"The trader may often benefit by waiting for a retracement before implementing a position based on the confirmation of a failed head-and-shoulders pattern."*

In the soybean oil example (Fig 11.30), prices first **rebounded** after the failed H&S bottom confirmation before eventually heading sharply lower.

**Trade-off**: waiting for a retracement gives a better entry price, but you may miss the trade entirely if no retracement occurs or the retracement is very modest.

---

## When This Concept Works Best

- **Double tops/bottoms that stood for months**: The coffee double top held for several months before being penetrated — longer duration = more market participants "agree" it's a top, more trapped when it fails
- **H&S patterns in widely-watched markets**: More observers = more positioning based on the pattern = more forced repositioning when it fails
- **After the neckline has already been broken**: An H&S top that triggered sells on the neckline break, then reversed through the right shoulder, traps the most committed sellers
- **Combined with other failed signals**: A failed H&S that coincides with a [[Return to Spike Extremes|spike penetration]] or [[Filled Gaps as Failed Signals|filled gap]] amplifies the signal

---

## When to Be Cautious

- **Marginal penetrations**: A close barely above a double top by a tiny amount may be noise. Look for a decisive breakthrough
- **H&S patterns with sloping necklines**: Ambiguity in where the shoulders and neckline are = ambiguity in the confirmation level
- **Double tops/bottoms are rare as failed signals**: Schwager notes they provide "good signals but are relatively rare." Don't force the pattern
- **Retracement can confuse**: After a failed H&S confirmation, a pullback toward the shoulder level can look like the formation is reasserting itself. Define your invalidation level clearly

---

## Schwager's Key Examples

### May/July 1994 Coffee (Figures 11.27-28)
A double top formed in July-September 1993 was penetrated approximately seven months later. The immense rally that followed made the earlier double top "look like nothing more than a squiggle in an extended, narrow trading range." Key lesson: formations that appear major at the time can be dwarfed by subsequent moves.

### IBM (Figure 11.29)
A failed head-and-shoulders top pattern. The rebound above the November 1995 (right) shoulder confirmed the H&S top as failed = BUY signal.

### July 1991 Soybean Oil (Figure 11.30)
A failed head-and-shoulders bottom pattern. The downside penetration of the right shoulder confirmed the formation as failed = SELL signal. Notably, prices first rebounded after confirmation before heading sharply lower — illustrating the retracement opportunity.

---

## Schwager's Frequency Assessment

| Pattern Type | As Failed Signal | Frequency | Quality |
|---|---|---|---|
| **Double top/bottom** | Price penetrates the double level | Relatively rare | Good |
| **Head-and-shoulders** | Price beyond right shoulder | More common | Often excellent |

This frequency difference means traders should focus more attention on monitoring H&S patterns for failure than on double tops/bottoms.

---

## Cross-Chapter Links

- **[[Failed Signals — The Overarching Principle]]**: Top/bottom formation failures are a specific application
- **[[Ch5 — Chart Patterns]]**: Defines double tops/bottoms, head-and-shoulders, and their normal interpretation as reversal patterns
- **[[Ch4 — Trading Ranges and Support and Resistance]]**: The formation levels act as support/resistance — penetration = support/resistance failure
- **[[Bull Traps]]** / **[[Bear Traps]]**: Conceptually related — both involve price "proving" a level then breaking through it. Traps operate on ranges; this operates on reversal formations
- **[[Breaking of Curvature]]**: Next concept — another formation-level failed signal (rounding patterns)

---

## Python Implementation

See `failed_formation_detector.py`:
- `detect_double_top()` / `detect_double_bottom()` — find double formations with configurable tolerance and valley/peak depth requirements
- `detect_hs_top()` — finds H&S patterns with shoulder tolerance and head protrusion requirements
- `detect_failed_formation()` — monitors for close beyond the key level (double top/bottom level or right shoulder price)
- All detectors use swing-point-based analysis with configurable sensitivity

---

## Key Takeaway

Failed top/bottom formations are among the most psychologically impactful failed signals because the original patterns (double tops, H&S) are so widely taught and recognized. When a "textbook" double top or H&S is negated, it forces a massive repositioning — everyone who sold on the pattern must now cover, and everyone who was waiting to sell now has to reconsider. Schwager's coffee example is the perfect illustration: what looked like a definitive double top ceiling at the time turned out to be nothing more than a minor pause before a towering rally. The lesson cuts both ways — be humble about pattern identification, and be ready to reverse when the pattern fails.
