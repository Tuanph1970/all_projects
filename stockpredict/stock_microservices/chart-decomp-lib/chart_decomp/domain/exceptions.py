"""Domain exceptions — all library-raised errors derive from ChartDecompError."""
from __future__ import annotations


class ChartDecompError(Exception):
    """Base for all chart-decomp errors."""


class InputValidationError(ChartDecompError):
    """Raised before an algorithm is invoked when input data is invalid.

    NFR-R1: every public function validates before calling the underlying lib.
    """


class CausalityViolationError(ChartDecompError):
    """Raised when code attempts to use future data in a forecasting context.

    Constraint C1: strict causality.  NFR-R2: raise, never silently proceed.
    """


class InsufficientDataError(ChartDecompError):
    """Raised when the series is too short to complete the requested operation."""


class DecompositionError(ChartDecompError):
    """Raised when an underlying decomposition algorithm fails to converge."""


class MissingDependencyError(ChartDecompError):
    """Raised when an optional dependency (PyEMD, vmdpy) is not installed."""
