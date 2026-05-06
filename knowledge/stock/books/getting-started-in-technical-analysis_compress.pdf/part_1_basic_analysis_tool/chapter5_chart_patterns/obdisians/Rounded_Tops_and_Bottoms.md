# Rounded Tops and Bottoms

> Part of: [[Chapter_05_Chart_Patterns]] → Top and Bottom Formations

## Definition

**Rounded tops** (also called *saucer tops*) and **rounded bottoms** (*saucer bottoms*) are slow, gradual reversal formations in which price traces out the curved outer perimeter of a shallow bowl — convex on a top, concave on a bottom.

These patterns are uncommon but, when they form, are among the **most reliable** reversal signals. The reliability stems from their character: a rounding shape implies a *gradual, broad-based shift in market sentiment*, not a panic or a single news shock. By the time the pattern is visible, conviction in the prior trend has been quietly eroded over weeks or months.

The pattern doesn't need to be perfectly smooth — small jagged spikes inside don't disqualify it as long as the overall outer boundary traces a curve.

## Illustration

![[rounded_top_bottom_illustration.svg]]

## Analogy — A Train Coming to a Stop

Picture a freight train traveling at full speed. It can't stop instantly — physics won't allow it. But you can see the engineer cut the throttle: the engine note drops, then the brakes squeeze gently, then more firmly. The train decelerates, hesitates at almost-stopped, then reverses just slightly. There's no single dramatic moment — just a gradual, irreversible change of state.

A rounded top is that train. By the time you can clearly see the deceleration, you know the direction will reverse. The pattern's slow nature is what makes it so trustworthy: it took *all those weeks* of buyer fatigue to bend the trend, and that exhaustion doesn't come back overnight.

## Numeric Example

A weekly chart on a stock making a rounded top:

| Week | High | Notes |
|---|---|---|
| W1  | 80.20 | Climbing |
| W6  | 92.50 | Acceleration |
| W11 | 99.10 | Approaching peak |
| W14 | 101.20 | Plateau begins |
| W17 | 100.80 | Sideways |
| W22 | 98.40 | Slight decline |
| W28 | 92.10 | Acceleration down |
| W34 | 80.10 | Mirror of W1 |

The chart traces a near-symmetric arc over ~34 weeks. There's no single dramatic top day; the change of leadership is gradual.

A useful diagnostic: fit a parabola to the highs over a window. If R² > 0.85 and the parabola's coefficient is negative (open-down → top), the pattern is strong.

## Python Code

```python
import numpy as np
import pandas as pd

def detect_rounding(df: pd.DataFrame, window: int = 60,
                   r2_threshold: float = 0.85) -> dict | None:
    """
    Fit a parabola to recent highs (for tops) or lows (for bottoms).
    Returns the type and goodness-of-fit if R^2 exceeds threshold.
    """
    if len(df) < window:
        return None
    recent = df.iloc[-window:]
    x = np.arange(window)

    def fit(y):
        coeffs = np.polyfit(x, y, 2)
        y_hat = np.polyval(coeffs, x)
        ss_res = np.sum((y - y_hat) ** 2)
        ss_tot = np.sum((y - np.mean(y)) ** 2)
        r2 = 1 - ss_res / ss_tot if ss_tot else 0.0
        return coeffs, r2

    h_coeffs, h_r2 = fit(recent["high"].values)
    l_coeffs, l_r2 = fit(recent["low"].values)

    if h_coeffs[0] < 0 and h_r2 >= r2_threshold:
        return {"type": "rounding_top", "r2": h_r2, "coeffs": h_coeffs}
    if l_coeffs[0] > 0 and l_r2 >= r2_threshold:
        return {"type": "rounding_bottom", "r2": l_r2, "coeffs": l_coeffs}
    return None


def break_of_curvature(df: pd.DataFrame, fitted_curve: np.ndarray,
                       sigma_threshold: float = 2.0) -> bool:
    """
    Schwager: a 'break of curvature' is when prices abruptly violate the
    rounding boundary. Useful both as the entry trigger and (Ch.11) as a failed-signal indicator.
    """
    residuals = df["close"].values[-len(fitted_curve):] - fitted_curve
    return abs(residuals[-1]) > sigma_threshold * residuals[:-1].std()
```

## Relationships

### Within Chapter 5

- **Opposite of [[V Tops and Bottoms]]**: V is instant reversal; rounding is gradual reversal. Different time signatures, very different reliability profiles.
- **Combines with [[Triangles|triangle]] / [[Wedges|wedge]] late in the formation** — sometimes the rounding ends with a small descending triangle or wedge that resolves downward.
- **Confirmed by [[Thrust Days]]** breaking the curve on the way out.

### Outside Chapter 5

- **[[Chapter 03 - Trends]]** — rounding is essentially a slow trend transition without a single pivot point.
- **[[Chapter 11 - The Most Important Rule]]** — Schwager treats "breaking of curvature" as a major *failed-signal* category: if a clear rounding pattern is sharply violated in the opposite direction, that violation is itself a strong signal in the breakout direction. Failed rounding tops can be very bullish; failed rounding bottoms very bearish.
- **[[Chapter 10 - Setting Objectives]]** — projection is less mechanical than other patterns; depth of the prior bowl gives a rough magnitude.

### When does this concept work well?

- **Best**: weekly or monthly charts; over many months; in liquid, large-cap names where sentiment shifts slowly.
- **Worst**: short-term charts in volatile names — too much noise to fit a clean curve.

#chart-patterns #reversal-pattern #rounded-top #rounded-bottom #saucer
