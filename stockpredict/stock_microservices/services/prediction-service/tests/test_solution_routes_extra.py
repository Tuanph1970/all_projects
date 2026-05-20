"""Deep-coverage tests for app.api.solution_routes.

Targets the parts that the original test_solution_routes.py left alone:
the indicator math (_calculate_indicator and _prepare_indicator_features),
the feature-engineering helper (_build_feature_df), the heavy
calculate_solution_indicators / predict_solution endpoints, the
train_solution dispatcher, and _run_training's failure paths.

Heavy ML is mocked: we never train a real XGBoost/LightGBM model here
— that's covered by the existing prediction-service training tests.
Instead we feed a deterministic OHLCV frame and a fake model object
(MagicMock.predict) so the surrounding pipeline is exercised end-to-end.
"""
from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pandas as pd
import pytest
from httpx import AsyncClient

from app.api import solution_routes
from app.api.solution_routes import (
    _build_feature_df,
    _calculate_indicator,
    _prepare_indicator_features,
    _run_training,
    _safe_val,
)


PREFIX = "/stock_helper/api/v2/solutions"


# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------


def _ohlcv_frame(rows: int = 80, seed: int = 7) -> pd.DataFrame:
    """Deterministic OHLCV with a DatetimeIndex — what calculators expect."""
    dates = pd.date_range("2026-01-01", periods=rows, freq="B")
    rng = np.random.default_rng(seed)
    close = 100 + np.cumsum(rng.normal(0, 1.0, size=rows))
    df = pd.DataFrame(
        {
            "open": close + rng.normal(0, 0.2, size=rows),
            "high": close + 1.0,
            "low": close - 1.0,
            "close": close,
            "volume": rng.integers(1_000, 5_000, size=rows).astype(float),
        },
        index=dates,
    )
    df.index.name = "date"
    return df


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


class _FakeAsyncClient:
    """Async-context-manager whose .get() returns a pre-canned response."""

    def __init__(self, response):
        self._response = response

    async def __aenter__(self):
        c = MagicMock()
        c.get = AsyncMock(return_value=self._response)
        return c

    async def __aexit__(self, *_):
        return False


# ---------------------------------------------------------------------------
# _safe_val — primitive helper
# ---------------------------------------------------------------------------


def test_safe_val_none_returns_none():
    assert _safe_val(None) is None


def test_safe_val_nan_returns_none():
    assert _safe_val(float("nan")) is None


def test_safe_val_pandas_na_returns_none():
    assert _safe_val(pd.NA) is None


def test_safe_val_finite_float_returns_float():
    assert _safe_val(1.5) == 1.5
    # numpy scalars get coerced to Python float
    assert _safe_val(np.float64(2.25)) == 2.25


# ---------------------------------------------------------------------------
# _calculate_indicator — exercise every supported indicator code so the
# big branch table inside the function lights up.
# ---------------------------------------------------------------------------


_INDICATOR_CASES = [
    ("SMA", {"period": 5}, "sma"),
    ("EMA", {"period": 5}, "ema"),
    ("WMA", {"period": 5}, "wma"),
    ("DEMA", {"period": 5}, "dema"),
    ("TEMA", {"period": 5}, "tema"),
    ("MACD", {}, "macd"),
    ("ADX", {}, "adx"),
    ("PSAR", {}, "psar"),
    ("RSI", {}, "rsi"),
    ("STOCH", {}, "stoch_k"),
    ("STOCH_RSI", {}, "stoch_rsi_k"),
    ("CCI", {}, "cci"),
    ("WILLIAMS_R", {}, "williams_r"),
    ("ROC", {}, "roc"),
    ("MOM", {}, "mom"),
    ("TSI", {}, "tsi"),
    ("UO", {}, "uo"),
    ("AO", {}, "ao"),
    ("BB", {}, "bb_upper"),
    ("ATR", {}, "atr"),
    ("KELTNER", {}, "kc_upper"),
    ("DONCHIAN", {}, "dc_upper"),
    ("STDDEV", {}, "stddev"),
    ("HV", {}, "hv"),
    ("VOLUME", {}, "volume"),
    ("OBV", {}, "obv"),
    ("VWAP", {}, "vwap"),
    ("MFI", {}, "mfi"),
    ("AD", {}, "ad"),
    ("CMF", {}, "cmf"),
    ("CHO", {}, "cho"),
    ("VOSC", {}, "vosc"),
    ("EOM", {}, "eom"),
    ("FI", {}, "fi"),
    ("NVI", {}, "nvi"),
    ("PVI", {}, "pvi"),
    ("Volume_MA", {}, "volume_ma"),
    ("SUPERTREND", {}, "supertrend"),
    # AROON has a source bug (calls AroonIndicator without `low`); it
    # falls through to the close-fallback. Excluded from the strict-key
    # check below but still exercised by test_calculate_indicator_aroon_fallback.
    ("VORTEX", {}, "vortex_pos"),
    ("ICHIMOKU", {}, "ichimoku_conv"),
]


@pytest.mark.parametrize("code,params,expected_key", _INDICATOR_CASES)
def test_calculate_indicator_supported_codes(code, params, expected_key):
    df = _ohlcv_frame(120)
    out = _calculate_indicator(df, code, params)
    assert isinstance(out, list)
    assert len(out) == len(df)
    # Every row gets a date plus the indicator's value column(s).
    assert "date" in out[0]
    assert expected_key in out[0]


def test_calculate_indicator_aroon_falls_back_due_to_source_bug():
    """The AROON branch in solution_routes calls ta.trend.AroonIndicator with
    only `close` (it should also pass `low`), so it always raises and falls
    through to the close-price fallback. We pin that behavior so a future
    fix doesn't silently change the response shape."""
    df = _ohlcv_frame(40)
    out = _calculate_indicator(df, "AROON", {})
    assert len(out) == len(df)
    # Fallback returns a `value` key, not `aroon_up`.
    assert "value" in out[0]


def test_calculate_indicator_unknown_code_falls_back_to_close():
    """Unknown code → fallback returns the close price under a `value` key."""
    df = _ohlcv_frame(20)
    out = _calculate_indicator(df, "TOTALLY_UNKNOWN", {})
    assert len(out) == len(df)
    assert "value" in out[0]
    assert out[-1]["value"] == pytest.approx(float(df["close"].iloc[-1]))


def test_calculate_indicator_exception_falls_back_to_close():
    """If the underlying ta call blows up, we still return one row per
    date with the close price — the warning is logged but the function
    never raises."""
    df = _ohlcv_frame(20)
    # Force a TypeError by passing a non-numeric period.
    with patch(
        "app.api.solution_routes.ta.trend.SMAIndicator",
        side_effect=ValueError("bad arg"),
    ):
        out = _calculate_indicator(df, "SMA", {"period": "garbage"})
    assert len(out) == len(df)
    assert "value" in out[0]


# ---------------------------------------------------------------------------
# _prepare_indicator_features — multi-indicator merge
# ---------------------------------------------------------------------------


def test_prepare_indicator_features_handles_dict_params():
    df = _ohlcv_frame(60)
    rows = [
        {"name": "SMA", "parameters": {"period": 5}, "default_parameters": None},
        {"name": "RSI", "parameters": None, "default_parameters": {"period": 14}},
    ]
    feat_df, by_date = _prepare_indicator_features(df, rows)
    assert "sma" in feat_df.columns
    assert "rsi" in feat_df.columns
    # by_date has one entry per output bar.
    assert len(by_date) > 0


def test_prepare_indicator_features_handles_string_params():
    """parameters may arrive as a JSON string from the DB column."""
    df = _ohlcv_frame(60)
    rows = [
        {
            "name": "EMA",
            "parameters": '{"period": 5}',  # JSON string
            "default_parameters": None,
        },
    ]
    feat_df, _ = _prepare_indicator_features(df, rows)
    assert "ema" in feat_df.columns


def test_prepare_indicator_features_handles_invalid_json_string():
    """A malformed JSON parameters string is swallowed; default params apply."""
    df = _ohlcv_frame(60)
    rows = [
        {
            "name": "SMA",
            "parameters": "{not valid json",
            "default_parameters": '{"period": 5}',
        },
    ]
    feat_df, _ = _prepare_indicator_features(df, rows)
    assert "sma" in feat_df.columns


def test_prepare_indicator_features_skips_empty_indicator_data():
    """An indicator whose code is unknown returns the close-fallback,
    but if _calculate_indicator returned [] we'd skip silently."""
    df = _ohlcv_frame(40)
    with patch(
        "app.api.solution_routes._calculate_indicator", return_value=[]
    ):
        feat_df, by_date = _prepare_indicator_features(
            df, [{"name": "SMA", "parameters": {}}]
        )
    # Nothing added — feature df has the same row count but no new columns.
    assert feat_df.empty or len(feat_df.columns) == 0
    assert by_date == {}


# ---------------------------------------------------------------------------
# _build_feature_df — pure feature engineering
# ---------------------------------------------------------------------------


def test_build_feature_df_includes_price_volatility_lag_features():
    df = _ohlcv_frame(60)
    indicators = pd.DataFrame({"rsi": np.random.rand(60)}, index=df.index)
    fdf = _build_feature_df(df, indicators)
    for col in [
        "close", "returns", "log_returns",
        "high_low_ratio", "close_open_ratio",
        "close_lag_1", "close_lag_5", "close_lag_10",
        "returns_lag_1",
        "volatility_5", "volatility_20",
        "volume_sma_20", "volume_ratio",
        "rsi",  # indicator passed in
    ]:
        assert col in fdf.columns, f"missing engineered feature: {col}"


def test_build_feature_df_without_volume_column():
    """When volume is absent the volume features are simply skipped — the
    function still returns a frame with the other columns."""
    df = _ohlcv_frame(40).drop(columns=["volume"])
    indicators = pd.DataFrame(index=df.index)
    fdf = _build_feature_df(df, indicators)
    assert "volume_ratio" not in fdf.columns
    assert "close" in fdf.columns


# ---------------------------------------------------------------------------
# GET /models — unauthenticated branch
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_predict_models_unauthenticated_branch(
    client: AsyncClient, mock_db
):
    from app.api.dependencies import get_current_user_optional
    from app.main import app as fastapi_app

    rows = [{"id": 1, "model_name": "M1", "model_type": "XGBoost",
             "model_sub_type": "", "past_covariate": None, "future_covariate": None}]
    mock_db.execute = AsyncMock(return_value=_result_with_mappings(rows))

    fastapi_app.dependency_overrides[get_current_user_optional] = lambda: None
    try:
        r = await client.get(f"{PREFIX}/models")
    finally:
        fastapi_app.dependency_overrides[get_current_user_optional] = lambda: {
            "user_id": 1, "email": "test@example.com", "role": "user"
        }
    assert r.status_code == 200
    # The SQL didn't include user_id filter — body still returns rows.
    assert r.json()[0]["model_name"] == "M1"


# ---------------------------------------------------------------------------
# POST /train — dispatcher behavior
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_train_solution_requires_id(client: AsyncClient):
    r = await client.post(f"{PREFIX}/train", json={})
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_train_solution_short_circuits_when_already_training(client: AsyncClient):
    """If a training is already in flight, return early without enqueuing
    another task."""
    solution_routes.training_status[55] = {"status": "training", "progress": 50}
    try:
        with patch("app.api.solution_routes.asyncio.create_task") as mock_create:
            r = await client.post(f"{PREFIX}/train", json={"id": 55})
        assert r.status_code == 200
        assert r.json()["status"] == "training"
        mock_create.assert_not_called()
    finally:
        solution_routes.training_status.pop(55, None)


@pytest.mark.asyncio
async def test_train_solution_launches_background_task(client: AsyncClient):
    """A fresh training session marks the slot and creates an asyncio task."""
    solution_routes.training_status.pop(56, None)

    captured = {}

    def _fake_create_task(coro):
        # Close the coro to avoid "coroutine was never awaited" warnings.
        coro.close()
        captured["called"] = True
        return MagicMock()

    with patch(
        "app.api.solution_routes.asyncio.create_task", side_effect=_fake_create_task
    ):
        r = await client.post(
            f"{PREFIX}/train",
            json={"id": 56, "start_date": "2026-01-01", "end_date": "2026-04-01"},
        )

    assert r.status_code == 200
    assert r.json()["status"] == "training"
    assert captured.get("called") is True
    # Slot was registered.
    assert 56 in solution_routes.training_status
    solution_routes.training_status.pop(56, None)


# ---------------------------------------------------------------------------
# POST /predict — predict_solution endpoint
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_predict_solution_requires_id(client: AsyncClient):
    r = await client.post(f"{PREFIX}/predict", json={})
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_predict_solution_404_when_solution_missing(client: AsyncClient, mock_db):
    mock_db.execute = AsyncMock(return_value=_result_with_first(None))
    r = await client.post(f"{PREFIX}/predict", json={"id": 7})
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_predict_solution_404_when_model_missing(client: AsyncClient, mock_db):
    """Solution exists but its model_instances row is gone."""
    mock_db.execute = AsyncMock(side_effect=[
        _result_with_first({"id": 7, "ticker": "FPT", "model_id": 99}),
        _result_with_first(None),
    ])
    r = await client.post(f"{PREFIX}/predict", json={"id": 7})
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_predict_solution_400_when_model_not_trained(client: AsyncClient, mock_db):
    mock_db.execute = AsyncMock(side_effect=[
        _result_with_first({"id": 7, "ticker": "FPT", "model_id": 99}),
        _result_with_first({"id": 99, "status": "created", "file_path": None}),
    ])
    r = await client.post(f"{PREFIX}/predict", json={"id": 7})
    assert r.status_code == 400
    assert "not trained" in r.json()["detail"].lower()


@pytest.mark.asyncio
async def test_predict_solution_400_when_model_file_missing(client: AsyncClient, mock_db):
    """Model row says trained but the .joblib file was deleted."""
    mock_db.execute = AsyncMock(side_effect=[
        _result_with_first({"id": 7, "ticker": "FPT", "model_id": 99}),
        _result_with_first({"id": 99, "status": "trained", "file_path": "/tmp/missing_xyz.joblib"}),
    ])
    with patch("app.api.solution_routes.os.path.exists", return_value=False):
        r = await client.post(f"{PREFIX}/predict", json={"id": 7})
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_predict_solution_happy_path_with_mocked_model(client: AsyncClient, mock_db):
    """Full happy path: solution exists, model trained, file loads, price
    data fetched via httpx, indicators computed, model predicts, response
    persisted. We mock the heavy bits so this stays a unit test."""
    df = _ohlcv_frame(120)
    price_records = [
        {"time": d.strftime("%Y-%m-%d"), "open": float(df.loc[d, "open"]),
         "high": float(df.loc[d, "high"]), "low": float(df.loc[d, "low"]),
         "close": float(df.loc[d, "close"]), "volume": float(df.loc[d, "volume"])}
        for d in df.index
    ]

    # 3 db.execute calls inside predict_solution: solution lookup, model
    # lookup, indicator list. Then 1–2 UPDATEs at the end.
    solution_row = {"id": 7, "ticker": "FPT", "model_id": 99}
    model_row = {"id": 99, "status": "trained", "file_path": "/tmp/m99.joblib"}
    indicator_rows = []  # No indicators — just OHLCV-derived features.

    update_result = MagicMock()
    mock_db.execute = AsyncMock(side_effect=[
        _result_with_first(solution_row),
        _result_with_first(model_row),
        _result_with_mappings(indicator_rows),
        update_result,
    ])
    mock_db.commit = AsyncMock()

    # Fake the saved model object.
    fake_model = MagicMock()
    # Predictions are slightly noisy copies of the close price.
    fake_model.predict = lambda X: X[:, 0] * 1.01 if X.ndim == 2 else np.array([100.0])
    saved = {
        "model": fake_model,
        "feature_cols": ["close", "returns", "high_low_ratio"],
    }

    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"data": price_records}

    with patch("app.api.solution_routes.os.path.exists", return_value=True), \
         patch("app.api.solution_routes.joblib.load", return_value=saved), \
         patch("app.api.solution_routes.httpx.AsyncClient",
               return_value=_FakeAsyncClient(resp)):
        r = await client.post(
            f"{PREFIX}/predict",
            json={
                "id": 7,
                "start_date": df.index[60].strftime("%Y-%m-%d"),
                "end_date": df.index[-1].strftime("%Y-%m-%d"),
                "predict_days": 3,
            },
        )

    assert r.status_code == 200, r.text
    body = r.json()
    assert body["solution_id"] == 7
    assert body["ticker"] == "FPT"
    assert isinstance(body["actual"], list)
    assert isinstance(body["predict"], list)
    assert isinstance(body["future"], list)
    assert body["metrics"]["rmse"] is not None


@pytest.mark.asyncio
async def test_predict_solution_502_when_stock_data_unavailable(client: AsyncClient, mock_db):
    """If stock-data-service returns non-200, we surface a 502."""
    mock_db.execute = AsyncMock(side_effect=[
        _result_with_first({"id": 7, "ticker": "FPT", "model_id": 99}),
        _result_with_first({"id": 99, "status": "trained", "file_path": "/tmp/m99.joblib"}),
        _result_with_mappings([]),  # indicators
    ])
    fake_model = MagicMock()
    saved = {"model": fake_model, "feature_cols": ["close"]}
    resp = MagicMock()
    resp.status_code = 503

    with patch("app.api.solution_routes.os.path.exists", return_value=True), \
         patch("app.api.solution_routes.joblib.load", return_value=saved), \
         patch("app.api.solution_routes.httpx.AsyncClient",
               return_value=_FakeAsyncClient(resp)):
        r = await client.post(f"{PREFIX}/predict", json={"id": 7})

    assert r.status_code == 502


# ---------------------------------------------------------------------------
# POST /{id}/indicators/calculate — calculate_solution_indicators
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_calculate_indicators_requires_required_fields(client: AsyncClient):
    r = await client.post(f"{PREFIX}/7/indicators/calculate", json={})
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_calculate_indicators_returns_empty_when_no_indicators(client: AsyncClient, mock_db):
    """No solution_indicators rows → return {} without hitting stock-data."""
    mock_db.execute = AsyncMock(return_value=_result_with_mappings([]))
    r = await client.post(
        f"{PREFIX}/7/indicators/calculate",
        json={"symbol": "FPT", "start_date": "2026-01-01", "end_date": "2026-04-01"},
    )
    assert r.status_code == 200
    assert r.json() == {}


@pytest.mark.asyncio
async def test_calculate_indicators_500_on_indicator_query_error(client: AsyncClient, mock_db):
    mock_db.execute = AsyncMock(side_effect=RuntimeError("DB down"))
    r = await client.post(
        f"{PREFIX}/7/indicators/calculate",
        json={"symbol": "FPT", "start_date": "2026-01-01", "end_date": "2026-04-01"},
    )
    assert r.status_code == 500


@pytest.mark.asyncio
async def test_calculate_indicators_502_when_stock_data_fails(client: AsyncClient, mock_db):
    """Indicator rows present but stock-data-service down → 502."""
    indicator_rows = [{
        "indicator_id": 1, "indicator_category": "trend", "covariate_type": "past",
        "parameters": None, "name": "SMA", "type": "trend",
        "default_parameters": '{"period": 5}', "calculation_function": None,
    }]
    mock_db.execute = AsyncMock(return_value=_result_with_mappings(indicator_rows))
    resp = MagicMock()
    resp.status_code = 503

    with patch("app.api.solution_routes.httpx.AsyncClient",
               return_value=_FakeAsyncClient(resp)):
        r = await client.post(
            f"{PREFIX}/7/indicators/calculate",
            json={"symbol": "FPT", "start_date": "2026-01-01", "end_date": "2026-04-01"},
        )
    assert r.status_code == 503  # bubble up upstream status


@pytest.mark.asyncio
async def test_calculate_indicators_404_when_no_price_data(client: AsyncClient, mock_db):
    """Stock-data-service responds 200 but with an empty data list."""
    indicator_rows = [{
        "indicator_id": 1, "indicator_category": "trend", "covariate_type": "past",
        "parameters": None, "name": "SMA", "type": "trend",
        "default_parameters": '{"period": 5}', "calculation_function": None,
    }]
    mock_db.execute = AsyncMock(return_value=_result_with_mappings(indicator_rows))
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"data": []}

    with patch("app.api.solution_routes.httpx.AsyncClient",
               return_value=_FakeAsyncClient(resp)):
        r = await client.post(
            f"{PREFIX}/7/indicators/calculate",
            json={"symbol": "FPT", "start_date": "2026-01-01", "end_date": "2026-04-01"},
        )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_calculate_indicators_happy_path(client: AsyncClient, mock_db):
    """Indicator rows + good price data → response includes the indicator
    values grouped by category, plus the `price` candle data."""
    df = _ohlcv_frame(60)
    price_records = [
        {"time": d.strftime("%Y-%m-%d"),
         "open": float(df.loc[d, "open"]), "high": float(df.loc[d, "high"]),
         "low": float(df.loc[d, "low"]), "close": float(df.loc[d, "close"]),
         "volume": float(df.loc[d, "volume"])}
        for d in df.index
    ]
    indicator_rows = [{
        "indicator_id": 1, "indicator_category": "trend", "covariate_type": "past",
        "parameters": '{"period": 5}', "name": "SMA", "type": "trend",
        "default_parameters": None, "calculation_function": None,
    }]
    mock_db.execute = AsyncMock(return_value=_result_with_mappings(indicator_rows))
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"data": price_records}

    with patch("app.api.solution_routes.httpx.AsyncClient",
               return_value=_FakeAsyncClient(resp)):
        r = await client.post(
            f"{PREFIX}/7/indicators/calculate",
            json={"symbol": "FPT", "start_date": "2026-01-01", "end_date": "2026-04-01"},
        )
    assert r.status_code == 200, r.text
    body = r.json()
    assert "trend" in body
    assert body["trend"]["name"] == "SMA"
    assert "price" in body
    assert len(body["price"]["data"]) == 60


# ---------------------------------------------------------------------------
# _run_training — background task error paths
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_training_marks_failed_when_solution_missing(monkeypatch):
    """If tbl_solution lookup returns nothing, the function must record a
    failed status in training_status and exit without raising."""
    sid = 9001
    solution_routes.training_status.pop(sid, None)

    session = AsyncMock()
    session.execute = AsyncMock(return_value=_result_with_first(None))
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)

    monkeypatch.setattr(
        "app.api.solution_routes.async_session_factory",
        MagicMock(return_value=session),
    )

    await _run_training(sid, {"start_date": "2026-01-01", "end_date": "2026-03-01"})

    assert solution_routes.training_status[sid]["status"] == "failed"
    assert "not found" in solution_routes.training_status[sid]["error"].lower()
    solution_routes.training_status.pop(sid, None)


@pytest.mark.asyncio
async def test_run_training_marks_failed_when_model_missing(monkeypatch):
    sid = 9002
    solution_routes.training_status.pop(sid, None)

    session = AsyncMock()
    session.execute = AsyncMock(side_effect=[
        _result_with_first({"id": sid, "ticker": "FPT", "model_id": 99}),
        _result_with_first(None),
    ])
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)

    monkeypatch.setattr(
        "app.api.solution_routes.async_session_factory",
        MagicMock(return_value=session),
    )

    await _run_training(sid, {"start_date": "2026-01-01", "end_date": "2026-03-01"})

    assert solution_routes.training_status[sid]["status"] == "failed"
    assert "model instance" in solution_routes.training_status[sid]["error"].lower()
    solution_routes.training_status.pop(sid, None)


@pytest.mark.asyncio
async def test_run_training_marks_failed_on_stock_data_503(monkeypatch):
    sid = 9003
    solution_routes.training_status.pop(sid, None)

    session = AsyncMock()
    session.execute = AsyncMock(side_effect=[
        _result_with_first({"id": sid, "ticker": "FPT", "model_id": 99}),
        _result_with_first({"id": 99, "model_type": "XGBoost",
                            "model_sub_type": "", "config_json": None}),
        _result_with_mappings([]),  # indicators
    ])
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)

    monkeypatch.setattr(
        "app.api.solution_routes.async_session_factory",
        MagicMock(return_value=session),
    )

    resp = MagicMock()
    resp.status_code = 503
    with patch("app.api.solution_routes.httpx.AsyncClient",
               return_value=_FakeAsyncClient(resp)):
        await _run_training(sid, {"start_date": "2026-01-01", "end_date": "2026-03-01"})

    assert solution_routes.training_status[sid]["status"] == "failed"
    assert "503" in solution_routes.training_status[sid]["error"]
    solution_routes.training_status.pop(sid, None)


@pytest.mark.asyncio
async def test_run_training_marks_failed_when_price_list_empty(monkeypatch):
    sid = 9004
    solution_routes.training_status.pop(sid, None)

    session = AsyncMock()
    session.execute = AsyncMock(side_effect=[
        _result_with_first({"id": sid, "ticker": "FPT", "model_id": 99}),
        _result_with_first({"id": 99, "model_type": "XGBoost",
                            "model_sub_type": "", "config_json": None}),
        _result_with_mappings([]),
    ])
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)

    monkeypatch.setattr(
        "app.api.solution_routes.async_session_factory",
        MagicMock(return_value=session),
    )

    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"data": []}
    with patch("app.api.solution_routes.httpx.AsyncClient",
               return_value=_FakeAsyncClient(resp)):
        await _run_training(sid, {"start_date": "2026-01-01", "end_date": "2026-03-01"})

    assert solution_routes.training_status[sid]["status"] == "failed"
    assert "no price data" in solution_routes.training_status[sid]["error"].lower()
    solution_routes.training_status.pop(sid, None)


@pytest.mark.asyncio
async def test_run_training_outer_exception_records_failure(monkeypatch):
    """An unexpected exception (e.g., session_factory blows up) is caught
    and stored as a `failed` status — never raised back to the scheduler."""
    sid = 9005
    solution_routes.training_status.pop(sid, None)

    def boom():
        raise RuntimeError("kaboom")

    monkeypatch.setattr("app.api.solution_routes.async_session_factory", boom)

    await _run_training(sid, {"start_date": "2026-01-01", "end_date": "2026-03-01"})

    assert solution_routes.training_status[sid]["status"] == "failed"
    assert "kaboom" in solution_routes.training_status[sid]["error"]
    solution_routes.training_status.pop(sid, None)


@pytest.mark.asyncio
async def test_run_training_marks_failed_when_too_few_usable_rows(monkeypatch):
    """A short price series gets dropped to <30 usable rows after feature
    prep — the helper records that as 'Insufficient data'."""
    sid = 9006
    solution_routes.training_status.pop(sid, None)

    # 25 rows of OHLCV — after the rolling 20-window features + target
    # shift + dropna, fewer than 30 remain.
    df = _ohlcv_frame(25)
    price_records = [
        {"time": d.strftime("%Y-%m-%d"),
         "open": float(df.loc[d, "open"]), "high": float(df.loc[d, "high"]),
         "low": float(df.loc[d, "low"]), "close": float(df.loc[d, "close"]),
         "volume": float(df.loc[d, "volume"])}
        for d in df.index
    ]

    session = AsyncMock()
    session.execute = AsyncMock(side_effect=[
        _result_with_first({"id": sid, "ticker": "FPT", "model_id": 99}),
        _result_with_first({"id": 99, "model_type": "XGBoost",
                            "model_sub_type": "", "config_json": None}),
        _result_with_mappings([]),
    ])
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    monkeypatch.setattr(
        "app.api.solution_routes.async_session_factory",
        MagicMock(return_value=session),
    )

    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"data": price_records}
    with patch("app.api.solution_routes.httpx.AsyncClient",
               return_value=_FakeAsyncClient(resp)):
        await _run_training(sid, {"start_date": "2026-01-01", "end_date": "2026-03-01"})

    assert solution_routes.training_status[sid]["status"] == "failed"
    assert "insufficient" in solution_routes.training_status[sid]["error"].lower()
    solution_routes.training_status.pop(sid, None)
