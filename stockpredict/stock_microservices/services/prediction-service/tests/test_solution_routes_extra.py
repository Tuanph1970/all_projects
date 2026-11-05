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
    """Async-context-manager whose .get() returns a pre-canned response.

    It also RECORDS the query parameters of the last call, because Backlog #128
    is about the date range the service asks stock-data-service for: a test that
    only checked the response could not tell a widened warm-up window from the
    flat 60 days it replaced.
    """

    def __init__(self, response):
        self._response = response
        self.last_params = None
        self.last_url = None

    async def __aenter__(self):
        async def _get(url, **kwargs):
            self.last_url = url
            self.last_params = kwargs.get("params") or {}
            return self._response

        c = MagicMock()
        c.get = _get
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
    # AROON joined this sweep when #130 fixed it; it used to be excluded here
    # because it always fell through to the close-price fallback.
    ("AROON", {}, "aroon_up"),
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


# THESE THREE TESTS USED TO ASSERT THE OPPOSITE, and the rewrite is the point
# of Backlog #130 rather than a convenience.
#
# They pinned the close-price fallback: one of them even said "we pin that
# behavior so a future fix doesn't silently change the response shape". That
# sentence was right about the shape and wrong about what deserved pinning —
# the shape it protected was a column of CLOSE PRICES wearing the name of the
# indicator the operator had chosen, which is the #109/#110/#112 defect class
# and the quietest member of it, because close-as-a-feature produces entirely
# plausible metrics.
#
# A test can hold a known defect in place deliberately; that is legitimate when
# the defect is documented and the alternative is worse. Here the alternative
# was not worse, and nothing in the register said this was a deliberate
# compromise — it was simply never revisited. So the pin is replaced by its
# opposite, and the three tests now say: AROON computes, and anything that
# cannot be computed raises instead of lying.


def test_aroon_is_computed_from_the_high_and_low_extremes():
    """Backlog #130. The branch passed `close` as the first positional argument
    and nothing for `low`, so AroonIndicator raised on EVERY call and AROON was
    silently the close price for as long as it has been in the catalogue.

    Aroon measures how long since the highest high and the lowest low, so the
    values must respond to the HIGH/LOW extremes and must be percentages."""
    df = _ohlcv_frame(60)
    out = _calculate_indicator(df, "AROON", {"period": 25})
    assert len(out) == len(df)
    assert "aroon_up" in out[0] and "aroon_down" in out[0]
    assert "value" not in out[0], "a `value` key means it fell back to close"
    settled = [r for r in out[30:] if r["aroon_up"] is not None]
    assert settled, "no finite values after the warm-up"
    assert all(0 <= r["aroon_up"] <= 100 and 0 <= r["aroon_down"] <= 100
               for r in settled), "Aroon is a percentage"


def test_aroon_reads_the_highs_and_not_the_closes():
    """Non-vacuity for the fix: if `close` were still being passed, moving the
    highs alone could not change the answer."""
    df = _ohlcv_frame(60)
    base = _calculate_indicator(df, "AROON", {"period": 25})
    lifted = df.copy()
    lifted.iloc[-1, lifted.columns.get_loc("high")] += 50      # a new extreme
    after = _calculate_indicator(lifted, "AROON", {"period": 25})
    assert base[-1]["aroon_up"] != after[-1]["aroon_up"]


def test_an_unimplemented_indicator_raises_instead_of_returning_close():
    """Thirteen catalogue entries have no implementation (measured 2026-11-05:
    FIB_EXT, FIB_RET, PIVOT, HEIKIN_ASHI, MP, RENKO, TP, WC, AC, ALLIGATOR,
    FRACTALS, GATOR, MFI_BW). They came back as close prices under the chosen
    indicator's name."""
    df = _ohlcv_frame(20)
    with pytest.raises(solution_routes.IndicatorError, match="no implementation"):
        _calculate_indicator(df, "TOTALLY_UNKNOWN", {})


def test_a_library_failure_raises_instead_of_returning_close():
    """The quietest route into the same defect: any exception from `ta` used to
    become a close-price column plus a log line nobody reads."""
    df = _ohlcv_frame(20)
    with patch(
        "app.api.solution_routes.ta.trend.SMAIndicator",
        side_effect=ValueError("bad arg"),
    ):
        with pytest.raises(solution_routes.IndicatorError, match="could not be calculated"):
            _calculate_indicator(df, "SMA", {"period": "garbage"})


def test_the_raised_error_names_the_indicator_and_the_reason():
    """The operator has to be told WHICH indicator and WHY, or the disclosure is
    just a failure with no action attached."""
    df = _ohlcv_frame(20)
    with patch("app.api.solution_routes.ta.trend.SMAIndicator",
               side_effect=ValueError("bad arg")):
        try:
            _calculate_indicator(df, "SMA", {})
        except solution_routes.IndicatorError as exc:
            assert "SMA" in str(exc)
            assert "ValueError" in str(exc) and "bad arg" in str(exc)
        else:
            pytest.fail("no IndicatorError raised")


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


# ---------------------------------------------------------------------------
# Backlog #127 — the forecast horizon is the model's own
# ---------------------------------------------------------------------------
#
# Three numbers used to disagree for one model: the config said
# output_chunk_length, the training result's prediction_dates block said 10, and
# the forecast was DEFAULT_PREDICTION_DAYS long. resolve_output_chunk_length is
# now the single answer, so these tests pin the precedence rather than any one
# literal.


def test_the_horizon_comes_from_the_models_config():
    assert solution_routes.resolve_output_chunk_length({"output_chunk_length": 7}) == 7


def test_a_horizon_stored_as_a_string_is_read_as_a_number():
    """config_json is written by the Solutions form, which posts '10' not 10 —
    the same shape that made #124's hyperparameters reach darts as strings."""
    assert solution_routes.resolve_output_chunk_length(
        '{"output_chunk_length": "10", "n_epochs": "300"}') == 10


def test_an_explicit_predict_days_outranks_the_config():
    """A caller naming a number is not making a mistake, and predict_days
    predates the horizon living in the config."""
    assert solution_routes.resolve_output_chunk_length(
        {"output_chunk_length": 10}, requested=3) == 3


def test_a_model_declaring_no_horizon_keeps_the_previous_offer():
    """RNN is parameterised by training_length and has no output_chunk_length at
    all. Those models offered 10 before this change and must still offer 10 —
    the fix is meant to change behaviour only where the config speaks."""
    assert solution_routes.resolve_output_chunk_length(
        {"training_length": 30}) == solution_routes.PREDICTION_HORIZON_FALLBACK


@pytest.mark.parametrize("junk", [None, "", "not a json", "[]", {"output_chunk_length": "abc"},
                                 {"output_chunk_length": 0}, {"output_chunk_length": -5}])
def test_an_unusable_horizon_falls_back_rather_than_forecasting_nothing(junk):
    """A zero or negative horizon would make the forecast loop produce an empty
    series — the #128 symptom arriving by a different route."""
    assert solution_routes.resolve_output_chunk_length(junk) == \
        solution_routes.PREDICTION_HORIZON_FALLBACK


def test_a_horizon_beyond_the_service_maximum_is_clamped():
    settings = solution_routes.settings
    assert solution_routes.resolve_output_chunk_length(
        {"output_chunk_length": settings.MAX_PREDICTION_DAYS + 50}
    ) == settings.MAX_PREDICTION_DAYS


@pytest.mark.asyncio
async def test_the_forecast_is_as_long_as_the_models_horizon(client: AsyncClient, mock_db):
    """#127 end to end: no predict_days in the request, so the forecast length
    must come from config_json — it used to be DEFAULT_PREDICTION_DAYS."""
    horizon = 7
    assert horizon != solution_routes.settings.DEFAULT_PREDICTION_DAYS, \
        "the test would pass vacuously if these agreed"

    df = _ohlcv_frame(200)
    price_records = [
        {"time": d.strftime("%Y-%m-%d"), "open": float(df.loc[d, "open"]),
         "high": float(df.loc[d, "high"]), "low": float(df.loc[d, "low"]),
         "close": float(df.loc[d, "close"]), "volume": float(df.loc[d, "volume"])}
        for d in df.index
    ]

    mock_db.execute = AsyncMock(side_effect=[
        _result_with_first({"id": 7, "ticker": "FPT", "model_id": 99}),
        _result_with_first({"id": 99, "status": "trained", "file_path": "/tmp/m99.joblib",
                            "config_json": json.dumps({"output_chunk_length": str(horizon)})}),
        _result_with_mappings([]),
        MagicMock(),
    ])
    mock_db.commit = AsyncMock()

    fake_model = MagicMock()
    fake_model.predict = lambda X: X[:, 0] * 1.01 if X.ndim == 2 else np.array([100.0])
    saved = {"model": fake_model, "feature_cols": ["close", "returns", "high_low_ratio"]}

    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"data": price_records}

    with patch("app.api.solution_routes.os.path.exists", return_value=True), \
         patch("app.api.solution_routes.joblib.load", return_value=saved), \
         patch("app.api.solution_routes.httpx.AsyncClient",
               return_value=_FakeAsyncClient(resp)):
        r = await client.post(f"{PREFIX}/predict", json={
            "id": 7,
            "start_date": df.index[150].strftime("%Y-%m-%d"),
            "end_date": df.index[-1].strftime("%Y-%m-%d"),
        })

    assert r.status_code == 200, r.text
    body = r.json()
    assert body["future_days"] == horizon
    assert len(body["future"]) == horizon


# ---------------------------------------------------------------------------
# Backlog #128 — warm-up, and refusing instead of returning an empty 200
# ---------------------------------------------------------------------------


def test_the_warmup_covers_the_fixed_feature_windows_with_no_indicators():
    """volatility_20 and close_lag_10 need bars whether or not an indicator is
    attached, so the floor applies to a solution with none."""
    days = solution_routes.warmup_calendar_days([])
    assert days >= solution_routes.BASE_WARMUP_BARS


def test_the_warmup_grows_with_the_indicator_lookback():
    """ICHIMOKU's senkou_b_period of 52 must buy more history than RSI's 14 —
    the flat 60 days this replaces is what emptied the frame."""
    short = solution_routes.warmup_calendar_days(
        [{"parameters": {"period": 14}}])
    long = solution_routes.warmup_calendar_days(
        [{"parameters": {"tenkan_period": 9, "kijun_period": 26, "senkou_b_period": 52}}])
    assert long > short
    assert long > 60, "the old flat 60-day window is what #128 was about"


def test_the_warmup_reads_parameters_stored_as_json_text():
    """solution_indicators.parameters is a JSON column; a string there must not
    silently contribute a lookback of zero."""
    as_text = solution_routes.warmup_calendar_days(
        [{"parameters": '{"senkou_b_period": 52}'}])
    as_dict = solution_routes.warmup_calendar_days(
        [{"parameters": {"senkou_b_period": 52}}])
    assert as_text == as_dict


def test_the_warmup_falls_back_to_the_catalogue_default_parameters():
    as_default = solution_routes.warmup_calendar_days(
        [{"parameters": None, "default_parameters": {"period": 200}}])
    assert as_default > solution_routes.warmup_calendar_days([{"parameters": {"period": 14}}])


@pytest.mark.parametrize("junk", [{"parameters": "not json"}, {"parameters": []},
                                  {"parameters": {"flag": "yes"}}, {}])
def test_unreadable_indicator_parameters_still_yield_the_floor(junk):
    assert solution_routes.warmup_calendar_days([junk]) >= solution_routes.BASE_WARMUP_BARS


@pytest.mark.asyncio
async def test_too_little_history_is_refused_not_returned_as_an_empty_200(
        client: AsyncClient, mock_db):
    """#128. With fewer bars than the features need, dropna() empties the frame.
    That used to come back 200 with chart/actual/predict/future all empty and
    null metrics — a blank Prediction tab and no error — or as a 500 once the
    empty array reached sklearn (RandomForest, measured 2026-11-05)."""
    df = _ohlcv_frame(8)        # fewer rows than any rolling window needs
    price_records = [
        {"time": d.strftime("%Y-%m-%d"), "open": float(df.loc[d, "open"]),
         "high": float(df.loc[d, "high"]), "low": float(df.loc[d, "low"]),
         "close": float(df.loc[d, "close"]), "volume": float(df.loc[d, "volume"])}
        for d in df.index
    ]

    mock_db.execute = AsyncMock(side_effect=[
        _result_with_first({"id": 7, "ticker": "FPT", "model_id": 99}),
        _result_with_first({"id": 99, "status": "trained", "file_path": "/tmp/m99.joblib",
                            "config_json": "{}"}),
        _result_with_mappings([]),
    ])

    fake_model = MagicMock()
    # If the guard is removed this is what receives a 0-row array; the assertion
    # below would then see a 200 or a 500 instead of the refusal.
    fake_model.predict = lambda X: X[:, 0] * 1.01
    saved = {"model": fake_model, "feature_cols": ["close", "returns"]}

    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"data": price_records}

    with patch("app.api.solution_routes.os.path.exists", return_value=True), \
         patch("app.api.solution_routes.joblib.load", return_value=saved), \
         patch("app.api.solution_routes.httpx.AsyncClient",
               return_value=_FakeAsyncClient(resp)):
        r = await client.post(f"{PREFIX}/predict", json={
            "id": 7,
            "start_date": df.index[-1].strftime("%Y-%m-%d"),
            "end_date": df.index[-1].strftime("%Y-%m-%d"),
        })

    assert r.status_code == 422, r.text
    detail = r.json()["detail"]
    assert "Not enough price history" in detail
    assert "FPT" in detail


@pytest.mark.asyncio
async def test_the_predict_request_buys_warmup_history_before_the_window(
        client: AsyncClient, mock_db):
    """The widened fetch is only useful if it reaches stock-data-service, so the
    start_date actually sent is asserted. A 1-day window used to ask for 60
    calendar days; it must now ask for enough to compute an ICHIMOKU."""
    df = _ohlcv_frame(400)
    price_records = [
        {"time": d.strftime("%Y-%m-%d"), "open": float(df.loc[d, "open"]),
         "high": float(df.loc[d, "high"]), "low": float(df.loc[d, "low"]),
         "close": float(df.loc[d, "close"]), "volume": float(df.loc[d, "volume"])}
        for d in df.index
    ]
    indicator_rows = [{
        "indicator_id": 10, "indicator_category": "trend", "covariate_type": "past",
        "parameters": '{"tenkan_period": 9, "kijun_period": 26, "senkou_b_period": 52}',
        "name": "ICHIMOKU", "type": "trend",
        "default_parameters": '{"tenkan_period": 9, "kijun_period": 26, "senkou_b_period": 52}',
        "calculation_function": "calculate_ichimoku",
    }]

    mock_db.execute = AsyncMock(side_effect=[
        _result_with_first({"id": 7, "ticker": "FPT", "model_id": 99}),
        _result_with_first({"id": 99, "status": "trained", "file_path": "/tmp/m99.joblib",
                            "config_json": "{}"}),
        _result_with_mappings(indicator_rows),
        MagicMock(),
    ])
    mock_db.commit = AsyncMock()

    fake_model = MagicMock()
    fake_model.predict = lambda X: X[:, 0] * 1.01
    saved = {"model": fake_model, "feature_cols": ["close", "returns"]}

    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"data": price_records}
    fake_client = _FakeAsyncClient(resp)

    predict_start = df.index[-1]
    with patch("app.api.solution_routes.os.path.exists", return_value=True), \
         patch("app.api.solution_routes.joblib.load", return_value=saved), \
         patch("app.api.solution_routes.httpx.AsyncClient", return_value=fake_client):
        r = await client.post(f"{PREFIX}/predict", json={
            "id": 7,
            "start_date": predict_start.strftime("%Y-%m-%d"),
            "end_date": predict_start.strftime("%Y-%m-%d"),
        })

    assert r.status_code == 200, r.text
    asked_from = pd.Timestamp(fake_client.last_params["start_date"])
    bought = (predict_start - asked_from).days
    assert bought == solution_routes.warmup_calendar_days(indicator_rows)
    assert bought > 60, "a flat 60 days is the window that emptied the frame"


def test_the_warmup_floor_covers_the_hungriest_indicator():
    """#128, second iteration. The floor is a MEASUREMENT, not a guess: every
    catalogue indicator was computed over 880 bars of FPT on 2026-11-05 and
    SUPERTREND leaves 72 leading rows NaN — on a period of 10, so no multiple
    of its parameters predicts that. The first version of this fix bought 42
    bars for it and the frame still emptied.

    The floor must also cover the fixed feature windows on top of the indicator,
    since both consume the same leading rows."""
    assert solution_routes.BASE_WARMUP_BARS >= (
        solution_routes.MEASURED_WORST_INDICATOR_WARMUP_BARS + 20 + 10)


def test_the_floor_alone_is_enough_for_the_hungriest_indicator():
    """What the previous test asserts in bars, asserted in the calendar days
    actually requested — including SUPERTREND, whose parameters are small."""
    bought_bars = solution_routes.warmup_calendar_days(
        [{"parameters": {"period": 10, "multiplier": 3}}]) / solution_routes.CALENDAR_DAYS_PER_BAR
    assert bought_bars >= solution_routes.MEASURED_WORST_INDICATOR_WARMUP_BARS + 30


def test_an_edited_period_still_widens_the_warmup_past_the_floor():
    """Non-vacuity for the proportional term now that the floor is large: a user
    who sets a 200-day moving average must not be served the floor."""
    assert solution_routes.warmup_calendar_days([{"parameters": {"period": 200}}]) > \
        solution_routes.warmup_calendar_days([])


# ---------------------------------------------------------------------------
# Backlog #126 — the darts model reaches disk, and predict can use it
# ---------------------------------------------------------------------------


class _StubDartsModel:
    """Stands in for a Darts model: saves a marker, loads back from it.

    A stub rather than a real model because what is under test here is the
    PLUMBING — two files, the class recorded by name, file_path written — and a
    real fit would make these tests slow and darts-dependent for no extra
    coverage. The real round trip is covered in test_darts_trainer.py.
    """

    def __init__(self, tag="stub"):
        self.tag = tag

    def save(self, path):
        with open(path, "w") as fh:
            fh.write(self.tag)

    @classmethod
    def load(cls, path):
        with open(path) as fh:
            return cls(fh.read())


def _fitted(tmp_model=None):
    return {
        "model": tmp_model or _StubDartsModel("fitted-here"),
        "model_type": "DLinear",
        "target_scaler": "target-scaler-object",
        "past_scaler": "past-scaler-object",
        "future_scaler": None,
        "past_columns": ["rsi_14", "sma_20"],
        "future_columns": ["dayofweek"],
        "calendar_features": ["dayofweek"],
        "input_chunk_length": 20,
        "output_chunk_length": 5,
        "price_column": "close",
    }


def test_the_darts_bundle_round_trips_through_two_files(tmp_path):
    """Darts models do not survive joblib — measured against 0.48.1, a torch
    model pickled and reloaded raises "'NoneType' object has no attribute
    'set_predict_parameters'" on its next predict. So the model goes through
    Darts' own save() and the scalers and column list through joblib beside it."""
    with patch.object(solution_routes.settings, "MODEL_PATH", str(tmp_path)):
        sidecar = solution_routes.save_darts_bundle(42, _fitted())
        saved = __import__("joblib").load(sidecar)
        assert saved["engine"] == "darts"
        assert saved["past_columns"] == ["rsi_14", "sma_20"]
        assert saved["target_scaler"] == "target-scaler-object"
        assert "model" not in saved, (
            "the model must NOT be in the joblib — that is the thing joblib "
            "breaks for torch models")
        model = solution_routes.load_darts_model(saved)
        assert isinstance(model, _StubDartsModel) and model.tag == "fitted-here"


def test_the_sidecar_records_the_class_by_name_not_by_pickle(tmp_path):
    """Darts' generic ForecastingModel.load refuses a torch checkpoint
    (measured: UnpicklingError), so loading needs the concrete class. An import
    path is inspectable where a pickled class reference is not."""
    with patch.object(solution_routes.settings, "MODEL_PATH", str(tmp_path)):
        saved = __import__("joblib").load(
            solution_routes.save_darts_bundle(43, _fitted()))
    assert saved["model_class"] == "_StubDartsModel"
    assert saved["model_module"] == _StubDartsModel.__module__


def test_a_missing_darts_model_file_is_reported_rather_than_crashing(tmp_path):
    """The sidecar can outlive the model file — a cleared volume, a half-copied
    backup. The message has to say what to do."""
    with patch.object(solution_routes.settings, "MODEL_PATH", str(tmp_path)):
        sidecar = solution_routes.save_darts_bundle(44, _fitted())
    saved = __import__("joblib").load(sidecar)
    import os as _os
    _os.remove(saved["model_path"])
    with pytest.raises(FileNotFoundError, match="retrain"):
        solution_routes.load_darts_model(saved)


@pytest.mark.asyncio
async def test_predict_uses_the_darts_branch_when_the_bundle_says_darts(
        client: AsyncClient, mock_db):
    """#126 end to end through the route: a darts bundle must not reach the
    tabular pipeline, which calls ml_model.predict(X) on a feature MATRIX."""
    df = _ohlcv_frame(300)
    price_records = [
        {"time": d.strftime("%Y-%m-%d"), "open": float(df.loc[d, "open"]),
         "high": float(df.loc[d, "high"]), "low": float(df.loc[d, "low"]),
         "close": float(df.loc[d, "close"]), "volume": float(df.loc[d, "volume"])}
        for d in df.index
    ]
    mock_db.execute = AsyncMock(side_effect=[
        _result_with_first({"id": 7, "ticker": "FPT", "model_id": 99}),
        _result_with_first({"id": 99, "status": "trained",
                            "file_path": "/tmp/solution_7_darts.joblib",
                            "config_json": json.dumps({"output_chunk_length": "5"})}),
        _result_with_mappings([]),
        MagicMock(),
    ])
    mock_db.commit = AsyncMock()

    bundle = {"engine": "darts", "model_path": "/tmp/x.model",
              "model_module": __name__, "model_class": "_StubDartsModel",
              **{k: v for k, v in _fitted().items() if k != "model"}}

    last = df.index[-1]
    forecast = {
        "engine": "darts", "model_type": "DLinear",
        "backtest": [{"date": d.strftime("%Y-%m-%d"), "actual_price": 100.0 + i,
                      "predicted_price": 100.5 + i}
                     for i, d in enumerate(df.index[-4:])],
        "future": [{"date": (last + pd.Timedelta(days=i + 1)).strftime("%Y-%m-%d"),
                    "predicted_price": 101.0 + i} for i in range(5)],
        "requested_horizon": 5, "horizon": 5, "warnings": [],
    }

    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"data": price_records}

    with patch("app.api.solution_routes.os.path.exists", return_value=True), \
         patch("app.api.solution_routes.joblib.load", return_value=bundle), \
         patch("app.api.solution_routes.load_darts_model",
               return_value=_StubDartsModel()), \
         patch("app.services.darts_trainer.run_darts_forecast",
               return_value=forecast) as forecasted, \
         patch("app.api.solution_routes.httpx.AsyncClient",
               return_value=_FakeAsyncClient(resp)):
        r = await client.post(f"{PREFIX}/predict", json={
            "id": 7,
            "start_date": df.index[-4].strftime("%Y-%m-%d"),
            "end_date": last.strftime("%Y-%m-%d"),
        })

    assert r.status_code == 200, r.text
    body = r.json()
    assert forecasted.called, "the darts forecaster was never reached"
    assert body["engine"] == "darts", "the payload must name the engine (#109)"
    assert len(body["future"]) == 5
    assert len(body["actual"]) == len(body["predict"]) == 4
    assert body["future_days"] == 5
    # The chart carries a predicted value only where the backtest produced one,
    # rather than drawing an in-sample fit across the whole context as a forecast.
    with_pred = [p for p in body["chart"] if p.get("predicted_price") is not None]
    assert len(with_pred) == 4, len(with_pred)
    assert body["chart"], "the Prediction tab draws its context from this"


@pytest.mark.asyncio
async def test_a_bundle_with_no_engine_key_is_still_treated_as_tabular(
        client: AsyncClient, mock_db):
    """Every bundle written before #126 is a tabular one and has no engine key,
    so the absence must mean 'tabular' and not 'unknown'. Without this, the fix
    would break every solution trained before it."""
    df = _ohlcv_frame(200)
    price_records = [
        {"time": d.strftime("%Y-%m-%d"), "open": float(df.loc[d, "open"]),
         "high": float(df.loc[d, "high"]), "low": float(df.loc[d, "low"]),
         "close": float(df.loc[d, "close"]), "volume": float(df.loc[d, "volume"])}
        for d in df.index
    ]
    mock_db.execute = AsyncMock(side_effect=[
        _result_with_first({"id": 7, "ticker": "FPT", "model_id": 99}),
        _result_with_first({"id": 99, "status": "trained", "file_path": "/tmp/m.joblib",
                            "config_json": "{}"}),
        _result_with_mappings([]),
        MagicMock(),
    ])
    mock_db.commit = AsyncMock()
    fake_model = MagicMock()
    fake_model.predict = lambda X: X[:, 0] * 1.01
    saved = {"model": fake_model, "feature_cols": ["close", "returns"]}

    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"data": price_records}

    with patch("app.api.solution_routes.os.path.exists", return_value=True), \
         patch("app.api.solution_routes.joblib.load", return_value=saved), \
         patch("app.api.solution_routes.load_darts_model") as darts_loader, \
         patch("app.api.solution_routes.httpx.AsyncClient",
               return_value=_FakeAsyncClient(resp)):
        r = await client.post(f"{PREFIX}/predict", json={
            "id": 7,
            "start_date": df.index[150].strftime("%Y-%m-%d"),
            "end_date": df.index[-1].strftime("%Y-%m-%d"),
        })

    assert r.status_code == 200, r.text
    assert not darts_loader.called, "a legacy tabular bundle took the darts branch"
    assert r.json().get("engine") is None


@pytest.mark.asyncio
async def test_a_model_that_cannot_be_saved_fails_the_run_instead_of_being_trained(
        monkeypatch):
    """THE STATE #126 IS ABOUT MUST NOT BE REACHABLE BY A SECOND ROUTE. A
    solution marked 'trained' whose model is not on disk is exactly what made
    predict impossible, so a save failure fails the run — it is not logged and
    swallowed."""
    import app.services.darts_trainer as trainer

    frame = pd.DataFrame(
        {"close": np.linspace(10, 20, 60), "rsi_14": np.linspace(40, 60, 60)},
        index=pd.bdate_range("2025-01-01", periods=60))
    fake_result = {
        "metrics": {"rmse": 1.0, "mae": 0.8, "r2": 0.5, "direction_accuracy": 55.0},
        "naive": {"rmse": 1.2, "r2": 0.4}, "beats_naive_rmse": True,
        "covariates": {"past": ["rsi_14"], "future": []},
        "data_accounting": {"rows_used": 60, "training_samples": 48,
                            "validation_samples": 12},
        "predictions": [], "forecast_warnings": [],
        "fitted": _fitted(),
    }
    monkeypatch.setattr(trainer, "run_darts_training", lambda *a, **k: fake_result)
    monkeypatch.setattr(solution_routes, "save_darts_bundle",
                        lambda *a, **k: (_ for _ in ()).throw(OSError("disk full")))

    db = AsyncMock()
    db.execute = AsyncMock()
    db.commit = AsyncMock()
    solution_routes.training_status[4242] = {"status": "training", "progress": 0}

    await solution_routes._run_darts_engine(
        solution_id=4242, db=db, feature_df=frame,
        indicator_rows=[{"covariate_type": "past", "name": "RSI"}],
        model_instance={"model_type": "DLinear", "config_json": "{}"},
        model_id=99, ticker="FPT",
        train_params={"train_ratio": 0.8}, start_date="2025-01-01",
        end_date="2025-03-24", rows_before_warmup=60, rows_after_warmup=60)

    status = solution_routes.training_status[4242]
    assert status["status"] == "failed", status
    assert "could not be saved" in status["error"]
    assert not db.execute.called, "nothing may be marked trained after a failed save"
    solution_routes.training_status.pop(4242, None)


# ---------------------------------------------------------------------------
# compute_prediction_dates — one copy for both engines (#126/#127)
# ---------------------------------------------------------------------------


def test_the_prediction_window_starts_the_business_day_after_training():
    dates = solution_routes.compute_prediction_dates("2026-02-06", 1)   # a Friday
    assert dates["prediction_start_date"] == "2026-02-09"
    assert dates["prediction_end_date"] == "2026-02-09"


def test_the_prediction_window_is_as_long_as_the_horizon():
    dates = solution_routes.compute_prediction_dates("2026-02-02", 5)
    assert dates["prediction_start_date"] == "2026-02-03"
    assert dates["prediction_end_date"] == "2026-02-09"     # skips the weekend
    assert dates["output_chunk_length"] == 5


def test_the_prediction_window_reports_the_training_end_it_was_given():
    dates = solution_routes.compute_prediction_dates("2026-02-02", 3)
    assert dates["training_end_date"] == "2026-02-02"


@pytest.mark.asyncio
async def test_a_successful_darts_run_writes_file_path_and_the_predict_window(
        monkeypatch, tmp_path):
    """THE TWO THINGS #126 WAS. file_path stayed NULL, so predict could never
    load a model; and the result carried no prediction_dates, so the Predict
    tab had no window to offer after a training that reported success."""
    import app.services.darts_trainer as trainer

    frame = pd.DataFrame(
        {"close": np.linspace(10, 20, 60), "rsi_14": np.linspace(40, 60, 60)},
        index=pd.bdate_range("2025-01-01", periods=60))
    fake_result = {
        "metrics": {"rmse": 1.0, "mae": 0.8, "r2": 0.5, "direction_accuracy": 55.0},
        "naive": {"rmse": 1.2, "r2": 0.4}, "beats_naive_rmse": True,
        "covariates": {"past": ["rsi_14"], "future": []},
        "data_accounting": {"rows_used": 60, "training_samples": 48,
                            "validation_samples": 12},
        "predictions": [], "forecast_warnings": [],
        "fitted": _fitted(),
    }
    monkeypatch.setattr(trainer, "run_darts_training", lambda *a, **k: fake_result)
    monkeypatch.setattr(solution_routes.settings, "MODEL_PATH", str(tmp_path))

    statements, params = [], []

    async def _execute(stmt, args=None):
        statements.append(str(stmt))
        params.append(args or {})
        return MagicMock()

    db = AsyncMock()
    db.execute = _execute
    db.commit = AsyncMock()
    solution_routes.training_status[4343] = {"status": "training", "progress": 0}

    await solution_routes._run_darts_engine(
        solution_id=4343, db=db, feature_df=frame,
        indicator_rows=[{"covariate_type": "past", "name": "RSI"}],
        model_instance={"model_type": "DLinear",
                        "config_json": json.dumps({"output_chunk_length": "5"})},
        model_id=99, ticker="FPT",
        train_params={"train_ratio": 0.8}, start_date="2025-01-01",
        end_date="2025-03-21", rows_before_warmup=60, rows_after_warmup=60)

    status = solution_routes.training_status.pop(4343)
    assert status["status"] == "completed", status

    model_update = [p for s, p in zip(statements, params) if "file_path" in s]
    assert model_update, "model_instances was updated without file_path — #126"
    written = model_update[0]["file_path"]
    assert written.endswith("solution_4343_darts.joblib")
    import os as _os
    assert _os.path.exists(written), "file_path names a file that is not there"

    dates = status["result"]["prediction_dates"]
    assert dates["output_chunk_length"] == 5, (
        "the window must be the MODEL's horizon, not a literal")
    assert dates["prediction_start_date"] == "2025-03-24"      # the 21st is a Friday
    assert dates["training_end_date"] == "2025-03-21"


@pytest.mark.asyncio
async def test_the_tabular_training_result_also_offers_the_models_own_window(
        monkeypatch, tmp_path):
    """A GAP FOUND BY MUTATION TESTING, not by reading. Removing
    prediction_dates from the TABULAR result left the whole suite green: the
    darts side had a guard and this side had none, so the block the Predict tab
    pre-fills from was protected on one engine only. Both now, and the horizon
    is asserted against the model's config rather than against a literal."""
    sid = 9100
    solution_routes.training_status.pop(sid, None)

    rows = 200
    idx = pd.bdate_range("2025-01-01", periods=rows)
    close = np.linspace(20, 30, rows)
    price_records = [
        {"time": d.strftime("%Y-%m-%d"), "open": float(c), "high": float(c) + 1,
         "low": float(c) - 1, "close": float(c), "volume": 1000.0 + i}
        for i, (d, c) in enumerate(zip(idx, close))
    ]

    session = AsyncMock()
    session.execute = AsyncMock(side_effect=[
        _result_with_first({"id": sid, "ticker": "FPT", "model_id": 99}),
        _result_with_first({"id": 99, "model_type": "XGBoost", "model_sub_type": "",
                            "config_json": json.dumps({"output_chunk_length": "3"})}),
        _result_with_mappings([]),            # no indicators
        MagicMock(), MagicMock(), MagicMock(),
    ])
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    monkeypatch.setattr("app.api.solution_routes.async_session_factory",
                        MagicMock(return_value=session))
    # MODEL_PATH is the container's /app volume; unwritable from a test host.
    monkeypatch.setattr(solution_routes.settings, "MODEL_PATH", str(tmp_path))

    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"data": price_records}

    end_date = idx[-1].strftime("%Y-%m-%d")
    with patch("app.api.solution_routes.httpx.AsyncClient",
               return_value=_FakeAsyncClient(resp)):
        await _run_training(sid, {"start_date": idx[0].strftime("%Y-%m-%d"),
                                  "end_date": end_date,
                                  "engine": "tabular", "train_ratio": 0.8,
                                  "validation": True,
                                  # Explicit: left to the default this reaches
                                  # news-service over real HTTP and the test
                                  # hangs on it rather than failing.
                                  "include_news": False})

    status = solution_routes.training_status.pop(sid)
    assert status["status"] == "completed", status
    dates = status["result"]["prediction_dates"]
    assert dates["output_chunk_length"] == 3, (
        "the tabular path hardcoded 10 here before #127")
    assert dates["training_end_date"] == end_date
    assert pd.Timestamp(dates["prediction_start_date"]) > pd.Timestamp(end_date)
    assert pd.Timestamp(dates["prediction_start_date"]).weekday() < 5


def test_deleting_a_darts_bundle_takes_its_model_files_with_it(tmp_path):
    """A LEAK #126 CREATED, found by looking at the volume after a sweep rather
    than by reading the code: DELETE /models/{id} removes file_path — the
    joblib sidecar — and the Darts model file plus the torch .ckpt beside it
    survived. Fourteen orphans in one afternoon, each a model nothing can reach
    and nothing will ever delete."""
    with patch.object(solution_routes.settings, "MODEL_PATH", str(tmp_path)):
        sidecar = solution_routes.save_darts_bundle(77, _fitted())
    model_file = str(tmp_path / "solution_77_darts.model")
    # The .ckpt is torch's, written by Darts itself; the stub does not make one.
    open(model_file + ".ckpt", "w").close()

    companions = solution_routes.darts_companion_files(sidecar)
    assert sorted(companions) == sorted([model_file, model_file + ".ckpt"])


def test_a_tabular_bundle_has_no_darts_companions(tmp_path):
    """Non-vacuity: the cleanup must not start deleting files next to a plain
    tabular joblib because their names happen to look similar."""
    sidecar = tmp_path / "solution_78_model.joblib"
    __import__("joblib").dump({"model": "x", "feature_cols": ["close"]}, sidecar)
    assert solution_routes.darts_companion_files(str(sidecar)) == []


def test_an_unreadable_sidecar_still_gives_up_its_model_by_convention(tmp_path):
    """A corrupt sidecar must not mean an abandoned model file."""
    sidecar = tmp_path / "solution_79_darts.joblib"
    sidecar.write_bytes(b"not a joblib at all")
    model_file = tmp_path / "solution_79_darts.model"
    model_file.write_text("the model")
    assert solution_routes.darts_companion_files(str(sidecar)) == [str(model_file)]


# ---------------------------------------------------------------------------
# Backlog #131 — forecast dates come from the real session calendar
# ---------------------------------------------------------------------------
#
# THE CASE THIS IS BUILT ON IS REAL, not invented: FPT has no session from
# 2024-04-29 to 2024-05-01 (Reunification Day and Labour Day back to back) and
# resumes on 05-02. A solution trained to 04-29 and asked to predict 04-30
# returned a forecast dated 04-29 — before the window requested, and on a
# closed exchange. Found by tests/predict_roundtrip.py, seed 42, randomforest.

#: The gap, as the exchange actually had it.
_TET_GAP = [pd.Timestamp("2024-04-29"), pd.Timestamp("2024-04-30"),
            pd.Timestamp("2024-05-01")]


def _sessions_around_the_holiday():
    """Weekday dates with the Reunification/Labour closure actually missing."""
    days = pd.bdate_range("2024-03-01", "2024-06-28")
    return pd.DatetimeIndex([d for d in days if d not in _TET_GAP])


def test_a_forecast_is_never_dated_before_the_window_it_was_asked_for():
    """The defect itself. 2024-04-26 is the last bar and the caller asked from
    2024-04-30, so a date of 04-29 is a day that had already happened."""
    cal = _sessions_around_the_holiday()
    dates, _ = solution_routes.forecast_session_dates(
        cal, 3, anchor=pd.Timestamp("2024-04-26"),
        not_before=pd.Timestamp("2024-04-30"))
    assert min(dates) >= pd.Timestamp("2024-04-30")


def test_a_forecast_lands_on_real_sessions_across_a_market_holiday():
    """And the dates are the sessions the exchange actually held: 05-02 next,
    not 04-29 and not 05-01. Nothing but the price series knows this — there is
    no exchange calendar in the system to consult."""
    cal = _sessions_around_the_holiday()
    dates, estimated = solution_routes.forecast_session_dates(
        cal, 3, anchor=pd.Timestamp("2024-04-26"),
        not_before=pd.Timestamp("2024-04-30"))
    assert [str(d.date()) for d in dates] == ["2024-05-02", "2024-05-03", "2024-05-06"]
    assert estimated == 0, "these are known sessions, not guesses"
    assert not any(d in _TET_GAP for d in dates)


def test_without_a_requested_start_the_forecast_simply_follows_the_last_bar():
    """Non-vacuity for not_before: it must not shift dates when it is absent."""
    cal = _sessions_around_the_holiday()
    dates, estimated = solution_routes.forecast_session_dates(
        cal, 2, anchor=pd.Timestamp("2024-04-26"))
    assert [str(d.date()) for d in dates] == ["2024-05-02", "2024-05-03"]
    assert estimated == 0


def test_dates_past_the_known_calendar_are_counted_as_estimates():
    """Past the fetched series nothing knows the sessions, so a weekday step is
    the best available — and the COUNT of such dates is reported rather than
    the payload implying the whole series is known."""
    cal = _sessions_around_the_holiday()
    dates, estimated = solution_routes.forecast_session_dates(
        cal, 4, anchor=cal[-1])          # anchored at the very end
    assert len(dates) == 4
    assert estimated == 4
    assert all(d > cal[-1] for d in dates)


def test_a_partly_known_horizon_counts_only_the_guessed_dates():
    """The boundary case: some real sessions left, then extrapolation."""
    cal = _sessions_around_the_holiday()
    dates, estimated = solution_routes.forecast_session_dates(
        cal, 3, anchor=cal[-2])          # one known session remains
    assert len(dates) == 3
    assert estimated == 2


@pytest.mark.parametrize("count", [1, 5, 30])
def test_a_forecast_never_lands_on_a_weekend_and_is_always_full_length(count):
    cal = _sessions_around_the_holiday()
    dates, _ = solution_routes.forecast_session_dates(
        cal, count, anchor=cal[-1])
    assert len(dates) == count
    assert all(d.weekday() < 5 for d in dates)
    assert len(set(dates)) == count


def _holiday_price_records():
    """OHLCV over the real session calendar, including the tail past the window."""
    cal = _sessions_around_the_holiday()
    close = np.linspace(90, 110, len(cal))
    return cal, [
        {"time": d.strftime("%Y-%m-%d"), "open": float(c), "high": float(c) + 1,
         "low": float(c) - 1, "close": float(c), "volume": 1000.0 + i}
        for i, (d, c) in enumerate(zip(cal, close))
    ]


async def _predict_over_the_holiday(client, mock_db, **body):
    cal, records = _holiday_price_records()
    mock_db.execute = AsyncMock(side_effect=[
        _result_with_first({"id": 7, "ticker": "FPT", "model_id": 99}),
        _result_with_first({"id": 99, "status": "trained", "file_path": "/tmp/m.joblib",
                            "config_json": json.dumps({"output_chunk_length": "3"})}),
        _result_with_mappings([]),
        MagicMock(),
    ])
    mock_db.commit = AsyncMock()
    fake_model = MagicMock()
    fake_model.predict = lambda X: X[:, 0] * 1.01
    saved = {"model": fake_model, "feature_cols": ["close", "returns"]}
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"data": records}
    fake_client = _FakeAsyncClient(resp)

    with patch("app.api.solution_routes.os.path.exists", return_value=True), \
         patch("app.api.solution_routes.joblib.load", return_value=saved), \
         patch("app.api.solution_routes.httpx.AsyncClient", return_value=fake_client):
        r = await client.post(f"{PREFIX}/predict", json={"id": 7, **body})
    return r, fake_client, cal


@pytest.mark.asyncio
async def test_the_tabular_forecast_skips_the_closure_and_respects_the_window(
        client: AsyncClient, mock_db):
    """#131 through the route: the exact request that produced a forecast dated
    2024-04-29 for a window starting 2024-04-30."""
    r, _, _ = await _predict_over_the_holiday(
        client, mock_db, start_date="2024-04-30", end_date="2024-04-30")

    assert r.status_code == 200, r.text
    body = r.json()
    future = [pd.Timestamp(p["tradingdate"]) for p in body["future"]]
    assert future, "a forecast was still expected — the window being shut does " \
                   "not mean there is nothing ahead to forecast"
    assert min(future) >= pd.Timestamp("2024-04-30"), future
    assert not any(d in _TET_GAP for d in future), future
    assert str(min(future).date()) == "2024-05-02"
    assert body["forecast_dates_estimated"] == 0


@pytest.mark.asyncio
async def test_the_calendar_tail_never_reaches_the_model_frame(
        client: AsyncClient, mock_db):
    """THE LEAK TEST FOR #131's FIX. Bars past the prediction window are fetched
    on purpose — they are the only way to learn which days the exchange held —
    and they must never be fed to the model. If they were, the backtest would be
    scored against features built from the future of its own window, which is
    the look-ahead this service is built to avoid."""
    window_end = "2024-04-18"
    r, fake_client, _ = await _predict_over_the_holiday(
        client, mock_db, start_date="2024-04-10", end_date=window_end)

    assert r.status_code == 200, r.text
    body = r.json()

    # It really did ask for more than the window, or the fix does nothing.
    asked_to = pd.Timestamp(fake_client.last_params["end_date"])
    assert asked_to > pd.Timestamp(window_end), fake_client.last_params

    # And nothing the model saw post-dates the window.
    for series in ("chart", "actual", "predict"):
        for point in body[series]:
            day = pd.Timestamp(point.get("date") or point.get("tradingdate"))
            assert day <= pd.Timestamp(window_end), (series, str(day))


def test_sessions_between_the_last_bar_and_the_requested_start_are_excluded():
    """A VACUITY MY OWN TESTS HAD, found by mutation: removing the not_before
    filter left the suite green, because in the holiday fixture there are NO
    sessions between the last bar and the requested start — the closure is the
    gap. Nothing was being excluded, so the rule that excludes was untested.

    This is the shape that actually exercises it, and the one that matters most:
    a window starting several sessions after the last available bar. Without the
    filter the forecast would be labelled 2024-04-23 and presented as the answer
    to a request for 2024-04-30."""
    cal = _sessions_around_the_holiday()
    anchor = pd.Timestamp("2024-04-22")
    floor = pd.Timestamp("2024-04-30")
    skipped = [d for d in cal if anchor < d < floor]
    assert skipped, "the fixture must contain sessions to exclude, or this is vacuous again"

    dates, _ = solution_routes.forecast_session_dates(
        cal, 3, anchor=anchor, not_before=floor)
    assert all(d >= floor for d in dates), dates
    assert not any(d in skipped for d in dates), dates
    assert str(dates[0].date()) == "2024-05-02"


@pytest.mark.asyncio
async def test_a_window_opening_after_the_last_bar_is_honoured_through_the_route(
        client: AsyncClient, mock_db):
    """The same shape end to end: the data stops well before the window, and the
    forecast must still be dated inside it rather than straight after the bar."""
    cal, records = _holiday_price_records()
    cutoff = pd.Timestamp("2024-04-22")
    records = [r for r in records if pd.Timestamp(r["time"]) <= cutoff
               or pd.Timestamp(r["time"]) >= pd.Timestamp("2024-04-30")]

    mock_db.execute = AsyncMock(side_effect=[
        _result_with_first({"id": 7, "ticker": "FPT", "model_id": 99}),
        _result_with_first({"id": 99, "status": "trained", "file_path": "/tmp/m.joblib",
                            "config_json": json.dumps({"output_chunk_length": "2"})}),
        _result_with_mappings([]),
        MagicMock(),
    ])
    mock_db.commit = AsyncMock()
    fake_model = MagicMock()
    fake_model.predict = lambda X: X[:, 0] * 1.01
    saved = {"model": fake_model, "feature_cols": ["close", "returns"]}
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"data": records}

    with patch("app.api.solution_routes.os.path.exists", return_value=True), \
         patch("app.api.solution_routes.joblib.load", return_value=saved), \
         patch("app.api.solution_routes.httpx.AsyncClient",
               return_value=_FakeAsyncClient(resp)):
        r = await client.post(f"{PREFIX}/predict", json={
            "id": 7, "start_date": "2024-04-30", "end_date": "2024-05-03"})

    assert r.status_code == 200, r.text
    future = [pd.Timestamp(p["tradingdate"]) for p in r.json()["future"]]
    assert future and min(future) >= pd.Timestamp("2024-04-30"), future


# ---------------------------------------------------------------------------
# Backlog #130 — a failed indicator is excluded and reported, never faked
# ---------------------------------------------------------------------------


def _rows(*names):
    return [{"name": n, "parameters": None, "default_parameters": None}
            for n in names]


def test_a_failed_indicator_is_left_out_of_the_features():
    """Not replaced by close, not filled with zeros: absent. A zero column and
    a close column are both features the operator did not choose."""
    df = _ohlcv_frame(60)
    failures = []
    feat, _ = _prepare_indicator_features(
        df, _rows("SMA", "TOTALLY_UNKNOWN", "RSI"), failures=failures)
    assert "sma" in feat.columns and "rsi" in feat.columns
    assert not any("unknown" in c.lower() or c == "value" for c in feat.columns)


def test_a_failed_indicator_is_reported_with_its_name_and_reason():
    df = _ohlcv_frame(60)
    failures = []
    _prepare_indicator_features(df, _rows("SMA", "TOTALLY_UNKNOWN"),
                                failures=failures)
    assert len(failures) == 1
    assert failures[0]["name"] == "TOTALLY_UNKNOWN"
    assert "no implementation" in failures[0]["reason"]


def test_nothing_is_reported_when_every_indicator_computes():
    """Non-vacuity: an empty report must mean 'all present', so it cannot be
    filling up on healthy input."""
    df = _ohlcv_frame(60)
    failures = []
    feat, _ = _prepare_indicator_features(df, _rows("SMA", "RSI", "ATR", "OBV"),
                                          failures=failures)
    assert failures == []
    assert len(feat.columns) >= 4


def test_the_chart_series_also_omits_a_failed_indicator():
    """indicator_data_by_date feeds the chart. A close-price line drawn under
    the name of a failed indicator is the same lie in a second place."""
    df = _ohlcv_frame(60)
    _, by_date = _prepare_indicator_features(df, _rows("TOTALLY_UNKNOWN"))
    for values in by_date.values():
        assert "value" not in values


def test_collecting_failures_is_optional():
    """The per-step forecast loop calls this once per forecast day and has no
    use for the report; it must not be forced to pass a list."""
    df = _ohlcv_frame(60)
    feat, _ = _prepare_indicator_features(df, _rows("SMA", "TOTALLY_UNKNOWN"))
    assert "sma" in feat.columns


@pytest.mark.asyncio
async def test_training_refuses_when_no_configured_indicator_survives(monkeypatch):
    """The threshold case. A model that saw NONE of the four indicators the
    operator configured is not the model that was asked for, so this refuses
    rather than training and burying the reason in a JSON field — the same
    reasoning plan_covariates applies to an RNN with indicators attached."""
    sid = 9200
    solution_routes.training_status.pop(sid, None)

    idx = pd.bdate_range("2025-01-01", periods=200)
    close = np.linspace(20, 30, len(idx))
    records = [
        {"time": d.strftime("%Y-%m-%d"), "open": float(c), "high": float(c) + 1,
         "low": float(c) - 1, "close": float(c), "volume": 1000.0 + i}
        for i, (d, c) in enumerate(zip(idx, close))
    ]

    session = AsyncMock()
    session.execute = AsyncMock(side_effect=[
        _result_with_first({"id": sid, "ticker": "FPT", "model_id": 99}),
        _result_with_first({"id": 99, "model_type": "XGBoost", "model_sub_type": "",
                            "config_json": "{}"}),
        # Two indicators, both unimplemented — PIVOT and RENKO are real
        # catalogue entries with no branch in _calculate_indicator.
        _result_with_mappings([
            {"indicator_id": 50, "indicator_category": "trend",
             "covariate_type": "past", "parameters": None, "name": "PIVOT",
             "type": "support_resistance", "default_parameters": None,
             "calculation_function": "calculate_pivot"},
            {"indicator_id": 51, "indicator_category": "trend",
             "covariate_type": "past", "parameters": None, "name": "RENKO",
             "type": "price_transform", "default_parameters": None,
             "calculation_function": "calculate_renko"},
        ]),
    ])
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    monkeypatch.setattr("app.api.solution_routes.async_session_factory",
                        MagicMock(return_value=session))

    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"data": records}

    with patch("app.api.solution_routes.httpx.AsyncClient",
               return_value=_FakeAsyncClient(resp)):
        await _run_training(sid, {"start_date": idx[0].strftime("%Y-%m-%d"),
                                  "end_date": idx[-1].strftime("%Y-%m-%d"),
                                  "engine": "tabular", "include_news": False})

    status = solution_routes.training_status.pop(sid)
    assert status["status"] == "failed", status
    assert "none of this solution's indicators" in status["error"]
    assert "PIVOT" in status["error"] and "RENKO" in status["error"]


@pytest.mark.asyncio
async def test_training_proceeds_and_discloses_when_some_indicators_survive(
        monkeypatch, tmp_path):
    """Non-vacuity for the refusal above, and the normal shape of the
    disclosure: three of four is a result worth having, reported so the
    operator can see which one is missing."""
    sid = 9201
    solution_routes.training_status.pop(sid, None)

    idx = pd.bdate_range("2025-01-01", periods=200)
    close = np.linspace(20, 30, len(idx))
    records = [
        {"time": d.strftime("%Y-%m-%d"), "open": float(c), "high": float(c) + 1,
         "low": float(c) - 1, "close": float(c), "volume": 1000.0 + i}
        for i, (d, c) in enumerate(zip(idx, close))
    ]

    session = AsyncMock()
    session.execute = AsyncMock(side_effect=[
        _result_with_first({"id": sid, "ticker": "FPT", "model_id": 99}),
        _result_with_first({"id": 99, "model_type": "XGBoost", "model_sub_type": "",
                            "config_json": "{}"}),
        _result_with_mappings([
            {"indicator_id": 1, "indicator_category": "trend",
             "covariate_type": "past", "parameters": '{"period": 20}', "name": "SMA",
             "type": "trend", "default_parameters": '{"period": 20}',
             "calculation_function": "calculate_sma"},
            {"indicator_id": 50, "indicator_category": "trend",
             "covariate_type": "past", "parameters": None, "name": "PIVOT",
             "type": "support_resistance", "default_parameters": None,
             "calculation_function": "calculate_pivot"},
        ]),
        MagicMock(), MagicMock(), MagicMock(),
    ])
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    monkeypatch.setattr("app.api.solution_routes.async_session_factory",
                        MagicMock(return_value=session))
    monkeypatch.setattr(solution_routes.settings, "MODEL_PATH", str(tmp_path))

    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"data": records}

    with patch("app.api.solution_routes.httpx.AsyncClient",
               return_value=_FakeAsyncClient(resp)):
        await _run_training(sid, {"start_date": idx[0].strftime("%Y-%m-%d"),
                                  "end_date": idx[-1].strftime("%Y-%m-%d"),
                                  "engine": "tabular", "include_news": False})

    status = solution_routes.training_status.pop(sid)
    assert status["status"] == "completed", status
    reported = status["result"]["indicator_failures"]
    assert [f["name"] for f in reported] == ["PIVOT"]
    assert "no implementation" in reported[0]["reason"]


@pytest.mark.asyncio
async def test_an_unavailable_indicator_does_not_blank_the_whole_chart_response(
        client: AsyncClient, mock_db):
    """Backlog #130. calculate_solution_indicators called _calculate_indicator
    unguarded, which was safe only while that function could not fail — it
    answered everything, including indicators it has no implementation for,
    with the close price. Now that it raises, the failure must be reported for
    ITS category while the others still come back: one unavailable indicator
    turning the whole chart into a 500 would be a worse bug than the one fixed.

    Asserted through the endpoint rather than by reading its source, so it
    survives the code being rearranged."""
    idx = pd.bdate_range("2026-01-01", periods=60)
    close = np.linspace(50, 60, len(idx))
    records = [
        {"time": d.strftime("%Y-%m-%d"), "open": float(c), "high": float(c) + 1,
         "low": float(c) - 1, "close": float(c), "volume": 1000.0}
        for d, c in zip(idx, close)
    ]
    rows = [
        {"indicator_id": 1, "indicator_category": "trend", "covariate_type": "past",
         "parameters": '{"period": 5}', "name": "SMA", "type": "trend",
         "default_parameters": '{"period": 5}', "calculation_function": None},
        {"indicator_id": 50, "indicator_category": "volume", "covariate_type": "past",
         "parameters": None, "name": "PIVOT", "type": "support_resistance",
         "default_parameters": None, "calculation_function": None},
    ]
    mock_db.execute = AsyncMock(return_value=_result_with_mappings(rows))
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"data": records}

    with patch("app.api.solution_routes.httpx.AsyncClient",
               return_value=_FakeAsyncClient(resp)):
        r = await client.post(
            f"{PREFIX}/7/indicators/calculate",
            json={"symbol": "FPT", "start_date": "2026-01-01", "end_date": "2026-04-01"})

    assert r.status_code == 200, r.text
    body = r.json()
    assert body["trend"]["data"], "the indicator that works must still be returned"
    assert "error" not in body["trend"]
    assert body["volume"]["data"] == []
    assert "no implementation" in body["volume"]["error"]
    # And emphatically NOT a close-price series dressed as PIVOT.
    assert not any("value" in point for point in body["volume"]["data"])


# ---------------------------------------------------------------------------
# Backlog #132 — the catalogue offers only what it can compute
# ---------------------------------------------------------------------------


def test_the_unavailable_list_is_exactly_what_cannot_be_computed():
    """THE GUARD THAT KEEPS THE LIST HONEST, and the reason it is a set in code
    rather than a flag in the database: it is checked against the code that
    makes it obsolete.

    Implement one of the thirteen and forget to remove it here — the catalogue
    goes on hiding a working indicator. Add a catalogue entry with no
    implementation and forget to add it — the GUI offers a control that fails
    after the operator has configured and trained a solution. Both are a
    failure of this test rather than a discovery months later."""
    df = _ohlcv_frame(120)
    catalogue = sorted(set(solution_routes.INDICATOR_NAME_MAP) |
                       set(solution_routes.UNAVAILABLE_INDICATORS))

    cannot = set()
    for name in catalogue:
        code = solution_routes.INDICATOR_NAME_MAP.get(name, name)
        try:
            _calculate_indicator(df, code, {})
        except solution_routes.IndicatorError:
            cannot.add(name.strip().upper())

    assert cannot == set(solution_routes.UNAVAILABLE_INDICATORS), (
        f"listed but computable: "
        f"{sorted(set(solution_routes.UNAVAILABLE_INDICATORS) - cannot)}; "
        f"uncomputable but not listed: {sorted(cannot - set(solution_routes.UNAVAILABLE_INDICATORS))}")


def test_the_thirteen_are_all_of_three_whole_groups():
    """They are not scattered picks: support_resistance, price_transform and
    bill_williams are unimplemented in their entirety, which is why hiding them
    removes three dropdowns rather than leaving gap-toothed ones."""
    assert len(solution_routes.UNAVAILABLE_INDICATORS) == 13


@pytest.mark.parametrize("name", ["SMA", "RSI", "ATR", "OBV", "AROON"])
def test_a_working_indicator_is_still_offered(name):
    """Non-vacuity: the filter must not be hiding anything that works — AROON
    included, which it would have been entitled to before #130 fixed it."""
    assert solution_routes.indicator_is_available(name)


@pytest.mark.parametrize("name", ["PIVOT", "RENKO", "GATOR"])
def test_an_unimplemented_indicator_is_not_offered(name):
    assert not solution_routes.indicator_is_available(name)


def test_availability_ignores_case_and_padding():
    """The name arrives from a database column and from request bodies."""
    assert not solution_routes.indicator_is_available(" pivot ")
    assert solution_routes.indicator_is_available(None) is True, (
        "a missing name must not be treated as unavailable — that would hide "
        "rows for a reason unrelated to #132")


@pytest.mark.asyncio
async def test_an_unimplemented_indicator_cannot_be_attached_to_a_solution(
        client: AsyncClient, mock_db):
    """Refused at the write boundary. The listing no longer offers these, so a
    request carrying one came from a stale page or straight from the API —
    either way the moment to say so is while the operator is choosing."""
    mock_db.execute = AsyncMock(return_value=_result_with_mappings(
        [{"id": 50, "name": "PIVOT"}]))
    r = await client.post(
        f"{PREFIX}/7/indicators/set",
        json={"trend_indicator": {"id": 50, "covariate_type": "past",
                                  "parameters": {}}})
    assert r.status_code == 422, r.text
    assert "PIVOT" in r.json()["detail"]
    assert "no implementation" in r.json()["detail"]


@pytest.mark.asyncio
async def test_a_working_indicator_can_still_be_attached(client: AsyncClient, mock_db):
    """Non-vacuity for the guard above: the ordinary path must still work."""
    mock_db.execute = AsyncMock(side_effect=[
        _result_with_mappings([{"id": 1, "name": "SMA"}]),   # availability check
        MagicMock(),                                        # DELETE
        MagicMock(),                                        # INSERT
    ])
    mock_db.commit = AsyncMock()
    r = await client.post(
        f"{PREFIX}/7/indicators/set",
        json={"trend_indicator": {"id": 1, "covariate_type": "past",
                                  "parameters": {"period": 20}}})
    assert r.status_code == 200, r.text
    assert r.json()["solution_id"] == 7
