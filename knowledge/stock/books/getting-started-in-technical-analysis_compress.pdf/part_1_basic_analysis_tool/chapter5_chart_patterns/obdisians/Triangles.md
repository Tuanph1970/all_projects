# Triangles

> Part of: [[Chapter_05_Chart_Patterns]] → Continuation Patterns (also tops/bottoms)

## Definition

A **triangle** is a multi-week consolidation in which the trading range narrows over time, drawing converging trendlines. Three classic forms:

| Type | Upper boundary | Lower boundary | Conventional bias |
|---|---|---|---|
| **Symmetrical** | Falling | Rising | Continuation of prior trend |
| **Ascending** | Flat | Rising | Bullish (slope of hypotenuse up) |
| **Descending** | Falling | Flat | Bearish (slope of hypotenuse down) |

**Schwager's caveat**: the *direction of breakout* matters more than the textbook type. He shows examples where a textbook-bearish descending triangle breaks *upward* — and you trade the breakout, not the textbook.

A triangle is most often a **continuation** pattern (Schwager places it in the continuation section), but it can also form at major tops or bottoms — the same shape, different context.

## Illustration

![[triangles_illustration.svg]]

## Analogy — A Crowd Squeezing Through a Doorway

Imagine a wide hallway that gradually narrows into a single doorway. People are pushing in from both sides. As the corridor tightens, individual movements become smaller — there's no room to swing — until everyone has to commit to one direction at the doorway. The moment they pour through the door, you know which way the crowd was actually leaning.

A triangle is that hallway. The narrowing range is the squeeze. The breakout is the doorway — and that's when you find out who was really winning the push.

## Numeric Example

A symmetrical triangle on a stock:

| Week | Swing High | Swing Low |
|---|---|---|
| 1 | 105.00 | 95.00 |
| 2 | 103.50 | 96.50 |
| 3 | 102.00 | 98.00 |
| 4 | 100.80 | 99.20 |
| **5** | **breakout: close 103.20** | — |

- Range narrowed from 10.00 → 1.60 over four weeks (classic compression)
- Triangle width at apex ≈ 1.60
- A close at 103.20 (above the upper trendline projected at ~101.80) → upside breakout
- Measured target: triangle widest part = 10.00, projected from breakout level → 101.80 + 10.00 = **111.80** target

## Python Code

```python
import numpy as np
import pandas as pd

def detect_triangle(df: pd.DataFrame, window: int = 30,
                   min_pivots: int = 4) -> dict:
    """
    Naive triangle detector: fit linear trendlines to recent highs and lows.
    Returns slopes; converging slopes (opposite signs or one ~ 0) indicate a triangle.
    """
    recent = df.iloc[-window:]
    x = np.arange(len(recent))

    # Identify swing highs/lows (very simple: local max/min in 5-bar window)
    rolling_max = recent["high"].rolling(5, center=True).max()
    rolling_min = recent["low"].rolling(5, center=True).min()
    pivot_highs = recent[recent["high"] == rolling_max]
    pivot_lows  = recent[recent["low"]  == rolling_min]

    if len(pivot_highs) < min_pivots // 2 or len(pivot_lows) < min_pivots // 2:
        return {"type": None}

    h_slope, h_int = np.polyfit(pivot_highs.index.map(recent.index.get_loc),
                                pivot_highs["high"].values, 1)
    l_slope, l_int = np.polyfit(pivot_lows.index.map(recent.index.get_loc),
                                pivot_lows["low"].values, 1)

    if abs(h_slope) < 1e-3 and l_slope > 0:
        kind = "ascending"
    elif h_slope < 0 and abs(l_slope) < 1e-3:
        kind = "descending"
    elif h_slope < 0 and l_slope > 0:
        kind = "symmetrical"
    else:
        kind = None

    return {"type": kind,
            "upper_slope": h_slope, "lower_slope": l_slope,
            "apex_x": (l_int - h_int) / (h_slope - l_slope) if h_slope != l_slope else None}


def triangle_breakout(df: pd.DataFrame, upper: float, lower: float) -> str | None:
    last = df.iloc[-1]
    if last["close"] > upper:  return "up"
    if last["close"] < lower:  return "down"
    return None


def measured_target(breakout_price: float, widest_height: float,
                    direction: str) -> float:
    return breakout_price + widest_height if direction == "up" \
           else breakout_price - widest_height
```

## Relationships

### Within Chapter 5

- **Versus [[Flags and Pennants]]**: pennants look like small triangles — but flags/pennants are *short* (1–3 weeks); triangles are longer. Different time scale, similar geometry.
- **Triangle Tops/Bottoms**: triangles can also serve as reversal patterns at trend extremes — same shape, but the prior context determines whether the breakout is continuation or reversal.
- **Confirmed by [[Thrust Days]]**: a thrust-day breakout from a triangle is more reliable than an intraday peek.
- **Strengthened by [[Wide-Ranging Days]]**: a wide-ranging breakout bar adds conviction.

### Outside Chapter 5

- **[[Chapter 04 - Trading Ranges and Support and Resistance]]** — a triangle is a special case of a contracting trading range; breakout logic is the same.
- **[[Chapter 09 - Choosing Stop-Loss Points]]** — natural stop is the *opposite trendline* or the apex of the triangle.
- **[[Chapter 10 - Setting Objectives]]** — measured-move target = triangle's widest height, projected from the breakout point.
- **[[Chapter 11 - The Most Important Rule]]** — false triangle breakouts (close back inside) are a textbook bull/bear trap.

### When does this concept work well?

- **Best**: long, well-defined triangles (≥6 weeks) with declining volume into the apex, breakout on rising volume and a wide-range thrust day.
- **Worst**: tiny triangles in choppy markets (these are just normal noise) or breakouts that happen *very late* near the apex (low energy).

#chart-patterns #continuation-pattern #reversal-pattern #triangles
