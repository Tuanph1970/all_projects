# Oscillators
---
**Source:** *Getting Started in Technical Analysis* — Jack D. Schwager, Chapter 6 (pp. 110–119)
**Tags:** #technical-analysis #oscillators #momentum #schwager #countertrend #indicators
**Related:** [[Momentum]] · [[RSI]] · [[Stochastics]] · [[MACD]] · [[Overbought and Oversold]] · [[Divergence]] · [[Failed Signals]] · [[Trading Ranges]] · [[Trends]]

---

## Definition

Oscillators are **price-based mathematical formulas** — a subset of technical indicators — used to evaluate price activity and make trading decisions. They are a group of **countertrend, momentum-based indicators** that typically move above and below a horizontal axis (the equilibrium line) representing neutral market momentum.

> Despite the variety of names and imposing formulas, **virtually all oscillators are variations on the same underlying concept: momentum** — the rate (speed) at which prices change. — Schwager

### Key Members of the Oscillator Family
- **Momentum** (price minus price N days ago)
- **Rate of Change / ROC** (price divided by price N days ago)
- **Moving Average-based oscillator** (price minus moving average)
- **Price Oscillator** (short MA minus long MA)
- **MACD** — Moving Average Convergence-Divergence
- **RSI** — Relative Strength Index
- **Stochastics** (%K and %D lines)

> "One of the most significant aspects of Figures 6.1–6.5 is the **similarity between the different oscillators** despite the variety of calculations used to construct them." — Schwager

---

## Purpose — Two Components

Both purposes are rooted in momentum:

### 1. Trend Health Assessment (Diagnostic Use)
- Healthy price trends exhibit **strong, consistent momentum**
- Weakening trends show **stagnant or declining momentum** — an early warning of possible reversal or correction
- Used as a **thermometer**: reading the internal condition of the trend, not trading against it
- Example: RSI peaks declining across successive price highs → trend is losing energy even while price still rises

### 2. Identifying Short-Term Exhaustion Points (Overbought/Oversold)
- Extremely strong, rapid price moves are **not indefinitely sustainable**
- Even the strongest trends are punctuated by retracements
- Oscillators flag moments where price has moved **too far, too fast** — vulnerable to at least a temporary reversal
- These extremes are labeled **overbought** (too high, too fast) and **oversold** (too low, too fast)

---

## Countertrend Nature

Oscillators are **primarily countertrend tools** — they generate signals *against* the prevailing price direction.

### Countertrend vs. Trend-Following — The Two Camps

| Approach | Question Asked | Signal Logic | Tools |
|---|---|---|---|
| **Trend-following** | "Is a trend underway? Get on board." | Signals *in the direction* of the move | Moving averages, breakouts, trend lines |
| **Countertrend** | "Has the move gone too far? Fade it." | Signals *against* the move | Oscillators (RSI, stochastics, MACD, etc.) |

### Why Oscillators Are Countertrend by Mechanics
When an oscillator hits an overbought level, it says "price has risen a lot, very fast." The implied trade is to **sell into that strength** — which is by definition a countertrend action. You're not joining the move; you're betting against its continuation.

### The Psychological Appeal — and the Trap
- Countertrend trading *feels* smart — buying low, selling high, outsmarting the crowd
- Trend-following *feels* like chasing — buying after price has already risen
- But this psychological comfort is precisely what leads traders into the trap: **oscillators assume the current move will reverse, but trends can persist far longer than oscillators suggest they should**

---

## The Four Use Cases of Oscillators

This is the critical framework for understanding when oscillators help vs. when they destroy you.

### Use Case 1: Countertrend Trading Signals in a Range ✅ (Where Oscillators Shine)

**Scenario:** Stock bouncing between $50 and $60 for months. No clear trend.

**How used:** RSI drops below 30 near $50 → buy. RSI rises above 70 near $60 → sell. Oscillator acts as **entry and exit trigger**.

**Why it works:** In a range, prices genuinely mean-revert. Support and resistance act as walls. The oscillator quantifies what the range boundaries already tell you — momentum has pushed price to an extreme that will snap back.

**Schwager's evidence:** Soybean oil example (Figure 10.6) — RSI overbought/oversold signals provide "reasonably good position liquidation signals" because the market stayed in a trading range.

> This is the use case behind the statement "oscillators work well in ranges."

---

### Use Case 2: Countertrend Trading Signals in a Trend ❌ (Where Oscillators Destroy You)

**Scenario:** Stock breaks out at $60 and trends to $100 over several months.

**How used (incorrectly):** RSI hits 70 at $70 → short. Price keeps climbing. RSI hits 75 at $80 → short again. Every trade is a loser.

**Why it fails:** "Overbought" means "has risen fast" — not "will reverse." In a strong trend, fast rises are *normal*, not exhaustive. The oscillator reports a fact about speed, but the trader interprets it as a reversal prediction.

**Schwager's evidence:** Citicorp weekly chart (Figure 6.8) — RSI posted "repeated and sustained overbought signals without registering a single oversold signal." Nothing but false sell signals through the entire uptrend.

**Key observation — Oscillator Skew:** In trending markets, oscillators become **systematically skewed** in the direction of the trend. In an uptrend: constant overbought signals, no oversold signals. In a downtrend: constant oversold signals, no overbought signals. This is a structural property, not a bug you can fix.

> This is the use case behind the statement "oscillators are bad in trends." It is true — **for this specific application**.

---

### Use Case 3: Trend Health Diagnostic ✅ (Oscillators Add Value *During* Trends)

**Scenario:** Same stock trending from $60 to $100. You're already long, asking: "Is this trend still healthy?"

**How used:** You **observe, don't trade**:
- Rally $60→$70: RSI peaks at 78. Strong momentum. Healthy.
- Rally $72→$82: RSI peaks at 76. Consistent.
- Rally $85→$95: RSI peaks at 68. Price made higher high, RSI made lower high. **Momentum divergence emerging.**
- Rally $92→$100: RSI peaks at 60. Divergence widening.

**What you do:** You don't short. But you might:
- Tighten your trailing stop
- Take partial profits
- Decide *not* to add to the position
- Watch for price confirmation of a reversal

**Why this works even in trends:** You're not asking "should I fight the trend?" (the question oscillators can't answer). You're asking "is the trend's engine weakening?" (the question momentum measurement is designed to answer). You still require **price confirmation** before acting.

> The oscillator is a dashboard gauge, not a trade trigger.

---

### Use Case 4: Trend-Direction Entry Timing ✅ (The Often-Overlooked Use)

**Scenario:** Stock is in a clear uptrend. You want to buy, but not at the top of a short-term rally.

**How used:** Wait for RSI to pull back toward the lower end of its recent range within the uptrend (e.g., RSI dips to 40-45 during a minor pullback). Buy — because short-term selling pressure has temporarily exhausted itself.

**Key insight:** You're using the oscillator as a countertrend tool **in service of a trend-following strategy**. The oscillator doesn't tell you the direction (you know the trend is up from chart structure). It tells you **timing** — when the pullback has run its course.

**Schwager's hint:** On the Citicorp chart, the oscillator never produced oversold signals, but he notes "the latter would have been more useful for traders seeking entry points to the existing trend." In an uptrend, the *oversold* signals (not overbought) are the valuable ones.

**Requires adjusting OB/OS levels for trend:** In a strong uptrend, shift from 70/30 to something like 80/40 — harder to trigger sell signals, easier to trigger buy-the-dip signals.

---

## Summary Matrix: When Oscillators Help vs. Hurt

| | **Range Market** | **Trending Market** |
|---|---|---|
| **As trade trigger** (countertrend entry) | ✅ Works well — mean reversion is real within ranges | ❌ Disaster — fighting a trend that persists |
| **As diagnostic** (reading momentum / timing entries) | ⚪ Less interesting — no trend to diagnose | ✅ Very useful — trend health assessment, pullback entry timing |

> **The same indicator reading means different things depending on what question you're asking.** RSI at 75 can mean "sell this overextended range-bound stock" (valid), "sell this trending stock" (dangerous), or "the trend still shows strong momentum" (useful information). The oscillator doesn't know which market context it's in — **you** have to.

---

## Schwager's Conclusion: Oscillators as "Trading Alerts"

Because of the structural limitations in trending markets — and because **it is impossible to know when a trend will end and a trading range will begin** — Schwager concludes that oscillator signals should be used as **"trading alerts"**, not standalone trade triggers.

### The Recommended Sequence:
1. **Oscillator flags a condition** (e.g., overbought, divergence)
2. **You do NOT act on that alone**
3. **Wait for price itself to confirm** a reversal — through a chart pattern, support/resistance break, failed signal, etc.
4. **Only then take the trade**

> The oscillator provides the **hypothesis** ("this move may be exhausted"). Price action provides the **confirmation**. Without the second step, you're blindly fading trends.

### Risk Management is Non-Negotiable
> "Unless stops are used to limit risk, countertrend oscillator signals can lead to large and repeated losses." — Schwager

---

## Connection to Broader Framework

### Link to Failed Signals (Chapter 11)
Oscillator divergences and overbought/oversold signals are themselves **potential failed signals** — they predict a reversal that may never come. The failed signal framework applies here: if the oscillator-predicted reversal doesn't materialize, that failure itself may be a stronger signal (the trend is even more robust than expected).

### Link to Contrarian Detection (Buffett → Schwager)
Oscillators are one of the chart-based mechanisms for detecting Buffett's "fearful when others are greedy" extremes. But just as Buffett doesn't short solely because others are bullish, Schwager says don't sell solely because an oscillator says overbought. The extreme is the **alert**; the confirmation is the **trigger**.

### Link to Decision Support Framework
Oscillators fit Schwager's broader philosophy: technical analysis is about **decision support with defined risk**, not prediction. Oscillators answer:
- "How much energy is behind this move?"
- "Is this move overextended?"
These feed into entry, exit, and position-sizing decisions. They don't tell you *what will happen* — they tell you *what the current momentum profile looks like*.

---

## Chapter 6 — Full Concept List

1. ~~Oscillators (definition and purpose)~~ ✅
2. Momentum (rate of price change)
3. Equilibrium line
4. Overbought levels
5. Oversold levels
6. Momentum indicator (price - price N days ago)
7. Rate of Change / ROC (price ÷ price N days ago)
8. Oscillator sensitivity (effect of N-day period selection)
9. Moving average–based oscillator (price - MA)
10. Price oscillator (short MA - long MA)
11. MACD (Moving Average Convergence-Divergence)
12. MACD signal line (9-day MA of MACD)
13. MACD histogram
14. MACD crossover signals
15. Unbounded vs. normalized (bounded) oscillators
16. Relative Strength Index (RSI)
17. Stochastics (%K / %D, fast vs. slow)
18. Setting OB/OS levels for unbounded indicators
19. Setting OB/OS levels for normalized indicators
20. Divergence (momentum vs. price disagreement)
21. Bullish divergence
22. Bearish divergence
23. Multiple/repeated divergences (false divergence problem)
24. Oscillator skew in trending markets
25. Adjusting OB/OS levels for trend direction
26. Oscillators as "trading alerts" (requiring price confirmation)
27. Oscillator effectiveness: trading range vs. trending market
