"""VMD decomposer — Variational Mode Decomposition.

Uses the vmdpy library.  Missing library raises MissingDependencyError at
call time.

Constraint C3 (mode ordering): modes are ALWAYS sorted by ascending center
frequency before returning — failure to do this causes silent feature-vector
meaning-shifts when VMD is refit on a sliding window (Trap B2).

Trap B4: VMD is NOT an exact reconstruction method.  The relative L2 error
is reported in the result entity so callers can decide whether the
decomposition quality is acceptable.
"""
from __future__ import annotations

import numpy as np

from chart_decomp.domain.entities import VMDResult
from chart_decomp.domain.exceptions import DecompositionError, MissingDependencyError
from chart_decomp.domain.value_objects import TimeSeries, VMDParams


def _require_vmdpy():
    try:
        import vmdpy  # noqa: F401
    except ImportError as exc:
        raise MissingDependencyError(
            "vmdpy is required for VMD: pip install vmdpy"
        ) from exc


class VMDDecomposer:
    """Implements IVMDDecomposer using vmdpy.

    Design patterns:
        Concrete Strategy — plugged in by DecomposerFactory.
    """

    def decompose(self, series: TimeSeries, params: VMDParams) -> VMDResult:
        """Decompose the series into K variational modes.

        Steps:
        1. Subtract mean (stored for reconstruction).
        2. Run VMD algorithm.
        3. Sort modes by ascending center frequency (Constraint C3).
        4. Compute relative L2 reconstruction error (Trap B4 transparency).

        Returns
        -------
        VMDResult with modes sorted by ascending center_frequency.
        """
        _require_vmdpy()
        from vmdpy import VMD  # type: ignore

        x = series.values
        mu = float(x.mean())
        x_centered = x - mu

        try:
            u, u_hat, omega = VMD(
                x_centered,
                params.alpha,
                params.tau,
                params.K,
                params.DC,
                params.init,
                params.tol,
            )
        except Exception as exc:
            raise DecompositionError(f"vmdpy.VMD failed: {exc}") from exc

        # omega shape: (n_iter, K) — take last row (converged frequencies)
        if omega.ndim == 2:
            omega_final = omega[-1]
        else:
            omega_final = omega

        # Constraint C3: sort by ascending center frequency
        sort_idx = np.argsort(omega_final)
        modes = u[sort_idx]
        center_freqs = omega_final[sort_idx]

        # Relative L2 reconstruction error (Trap B4)
        reconstruction = modes.sum(axis=0) + mu
        norm_x = np.linalg.norm(x)
        if norm_x < 1e-12:
            rel_error = 0.0
        else:
            rel_error = float(np.linalg.norm(x - reconstruction) / norm_x)

        return VMDResult(
            modes=modes,
            center_frequencies=center_freqs,
            series_mean=mu,
            reconstruction_error=rel_error,
        )
