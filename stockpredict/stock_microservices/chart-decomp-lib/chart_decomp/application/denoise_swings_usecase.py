"""Use-case: Joint denoise-swing calibration (FR-DN-2).

Denoising strength and swing threshold are tightly coupled (SRS §II.2.2 L1):

    - Light denoising + tight threshold → hundreds of spurious pivots.
    - Heavy denoising + loose threshold → real patterns flattened out.

This use-case sweeps a grid of (k_drop, threshold) combinations, runs the
Layer-1 denoiser and Layer-2a swing extractor for each combination, and
returns a CalibrationResult that lets the analyst inspect the trade-off.

When ``labeled_swings`` are provided (planted labels from a known series),
recall is also computed: the fraction of label indices recovered by extracted
swings within ``recovery_tol`` samples.  This turns the calibration into a
quantitative diagnostic for threshold selection (L1 coupling criterion).

Public API
----------
DenoiseSwingtUseCase.calibrate(...)  →  CalibrationResult
calibrate_denoise_swings(...)        →  CalibrationResult  (convenience wrapper)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence

import numpy as np

from chart_decomp.domain.entities import Swing
from chart_decomp.domain.value_objects import (
    DenoiseParams,
    SwingParams,
    TimeSeries,
)
from chart_decomp.infrastructure.denoise.wavelet_denoiser import WaveletDenoiser
from chart_decomp.infrastructure.swings.swing_extractor import SwingExtractor


@dataclass
class CalibrationPoint:
    """One (k_drop, threshold) cell in the calibration grid (FR-DN-2).

    swing_count : number of retained swing pivots after denoising + extraction.
    recall      : fraction of labeled pivots recovered within recovery_tol
                  samples.  None when no labels were supplied.
    """

    k_drop: int
    threshold: float
    swing_count: int
    recall: Optional[float]


@dataclass
class CalibrationResult:
    """Full calibration grid result (FR-DN-2).

    points           : one CalibrationPoint per (k_drop, threshold) pair,
                       in row-major order (k_drop varies slowest).
    series_length    : length of the input series.
    k_drop_values    : k_drop values that were swept.
    threshold_values : threshold values that were swept.
    """

    points: list[CalibrationPoint]
    series_length: int
    k_drop_values: list[int]
    threshold_values: list[float]

    def as_grid(self) -> dict[tuple[int, float], CalibrationPoint]:
        """Dict keyed by (k_drop, threshold) for direct look-up."""
        return {(p.k_drop, p.threshold): p for p in self.points}

    def best_recall(self) -> Optional[CalibrationPoint]:
        """Point with the highest recall, or None when no labels were used."""
        labeled = [p for p in self.points if p.recall is not None]
        if not labeled:
            return None
        return max(labeled, key=lambda p: p.recall)  # type: ignore[arg-type]


def _recall(
    extracted: list[Swing],
    labels: list[Swing],
    tol: int,
) -> float:
    """Fraction of labeled pivots that have an extracted neighbour within tol."""
    if not labels:
        return 1.0
    extracted_indices = np.array([s.index for s in extracted], dtype=int)
    recovered = 0
    for lab in labels:
        if extracted_indices.size > 0:
            if int(np.min(np.abs(extracted_indices - lab.index))) <= tol:
                recovered += 1
    return recovered / len(labels)


class DenoiseSwingtUseCase:
    """Sweeps (k_drop, threshold) to help pick a coupled operating point (FR-DN-2).

    Naming note: the class is intentionally spelled *Swingt* (not *Swing*) to
    avoid shadowing the ``Swing`` domain entity when both are in scope.
    """

    def __init__(self) -> None:
        self._denoiser = WaveletDenoiser()
        self._extractor = SwingExtractor()

    def calibrate(
        self,
        x: np.ndarray,
        k_drop_values: Sequence[int] = (0, 1, 2, 3),
        threshold_values: Sequence[float] = (0.04, 0.06, 0.08, 0.10, 0.12),
        labeled_swings: Optional[list[Swing]] = None,
        *,
        wavelet: str = "sym8",
        level: int = 4,
        threshold_mode: str = "range_frac",
        order: int = 10,
        min_gap: int = 8,
        atr_period: int = 14,
        recovery_tol: int = 5,
    ) -> CalibrationResult:
        """Sweep (k_drop, threshold) and report swing count [+ recall].

        Parameters
        ----------
        x                : raw price series.
        k_drop_values    : finest detail bands to drop in Layer 1 (0 = no denoise).
        threshold_values : swing significance threshold values for Layer 2a.
                           Interpreted according to ``threshold_mode``.
        labeled_swings   : planted ground-truth pivots; when supplied, recall is
                           computed at each grid point (L1 coupling).
        wavelet          : MODWT wavelet for denoising (default 'sym8').
        level            : MODWT decomposition level (default 4).
        threshold_mode   : 'range_frac', 'atr', or 'absolute' (L4 scale-robust).
        order            : argrelextrema comparison window (default 10).
        min_gap          : minimum sample gap between consecutive pivots.
        atr_period       : Wilder ATR period (used when threshold_mode='atr').
        recovery_tol     : max index distance to count a label as recovered.
        """
        ts = TimeSeries(x)
        k_drops = list(k_drop_values)
        thresholds = list(threshold_values)
        points: list[CalibrationPoint] = []

        for k in k_drops:
            # Denoise once per k_drop — threshold doesn't affect denoising.
            denoise_params = DenoiseParams(wavelet=wavelet, level=level, k_drop=k)
            try:
                denoised = self._denoiser.denoise(ts, denoise_params)
                denoised_ts = TimeSeries(denoised)
            except Exception:
                # If denoising fails (e.g. series too short for chosen level),
                # treat as identity and continue.
                denoised_ts = ts

            for thr in thresholds:
                swing_params = SwingParams(
                    order=order,
                    threshold_mode=threshold_mode,
                    threshold=thr,
                    atr_period=atr_period,
                    min_gap=min_gap,
                )
                try:
                    swings = self._extractor.extract(denoised_ts, swing_params)
                except Exception:
                    swings = []

                rec: Optional[float] = None
                if labeled_swings is not None:
                    rec = _recall(swings, labeled_swings, recovery_tol)

                points.append(
                    CalibrationPoint(
                        k_drop=k,
                        threshold=thr,
                        swing_count=len(swings),
                        recall=rec,
                    )
                )

        return CalibrationResult(
            points=points,
            series_length=len(x),
            k_drop_values=k_drops,
            threshold_values=thresholds,
        )


# ── Convenience wrapper ───────────────────────────────────────────────────────

_uc = DenoiseSwingtUseCase()


def calibrate_denoise_swings(
    x: np.ndarray,
    k_drop_values: Sequence[int] = (0, 1, 2, 3),
    threshold_values: Sequence[float] = (0.04, 0.06, 0.08, 0.10, 0.12),
    labeled_swings: Optional[list[Swing]] = None,
    **kwargs,
) -> CalibrationResult:
    """Joint denoise-swing calibration (FR-DN-2) — convenience wrapper.

    See DenoiseSwingtUseCase.calibrate() for full parameter documentation.
    """
    return _uc.calibrate(
        x,
        k_drop_values=k_drop_values,
        threshold_values=threshold_values,
        labeled_swings=labeled_swings,
        **kwargs,
    )
