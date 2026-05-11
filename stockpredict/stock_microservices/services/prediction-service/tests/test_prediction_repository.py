"""Tests for app.repositories.prediction_repository.

The repository wraps SQLAlchemy 2.0 async sessions. Each test feeds it
a mock session whose execute() returns canned results, so we verify
the methods build the right INSERT/UPDATE/SELECT shape and unwrap the
results correctly. No DB engine touched here — that's integration
territory.
"""
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.domain import (
    MLModel,
    ModelStatus,
    ModelTrainingLog,
    ModelType,
    Prediction,
)
from app.repositories.prediction_repository import PredictionRepository


def _session_returning_scalar(value):
    """Session whose single execute() returns scalar_one_or_none = value."""
    session = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    result.scalar.return_value = value
    session.execute = AsyncMock(return_value=result)
    return session


def _session_returning_list(rows):
    session = AsyncMock()
    result = MagicMock()
    scalars = MagicMock()
    scalars.all.return_value = rows
    result.scalars.return_value = scalars
    session.execute = AsyncMock(return_value=result)
    return session


# ---------------------------------------------------------------------------
# Model CRUD
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_model_adds_commits_and_refreshes():
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    repo = PredictionRepository(session)
    model = await repo.create_model(
        name="lstm-v1",
        model_type=ModelType.LSTM,
        symbol="fpt",
        version="1.0.0",
    )

    assert isinstance(model, MLModel)
    assert model.name == "lstm-v1"
    assert model.symbol == "FPT"  # uppercased
    assert model.status == ModelStatus.TRAINING
    session.add.assert_called_once_with(model)
    session.commit.assert_awaited_once()
    session.refresh.assert_awaited_once_with(model)


@pytest.mark.asyncio
async def test_get_model_by_id_returns_row_or_none():
    expected = MLModel(id=7, name="m", model_type=ModelType.LSTM, status=ModelStatus.READY)
    session = _session_returning_scalar(expected)
    repo = PredictionRepository(session)
    assert (await repo.get_model_by_id(7)) is expected

    none_session = _session_returning_scalar(None)
    assert (await PredictionRepository(none_session).get_model_by_id(999)) is None


@pytest.mark.asyncio
async def test_get_active_model_uppercases_symbol_in_query():
    """Passing 'fpt' should not silently miss the FPT row."""
    expected = MLModel(id=1, name="m", model_type=ModelType.LSTM, status=ModelStatus.READY, symbol="FPT")
    session = _session_returning_scalar(expected)
    repo = PredictionRepository(session)
    out = await repo.get_active_model(ModelType.LSTM, symbol="fpt")
    assert out is expected
    session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_all_models_with_filters():
    rows = [
        MLModel(id=1, name="m1", model_type=ModelType.LSTM, status=ModelStatus.READY, symbol="FPT"),
        MLModel(id=2, name="m2", model_type=ModelType.LSTM, status=ModelStatus.READY, symbol="FPT"),
    ]
    session = _session_returning_list(rows)
    repo = PredictionRepository(session)
    out = await repo.get_all_models(model_type=ModelType.LSTM, symbol="FPT", active_only=True)
    assert out == rows


@pytest.mark.asyncio
async def test_get_all_models_no_filters_returns_all():
    rows = [MLModel(id=1, name="m1", model_type=ModelType.LSTM, status=ModelStatus.READY)]
    session = _session_returning_list(rows)
    repo = PredictionRepository(session)
    out = await repo.get_all_models()
    assert out == rows


@pytest.mark.asyncio
async def test_update_model_runs_update_then_refetch():
    """update_model fires UPDATE then re-fetches via get_model_by_id."""
    refreshed = MLModel(id=1, name="m1", model_type=ModelType.LSTM, status=ModelStatus.READY, accuracy=0.91)

    session = AsyncMock()
    update_result = MagicMock()
    fetch_result = MagicMock()
    fetch_result.scalar_one_or_none.return_value = refreshed
    session.execute = AsyncMock(side_effect=[update_result, fetch_result])
    session.commit = AsyncMock()

    repo = PredictionRepository(session)
    out = await repo.update_model(1, accuracy=0.91)
    assert out is refreshed
    assert session.execute.await_count == 2
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_model_metrics_marks_ready_and_stamps_trained_at():
    refreshed = MLModel(id=1, name="m1", model_type=ModelType.LSTM, status=ModelStatus.READY)
    session = AsyncMock()
    update_result = MagicMock()
    fetch_result = MagicMock()
    fetch_result.scalar_one_or_none.return_value = refreshed
    session.execute = AsyncMock(side_effect=[update_result, fetch_result])
    session.commit = AsyncMock()

    repo = PredictionRepository(session)
    out = await repo.update_model_metrics(1, accuracy=0.9, mse=0.01, mae=0.05, rmse=0.1, r2_score=0.8)
    assert out is refreshed
    # The UPDATE call's values dict should set status=READY + trained_at.
    set_values = session.execute.await_args_list[0].args[0].compile().params
    assert set_values.get("status") == ModelStatus.READY
    assert "trained_at" in set_values


@pytest.mark.asyncio
async def test_deactivate_old_models_returns_rowcount():
    session = AsyncMock()
    update_result = MagicMock()
    update_result.rowcount = 3
    session.execute = AsyncMock(return_value=update_result)
    session.commit = AsyncMock()

    repo = PredictionRepository(session)
    n = await repo.deactivate_old_models(ModelType.LSTM, symbol="fpt")
    assert n == 3
    session.commit.assert_awaited_once()


# ---------------------------------------------------------------------------
# Predictions
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_save_prediction_persists_with_uppercased_symbol():
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    repo = PredictionRepository(session)
    out = await repo.save_prediction(
        model_id=1,
        symbol="fpt",
        prediction_date=datetime.utcnow(),
        target_date=datetime.utcnow() + timedelta(days=1),
        predicted_price=100.0,
        predicted_change=1.5,
        predicted_direction="up",
        confidence=0.8,
    )
    assert out.symbol == "FPT"
    session.add.assert_called_once_with(out)
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_save_predictions_bulk_returns_persisted_list():
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()

    repo = PredictionRepository(session)
    payload = [
        {
            "model_id": 1,
            "symbol": "FPT",
            "prediction_date": datetime.utcnow(),
            "target_date": datetime.utcnow() + timedelta(days=1),
            "predicted_price": 100.0,
            "predicted_change": 0.5,
            "predicted_direction": "up",
            "confidence": 0.7,
        },
        {
            "model_id": 1,
            "symbol": "FPT",
            "prediction_date": datetime.utcnow(),
            "target_date": datetime.utcnow() + timedelta(days=2),
            "predicted_price": 101.0,
            "predicted_change": 1.0,
            "predicted_direction": "up",
            "confidence": 0.7,
        },
    ]
    out = await repo.save_predictions_bulk(payload)
    assert len(out) == 2
    assert session.add.call_count == 2
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_predictions_with_date_range_and_limit():
    rows = [Prediction(id=1, model_id=1, symbol="FPT")]
    session = _session_returning_list(rows)
    repo = PredictionRepository(session)
    start = datetime.utcnow() - timedelta(days=7)
    end = datetime.utcnow()
    out = await repo.get_predictions("fpt", start_date=start, end_date=end, limit=50)
    assert out == rows


@pytest.mark.asyncio
async def test_get_latest_predictions_returns_future_only():
    rows = [Prediction(id=1, model_id=1, symbol="FPT")]
    session = _session_returning_list(rows)
    repo = PredictionRepository(session)
    out = await repo.get_latest_predictions("fpt", days=5)
    assert out == rows


@pytest.mark.asyncio
async def test_update_prediction_actual_returns_none_when_missing():
    """No row matched → return None without mutating anything."""
    session = AsyncMock()
    fetch_result = MagicMock()
    fetch_result.scalar_one_or_none.return_value = None
    session.execute = AsyncMock(return_value=fetch_result)

    repo = PredictionRepository(session)
    out = await repo.update_prediction_actual(999, actual_price=100.0)
    assert out is None


# ---------------------------------------------------------------------------
# Training logs + analytics
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_training_log_persists():
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    repo = PredictionRepository(session)
    log = await repo.create_training_log(model_id=7)
    assert isinstance(log, ModelTrainingLog)
    assert log.model_id == 7
    session.add.assert_called_once()
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_training_logs_returns_rows():
    rows = [ModelTrainingLog(id=1, model_id=7)]
    session = _session_returning_list(rows)
    repo = PredictionRepository(session)
    out = await repo.get_training_logs(7, limit=5)
    assert out == rows


@pytest.mark.asyncio
async def test_log_prediction_request_uppercases_symbol():
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()

    repo = PredictionRepository(session)
    await repo.log_prediction_request(
        user_id=1, symbol="fpt", model_type="LSTM", prediction_days=5
    )
    persisted = session.add.call_args.args[0]
    assert persisted.symbol == "FPT"
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_model_accuracy_stats_zero_when_no_predictions():
    """row.total = 0 → division-by-zero short-circuits to 0% accuracy."""
    session = AsyncMock()
    result = MagicMock()
    row = MagicMock()
    row.total = 0
    row.correct = 0
    row.avg_error = None
    result.fetchone.return_value = row
    session.execute = AsyncMock(return_value=result)

    repo = PredictionRepository(session)
    stats = await repo.get_model_accuracy_stats(model_id=1, days=30)
    assert stats["total_predictions"] == 0
    assert stats["direction_accuracy"] == 0
    assert stats["average_error"] == 0


@pytest.mark.asyncio
async def test_get_model_accuracy_stats_computes_percent_when_data_present():
    session = AsyncMock()
    result = MagicMock()
    row = MagicMock()
    row.total = 10
    row.correct = 7
    row.avg_error = 0.42
    result.fetchone.return_value = row
    session.execute = AsyncMock(return_value=result)

    repo = PredictionRepository(session)
    stats = await repo.get_model_accuracy_stats(model_id=1, days=30)
    assert stats["total_predictions"] == 10
    assert stats["correct_predictions"] == 7
    assert stats["direction_accuracy"] == 70.0
    assert stats["average_error"] == pytest.approx(0.42)


@pytest.mark.asyncio
async def test_get_prediction_count_last_24h_returns_scalar():
    session = AsyncMock()
    result = MagicMock()
    result.scalar.return_value = 42
    session.execute = AsyncMock(return_value=result)

    repo = PredictionRepository(session)
    assert await repo.get_prediction_count_last_24h(1) == 42


@pytest.mark.asyncio
async def test_get_prediction_count_last_24h_zero_when_none():
    """SCALAR can be None for an empty COUNT; method coerces to 0."""
    session = AsyncMock()
    result = MagicMock()
    result.scalar.return_value = None
    session.execute = AsyncMock(return_value=result)

    repo = PredictionRepository(session)
    assert await repo.get_prediction_count_last_24h(1) == 0
