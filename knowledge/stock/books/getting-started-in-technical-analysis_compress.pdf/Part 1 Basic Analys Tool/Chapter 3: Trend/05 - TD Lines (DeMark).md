# TD Lines (DeMark)

## Description

Thomas DeMark's method for drawing trend lines **objectively**. Connect exactly two points: for uptrend lines, the most recent RL and the most recent preceding *lower* RL; for downtrend lines, the most recent RH and the most recent preceding *higher* RH.

The "lower/higher" constraint ensures the line's slope matches the expected trend direction and confirms the higher-lows (or lower-highs) pattern is intact. Lines automatically redraw as new swing points form — solving the [[10 - Trend Line Redrawing|redrawing problem]] by making it a feature rather than a bug.

Schwager (p.41): "By basing trend line definitions on the most recent relative highs and lows, trend lines will be continually redefined as new relative highs and lows occur."

## Simple Analogy

Imagine a relay race where each runner must be faster than the previous one (the "lower/higher" rule). The TD Line is always drawn between the current runner and the most recent qualifying predecessor. When a new faster runner joins, the line updates. You don't need a referee to decide which runners count — the rule is explicit. That's the objectivity advantage over [[03 - Conventional Trend Lines]].

## Algorithm

```
TD Uptrend Line:
1. Detect all RLs with parameter N
2. Start from the most recent RL (call it RL_current)
3. Walk backward through previous RLs
4. Find the first RL where price < RL_current price (call it RL_previous)
5. Connect RL_previous → RL_current → extend forward

TD Downtrend Line:
1. Detect all RHs with parameter N
2. Start from the most recent RH (RH_current)
3. Walk backward to find the first RH where price > RH_current
4. Connect RH_previous → RH_current → extend forward
```

**N parameter trade-off** (Schwager p.42, comparing Figures 3.13 and 3.14):
- N=4: more RLs qualify, frequent lines, faster signals, more noise
- N=8: fewer RLs qualify, fewer lines, more significant, slower signals

## Illustration

**Chart:** `assets/charts/trend_lines_comparison.png` (panel 3 of 6)

**Interactive simulation:** `assets/simulations/td_lines_stepper.jsx`
- 6-step walkthrough: detect RLs → find most recent → walk back → draw line → show previous line → N trade-off

**Book references:** Figures 3.13 (N=8, Swiss franc), 3.14 (N=4, Swiss franc)

## Python Code

**File:** `assets/code/trend_lines.py` → function `td_trend_lines()`

```python
def td_trend_lines(df, n=8) -> list[TrendLine]:
    """
    DeMark's rule: connect most recent RL to most recent
    preceding LOWER RL (uptrend) or most recent RH to most
    recent preceding HIGHER RH (downtrend).
    """
    data = detect_swing_points(df, n)
    # Find most recent RL, walk backward for lower one
    # Find most recent RH, walk backward for higher one
    ...
```

## Connections

- **Depends on:** [[01 - Relative Highs and Relative Lows]]
- **Solves:** Subjectivity problem of [[03 - Conventional Trend Lines]]
- **Compare with:** [[04 - Internal Trend Lines]] (opposite philosophy — TD anchors to extremes, internal ignores them)
- **Limitation:** Only 2 anchor points (no "multiple touch" confirmation), N parameter still subjective
- **Source:** Schwager pp.41-42, referencing DeMark "The New Science of Technical Analysis" (1994)

---
*Tags: #trend-line #objective #schwager-ch3 #codeable #parametric*
