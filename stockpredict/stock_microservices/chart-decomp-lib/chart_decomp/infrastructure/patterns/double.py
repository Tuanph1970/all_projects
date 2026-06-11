"""Double Top / Bottom detectors (FR-PAT-DT).

Operate on the alternating swing skeleton (FR-SW-2):

    Double Top    — H L H: two near-equal highs (within tol_equal) separated by
                    at least min_separation bars, with an intervening trough at
                    least min_trough_depth below the lower peak.
    Double Bottom — L H L (mirror): two near-equal lows around an intervening
                    peak at least min_trough_depth above the higher low.

Quality score (FR-SCORE-1) blends three terms (weights sum to 1.0):
  0.4 × similarity   — relative closeness of the two peaks/lows
  0.3 × depth_score  — separating-extremum depth as fraction of the full series
                       range (range-normalised per L4; replaces the old local-peak
                       denominator that saturated scores on random walks).
                       _DEPTH_REF_RANGE = 0.80 is calibrated so that the median
                       null depth (≈ 0.25 of range) scores ≈ 0.31, leaving room
                       for the genuine 95th percentile to not saturate.
  0.3 × traj_score   — R² of a symmetric quadratic fit to the full inter-peak
                       window (concave-up for Double Top, concave-down for Bottom).
                       A clean U/∩ shape → R² ≈ 0.90; a jagged random walk → R²
                       ≈ 0.10–0.50. This replaces the two-leg linear R² which was
                       ineffective because swing legs are monotone by construction.
"""
from __future__ import annotations

import numpy as np

from chart_decomp.domain.entities import Detection, SwingSkeleton
from chart_decomp.domain.value_objects import DoubleParams
from chart_decomp.infrastructure.patterns.base import PatternDetectorBase

# Depth of the separating extremum (fraction of the full series range) at which
# the depth sub-score saturates.  Calibrated from null-distribution analysis:
# the median null double-top depth_rng ≈ 0.25, p95 ≈ 0.65.  Using 0.80 keeps
# p95 unsaturated (~0.81 depth_score) while genuine deep troughs (> 0.65 range)
# still approach 1.0.
_DEPTH_REF_RANGE = 0.80


def _vshape_r2(x: np.ndarray, i_start: int, i_end: int) -> float:
    """R² of a symmetric quadratic (a·t² + b) fit over x[i_start:i_end+1].

    Captures how cleanly the inter-peak window forms a U-shape (Double Top
    trough) or ∩-shape (Double Bottom peak).  LSQ picks the best-fitting
    quadratic regardless of concavity direction, so the same function works
    for both pattern types.

    A clean pattern → high R² (≈ 0.90–0.99).
    A random-walk window with extra wiggles → low R² (≈ 0.10–0.55).
    Windows shorter than 3 bars return 0.5 (neutral, no penalty).
    """
    seg = x[i_start : i_end + 1].astype(np.float64)
    n = len(seg)
    if n < 3:
        return 0.5
    t = np.arange(n, dtype=np.float64)
    t_norm = t - (n - 1) / 2.0
    A = np.column_stack([t_norm ** 2, np.ones(n)])
    coeffs, *_ = np.linalg.lstsq(A, seg, rcond=None)
    y_pred = A @ coeffs
    ss_res = float(np.sum((seg - y_pred) ** 2))
    ss_tot = float(np.sum((seg - seg.mean()) ** 2))
    if ss_tot < 1e-10:
        return 1.0
    return float(max(0.0, min(1.0, 1.0 - ss_res / ss_tot)))


class DoubleTopDetector(PatternDetectorBase):
    """Double Top (bearish): H L H with two near-equal highs."""

    name = "Double Top"

    def detect(self, skeleton: SwingSkeleton, x: np.ndarray, params=None) -> list[Detection]:
        params = params or DoubleParams()
        sw = skeleton.swings
        rng = self.series_range(x) or 1.0
        out: list[Detection] = []

        for i in range(len(sw) - 2):
            p1, trough, p2 = sw[i : i + 3]
            if (p1.kind, trough.kind, p2.kind) != ("H", "L", "H"):
                continue
            if (p2.index - p1.index) < params.min_separation:
                continue
            if not self.within_tol(p1.price, p2.price, params.tol_equal):
                continue
            lower_peak = min(p1.price, p2.price)
            # Local-peak relative depth is used only as a quick early-exit filter.
            depth_local = (lower_peak - trough.price) / lower_peak if lower_peak > 0 else 0.0
            if depth_local < params.min_trough_depth:
                continue

            similarity = self.clamp01(1.0 - self.rel_diff(p1.price, p2.price))
            depth_rng = (lower_peak - trough.price) / rng
            depth_score = self.clamp01(depth_rng / _DEPTH_REF_RANGE)
            traj_score = _vshape_r2(x, p1.index, p2.index)
            score = self.clamp01(0.4 * similarity + 0.3 * depth_score + 0.3 * traj_score)
            out.append(
                Detection(
                    pattern=self.name,
                    start_index=p1.index,
                    end_index=p2.index,
                    pivots=[p1.index, trough.index, p2.index],
                    score=score,
                    details={
                        "peak1": p1.price,
                        "trough": trough.price,
                        "peak2": p2.price,
                        "neckline": trough.price,
                    },
                )
            )
        return out


class DoubleBottomDetector(PatternDetectorBase):
    """Double Bottom (bullish): L H L with two near-equal lows."""

    name = "Double Bottom"

    def detect(self, skeleton: SwingSkeleton, x: np.ndarray, params=None) -> list[Detection]:
        params = params or DoubleParams()
        sw = skeleton.swings
        rng = self.series_range(x) or 1.0
        out: list[Detection] = []

        for i in range(len(sw) - 2):
            t1, peak, t2 = sw[i : i + 3]
            if (t1.kind, peak.kind, t2.kind) != ("L", "H", "L"):
                continue
            if (t2.index - t1.index) < params.min_separation:
                continue
            if not self.within_tol(t1.price, t2.price, params.tol_equal):
                continue
            higher_low = max(t1.price, t2.price)
            # Local-peak relative height is used only as a quick early-exit filter.
            height_local = (peak.price - higher_low) / peak.price if peak.price > 0 else 0.0
            if height_local < params.min_trough_depth:
                continue

            similarity = self.clamp01(1.0 - self.rel_diff(t1.price, t2.price))
            height_rng = (peak.price - higher_low) / rng
            height_score = self.clamp01(height_rng / _DEPTH_REF_RANGE)
            traj_score = _vshape_r2(x, t1.index, t2.index)
            score = self.clamp01(0.4 * similarity + 0.3 * height_score + 0.3 * traj_score)
            out.append(
                Detection(
                    pattern=self.name,
                    start_index=t1.index,
                    end_index=t2.index,
                    pivots=[t1.index, peak.index, t2.index],
                    score=score,
                    details={
                        "trough1": t1.price,
                        "peak": peak.price,
                        "trough2": t2.price,
                        "neckline": peak.price,
                    },
                )
            )
        return out
