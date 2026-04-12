"""
Breaking of Curvature Detector — Chapter 11, Concept 12
=========================================================
Rounding patterns (tops and bottoms) are among the most reliable
formations. When the smooth curvature is broken — price suddenly
deviates from the arc — the rounding pattern becomes a failed signal.

- Rounding top curvature broken upward → BUY
- Rounding bottom curvature broken downward → SELL

This is the most "organic" failed signal: rounding patterns represent
gradual consensus shifts, so their abrupt failure carries maximum
surprise value.

Schwager: "Rounding patterns often provide very reliable trading signals.
In this sense, the breaking of a curved price pattern can be viewed as
transforming the pattern into a failed signal."

Key example: Canadian dollar continuous futures (Fig 11.31) — breaking
the curvature of an apparent rounding top = bullish signal.
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class RoundingType(Enum):
    TOP = "rounding_top"
    BOTTOM = "rounding_bottom"


@dataclass
class RoundingPattern:
    """A detected rounding top or bottom pattern."""
    rounding_type: RoundingType
    start_idx: int
    apex_idx: int              # Highest point (top) or lowest point (bottom)
    current_end_idx: int       # Where the curve currently extends to
    apex_price: float
    curvature_quality: float   # R-squared of polynomial fit (0-1)
    fitted_coefficients: tuple # Quadratic coefficients (a, b, c)

    def expected_price_at(self, idx: int) -> float:
        """Price the curve would predict at a given bar index."""
        a, b, c = self.fitted_coefficients
        return a * idx**2 + b * idx + c


@dataclass
class CurvatureBreak:
    """A confirmed break of curvature — the failed signal."""
    pattern: RoundingPattern
    break_date: pd.Timestamp
    break_bar_idx: int
    break_price: float            # Actual close at break
    expected_price: float         # Where the curve predicted price would be
    deviation: float              # How far price deviated from the curve
    trade_direction: str          # 'long' for broken rounding top, 'short' for bottom


def fit_rounding_pattern(
    df: pd.DataFrame,
    start_idx: int,
    end_idx: int,
    rounding_type: RoundingType,
    min_r_squared: float = 0.6,
) -> Optional[RoundingPattern]:
    """
    Fit a quadratic curve to price data and check if it forms a rounding
    pattern with sufficient quality.

    For rounding top: fits to highs, quadratic opens downward (a < 0)
    For rounding bottom: fits to lows, quadratic opens upward (a > 0)

    Parameters
    ----------
    df : DataFrame with ['high', 'low', 'close']
    start_idx, end_idx : range to fit
    rounding_type : TOP or BOTTOM
    min_r_squared : minimum fit quality

    Returns
    -------
    RoundingPattern or None
    """
    if end_idx - start_idx < 15:
        return None

    indices = np.arange(start_idx, end_idx + 1)

    if rounding_type == RoundingType.TOP:
        prices = df.iloc[start_idx:end_idx + 1]['high'].values
    else:
        prices = df.iloc[start_idx:end_idx + 1]['low'].values

    # Fit quadratic: price = a*x^2 + b*x + c
    coeffs = np.polyfit(indices, prices, 2)
    a, b, c = coeffs

    # Check curvature direction
    if rounding_type == RoundingType.TOP and a >= 0:
        return None  # Must open downward for a top
    if rounding_type == RoundingType.BOTTOM and a <= 0:
        return None  # Must open upward for a bottom

    # Calculate R-squared
    fitted = np.polyval(coeffs, indices)
    ss_res = np.sum((prices - fitted) ** 2)
    ss_tot = np.sum((prices - np.mean(prices)) ** 2)
    r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

    if r_squared < min_r_squared:
        return None

    # Find apex
    apex_x = -b / (2 * a)
    apex_idx_int = int(round(apex_x))
    apex_idx_int = max(start_idx, min(end_idx, apex_idx_int))
    apex_price = np.polyval(coeffs, apex_idx_int)

    return RoundingPattern(
        rounding_type=rounding_type,
        start_idx=start_idx,
        apex_idx=apex_idx_int,
        current_end_idx=end_idx,
        apex_price=apex_price,
        curvature_quality=round(r_squared, 3),
        fitted_coefficients=(a, b, c),
    )


def detect_curvature_break(
    df: pd.DataFrame,
    pattern: RoundingPattern,
    deviation_threshold: float = 0.03,
    scan_bars: int = 20,
) -> Optional[CurvatureBreak]:
    """
    Check if the curvature of a rounding pattern is broken.

    Monitors bars after the pattern's current end for price deviating
    significantly from the expected curve trajectory.

    For rounding top: close significantly ABOVE the expected curve → BUY
    For rounding bottom: close significantly BELOW the expected curve → SELL

    Parameters
    ----------
    df : DataFrame with price data
    pattern : RoundingPattern object
    deviation_threshold : minimum deviation as fraction of price
    scan_bars : bars after pattern end to scan

    Returns
    -------
    CurvatureBreak or None
    """
    scan_end = min(pattern.current_end_idx + scan_bars, len(df))

    for i in range(pattern.current_end_idx + 1, scan_end):
        bar = df.iloc[i]
        expected = pattern.expected_price_at(i)

        if expected <= 0:
            continue

        if pattern.rounding_type == RoundingType.TOP:
            # Rounding top: expect price to curve down
            # Break = close significantly above expected curve
            deviation = (bar['close'] - expected) / expected
            if deviation > deviation_threshold:
                return CurvatureBreak(
                    pattern=pattern,
                    break_date=df.index[i],
                    break_bar_idx=i,
                    break_price=bar['close'],
                    expected_price=round(expected, 2),
                    deviation=round(deviation, 4),
                    trade_direction='long',
                )

        elif pattern.rounding_type == RoundingType.BOTTOM:
            # Rounding bottom: expect price to curve up
            # Break = close significantly below expected curve
            deviation = (expected - bar['close']) / expected
            if deviation > deviation_threshold:
                return CurvatureBreak(
                    pattern=pattern,
                    break_date=df.index[i],
                    break_bar_idx=i,
                    break_price=bar['close'],
                    expected_price=round(expected, 2),
                    deviation=round(deviation, 4),
                    trade_direction='short',
                )

    return None


def scan_for_rounding_patterns(
    df: pd.DataFrame,
    min_length: int = 20,
    max_length: int = 60,
    step: int = 5,
    min_r_squared: float = 0.6,
) -> list[RoundingPattern]:
    """
    Scan the data for rounding top and bottom patterns at various
    window sizes.

    Returns
    -------
    List of RoundingPattern objects, sorted by curvature quality
    """
    patterns = []

    for length in range(min_length, min(max_length, len(df)), step):
        for start in range(0, len(df) - length, step):
            end = start + length

            for rt in [RoundingType.TOP, RoundingType.BOTTOM]:
                rp = fit_rounding_pattern(
                    df, start, end, rt, min_r_squared
                )
                if rp:
                    patterns.append(rp)

    # Sort by quality, deduplicate overlapping patterns
    patterns.sort(key=lambda p: p.curvature_quality, reverse=True)

    # Simple dedup: remove patterns whose apex is within 5 bars of a better one
    filtered = []
    used_apexes = set()
    for p in patterns:
        apex_key = p.apex_idx // 5
        if apex_key not in used_apexes:
            filtered.append(p)
            used_apexes.add(apex_key)

    return filtered


# ── Example usage ──────────────────────────────────────────────────
if __name__ == "__main__":
    np.random.seed(42)
    dates = pd.date_range('2024-01-01', periods=80, freq='B')

    # Simulate a rounding top that breaks upward
    x = np.arange(80)
    # Quadratic rounding top: peaks around bar 30
    curve = -0.015 * (x - 30)**2 + 120
    noise = np.random.randn(80) * 0.8
    prices = curve + noise

    # Break the curvature at bar 55 — sharp upward move
    for i in range(55, 70):
        prices[i] += (i - 54) * 1.5

    highs = prices + np.random.uniform(0.5, 1.5, 80)
    lows = prices - np.random.uniform(0.5, 1.5, 80)

    df = pd.DataFrame({
        'high': highs, 'low': lows, 'close': prices
    }, index=dates)

    # Fit rounding top to first 55 bars
    rp = fit_rounding_pattern(df, 5, 50, RoundingType.TOP, min_r_squared=0.4)
    if rp:
        print(f"Rounding top detected:")
        print(f"  Apex:     bar {rp.apex_idx}, price {rp.apex_price:.1f}")
        print(f"  Quality:  R² = {rp.curvature_quality}")
        print(f"  Coeffs:   a={rp.fitted_coefficients[0]:.6f}")

        cb = detect_curvature_break(df, rp, deviation_threshold=0.02)
        if cb:
            print(f"\n  Curvature BROKEN on {cb.break_date.date()}")
            print(f"    Actual:    {cb.break_price:.1f}")
            print(f"    Expected:  {cb.expected_price:.1f}")
            print(f"    Deviation: {cb.deviation:.1%}")
            print(f"    Trade:     {cb.trade_direction}")
        else:
            print("  Curvature intact.")
    else:
        print("No rounding top found.")
