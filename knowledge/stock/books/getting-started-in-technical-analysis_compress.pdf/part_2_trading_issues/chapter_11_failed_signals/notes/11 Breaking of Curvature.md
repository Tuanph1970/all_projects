# 11 Breaking of Curvature

**Parent:** [[00 Chapter 11 Index]] · **Master:** [[01 Failed Signals]]
**Tags:** #chapter11 #failed-signal #rounding

## Definition

Rounding patterns — rounding tops, rounding bottoms (saucers) — are among the most reliable reversal patterns in technical analysis precisely because they describe a *gradual change of sentiment* rather than a single sharp event. A **breaking of curvature** is the failed-signal version: when prices push *outside* the implied curved shape, the rounding interpretation is invalidated and a continuation in the direction of the break is likely.

Concretely, if a chart appears to be tracing out a rounding top (a slow downward arc), an unexpected rally that takes price clearly above the projected curve breaks the curvature → bullish signal. The same logic mirrors for rounding bottoms broken to the downside.

## Illustration

![[11_breaking_curvature.png]]

The book's **Figure 11.31** (Canadian dollar continuous futures) shows a textbook example: an apparent rounding-top pattern that is broken to the upside, repudiating the bearish curvature read.

## Common-life analogy

You watch a long road trip on a map and see the route is shaped like a wide arc — the driver seems headed slowly back home (rounding top). For weeks each day's drive nudges the arc closer to home. Then one morning they post a photo from a city *farther* than they've ever been from home. The arc is broken — they weren't winding back, they were just taking the scenic route, and now you can predict they'll keep heading further out.

## Numeric example

Over six months a stock traces a slow rounding top: peaking at $80, drifting down to $76, then $74, $72, $70 — a clean parabolic shape suggesting a deeper decline. A least-squares fit on the closes of those six months gives the parabola:

```
close ≈ -0.02 * (day - 90)² + 80
```

Projected close for day 200 = ~$56. But on day 200 the actual close prints **$72** — well above the projected $56 (and above the recent local highs around $70). The curvature has broken.

Trade plan: long at $72 with stop just below the recent reaction low ($68). Risk = $4. If the curvature break presages a return to the prior peak, $80 is the immediate target — 2:1 reward-to-risk.

## Python sketch

```python
import numpy as np

def fit_curve(closes, start, end):
    """Fit y = a*x² + b*x + c on closes[start:end]; return (a, b, c)."""
    x = np.arange(end - start)
    y = closes[start:end]
    return np.polyfit(x, y, 2)

def curvature_break(closes, start, end, pattern="top",
                    lookahead=30, tolerance=0.02):
    """Yield first close whose projected curve is violated by `tolerance`."""
    a, b, c = fit_curve(closes, start, end)
    for j in range(end, min(end + lookahead, len(closes))):
        x = j - start
        proj = a*x*x + b*x + c
        actual = closes[j]
        if pattern == "top" and actual > proj * (1 + tolerance):
            return j
        if pattern == "bottom" and actual < proj * (1 - tolerance):
            return j
    return None
```

Full version: `code/chapter11_detectors.py` → `detect_curvature_break()`.

## Relationships within the chapter

- The **curvilinear sibling** of [[10 Penetration of Top and Bottom Formations]] — both describe a major reversal pattern getting repudiated. The H&S/double-top concept uses *discrete* reference points (right shoulder, top high); curvature uses a *continuous* projected line.
- Both depend on [[01 Failed Signals]] as the master concept and use [[03 Confirmation Conditions]] (typically the "strong" form: a clear close outside the projected curve, sometimes with a percentage tolerance).
- Conceptually, this is the most **subjective** failed-signal type in the chapter — drawing the curve is a visual judgement, much like drawing trend lines in [[04 False Trend Line Breakouts]]. The same caution applies.

## When the concept works best

- **Long, smooth, multi-month rounding patterns.** A two-week mini-arc shouldn't be treated as a real curvature; the longer and cleaner the arc, the more meaningful its violation.
- **Charts where you can identify the curve before the break.** If you only "see the rounding" *after* the break has already occurred, you're hindsight-fitting.
- **In conjunction with another failure type.** A curvature break that coincides with a [[05 Filled Gaps]] event or a [[07 Return to Wide-Ranging Day Extremes]] failure stacks evidence and produces the strongest trades.

## Relationships outside the chapter

- Rounding tops, rounding bottoms (saucers): [[Chapter 5 - Chart Patterns]].
- Curve-fitting connects to the trend-line and moving-average framing in [[Chapter 3 - Trends]] — both are smoothings of price; one linear, one quadratic.
- The "curvature" framing also resonates with the **cup-and-handle** pattern referenced in [[Chapter 17 - Eighty-Two Trading Rules]] (rule #74).
