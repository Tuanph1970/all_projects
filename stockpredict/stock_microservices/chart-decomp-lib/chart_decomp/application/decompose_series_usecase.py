"""Use-case: Decompose a univariate series.

Orchestrates the domain objects:
    TimeSeries (VO) → DecomposerFactory → concrete IDecomposer → entity result.

Clients call execute(x, method, params) and receive the typed result entity.
The use-case enforces input validation via TimeSeries construction, so
callers do not need to check dtype/NaN/length themselves.
"""
from __future__ import annotations

from typing import Union

import numpy as np

from chart_decomp.domain.entities import EMDResult, MODWTResult, VMDResult
from chart_decomp.domain.value_objects import (
    EMDParams,
    EEMDParams,
    MODWTParams,
    TimeSeries,
    VMDParams,
)
from chart_decomp.factories.decomposer_factory import DecomposerFactory

_AnyResult = Union[MODWTResult, EMDResult, VMDResult]


class DecomposeSeriesUseCase:
    """Application service for single-series decomposition.

    Design patterns:
        Facade over factory + strategy.
    """

    def __init__(self) -> None:
        self._factory = DecomposerFactory()

    def execute(
        self,
        x: np.ndarray,
        method: str,
        params: MODWTParams | EMDParams | EEMDParams | VMDParams | None = None,
    ) -> _AnyResult:
        """Decompose x using the named method.

        Parameters
        ----------
        x      : raw 1-D array (validated inside TimeSeries)
        method : "modwt" | "emd" | "eemd" | "vmd"
        params : typed params for the chosen method; uses defaults if None

        Returns
        -------
        MODWTResult | EMDResult | VMDResult depending on method.
        """
        series = TimeSeries(x)

        if method == "modwt":
            decomposer = self._factory.create_modwt()
            return decomposer.decompose(series, params or MODWTParams())

        if method == "emd":
            decomposer = self._factory.create_emd()
            return decomposer.decompose(series, params or EMDParams())

        if method == "eemd":
            decomposer = self._factory.create_emd()
            return decomposer.decompose_ensemble(series, params or EEMDParams())

        if method == "vmd":
            decomposer = self._factory.create_vmd()
            return decomposer.decompose(series, params or VMDParams())

        raise ValueError(
            f"Unknown decomposition method '{method}'; "
            "choose from: modwt, emd, eemd, vmd"
        )
