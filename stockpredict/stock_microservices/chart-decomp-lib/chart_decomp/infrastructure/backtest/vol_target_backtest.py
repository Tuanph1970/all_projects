"""Vol-targeting strategy backtest (FR-BT-*).

Position sizing (FR-BT-POS):
    w[t] = clip(target_ann_vol / max(sigma_hat[t+1], eps), -MAX_LEV, +MAX_LEV)

PnL accounting (FR-BT-PNL):
    gross_pnl[t+1] = w[t] * ret[t+1]
    turnover[t+1]  = |w[t+1] - w[t]|
    cost[t+1]      = turnover[t+1] * cost_bps / 10000
    net_pnl[t+1]   = gross_pnl[t+1] - cost[t+1]
"""
from __future__ import annotations

import numpy as np

from chart_decomp.domain.entities import BacktestResult
from chart_decomp.domain.exceptions import InputValidationError
from chart_decomp.domain.value_objects import BacktestParams

_EPS = 1e-8


class VolTargetBacktester:
    """Implements IBacktester.

    Design patterns:
        Concrete Strategy.
    """

    def run(
        self,
        returns: np.ndarray,
        vol_forecast: np.ndarray,
        params: BacktestParams | None = None,
    ) -> BacktestResult:
        """Run vol-targeting backtest.

        Parameters
        ----------
        returns      : daily return series, shape (N,)
        vol_forecast : one-step-ahead annualized vol forecasts, shape (N,).
                       vol_forecast[t] is the forecast for day t+1.
        params       : BacktestParams; uses defaults if None

        Returns
        -------
        BacktestResult with PnL, position, turnover, and all SRS metrics.
        """
        if params is None:
            params = BacktestParams()
        returns = np.asarray(returns, dtype=np.float64)
        vol_forecast = np.asarray(vol_forecast, dtype=np.float64)
        N = len(returns)

        if len(vol_forecast) != N:
            raise InputValidationError(
                f"returns length {N} != vol_forecast length {len(vol_forecast)}"
            )

        # Replace NaN forecasts with a conservative value (annualized 30% vol)
        safe_forecast = np.where(
            np.isnan(vol_forecast) | (vol_forecast <= 0),
            0.30,
            vol_forecast,
        )

        # Position sizes w[t] for day t+1
        w = np.clip(
            params.target_ann_vol / np.maximum(safe_forecast, _EPS),
            -params.max_leverage,
            params.max_leverage,
        )

        # PnL on day t = w[t-1] * ret[t]  (shift positions forward by 1)
        gross_pnl = np.zeros(N)
        gross_pnl[1:] = w[:-1] * returns[1:]

        # Turnover on day t = |w[t] - w[t-1]|
        turnover = np.zeros(N)
        turnover[1:] = np.abs(w[1:] - w[:-1])

        cost = turnover * params.cost_bps / 10_000.0
        net_pnl = gross_pnl - cost

        metrics = self._compute_metrics(gross_pnl, net_pnl, w, turnover, params)
        return BacktestResult(
            pnl_gross=gross_pnl,
            pnl_net=net_pnl,
            positions=w,
            turnover=turnover,
            metrics=metrics,
        )

    @staticmethod
    def _compute_metrics(
        gross_pnl: np.ndarray,
        net_pnl: np.ndarray,
        positions: np.ndarray,
        turnover: np.ndarray,
        params: BacktestParams,
    ) -> dict:
        ann = params.annualization
        n = len(net_pnl)

        ann_ret = float(net_pnl.mean() * ann)
        ann_vol = float(net_pnl.std() * np.sqrt(ann))
        sharpe = ann_ret / ann_vol if ann_vol > 1e-10 else 0.0

        cum = np.cumsum(net_pnl)
        running_max = np.maximum.accumulate(cum)
        drawdown = running_max - cum
        maxdd = float(drawdown.max())

        avg_leverage = float(np.abs(positions).mean())
        ann_turnover = float(turnover.mean() * ann)
        cost_drag = float((gross_pnl - net_pnl).mean() * ann)

        return {
            "ann_ret": ann_ret,
            "ann_vol": ann_vol,
            "sharpe": float(sharpe),
            "maxdd": maxdd,
            "avg_leverage": avg_leverage,
            "ann_turnover": ann_turnover,
            "cost_drag": cost_drag,
        }
