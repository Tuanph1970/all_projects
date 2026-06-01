"""F-053 — Parameter-set sensitivity report (Schwager Ch 15).

A single backtest "optimum" is meaningless if a one-step change in a parameter
collapses it.  This module re-runs the pipeline across the base config and its
immediate neighbours, reports the dispersion of a chosen metric, and flags
*fragile optima* so a robust parameter region — not a lucky spike — is what
gets trusted.

Public API
----------
run_param_sensitivity(base_config, bars, metric="total_net_pnl") -> SensitivityReport
classify_fragility(base_metric, neighbor_metrics) -> (fragile, stats, reason)
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from app.services.backtest.harness import (
    BacktestConfig,
    BacktestStats,
    run_backtest_on_bars,
)
from app.services.signal.base import OHLCVBar


# ---------------------------------------------------------------------------
# Output structures
# ---------------------------------------------------------------------------

@dataclass
class ParamVariant:
    label: str                 # "base" or e.g. "fast_ma=12"
    overrides: Dict[str, Any]  # params that differ from base ({} for base)
    metric: float
    stats: BacktestStats


@dataclass
class SensitivityReport:
    metric_name: str
    base_metric: float
    variants: List[ParamVariant] = field(default_factory=list)
    mean: float = 0.0
    std: float = 0.0
    cv: float = 0.0            # coefficient of variation = std / |mean|
    min: float = 0.0
    max: float = 0.0
    fragile: bool = False
    reason: str = ""


# ---------------------------------------------------------------------------
# Neighbour grid
# ---------------------------------------------------------------------------

def _grid_neighbors(base: BacktestConfig) -> List[Tuple[str, Dict[str, Any]]]:
    """One-at-a-time ± perturbations of the tunable parameters.

    Only emits neighbours that stay valid (fast_ma ≥ 2, fast_ma < slow_ma,
    breakout_n ≥ 5).  With the default config this yields 6 neighbours.
    """
    candidates: List[Tuple[str, Dict[str, Any]]] = [
        ("fast_ma", {"fast_ma": base.fast_ma - 2}),
        ("fast_ma", {"fast_ma": base.fast_ma + 2}),
        ("slow_ma", {"slow_ma": base.slow_ma - 5}),
        ("slow_ma", {"slow_ma": base.slow_ma + 5}),
        ("breakout_n", {"breakout_n": base.breakout_n - 5}),
        ("breakout_n", {"breakout_n": base.breakout_n + 5}),
    ]

    valid: List[Tuple[str, Dict[str, Any]]] = []
    for param, override in candidates:
        merged = {**base.__dict__, **override}
        if merged["fast_ma"] < 2 or merged["fast_ma"] >= merged["slow_ma"]:
            continue
        if merged["breakout_n"] < 5:
            continue
        key, val = next(iter(override.items()))
        valid.append((f"{key}={val}", override))
    return valid


def _metric_of(stats: BacktestStats, name: str) -> float:
    """Read a metric off BacktestStats; None (e.g. sharpe with <3 points) → 0.0."""
    value = getattr(stats, name, None)
    return float(value) if value is not None else 0.0


def _with_overrides(base: BacktestConfig, overrides: Dict[str, Any]) -> BacktestConfig:
    return BacktestConfig(**{**base.__dict__, **overrides})


# ---------------------------------------------------------------------------
# Fragility classification
# ---------------------------------------------------------------------------

def classify_fragility(
    base_metric: float,
    neighbor_metrics: List[float],
    *,
    cv_threshold: float = 0.5,
    drop_threshold: float = 0.4,
) -> Tuple[bool, Dict[str, Any], str]:
    """Decide whether the base optimum is fragile.

    Fragile when either:
      * dispersion is high — coefficient of variation across all variants
        ≥ ``cv_threshold`` (the neighbourhood is unstable), or
      * the base is the unique peak — it is the best variant AND sits
        ``drop_threshold`` (fractionally) above the neighbour mean.
    """
    all_metrics = [base_metric] + list(neighbor_metrics)
    n = len(all_metrics)
    mean_all = sum(all_metrics) / n if n else 0.0
    std_all = statistics.stdev(all_metrics) if n > 1 else 0.0
    if mean_all != 0:
        cv = abs(std_all / mean_all)
    else:
        cv = 0.0 if std_all == 0 else float("inf")

    neighbor_mean = (sum(neighbor_metrics) / len(neighbor_metrics)) if neighbor_metrics else base_metric
    base_is_best = base_metric >= max(all_metrics)
    drop = ((base_metric - neighbor_mean) / abs(base_metric)) if base_metric != 0 else 0.0

    high_dispersion = cv >= cv_threshold
    sharp_peak = base_is_best and drop >= drop_threshold
    fragile = high_dispersion or sharp_peak

    if not fragile:
        reason = "stable: neighbours track the base within tolerance"
    elif high_dispersion and sharp_peak:
        reason = f"fragile: high dispersion (cv={cv:.2f}) and base is a sharp peak (drop={drop:.2f})"
    elif high_dispersion:
        reason = f"fragile: high dispersion across neighbours (cv={cv:.2f})"
    else:
        reason = f"fragile: base is a sharp peak {drop:.2f} above neighbour mean"

    stats = {
        "mean": round(mean_all, 4),
        "std": round(std_all, 4),
        "cv": round(cv, 4) if cv != float("inf") else cv,
        "neighbor_mean": round(neighbor_mean, 4),
        "base_is_best": base_is_best,
        "drop": round(drop, 4),
    }
    return fragile, stats, reason


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def run_param_sensitivity(
    base_config: BacktestConfig,
    bars: List[OHLCVBar],
    *,
    metric: str = "total_net_pnl",
    cv_threshold: float = 0.5,
    drop_threshold: float = 0.4,
) -> SensitivityReport:
    """Backtest the base config and its neighbours; report metric dispersion."""
    variants: List[ParamVariant] = []

    base_result = run_backtest_on_bars(base_config, bars)
    base_metric = _metric_of(base_result.stats, metric)
    variants.append(ParamVariant("base", {}, base_metric, base_result.stats))

    neighbor_metrics: List[float] = []
    for label, overrides in _grid_neighbors(base_config):
        cfg = _with_overrides(base_config, overrides)
        res = run_backtest_on_bars(cfg, bars)
        m = _metric_of(res.stats, metric)
        neighbor_metrics.append(m)
        variants.append(ParamVariant(label, overrides, m, res.stats))

    fragile, frag_stats, reason = classify_fragility(
        base_metric, neighbor_metrics,
        cv_threshold=cv_threshold, drop_threshold=drop_threshold,
    )

    all_metrics = [v.metric for v in variants]
    return SensitivityReport(
        metric_name=metric,
        base_metric=base_metric,
        variants=variants,
        mean=frag_stats["mean"],
        std=frag_stats["std"],
        cv=frag_stats["cv"],
        min=round(min(all_metrics), 4),
        max=round(max(all_metrics), 4),
        fragile=fragile,
        reason=reason,
    )
