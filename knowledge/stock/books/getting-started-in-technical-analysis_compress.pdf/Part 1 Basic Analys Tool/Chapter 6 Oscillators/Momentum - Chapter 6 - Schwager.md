# Momentum
---
**Source:** *Getting Started in Technical Analysis* — Jack D. Schwager, Chapter 6 (pp. 110–113)
**Tags:** #technical-analysis #momentum #oscillators #schwager #price-change #indicators
**Related:** [[Oscillators]] · [[Equilibrium Line]] · [[Overbought and Oversold]] · [[Divergence]] · [[Rate of Change (ROC)]] · [[MACD]] · [[RSI]] · [[Stochastics]]

---

## Definition

Momentum is **the rate or speed of price change**. Not the direction of price, not the magnitude of a move, but *how fast* price is changing.

In calculus terms: momentum is the **first derivative of price** — not "where is price?" but "how quickly is price getting there?"

---

## The Two Meanings of "Momentum"

The word "momentum" is used in two distinct ways in Chapter 6. This causes confusion if not separated clearly.

### 1. Momentum as a Concept (Parent)
The foundational idea that **all oscillators are built on**. Every oscillator — RSI, stochastics, MACD, ROC, all of them — is trying to measure momentum in one way or another. Momentum the concept is the **parent**; oscillators are tools that measure it.

### 2. Momentum as a Specific Indicator (Child)
The simplest oscillator formula: `Today's close − Close N days ago`. It happens to share the name of the concept it measures because it's the most direct, unadorned way to quantify it. In this sense, the Momentum indicator is just **one member** of the oscillator family.

### The Hierarchy

```
Momentum (the concept — rate of price change)
  └── Oscillators (tools that measure momentum)
        ├── Momentum indicator (simplest: price − price N days ago)
        ├── Rate of Change / ROC (price ÷ price N days ago)
        ├── Moving average-based oscillator (price − MA)
        ├── Price oscillator (short MA − long MA)
        ├── MACD
        ├── RSI
        └── Stochastics
```

> **Analogy:** "Search" is a concept; "Google Search" is one specific implementation of it. Momentum is the concept; the Momentum indicator is one specific implementation.

---

## Relationship: Momentum ↔ Oscillators

This relationship is bidirectional and operates at two levels:

| | Momentum (concept) | Momentum (indicator) |
|---|---|---|
| **Relationship to Oscillators** | **Parent** — the foundational idea all oscillators measure | **Sibling** — one oscillator among many (RSI, MACD, stochastics, etc.) |
| **Scope** | Universal — applies to every oscillator | Specific — one particular formula |
| **Implication** | Understanding momentum = understanding what ALL oscillators tell you | The Momentum indicator is the simplest, most direct measurement |

> "Virtually all these indicators are based on the concept of momentum... almost all popular oscillators are variations on these simple themes." — Schwager

**Key insight:** The "arcane names and imposing formulas" of different oscillators are surface-level variety. Underneath, they're all reading the same engine gauge — momentum. The formula differences affect sensitivity and smoothing, but the underlying signal is the same.

---

## Why Momentum Matters — Two Components

Both feed into oscillator design:

### 1. Trend Health Assessment
- Healthy price trends exhibit **strong, consistent momentum**
- Weakening trends show **stagnant or declining momentum**
- This is an early warning of possible reversal or correction — the engine strains *before* the car slows down

### 2. Identifying Exhaustion Points (Overbought/Oversold)
- Extremely strong, rapid price moves are **not indefinitely sustainable**
- Even the strongest trends are punctuated by retracements
- Momentum flags moments where price has moved too far, too fast

---

## Price vs. Momentum — The Critical Distinction

These are two **separate dimensions** of market behavior:

| Dimension | Question it answers | What it tells you |
|---|---|---|
| **Price** | "Where is the market?" | Position / level |
| **Momentum** | "How fast is it getting there?" | Speed / force / quality of move |

They usually move together — price rising with rising momentum is a healthy trend. But they can **diverge**, and that divergence is where the most valuable information lives:
- Price makes a new high → momentum doesn't confirm → trend's engine is weakening even though the car is still moving forward
- This is the foundation of the [[Divergence]] concept

---

## Schwager's Two-Stock Example

**Stock A** over five days: +0.5, +1, +2, +3, +4 points
- Each day's gain is *accelerating*
- Total: +10.5 points
- **Strong momentum** — moving with increasing force

**Stock B** over five days: +2, −1, +0.5, +0.5, +0.25 points
- Gains are erratic and *decelerating*
- Total: +2.25 points
- **Weak momentum** — sputtering

Both stocks rose. But if you only looked at direction ("both went up"), you'd miss the critical difference. Momentum tells you about the **quality** of the move, not just its existence.

---

## How Momentum Gets Calculated

### The Momentum Indicator (Subtraction Method)
```
Momentum = Today's close − Close N days ago
```

**Example:** Stock closes at $105 today, was at $100 ten days ago → 10-day momentum = +5.
Next day: closes at $102, the 10-day-ago price was $101 → momentum = +1.
Price is still rising, but momentum has *decreased* — the pace of advance has slowed.

### Rate of Change / ROC (Division Method)
```
ROC = Today's close ÷ Close N days ago
```

Schwager notes these are "virtually identical" except for the scale. Both oscillate around a neutral level — the [[Equilibrium Line]].

---

## Reading Momentum — The Four States

Momentum indicator readings exist in four states relative to the equilibrium line:

### State 1: Above the line and rising ↗
- Price is advancing with *increasing* momentum
- The trend is **accelerating**
- Strongest bullish condition

### State 2: Above the line and falling ↘
- Price is still higher than N days ago, but the pace is slowing
- The trend is still positive but **decelerating**
- ⚠️ Early warning territory

### State 3: Below the line and falling ↘
- Price is declining with *increasing* downward momentum
- The trend is **accelerating to the downside**
- Strongest bearish condition

### State 4: Below the line and rising ↗
- Price is still lower than N days ago, but the decline is losing speed
- The downtrend is **decelerating**
- Potential bottoming signal

### The Ball Analogy
Think of a ball thrown into the air:
- **State 1:** Ball on its way up, still accelerating
- **State 2:** Ball still going up, but gravity is taking over — slowing down
- The deceleration (State 2) happens *before* the ball stops and reverses
- Momentum captures that deceleration before price itself turns — this is why it's useful as an **early warning system**

---

## Sensitivity — The N-Day Parameter Tradeoff

The number of days (N) controls how sensitive the oscillator is:

| Parameter | Behavior | Reversals Signaled | Noise Level |
|---|---|---|---|
| **Shorter (e.g., 5-day)** | Closely tracks short-term fluctuations | Smaller, more frequent | Higher — more false signals |
| **Longer (e.g., 20-day)** | Filters out minor swings, reflects major turning points | Larger, less frequent | Lower — smoother but laggier |

> This is an exact parallel to the **moving average length tradeoff** from Chapter 3 — shorter is more sensitive but noisier, longer is smoother but laggier. There is no "right" N value; it depends on what timeframe you're trying to read.

Schwager illustrates this with 5-day vs. 20-day momentum (Figure 6.3): the 5-day study reflects more of the smaller market swings, while the 20-day study mostly reflects the major turning points.

---

## The Key Takeaway

> Understanding momentum means you understand what **all** oscillators are actually telling you, regardless of their formula.

RSI, stochastics, MACD, price oscillators — they're all different mathematical wrappers around the same core question: **"How fast is price changing?"** The formula differences affect sensitivity and smoothing, but the underlying signal is the same. Once you understand momentum, the rest of Chapter 6 is exploring different ways to package and display it.

---

## Connection to Broader Framework

### Link to [[Oscillators]]
- Momentum is the **parent concept** that all oscillators measure
- The Momentum indicator is the **simplest oscillator** — one sibling among many
- All oscillator behaviors (overbought/oversold, divergence, skew) are manifestations of momentum dynamics

### Link to [[Divergence]]
- Divergence is what happens when price and momentum **disagree**
- Momentum declining while price rises = trend losing internal energy
- This is the most valuable early warning signal oscillators provide

### Link to Decision Support Framework
- Momentum doesn't predict *what will happen*
- It tells you *what the current speed profile looks like*
- Combined with price action and chart structure → informed entry/exit/sizing decisions with defined risk
