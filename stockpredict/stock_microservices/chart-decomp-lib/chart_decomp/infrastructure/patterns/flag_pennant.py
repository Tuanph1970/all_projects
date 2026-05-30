"""Flag / Pennant detectors (FR-PAT-FLAG).

Operate on the alternating swing skeleton (FR-SW-2):

    Bull Flag    — L(pole_base) H(pole_top) with height ≥ pole_min × range,
                   followed by ≥ 4 consolidation pivots (2H + 2L) whose upper
                   and lower bound lines are parallel (similar slopes).
    Bull Pennant — same pole, consolidation with converging bounds
                   (upper line slopes down, lower line slopes up).
    Bear Flag    — H(pole_top) L(pole_bottom) mirror with rising consolidation.
    Bear Pennant — mirror pennant after a downward pole.

Pole and retrace thresholds are fractions of the series range (L4, scale-robust).
Channel classification uses slope signs (pennant) or normalised slope difference
(flag) — see _classify_channel().

Quality score (FR-SCORE-1) blends pole steepness, consolidation tightness, and
channel quality (parallelism for flags, convergence for pennants).
"""
from __future__ import annotations

import numpy as np

from chart_decomp.domain.entities import Detection, SwingSkeleton
from chart_decomp.domain.value_objects import FlagParams
from chart_decomp.infrastructure.patterns.base import PatternDetectorBase

# Maximum swing count (beyond the two pole swings) scanned for consolidation.
_MAX_CONSOL_SWINGS = 8

# Normalised slope difference below which two lines are "parallel" for a flag.
# Units: fraction of (series_range / consolidation_span).
_PARALLEL_TOL = 0.6

# Reference convergence (as fraction of series_range) for full pennant channel score.
_PENNANT_CONV_REF = 0.20


def _classify_channel(
    sl_h: float, sl_l: float, consol_span: float, series_range: float
) -> str | None:
    """Return 'pennant', 'flag', or None (does not satisfy either shape).

    Pennant: upper bound slopes down AND lower bound slopes up (converging).
    Flag:    the two slope magnitudes are within _PARALLEL_TOL of each other
             (relative to the natural slope unit series_range / consol_span).
    """
    if sl_h < 0.0 and sl_l > 0.0:
        return "pennant"
    ref = series_range / max(consol_span, 1.0)
    if abs(sl_h - sl_l) < _PARALLEL_TOL * ref:
        return "flag"
    return None


def _score(
    pole_height: float,
    series_range: float,
    params: FlagParams,
    retrace: float,
    sl_h: float,
    sl_l: float,
    consol_span: float,
    kind: str,
) -> float:
    """FR-SCORE-1: blend pole steepness, consolidation tightness, channel quality."""
    pole_score = PatternDetectorBase.clamp01(
        pole_height / max(params.pole_min * series_range, 1e-10)
    )
    tightness = PatternDetectorBase.clamp01(
        1.0 - retrace / max(params.retr_max * pole_height, 1e-10)
    )
    if kind == "pennant":
        # Score proportional to total convergence as a fraction of series range.
        convergence = (abs(sl_h) + abs(sl_l)) * consol_span
        channel = PatternDetectorBase.clamp01(
            convergence / max(_PENNANT_CONV_REF * series_range, 1e-10)
        )
    else:
        # Score inversely proportional to slope divergence.
        ref = series_range / max(consol_span, 1.0)
        channel = PatternDetectorBase.clamp01(
            1.0 - abs(sl_h - sl_l) / max(_PARALLEL_TOL * ref, 1e-10)
        )
    return PatternDetectorBase.clamp01(
        0.4 * pole_score + 0.3 * tightness + 0.3 * channel
    )


class BullFlagDetector(PatternDetectorBase):
    """Bull Flag / Bull Pennant: sharp upward pole then counter-trend consolidation.

    Detects both Bull Flag (parallel channel) and Bull Pennant (converging channel)
    from the same L→H pole. The Detection.pattern field distinguishes them.

    Pitfalls:
        Requires ≥ 2 H and ≥ 2 L consolidation pivots to fit bound lines; series
        with very few swings after the pole will not match.
    """

    name = "Bull Flag"

    def detect(
        self, skeleton: SwingSkeleton, x: np.ndarray, params=None
    ) -> list[Detection]:
        params = params or FlagParams()
        sw = skeleton.swings
        rng = self.series_range(x) or 1.0
        out: list[Detection] = []

        for i in range(len(sw) - 1):
            if sw[i].kind != "L" or sw[i + 1].kind != "H":
                continue
            pole_base, pole_top = sw[i], sw[i + 1]
            pole_height = pole_top.price - pole_base.price
            if pole_height < params.pole_min * rng:
                continue

            upper_limit = min(i + 2 + _MAX_CONSOL_SWINGS + 1, len(sw))
            for j_end in range(i + 4, upper_limit):
                consol = sw[i + 2 : j_end + 1]
                consol_h = [s for s in consol if s.kind == "H"]
                consol_l = [s for s in consol if s.kind == "L"]
                if len(consol_h) < 2 or len(consol_l) < 2:
                    continue

                min_price = min(s.price for s in consol)
                if min_price <= pole_base.price:
                    break  # consolidation fell below the pole base; no recovery
                retrace = pole_top.price - min_price
                if retrace <= 0.0 or retrace > params.retr_max * pole_height:
                    continue

                h_xs = np.array([s.index for s in consol_h], dtype=np.float64)
                h_ys = np.array([s.price for s in consol_h], dtype=np.float64)
                l_xs = np.array([s.index for s in consol_l], dtype=np.float64)
                l_ys = np.array([s.price for s in consol_l], dtype=np.float64)
                sl_h, _ = self.linfit(h_xs, h_ys)
                sl_l, _ = self.linfit(l_xs, l_ys)

                consol_span = float(consol[-1].index - consol[0].index)
                kind = _classify_channel(sl_h, sl_l, consol_span, rng)
                if kind is None:
                    continue

                pattern_name = "Bull Flag" if kind == "flag" else "Bull Pennant"
                out.append(
                    Detection(
                        pattern=pattern_name,
                        start_index=pole_base.index,
                        end_index=consol[-1].index,
                        pivots=[pole_base.index, pole_top.index]
                        + [s.index for s in consol],
                        score=_score(
                            pole_height, rng, params, retrace,
                            sl_h, sl_l, consol_span, kind,
                        ),
                        details={
                            "pole_height": float(pole_height),
                            "pole_base": float(pole_base.price),
                            "pole_top": float(pole_top.price),
                            "retrace_frac": float(retrace / pole_height),
                            "upper_slope": float(sl_h),
                            "lower_slope": float(sl_l),
                            "kind": kind,
                        },
                    )
                )
                break  # smallest valid consolidation window wins

        return out


class BearFlagDetector(PatternDetectorBase):
    """Bear Flag / Bear Pennant: sharp downward pole then counter-trend consolidation.

    Detects both Bear Flag (parallel channel) and Bear Pennant (converging channel)
    from the same H→L pole. The Detection.pattern field distinguishes them.

    Pitfalls:
        Requires ≥ 2 H and ≥ 2 L consolidation pivots to fit bound lines.
    """

    name = "Bear Flag"

    def detect(
        self, skeleton: SwingSkeleton, x: np.ndarray, params=None
    ) -> list[Detection]:
        params = params or FlagParams()
        sw = skeleton.swings
        rng = self.series_range(x) or 1.0
        out: list[Detection] = []

        for i in range(len(sw) - 1):
            if sw[i].kind != "H" or sw[i + 1].kind != "L":
                continue
            pole_top, pole_bottom = sw[i], sw[i + 1]
            pole_height = pole_top.price - pole_bottom.price
            if pole_height < params.pole_min * rng:
                continue

            upper_limit = min(i + 2 + _MAX_CONSOL_SWINGS + 1, len(sw))
            for j_end in range(i + 4, upper_limit):
                consol = sw[i + 2 : j_end + 1]
                consol_h = [s for s in consol if s.kind == "H"]
                consol_l = [s for s in consol if s.kind == "L"]
                if len(consol_h) < 2 or len(consol_l) < 2:
                    continue

                max_price = max(s.price for s in consol)
                if max_price >= pole_top.price:
                    break  # consolidation exceeded the pole top; no valid window
                retrace = max_price - pole_bottom.price
                if retrace <= 0.0 or retrace > params.retr_max * pole_height:
                    continue

                h_xs = np.array([s.index for s in consol_h], dtype=np.float64)
                h_ys = np.array([s.price for s in consol_h], dtype=np.float64)
                l_xs = np.array([s.index for s in consol_l], dtype=np.float64)
                l_ys = np.array([s.price for s in consol_l], dtype=np.float64)
                sl_h, _ = self.linfit(h_xs, h_ys)
                sl_l, _ = self.linfit(l_xs, l_ys)

                consol_span = float(consol[-1].index - consol[0].index)
                kind = _classify_channel(sl_h, sl_l, consol_span, rng)
                if kind is None:
                    continue

                pattern_name = "Bear Flag" if kind == "flag" else "Bear Pennant"
                out.append(
                    Detection(
                        pattern=pattern_name,
                        start_index=pole_top.index,
                        end_index=consol[-1].index,
                        pivots=[pole_top.index, pole_bottom.index]
                        + [s.index for s in consol],
                        score=_score(
                            pole_height, rng, params, retrace,
                            sl_h, sl_l, consol_span, kind,
                        ),
                        details={
                            "pole_height": float(pole_height),
                            "pole_top": float(pole_top.price),
                            "pole_bottom": float(pole_bottom.price),
                            "retrace_frac": float(retrace / pole_height),
                            "upper_slope": float(sl_h),
                            "lower_slope": float(sl_l),
                            "kind": kind,
                        },
                    )
                )
                break

        return out
