"""jumps/ — Lee-Mykland jump test, daily variant (FR-JUMP, EC4, EC5).

Pure stats stage: NO I/O. Statistic L_t = r_t / sigma_local(t), where sigma_local is a
bipower-variation estimate of local diffusive volatility from a trailing daily-return
window ending STRICTLY before t0 (EC1) — reusing the return/vol conventions of the
in-repo chart_decomp package for the surrogate null.

Threshold choice (documented, EC5): the event day is *pre-specified*, not scanned, so
we use a single-test two-sided normal critical value rather than Lee-Mykland's Gumbel
max-threshold (which corrects for scanning every day). This keeps the per-event false-
positive rate at the nominal `level` (verified against a random-walk null). The Gumbel
scanning threshold is a deferred option. As a daily variant, power is reduced vs the
intraday original (EC5).
"""
from __future__ import annotations

import numpy as np
from scipy.stats import norm

from chart_decomp.infrastructure.validation.surrogates import make_surrogate

from event_reaction.exceptions import InsufficientDataError
from event_reaction.types import JumpTest

_MU1 = np.sqrt(2.0 / np.pi)  # E|Z| for standard normal


def _as_array(x) -> np.ndarray:
    return x.to_numpy(dtype=float) if hasattr(x, "to_numpy") else np.asarray(x, dtype=float)


def _local_bipower_vol(r: np.ndarray, pos: int, K: int) -> float:
    """Bipower local volatility from the K returns strictly before ``pos``."""
    if pos - K < 0:
        raise InsufficientDataError(
            f"need {K} returns before t0 for local vol (pos={pos})"
        )
    w = r[pos - K:pos]
    prods = np.abs(w[1:]) * np.abs(w[:-1])
    bpv = float(np.mean(prods))
    return float(np.sqrt(bpv) / _MU1)


def _null_fpr(r: np.ndarray, *, level: float, K: int, n_null: int, seed: int) -> float:
    """Empirical single-test FPR on gaussian random-walk surrogates (EC4).

    Reuses chart_decomp.make_surrogate (gaussian) to build null return paths.
    """
    if n_null <= 0:
        return float("nan")
    thr = float(norm.ppf(1.0 - level / 2.0))
    count = used = 0
    for s in range(n_null):
        price = make_surrogate(r, method="gaussian", seed=seed + s)
        sur = np.diff(price)
        pos = len(sur) - 1
        if pos < K:
            continue
        sigma = _local_bipower_vol(sur, pos, K)
        if sigma <= 0:
            continue
        count += int(abs(sur[pos] / sigma) > thr)
        used += 1
    return count / used if used else float("nan")


def jump_test_daily(
    asset_logret,
    t0_index: int,
    *,
    level: float = 0.01,
    local_window: int = 21,
    n_null: int = 0,
    seed: int = 0,
) -> JumpTest:
    """Lee-Mykland daily jump test at ``t0_index`` (FR-JUMP).

    Parameters
    ----------
    asset_logret : daily log-return series/array (returns-index space).
    t0_index : position of the event-day return.
    level : test level (two-sided).
    local_window : trailing daily-return window K for local vol (EC5).
    n_null : if > 0, also compute the random-walk-null FPR over this many surrogates (EC4).
    seed : surrogate seed (EC7).
    """
    r = _as_array(asset_logret)
    if not 0 <= t0_index < len(r):
        raise InsufficientDataError(f"t0_index {t0_index} out of range")
    sigma_local = _local_bipower_vol(r, t0_index, local_window)
    if sigma_local <= 0:
        raise InsufficientDataError("degenerate (zero) local volatility")

    statistic = float(r[t0_index] / sigma_local)
    threshold = float(norm.ppf(1.0 - level / 2.0))
    is_jump = bool(abs(statistic) > threshold)
    null_fpr = _null_fpr(r, level=level, K=local_window, n_null=n_null, seed=seed)

    return JumpTest(
        statistic=statistic,
        threshold=threshold,
        is_jump=is_jump,
        sigma_local=sigma_local,
        null_fpr=null_fpr,
    )
