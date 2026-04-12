---
title: "Breaking of Curvature"
chapter: 11
concept: 12
tags:
  - failed-signals
  - rounding-pattern
  - curvature
  - saucer
  - reversal
  - schwager
  - chapter-11
aliases:
  - Breaking Curvature
  - Failed Rounding Top
  - Failed Rounding Bottom
  - Failed Saucer
related:
  - "[[Failed Signals — The Overarching Principle]]"
  - "[[Penetration of Top and Bottom Formations]]"
  - "[[Ch5 — Chart Patterns]]"
  - "[[Ch9 — Choosing Stop-Loss Points]]"
---

# Breaking of Curvature

## Definition

Rounding patterns (tops and bottoms, also called "saucers") are among the most reliable chart formations. When the smooth curvature of such a pattern is **broken** — price suddenly deviates from the expected arc — the rounding pattern becomes a failed signal.

- Rounding top curvature broken **upward** → **BUY**
- Rounding bottom curvature broken **downward** → **SELL**

> *"Rounding patterns often provide very reliable trading signals. In this sense, the breaking of a curved price pattern can be viewed as transforming the pattern into a failed signal."*
> — Schwager, Ch. 11

---

## Simple Analogy: The River Bend

A river flowing through flat terrain naturally curves — it bends gradually in one direction, and everyone assumes it will keep bending that way. Maps are drawn, bridges planned, and settlements built based on this assumption.

Then suddenly, the river cuts straight ahead, ignoring the curve entirely. It carves a new channel. All the infrastructure built for the expected path is now worthless.

A rounding pattern is like that river bend — a gradual, organic curve that everyone expects to continue. Breaking the curvature is the river cutting a new channel. The more established the bend, the more disruptive the break.

---

## How Rounding Patterns Work (Ch 5 Review)

Rounding patterns represent a **gradual consensus shift**:

| Pattern | Description | Implication |
|---|---|---|
| **Rounding top** | Price gradually curves from rising to flat to falling — like an inverted bowl | Slow transition from bullish to bearish |
| **Rounding bottom** | Price gradually curves from falling to flat to rising — like a bowl/saucer | Slow transition from bearish to bullish |

Schwager's Ch 5 assessment:

> *"Rounded tops and rounded bottoms occur somewhat infrequently, but are among the most reliable top and bottom formations."*

The key criterion: the **outer perimeter** must conform to a rounding shape. Minor jags within the pattern are acceptable as long as the overall curvature holds.

---

## The Break

### Rounding Top Broken Upward → BUY

1. Price traces a smooth downward arc (rounding top forming)
2. Participants adapt to the gradual rollover — selling increases
3. Suddenly, price **breaks above** the expected curve trajectory
4. The gradual bearish transition has failed → strong BUY signal

### Rounding Bottom Broken Downward → SELL

1. Price traces a smooth upward arc (rounding bottom forming)
2. Participants adapt to the gradual recovery — buying increases
3. Suddenly, price **breaks below** the expected curve trajectory
4. The gradual bullish transition has failed → strong SELL signal

---

## What Makes This Unique Among Failed Signals

Breaking of curvature is the only failed signal type that involves a **gradual** original pattern. Every other failed signal in Chapter 11 involves a sharp event:

| Other Failed Signals | Original Pattern | Failure Speed |
|---|---|---|
| Bull/bear traps | Sharp breakout | Quick reversal |
| False trend line breakouts | Sharp penetration | Quick return |
| Filled gaps | One-day gap | Days to fill |
| Spike penetrations | One-day spike | Weeks/months |
| WRD penetrations | One-day WRD | Days to weeks |
| Flag counter breakouts | Brief consolidation | Days |
| Failed H&S / double tops | Multi-swing formation | Days to weeks |
| **Breaking of curvature** | **Gradual arc over weeks/months** | **Sudden break** |

This contrast — **slow setup, sudden failure** — is what gives the signal its power. When a slow, organic consensus is abruptly violated, the surprise is maximal.

---

## When This Concept Works Best

- **Well-formed rounding patterns**: The smoother the original curve (fewer jags, clearer arc), the more meaningful its break. A ragged, unclear "rounding" pattern carries less weight
- **After the curve has been established over many weeks**: Short-duration curves are less significant — the more time the curve has been forming, the more participants have adjusted to it
- **When the break is sharp and decisive**: A gradual deviation from the curve could just be the pattern evolving. A sharp, sudden break is the clear failed signal
- **Combined with volume expansion on the break**: Rising volume on the curvature break confirms genuine participation rather than a random fluctuation

---

## When to Be Cautious

- **Ambiguous rounding patterns**: Not every gradual price curve is a rounding pattern. If the curvature is unclear or the "outer perimeter" doesn't conform to a smooth shape, don't force the interpretation
- **Minor deviations vs. genuine breaks**: Rounding patterns can have "jags" within them (Schwager notes this in Ch 5). A minor deviation from the perfect arc may just be normal noise within the pattern
- **Subjectivity**: Rounding patterns are inherently more subjective than double tops or H&S. Where exactly does the curve break? This requires judgment — the Python implementation uses quadratic fitting and deviation thresholds, but real-world assessment involves visual evaluation
- **Rarity**: Schwager notes rounding patterns occur "somewhat infrequently." Their failure is rarer still

---

## Schwager's Key Example

### Canadian Dollar Continuous Futures (Figure 11.31)
The breaking of the curvature of what had been an apparent rounding top pattern represented a bullish signal. This is the only example Schwager provides for this concept — reflecting its relative rarity compared to other failed signal types. The brevity of his treatment suggests it's a pattern to recognize when it appears, rather than one to actively scan for.

---

## Cross-Chapter Links

- **[[Failed Signals — The Overarching Principle]]**: Breaking curvature is the final specific application in Schwager's catalog
- **[[Ch5 — Chart Patterns]]**: Defines rounding tops and bottoms as "among the most reliable formations" — the foundation that makes their failure meaningful
- **[[Penetration of Top and Bottom Formations]]**: The sister concept — both involve failure of formation-level patterns, but double tops/H&S are angular while rounding patterns are curved
- **[[Ch9 — Choosing Stop-Loss Points]]**: The curve's expected trajectory provides a natural reference for stop placement

---

## Python Implementation

See `curvature_break_detector.py`:
- `fit_rounding_pattern()` — fits a quadratic polynomial to highs (top) or lows (bottom), checks curvature direction and R² quality
- `detect_curvature_break()` — monitors bars beyond the fitted curve for significant deviation from the expected trajectory
- `scan_for_rounding_patterns()` — scans the data at various window sizes, deduplicates overlapping patterns, returns sorted by fit quality
- Uses quadratic regression: `price = a*x² + b*x + c` where the sign of `a` determines the curvature direction (negative = top, positive = bottom)

---

## Key Takeaway

Breaking of curvature is the most **aesthetically distinct** failed signal — it's the only one involving a smooth, organic original pattern. While Schwager treats it briefly (one example, one paragraph), the principle is powerful precisely because of the contrast: rounding patterns are gradual and reliable; their failure is sudden and shocking. Think of it as the quiet, steady drumbeat that everyone has been marching to suddenly stopping. The silence is louder than any crash. When you spot a well-formed rounding pattern breaking its curve, the signal quality is high — but the pattern is rare enough that it's a bonus rather than a bread-and-butter trading tool.
