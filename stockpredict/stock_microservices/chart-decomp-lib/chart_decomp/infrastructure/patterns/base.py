"""Shared base + geometry helpers for chart-pattern detectors (FR-PAT-*).

Every concrete detector (A6–A9) subclasses ``PatternDetectorBase``, sets a
``name``, and implements ``detect(skeleton, x, params) -> list[Detection]``.
The geometry helpers here are harvested from the ai-insights-service detectors
but re-expressed for the univariate swing skeleton (close-price array), with
scale-robust comparisons (relative differences, range fractions) per L4.
"""
from __future__ import annotations

import numpy as np

from chart_decomp.domain.entities import Detection, SwingSkeleton


class PatternDetectorBase:
    """Base interface + shared geometry for pattern detectors (FR-PAT-EXT).

    Implements IPatternDetector structurally: subclasses provide ``name`` and
    override ``detect``.
    """

    name: str = "Pattern"

    def detect(self, skeleton: SwingSkeleton, x: np.ndarray, params=None) -> list[Detection]:
        raise NotImplementedError

    # ── Shared geometry helpers ──────────────────────────────────────────────

    @staticmethod
    def linfit(xs: np.ndarray, ys: np.ndarray) -> tuple[float, float]:
        """Least-squares (slope, intercept) of ys on xs. Flat line if < 2 pts."""
        xs = np.asarray(xs, dtype=np.float64)
        ys = np.asarray(ys, dtype=np.float64)
        if len(xs) < 2:
            return 0.0, float(ys[0]) if len(ys) else 0.0
        xm, ym = xs.mean(), ys.mean()
        ss = float(((xs - xm) ** 2).sum())
        slope = 0.0 if ss == 0.0 else float(((xs - xm) * (ys - ym)).sum() / ss)
        return slope, float(ym - slope * xm)

    @staticmethod
    def line_at(x1: float, y1: float, x2: float, y2: float, x: float) -> float:
        """Linear interpolation of the line (x1,y1)–(x2,y2) evaluated at x."""
        if x2 == x1:
            return float(y1)
        slope = (y2 - y1) / (x2 - x1)
        return float(y1 + slope * (x - x1))

    @staticmethod
    def rel_diff(a: float, b: float) -> float:
        """Symmetric relative difference |a-b| / mean(|a|,|b|) (0 when both 0)."""
        mean = (abs(a) + abs(b)) / 2.0
        if mean == 0.0:
            return 0.0
        return abs(a - b) / mean

    @classmethod
    def within_tol(cls, a: float, b: float, tol: float) -> bool:
        """True iff a and b agree within relative tolerance ``tol``."""
        return cls.rel_diff(a, b) <= tol

    @staticmethod
    def series_range(x: np.ndarray) -> float:
        x = np.asarray(x, dtype=np.float64)
        return float(x.max() - x.min())

    @staticmethod
    def clamp01(v: float) -> float:
        return float(min(1.0, max(0.0, v)))
