"""
Concept 7: Internal Trend Line.

From Schwager Ch.3, p.42-44:

    "Conventional trend lines are typically drawn to encompass extreme
    highs and lows. An argument can be made, however, that extreme
    highs and lows represent emotional excesses in the market, and as
    such may not represent the dominant trend in the market."

An internal trend line is a line that best approximates the MAJORITY
of relative highs or relative lows, ignoring the extreme outliers.
The trade-off vs. conventional lines: more representative of the
"core" trend, but more subjective. Schwager reports they often define
support/resistance better in his experience.

Implementation: linear regression through pivot points, with optional
outlier trimming.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Tuple
import statistics


@dataclass
class InternalLine:
    intercept: float
    slope: float
    used_indices: List[int]   # which pivots were kept after trimming
    rejected_indices: List[int]

    def value_at(self, x: int) -> float:
        return self.intercept + self.slope * x


def _ols(xs: List[int], ys: List[float]) -> Tuple[float, float]:
    """Ordinary least squares: returns (intercept, slope)."""
    n = len(xs)
    mx = sum(xs) / n
    my = sum(ys) / n
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    den = sum((x - mx) ** 2 for x in xs)
    if den == 0:
        return my, 0.0
    slope = num / den
    intercept = my - slope * mx
    return intercept, slope


def fit_internal_line(prices: List[float],
                      pivot_indices: List[int],
                      trim_outliers_z: float = 1.5) -> InternalLine:
    """Fit a line through pivots, trimming residual outliers (extreme excursions).

    Two-pass:
      1. Initial OLS through all pivot points.
      2. Drop points whose residual z-score exceeds `trim_outliers_z`.
      3. Refit OLS through the surviving points.

    Args:
        prices: full price series (e.g. closes, lows, or highs).
        pivot_indices: bar indices of the pivot points to fit.
        trim_outliers_z: z-score cutoff for residuals; e.g. 1.5 trims the
            obvious extreme spikes that "represent emotional excesses".
    """
    if len(pivot_indices) < 2:
        raise ValueError("Need at least 2 pivots")

    xs = pivot_indices
    ys = [prices[i] for i in xs]
    intercept, slope = _ols(xs, ys)

    residuals = [y - (intercept + slope * x) for x, y in zip(xs, ys)]
    sigma = statistics.pstdev(residuals) or 1e-9
    keep = [i for i, r in enumerate(residuals) if abs(r / sigma) <= trim_outliers_z]
    drop = [xs[i] for i in range(len(xs)) if i not in keep]

    if len(keep) >= 2:
        kxs = [xs[i] for i in keep]
        kys = [ys[i] for i in keep]
        intercept, slope = _ols(kxs, kys)
        used = kxs
    else:
        used = xs

    return InternalLine(intercept=intercept, slope=slope,
                        used_indices=used, rejected_indices=drop)


if __name__ == "__main__":
    import random
    random.seed(3)
    n = 80
    closes = [50 + 0.3 * i + random.gauss(0, 0.5) for i in range(n)]
    # inject one extreme low pivot (emotional excess)
    closes[20] -= 5.0

    pivots = [10, 20, 30, 45, 60, 72]   # the relative lows we'd identify

    line = fit_internal_line(closes, pivots, trim_outliers_z=1.0)
    print(f"Slope: {line.slope:.4f}, Intercept: {line.intercept:.2f}")
    print(f"Pivots kept:     {line.used_indices}")
    print(f"Pivots rejected: {line.rejected_indices}")
    print(f"Line at bar 0: {line.value_at(0):.2f}")
    print(f"Line at bar 79: {line.value_at(79):.2f}")
