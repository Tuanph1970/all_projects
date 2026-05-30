"""Double Top / Bottom detectors (FR-PAT-DT).

Operate on the alternating swing skeleton (FR-SW-2):

    Double Top    — H L H: two near-equal highs (within tol_equal) separated by
                    at least min_separation bars, with an intervening trough at
                    least min_trough_depth below the lower peak.
    Double Bottom — L H L (mirror): two near-equal lows around an intervening
                    peak at least min_trough_depth above the higher low.

Quality score (FR-SCORE-1) blends peak/low similarity with the relative depth of
the separating extremum. All comparisons are relative / range-normalized (L4).
"""
from __future__ import annotations

import numpy as np

from chart_decomp.domain.entities import Detection, SwingSkeleton
from chart_decomp.domain.value_objects import DoubleParams
from chart_decomp.infrastructure.patterns.base import PatternDetectorBase

# A separating extremum this far (fraction of the lower peak / higher low) from
# the pair scores full depth; shallower separations score proportionally less.
_DEPTH_REF = 0.1


class DoubleTopDetector(PatternDetectorBase):
    """Double Top (bearish): H L H with two near-equal highs."""

    name = "Double Top"

    def detect(self, skeleton: SwingSkeleton, x: np.ndarray, params=None) -> list[Detection]:
        params = params or DoubleParams()
        sw = skeleton.swings
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
            depth = (lower_peak - trough.price) / lower_peak if lower_peak > 0 else 0.0
            if depth < params.min_trough_depth:
                continue

            similarity = self.clamp01(1.0 - self.rel_diff(p1.price, p2.price))
            depth_score = self.clamp01(depth / _DEPTH_REF)
            score = self.clamp01(0.5 * similarity + 0.5 * depth_score)
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
            height = (peak.price - higher_low) / peak.price if peak.price > 0 else 0.0
            if height < params.min_trough_depth:
                continue

            similarity = self.clamp01(1.0 - self.rel_diff(t1.price, t2.price))
            height_score = self.clamp01(height / _DEPTH_REF)
            score = self.clamp01(0.5 * similarity + 0.5 * height_score)
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
