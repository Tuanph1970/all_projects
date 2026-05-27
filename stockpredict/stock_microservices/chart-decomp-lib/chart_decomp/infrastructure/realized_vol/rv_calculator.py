"""Realized variance / volatility computation (FR-RV).

Two input modes:
    2-D (N_days, M_intraday): proper RV = sum(r²) across intraday returns.
    1-D (N_days,): daily returns approximation RV ≈ r²  (warns: high-noise).

All output arrays have length N_days.
"""
from __future__ import annotations

import warnings

import numpy as np

from chart_decomp.domain.exceptions import InputValidationError

_EPS = 1e-10


class RealizedVolCalculator:
    """Pure domain-logic object with no external dependencies."""

    def compute(
        self,
        returns: np.ndarray,
        annualization: int = 252,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Compute (RV, annualized_vol, log_RV) from returns.

        Parameters
        ----------
        returns       : shape (N_days, M_intraday) or (N_days,)
        annualization : trading days per year (default 252)

        Returns
        -------
        rv      : realized variance, shape (N_days,)
        vol     : annualized vol = sqrt(rv * annualization), shape (N_days,)
        log_rv  : log(rv + eps), shape (N_days,)
        """
        arr = np.asarray(returns, dtype=np.float64)
        if arr.ndim == 1:
            warnings.warn(
                "1-D daily returns passed to realized_vol; "
                "RV is approximated as r² which is a high-noise estimator. "
                "Provide intraday returns (2-D array) for proper RV.",
                UserWarning,
                stacklevel=3,
            )
            rv = arr ** 2
        elif arr.ndim == 2:
            if arr.shape[1] < 1:
                raise InputValidationError(
                    "Intraday returns must have at least 1 bar per day"
                )
            rv = np.sum(arr ** 2, axis=1)
        else:
            raise InputValidationError(
                f"returns must be 1-D or 2-D; got shape {arr.shape}"
            )

        vol = np.sqrt(rv * annualization)
        log_rv = np.log(rv + _EPS)
        return rv, vol, log_rv
