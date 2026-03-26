---
tags: [technical-analysis, schwager, continuation-pattern, triangles]
source: "Schwager - Getting Started in Technical Analysis, Chapter 5 pp.87-90, 104-105; Chapter 12 pp.181-182"
related: ["[[Continuation Patterns MOC]]", "[[Flags and Pennants]]", "[[Wedges]]", "[[Signal Frequency vs Reliability Trade-off]]"]
---

# Triangles

## Definition

A **triangle** is a congestion pattern in which prices gradually converge to a point. It's formed by connecting at least two swing highs (upper trendline) and two swing lows (lower trendline), where the lines converge rather than run parallel.

Triangles are among the **most common** continuation patterns, but they can also serve as top and bottom formations.

## The Three Types

### Symmetrical Triangle
- **Structure**: Both the upper trendline slopes down and the lower trendline slopes up, converging at roughly equal angles
- **Expected breakout**: In the direction of the **preceding trend** (continuation)
- **Analogy**: Two negotiators gradually moving toward a compromise. Both sides are giving ground equally. When one side finally walks away, they usually go back to where they came from — the prior trend resumes
- Schwager examples: Delta Air Lines (Fig 5.17), Swiss franc continuous futures (Fig 5.18)

### Ascending Triangle
- **Structure**: The upper boundary is roughly **flat** (horizontal resistance), while the lower trendline slopes upward (higher lows)
- **Conventional wisdom**: Breakout should follow the slope of the hypotenuse → **upward**
- **Analogy**: A crowd pushing against a locked door. Each push gets stronger (higher lows), but the door (resistance) stays put. Eventually the hinges give way and the crowd surges through
- Schwager examples: September 1992 Eurodollar (Fig 5.19), October 1992 sugar (Fig 5.20)

### Descending Triangle
- **Structure**: The lower boundary is roughly **flat** (horizontal support), while the upper trendline slopes downward (lower highs)
- **Conventional wisdom**: Breakout should follow the slope of the hypotenuse → **downward**
- **Analogy**: A floor supporting weight while the ceiling keeps dropping. Each rally is weaker than the last (lower highs), but the floor (support) holds. Eventually the floor cracks and prices fall through
- Schwager examples: Soybean oil continuous futures (Fig 5.21), soybean meal continuous futures (Fig 5.22)

## Schwager's Key Insight: Breakout Direction > Triangle Type

> The direction of the breakout from a triangle formation is **more important than the type**.

This is a critical distinction. Conventional wisdom says ascending triangles break up and descending triangles break down. Schwager disagrees — he prioritizes what actually happens over what the shape predicts.

**Example**: Figure 5.23 shows a **descending triangle** in Host Marriott Corp. that broke out to the **upside** — the same direction the triangle was entered (from below). The type said "down," the breakout said "up." Schwager sides with the breakout.

**Practical implication**: Don't pre-commit to a direction based on triangle type alone. Wait for the breakout, then trade in that direction.

## Triangles as Top/Bottom Formations

While triangles are primarily continuation patterns, they can also mark **major reversals**:

> Triangles, which are among the most common continuation patterns, can be top and bottom formations as well. — Schwager (p.104)

Figure 5.44 illustrates a **triangle top** in Intel. The key consideration remains the same: the direction of the breakout determines interpretation.

## The Triangle vs. Pennant Distinction

| Feature | Triangle | Pennant |
|---------|----------|---------|
| Duration | Longer (weeks to months) | Short (1–3 weeks) |
| Structure | Converging trendlines | Converging trendlines |
| Context | Can be continuation or reversal | Almost always continuation |

Pennants may *look* like triangles, but they differ in **time**. A short-duration converging pattern within a strong trend is a pennant; a longer-duration one is a triangle.

## Real-World Trading Lessons (Chapter 12)

### Trade 12.1: December 1993 T-bond
- **Entry**: Breakout above a triangular consolidation + pullback to the support level (internal trendline + top of triangle)
- **Exit**: Significant downside penetration of the lower end of the triangle invalidated the original premise
- **Lesson**: *"A trade should always be liquidated once the primary premise for the trade is violated."* Getting out early kept the loss small. Procrastination would have been very costly.

### Trade 12.4: December 1994 British pound
- **Entry**: Sustained upside breakout above triangle consolidation + pennant continuation
- **Strategy note**: Schwager originally placed a limit order within the triangle, anticipating the breakout. When price didn't reach the limit, he entered at market — salvaging the remaining profit potential rather than treating it as a "missed trade"
- **Exit**: Downside wide-ranging day after attaining a measured move objective

## Structural Components (For Algorithmic Detection)

A triangle requires:
1. **At least 2 swing highs** forming the upper trendline
2. **At least 2 swing lows** forming the lower trendline
3. **Convergence**: The trendlines must slope toward each other
4. **Sufficient width**: The pattern should span enough bars to be meaningful (Schwager implies at least 5 trading days for a continuation pattern)
5. **Prior trend context**: The preceding trend direction determines whether the triangle is interpreted as continuation or reversal

### Type Classification

| Condition | Type |
|-----------|------|
| Upper line slopes down AND lower line slopes up (roughly equal) | Symmetrical |
| Upper line is roughly flat AND lower line slopes up | Ascending |
| Lower line is roughly flat AND upper line slopes down | Descending |

## Python Detection

```python
import numpy as np
import pandas as pd


def find_swing_points(df: pd.DataFrame, order: int = 5) -> tuple:
    """
    Identify swing highs and swing lows.

    A swing high at index i means high[i] is the highest high
    in the window [i-order, i+order].

    Parameters
    ----------
    order : int
        Number of bars on each side to compare (requires future data).
    """
    swing_highs = []
    swing_lows = []

    for i in range(order, len(df) - order):
        window_highs = df['high'].iloc[i - order:i + order + 1]
        window_lows = df['low'].iloc[i - order:i + order + 1]

        if df['high'].iloc[i] == window_highs.max():
            swing_highs.append((df.index[i], df['high'].iloc[i]))
        if df['low'].iloc[i] == window_lows.min():
            swing_lows.append((df.index[i], df['low'].iloc[i]))

    return swing_highs, swing_lows


def fit_trendline(points: list) -> tuple:
    """
    Fit a linear regression through a list of (date, price) points.
    Returns (slope_per_bar, intercept, r_squared).
    """
    if len(points) < 2:
        return None, None, 0.0

    # Convert dates to numeric indices
    x = np.arange(len(points), dtype=float)
    y = np.array([p[1] for p in points])

    coeffs = np.polyfit(x, y, 1)
    slope, intercept = coeffs[0], coeffs[1]

    # R-squared
    y_pred = np.polyval(coeffs, x)
    ss_res = np.sum((y - y_pred) ** 2)
    ss_tot = np.sum((y - np.mean(y)) ** 2)
    r_sq = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0.0

    return slope, intercept, r_sq


def detect_triangles(df: pd.DataFrame, swing_order: int = 5,
                     min_points: int = 2, min_bars: int = 10,
                     convergence_threshold: float = 0.0,
                     r_sq_min: float = 0.7) -> list:
    """
    Detect triangle patterns from OHLC data.

    Logic:
    1. Find swing highs and swing lows
    2. For sliding windows of swing points, fit upper and lower trendlines
    3. Check if the lines converge (slopes point toward each other)
    4. Classify the triangle type based on slope characteristics

    Parameters
    ----------
    swing_order : int
        Bars on each side for swing point detection
    min_points : int
        Minimum touches required per trendline
    min_bars : int
        Minimum duration of the pattern in bars
    convergence_threshold : float
        A slope is "flat" if abs(slope) < this value
        (set relative to price scale, e.g., 0.05 * ADTR)
    r_sq_min : float
        Minimum R-squared for trendline fit quality

    Returns
    -------
    list of dict with triangle metadata
    """
    swing_highs, swing_lows = find_swing_points(df, swing_order)

    triangles = []

    # Sliding window over swing points
    for i in range(len(swing_highs) - min_points + 1):
        upper_points = swing_highs[i:i + min_points + 2]

        # Find contemporaneous swing lows
        start_date = upper_points[0][0]
        end_date = upper_points[-1][0]
        lower_points = [
            p for p in swing_lows
            if start_date <= p[0] <= end_date
        ]

        if len(lower_points) < min_points:
            continue

        upper_slope, upper_int, upper_r2 = fit_trendline(upper_points)
        lower_slope, lower_int, lower_r2 = fit_trendline(lower_points)

        if upper_slope is None or lower_slope is None:
            continue
        if upper_r2 < r_sq_min or lower_r2 < r_sq_min:
            continue

        # Check convergence: upper slopes down, lower slopes up
        # (or at least they point toward each other)
        if upper_slope >= lower_slope:
            continue  # Lines diverge or are parallel — not a triangle

        # Duration check
        start_idx = df.index.get_loc(start_date)
        end_idx = df.index.get_loc(end_date)
        if (end_idx - start_idx) < min_bars:
            continue

        # Classify type
        flat_threshold = convergence_threshold
        upper_flat = abs(upper_slope) < flat_threshold
        lower_flat = abs(lower_slope) < flat_threshold

        if upper_flat and not lower_flat:
            tri_type = 'ascending'
        elif lower_flat and not upper_flat:
            tri_type = 'descending'
        else:
            tri_type = 'symmetrical'

        triangles.append({
            'start_date': start_date,
            'end_date': end_date,
            'type': tri_type,
            'upper_slope': upper_slope,
            'lower_slope': lower_slope,
            'upper_r2': upper_r2,
            'lower_r2': lower_r2,
            'duration_bars': end_idx - start_idx,
            'upper_touches': len(upper_points),
            'lower_touches': len(lower_points),
        })

    return triangles


def detect_triangle_breakout(df: pd.DataFrame, triangle: dict,
                              lookforward: int = 10) -> dict | None:
    """
    After detecting a triangle, check if a breakout occurred.

    A breakout is confirmed when the close moves beyond
    the projected trendline value.
    """
    end_idx = df.index.get_loc(triangle['end_date'])
    
    for i in range(end_idx + 1,
                   min(end_idx + 1 + lookforward, len(df))):
        curr = df.iloc[i]
        bars_from_start = i - df.index.get_loc(triangle['start_date'])

        # Project trendline values at this bar
        # (simplified — uses slope × bars_elapsed)
        proj_upper = (triangle['upper_slope'] * bars_from_start
                      + df.loc[triangle['start_date'], 'high'])
        proj_lower = (triangle['lower_slope'] * bars_from_start
                      + df.loc[triangle['start_date'], 'low'])

        if curr['close'] > proj_upper:
            return {
                'breakout_date': df.index[i],
                'direction': 'up',
                'breakout_price': curr['close'],
            }
        elif curr['close'] < proj_lower:
            return {
                'breakout_date': df.index[i],
                'direction': 'down',
                'breakout_price': curr['close'],
            }

    return None
```

## Trading Decision Framework

```
Triangle detected
     │
     ├─ Wait for breakout (don't pre-commit based on type)
     │
     ├─ Breakout occurs
     │      │
     │      ├─ Direction matches prior trend? → Continuation trade
     │      │     • Stop: opposite side of triangle
     │      │     • Target: measured move from triangle width
     │      │
     │      └─ Direction opposes prior trend? → Potential reversal
     │            • Higher conviction if triangle appears after
     │              extended move (top/bottom formation)
     │            • Stop: same — opposite side of triangle
     │
     └─ No breakout (price drifts toward apex)
            • Pattern loses significance as apex approaches
            • Eventually the triangle "expires"
```

## Connections

- [[Flags and Pennants]] — shorter-duration version of the same convergence concept
- [[Wedges]] — similar converging structure, but both lines slope in the same direction
- Chapter 11 failed signals — a breakout from a triangle that fails and reverses is a powerful signal in the opposite direction
- Chapter 12 (Trade 12.1) — real-world triangle trade with entry, exit, and lessons learned
