"""Triangle pattern detectors (FR-PAT-TRI).

Operate on the alternating swing skeleton (FR-SW-2):

    Ascending  — flat upper trendline (H pivots), rising lower trendline (L pivots).
    Descending — falling upper trendline, flat lower trendline.
    Symmetric  — falling upper, rising lower (converging from both sides).

Detection: slide a window of ≥ min_pivots consecutive swings over the skeleton;
for each window with ≥ 2H and ≥ 2L pivots, fit lines through each group and
classify the slope pair (FR-PAT-TRI).

"Flat" / "rising" / "falling" are defined relative to the natural slope unit
``series_range / span`` scaled by ``flat_slope_eps``, making thresholds
scale-robust (L4).

Quality score (FR-SCORE-1) blends pattern-specific shape quality and line-fit
R² for both bounds.
"""
from __future__ import annotations

import numpy as np

from chart_decomp.domain.entities import Detection, SwingSkeleton
from chart_decomp.domain.value_objects import TriangleParams
from chart_decomp.infrastructure.patterns.base import PatternDetectorBase

# Extra windows to scan beyond min_pivots before giving up on a starting pivot.
_MAX_EXTRA = 8


# ── Slope classification helpers ────���────────────────────────────────────────

def _flat(slope: float, eps: float, ref: float) -> bool:
    return abs(slope) < eps * ref


def _rising(slope: float, eps: float, ref: float) -> bool:
    return slope > eps * ref


def _falling(slope: float, eps: float, ref: float) -> bool:
    return slope < -(eps * ref)


# ── Line-fit quality (R²) ────���────────────────────────────────��──────────────

def _r2(xs: np.ndarray, ys: np.ndarray, slope: float, intercept: float) -> float:
    """R² of linear fit — 1.0 when all pivots lie on the fitted line."""
    y_pred = slope * xs + intercept
    ss_res = float(np.sum((ys - y_pred) ** 2))
    ss_tot = float(np.sum((ys - ys.mean()) ** 2))
    if ss_tot < 1e-10:
        return 1.0  # all pivots at the same level → perfect flat-line fit
    return PatternDetectorBase.clamp01(1.0 - ss_res / ss_tot)


# ── Shared sliding-window detection ─────────────────────────────────────────

def _detect(
    skeleton: SwingSkeleton,
    x: np.ndarray,
    params: TriangleParams,
    pattern_name: str,
    classify,   # (sl_h, sl_l, eps, ref) -> bool
    shape_score,  # (sl_h, sl_l, span, rng) -> float in [0, 1]
) -> list[Detection]:
    sw = skeleton.swings
    rng = PatternDetectorBase.series_range(x) or 1.0
    out: list[Detection] = []

    for i in range(len(sw)):
        j_max = min(i + params.min_pivots - 1 + _MAX_EXTRA, len(sw) - 1)
        for j in range(i + params.min_pivots - 1, j_max + 1):
            window = sw[i : j + 1]
            h_pivots = [s for s in window if s.kind == "H"]
            l_pivots = [s for s in window if s.kind == "L"]
            if len(h_pivots) < 2 or len(l_pivots) < 2:
                continue

            h_xs = np.array([s.index for s in h_pivots], dtype=np.float64)
            h_ys = np.array([s.price for s in h_pivots], dtype=np.float64)
            l_xs = np.array([s.index for s in l_pivots], dtype=np.float64)
            l_ys = np.array([s.price for s in l_pivots], dtype=np.float64)

            sl_h, ic_h = PatternDetectorBase.linfit(h_xs, h_ys)
            sl_l, ic_l = PatternDetectorBase.linfit(l_xs, l_ys)

            span = float(window[-1].index - window[0].index)
            ref = rng / max(span, 1.0)

            if not classify(sl_h, sl_l, params.flat_slope_eps, ref):
                continue

            h_r2 = _r2(h_xs, h_ys, sl_h, ic_h)
            l_r2 = _r2(l_xs, l_ys, sl_l, ic_l)
            ss = shape_score(sl_h, sl_l, span, rng)
            score = PatternDetectorBase.clamp01(
                0.4 * ss + 0.3 * h_r2 + 0.3 * l_r2
            )

            out.append(
                Detection(
                    pattern=pattern_name,
                    start_index=window[0].index,
                    end_index=window[-1].index,
                    pivots=[s.index for s in window],
                    score=score,
                    details={
                        "upper_slope": float(sl_h),
                        "lower_slope": float(sl_l),
                        "h_r2": float(h_r2),
                        "l_r2": float(l_r2),
                    },
                )
            )
            break  # smallest valid window for this starting pivot

    return out


# ── Shape-score helpers ───────���───────────────────────────────────────────────

def _sym_shape(sl_h: float, sl_l: float, span: float, rng: float) -> float:
    """Convergence strength as a fraction of series range."""
    return PatternDetectorBase.clamp01(
        (abs(sl_h) + abs(sl_l)) * span / max(0.5 * rng, 1e-10)
    )


def _asc_shape(sl_h: float, sl_l: float, span: float, rng: float) -> float:
    """Rising lower slope strength."""
    return PatternDetectorBase.clamp01(
        sl_l * span / max(0.3 * rng, 1e-10)
    )


def _desc_shape(sl_h: float, sl_l: float, span: float, rng: float) -> float:
    """Falling upper slope strength."""
    return PatternDetectorBase.clamp01(
        abs(sl_h) * span / max(0.3 * rng, 1e-10)
    )


# ── Concrete detectors ─────────────────────────────��──────────────────────────

class SymmetricTriangleDetector(PatternDetectorBase):
    """Symmetric Triangle (FR-PAT-TRI): falling upper trendline, rising lower trendline.

    Both lines are 'non-flat' and converge toward an apex. Requires ≥ min_pivots
    swing pivots with at least 2H and 2L.

    Pitfalls:
        A very short consolidation with steep but nearly equal H/L moves may
        score low on shape_score even if it satisfies the slope-pair test.
    """

    name = "Symmetric Triangle"

    def detect(
        self, skeleton: SwingSkeleton, x: np.ndarray, params=None
    ) -> list[Detection]:
        params = params or TriangleParams()
        return _detect(
            skeleton, x, params, self.name,
            classify=lambda sl_h, sl_l, eps, ref: (
                _falling(sl_h, eps, ref) and _rising(sl_l, eps, ref)
            ),
            shape_score=_sym_shape,
        )


class AscendingTriangleDetector(PatternDetectorBase):
    """Ascending Triangle (FR-PAT-TRI): flat upper resistance, rising lower support.

    Upper trendline (H pivots) is 'flat' (|slope| < flat_slope_eps × ref);
    lower trendline (L pivots) is 'rising' (slope > flat_slope_eps × ref).
    Bullish bias — price coils under a flat ceiling.
    """

    name = "Ascending Triangle"

    def detect(
        self, skeleton: SwingSkeleton, x: np.ndarray, params=None
    ) -> list[Detection]:
        params = params or TriangleParams()
        return _detect(
            skeleton, x, params, self.name,
            classify=lambda sl_h, sl_l, eps, ref: (
                _flat(sl_h, eps, ref) and _rising(sl_l, eps, ref)
            ),
            shape_score=_asc_shape,
        )


class DescendingTriangleDetector(PatternDetectorBase):
    """Descending Triangle (FR-PAT-TRI): falling upper resistance, flat lower support.

    Upper trendline (H pivots) is 'falling' (slope < -flat_slope_eps × ref);
    lower trendline (L pivots) is 'flat'. Bearish bias — price compresses onto
    a horizontal floor.
    """

    name = "Descending Triangle"

    def detect(
        self, skeleton: SwingSkeleton, x: np.ndarray, params=None
    ) -> list[Detection]:
        params = params or TriangleParams()
        return _detect(
            skeleton, x, params, self.name,
            classify=lambda sl_h, sl_l, eps, ref: (
                _falling(sl_h, eps, ref) and _flat(sl_l, eps, ref)
            ),
            shape_score=_desc_shape,
        )
