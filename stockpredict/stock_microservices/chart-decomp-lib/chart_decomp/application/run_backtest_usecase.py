"""Use-case: Vol-targeting strategy backtest."""
from __future__ import annotations

import numpy as np

from chart_decomp.domain.entities import BacktestResult
from chart_decomp.domain.value_objects import BacktestParams
from chart_decomp.infrastructure.backtest.vol_target_backtest import VolTargetBacktester


class RunBacktestUseCase:
    def __init__(self) -> None:
        self._backtester = VolTargetBacktester()

    def execute(
        self,
        returns: np.ndarray,
        vol_forecast: np.ndarray,
        params: BacktestParams | None = None,
    ) -> BacktestResult:
        """Run vol-targeting backtest.

        returns      : daily returns, shape (N,)
        vol_forecast : one-step-ahead annualized vol forecasts, shape (N,)
        params       : BacktestParams; uses defaults if None
        """
        return self._backtester.run(
            np.asarray(returns, dtype=np.float64),
            np.asarray(vol_forecast, dtype=np.float64),
            params or BacktestParams(),
        )
