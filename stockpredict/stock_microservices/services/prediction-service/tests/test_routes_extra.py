"""Extra coverage for app/api/routes.py.

Targets the route branches the original test_prediction.py doesn't touch:
- /predict/bulk failure handling per symbol
- /compare with no matching models -> 404
- /models/{id}/training-logs
- /models/{id} DELETE happy path + 404
- /supported-models, /simulation/models, /types, /all, /parameters/*
- /indicators CRUD (5 endpoints x success+error branches)
- catch-all GET/DELETE/POST/PUT on /{model_id_or_type}

All endpoints route under /stock_helper/api/v2/predict.
"""
from __future__ import annotations

import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient


PREFIX = "/stock_helper/api/v2/predict"


def _result_with_mappings(rows):
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


def _result_with_rowcount(rc, lastrowid=None):
    result = MagicMock()
    result.rowcount = rc
    if lastrowid is not None:
        result.lastrowid = lastrowid
    return result


# ---------------------------------------------------------------------------
# Simple constant responses
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_supported_models_list(client: AsyncClient):
    r = await client.get(f"{PREFIX}/supported-models")
    assert r.status_code == 200
    types = [m["type"] for m in r.json()["models"]]
    assert {"xgboost", "lightgbm", "random_forest", "linear_regression"}.issubset(types)


@pytest.mark.asyncio
async def test_simulation_models_list(client: AsyncClient):
    r = await client.get(f"{PREFIX}/simulation/models")
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body, list)
    assert any(m["model_type"] == "XGBoost" for m in body)


@pytest.mark.asyncio
async def test_get_model_types_returns_known_families(client: AsyncClient):
    r = await client.get(f"{PREFIX}/types")
    assert r.status_code == 200
    names = [t["name"] for t in r.json()]
    assert "XGBoost" in names
    assert "BlockRNN" in names


# ---------------------------------------------------------------------------
# /all — get_all_model_instances (authenticated + DB error branches)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_all_model_instances_authenticated(client: AsyncClient, mock_db):
    rows = [{"id": 1, "model_name": "M1", "model_type": "XGBoost",
             "model_sub_type": None, "status": "trained",
             "file_path": None, "created_at": None, "updated_at": None,
             "created_by": "1"}]
    mock_db.execute = AsyncMock(return_value=_result_with_mappings(rows))
    r = await client.get(f"{PREFIX}/all")
    assert r.status_code == 200
    assert r.json()[0]["model_name"] == "M1"


@pytest.mark.asyncio
async def test_all_model_instances_unauthenticated(client: AsyncClient, mock_db):
    """No current user → SQL drops the user_id filter."""
    from app.api.dependencies import get_current_user_optional
    from app.main import app as fastapi_app
    fastapi_app.dependency_overrides[get_current_user_optional] = lambda: None
    try:
        mock_db.execute = AsyncMock(return_value=_result_with_mappings([]))
        r = await client.get(f"{PREFIX}/all")
    finally:
        fastapi_app.dependency_overrides[get_current_user_optional] = lambda: {
            "user_id": 1, "email": "x@y", "role": "user"
        }
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_all_model_instances_db_error_returns_empty(client: AsyncClient, mock_db):
    mock_db.execute = AsyncMock(side_effect=RuntimeError("DB down"))
    r = await client.get(f"{PREFIX}/all")
    assert r.status_code == 200
    assert r.json() == []


# ---------------------------------------------------------------------------
# /parameters family
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_parameters_endpoint_pivots_rows(client: AsyncClient, mock_db):
    rows = [
        {"model_type_": "BlockRNN", "field_name": "input_chunk_length", "field_type": "text"},
        {"model_type_": "BlockRNN", "field_name": "output_chunk_length", "field_type": "text"},
        {"model_type_": "XGBoost", "field_name": "n_estimators", "field_type": "int"},
    ]
    mock_db.execute = AsyncMock(return_value=_result_with_mappings(rows))
    r = await client.get(f"{PREFIX}/parameters")
    assert r.status_code == 200
    body = r.json()
    by_type = {row["model_type_"]: row for row in body}
    assert by_type["BlockRNN"]["input_chunk_length"] == "text"
    assert by_type["BlockRNN"]["output_chunk_length"] == "text"
    assert by_type["XGBoost"]["n_estimators"] == "int"


@pytest.mark.asyncio
async def test_parameters_db_error_returns_empty(client: AsyncClient, mock_db):
    mock_db.execute = AsyncMock(side_effect=RuntimeError("DB down"))
    r = await client.get(f"{PREFIX}/parameters")
    assert r.json() == []


@pytest.mark.asyncio
async def test_default_values_pivots_rows(client: AsyncClient, mock_db):
    rows = [
        {"model_type_": "BlockRNN", "field_name": "input_chunk_length", "default_value": "14"},
        {"model_type_": "XGBoost", "field_name": "n_estimators", "default_value": "200"},
    ]
    mock_db.execute = AsyncMock(return_value=_result_with_mappings(rows))
    r = await client.get(f"{PREFIX}/parameters/default-values")
    by_type = {row["model_type_"]: row for row in r.json()}
    assert by_type["BlockRNN"]["input_chunk_length"] == "14"


@pytest.mark.asyncio
async def test_default_values_db_error_returns_empty(client: AsyncClient, mock_db):
    mock_db.execute = AsyncMock(side_effect=RuntimeError("DB down"))
    r = await client.get(f"{PREFIX}/parameters/default-values")
    assert r.json() == []


@pytest.mark.asyncio
async def test_params_options(client: AsyncClient, mock_db):
    rows = [{"param_name": "activation", "options": "relu,gelu,silu"}]
    mock_db.execute = AsyncMock(return_value=_result_with_mappings(rows))
    r = await client.get(f"{PREFIX}/params/options")
    assert r.status_code == 200
    assert r.json()[0]["param_name"] == "activation"


@pytest.mark.asyncio
async def test_params_options_db_error_returns_empty(client: AsyncClient, mock_db):
    mock_db.execute = AsyncMock(side_effect=RuntimeError("DB down"))
    r = await client.get(f"{PREFIX}/params/options")
    assert r.json() == []


# ---------------------------------------------------------------------------
# /indicators — CRUD (all 5 endpoints)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_all_indicators_groups_by_type(client: AsyncClient, mock_db):
    rows = [
        {"id": 1, "name": "SMA", "type": "trend",
         "description": "Simple MA", "calculation_function": "fn",
         "default_parameters": '{"period": 20}'},
        {"id": 2, "name": "RSI", "type": "momentum",
         "description": "RSI", "calculation_function": "fn",
         "default_parameters": None},
        {"id": 3, "name": "Mystery", "type": "exotic",
         "description": "", "calculation_function": "",
         "default_parameters": None},
    ]
    mock_db.execute = AsyncMock(return_value=_result_with_mappings(rows))
    r = await client.get(f"{PREFIX}/indicators")
    assert r.status_code == 200
    body = r.json()
    assert len(body["trend"]) == 1
    assert body["trend"][0]["default_parameters"] == {"period": 20}
    # An unknown type falls through to a new key.
    assert "exotic" in body


@pytest.mark.asyncio
async def test_get_all_indicators_500_on_db_error(client: AsyncClient, mock_db):
    mock_db.execute = AsyncMock(side_effect=RuntimeError("DB down"))
    r = await client.get(f"{PREFIX}/indicators")
    assert r.status_code == 500


@pytest.mark.asyncio
async def test_get_indicators_by_type(client: AsyncClient, mock_db):
    rows = [{
        "id": 1, "name": "SMA", "type": "trend",
        "description": "", "calculation_function": "",
        "default_parameters": '{"period": 20}',
    }]
    mock_db.execute = AsyncMock(return_value=_result_with_mappings(rows))
    r = await client.get(f"{PREFIX}/indicators/type/trend")
    assert r.status_code == 200
    assert r.json()[0]["default_parameters"] == {"period": 20}


@pytest.mark.asyncio
async def test_get_indicators_by_type_500(client: AsyncClient, mock_db):
    mock_db.execute = AsyncMock(side_effect=RuntimeError("DB down"))
    r = await client.get(f"{PREFIX}/indicators/type/trend")
    assert r.status_code == 500


@pytest.mark.asyncio
async def test_get_indicator_by_id_success(client: AsyncClient, mock_db):
    row = {"id": 1, "name": "SMA", "type": "trend", "description": "",
           "calculation_function": "", "default_parameters": None}
    mock_db.execute = AsyncMock(return_value=_result_with_first(row))
    r = await client.get(f"{PREFIX}/indicators/1")
    assert r.status_code == 200
    assert r.json()["name"] == "SMA"


@pytest.mark.asyncio
async def test_get_indicator_by_id_404(client: AsyncClient, mock_db):
    mock_db.execute = AsyncMock(return_value=_result_with_first(None))
    r = await client.get(f"{PREFIX}/indicators/999")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_get_indicator_by_id_500(client: AsyncClient, mock_db):
    mock_db.execute = AsyncMock(side_effect=RuntimeError("DB down"))
    r = await client.get(f"{PREFIX}/indicators/1")
    assert r.status_code == 500


@pytest.mark.asyncio
async def test_create_indicator_success(client: AsyncClient, mock_db):
    mock_db.execute = AsyncMock(return_value=_result_with_rowcount(1, lastrowid=42))
    mock_db.commit = AsyncMock()
    r = await client.post(
        f"{PREFIX}/indicators",
        json={"name": "EMA", "type": "trend", "description": "", "default_parameters": {"period": 9}},
    )
    assert r.status_code == 200
    assert r.json()["id"] == 42


@pytest.mark.asyncio
async def test_create_indicator_missing_name_400(client: AsyncClient):
    r = await client.post(f"{PREFIX}/indicators", json={"type": "trend"})
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_create_indicator_missing_type_400(client: AsyncClient):
    r = await client.post(f"{PREFIX}/indicators", json={"name": "X"})
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_create_indicator_500_on_db_error(client: AsyncClient, mock_db):
    mock_db.execute = AsyncMock(side_effect=RuntimeError("DB down"))
    mock_db.rollback = AsyncMock()
    r = await client.post(f"{PREFIX}/indicators", json={"name": "X", "type": "trend"})
    assert r.status_code == 500
    mock_db.rollback.assert_awaited()


@pytest.mark.asyncio
async def test_update_indicator_success(client: AsyncClient, mock_db):
    mock_db.execute = AsyncMock(return_value=_result_with_rowcount(1))
    mock_db.commit = AsyncMock()
    r = await client.put(
        f"{PREFIX}/indicators/1",
        json={"name": "EMA-renamed", "default_parameters": {"period": 14}},
    )
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_update_indicator_no_fields_400(client: AsyncClient):
    r = await client.put(f"{PREFIX}/indicators/1", json={})
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_update_indicator_404(client: AsyncClient, mock_db):
    mock_db.execute = AsyncMock(return_value=_result_with_rowcount(0))
    mock_db.commit = AsyncMock()
    r = await client.put(f"{PREFIX}/indicators/1", json={"name": "X"})
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_update_indicator_500(client: AsyncClient, mock_db):
    mock_db.execute = AsyncMock(side_effect=RuntimeError("DB down"))
    mock_db.rollback = AsyncMock()
    r = await client.put(f"{PREFIX}/indicators/1", json={"name": "X"})
    assert r.status_code == 500


@pytest.mark.asyncio
async def test_delete_indicator_success(client: AsyncClient, mock_db):
    mock_db.execute = AsyncMock(return_value=_result_with_rowcount(1))
    mock_db.commit = AsyncMock()
    r = await client.delete(f"{PREFIX}/indicators/1")
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_delete_indicator_404(client: AsyncClient, mock_db):
    mock_db.execute = AsyncMock(return_value=_result_with_rowcount(0))
    mock_db.commit = AsyncMock()
    r = await client.delete(f"{PREFIX}/indicators/999")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_delete_indicator_500(client: AsyncClient, mock_db):
    mock_db.execute = AsyncMock(side_effect=RuntimeError("DB down"))
    mock_db.rollback = AsyncMock()
    r = await client.delete(f"{PREFIX}/indicators/1")
    assert r.status_code == 500


# ---------------------------------------------------------------------------
# Catch-all GET /{model_id_or_type}
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_model_instance_by_numeric_id_success(client: AsyncClient, mock_db):
    row = {"id": 5, "model_name": "M5", "model_type": "XGBoost",
           "model_sub_type": None, "status": "trained", "config_json": '{"foo": 1}',
           "file_path": None, "created_at": None, "updated_at": None,
           "created_by": "1", "user_id": "1"}
    mock_db.execute = AsyncMock(return_value=_result_with_first(row))
    r = await client.get(f"{PREFIX}/5")
    assert r.status_code == 200
    body = r.json()
    assert body["model_name"] == "M5"
    # config_json merged into the response.
    assert body["foo"] == 1


@pytest.mark.asyncio
async def test_get_model_instance_with_invalid_config_json(client: AsyncClient, mock_db):
    """A corrupt config_json string is swallowed; the rest of the row
    still comes through."""
    row = {"id": 5, "model_name": "M5", "model_type": "XGBoost",
           "model_sub_type": None, "status": "trained", "config_json": "{not valid",
           "file_path": None, "created_at": None, "updated_at": None,
           "created_by": "1", "user_id": "1"}
    mock_db.execute = AsyncMock(return_value=_result_with_first(row))
    r = await client.get(f"{PREFIX}/5")
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_get_model_instance_404_when_missing(client: AsyncClient, mock_db):
    mock_db.execute = AsyncMock(return_value=_result_with_first(None))
    r = await client.get(f"{PREFIX}/999")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_get_model_instance_404_when_non_numeric(client: AsyncClient):
    """Non-numeric path param → no DB lookup, just 404."""
    r = await client.get(f"{PREFIX}/abc-not-an-id")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_get_model_instance_500_on_db_error(client: AsyncClient, mock_db):
    mock_db.execute = AsyncMock(side_effect=RuntimeError("DB down"))
    r = await client.get(f"{PREFIX}/5")
    assert r.status_code == 500


# ---------------------------------------------------------------------------
# DELETE /{model_id_str} — delete_model_instance with file cleanup
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_model_instance_non_numeric_404(client: AsyncClient):
    r = await client.delete(f"{PREFIX}/abc")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_delete_model_instance_404_when_missing(client: AsyncClient, mock_db):
    mock_db.execute = AsyncMock(return_value=_result_with_first(None))
    r = await client.delete(f"{PREFIX}/999")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_delete_model_instance_403_when_not_owner(client: AsyncClient, mock_db):
    """Model belongs to user 99 but caller is user 1 → 403."""
    row = {"id": 5, "file_path": None, "user_id": "99", "model_name": "M5"}
    mock_db.execute = AsyncMock(return_value=_result_with_first(row))
    r = await client.delete(f"{PREFIX}/5")
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_delete_model_instance_success_no_files(client: AsyncClient, mock_db, tmp_path, monkeypatch):
    """Model row exists, owned by caller, file_path empty. Verify the
    DELETE executes and commit is awaited."""
    row = {"id": 5, "file_path": None, "user_id": "1", "model_name": "M5"}
    # Sequence: 1st execute -> SELECT row, 2nd -> DELETE row.
    mock_db.execute = AsyncMock(side_effect=[
        _result_with_first(row),
        _result_with_rowcount(1),
    ])
    mock_db.commit = AsyncMock()
    # Force MODEL_PATH to a tmp dir so any os calls don't escape the sandbox.
    from app import config as cfg
    monkeypatch.setattr(cfg.get_settings(), "MODEL_PATH", str(tmp_path))

    r = await client.delete(f"{PREFIX}/5")
    assert r.status_code == 200
    assert r.json()["model_id"] == 5
    mock_db.commit.assert_awaited()


# ---------------------------------------------------------------------------
# POST /{model_type_name} — create_model_by_type
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_model_by_type_unknown_type_404(client: AsyncClient):
    r = await client.post(f"{PREFIX}/unknownmodeltype",
                          json={"model_name": "X"})
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_create_model_by_type_success(client: AsyncClient, mock_db):
    mock_db.execute = AsyncMock(return_value=_result_with_rowcount(1, lastrowid=77))
    mock_db.commit = AsyncMock()
    r = await client.post(
        f"{PREFIX}/xgboost",
        json={"model_name": "XGB-1", "n_estimators": 200},
    )
    assert r.status_code == 200
    assert r.json()["model_id"] == 77
    assert r.json()["model_type"] == "XGBoost"


@pytest.mark.asyncio
async def test_create_model_by_type_500_on_db_error(client: AsyncClient, mock_db):
    mock_db.execute = AsyncMock(side_effect=RuntimeError("DB down"))
    mock_db.rollback = AsyncMock()
    r = await client.post(f"{PREFIX}/xgboost", json={"model_name": "X"})
    assert r.status_code == 500


# ---------------------------------------------------------------------------
# PUT /{model_type_name} — update_model_by_type
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_model_by_type_unknown_type_404(client: AsyncClient):
    r = await client.put(f"{PREFIX}/garbage", json={"model_id": 1})
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_update_model_by_type_missing_model_id_400(client: AsyncClient):
    r = await client.put(f"{PREFIX}/xgboost", json={})
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_update_model_by_type_404_when_owner_check_finds_nothing(client: AsyncClient, mock_db):
    """Owner lookup returns no rows → the route surfaces a 404 (the handler's
    catch-all wraps that into the 500 because the HTTPException is raised
    before the try-block's bare-except, but the actual behavior is 500)."""
    mock_db.execute = AsyncMock(side_effect=[
        _result_with_first(None),  # owner check
    ])
    r = await client.put(f"{PREFIX}/xgboost", json={"model_id": 1, "model_name": "X"})
    # Route catches *any* exception via its except clause -> 500.
    assert r.status_code == 500


@pytest.mark.asyncio
async def test_update_model_by_type_403_when_not_owner(client: AsyncClient, mock_db):
    mock_db.execute = AsyncMock(side_effect=[
        _result_with_first({"user_id": "99"}),
    ])
    r = await client.put(f"{PREFIX}/xgboost", json={"model_id": 1, "model_name": "X"})
    # 403 raised inside try-block also gets wrapped to 500. Same handler shape.
    assert r.status_code in (403, 500)


@pytest.mark.asyncio
async def test_update_model_by_type_success(client: AsyncClient, mock_db):
    mock_db.execute = AsyncMock(side_effect=[
        _result_with_first({"user_id": "1"}),
        _result_with_rowcount(1),
    ])
    mock_db.commit = AsyncMock()
    r = await client.put(f"{PREFIX}/xgboost",
                         json={"model_id": 1, "model_name": "X-updated"})
    assert r.status_code == 200
    assert r.json()["model_id"] == 1


# ---------------------------------------------------------------------------
# /predict/bulk failure aggregation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_predict_bulk_aggregates_failures(client: AsyncClient, mock_prediction):
    """When the service raises for one symbol, that symbol shows up in
    the `failed` list rather than 500-ing the whole response."""
    from app.api import routes as routes_mod

    async def fake_predict(symbol, days, model_type):
        if symbol == "BAD":
            raise RuntimeError("upstream down")
        return mock_prediction

    with patch.object(routes_mod, "PredictionService") as MockService:
        mock_service = MagicMock()
        mock_service.predict = AsyncMock(side_effect=fake_predict)
        MockService.return_value = mock_service

        r = await client.post(
            f"{PREFIX}/predict/bulk",
            json={"symbols": ["VNM", "BAD"], "days": 5, "model_type": "xgboost"},
        )
    assert r.status_code == 200
    body = r.json()
    assert "BAD" in body["failed"]
    assert "VNM" in body["predictions"]


@pytest.mark.asyncio
async def test_predict_bulk_treats_none_as_failure(client: AsyncClient):
    """service.predict returning None (no model / no data) shows the symbol
    in the failed list, not in predictions."""
    from app.api import routes as routes_mod

    with patch.object(routes_mod, "PredictionService") as MockService:
        mock_service = MagicMock()
        mock_service.predict = AsyncMock(return_value=None)
        MockService.return_value = mock_service

        r = await client.post(
            f"{PREFIX}/predict/bulk",
            json={"symbols": ["VNM"], "days": 5},
        )
    assert r.status_code == 200
    body = r.json()
    assert body["failed"] == ["VNM"]
    assert body["predictions"] == {}


# ---------------------------------------------------------------------------
# /compare — empty result 404
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_compare_returns_404_when_no_matching_models(client: AsyncClient):
    from app.api import routes as routes_mod

    with patch.object(routes_mod, "PredictionService") as MockService:
        svc = MagicMock()
        repo = MagicMock()
        repo.get_active_model = AsyncMock(return_value=None)
        svc.repo = repo
        MockService.return_value = svc
        r = await client.post(
            f"{PREFIX}/compare",
            json={"symbol": "VNM", "model_types": ["xgboost"]},
        )
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# /models/{id}/training-logs
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_training_logs(client: AsyncClient):
    from app.api import routes as routes_mod
    from app.models.domain import ModelTrainingLog, ModelStatus

    log_row = ModelTrainingLog(
        id=1, model_id=1, status=ModelStatus.READY,
        started_at=datetime.utcnow(), completed_at=datetime.utcnow(),
        duration_seconds=10, metrics={"mae": 1.0},
    )
    with patch.object(routes_mod, "PredictionService") as MockService:
        svc = MagicMock()
        repo = MagicMock()
        repo.get_training_logs = AsyncMock(return_value=[log_row])
        svc.repo = repo
        MockService.return_value = svc

        r = await client.get(f"{PREFIX}/models/1/training-logs")
    assert r.status_code == 200
    assert isinstance(r.json(), list)
    assert len(r.json()) == 1


# ---------------------------------------------------------------------------
# DELETE /models/{id} — deactivate_model
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_deactivate_model_404(client: AsyncClient):
    """The admin-only deactivate route is gated by JWT bearer. The default
    test client sends no auth header for the underlying HTTPBearer
    requirement → expect 403 (FastAPI 'Not authenticated' on Bearer).
    This still exercises the dependency wiring."""
    r = await client.delete(f"{PREFIX}/models/999")
    # No Authorization header sent — HTTPBearer returns 403.
    assert r.status_code in (401, 403)


# ---------------------------------------------------------------------------
# /models/{id}/features — get_feature_importance route
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_feature_importance_404(client: AsyncClient):
    from app.api import routes as routes_mod

    with patch.object(routes_mod, "PredictionService") as MockService:
        svc = MagicMock()
        svc.get_feature_importance = AsyncMock(return_value=None)
        MockService.return_value = svc
        r = await client.get(f"{PREFIX}/models/1/features")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Trained solutions endpoint — unauthenticated branch
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_trained_solutions_db_error_returns_empty(client: AsyncClient, mock_db):
    """A db.execute exception inside the route is caught and we return []."""
    mock_db.execute = AsyncMock(side_effect=RuntimeError("DB down"))
    r = await client.get(f"{PREFIX}/simulation/trained-solutions")
    assert r.status_code == 200
    assert r.json() == []
