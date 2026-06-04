"""EMD / EEMD decomposer — Empirical Mode Decomposition.

Uses the PyEMD library (import name: PyEMD).  Missing library raises
MissingDependencyError at call time, not at import time, so the rest of the
library is usable without PyEMD installed.

Constraint C3: IMFs are always returned highest-frequency-first (index 0) with
the residue last — this is PyEMD's natural ordering and is preserved here.

Trap B3: EMD end-effects — cubic-spline envelopes near the boundary are
unstable; recent IMF values may shift when new data arrives.  The forecasting
layer enforces edge_lag to avoid reading fresh-edge values.
"""
from __future__ import annotations

import warnings
from typing import Optional

import numpy as np

from chart_decomp.domain.entities import EMDResult
from chart_decomp.domain.exceptions import DecompositionError, MissingDependencyError
from chart_decomp.domain.value_objects import EMDParams, EEMDParams, TimeSeries


def _require_pyemd():
    try:
        import PyEMD  # noqa: F401
    except ImportError as exc:
        raise MissingDependencyError(
            "PyEMD is required for EMD/EEMD: pip install EMD-signal"
        ) from exc


def _dominant_period(imf: np.ndarray) -> float:
    """Estimate dominant period via zero-crossing counting.

    period = 2 * N / n_zero_crossings  (SRS §3.1.2)
    Returns np.inf when fewer than 2 zero-crossings are found (residue / trend).
    """
    zc = int(np.sum(np.diff(np.sign(imf)) != 0))
    if zc < 2:
        return np.inf
    return 2.0 * len(imf) / zc


class EMDDecomposer:
    """Implements IEMDDecomposer using PyEMD.

    Design patterns:
        Concrete Strategy — plugged in by DecomposerFactory.
        Template Method  — _run_emd shared by decompose() and decompose_ensemble().
    """

    def decompose(self, series: TimeSeries, params: EMDParams) -> EMDResult:
        """Run standard EMD on the series.

        Returns IMFs in rows 0..K-2 (highest-to-lowest frequency) and the
        monotonic residue in the last row.
        """
        _require_pyemd()
        from PyEMD import EMD  # type: ignore

        x = series.values.copy()
        emd = EMD()
        emd.MAX_ITERATION = params.max_sift

        try:
            raw_imfs = emd(x, max_imf=params.max_imfs or 0)
        except Exception as exc:
            raise DecompositionError(f"PyEMD.EMD failed: {exc}") from exc

        return self._build_result(raw_imfs)

    def decompose_ensemble(self, series: TimeSeries, params: EEMDParams) -> EMDResult:
        """Run EEMD: ensemble of EMD on noise-perturbed copies, averaged.

        Uses params.seed for the EEMD noise seed (Constraint C5: reproducibility).
        """
        _require_pyemd()
        from PyEMD import EEMD  # type: ignore

        x = series.values.copy()
        noise_width = params.noise_width * float(np.std(x))

        # parallel=False is mandatory here: PyEMD's EEMD otherwise spawns a
        # multiprocessing.Pool, which deadlocks/stalls when this runs inside the
        # FastAPI request threadpool (run_in_threadpool). Serial EEMD is fast
        # enough (~0.1s for n_trials=100 on ~500 points).
        eemd = EEMD(trials=params.n_trials, noise_width=noise_width, parallel=False)
        if params.seed is not None:
            eemd.noise_seed(params.seed)
        eemd.MAX_ITERATION = params.stop_tol  # EEMD uses tolerance differently

        try:
            raw_imfs = eemd.eemd(x, max_imf=params.max_imfs or 0)
        except Exception as exc:
            raise DecompositionError(f"PyEMD.EEMD failed: {exc}") from exc

        return self._build_result(raw_imfs)

    # ── Internal ───────────────────────────────────────────────────────────────

    @staticmethod
    def _build_result(raw_imfs: np.ndarray) -> EMDResult:
        """Convert raw PyEMD output into a clean EMDResult entity."""
        if raw_imfs.ndim == 1:
            raw_imfs = raw_imfs[np.newaxis, :]

        K = raw_imfs.shape[0]

        # Dominant periods for all IMFs except the last (residue)
        dominant_periods = [_dominant_period(raw_imfs[i]) for i in range(K - 1)]

        # PyEMD does not report sift iterations per IMF publicly; use sentinel
        n_sift_iters = [0] * K

        return EMDResult(
            imfs=raw_imfs,
            dominant_periods=dominant_periods,
            n_sift_iters=n_sift_iters,
        )
