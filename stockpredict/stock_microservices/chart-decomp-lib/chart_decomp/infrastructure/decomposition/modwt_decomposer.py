"""MODWT decomposer — Maximal Overlap Discrete Wavelet Transform.

Uses pywt.swt (Stationary Wavelet Transform = MODWT) with energy-preserving
normalization.  Produces MRA (multi-resolution analysis) components so that
    approximation + sum(details) == x  (within 1e-10).

Constraint C2: every detail level has a COI width stored in the result so
the caller can shade edge-contaminated samples.
"""
from __future__ import annotations

import math
import warnings

import numpy as np
import pywt

from chart_decomp.domain.entities import MODWTResult
from chart_decomp.domain.exceptions import DecompositionError, InsufficientDataError
from chart_decomp.domain.value_objects import MODWTParams, TimeSeries


class MODWTDecomposer:
    """Implements IMODWTDecomposer via pywt.swt with norm=True.

    Design patterns:
        Concrete Strategy — plugged in by DecomposerFactory.
    """

    def decompose(self, series: TimeSeries, params: MODWTParams) -> MODWTResult:
        """Run MODWT and return MRA components.

        Parameters
        ----------
        series : validated TimeSeries
        params : MODWTParams (wavelet, level, boundary)

        Returns
        -------
        MODWTResult with:
            approximation — A_J (coarsest smooth signal), shape (N,)
            details       — [D_1, …, D_J] finest-to-coarsest, each shape (N,)
            coi_widths    — half-width in samples per detail level
        """
        x = series.values
        N = len(x)
        J = params.level
        wavelet = params.wavelet

        wav = pywt.Wavelet(wavelet)
        L = len(wav.filter_bank[0])

        # Pad first — max_level is checked on the padded (power-of-2) length
        x_work, pad_len = self._pad(x, J)
        max_level = pywt.swt_max_level(len(x_work))
        if J > max_level:
            raise InsufficientDataError(
                f"Padded length {len(x_work)} supports at most {max_level} MODWT levels; "
                f"requested {J}. Use a longer series or reduce level."
            )

        try:
            # norm=True → energy-preserving MODWT normalization
            swt_coeffs = pywt.swt(x_work, wavelet, level=J, norm=True)
        except Exception as exc:
            raise DecompositionError(f"pywt.swt failed: {exc}") from exc

        # swt_coeffs[0] = (cA_J, cD_J) — coarsest
        # swt_coeffs[J-1] = (cA_1, cD_1) — finest

        # Extract MRA components via synthesis (iswt with one level at a time).
        # By linearity of iswt: sum of individual-level reconstructions == x.
        n_work = len(x_work)
        zeros = [
            (np.zeros(n_work, dtype=np.float64), np.zeros(n_work, dtype=np.float64))
            for _ in range(J)
        ]

        # Approximation A_J
        # norm=True must be passed to iswt to match the norm=True swt (pywt ≥ 1.7)
        c_aj = [list(z) for z in zeros]
        c_aj[0][0] = swt_coeffs[0][0].copy()
        a_J = pywt.iswt(c_aj, wavelet, norm=True)[:N]

        # Details D_1 … D_J
        details: list[np.ndarray] = []
        for j_idx in range(J):
            # j_idx=0 → D_1 (finest, swt_coeffs[J-1])
            # j_idx=J-1 → D_J (coarsest, swt_coeffs[0])
            coeff_idx = J - 1 - j_idx
            c_dj = [list(z) for z in zeros]
            c_dj[coeff_idx][1] = swt_coeffs[coeff_idx][1].copy()
            d_j = pywt.iswt(c_dj, wavelet, norm=True)[:N]
            details.append(d_j)

        # COI half-widths: coi_widths[j] for D_{j+1}
        # coi_width(level=j+1) = (2^(j+1) - 1) * (L - 1)
        coi_widths = [(2 ** (j + 1) - 1) * (L - 1) for j in range(J)]

        return MODWTResult(
            approximation=a_J,
            details=details,
            wavelet=wavelet,
            level=J,
            coi_widths=coi_widths,
        )

    # ── Helpers ────────────────────────────────────────────────────────────────

    @staticmethod
    def _pad(x: np.ndarray, level: int) -> tuple[np.ndarray, int]:
        """Pad x to the next power-of-2 length using symmetric reflection."""
        N = len(x)
        target = 2 ** math.ceil(math.log2(max(N, 1)))
        # pywt.swt requires length >= 2^level
        target = max(target, 2 ** level)
        if target == N:
            return x, 0
        pad_len = target - N
        x_padded = np.pad(x, (0, pad_len), mode="reflect")
        return x_padded, pad_len
