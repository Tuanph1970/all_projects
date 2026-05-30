"""Swing extractor — Layer 2a of the pattern-detection pipeline (FR-SW-1/2/3).

Design lessons made binding (SRS §II.2.2):
    L2 — built on a VETTED primitive (``scipy.signal.argrelextrema``), never a
         hand-rolled comparison loop. Only the alternation-enforcement and
         prominence/spacing filtering are our own, layered on top.
    L4 — thresholds are scale-robust: a fraction of the series range, a multiple
         of rolling ATR, or an absolute price distance. Percent-of-price is
         deliberately not available (rejected at the SwingParams level).

The output is a strictly-alternating H/L pivot list (FR-SW-2). The filtering is
a significance-based ZigZag over the argrelextrema candidates: a reversal pivot
is accepted only when the move from the last accepted pivot clears the
prominence threshold and the minimum index gap; same-direction extrema update
the running pivot to the more extreme one (which absorbs ignored minor swings
and keeps the sequence alternating without bespoke reset logic).
"""
from __future__ import annotations

import numpy as np
from scipy.signal import argrelextrema

from chart_decomp.domain.entities import Swing
from chart_decomp.domain.value_objects import SwingParams, TimeSeries


class SwingExtractor:
    """Implements ISwingExtractor.

    Design patterns:
        Concrete Strategy — plugged into the pattern pipeline.
    """

    def extract(self, series: TimeSeries, params: SwingParams) -> list[Swing]:
        """Return the ordered, strictly-alternating swing pivots of ``series``.

        Parameters
        ----------
        series : validated TimeSeries (typically the denoised price series)
        params : SwingParams (order, threshold_mode, threshold, atr_period, min_gap)
        """
        x = series.values
        n = len(x)

        # ── 1. Candidate extrema via the vetted primitive (L2) ────────────────
        maxima = argrelextrema(x, np.greater, order=params.order)[0]
        minima = argrelextrema(x, np.less, order=params.order)[0]
        candidates = [(int(i), "H") for i in maxima] + [(int(i), "L") for i in minima]
        if not candidates:
            return []
        candidates.sort(key=lambda t: t[0])

        # ── 2. Per-sample prominence threshold (scale-robust, L4) ─────────────
        thr = self._threshold_array(x, params)

        # ── 3. Significance ZigZag (alternation + prominence + min_gap) ───────
        pivots: list[tuple[int, str]] = []
        for idx, kind in candidates:
            if not pivots:
                pivots.append((idx, kind))
                continue

            last_idx, last_kind = pivots[-1]
            if kind == last_kind:
                # Same direction: keep the more extreme extremum.
                if self._is_more_extreme(x[idx], x[last_idx], kind):
                    pivots[-1] = (idx, kind)
                continue

            # Opposite direction → candidate reversal.
            move = abs(float(x[idx]) - float(x[last_idx]))
            gap_ok = (idx - last_idx) >= params.min_gap
            if move >= thr[idx] and gap_ok:
                pivots.append((idx, kind))
            # else: ignore this minor reversal; a later same-direction extremum
            # will update the running pivot if it is more extreme.

        # A single seeded pivot is not a swing: a skeleton needs at least one
        # confirmed reversal (≥2 alternating pivots) to define a move.
        if len(pivots) < 2:
            return []

        return [Swing(index=i, price=float(x[i]), kind=k) for i, k in pivots]

    # ── Helpers ──────────────────────────────────────────────────────────────

    @staticmethod
    def _is_more_extreme(price: float, ref: float, kind: str) -> bool:
        return price > ref if kind == "H" else price < ref

    def _threshold_array(self, x: np.ndarray, params: SwingParams) -> np.ndarray:
        """Per-sample minimum-prominence threshold for the chosen mode (L4)."""
        n = len(x)
        if params.threshold_mode == "range_frac":
            rng = float(x.max() - x.min())
            return np.full(n, params.threshold * rng)
        if params.threshold_mode == "absolute":
            return np.full(n, float(params.threshold))
        # "atr": multiple of a rolling, close-only ATR
        atr = self._close_atr(x, params.atr_period)
        return params.threshold * atr

    @staticmethod
    def _close_atr(x: np.ndarray, period: int) -> np.ndarray:
        """Wilder-smoothed ATR on a close-only series (TR = |Δclose|).

        Mirrors analysis-/ai-insights-service ATR, adapted to a univariate
        series. Leading samples (before the first smoothed value) are
        back-filled with the first finite ATR so the prominence threshold is
        always defined.
        """
        n = len(x)
        tr = np.zeros(n, dtype=np.float64)
        tr[1:] = np.abs(np.diff(x))
        atr = np.full(n, np.nan, dtype=np.float64)
        if n > period:
            atr[period] = float(tr[1 : period + 1].mean())
            for i in range(period + 1, n):
                atr[i] = (atr[i - 1] * (period - 1) + tr[i]) / period

        finite = np.isfinite(atr)
        if finite.any():
            first_valid = float(atr[finite][0])
            atr = np.where(finite, atr, first_valid)
        else:
            fallback = float(np.std(tr[1:])) if n > 1 else 0.0
            if fallback == 0.0:
                fallback = float(x.max() - x.min()) or 1.0
            atr = np.full(n, fallback)
        return atr
