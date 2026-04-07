# Uptrend and Downtrend

## Description

The most basic trend definition. An **uptrend** is a succession of higher highs and higher lows — each [[01 - Relative Highs and Relative Lows|RH]] is higher than the preceding RH, and each RL is higher than the preceding RL. A **downtrend** is a succession of lower highs and lower lows.

An uptrend is considered intact until a previous RL (reaction low) is broken. A downtrend is intact until a previous RH is exceeded. Schwager emphasizes this should be viewed as a "clue, not absolute proof" of reversal.

## Simple Analogy

Think of the chart as **breathing**. Each inhale (rally) peaks at an RH; each exhale (decline) bottoms at an RL. In an uptrend, each breath reaches higher than the last — the organism is gaining altitude. In a downtrend, each breath sinks lower. When a breath fails to reach higher (uptrend) or fails to sink lower (downtrend), the rhythm has broken — the first warning that the pattern may be changing.

## Formal Definition

```
Uptrend:   RH₁ < RH₂ < RH₃ ...  AND  RL₁ < RL₂ < RL₃ ...
Downtrend: RH₁ > RH₂ > RH₃ ...  AND  RL₁ > RL₂ > RL₃ ...

Uptrend warning:   price penetrates the most recent RL
Downtrend warning:  price exceeds the most recent RH
```

## Illustration

**Chart reference:** Schwager Figure 3.1 (Eurodollar uptrend), Figure 3.3 (Coffee downtrend)

The Figure 3.3 Coffee chart shows the complete downtrend sequence with each RH and RL labeled, culminating in the "Downtrend pattern broken" annotation where price finally exceeds a previous RH.

**Interactive simulation:** `assets/simulations/swing_points_detector.jsx`
- The "RH/RL Sequence → Trend Classification" panel at the bottom shows the higher/lower pattern with color-coded arrows

## Python Code

**File:** `assets/code/trend_lines.py` → function `classify_trend()` (embedded in swing point detector)

```python
def classify_trend(data, relativeHighs, relativeLows):
    allPoints = [
        *[{"idx": i, "type": "RH", "price": data[i].high} for i in relativeHighs],
        *[{"idx": i, "type": "RL", "price": data[i].low} for i in relativeLows],
    ]
    allPoints.sort(key=lambda p: p["idx"])
    # Compare consecutive RHs and consecutive RLs
    # Higher High / Lower High, Higher Low / Lower Low
```

## Connections

- **Depends on:** [[01 - Relative Highs and Relative Lows]]
- **Used by:** [[03 - Conventional Trend Lines]], [[05 - TD Lines (DeMark)]], [[07 - Trend Line Rules]], [[11 - False Penetrations]]
- **Source:** Schwager pp.33-34

---
*Tags: #definition #schwager-ch3 #trend-structure*
