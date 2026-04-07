# Chapter 6 — Oscillators: Complete Summary
---
**Source:** *Getting Started in Technical Analysis* — Jack D. Schwager, Chapter 6 (pp. 110–119)
**Tags:** #technical-analysis #oscillators #chapter-6 #schwager #summary #momentum #indicators
**Related:** [[Oscillators]] · [[Momentum]] · [[Equilibrium Line]] · [[Overbought and Oversold]] · [[Momentum Indicator]] · [[Rate of Change (ROC)]] · [[Oscillator Sensitivity]] · [[Moving Average-Based Oscillator]] · [[Price Oscillator]] · [[MACD]] · [[Unbounded vs Normalized Oscillators]] · [[RSI]] · [[Stochastics]] · [[Divergence]] · [[MACD + Volume Confirmation]]

---

## The Chapter in One Paragraph

Despite the variety of names and imposing formulas, virtually all oscillators are variations on a single concept: **momentum** — the rate at which prices change. They serve two purposes: assessing trend health (diagnostic) and identifying short-term exhaustion points (overbought/oversold). As countertrend tools, they work well in trading ranges but are dangerous in trending markets. Schwager's conclusion: oscillator signals should be treated as **"trading alerts"** requiring price confirmation, not standalone trade triggers. Unless stops are used to limit risk, countertrend oscillator signals can lead to large and repeated losses.

---

## Remaining Concepts (23–27)

### Concept 23: Multiple/Repeated Divergences

Covered in detail in [[Divergence]]. The key points:

> "Divergences rarely occur only between the penultimate and final peaks in an advance, or the last two lows in a downtrend." — Schwager

- Divergences can appear **multiple times** during a sustained trend, long before the actual reversal
- Schwager's Citicorp example shows 5+ bearish divergences during a continued uptrend (points X, Y, Z, A, B, C, D)
- Traders who short at the first divergence enter **prematurely** and see the market continue climbing
- The reason: in strong trends, the initial momentum burst is almost always the strongest. Every subsequent rally naturally has slightly less momentum — making divergence **normal** in healthy trends, not a death signal.

**Practical implication:** Never act on divergence alone. Each divergence looks like "the one" that will work, pulling you into repeated losing positions. Require price confirmation (support break, chart pattern reversal, failed signal) before acting.

---

### Concept 24: Oscillator Skew in Trending Markets

Covered in detail in [[Overbought and Oversold]] and [[Oscillators]]. The key points:

> "The oscillator posted repeated and sustained overbought signals without registering a single oversold signal." — Schwager (on Citicorp, Figure 6.8)

In trending markets, oscillators become **systematically skewed** in the trend's direction:

| Trend | OB Signals | OS Signals | Result |
|---|---|---|---|
| **Uptrend** | Frequent, sustained | Rare or absent | Many false sell signals, no useful buy signals |
| **Downtrend** | Rare or absent | Frequent, sustained | Many false buy signals, no useful sell signals |

The skew produces exactly the wrong signal profile: in an uptrend, the sell signals you don't need fire constantly while the buy-the-dip signals you do need never appear. This is a **structural property** of all oscillators in trends, not a bug in any specific formula.

---

### Concept 25: Adjusting OB/OS Levels for Trend Direction

Covered in detail in [[Overbought and Oversold]]. Schwager's explicit recommendation:

> "It is necessary to adjust overbought and oversold levels to compensate for trend." — Schwager

| Market Context | OB Level (RSI) | OS Level (RSI) | Logic |
|---|---|---|---|
| **Range** | 70 | 30 | Symmetric — both sides useful |
| **Uptrend** | 80 | 40 | Suppress sell signals, enable buy-dip signals |
| **Downtrend** | 60 | 20 | Suppress buy signals, enable sell-rally signals |

Shifting both levels in the trend's direction transforms the oscillator from a countertrend tool (fighting the trend) into a **trend-direction entry timer** (buying pullbacks within the trend). This is the bridge from Use Case 2 (disaster) to Use Case 4 (useful).

---

### Concept 26: Oscillators as "Trading Alerts"

This is Schwager's concluding recommendation — the practical framework for using oscillators safely:

> "Because of these limitations, oscillator signals are often used as 'trading alerts,' warnings of possible price developments. Positions are established only when price confirms a reversal." — Schwager

The two-step process:
1. **Oscillator provides the hypothesis:** "Conditions are extreme" (OB/OS) or "Momentum is not confirming" (divergence)
2. **Price provides the confirmation:** A chart pattern, support/resistance break, failed signal, or other price-based evidence that the market is actually turning

Without step 2, you're trading on the oscillator's opinion about momentum speed — which is a fact, not a prediction. The confirmation converts the fact into an actionable signal.

### Why This Matters
- OB/OS without confirmation → repeated losses in trends (the rubber band held by the trend hand)
- Divergence without confirmation → premature entries against sustained trends (the multiple divergence problem)
- Alert + confirmation → higher quality signals at the cost of later entries (the familiar sensitivity tradeoff, but applied to the entire framework rather than a single parameter)

---

### Concept 27: Oscillator Effectiveness — Trading Range vs. Trending Market

This is the meta-concept that frames the entire chapter. Schwager opens and closes with it:

> "While the traditional countertrend approach of selling when the oscillator is overbought and buying when the oscillator is oversold may provide excellent entry points in trading ranges, it is a recipe for disaster in trending markets." — Schwager

The **core unsolvable problem:** you can't know in advance whether the market is about to trend or stay in a range. "It is impossible to know when a trend will end and a trading range will begin." This means any oscillator-based approach carries inherent regime risk — the strategy that works perfectly in one context destroys you in the other.

**Schwager's solutions:**
1. Use oscillators as alerts, not triggers (concept 26)
2. Require price confirmation before acting
3. Always use stops to limit risk
4. Adjust OB/OS levels for the prevailing trend (concept 25)
5. Recognize that oscillators are diagnostic tools for trend health, not just countertrend entry generators

This is the same trending/ranging regime tradeoff identified in Chapter 3 for moving averages — but viewed from the opposite side. Moving averages fail in ranges; oscillators fail in trends. They're complementary tools, each excelling where the other struggles.

---

## The Four Use Cases — Complete Framework

From the [[Oscillators]] note, the definitive framework for oscillator application:

| | **Range Market** | **Trending Market** |
|---|---|---|
| **As trade trigger** (countertrend entry) | ✅ Works well | ❌ Disaster |
| **As diagnostic** (trend health / entry timing) | ⚪ Less relevant | ✅ Very useful |

---

## The Oscillator Family Tree

```
Momentum (the concept — rate of price change)
  └── Oscillators (tools that measure momentum)
        │
        ├── UNBOUNDED (no fixed range)
        │   ├── Momentum indicator (price − price N days ago)
        │   ├── Rate of Change / ROC (price ÷ price N days ago)
        │   ├── MA-based oscillator (price − MA)
        │   ├── Price oscillator (short MA − long MA)
        │   └── MACD (EMA12 − EMA26 + signal line + histogram)
        │
        └── NORMALIZED (fixed 0–100 range)
            ├── RSI (gain/loss balance, Wilder smoothing)
            └── Stochastics (close position in N-day range, %K/%D)
```

---

## The Smoothing Ladder

```
Momentum         = Price − Price(N)          ← raw vs. raw (fastest, noisiest)
MA Oscillator    = Price − MA(N)             ← raw vs. smoothed
Price Oscillator = MA(short) − MA(long)      ← smoothed vs. smoothed
MACD line        = EMA(12) − EMA(26)         ← smoothed vs. smoothed (EMA)
Signal line      = 9-EMA of MACD line        ← oscillator smoothed again
Histogram        = MACD − Signal             ← rate of change of the smoothed
```

Each rung adds processing: noise decreases, lag increases. No free lunch.

---

## Key Equivalences to Remember

These prevent double-counting signals as independent confirmations:

| What appears as two things | Is actually one thing |
|---|---|
| N-day MA direction change on price chart | N-day Momentum crossing zero |
| Price crossing the MA | MA-based oscillator crossing zero |
| Short MA crossing long MA on price chart | Price oscillator crossing zero |
| 12-EMA crossing 26-EMA | MACD crossing zero |
| Momentum shape vs. ROC shape | Identical — different scale only |
| Subtraction vs. division oscillators | Same shape — same signals |

---

## Schwager's Core Messages

1. **All oscillators measure the same thing:** momentum. Different formulas, same fundamental information.
2. **OB/OS works in ranges, fails in trends.** This is structural, not fixable by changing the oscillator.
3. **Divergence is a warning, not a signal.** Multiple divergences are common in healthy trends.
4. **Oscillators are alerts, not triggers.** Price confirmation is required before acting.
5. **Stops are non-negotiable.** "Unless stops are used to limit risk, countertrend oscillator signals can lead to large and repeated losses."
6. **The trending/ranging regime problem is unsolvable.** You can't know in advance which context you're in. Design your approach to survive being wrong about the regime.

---

## Chapter 6 Vault — Complete Note Inventory

| # | Note | Concepts Covered |
|---|---|---|
| 1 | [[Oscillators]] | 1. Definition/purpose, countertrend nature, four use cases, summary matrix |
| 2 | [[Momentum]] | 2. Rate of price change, parent/child relationship, two purposes |
| 3 | [[Equilibrium Line]] | 3. Zero line, three zones, four states, crossover signals |
| 4 | [[Overbought and Oversold]] | 4-5. OB/OS levels, unbounded vs normalized setting, trend adjustment, timing approaches, skew problem |
| 5 | [[Momentum Indicator]] | 6. Simplest oscillator, MA equivalence, speedometer analogy |
| 6 | [[Rate of Change (ROC)]] | 7. Division sibling, scale independence, cross-instrument portability |
| 7 | [[Oscillator Sensitivity]] | 8. N-day tradeoff, proportionality rule, microscope analogy |
| 8 | [[Moving Average-Based Oscillator]] | 9. Price minus MA, bridge between trend/countertrend, dog-on-leash analogy |
| 9 | [[Price Oscillator]] | 10. Short MA minus long MA, double smoothing, two-runners analogy, MA crossover equivalence |
| 10 | [[MACD]] | 11-14. EMA(12)-EMA(26), signal line, histogram, crossover signals, convergence/divergence naming |
| 11 | [[MACD + Volume Confirmation]] | Extended: volume as independent confirmation, OBV divergence, double divergence |
| 12 | [[Unbounded vs Normalized Oscillators]] | 15. Two oscillator families, OB/OS level-setting difference, thermometer analogy |
| 13 | [[RSI]] | 16. Gain/loss balance, Wilder smoothing, win-loss analogy, formula walkthrough |
| 14 | [[Stochastics]] | 17. Close position in range, fast/slow variants, elevator analogy, %K/%D crossover |
| 15 | [[Divergence]] | 20-23. Bearish/bullish divergence, multiple divergence warning, runner's lap times analogy |
| 16 | [[Chapter 6 — Oscillators Complete Summary]] | 23-27. Multiple divergences, oscillator skew, trend adjustment, trading alerts, range vs trend effectiveness |

**Total: 16 notes** covering all 27 concepts from Chapter 6.

---

## Analogies Reference

| Concept | Analogy | What It Maps To |
|---|---|---|
| [[Equilibrium Line]] | Sea level | Neutral momentum reference point |
| [[Overbought and Oversold]] | Rubber band | Stretch (extreme) + snap-back (reversal) + hand (trend holding the stretch) |
| [[Momentum Indicator]] | Raw speedometer | Unfiltered, fast, noisy, scale-dependent |
| [[Rate of Change (ROC)]] | Percentage ruler | Scale-independent measurement of the same distance |
| [[Oscillator Sensitivity]] | Microscope zoom | Different N values see different phenomena, not just different resolution |
| [[Moving Average-Based Oscillator]] | Dog on a leash | Price (dog) orbits the MA (person), oscillator measures the leash length |
| [[Price Oscillator]] | Two runners | Gap between fast and slow runners = momentum |
| [[MACD]] | Speedometer + avg + gauge | Three layers of the same speed measurement |
| [[Unbounded vs Normalized Oscillators]] | Two thermometer types | Raw difference vs. percentage scale — portable vs. instrument-specific |
| [[RSI]] | Win-loss record | Adjusted for margin of victory, scaled to 0-100 |
| [[Stochastics]] | Elevator in a building | Position within the recent range = what floor you're on |
| [[Divergence]] | Runner's lap times | Distance keeps growing, but each lap takes longer |

---

## What Comes Next

Chapters beyond Chapter 6 remain to be studied:
- **Chapter 7:** Is Chart Analysis Still Valid? — Schwager's defense of technical analysis
- **Chapter 8:** Midtrend Entry and Pyramiding — entering positions within existing trends
- **Chapter 9:** Choosing Stop-Loss Points — risk control mechanics
- **Chapter 10:** Setting Objectives and Other Position Exit Criteria — includes OB/OS, contrary opinion, trailing stops
- **Chapter 11:** The Most Important Rule in Chart Analysis — failed signals (the contrarian framework)
- **Chapter 12:** Real-World Chart Analysis — Schwager's actual trade examples

Open conceptual threads worth revisiting:
- Multi-timeframe analysis (daily/weekly integration)
- Volume as a confirmation tool within Schwager's price-centric framework
- Combining indicators (MACD + RSI + volume — independent dimensions)
- The trending/ranging regime detection problem — Schwager's "unsolvable" core challenge
