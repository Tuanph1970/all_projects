# Relative Highs and Relative Lows

## Description

The foundational primitive of Chapter 3. A **Relative High (RH)** is a daily high that is higher than the highs of the preceding N days and succeeding N days. A **Relative Low (RL)** is a daily low that is lower than the lows of the preceding N days and succeeding N days. Schwager recommends N between 5 and 15.

These are the anchor points that all other trend concepts build upon — [[02 - Uptrend and Downtrend]] definition, [[03 - Conventional Trend Lines]], [[05 - TD Lines (DeMark)]], [[06 - Trend Channels]], and stop placement (Ch.9).

## Simple Analogy

Think of a mountain range seen from an airplane. The **peaks** are Relative Highs — each one is higher than the surrounding terrain for some distance in both directions. The **valleys** are Relative Lows — each one is lower than the surrounding terrain. The parameter N controls how far you look in each direction: N=5 picks up small foothills, N=15 only detects major peaks and valleys.

The key constraint: you can't confirm a peak until you've walked N steps past it and verified the terrain dropped. That's the inherent **lag** — you always identify swing points after the fact.

## Formal Definition

```
RH at bar i:  high[i] > high[j]  for all j in [i-N, i+N], j ≠ i
RL at bar i:  low[i]  < low[j]   for all j in [i-N, i+N], j ≠ i
```

**Parameter N trade-off:**
- ↑N = fewer, more significant points, more lag
- ↓N = more points, noisier, less lag

## Illustration

**Interactive simulation:** `assets/simulations/swing_points_detector.jsx`
- Adjustable N slider showing RH/RL detection on synthetic price data
- Shows the N-bar "blind zone" on each end (lag visualization)
- Displays the RH/RL sequence with trend classification

## Python Code

**File:** `assets/code/trend_lines.py` → function `detect_swing_points()`

```python
def detect_swing_points(df: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    """
    Schwager's definition (Glossary p.329):
    RH at bar i: high[i] > high[j] for all j in [i-n, i+n], j != i
    RL at bar i: low[i]  < low[j]  for all j in [i-n, i+n], j != i
    """
    highs = df["high"].values
    lows = df["low"].values
    length = len(df)
    is_rh = np.zeros(length, dtype=bool)
    is_rl = np.zeros(length, dtype=bool)

    for i in range(n, length - n):
        window_highs = highs[i - n : i + n + 1]
        window_lows = lows[i - n : i + n + 1]
        if highs[i] == np.max(window_highs) and np.sum(window_highs == highs[i]) == 1:
            is_rh[i] = True
        if lows[i] == np.min(window_lows) and np.sum(window_lows == lows[i]) == 1:
            is_rl[i] = True

    result = df.copy()
    result["is_rh"] = is_rh
    result["is_rl"] = is_rl
    return result
```

## Connections

- **Used by:** [[02 - Uptrend and Downtrend]], [[03 - Conventional Trend Lines]], [[05 - TD Lines (DeMark)]], [[06 - Trend Channels]], [[10 - Trend Line Redrawing]]
- **Source:** Schwager Glossary p.329, Ch.9 footnote p.139

---
*Tags: #foundation #schwager-ch3 #codeable*
