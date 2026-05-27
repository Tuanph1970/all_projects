"""CD-506 — End-to-end Heston stochastic-volatility path test.

Generates a 2500-day Heston SV path (seeded, reproducible) and validates the
full forecasting + backtest pipeline end-to-end.

Acceptance criteria (SRS §5.4):
  1. HAR achieves OOS R² ≥ 0.85 on the Heston log-variance series.
  2. Vol-targeting backtest: 30-day rolling annualised vol is within ±30% of the
     target (15%) on at least 70% of valid rolling-window days.
  3. VMD-HAR RMSE is within ±10% of HAR RMSE (look-ahead regression guard).
     — skipped automatically when vmdpy is not installed.

Marked @pytest.mark.slow — excluded from quick-test.sh.
"""
from __future__ import annotations

import numpy as np
import pytest

import chart_decomp as cd


# ── Heston model parameters ────────────────────────────────────────────────────

_N = 2500
_SEED = 42
_KAPPA = 2.0       # mean-reversion speed (half-life ≈ 90 trading days)
_THETA = 0.04      # long-run variance  → ~20% annual vol
_SIGMA_V = 0.3     # vol-of-vol  (Feller satisfied: 2κθ=0.16 > σ_v²=0.09)
_V0 = 0.04         # initial variance (= θ, start at long-run mean)
_TARGET_VOL = 0.15 # vol-targeting strategy target (annualised)
_DT = 1.0 / 252    # daily step


# ── Path generator ─────────────────────────────────────────────────────────────

def _heston_path(
    N: int = _N,
    kappa: float = _KAPPA,
    theta: float = _THETA,
    sigma_v: float = _SIGMA_V,
    V0: float = _V0,
    seed: int = _SEED,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Euler-Maruyama Heston variance path.

    Returns
    -------
    V       : daily variance process, shape (N,)
    returns : daily price returns √V_t * ε, shape (N,)
    log_rv  : log(V_t), shape (N,)  — used as the "realised variance" series
    """
    rng = np.random.default_rng(seed)
    dt = _DT
    V = np.empty(N)
    V[0] = V0
    for t in range(1, N):
        v_pos = max(V[t - 1], 0.0)
        drift = kappa * (theta - v_pos) * dt
        diffusion = sigma_v * np.sqrt(v_pos * dt) * rng.standard_normal()
        V[t] = max(V[t - 1] + drift + diffusion, 1e-8)

    returns = np.sqrt(V) * rng.standard_normal(N)
    log_rv = np.log(V)
    return V, returns, log_rv


# ── Shared path (generated once via module-level cache) ───────────────────────

_HESTON = None


def _get_heston():
    global _HESTON
    if _HESTON is None:
        _HESTON = _heston_path()
    return _HESTON


# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.slow
class TestHarOnHestonPath:
    """HAR walk-forward forecast on Heston log-variance — R² ≥ 0.85 OOS."""

    def test_har_r2_oos(self):
        _V, _returns, log_rv = _get_heston()

        result = cd.har_forecast(log_rv)

        r2 = result.metrics["r2"]
        assert r2 >= 0.85, (
            f"HAR OOS R²={r2:.4f} on Heston path failed threshold 0.85. "
            "Check that log(V_t) from the Heston simulation is sufficiently "
            "autocorrelated (κ={_KAPPA}, N={_N})."
        )

    def test_har_metrics_finite(self):
        _V, _returns, log_rv = _get_heston()
        result = cd.har_forecast(log_rv)
        for key in ("rmse", "mae", "r2", "qlike"):
            assert np.isfinite(result.metrics[key]), f"Metric {key} is not finite"

    def test_har_predictions_count(self):
        _V, _returns, log_rv = _get_heston()
        result = cd.har_forecast(log_rv)
        # At least 50% of days should have predictions (excludes warmup)
        assert len(result.predictions) >= _N // 2


@pytest.mark.slow
class TestVolTargetBacktest:
    """Vol-targeting backtest driven by HAR forecasts — rolling vol within ±30% target."""

    def _build_vol_forecast(self, har_result, N: int, default_vol: float) -> np.ndarray:
        """Expand HAR predictions into a full-length annualised vol array."""
        vol_fc = np.full(N, default_vol)
        for i, t in enumerate(har_result.timestamps):
            vol_fc[t] = np.sqrt(np.exp(har_result.predictions[i]) * 252)
        return vol_fc

    def test_rolling_vol_within_band(self):
        """30-day rolling vol of net PnL must be within ±30% of target on ≥70% of days."""
        _V, returns, log_rv = _get_heston()

        har_result = cd.har_forecast(log_rv)

        default_vol = np.sqrt(_THETA * 252)  # fallback before HAR warms up
        vol_fc = self._build_vol_forecast(har_result, _N, default_vol)

        bt = cd.vol_target_backtest(returns, vol_fc, target_ann_vol=_TARGET_VOL)

        # 30-day rolling annualised vol of daily net PnL
        window = 30
        pnl = bt.pnl_net
        # Start computing after HAR warmup so default-vol sizing doesn't bias results
        warmup = int(har_result.timestamps[0]) + window
        pnl_oos = pnl[warmup:]
        n = len(pnl_oos)
        assert n >= 200, f"Too few OOS days ({n}) for rolling vol test"

        roll_vol = np.array([
            np.std(pnl_oos[max(0, i - window + 1) : i + 1]) * np.sqrt(252)
            for i in range(n)
        ])
        valid = roll_vol[window - 1:]  # drop first window-1 partially-filled windows
        assert len(valid) >= 100, "Not enough valid rolling-window days"

        lo, hi = 0.70 * _TARGET_VOL, 1.30 * _TARGET_VOL
        in_band = np.sum((valid >= lo) & (valid <= hi))
        frac = in_band / len(valid)

        assert frac >= 0.70, (
            f"Only {frac:.1%} of rolling-vol days within ±30% of target "
            f"({lo:.3f}–{hi:.3f}). Need ≥70%."
        )

    def test_backtest_metrics_present(self):
        _V, returns, log_rv = _get_heston()
        har_result = cd.har_forecast(log_rv)
        default_vol = np.sqrt(_THETA * 252)
        vol_fc = self._build_vol_forecast(har_result, _N, default_vol)
        bt = cd.vol_target_backtest(returns, vol_fc, target_ann_vol=_TARGET_VOL)
        for key in ("ann_ret", "ann_vol", "sharpe", "maxdd", "avg_leverage"):
            assert key in bt.metrics


@pytest.mark.slow
class TestVmdHarLookAheadGuard:
    """VMD-HAR RMSE must stay within ±10% of HAR RMSE (accidental look-ahead guard).

    Skipped when vmdpy is not installed.
    """

    @pytest.fixture(autouse=True)
    def require_vmdpy(self):
        pytest.importorskip("vmdpy", reason="vmdpy not installed — skipping VMD-HAR guard")

    def test_vmd_har_rmse_within_10pct_of_har(self):
        _V, _returns, log_rv = _get_heston()

        har_result = cd.har_forecast(log_rv)
        vmd_har_result = cd.vmd_har_forecast(
            log_rv,
            K=4,
            alpha=1500.0,
            window=1000,
            refit_vmd_every=20,
            refit_model_every=60,
            edge_lag=5,
        )

        har_rmse = har_result.metrics["rmse"]
        vmd_rmse = vmd_har_result.metrics["rmse"]

        assert har_rmse > 0, "HAR RMSE must be positive"
        ratio = vmd_rmse / har_rmse

        assert ratio >= 0.90, (
            f"VMD-HAR RMSE ({vmd_rmse:.5f}) is more than 10% better than HAR "
            f"({har_rmse:.5f}, ratio={ratio:.3f}). Possible accidental look-ahead."
        )
        assert ratio <= 1.10, (
            f"VMD-HAR RMSE ({vmd_rmse:.5f}) is more than 10% worse than HAR "
            f"({har_rmse:.5f}, ratio={ratio:.3f}). Check VMD-HAR implementation."
        )

    def test_vmd_har_metrics_finite(self):
        _V, _returns, log_rv = _get_heston()
        result = cd.vmd_har_forecast(log_rv, K=4, window=1000)
        for key in ("rmse", "mae", "r2", "qlike"):
            assert np.isfinite(result.metrics[key]), f"VMD-HAR metric {key} is not finite"
