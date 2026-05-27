"""VMD-augmented HAR walk-forward forecaster (FR-FCST-VMD-HAR).

Constraint C1 — STRICT CAUSALITY:
    VMD is run on a TRAILING WINDOW [t-window+1, t] of log_rv, never on
    the full series.  Mode features are read with an edge_lag offset from
    the right edge of the window to avoid the unstable VMD boundary
    (Trap B3 analogy — Trap B3 is for EMD but the same principle applies).

Constraint C3 — MODE ORDERING:
    After every VMD refit, modes are sorted by ascending center frequency.
    Without this, the feature vector silently changes meaning (Trap B2).

Feature vector at time t:
    [HAR_daily, HAR_weekly, HAR_monthly,            ← 3 HAR features
     m_k[t_lag], m_k_weekly_mean, m_k_monthly_mean  ← 3 features × K modes]
    Total: 3 + 3K features.
"""
from __future__ import annotations

import numpy as np
from sklearn.linear_model import Ridge

from chart_decomp.domain.entities import ForecastResult
from chart_decomp.domain.exceptions import (
    CausalityViolationError,
    InsufficientDataError,
    MissingDependencyError,
)
from chart_decomp.domain.value_objects import VMDHARParams
from chart_decomp.infrastructure.forecasting.har_forecaster import HARForecaster


def _require_vmdpy():
    try:
        import vmdpy  # noqa: F401
    except ImportError as exc:
        raise MissingDependencyError(
            "vmdpy is required for VMD-HAR: pip install vmdpy"
        ) from exc


class VMDHARForecaster:
    """Implements IForecaster for the VMD-augmented HAR model.

    Design patterns:
        Concrete Strategy.
        Extends HARForecaster logic via composition (not inheritance)
        so the HAR helper methods remain reusable.
    """

    def __init__(self) -> None:
        self._har = HARForecaster()

    def forecast(self, log_rv: np.ndarray, params: VMDHARParams | None = None) -> ForecastResult:
        """Walk-forward VMD-HAR forecast.

        Parameters
        ----------
        log_rv : 1-D float array, shape (N,)
        params : VMDHARParams; uses defaults if None

        Returns
        -------
        ForecastResult with predictions at timestamps where both the training
        window and edge_lag are satisfied.
        """
        _require_vmdpy()

        if params is None:
            params = VMDHARParams()
        log_rv = np.asarray(log_rv, dtype=np.float64)
        N = len(log_rv)

        if N < params.min_train + params.window + 2:
            raise InsufficientDataError(
                f"Series too short for VMD-HAR "
                f"(need min_train={params.min_train} + window={params.window})"
            )

        predictions = np.full(N, np.nan)
        actuals = np.full(N, np.nan)

        model: Ridge | None = None
        last_model_refit = -params.refit_model_every
        last_vmd_refit = -params.refit_vmd_every

        vmd_modes: np.ndarray | None = None
        vmd_window_lo = 0

        K = params.K
        feature_names = (
            ["log_rv_daily", "log_rv_weekly_mean", "log_rv_monthly_mean"]
            + [f"vmd_{k}_{s}" for k in range(K) for s in ("daily", "weekly", "monthly")]
        )

        for t in range(params.min_train, N - 1):
            HARForecaster._check_causality(t, N)

            # ── Causal VMD refit on trailing window ───────────────────────────
            if (t - last_vmd_refit) >= params.refit_vmd_every or vmd_modes is None:
                lo = max(0, t - params.window + 1)
                x_window = log_rv[lo : t + 1]  # strictly ≤ t
                vmd_modes, vmd_window_lo = self._fit_vmd(x_window, lo, params)
                last_vmd_refit = t

            # ── Read VMD features with edge_lag ───────────────────────────────
            lag_idx = (t - vmd_window_lo) - params.edge_lag
            if lag_idx < 21 or vmd_modes is None:
                # Not enough lag buffer; skip this step
                continue

            vmd_feat = self._vmd_features(vmd_modes, lag_idx, K)

            # ── HAR features at time t ────────────────────────────────────────
            har_feat = HARForecaster._build_features(log_rv, t)

            full_feat = np.concatenate([har_feat, vmd_feat])

            # ── Model refit if due ────────────────────────────────────────────
            if (t - last_model_refit) >= params.refit_model_every or model is None:
                model = self._fit_model(log_rv, t, params, feature_names)
                last_model_refit = t

            if model is None:
                continue

            predictions[t] = float(model.predict(full_feat.reshape(1, -1))[0])
            actuals[t] = log_rv[t + 1]

        mask = ~np.isnan(predictions)
        ts = np.where(mask)[0]
        preds = predictions[mask]
        acts = actuals[mask]

        metrics = HARForecaster._compute_metrics(preds, acts)
        return ForecastResult(
            timestamps=ts,
            predictions=preds,
            actuals=acts,
            metrics=metrics,
            features_used=feature_names,
        )

    # ── Helpers ────────────────────────────────────────────────────────────────

    @staticmethod
    def _fit_vmd(
        x_window: np.ndarray,
        window_lo: int,
        params: VMDHARParams,
    ) -> tuple[np.ndarray, int]:
        """Run VMD on x_window; return (modes sorted by center freq, window_lo)."""
        from vmdpy import VMD  # type: ignore

        u, _, omega = VMD(
            x_window,
            params.alpha,
            0.0,       # tau
            params.K,
            0,         # DC
            1,         # init uniform
            1e-7,      # tol
        )
        # omega: (n_iter, K) or (K,); take last row
        if omega.ndim == 2:
            omega = omega[-1]
        sort_idx = np.argsort(omega)
        return u[sort_idx], window_lo

    @staticmethod
    def _vmd_features(modes: np.ndarray, lag_idx: int, K: int) -> np.ndarray:
        """Build 3*K VMD feature vector at lag_idx."""
        feats = []
        for k in range(K):
            m = modes[k]
            feats.append(m[lag_idx])
            feats.append(float(np.mean(m[max(0, lag_idx - 4) : lag_idx + 1])))
            feats.append(float(np.mean(m[max(0, lag_idx - 21) : lag_idx + 1])))
        return np.array(feats, dtype=np.float64)

    def _fit_model(
        self,
        log_rv: np.ndarray,
        t_current: int,
        params: VMDHARParams,
        feature_names: list[str],
    ) -> Ridge | None:
        """Build training set up to t_current and fit Ridge."""
        from vmdpy import VMD  # type: ignore

        K = params.K
        X_rows, y_rows = [], []

        vmd_modes_cache: np.ndarray | None = None
        vmd_cache_lo = 0
        vmd_last_fit = -params.refit_vmd_every

        for t in range(params.min_train, t_current):
            if (t - vmd_last_fit) >= params.refit_vmd_every or vmd_modes_cache is None:
                lo = max(0, t - params.window + 1)
                x_win = log_rv[lo : t + 1]
                vmd_modes_cache, vmd_cache_lo = self._fit_vmd(x_win, lo, params)
                vmd_last_fit = t

            lag_idx = (t - vmd_cache_lo) - params.edge_lag
            if lag_idx < 21:
                continue

            vmd_feat = self._vmd_features(vmd_modes_cache, lag_idx, K)
            har_feat = HARForecaster._build_features(log_rv, t)
            X_rows.append(np.concatenate([har_feat, vmd_feat]))
            y_rows.append(log_rv[t + 1])

        if len(X_rows) < 10:
            return None
        X = np.vstack(X_rows)
        y = np.array(y_rows)
        return Ridge(alpha=params.ridge_alpha).fit(X, y)
