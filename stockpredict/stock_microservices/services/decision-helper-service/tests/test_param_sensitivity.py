"""F-053 — Parameter-set sensitivity report (Schwager Ch 15).

Runs the base parameter set plus its immediate neighbours through the backtest
harness, reports the dispersion of a chosen metric, and flags *fragile optima*
— a base config that only looks good because it sits on a sharp peak that its
neighbours fall off.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import List

import pytest

from app.services.backtest.harness import BacktestConfig
from app.services.signal.base import OHLCVBar
from app.services.backtest.sensitivity import (
    SensitivityReport,
    classify_fragility,
    run_param_sensitivity,
    _grid_neighbors,
    _metric_of,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _base_config():
    return BacktestConfig(
        ticker="VCB",
        start_date=date(2023, 1, 2),
        end_date=date(2023, 6, 30),
        fast_ma=10, slow_ma=50, breakout_n=20,
    )


def _trend_bars(n: int, step: float = 0.5, start_price: float = 50.0):
    bars = []
    price = start_price
    d = date(2022, 1, 3)
    for i in range(n):
        bars.append(OHLCVBar(date=d + timedelta(days=i), open=price, high=price + step,
                             low=price - 0.1, close=price + step, volume=1_000_000))
        price += step
    return bars


# ---------------------------------------------------------------------------
# Grid generation — "5+ neighbouring parameter sets"
# ---------------------------------------------------------------------------

def test_grid_generates_at_least_five_valid_neighbours():
    neighbours = _grid_neighbors(_base_config())
    assert len(neighbours) >= 5
    for label, overrides in neighbours:
        merged = {**_base_config().__dict__, **overrides}
        assert merged["fast_ma"] >= 2
        assert merged["fast_ma"] < merged["slow_ma"]
        assert merged["breakout_n"] >= 5
        assert isinstance(label, str) and label


# ---------------------------------------------------------------------------
# Metric extraction
# ---------------------------------------------------------------------------

def test_metric_of_handles_missing_sharpe():
    from app.services.backtest.harness import _empty_stats
    stats = _empty_stats()  # sharpe_ratio is None
    assert _metric_of(stats, "sharpe_ratio") == 0.0
    assert _metric_of(stats, "total_net_pnl") == 0.0


# ---------------------------------------------------------------------------
# Fragility classification (pure)
# ---------------------------------------------------------------------------

def test_stable_neighbourhood_not_fragile():
    fragile, stats, _ = classify_fragility(100.0, [98.0, 102.0, 99.0, 101.0, 100.0])
    assert fragile is False
    assert stats["cv"] < 0.5


def test_high_dispersion_is_fragile():
    fragile, stats, reason = classify_fragility(100.0, [10.0, -50.0, 200.0, -30.0, 5.0])
    assert fragile is True
    assert stats["cv"] >= 0.5


def test_sharp_peak_is_fragile():
    # Base is the clear best; neighbours collapse → fragile optimum.
    fragile, stats, reason = classify_fragility(200.0, [20.0, 25.0, 18.0, 22.0, 19.0])
    assert fragile is True
    assert stats["base_is_best"] is True


def test_all_zero_not_fragile():
    fragile, stats, _ = classify_fragility(0.0, [0.0, 0.0, 0.0, 0.0, 0.0])
    assert fragile is False
    assert stats["cv"] == 0.0


# ---------------------------------------------------------------------------
# End-to-end report
# ---------------------------------------------------------------------------

def test_report_runs_base_plus_neighbours():
    bars = _trend_bars(400)
    report = run_param_sensitivity(_base_config(), bars, metric="total_net_pnl")
    assert isinstance(report, SensitivityReport)
    assert report.metric_name == "total_net_pnl"
    # base + at least 5 neighbours all evaluated
    assert len(report.variants) >= 6
    assert any(v.label == "base" for v in report.variants)
    # dispersion stats present and consistent
    assert report.max >= report.min
    assert report.std >= 0.0
    assert isinstance(report.fragile, bool)


def test_report_flat_market_is_not_fragile():
    # Flat bars → every param set trades nothing → zero metric everywhere.
    flat = [OHLCVBar(date=date(2022, 1, 3) + timedelta(days=i), open=100, high=100.1,
                     low=99.9, close=100, volume=1_000_000) for i in range(400)]
    report = run_param_sensitivity(_base_config(), flat, metric="total_net_pnl")
    assert report.fragile is False
    assert report.std == 0.0
