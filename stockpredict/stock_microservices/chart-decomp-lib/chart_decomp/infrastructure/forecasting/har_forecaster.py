"""HAR (Heterogeneous Autoregressive) walk-forward volatility forecaster.

Constraint C1 — STRICT CAUSALITY:
    At every step t we build features from log_rv[0:t+1] only and predict
    log_rv[t+1].  Training data for refits is log_rv[0:t+1].
    NFR-R2: a CausalityViolationError is raised if callers pass futures.

Feature vector at time t (SRS §3.7.1):
    [log_rv[t],
     mean(log_rv[max(0,t-4):t+1]),    ← weekly component
     mean(log_rv[max(0,t-21):t+1])]   ← monthly component

Model: Ridge regression with configurable alpha.
Refits every `refit_every` steps on all data strictly before t+1.
"""
from __future__ import annotations

import numpy as np
from sklearn.linear_model import Ridge

from chart_decomp.domain.entities import ForecastResult
from chart_decomp.domain.exceptions import CausalityViolationError, InsufficientDataError
from chart_decomp.domain.value_objects import HARParams

_FEATURE_NAMES = ["log_rv_daily", "log_rv_weekly_mean", "log_rv_monthly_mean"]


class HARForecaster:
    """Implements IForecaster for the HAR model.

    Design patterns:
        Concrete Strategy.
        Template Method: _build_features / _refit_if_needed used by VMD-HAR subclass.
    """

    def forecast(self, log_rv: np.ndarray, params: HARParams | None = None) -> ForecastResult:
        """Walk-forward HAR forecast.

        Parameters
        ----------
        log_rv : 1-D float array of log realized variance, shape (N,)
        params : HARParams; uses defaults if None

        Returns
        -------
        ForecastResult with predictions aligned to timestamps[i] = t
        where predictions[i] is the forecast for log_rv[t+1].
        """
        if params is None:
            params = HARParams()
        log_rv = np.asarray(log_rv, dtype=np.float64)
        N = len(log_rv)

        if N < params.min_train + 2:
            raise InsufficientDataError(
                f"Need at least {params.min_train + 2} observations; got {N}"
            )

        predictions = np.full(N, np.nan)
        actuals = np.full(N, np.nan)
        model: Ridge | None = None
        last_refit = -params.refit_every  # triggers initial refit

        for t in range(params.min_train, N - 1):
            # Causality check: we only look at log_rv[0:t+1]
            self._check_causality(t, N)

            # Refit ridge if due
            if (t - last_refit) >= params.refit_every or model is None:
                model = self._fit(log_rv[: t + 1], params)
                last_refit = t

            feat = self._build_features(log_rv, t)
            predictions[t] = float(model.predict(feat.reshape(1, -1))[0])
            actuals[t] = log_rv[t + 1]

        mask = ~np.isnan(predictions)
        ts = np.where(mask)[0]
        preds = predictions[mask]
        acts = actuals[mask]

        metrics = self._compute_metrics(preds, acts)
        return ForecastResult(
            timestamps=ts,
            predictions=preds,
            actuals=acts,
            metrics=metrics,
            features_used=list(_FEATURE_NAMES),
        )

    # ── Helpers — accessible to subclasses ────────────────────────────────────

    @staticmethod
    def _build_features(log_rv: np.ndarray, t: int) -> np.ndarray:
        """Build HAR feature vector at time t using only log_rv[0:t+1]."""
        daily = log_rv[t]
        weekly = float(np.mean(log_rv[max(0, t - 4) : t + 1]))
        monthly = float(np.mean(log_rv[max(0, t - 21) : t + 1]))
        return np.array([daily, weekly, monthly], dtype=np.float64)

    @staticmethod
    def _fit(log_rv_history: np.ndarray, params: HARParams) -> Ridge:
        """Fit ridge on all available (feature, target) pairs from log_rv_history."""
        T = len(log_rv_history)
        min_idx = 21  # need 21 lags for monthly feature
        X_rows, y_rows = [], []
        for t in range(min_idx, T - 1):
            feat = HARForecaster._build_features(log_rv_history, t)
            X_rows.append(feat)
            y_rows.append(log_rv_history[t + 1])
        if not X_rows:
            raise InsufficientDataError("Not enough history to build HAR training set")
        X = np.vstack(X_rows)
        y = np.array(y_rows)
        return Ridge(alpha=params.ridge_alpha).fit(X, y)

    @staticmethod
    def _check_causality(t: int, N: int) -> None:
        """Raise if t is the last index — no target log_rv[t+1] would exist."""
        if t >= N - 1:
            raise CausalityViolationError(
                f"Cannot forecast at t={t}: there is no log_rv[{t+1}] in the series "
                "(NFR-R2: strict causality enforced)"
            )

    @staticmethod
    def _compute_metrics(preds: np.ndarray, acts: np.ndarray) -> dict:
        if len(preds) == 0:
            return {}
        resid = acts - preds
        rmse = float(np.sqrt(np.mean(resid ** 2)))
        mae = float(np.mean(np.abs(resid)))
        ss_res = float(np.sum(resid ** 2))
        ss_tot = float(np.sum((acts - acts.mean()) ** 2))
        r2 = 1.0 - ss_res / ss_tot if ss_tot > 1e-15 else 0.0

        # QLIKE on variance scale: mean(σ²_true/σ²_pred − log(σ²_true/σ²_pred) − 1)
        var_pred = np.exp(preds)
        var_true = np.exp(acts)
        ratio = var_true / np.where(var_pred > 1e-30, var_pred, 1e-30)
        qlike = float(np.mean(ratio - np.log(ratio) - 1.0))

        return {"rmse": rmse, "mae": mae, "r2": float(r2), "qlike": qlike, "dm_vs_har": None}
