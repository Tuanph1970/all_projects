"""Extra coverage for app.services.prediction_service.PredictionService.

Picks up the train_model happy + failure paths and the predict() success
loop that the original test_prediction_service.py left at the front
door. We never train a real model — joblib.dump/load and the sklearn
fit/predict calls are mocked.
"""
from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from app.models.domain import MLModel, ModelStatus, ModelType
from app.services.prediction_service import PredictionService


def _make_service(session=None) -> PredictionService:
    return PredictionService(session if session is not None else AsyncMock())


def _ohlcv_df(rows: int = 200, seed: int = 13) -> pd.DataFrame:
    """Long enough OHLCV series that _prepare_features keeps >>30 rows
    after the 50-bar rolling windows + target shift + dropna."""
    dates = pd.date_range("2026-01-01", periods=rows, freq="D")
    rng = np.random.default_rng(seed)
    close = 100 + np.cumsum(rng.normal(0, 1.0, size=rows))
    return pd.DataFrame(
        {
            "date": dates,
            "open": close + rng.normal(0, 0.2, size=rows),
            "high": close + 1.0,
            "low": close - 1.0,
            "close": close,
            "volume": rng.integers(1_000, 5_000, size=rows),
        }
    )


# ---------------------------------------------------------------------------
# _get_current_price — exception branch
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_current_price_swallows_exceptions():
    """A network exception in the httpx call returns None, not a raise."""
    class Boom:
        async def __aenter__(self):
            raise ConnectionError("network down")

        async def __aexit__(self, *_):
            return False

    with patch("app.services.prediction_service.httpx.AsyncClient", return_value=Boom()):
        svc = _make_service()
        assert await svc._get_current_price("FPT") is None


# ---------------------------------------------------------------------------
# train_model — full happy path with mocked ML libs
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("model_type", [
    ModelType.XGBOOST,
    ModelType.LIGHTGBM,
    ModelType.RANDOM_FOREST,
    ModelType.LINEAR_REGRESSION,
])
@pytest.mark.asyncio
async def test_train_model_happy_path_per_family(model_type, tmp_path, monkeypatch):
    """Drive every ML-family branch of train_model. We never actually fit
    a model — the constructor returns a MagicMock whose .fit / .predict
    are no-ops."""
    svc = _make_service()
    df = _ohlcv_df(200)

    # Patch every external + heavy bit.
    monkeypatch.setattr(
        svc, "_fetch_historical_data", AsyncMock(return_value=df)
    )
    created_model = MagicMock(id=42)
    log = MagicMock(id=99)
    svc.repo.create_model = AsyncMock(return_value=created_model)
    svc.repo.create_training_log = AsyncMock(return_value=log)
    svc.repo.update_model = AsyncMock()
    svc.repo.complete_training_log = AsyncMock()
    svc.repo.deactivate_old_models = AsyncMock()

    # Each ML constructor returns a mock fitter with deterministic predict.
    fake_fitter = MagicMock()
    fake_fitter.fit = MagicMock()
    fake_fitter.predict = lambda X: np.full(len(X), 100.0)

    monkeypatch.setattr(
        "app.services.prediction_service.xgb.XGBRegressor",
        MagicMock(return_value=fake_fitter),
    )
    monkeypatch.setattr(
        "app.services.prediction_service.lgb.LGBMRegressor",
        MagicMock(return_value=fake_fitter),
    )
    monkeypatch.setattr(
        "app.services.prediction_service.RandomForestRegressor",
        MagicMock(return_value=fake_fitter),
    )
    monkeypatch.setattr(
        "app.services.prediction_service.LinearRegression",
        MagicMock(return_value=fake_fitter),
    )
    monkeypatch.setattr(
        "app.services.prediction_service.joblib.dump", lambda *a, **kw: None,
    )
    monkeypatch.setattr(
        "app.services.prediction_service.os.makedirs", lambda *a, **kw: None,
    )

    result = await svc.train_model(model_type, symbol="FPT", lookback_days=200)
    assert result.status == "completed"
    assert result.model_id == 42
    svc.repo.update_model.assert_awaited()
    svc.repo.complete_training_log.assert_awaited()
    svc.repo.deactivate_old_models.assert_awaited()


@pytest.mark.asyncio
async def test_train_model_records_failure_when_fit_raises(monkeypatch):
    """If the underlying ML library raises during .fit, the model row is
    marked FAILED, the training log is closed with an error message, and
    the response is a failed status — not a propagated exception."""
    svc = _make_service()
    df = _ohlcv_df(200)
    monkeypatch.setattr(svc, "_fetch_historical_data", AsyncMock(return_value=df))

    model_row = MagicMock(id=51)
    log = MagicMock(id=52)
    svc.repo.create_model = AsyncMock(return_value=model_row)
    svc.repo.create_training_log = AsyncMock(return_value=log)
    svc.repo.update_model = AsyncMock()
    svc.repo.complete_training_log = AsyncMock()
    svc.repo.deactivate_old_models = AsyncMock()

    bad_fitter = MagicMock()
    bad_fitter.fit = MagicMock(side_effect=RuntimeError("CUDA out of memory"))
    monkeypatch.setattr(
        "app.services.prediction_service.xgb.XGBRegressor",
        MagicMock(return_value=bad_fitter),
    )

    result = await svc.train_model(ModelType.XGBOOST, symbol="FPT")
    assert result.status == "failed"
    assert result.model_id == 51
    # update_model called with status=FAILED.
    failed_call = [
        c for c in svc.repo.update_model.await_args_list
        if c.kwargs.get("status") == ModelStatus.FAILED
    ]
    assert len(failed_call) >= 1
    svc.repo.complete_training_log.assert_awaited()


# ---------------------------------------------------------------------------
# predict — happy path with mocked model + features
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_predict_happy_path_returns_response(monkeypatch):
    """End-to-end predict: active model exists, joblib.load returns a
    fitter, historical data + current price are mocked. Output must be a
    PredictionResponse with the requested number of daily predictions."""
    svc = _make_service()

    model_row = MagicMock(
        id=1, file_path="/tmp/fake.joblib", model_type=MagicMock(value="xgboost"),
        accuracy=85.0, feature_columns=None,
    )
    svc.repo.get_active_model = AsyncMock(return_value=model_row)
    svc.repo.save_prediction = AsyncMock()

    df = _ohlcv_df(200)
    monkeypatch.setattr(svc, "_fetch_historical_data", AsyncMock(return_value=df))
    monkeypatch.setattr(svc, "_get_current_price", AsyncMock(return_value=110.0))

    fake_model = MagicMock()
    # Returns one prediction per call (last_row has 1 row).
    fake_model.predict = lambda X: np.array([float(X.iloc[0, 0]) + 1.0])
    monkeypatch.setattr(
        "app.services.prediction_service.joblib.load", lambda _: fake_model
    )

    result = await svc.predict("FPT", days=3, model_type=ModelType.XGBOOST)
    assert result is not None
    assert result.symbol == "FPT"
    assert len(result.predictions) == 3
    assert all(0.5 <= p.confidence <= 0.95 for p in result.predictions)


@pytest.mark.asyncio
async def test_predict_falls_back_to_general_model_when_symbol_specific_missing(monkeypatch):
    """get_active_model(mt, symbol) returns None → retry with (mt, None)."""
    svc = _make_service()
    general_model = MagicMock(
        id=2, file_path="/tmp/fake2.joblib", model_type=MagicMock(value="xgboost"),
        accuracy=80.0, feature_columns=None,
    )
    # First call (symbol-specific) returns None; second (general) returns row.
    svc.repo.get_active_model = AsyncMock(side_effect=[None, general_model])
    svc.repo.save_prediction = AsyncMock()

    df = _ohlcv_df(150)
    monkeypatch.setattr(svc, "_fetch_historical_data", AsyncMock(return_value=df))
    monkeypatch.setattr(svc, "_get_current_price", AsyncMock(return_value=100.0))
    monkeypatch.setattr(
        "app.services.prediction_service.joblib.load",
        lambda _: MagicMock(predict=lambda X: np.array([100.5])),
    )

    result = await svc.predict("FPT", days=2)
    assert result is not None
    assert len(result.predictions) == 2


@pytest.mark.asyncio
async def test_predict_returns_none_when_joblib_load_fails(monkeypatch):
    """A joblib error inside predict() is caught and returns None."""
    svc = _make_service()
    model_row = MagicMock(
        id=1, file_path="/tmp/fake.joblib", model_type=MagicMock(value="xgboost"),
        accuracy=80.0, feature_columns=None,
    )
    svc.repo.get_active_model = AsyncMock(return_value=model_row)
    monkeypatch.setattr(
        "app.services.prediction_service.joblib.load",
        MagicMock(side_effect=RuntimeError("bad pickle")),
    )

    assert await svc.predict("FPT") is None


@pytest.mark.asyncio
async def test_predict_returns_none_when_features_unavailable(monkeypatch):
    """_fetch_historical_data returns None during prediction → return None."""
    svc = _make_service()
    model_row = MagicMock(
        id=1, file_path="/tmp/fake.joblib", model_type=MagicMock(value="xgboost"),
        accuracy=80.0, feature_columns=None,
    )
    svc.repo.get_active_model = AsyncMock(return_value=model_row)
    monkeypatch.setattr(svc, "_fetch_historical_data", AsyncMock(return_value=None))
    monkeypatch.setattr(
        "app.services.prediction_service.joblib.load",
        lambda _: MagicMock(predict=lambda X: np.array([100.0])),
    )

    assert await svc.predict("FPT") is None


# ---------------------------------------------------------------------------
# get_feature_importance — exception branch
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_feature_importance_returns_none_on_load_error(monkeypatch):
    svc = _make_service()
    svc.repo.get_model_by_id = AsyncMock(
        return_value=MagicMock(
            id=1, file_path="/tmp/fake.joblib", feature_columns=["x"],
            model_type=MagicMock(value="xgboost"),
        )
    )
    monkeypatch.setattr(
        "app.services.prediction_service.joblib.load",
        MagicMock(side_effect=RuntimeError("bad pickle")),
    )
    assert await svc.get_feature_importance(1) is None


@pytest.mark.asyncio
async def test_get_feature_importance_returns_none_when_model_has_no_importances(monkeypatch):
    """Sklearn LinearRegression doesn't expose feature_importances_ —
    the function returns None rather than guessing."""
    svc = _make_service()
    svc.repo.get_model_by_id = AsyncMock(
        return_value=MagicMock(
            id=1, file_path="/tmp/fake.joblib", feature_columns=["x"],
            model_type=MagicMock(value="linear_regression"),
        )
    )
    plain_model = MagicMock(spec=[])  # no feature_importances_ attribute
    monkeypatch.setattr(
        "app.services.prediction_service.joblib.load", lambda _: plain_model
    )
    assert await svc.get_feature_importance(1) is None
