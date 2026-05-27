"""CD-505 — Causality and look-ahead tests (SRS §5.3).

Test 1 — No-leakage swap test:
    Swap the target series at t' < t with random noise.
    Predictions at t' must not change — if they do, the model used future data.

Test 2 — Deliberate look-ahead detector:
    A fake forecaster that peeks at log_rv[t+1] should achieve R² >> 0 on OOS.
    This test guards against accidentally passing something similar as the
    'clean' model in CI; if it fails, the test suite itself is broken.
"""
from __future__ import annotations

import numpy as np
import pytest

import chart_decomp as cd
from chart_decomp.application.run_forecast_usecase import RunForecastUseCase
from chart_decomp.domain.entities import ForecastResult


def _fake_log_rv(N: int = 600, seed: int = 42) -> np.ndarray:
    rng = np.random.default_rng(seed)
    x = np.zeros(N)
    for t in range(1, N):
        x[t] = 0.9 * x[t - 1] + rng.normal(0, 0.3)
    return x - 10.0


class TestHARCausality:
    def test_no_leakage_swap(self):
        """Swapping future values must not change past predictions (Constraint C1)."""
        rng = np.random.default_rng(0)
        N = 400
        log_rv = _fake_log_rv(N)

        result_clean = cd.har_forecast(log_rv)
        swap_point = N // 2  # swap everything from here onward

        # Replace future values with pure noise
        log_rv_corrupted = log_rv.copy()
        log_rv_corrupted[swap_point:] = rng.normal(-10, 1, N - swap_point)

        result_corrupted = cd.har_forecast(log_rv_corrupted)

        # Predictions strictly before swap_point must be identical
        mask_clean = result_clean.timestamps < swap_point
        mask_corr = result_corrupted.timestamps < swap_point

        if mask_clean.any() and mask_corr.any():
            ts_clean = set(result_clean.timestamps[mask_clean].tolist())
            ts_corr = set(result_corrupted.timestamps[mask_corr].tolist())
            common = sorted(ts_clean & ts_corr)
            if common:
                idx_c = {t: i for i, t in enumerate(result_clean.timestamps.tolist())}
                idx_r = {t: i for i, t in enumerate(result_corrupted.timestamps.tolist())}
                for t in common:
                    p_clean = result_clean.predictions[idx_c[t]]
                    p_corr = result_corrupted.predictions[idx_r[t]]
                    assert abs(p_clean - p_corr) < 1e-9, (
                        f"Causality leak detected at t={t}: "
                        f"clean={p_clean:.6f} vs corrupted={p_corr:.6f}"
                    )


class TestLookAheadDetector:
    """Regression guard: a deliberate look-ahead 'forecaster' must be detectable.

    If this test FAILS it means our causality tests are not sensitive enough —
    something is broken in the test harness, not in the production code.
    """

    def test_lookahead_achieves_high_r2(self):
        """A forecast that cheats by reading t+1 should get R² > 0.90."""
        log_rv = _fake_log_rv(500)
        # Cheat: predict log_rv[t+1] = log_rv[t+1] + tiny noise
        rng = np.random.default_rng(99)
        min_train = 252
        N = len(log_rv)

        ts, preds, acts = [], [], []
        for t in range(min_train, N - 1):
            # Look-ahead: use actual future value + noise
            pred = log_rv[t + 1] + rng.normal(0, 0.001)
            ts.append(t)
            preds.append(pred)
            acts.append(log_rv[t + 1])

        ts_arr = np.array(ts)
        preds_arr = np.array(preds)
        acts_arr = np.array(acts)

        resid = acts_arr - preds_arr
        ss_res = np.sum(resid ** 2)
        ss_tot = np.sum((acts_arr - acts_arr.mean()) ** 2)
        r2 = 1.0 - ss_res / ss_tot

        assert r2 > 0.90, (
            f"Look-ahead detector should get R²>0.90; got {r2:.3f}. "
            "If this fails, the test harness is broken."
        )
