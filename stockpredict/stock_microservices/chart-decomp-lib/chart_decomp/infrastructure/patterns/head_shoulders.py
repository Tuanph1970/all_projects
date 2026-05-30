"""Head & Shoulders detectors (FR-PAT-HS).

Operate on the alternating swing skeleton (FR-SW-2):

    H&S top         — label sequence H L H L H, middle high (head) strictly
                      highest, shoulders within tol_shoulder, neckline troughs
                      within tol_neckline.
    Inverse H&S     — mirror sequence L H L H L, middle low (head) strictly
                      lowest, shoulders within tol_shoulder, neckline peaks
                      within tol_neckline.

Quality score (FR-SCORE-1) blends shoulder symmetry, neckline flatness, and head
prominence (head height as a fraction of the series range). All comparisons are
relative / range-normalized (scale-robust, L4). Geometry harvested from the
ai-insights-service H&S detector, re-expressed on the close-only skeleton.
"""
from __future__ import annotations

import numpy as np

from chart_decomp.domain.entities import Detection, Swing, SwingSkeleton
from chart_decomp.domain.value_objects import HSParams
from chart_decomp.infrastructure.patterns.base import PatternDetectorBase

# Head height (vs the higher/lower shoulder) of this fraction of the series
# range scores full prominence; smaller heads score proportionally less.
_PROMINENCE_REF = 0.2


class HeadAndShouldersDetector(PatternDetectorBase):
    """H&S top (bearish): H L H L H with the head strictly highest."""

    name = "Head & Shoulders"

    def detect(self, skeleton: SwingSkeleton, x: np.ndarray, params=None) -> list[Detection]:
        params = params or HSParams()
        sw = skeleton.swings
        rng = self.series_range(x) or 1.0
        out: list[Detection] = []

        for i in range(len(sw) - 4):
            w = sw[i : i + 5]
            if [s.kind for s in w] != ["H", "L", "H", "L", "H"]:
                continue
            ls, t1, head, t2, rs = w
            if not (head.price > ls.price and head.price > rs.price):
                continue
            if not self.within_tol(ls.price, rs.price, params.tol_shoulder):
                continue
            if not self.within_tol(t1.price, t2.price, params.tol_neckline):
                continue

            head_height = head.price - max(ls.price, rs.price)
            out.append(self._make(ls, t1, head, t2, rs, head_height, rng))
        return out

    def _make(self, ls, t1, head, t2, rs, head_height, rng) -> Detection:
        symmetry = self.clamp01(1.0 - self.rel_diff(ls.price, rs.price))
        flatness = self.clamp01(1.0 - self.rel_diff(t1.price, t2.price))
        prominence = self.clamp01((head_height / rng) / _PROMINENCE_REF)
        score = self.clamp01(0.4 * symmetry + 0.3 * flatness + 0.3 * prominence)
        neckline = (t1.price + t2.price) / 2.0
        return Detection(
            pattern=self.name,
            start_index=ls.index,
            end_index=rs.index,
            pivots=[ls.index, t1.index, head.index, t2.index, rs.index],
            score=score,
            details={
                "left_shoulder": ls.price,
                "head": head.price,
                "right_shoulder": rs.price,
                "neckline": neckline,
            },
        )


class InverseHeadAndShouldersDetector(PatternDetectorBase):
    """Inverse H&S (bullish): L H L H L with the head strictly lowest."""

    name = "Inverse Head & Shoulders"

    def detect(self, skeleton: SwingSkeleton, x: np.ndarray, params=None) -> list[Detection]:
        params = params or HSParams()
        sw = skeleton.swings
        rng = self.series_range(x) or 1.0
        out: list[Detection] = []

        for i in range(len(sw) - 4):
            w = sw[i : i + 5]
            if [s.kind for s in w] != ["L", "H", "L", "H", "L"]:
                continue
            ls, t1, head, t2, rs = w
            if not (head.price < ls.price and head.price < rs.price):
                continue
            if not self.within_tol(ls.price, rs.price, params.tol_shoulder):
                continue
            if not self.within_tol(t1.price, t2.price, params.tol_neckline):
                continue

            head_depth = min(ls.price, rs.price) - head.price
            symmetry = self.clamp01(1.0 - self.rel_diff(ls.price, rs.price))
            flatness = self.clamp01(1.0 - self.rel_diff(t1.price, t2.price))
            prominence = self.clamp01((head_depth / rng) / _PROMINENCE_REF)
            score = self.clamp01(0.4 * symmetry + 0.3 * flatness + 0.3 * prominence)
            neckline = (t1.price + t2.price) / 2.0
            out.append(
                Detection(
                    pattern=self.name,
                    start_index=ls.index,
                    end_index=rs.index,
                    pivots=[ls.index, t1.index, head.index, t2.index, rs.index],
                    score=score,
                    details={
                        "left_shoulder": ls.price,
                        "head": head.price,
                        "right_shoulder": rs.price,
                        "neckline": neckline,
                    },
                )
            )
        return out
