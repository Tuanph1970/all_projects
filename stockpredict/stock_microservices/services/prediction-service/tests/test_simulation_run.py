"""Coverage for POST /simulation/run + SimulationService (Backlog: simulation dashboard).

The service is exercised directly with a mocked price fetch (no network / DB),
asserting the full SimulationResult shape the frontend consumes. The route is
exercised with the service mocked.
"""
import numpy as np
import pandas as pd
import pytest
from datetime import date
from unittest.mock import AsyncMock, patch

from app.services.simulation_service import SimulationService, SimulationError
from app.models.schemas import (
    SimulationRequest,
    SimulationTradingParams,
    SimulationResult,
    SimulationPortfolioMetrics,
    SimulationPredictionAccuracy,
)

PREFIX = "/stock_helper/api/v2/predict"


def _synthetic_prices(n: int = 320, start: str = "2022-06-01", seed: int = 7) -> pd.DataFrame:
    """A trending+noisy OHLCV series with enough rows to train + simulate."""
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range(start=start, periods=n)
    # Upward drift + sinusoid + noise → a learnable next-day target.
    t = np.arange(n)
    close = 50.0 + 0.05 * t + 3.0 * np.sin(t / 12.0) + rng.normal(0, 0.7, n)
    close = np.maximum(close, 1.0)
    high = close + np.abs(rng.normal(0.5, 0.3, n))
    low = close - np.abs(rng.normal(0.5, 0.3, n))
    open_ = close + rng.normal(0, 0.4, n)
    volume = rng.integers(100_000, 500_000, n).astype(float)
    return pd.DataFrame({
        "date": dates, "open": open_, "high": high,
        "low": low, "close": close, "volume": volume,
    })


def _service_with_prices(df: pd.DataFrame) -> SimulationService:
    svc = SimulationService(session=AsyncMock())
    svc._fetch_range = AsyncMock(return_value=df)
    return svc


# ── Service: happy path ───────────────────────────────────────────────────────

class TestSimulationServiceHappyPath:
    @pytest.fixture
    def req(self):
        return SimulationRequest(
            ticker="VNM",
            start_date=date(2023, 1, 2),
            end_date=date(2023, 6, 30),
            initial_capital=100_000_000,
            model_type="Linear Regression",   # deterministic, fast, no native deps
            trading_params=SimulationTradingParams(
                threshold_buy=0.01, threshold_sell=-0.01, position_size=0.3,
            ),
        )

    @pytest.mark.asyncio
    async def test_returns_simulation_result(self, req):
        svc = _service_with_prices(_synthetic_prices())
        result = await svc.run_simulation(req)
        assert isinstance(result, SimulationResult)
        assert result.ticker == "VNM"
        assert isinstance(result.portfolio_metrics, SimulationPortfolioMetrics)
        assert isinstance(result.prediction_accuracy, SimulationPredictionAccuracy)

    @pytest.mark.asyncio
    async def test_time_series_spans_simulation_window(self, req):
        svc = _service_with_prices(_synthetic_prices())
        result = await svc.run_simulation(req)
        assert len(result.time_series) >= 2
        # Every point carries actual + predicted prices.
        for pt in result.time_series:
            assert pt.actual_price > 0
            assert pt.predicted_price is not None
        # Dates are within the requested window.
        first = result.time_series[0].date
        last = result.time_series[-1].date
        assert first >= "2023-01-02"
        assert last <= "2023-06-30"

    @pytest.mark.asyncio
    async def test_metrics_are_internally_consistent(self, req):
        svc = _service_with_prices(_synthetic_prices())
        m = (await svc.run_simulation(req)).portfolio_metrics
        assert m.initial_capital == pytest.approx(100_000_000)
        # total_return = final - initial
        assert m.total_return == pytest.approx(m.final_value - m.initial_capital, abs=1.0)
        # total_return_pct consistent with the absolute return
        assert m.total_return_pct == pytest.approx(
            m.total_return / m.initial_capital * 100, abs=0.1
        )
        assert 0.0 <= m.win_rate <= 100.0
        assert m.max_drawdown <= 0.0          # drawdown is non-positive
        assert m.total_trades >= 0

    @pytest.mark.asyncio
    async def test_accuracy_in_valid_ranges(self, req):
        svc = _service_with_prices(_synthetic_prices())
        acc = (await svc.run_simulation(req)).prediction_accuracy
        assert 0.0 <= acc.direction_accuracy <= 100.0
        assert acc.mape >= 0.0

    @pytest.mark.asyncio
    async def test_transactions_have_buy_or_sell_types(self, req):
        svc = _service_with_prices(_synthetic_prices())
        result = await svc.run_simulation(req)
        for tx in result.transaction_history:
            assert tx.type in ("BUY", "SELL")
            assert tx.price > 0
            assert tx.cash_balance >= -1.0   # never spends below zero cash

    @pytest.mark.asyncio
    async def test_no_trades_when_thresholds_unreachable(self, req):
        # Absurdly high buy threshold → predicted return never qualifies.
        req.trading_params = SimulationTradingParams(
            threshold_buy=10.0, threshold_sell=-10.0, position_size=0.3,
        )
        svc = _service_with_prices(_synthetic_prices())
        result = await svc.run_simulation(req)
        assert result.transaction_history == []
        # Cash untouched → final value equals initial.
        assert result.portfolio_metrics.final_value == pytest.approx(100_000_000, abs=1.0)


# ── Service: model families ───────────────────────────────────────────────────

class TestModelFamilies:
    @pytest.mark.parametrize("model_name", [
        "XGBoost", "LightGBM", "Random Forest", "Linear Regression", "LSTM", "unknown",
    ])
    @pytest.mark.asyncio
    async def test_all_model_names_run(self, model_name):
        req = SimulationRequest(
            ticker="FPT", start_date=date(2023, 1, 2), end_date=date(2023, 5, 1),
            model_type=model_name,
        )
        svc = _service_with_prices(_synthetic_prices())
        result = await svc.run_simulation(req)
        assert isinstance(result, SimulationResult)


# ── Service: error paths ──────────────────────────────────────────────────────

class TestSimulationErrors:
    @pytest.mark.asyncio
    async def test_insufficient_data_raises(self):
        req = SimulationRequest(
            ticker="X", start_date=date(2023, 1, 2), end_date=date(2023, 6, 1),
        )
        svc = _service_with_prices(_synthetic_prices(n=40))  # < 80 rows
        with pytest.raises(SimulationError, match="Insufficient historical data"):
            await svc.run_simulation(req)

    @pytest.mark.asyncio
    async def test_none_data_raises(self):
        req = SimulationRequest(
            ticker="X", start_date=date(2023, 1, 2), end_date=date(2023, 6, 1),
        )
        svc = SimulationService(session=AsyncMock())
        svc._fetch_range = AsyncMock(return_value=None)
        with pytest.raises(SimulationError):
            await svc.run_simulation(req)

    @pytest.mark.asyncio
    async def test_end_before_start_raises(self):
        req = SimulationRequest(
            ticker="X", start_date=date(2023, 6, 1), end_date=date(2023, 1, 1),
        )
        svc = _service_with_prices(_synthetic_prices())
        with pytest.raises(SimulationError, match="end_date must be after"):
            await svc.run_simulation(req)

    @pytest.mark.asyncio
    async def test_start_too_late_leaves_no_training_rows(self):
        # start_date before the data even begins → no training rows.
        req = SimulationRequest(
            ticker="X", start_date=date(2000, 1, 1), end_date=date(2000, 6, 1),
        )
        svc = _service_with_prices(_synthetic_prices())
        with pytest.raises(SimulationError):
            await svc.run_simulation(req)


# ── Route ─────────────────────────────────────────────────────────────────────

class TestSimulationRoute:
    @pytest.mark.asyncio
    async def test_run_endpoint_returns_result(self, client):
        fake = SimulationResult(
            ticker="VNM", model_type="XGBoost",
            portfolio_metrics=SimulationPortfolioMetrics(
                initial_capital=1e8, final_value=1.1e8, total_return=1e7,
                total_return_pct=10.0, total_trades=4, win_rate=75.0,
                sharpe_ratio=1.2, max_drawdown=-5.0, alpha=2.0,
            ),
            prediction_accuracy=SimulationPredictionAccuracy(
                direction_accuracy=58.0, mape=3.1,
            ),
            time_series=[], transaction_history=[],
        )
        with patch.object(SimulationService, "run_simulation", new=AsyncMock(return_value=fake)):
            r = await client.post(f"{PREFIX}/simulation/run", json={
                "ticker": "VNM", "start_date": "2023-01-02", "end_date": "2023-06-30",
                "initial_capital": 100000000, "model_type": "XGBoost",
                "trading_params": {"threshold_buy": 0.02, "threshold_sell": -0.01, "position_size": 0.3},
            })
        assert r.status_code == 200
        body = r.json()
        assert body["portfolio_metrics"]["total_return_pct"] == 10.0
        assert body["prediction_accuracy"]["direction_accuracy"] == 58.0

    @pytest.mark.asyncio
    async def test_run_endpoint_422_on_simulation_error(self, client):
        with patch.object(
            SimulationService, "run_simulation",
            new=AsyncMock(side_effect=SimulationError("Insufficient historical data")),
        ):
            r = await client.post(f"{PREFIX}/simulation/run", json={
                "ticker": "ZZZ", "start_date": "2023-01-02", "end_date": "2023-06-30",
            })
        assert r.status_code == 422
        assert "Insufficient" in r.json()["detail"]
