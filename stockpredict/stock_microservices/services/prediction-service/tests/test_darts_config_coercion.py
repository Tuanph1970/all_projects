"""Backlog #124 — hyperparameters arrive as strings, because that is what the UI stores.

`model_instances.config_json` holds every value as a STRING. The live
user-created BlockRNN row on this install reads
`{"batch_size": "16", "learning_rate": "0.0001", "n_epochs": "300", ...}`, so
this is the normal shape of the data rather than something a test invented.

`build_model` always coerced the chunk lengths and n_epochs. Nothing coerced the
regression hyperparameters, and `_build_regression` forwarded them verbatim into
constructors that type-check. Measured by tests/model_sweep.py on 2026-11-04:

  * RandomForest never constructed at all;
  * CatBoost raised CatBoostError on a string and completed on a float;
  * XGBoost did NOT raise — it trained and returned a constant 119-day forecast
    with healthy-looking metrics.

The last one is why this is a correctness bug and not a robustness nicety: a
crash gets noticed, a flat forecast gets believed.
"""
from __future__ import annotations

import pytest

from app.services.darts_trainer import (
    DartsTrainingError,
    _REGRESSION_ACCEPTS,
    _REGRESSION_PARAM_TYPES,
    REGRESSION_MODELS,
    coerce_regression_params,
)

#: What the UI actually writes.
UI_CONFIG = {
    "n_estimators": "200", "max_depth": "6", "learning_rate": "0.001",
    "batch_size": "16", "n_epochs": "300", "dropout": "0",
}


# ---------------------------------------------------------------------------
# Coercion
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("model", sorted(REGRESSION_MODELS))
def test_string_hyperparameters_become_numbers(model):
    kwargs, _ = coerce_regression_params(model, UI_CONFIG)
    assert kwargs, f"{model} forwarded nothing"
    for key, value in kwargs.items():
        assert isinstance(value, _REGRESSION_PARAM_TYPES[key]), (
            f"{model}: {key}={value!r} is {type(value).__name__}, "
            f"expected {_REGRESSION_PARAM_TYPES[key].__name__}")
    assert not any(isinstance(v, str) for v in kwargs.values())


def test_an_int_parameter_written_as_a_decimal_survives():
    """A UI that writes "6.0" for max_depth should not break training;
    int("6.0") raises, so the cast goes through float first."""
    kwargs, _ = coerce_regression_params("XGBoost", {"max_depth": "6.0"})
    assert kwargs["max_depth"] == 6
    assert isinstance(kwargs["max_depth"], int)


def test_numbers_already_numeric_are_left_alone():
    kwargs, _ = coerce_regression_params(
        "XGBoost", {"n_estimators": 200, "learning_rate": 0.05})
    assert kwargs == {"n_estimators": 200, "learning_rate": 0.05}


@pytest.mark.parametrize("blank", ["", None])
def test_a_blank_value_is_skipped_not_coerced_to_zero(blank):
    """An empty form field must leave the library default in place. float("")
    raises and int(None) raises, but worse would be silently coercing to 0 —
    n_estimators=0 trains nothing and learning_rate=0 learns nothing."""
    kwargs, _ = coerce_regression_params("XGBoost", {"n_estimators": blank})
    assert "n_estimators" not in kwargs


# ---------------------------------------------------------------------------
# Filtering: a parameter the architecture cannot take
# ---------------------------------------------------------------------------

def test_random_forest_does_not_receive_a_learning_rate():
    """RandomForestRegressor has no learning_rate at ANY type — there is no
    boosting step to scale. Forwarding it was a TypeError, which is why
    RandomForest/darts could never be trained."""
    kwargs, notes = coerce_regression_params("RandomForest", UI_CONFIG)
    assert "learning_rate" not in kwargs
    assert kwargs["n_estimators"] == 200 and kwargs["max_depth"] == 6
    assert any("learning_rate" in n for n in notes), notes


def test_dropping_an_unusable_parameter_is_reported_not_silent():
    """The user asked for something; they are told it was ignored. Silently
    discarding configuration is how someone concludes a setting does nothing."""
    _, notes = coerce_regression_params("RandomForest", {"learning_rate": "0.1"})
    assert notes and "RandomForest" in notes[0]


@pytest.mark.parametrize("model", sorted(REGRESSION_MODELS))
def test_boosters_do_receive_a_learning_rate(model):
    """Non-vacuity for the filter: it must drop only what cannot be used."""
    kwargs, _ = coerce_regression_params(model, UI_CONFIG)
    if model == "RandomForest":
        pytest.skip("covered by its own test; it has no learning_rate")
    assert kwargs["learning_rate"] == pytest.approx(0.001)


# ---------------------------------------------------------------------------
# A value that cannot be a number must RAISE, not be absorbed
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("bad", ["abc", "1,5", "0.1.2", "fast"])
def test_an_unparseable_value_raises_rather_than_training_without_it(bad):
    """THE DISTINCTION THAT MATTERS. Dropping an unusable parameter is kind;
    dropping an unREADABLE one is dangerous, because the run then reports
    numbers from a model the user did not configure — which is exactly how
    XGBoost's constant forecast looked like a successful training."""
    with pytest.raises(DartsTrainingError) as e:
        coerce_regression_params("XGBoost", {"learning_rate": bad})
    assert "learning_rate" in str(e.value)
    assert "not a float" in str(e.value)


def test_the_error_says_what_to_do_about_it():
    with pytest.raises(DartsTrainingError) as e:
        coerce_regression_params("XGBoost", {"n_estimators": "lots"})
    msg = str(e.value)
    assert "not a int" in msg or "not an int" in msg
    assert "remove it" in msg


# ---------------------------------------------------------------------------
# The accept table is checked by CONSTRUCTING, not by trusting
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("model", sorted(REGRESSION_MODELS))
def test_every_regression_model_builds_with_every_param_it_claims_to_accept(model):
    """The table is hand-written because the Darts wrappers pass **kwargs down,
    so a signature proves nothing. This proves it the only way that counts: by
    building the model with the full declared set and seeing it not raise.

    If a future Darts release drops a parameter, this fails here rather than in
    a user's training run.
    """
    # darts ships in the service image, not on a developer host. Skipping where
    # it is absent keeps the rest of this file runnable anywhere; the test still
    # runs in CI and in the container, which is where it has to.
    pytest.importorskip("darts", reason="darts is installed in the service image")
    from darts.models import CatBoostModel, LightGBMModel, RandomForest, XGBModel
    builders = {"XGBoost": XGBModel, "LightGBM": LightGBMModel,
                "RandomForest": RandomForest, "CatBoost": CatBoostModel}
    kwargs, _ = coerce_regression_params(model, UI_CONFIG)
    base = {"lags": 14, "output_chunk_length": 5}
    if model == "LightGBM":
        base["verbose"] = -1
    builders[model](**base, **kwargs)        # must not raise


def test_every_regression_model_has_an_accept_entry():
    """A model missing from the table would silently receive NO hyperparameters
    — trained on library defaults while the UI showed the user's settings."""
    assert set(_REGRESSION_ACCEPTS) == set(REGRESSION_MODELS)


def test_no_accept_entry_names_a_parameter_we_cannot_type():
    assert all(p in _REGRESSION_PARAM_TYPES
               for params in _REGRESSION_ACCEPTS.values() for p in params)


# ---------------------------------------------------------------------------
# A constant forecast is not a forecast (#124, the #109 condition generalised)
# ---------------------------------------------------------------------------

from app.services.darts_trainer import forecast_warnings  # noqa: E402


def test_a_constant_forecast_is_reported():
    """#109 fixed one CAUSE of flatness; nothing detected the CONDITION.

    Measured 2026-11-04: XGBoost with learning_rate=0.001 and the default ~100
    boosting rounds returns a perfectly constant series alongside an rmse, an r2
    and a direction accuracy that all look ordinary. The maths is correct — an
    undertrained booster predicts the mean — but a reader cannot see it in the
    numbers, so the result has to say it.
    """
    warns = forecast_warnings([90.892] * 119)
    assert len(warns) == 1
    assert "no information" in warns[0]
    assert "90.892" in warns[0]


def test_a_forecast_that_moves_is_not_warned_about():
    """Non-vacuity: the guard must distinguish, not decorate every result."""
    assert forecast_warnings([10.0, 10.2, 10.1, 10.4]) == []


def test_a_barely_moving_forecast_is_not_called_constant():
    """Only EXACT constancy is reported. A quiet but real forecast is a tuning
    observation, and warning about it would train the reader to ignore the
    warning that matters."""
    assert forecast_warnings([10.0, 10.000001, 10.0, 10.000002]) == []


@pytest.mark.parametrize("series", [[], [1.0], None])
def test_too_short_to_judge_is_silent(series):
    assert forecast_warnings(series) == []


def test_nulls_do_not_create_a_false_constant():
    """A series of one real value and some Nones must not read as flat."""
    assert forecast_warnings([None, 10.0, None]) == []


def test_the_warning_names_a_likely_cause_rather_than_just_the_symptom():
    """"It is flat" sends the reader nowhere. The cause is almost always
    undertraining, and saying which knob differs per family."""
    w = forecast_warnings([5.0] * 10)[0]
    assert "learning_rate" in w and "epochs" in w


def test_the_result_carries_the_warning_field():
    """A guard computed and not returned protects nobody."""
    import inspect
    from app.services import darts_trainer
    src = inspect.getsource(darts_trainer.run_darts_training)
    assert "forecast_warnings" in src
