"""Coverage for GET /simulation/trained-solutions (Backlog #1).

Endpoint joins tbl_solution + model_instances, filters by train_status
∈ {trained, predicted}, scopes to the current user when authenticated,
and shapes a `training_period` string from the start/end dates. We mock
db.execute to control the SQL response.
"""
import pytest
from unittest.mock import MagicMock
from httpx import AsyncClient

from app.api.dependencies import get_current_user_optional


PREFIX = "/stock_helper/api/v2/predict"


def _mock_rows(rows: list[dict], mock_db):
    """Configure mock_db.execute to return the given list of mappings."""
    result = MagicMock()
    mappings = MagicMock()
    mappings.all.return_value = rows
    result.mappings.return_value = mappings
    mock_db.execute.return_value = result


@pytest.mark.asyncio
async def test_trained_solutions_empty_list_when_no_rows(
    client: AsyncClient, mock_db,
):
    _mock_rows([], mock_db)

    r = await client.get(f"{PREFIX}/simulation/trained-solutions")
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.asyncio
async def test_trained_solutions_shapes_training_period_from_dates(
    client: AsyncClient, mock_db,
):
    _mock_rows(
        [
            {
                "solution_id": 1,
                "solution_name": "FPT XGBoost daily",
                "ticker": "FPT",
                "start_training_date": "2023-01-01",
                "end_training_date": "2024-01-01",
                "updated_date": "2024-01-15",
                "model_name": "xgb_v1",
                "model_type": "XGBoost",
                "model_sub_type": None,
            }
        ],
        mock_db,
    )

    r = await client.get(f"{PREFIX}/simulation/trained-solutions")
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 1
    sol = body[0]
    assert sol["solution_id"] == 1
    assert sol["solution_name"] == "FPT XGBoost daily"
    assert sol["ticker"] == "FPT"
    assert sol["model_name"] == "xgb_v1"
    assert sol["training_period"] == "2023-01-01 → 2024-01-01"


@pytest.mark.asyncio
async def test_trained_solutions_handles_partial_dates(
    client: AsyncClient, mock_db,
):
    """Only start_training_date populated → 'từ <start>'.
    Both missing → '—' placeholder."""
    _mock_rows(
        [
            {
                "solution_id": 10,
                "solution_name": "incomplete dates",
                "ticker": "VNM",
                "start_training_date": "2024-06-01",
                "end_training_date": None,
                "updated_date": "2024-06-10",
                "model_name": "lstm_v1",
                "model_type": "LSTM",
                "model_sub_type": None,
            },
            {
                "solution_id": 11,
                "solution_name": "no dates",
                "ticker": "VCB",
                "start_training_date": None,
                "end_training_date": None,
                "updated_date": "2024-07-01",
                "model_name": "transformer_v1",
                "model_type": "Transformer",
                "model_sub_type": None,
            },
        ],
        mock_db,
    )

    r = await client.get(f"{PREFIX}/simulation/trained-solutions")
    assert r.status_code == 200
    body = r.json()
    assert body[0]["training_period"] == "từ 2024-06-01"
    assert body[1]["training_period"] == "—"


@pytest.mark.asyncio
async def test_trained_solutions_filters_by_user_when_authenticated(
    client: AsyncClient, mock_db,
):
    """Verify the SQL includes a user_id parameter when the caller is
    authenticated (the conftest's default override returns user_id=1).
    """
    _mock_rows([], mock_db)

    await client.get(f"{PREFIX}/simulation/trained-solutions")

    # db.execute(text(query), params) — params is positional arg [1].
    args = mock_db.execute.call_args.args
    sql = str(args[0])
    params = args[1] if len(args) > 1 else mock_db.execute.call_args.kwargs.get("params")
    assert "s.user_id = :user_id" in sql
    assert params == {"user_id": "1"}


@pytest.mark.asyncio
async def test_trained_solutions_no_user_filter_when_unauthenticated(
    client: AsyncClient, mock_db,
):
    """Without auth, SQL should NOT include the user_id clause."""
    _mock_rows([], mock_db)

    # Override the auth dep to return None for this single test.
    from app.main import app as fastapi_app
    fastapi_app.dependency_overrides[get_current_user_optional] = lambda: None
    try:
        await client.get(f"{PREFIX}/simulation/trained-solutions")
    finally:
        # Restore the conftest's default override (the test client cleanup
        # will clear all overrides at fixture teardown anyway).
        from app.api.dependencies import get_current_user_optional as gco
        fastapi_app.dependency_overrides[gco] = lambda: {
            "user_id": 1, "email": "test@example.com", "role": "user"
        }

    args = mock_db.execute.call_args.args
    sql = str(args[0])
    params = args[1] if len(args) > 1 else mock_db.execute.call_args.kwargs.get("params")
    assert "s.user_id" not in sql
    assert params == {}


@pytest.mark.asyncio
async def test_trained_solutions_filters_by_train_status(
    client: AsyncClient, mock_db,
):
    """Always include the train_status IN clause regardless of auth."""
    _mock_rows([], mock_db)

    await client.get(f"{PREFIX}/simulation/trained-solutions")

    sql = str(mock_db.execute.call_args.args[0])
    assert "s.train_status IN ('trained', 'predicted')" in sql


@pytest.mark.asyncio
async def test_trained_solutions_returns_empty_on_db_error(
    client: AsyncClient, mock_db,
):
    """Any unexpected DB error degrades to [] rather than 500.
    Frontend simulation dashboard expects an array no matter what."""
    mock_db.execute.side_effect = RuntimeError("DB down")

    r = await client.get(f"{PREFIX}/simulation/trained-solutions")
    assert r.status_code == 200
    assert r.json() == []


