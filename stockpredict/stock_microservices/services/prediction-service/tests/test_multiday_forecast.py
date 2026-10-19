"""Backlog #52 — the multi-day forecast must actually vary by day.

The bug: `predict()` built `last_row` once, before the loop, and then called
``ml_model.predict(last_row)`` with that identical row for every one of the N
days. Only the *date* differed, so the 5-day table on screen showed **one
number five times**.

The fix is the recursive (iterated) forecast, which is the right shape here
because the model is trained one step ahead — `_prepare_features` sets
``target = close.shift(-1)``. Each day's predicted close is appended to the
working series, the features are recomputed from it, and the next day is
predicted from those. Every feature the model reads is derived from `close`
except two volume ones, so almost all of them genuinely update.

Two assumptions are forced by that and are asserted here rather than left
implicit:

* **Volume is carried forward.** We cannot know a future day's volume, so the
  synthetic bar repeats the last real one. `volume_ratio` therefore drifts
  towards 1 over the horizon, which is the honest consequence.
* **Uncertainty grows with the horizon.** A recursive forecast feeds its own
  output back in, so day 5's error compounds day 1's. The interval widens with
  the square root of the horizon and confidence decays. Before this change the
  5-day band was exactly as tight as the 1-day band, which was a second and
  separately misleading defect on the same screen.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import numpy as np
import pandas as pd
import pytest

from app.models.schemas import ModelType
from app.services.prediction_service import PredictionService


def _ohlcv_df(n: int = 220, start: float = 100.0) -> pd.DataFrame:
    """A deterministic rising series with enough bars for sma_50."""
    rng = np.random.default_rng(11)
    closes = []
    price = start
    for _ in range(n):
        price *= float(np.exp(rng.normal(0.0008, 0.012)))
        closes.append(price)
    dates = [datetime(2023, 1, 1) + timedelta(days=i) for i in range(n)]
    return pd.DataFrame({
        "date": dates,
        "open": closes,
        "high": [c * 1.01 for c in closes],
        "low": [c * 0.99 for c in closes],
        "close": closes,
        "volume": [1_000_000 + i * 10 for i in range(n)],
    })


def _service() -> PredictionService:
    svc = PredictionService.__new__(PredictionService)
    svc.repo = MagicMock()
    svc.repo.save_prediction = AsyncMock()
    return svc


def _wire(svc, monkeypatch, predict_fn, current_price: float = 150.0):
    model_row = MagicMock(
        id=1, file_path="/tmp/fake.joblib", model_type=MagicMock(value="xgboost"),
        accuracy=85.0, feature_columns=None,
    )
    svc.repo.get_active_model = AsyncMock(return_value=model_row)
    monkeypatch.setattr(svc, "_fetch_historical_data", AsyncMock(return_value=_ohlcv_df()))
    monkeypatch.setattr(svc, "_get_current_price", AsyncMock(return_value=current_price))
    fake = MagicMock()
    fake.predict = predict_fn
    monkeypatch.setattr("app.services.prediction_service.joblib.load", lambda _: fake)
    return svc


#: A model that returns the most recent close plus a fixed step. Under the old
#: code every day saw the same features and so returned the same number; under
#: a recursive forecast each day sees the previous prediction and so steps up.
def _close_plus_one(X):
    return np.array([float(X["close_lag_1"].iloc[0]) + 1.0])


# ---------------------------------------------------------------------------
# The bug itself
# ---------------------------------------------------------------------------

class TestForecastVariesByDay:

    @pytest.mark.asyncio
    async def test_five_days_are_not_five_copies_of_one_number(self, monkeypatch):
        """The reported symptom, asserted directly."""
        svc = _wire(_service(), monkeypatch, _close_plus_one)
        res = await svc.predict("FPT", days=5, model_type=ModelType.XGBOOST)

        assert res is not None
        prices = [p.predicted_price for p in res.predictions]
        assert len(prices) == 5
        assert len(set(prices)) == 5, f"all five days returned {prices}"

    @pytest.mark.asyncio
    async def test_each_day_is_fed_the_previous_days_prediction(self, monkeypatch):
        """The mechanism, asserted on the model's own input.

        `close_lag_1` is the close one bar *before* the last, so on step k+2
        the model must be looking at the prediction made on step k — which is
        only possible if that prediction was appended to the series. Reading
        the feature directly is stronger than inferring it from the output
        sequence, and it does not depend on how the lag happens to line up.
        """
        seen = []

        def record(X):
            seen.append(float(X["close_lag_1"].iloc[0]))
            return np.array([float(X["close_lag_1"].iloc[0]) + 1.0])

        svc = _wire(_service(), monkeypatch, record)
        res = await svc.predict("FPT", days=4)

        preds = [p.predicted_price for p in res.predictions]
        # step 3 sees step 1's prediction, step 4 sees step 2's
        assert seen[2] == pytest.approx(preds[0], abs=0.01)
        assert seen[3] == pytest.approx(preds[1], abs=0.01)

    @pytest.mark.asyncio
    async def test_the_features_the_model_sees_change_every_day(self, monkeypatch):
        """Not just the prediction — the input. Recorded per call so a future
        refactor that re-freezes the row fails here."""
        seen = []

        def record(X):
            seen.append(X.iloc[0].to_dict())
            return np.array([float(X["close_lag_1"].iloc[0]) + 1.0])

        svc = _wire(_service(), monkeypatch, record)
        await svc.predict("FPT", days=3)

        assert len(seen) == 3
        for key in ("close_lag_1", "sma_5", "returns"):
            values = [row[key] for row in seen]
            assert len(set(values)) == 3, f"{key} was identical across days: {values}"

    @pytest.mark.asyncio
    async def test_one_day_still_works(self, monkeypatch):
        svc = _wire(_service(), monkeypatch, _close_plus_one)
        res = await svc.predict("FPT", days=1)
        assert len(res.predictions) == 1


# ---------------------------------------------------------------------------
# Uncertainty must grow with the horizon
# ---------------------------------------------------------------------------

class TestUncertaintyWidens:

    @pytest.mark.asyncio
    async def test_the_interval_widens_with_the_horizon(self, monkeypatch):
        """A recursive forecast feeds its own output back in, so day 5's error
        compounds day 1's. The band used to be identical for every day."""
        svc = _wire(_service(), monkeypatch, _close_plus_one)
        res = await svc.predict("FPT", days=5)

        widths = [
            (p.price_high - p.price_low) / p.predicted_price
            for p in res.predictions
        ]
        assert widths == sorted(widths), widths
        assert widths[-1] > widths[0] * 1.5

    @pytest.mark.asyncio
    async def test_confidence_decays_with_the_horizon(self, monkeypatch):
        svc = _wire(_service(), monkeypatch, _close_plus_one)
        res = await svc.predict("FPT", days=5)

        confidences = [p.confidence for p in res.predictions]
        assert confidences == sorted(confidences, reverse=True), confidences
        assert all(0.0 < c <= 0.95 for c in confidences)

    @pytest.mark.asyncio
    async def test_the_band_always_brackets_the_prediction(self, monkeypatch):
        svc = _wire(_service(), monkeypatch, _close_plus_one)
        res = await svc.predict("FPT", days=5)
        for p in res.predictions:
            assert p.price_low < p.predicted_price < p.price_high


# ---------------------------------------------------------------------------
# The assumptions the roll-forward forces
# ---------------------------------------------------------------------------

class TestRollForwardAssumptions:

    @pytest.mark.asyncio
    async def test_volume_is_carried_forward_not_invented(self, monkeypatch):
        """We cannot know a future day's volume. The synthetic bar repeats the
        last real one, so `volume_ratio` drifts towards 1 over the horizon —
        the honest consequence, asserted so it is not mistaken for a signal."""
        seen = []

        def record(X):
            seen.append(X.iloc[0].to_dict())
            return np.array([float(X["close_lag_1"].iloc[0]) + 1.0])

        svc = _wire(_service(), monkeypatch, record)
        await svc.predict("FPT", days=6)

        ratios = [row["volume_ratio"] for row in seen if "volume_ratio" in row]
        if len(ratios) >= 2:
            assert abs(ratios[-1] - 1.0) <= abs(ratios[0] - 1.0) + 1e-9

    @pytest.mark.asyncio
    async def test_the_synthetic_bar_survives_the_feature_dropna(self, monkeypatch):
        """`_prepare_features` ends in a row-wise `dropna()`. A synthetic bar
        with a NaN in any raw column would be silently discarded and the
        forecast would quietly stop advancing — so open/high/low are filled."""
        svc = _wire(_service(), monkeypatch, _close_plus_one)
        res = await svc.predict("FPT", days=5)
        assert len({p.predicted_price for p in res.predictions}) == 5

    @pytest.mark.asyncio
    async def test_every_day_is_persisted(self, monkeypatch):
        svc = _service()
        _wire(svc, monkeypatch, _close_plus_one)
        await svc.predict("FPT", days=4)
        assert svc.repo.save_prediction.await_count == 4

    @pytest.mark.asyncio
    async def test_change_is_measured_against_today_for_every_day(self, monkeypatch):
        """All horizons are quoted against the current price, so the column
        reads as a forecast path rather than day-on-day deltas."""
        svc = _wire(_service(), monkeypatch, _close_plus_one, current_price=120.0)
        res = await svc.predict("FPT", days=3)
        for p in res.predictions:
            expected = (p.predicted_price - 120.0) / 120.0 * 100.0
            assert p.predicted_change == pytest.approx(expected, abs=0.01)
