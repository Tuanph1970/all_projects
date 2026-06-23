"""Tests for app.services.prediction_service.PredictionService.

Covers the pure feature engineering, the httpx integration paths, the
early-return failure modes, and the simple repo-wrapper methods. The
heavy ML training path itself is not exercised here (it would need a
real model on disk and is the wrong place for unit tests); instead we
verify train_model's data-insufficient short-circuit.
"""
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from app.models.domain import MLModel, ModelStatus, ModelType
from app.services.prediction_service import PredictionService


def _make_service(session=None) -> PredictionService:
    if session is None:
        session = AsyncMock()
    return PredictionService(session)


def _sample_ohlcv_df(rows: int = 80) -> pd.DataFrame:
    """Build a deterministic OHLCV frame with enough rows that
    _prepare_features (which uses rolling windows up to 50) doesn't
    drop everything via dropna()."""
    dates = pd.date_range("2026-01-01", periods=rows, freq="D")
    rng = np.random.default_rng(seed=42)
    close = 100 + np.cumsum(rng.normal(0, 1.0, size=rows))
    return pd.DataFrame(
        {
            "date": dates,
            "open": close + rng.normal(0, 0.2, size=rows),
            "high": close + 1.0,
            "low": close - 1.0,
            "close": close,
            "volume": rng.integers(1000, 5000, size=rows),
        }
    )


# ---------------------------------------------------------------------------
# _fetch_historical_data — httpx integration paths
# ---------------------------------------------------------------------------

class _FakeAsyncClient:
    """Async-context-manager that yields a client whose .get() returns
    a pre-canned response. The patch site replaces httpx.AsyncClient,
    so the production code-under-test gets this instead."""

    def __init__(self, response):
        self._response = response

    async def __aenter__(self):
        client = MagicMock()
        client.get = AsyncMock(return_value=self._response)
        return client

    async def __aexit__(self, *_):
        return False


@pytest.mark.asyncio
async def test_fetch_historical_data_returns_dataframe_on_200():
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {
        "data": [
            {"date": "2026-05-01", "open": 1, "high": 2, "low": 0.5, "close": 1.5, "volume": 100},
            {"date": "2026-05-02", "open": 1.5, "high": 2.1, "low": 1.0, "close": 2.0, "volume": 110},
        ]
    }
    with patch("app.services.prediction_service.httpx.AsyncClient", return_value=_FakeAsyncClient(resp)):
        svc = _make_service()
        df = await svc._fetch_historical_data("FPT", days=30)
    assert df is not None
    assert len(df) == 2
    # Dates were parsed and the result sorted ascending.
    assert df["date"].is_monotonic_increasing


@pytest.mark.asyncio
async def test_fetch_historical_data_returns_none_on_non_200():
    resp = MagicMock()
    resp.status_code = 503
    with patch("app.services.prediction_service.httpx.AsyncClient", return_value=_FakeAsyncClient(resp)):
        svc = _make_service()
        assert await svc._fetch_historical_data("FPT") is None


@pytest.mark.asyncio
async def test_fetch_historical_data_swallows_network_errors():
    """An httpx exception should not propagate — return None instead."""
    class Boom:
        async def __aenter__(self):
            raise ConnectionError("network down")

        async def __aexit__(self, *_):
            return False

    with patch("app.services.prediction_service.httpx.AsyncClient", return_value=Boom()):
        svc = _make_service()
        assert await svc._fetch_historical_data("FPT") is None


@pytest.mark.asyncio
async def test_fetch_historical_data_returns_none_when_data_empty():
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {}  # no "data" key
    with patch("app.services.prediction_service.httpx.AsyncClient", return_value=_FakeAsyncClient(resp)):
        svc = _make_service()
        assert await svc._fetch_historical_data("FPT") is None


# ---------------------------------------------------------------------------
# _get_current_price
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_current_price_returns_price_field():
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"price": 123.5}
    with patch("app.services.prediction_service.httpx.AsyncClient", return_value=_FakeAsyncClient(resp)):
        svc = _make_service()
        assert await svc._get_current_price("FPT") == 123.5


@pytest.mark.asyncio
async def test_get_current_price_falls_back_to_close():
    """When the upstream omits "price" but provides "close", we use that."""
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"close": 99.9}
    with patch("app.services.prediction_service.httpx.AsyncClient", return_value=_FakeAsyncClient(resp)):
        svc = _make_service()
        assert await svc._get_current_price("FPT") == 99.9


@pytest.mark.asyncio
async def test_get_current_price_returns_none_on_failure():
    resp = MagicMock()
    resp.status_code = 500
    with patch("app.services.prediction_service.httpx.AsyncClient", return_value=_FakeAsyncClient(resp)):
        svc = _make_service()
        assert await svc._get_current_price("FPT") is None


# ---------------------------------------------------------------------------
# _prepare_features / _get_feature_columns — pure functions
# ---------------------------------------------------------------------------

def test_prepare_features_builds_indicator_columns():
    svc = _make_service()
    df = svc._prepare_features(_sample_ohlcv_df(80))
    # Each indicator family produces named columns.
    for col in [
        "returns",
        "log_returns",
        "sma_5",
        "sma_20",
        "ema_50",
        "volatility_20",
        "rsi",
        "macd",
        "macd_signal",
        "bb_middle",
        "bb_upper",
        "bb_lower",
        "bb_position",
        "volume_ratio",
        "close_lag_1",
        "close_lag_5",
        "returns_lag_1",
        "target",
    ]:
        assert col in df.columns, f"missing feature column: {col}"
    # dropna() removed the warmup rows but left something behind.
    assert len(df) > 0


def test_get_feature_columns_excludes_metadata_and_raw_ohlcv():
    svc = _make_service()
    df = pd.DataFrame(
        {
            "date": [],
            "open": [],
            "high": [],
            "low": [],
            "close": [],
            "volume": [],
            "symbol": [],
            "target": [],
            "rsi": [],
            "sma_20": [],
            "Unnamed: 0": [],
        }
    )
    cols = svc._get_feature_columns(df)
    # Engineered features stay; raw OHLCV + metadata + Unnamed pandas
    # artifacts are filtered out.
    assert "rsi" in cols
    assert "sma_20" in cols
    for excluded in ("date", "target", "symbol", "open", "high", "low", "close", "volume"):
        assert excluded not in cols
    assert all(not c.startswith("Unnamed") for c in cols)


# ---------------------------------------------------------------------------
# train_model — insufficient-data short-circuit
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_train_model_returns_failed_on_insufficient_data():
    """Less than 60 rows or no DataFrame → fail without touching ML."""
    svc = _make_service()
    with patch.object(svc, "_fetch_historical_data", AsyncMock(return_value=None)):
        result = await svc.train_model(ModelType.XGBOOST, symbol="FPT")
    assert result.status == "failed"
    assert result.model_id == 0
    assert "Insufficient" in result.message


@pytest.mark.asyncio
async def test_train_model_short_dataframe_returns_failed():
    short_df = _sample_ohlcv_df(rows=30)  # < 60
    svc = _make_service()
    with patch.object(svc, "_fetch_historical_data", AsyncMock(return_value=short_df)):
        result = await svc.train_model(ModelType.XGBOOST, symbol="FPT")
    assert result.status == "failed"


# ---------------------------------------------------------------------------
# predict — no-model + train-fail short-circuits
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_predict_returns_none_when_no_model_and_training_fails():
    """No active model → try to train; training also fails → return None."""
    svc = _make_service()
    svc.repo.get_active_model = AsyncMock(return_value=None)

    failed_train = MagicMock(status="failed", model_id=0)
    with patch.object(svc, "train_model", AsyncMock(return_value=failed_train)):
        result = await svc.predict("FPT", days=5)
    assert result is None


# ---------------------------------------------------------------------------
# get_models / get_model — wrapper methods
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_models_wraps_repo_rows_in_response_schema():
    svc = _make_service()
    rows = [
        MLModel(
            id=1,
            name="m1",
            model_type=ModelType.XGBOOST,
            status=ModelStatus.READY,
            symbol="FPT",
            version="1.0.0",
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
    ]
    svc.repo.get_all_models = AsyncMock(return_value=rows)
    out = await svc.get_models(model_type=ModelType.XGBOOST, symbol="FPT", active_only=True)
    assert len(out) == 1
    assert out[0].name == "m1"


@pytest.mark.asyncio
async def test_get_model_returns_none_when_missing():
    svc = _make_service()
    svc.repo.get_model_by_id = AsyncMock(return_value=None)
    assert await svc.get_model(999) is None


@pytest.mark.asyncio
async def test_get_model_wraps_row_in_response_schema():
    svc = _make_service()
    row = MLModel(
        id=7,
        name="m7",
        model_type=ModelType.XGBOOST,
        status=ModelStatus.READY,
        version="1.0.0",
        is_active=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    svc.repo.get_model_by_id = AsyncMock(return_value=row)
    out = await svc.get_model(7)
    assert out is not None
    assert out.name == "m7"


# ---------------------------------------------------------------------------
# get_feature_importance — model + file-existence guards
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_feature_importance_returns_none_when_model_missing():
    svc = _make_service()
    svc.repo.get_model_by_id = AsyncMock(return_value=None)
    assert await svc.get_feature_importance(999) is None


@pytest.mark.asyncio
async def test_get_feature_importance_returns_none_when_file_path_missing():
    """Model row exists but never finished training (no file_path)."""
    svc = _make_service()
    svc.repo.get_model_by_id = AsyncMock(
        return_value=MLModel(
            id=1, name="m1", model_type=ModelType.XGBOOST,
            status=ModelStatus.TRAINING, file_path=None,
        )
    )
    assert await svc.get_feature_importance(1) is None


@pytest.mark.asyncio
async def test_get_feature_importance_unwraps_sklearn_importances(monkeypatch):
    svc = _make_service()
    svc.repo.get_model_by_id = AsyncMock(
        return_value=MLModel(
            id=2,
            name="m2",
            model_type=ModelType.RANDOM_FOREST,
            status=ModelStatus.READY,
            file_path="/tmp/fake.joblib",
            feature_columns=["sma_20", "rsi", "macd"],
        )
    )

    fake_model = MagicMock()
    fake_model.feature_importances_ = np.array([0.2, 0.5, 0.3])
    monkeypatch.setattr(
        "app.services.prediction_service.joblib.load",
        lambda _: fake_model,
    )

    out = await svc.get_feature_importance(2)
    assert out is not None
    assert out.model_id == 2
    # Sorted descending by importance — rsi was 0.5, the highest.
    assert out.features[0].feature == "rsi"
    assert out.features[0].importance == pytest.approx(0.5)
    assert len(out.features) <= 20


# ---------------------------------------------------------------------------
# backtest — empty + non-empty paths
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_backtest_returns_none_when_no_history():
    """No historical price data for the symbol → nothing to backtest."""
    svc = _make_service()
    svc._fetch_historical_data = AsyncMock(return_value=None)
    out = await svc.backtest(
        "FPT", ModelType.XGBOOST,
        start_date=datetime(2026, 1, 1),
        end_date=datetime(2026, 5, 1),
    )
    assert out is None


@pytest.mark.asyncio
async def test_backtest_runs_walk_forward_over_window():
    """Backtest re-runs the model over the window without any stored predictions."""
    svc = _make_service()
    df = _sample_ohlcv_df(rows=120)
    svc._fetch_historical_data = AsyncMock(return_value=df)

    feature_cols = svc._get_feature_columns(svc._prepare_features(df))
    model = MagicMock(file_path="/tmp/model.pkl", feature_columns=feature_cols)
    svc.repo.get_active_model = AsyncMock(return_value=model)

    # Stub model predicts the prior close + a small offset for every row.
    fake_model = MagicMock()
    fake_model.predict = lambda X: (X["close_lag_1"] + 0.25).to_numpy()

    with patch("app.services.prediction_service.joblib.load", return_value=fake_model):
        out = await svc.backtest(
            "FPT", ModelType.XGBOOST,
            start_date=datetime(2026, 1, 1),
            end_date=datetime(2026, 5, 1),
        )

    assert out is not None
    assert out.symbol == "FPT"
    assert out.total_predictions > 0
    assert 0 <= out.correct_direction <= out.total_predictions
    assert 0 <= out.direction_accuracy <= 100
    assert out.mean_absolute_error >= 0
    assert out.root_mean_squared_error >= out.mean_absolute_error
    assert 0.5 <= out.average_confidence <= 0.95
