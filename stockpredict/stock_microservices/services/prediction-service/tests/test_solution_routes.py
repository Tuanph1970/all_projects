"""Tests for app.api.solution_routes.

Targets the CRUD/list endpoints and the _create_ml_model factory.
The heavy ML training and prediction paths (_run_training,
train_solution, predict_solution, calculate_solution_indicators) are
out of scope here — they pull in sklearn/XGBoost/LightGBM training
and would need DataFrame fixtures with many rows.

All DB calls go through SQLAlchemy `text()` execute, so the tests
hand mock_db a result with the right `mappings()` / `first()` /
`rowcount` / `lastrowid` shape.
"""
import json
from unittest.mock import AsyncMock, MagicMock, patch

import lightgbm as lgb
import pytest
import xgboost as xgb
from httpx import AsyncClient
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression

from app.api import solution_routes
from app.api.solution_routes import _create_ml_model


PREFIX = "/stock_helper/api/v2/solutions"


def _result_with_mappings(rows):
    """Build a mock result whose .mappings().all() returns `rows`."""
    result = MagicMock()
    mapper = MagicMock()
    mapper.all.return_value = rows
    result.mappings.return_value = mapper
    return result


def _result_with_first(row):
    result = MagicMock()
    mapper = MagicMock()
    mapper.first.return_value = row
    result.mappings.return_value = mapper
    return result


def _result_with_rowcount(rc):
    result = MagicMock()
    result.rowcount = rc
    return result


def _result_with_lastrowid(rid):
    result = MagicMock()
    result.lastrowid = rid
    return result


# ---------------------------------------------------------------------------
# _create_ml_model factory — branch coverage per ML family
# ---------------------------------------------------------------------------

class TestCreateMlModel:
    def test_xgboost_family(self):
        m = _create_ml_model("XGBoost")
        assert isinstance(m, xgb.XGBRegressor)

    def test_blockrnn_maps_to_xgboost(self):
        """BlockRNN is a DARTS type; not installed → maps to xgboost
        per DARTS_TO_ML_MAP, with the BlockRNN-specific defaults."""
        m = _create_ml_model("BlockRNN")
        assert isinstance(m, xgb.XGBRegressor)

    def test_lightgbm_family(self):
        m = _create_ml_model("LightGBM")
        assert isinstance(m, lgb.LGBMRegressor)

    def test_randomforest_family(self):
        m = _create_ml_model("RandomForest")
        assert isinstance(m, RandomForestRegressor)

    def test_linear_regression_fallback(self):
        m = _create_ml_model("LinearRegression")
        assert isinstance(m, LinearRegression)

    def test_unknown_type_defaults_to_xgboost(self):
        """Unknown DARTS name → falls back to xgboost (default ml_type)."""
        m = _create_ml_model("AnUnknownDartsType")
        assert isinstance(m, xgb.XGBRegressor)

    def test_user_config_overrides_defaults(self):
        """An explicit n_estimators in config_json beats the default."""
        m = _create_ml_model("XGBoost", config_json={"n_estimators": 42})
        assert m.n_estimators == 42

    def test_user_config_string_parsed_as_json(self):
        m = _create_ml_model("XGBoost", config_json='{"n_estimators": 7}')
        assert m.n_estimators == 7

    def test_invalid_config_json_falls_back_to_defaults(self):
        """A malformed JSON string is swallowed and defaults apply."""
        m = _create_ml_model("XGBoost", config_json="{not valid json")
        assert m.n_estimators == 200  # XGBoost default


# ---------------------------------------------------------------------------
# GET /all — get_solutions
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_solutions_returns_user_rows_when_authenticated(client: AsyncClient, mock_db):
    rows = [{"id": 1, "solution_name": "S1", "user_id": "1", "ticker": "FPT"}]
    mock_db.execute = AsyncMock(return_value=_result_with_mappings(rows))

    r = await client.get(f"{PREFIX}/all")
    assert r.status_code == 200
    body = r.json()
    assert body == [{"id": 1, "solution_name": "S1", "user_id": "1", "ticker": "FPT"}]


@pytest.mark.asyncio
async def test_get_solutions_returns_empty_on_db_error(client: AsyncClient, mock_db):
    """A database exception must not 500; degrade to []."""
    mock_db.execute = AsyncMock(side_effect=RuntimeError("DB down"))
    r = await client.get(f"{PREFIX}/all")
    assert r.status_code == 200
    assert r.json() == []


# ---------------------------------------------------------------------------
# GET /tickers — get_predict_tickers
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_predict_tickers_returns_ticker_objects(client: AsyncClient, mock_db):
    rows = [{"ticker": "FPT"}, {"ticker": "VNM"}]
    mock_db.execute = AsyncMock(return_value=_result_with_mappings(rows))

    r = await client.get(f"{PREFIX}/tickers")
    assert r.status_code == 200
    assert r.json() == [{"ticker": "FPT"}, {"ticker": "VNM"}]


@pytest.mark.asyncio
async def test_get_predict_tickers_empty_portfolio(client: AsyncClient, mock_db):
    mock_db.execute = AsyncMock(return_value=_result_with_mappings([]))
    r = await client.get(f"{PREFIX}/tickers")
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.asyncio
async def test_get_predict_tickers_swallows_db_error(client: AsyncClient, mock_db):
    mock_db.execute = AsyncMock(side_effect=RuntimeError("DB down"))
    r = await client.get(f"{PREFIX}/tickers")
    assert r.status_code == 200
    assert r.json() == []


# ---------------------------------------------------------------------------
# GET /models — get_predict_models
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_predict_models_returns_user_rows(client: AsyncClient, mock_db):
    rows = [
        {"id": 1, "model_name": "M1", "model_type": "XGBoost",
         "model_sub_type": "", "past_covariate": None, "future_covariate": None}
    ]
    mock_db.execute = AsyncMock(return_value=_result_with_mappings(rows))
    r = await client.get(f"{PREFIX}/models")
    assert r.status_code == 200
    assert r.json()[0]["model_name"] == "M1"


@pytest.mark.asyncio
async def test_get_predict_models_swallows_db_error(client: AsyncClient, mock_db):
    mock_db.execute = AsyncMock(side_effect=RuntimeError("DB down"))
    r = await client.get(f"{PREFIX}/models")
    assert r.status_code == 200
    assert r.json() == []


# ---------------------------------------------------------------------------
# POST / — create_solution
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_solution_returns_payload_with_lastrowid(client: AsyncClient, mock_db):
    mock_db.execute = AsyncMock(return_value=_result_with_lastrowid(42))
    mock_db.commit = AsyncMock()

    body = {
        "solution_name": "S1",
        "model_id": 1,
        "ticker": "FPT",
        "start_training_date": "2026-01-01",
        "end_training_date": "2026-04-01",
        "train_validation_ratio": 0.8,
    }
    r = await client.post(f"{PREFIX}/create", json=body)
    assert r.status_code == 200
    assert r.json()["id"] == 42
    assert r.json()["solution_name"] == "S1"
    mock_db.commit.assert_awaited()


@pytest.mark.asyncio
async def test_create_solution_500s_on_db_error(client: AsyncClient, mock_db):
    """On DB failure the handler rolls back and surfaces a 500."""
    mock_db.execute = AsyncMock(side_effect=RuntimeError("constraint violation"))
    mock_db.rollback = AsyncMock()

    r = await client.post(
        f"{PREFIX}/create",
        json={"solution_name": "S1", "model_id": 1, "ticker": "FPT"},
    )
    assert r.status_code == 500
    mock_db.rollback.assert_awaited()


# ---------------------------------------------------------------------------
# PUT / — update_solution
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_update_solution_requires_id(client: AsyncClient, mock_db):
    r = await client.put(f"{PREFIX}/update", json={"solution_name": "S1"})
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_update_solution_success(client: AsyncClient, mock_db):
    mock_db.execute = AsyncMock(return_value=_result_with_rowcount(1))
    mock_db.commit = AsyncMock()
    r = await client.put(
        f"{PREFIX}/update",
        json={"id": 7, "solution_name": "Renamed", "model_id": 1, "ticker": "FPT"},
    )
    assert r.status_code == 200
    assert r.json()["id"] == 7
    mock_db.commit.assert_awaited()


@pytest.mark.asyncio
async def test_update_solution_500s_on_db_error(client: AsyncClient, mock_db):
    mock_db.execute = AsyncMock(side_effect=RuntimeError("DB down"))
    mock_db.rollback = AsyncMock()
    r = await client.put(f"{PREFIX}/update", json={"id": 7, "solution_name": "S1"})
    assert r.status_code == 500
    mock_db.rollback.assert_awaited()


# ---------------------------------------------------------------------------
# /calculate-date-range
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_calculate_date_range_get_returns_default_range(client: AsyncClient):
    r = await client.get(f"{PREFIX}/calculate-date-range?ticker=FPT")
    assert r.status_code == 200
    body = r.json()
    assert "start_date" in body and "end_date" in body
    assert body["adjusted"] is False


@pytest.mark.asyncio
async def test_calculate_date_range_post_returns_default_range(client: AsyncClient):
    r = await client.post(f"{PREFIX}/calculate-date-range", json={"ticker": "FPT"})
    assert r.status_code == 200
    assert r.json()["recommended_points"] == 500


# ---------------------------------------------------------------------------
# /ticker/time_range/{ticker} — httpx-mocked
# ---------------------------------------------------------------------------

class _FakeAsyncClient:
    def __init__(self, response):
        self._response = response

    async def __aenter__(self):
        c = MagicMock()
        c.get = AsyncMock(return_value=self._response)
        return c

    async def __aexit__(self, *_):
        return False


@pytest.mark.asyncio
async def test_get_ticker_time_range_returns_first_and_last_dates(client: AsyncClient):
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = [
        {"time": "2024-01-01", "close": 100},
        {"time": "2026-05-01", "close": 110},
    ]
    with patch("app.api.solution_routes.httpx.AsyncClient", return_value=_FakeAsyncClient(resp)):
        r = await client.get(f"{PREFIX}/ticker/time_range/FPT")
    assert r.status_code == 200
    body = r.json()
    assert body["start_date"] == "2024-01-01"
    assert body["end_date"] == "2026-05-01"


@pytest.mark.asyncio
async def test_get_ticker_time_range_falls_back_to_defaults_on_non_200(client: AsyncClient):
    resp = MagicMock()
    resp.status_code = 503
    with patch("app.api.solution_routes.httpx.AsyncClient", return_value=_FakeAsyncClient(resp)):
        r = await client.get(f"{PREFIX}/ticker/time_range/FPT")
    assert r.status_code == 200
    assert r.json()["start_date"] == "2020-01-01"


@pytest.mark.asyncio
async def test_get_ticker_time_range_falls_back_to_defaults_on_exception(client: AsyncClient):
    class Boom:
        async def __aenter__(self):
            raise ConnectionError("down")

        async def __aexit__(self, *_):
            return False

    with patch("app.api.solution_routes.httpx.AsyncClient", return_value=Boom()):
        r = await client.get(f"{PREFIX}/ticker/time_range/FPT")
    assert r.status_code == 200
    assert r.json()["start_date"] == "2020-01-01"


# ---------------------------------------------------------------------------
# GET /{solution_id}/training-status
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_training_status_returns_not_found_when_no_session(client: AsyncClient):
    # Make sure no stale entry from a previous test.
    solution_routes.training_status.pop(99, None)
    r = await client.get(f"{PREFIX}/99/training-status")
    assert r.status_code == 200
    assert r.json()["status"] == "not_found"


@pytest.mark.asyncio
async def test_training_status_returns_current_in_progress(client: AsyncClient):
    solution_routes.training_status[100] = {"status": "training", "progress": 25}
    try:
        r = await client.get(f"{PREFIX}/100/training-status")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "training"
        assert body["progress"] == 25
    finally:
        solution_routes.training_status.pop(100, None)


@pytest.mark.asyncio
async def test_training_status_cleans_up_stale_completed_status(client: AsyncClient):
    """A completed status older than 300 seconds is GC'd on next read."""
    import time as time_module
    solution_routes.training_status[101] = {
        "status": "completed",
        "completed_at": time_module.time() - 1000,  # 16+ minutes ago
    }
    try:
        await client.get(f"{PREFIX}/101/training-status")
        # GC'd after the read.
        assert 101 not in solution_routes.training_status
    finally:
        solution_routes.training_status.pop(101, None)


# ---------------------------------------------------------------------------
# GET /{solution_id}/indicators
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_solution_indicators_groups_by_category(client: AsyncClient, mock_db):
    rows = [
        {
            "id": 1, "solution_id": 7, "indicator_id": 11,
            "indicator_category": "trend", "covariate_type": "past",
            "parameters": '{"period": 14}', "name": "EMA",
            "type": "trend", "description": "EMA desc",
            "default_parameters": '{"period": 20}',
        },
        {
            "id": 2, "solution_id": 7, "indicator_id": 12,
            "indicator_category": "momentum", "covariate_type": "past",
            "parameters": None, "name": "RSI",
            "type": "momentum", "description": "RSI desc",
            "default_parameters": None,
        },
    ]
    mock_db.execute = AsyncMock(return_value=_result_with_mappings(rows))
    r = await client.get(f"{PREFIX}/7/indicators")
    assert r.status_code == 200
    body = r.json()
    assert set(body.keys()) == {"trend", "momentum"}
    assert body["trend"]["name"] == "EMA"
    # parameters JSON was parsed back into a dict.
    assert body["trend"]["parameters"] == {"period": 14}
    assert body["momentum"]["parameters"] == {}


@pytest.mark.asyncio
async def test_get_solution_indicators_returns_empty_dict_on_db_error(client: AsyncClient, mock_db):
    mock_db.execute = AsyncMock(side_effect=RuntimeError("DB down"))
    r = await client.get(f"{PREFIX}/7/indicators")
    assert r.status_code == 200
    assert r.json() == {}


# ---------------------------------------------------------------------------
# POST /{solution_id}/indicators/set
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_set_solution_indicators_frontend_object_format(client: AsyncClient, mock_db):
    """Frontend posts {trend_indicator: {...}, momentum_indicator: {...}}."""
    mock_db.execute = AsyncMock(return_value=MagicMock())
    mock_db.commit = AsyncMock()
    body = {
        "trend_indicator": {"id": 11, "covariate_type": "past", "parameters": {"period": 14}},
        "momentum_indicator": {"id": 12, "covariate_type": "future", "parameters": {"period": 9}},
    }
    r = await client.post(f"{PREFIX}/7/indicators/set", json=body)
    assert r.status_code == 200
    mock_db.commit.assert_awaited()


@pytest.mark.asyncio
async def test_set_solution_indicators_array_format(client: AsyncClient, mock_db):
    """Array format also supported as a fallback."""
    mock_db.execute = AsyncMock(return_value=MagicMock())
    mock_db.commit = AsyncMock()
    body = {
        "indicators": [
            {"indicator_id": 11, "indicator_category": "trend", "covariate_type": "past", "parameters": {}}
        ]
    }
    r = await client.post(f"{PREFIX}/7/indicators/set", json=body)
    assert r.status_code == 200


# ---------------------------------------------------------------------------
# POST /{solution_id}/indicators/add
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_add_solution_indicator_success(client: AsyncClient, mock_db):
    mock_db.execute = AsyncMock(return_value=_result_with_lastrowid(99))
    mock_db.commit = AsyncMock()
    r = await client.post(
        f"{PREFIX}/7/indicators/add",
        json={
            "indicator_id": 11, "indicator_category": "trend",
            "covariate_type": "past", "parameters": {"period": 14},
        },
    )
    assert r.status_code == 200
    assert r.json()["id"] == 99


@pytest.mark.asyncio
async def test_add_solution_indicator_500s_on_db_error(client: AsyncClient, mock_db):
    mock_db.execute = AsyncMock(side_effect=RuntimeError("DB down"))
    mock_db.rollback = AsyncMock()
    r = await client.post(f"{PREFIX}/7/indicators/add", json={"indicator_id": 1})
    assert r.status_code == 500
    mock_db.rollback.assert_awaited()


# ---------------------------------------------------------------------------
# DELETE /{solution_id}/indicators/{indicator_id}
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_remove_solution_indicator_success(client: AsyncClient, mock_db):
    mock_db.execute = AsyncMock(return_value=_result_with_rowcount(1))
    mock_db.commit = AsyncMock()
    r = await client.delete(f"{PREFIX}/7/indicators/11")
    assert r.status_code == 200
    assert r.json()["solution_id"] == 7
    mock_db.commit.assert_awaited()


@pytest.mark.asyncio
async def test_remove_solution_indicator_500s_on_db_error(client: AsyncClient, mock_db):
    mock_db.execute = AsyncMock(side_effect=RuntimeError("DB down"))
    mock_db.rollback = AsyncMock()
    r = await client.delete(f"{PREFIX}/7/indicators/11")
    assert r.status_code == 500


# ---------------------------------------------------------------------------
# GET /{solution_id}
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_solution_by_id_returns_row_and_parses_json_fields(client: AsyncClient, mock_db):
    """training_result + prediction_result are JSON strings in the DB but
    delivered as parsed objects to the frontend."""
    row = {
        "id": 7, "solution_name": "S1", "user_id": "1", "ticker": "FPT",
        "training_result": '{"accuracy": 0.85}',
        "prediction_result": '{"forecast": [1, 2, 3]}',
    }
    mock_db.execute = AsyncMock(return_value=_result_with_first(row))
    r = await client.get(f"{PREFIX}/7")
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == 7
    assert body["training_result"] == {"accuracy": 0.85}
    assert body["prediction_result"] == {"forecast": [1, 2, 3]}


@pytest.mark.asyncio
async def test_get_solution_by_id_returns_404_when_missing(client: AsyncClient, mock_db):
    mock_db.execute = AsyncMock(return_value=_result_with_first(None))
    r = await client.get(f"{PREFIX}/999")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_get_solution_by_id_handles_invalid_json_field(client: AsyncClient, mock_db):
    """A corrupt training_result string is set to None rather than crashing
    the whole response."""
    row = {"id": 7, "training_result": "{not valid", "prediction_result": None}
    mock_db.execute = AsyncMock(return_value=_result_with_first(row))
    r = await client.get(f"{PREFIX}/7")
    assert r.status_code == 200
    assert r.json()["training_result"] is None


# ---------------------------------------------------------------------------
# PUT /{solution_id}
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_update_solution_by_id_success(client: AsyncClient, mock_db):
    mock_db.execute = AsyncMock(return_value=_result_with_rowcount(1))
    mock_db.commit = AsyncMock()
    r = await client.put(
        f"{PREFIX}/7",
        json={"solution_name": "Renamed", "model_id": 1, "ticker": "FPT"},
    )
    assert r.status_code == 200
    assert r.json()["id"] == 7


@pytest.mark.asyncio
async def test_update_solution_by_id_500s_on_db_error(client: AsyncClient, mock_db):
    mock_db.execute = AsyncMock(side_effect=RuntimeError("DB down"))
    mock_db.rollback = AsyncMock()
    r = await client.put(f"{PREFIX}/7", json={"solution_name": "X"})
    assert r.status_code == 500


# ---------------------------------------------------------------------------
# DELETE /{solution_id}
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_delete_solution_by_id_success(client: AsyncClient, mock_db):
    """First execute deletes indicators, second deletes the solution row."""
    indicator_delete = _result_with_rowcount(2)
    solution_delete = _result_with_rowcount(1)
    mock_db.execute = AsyncMock(side_effect=[indicator_delete, solution_delete])
    mock_db.commit = AsyncMock()

    r = await client.delete(f"{PREFIX}/7")
    assert r.status_code == 200
    assert r.json()["id"] == 7


@pytest.mark.asyncio
async def test_delete_solution_by_id_404_when_no_rows_affected(client: AsyncClient, mock_db):
    indicator_delete = _result_with_rowcount(0)
    solution_delete = _result_with_rowcount(0)
    mock_db.execute = AsyncMock(side_effect=[indicator_delete, solution_delete])
    mock_db.commit = AsyncMock()

    r = await client.delete(f"{PREFIX}/9999")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_delete_solution_by_id_500s_on_db_error(client: AsyncClient, mock_db):
    mock_db.execute = AsyncMock(side_effect=RuntimeError("DB down"))
    mock_db.rollback = AsyncMock()
    r = await client.delete(f"{PREFIX}/7")
    assert r.status_code == 500
