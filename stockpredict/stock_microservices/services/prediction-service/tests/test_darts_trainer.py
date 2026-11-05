"""Backlog #109 Phase 2 — the Darts training core.

Pure functions, so these run offline with no database, no HTTP and no fitted
model. The expensive end-to-end fit is exercised separately; what matters here
is the reasoning that decides WHAT gets fed to a model, because that is where
look-ahead bias would enter.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from app.services.darts_trainer import (
    DEFAULT_WINDOWS,
    MIN_TRAINING_WINDOWS,
    CovariateError,
    DartsTrainingError,
    calendar_frame,
    chronological_split,
    evaluate,
    extend_index,
    naive_baseline,
    plan_covariates,
    resolve_windows,
)

IDX = pd.bdate_range("2024-01-01", periods=300)


# ---------------------------------------------------------------------------
# The covariate rule — where leakage would enter
# ---------------------------------------------------------------------------

def test_indicators_marked_past_become_past_covariates():
    plan = plan_covariates(
        ["rsi_14", "sma_20"], {"rsi_14": "past", "sma_20": "past"},
        model_supports_future=False)
    assert plan.past_columns == ("rsi_14", "sma_20")
    assert plan.future_columns == ()
    assert plan.uses_past and not plan.uses_future


def test_an_indicator_marked_future_is_REFUSED_not_demoted():
    """The decision this module exists to make.

    A technical indicator is a function of price, so its values over the
    forecast horizon are not knowable without the future prices. Darts would
    accept the series and the model would train on information it will not have
    live. Silently demoting it to a past covariate would also be wrong — the
    operator asked for something impossible and must be told.
    """
    with pytest.raises(CovariateError) as e:
        plan_covariates(["rsi_14"], {"rsi_14": "future"}, model_supports_future=True)
    msg = str(e.value)
    assert "rsi_14" in msg, "the refusal must name the offending indicator"
    assert "KNOWN" in msg and "function of price" in msg


def test_both_is_refused_for_the_same_reason():
    """Honouring half of 'both' silently is worse than refusing it."""
    with pytest.raises(CovariateError) as e:
        plan_covariates(["macd"], {"macd": "both"}, model_supports_future=True)
    assert "macd" in str(e.value)


def test_the_refusal_names_every_offender_not_just_the_first():
    with pytest.raises(CovariateError) as e:
        plan_covariates(
            ["a", "b", "c"], {"a": "future", "b": "past", "c": "both"},
            model_supports_future=True)
    msg = str(e.value)
    assert "a" in msg and "c" in msg


def test_an_unrecognised_covariate_type_is_an_error_not_a_default():
    with pytest.raises(CovariateError):
        plan_covariates(["x"], {"x": "sideways"}, model_supports_future=False)


def test_a_missing_covariate_type_defaults_to_past():
    """`past` is the safe default: it cannot leak."""
    plan = plan_covariates(["x"], {}, model_supports_future=True)
    assert plan.past_columns == ("x",)


def test_calendar_features_are_the_only_future_covariates_offered():
    """And only to models that can use them."""
    supported = plan_covariates(["rsi"], {"rsi": "past"}, model_supports_future=True)
    assert supported.future_columns == ("dayofweek", "month", "day")
    assert supported.calendar_features == supported.future_columns

    unsupported = plan_covariates(["rsi"], {"rsi": "past"}, model_supports_future=False)
    assert unsupported.future_columns == ()


# ---------------------------------------------------------------------------
# Calendar features really are known ahead
# ---------------------------------------------------------------------------

def test_calendar_features_are_computable_for_dates_with_no_price_data():
    """The property that makes them legitimate future covariates: they depend
    on the date alone, so next month's values exist today."""
    future = pd.bdate_range("2030-01-01", periods=10)
    frame = calendar_frame(future)
    assert len(frame) == 10
    assert not frame.isna().any().any()
    assert frame.loc[future[0], "month"] == 1.0


def test_calendar_values_match_the_index():
    frame = calendar_frame(IDX)
    assert frame["dayofweek"].iloc[0] == float(IDX[0].dayofweek)
    assert frame["month"].iloc[0] == float(IDX[0].month)
    assert set(frame["dayofweek"].unique()) <= {0.0, 1.0, 2.0, 3.0, 4.0}, (
        "business-day index should never contain a weekend")


def test_extend_index_adds_business_days_beyond_the_end():
    """Darts needs a future covariate to cover the horizon, so the calendar
    series must run PAST the target."""
    out = extend_index(IDX, 5)
    assert len(out) == len(IDX) + 5
    assert out[len(IDX)] > IDX[-1]
    assert all(d.weekday() < 5 for d in out[len(IDX):])


def test_extend_index_is_a_no_op_for_zero_or_negative():
    assert len(extend_index(IDX, 0)) == len(IDX)
    assert len(extend_index(IDX, -3)) == len(IDX)


# ---------------------------------------------------------------------------
# Windows — the per-model data offset
# ---------------------------------------------------------------------------

def test_each_model_has_a_window_default():
    from app.api.routes import MODEL_TYPE_MAP

    missing = sorted(set(MODEL_TYPE_MAP.values()) - set(DEFAULT_WINDOWS))
    assert not missing, f"no window default for: {missing}"


def test_rnn_predicts_one_step_at_a_time():
    """RNNModel is the odd one: output_chunk_length is 1 by construction."""
    assert DEFAULT_WINDOWS["RNN"][1] == 1


def test_config_overrides_the_default_window():
    w = resolve_windows("TFT", {"input_chunk_length": 45, "output_chunk_length": 7}, 600)
    assert (w.input_chunk_length, w.output_chunk_length) == (45, 7)
    assert not w.warnings


def test_a_window_too_long_for_the_data_is_shrunk_AND_reported():
    """Clamped loudly, not quietly. A model that trains on eight windows
    produces numbers that look like results."""
    w = resolve_windows("TFT", {"input_chunk_length": 200}, 120)
    assert w.input_chunk_length < 200
    assert w.warnings and "reduced" in w.warnings[0]
    assert w.total_rows - (w.input_chunk_length + w.output_chunk_length) >= MIN_TRAINING_WINDOWS


def test_too_little_data_fails_instead_of_training_on_nothing():
    with pytest.raises(DartsTrainingError) as e:
        resolve_windows("TFT", None, 20)
    assert "usable rows" in str(e.value)


@pytest.mark.parametrize("bad", [{"input_chunk_length": 0}, {"output_chunk_length": -1}])
def test_nonpositive_windows_are_rejected(bad):
    with pytest.raises(DartsTrainingError):
        resolve_windows("TFT", bad, 600)


def test_a_three_year_request_supports_the_default_window():
    """The sizing claim in the module docstring, asserted: ~700 usable bars
    leaves well over the minimum at a 30-bar lookback."""
    w = resolve_windows("BlockRNN", None, 700)
    assert w.input_chunk_length == 30 and not w.warnings
    assert 700 - (w.input_chunk_length + w.output_chunk_length) > 600


# ---------------------------------------------------------------------------
# The split is chronological
# ---------------------------------------------------------------------------

def test_the_split_is_chronological_and_reports_its_boundary():
    split, train_end, val_start = chronological_split(IDX, 0.8)
    assert split == 240
    assert train_end == IDX[239].strftime("%Y-%m-%d")
    assert val_start == IDX[240].strftime("%Y-%m-%d")
    assert pd.Timestamp(val_start) > pd.Timestamp(train_end), "validation must follow training"


@pytest.mark.parametrize("ratio", [0.0, 1.0, -0.1, 1.5])
def test_a_ratio_outside_the_open_interval_is_rejected(ratio):
    with pytest.raises(DartsTrainingError):
        chronological_split(IDX, ratio)


def test_a_ratio_that_leaves_no_TRAINING_rows_is_rejected():
    """The reachable failure, corrected after checking the arithmetic: because
    `int()` floors, `split` is always < n for ratio < 1, so "no validation
    rows" cannot occur. What can occur is too few rows for the ratio to leave
    even one training row — int(2 * 0.4) == 0.
    """
    with pytest.raises(DartsTrainingError):
        chronological_split(IDX[:2], 0.4)


def test_a_high_ratio_on_a_short_series_still_leaves_one_validation_row():
    """The converse of the above: 0.999 on four rows is legal, not an error."""
    split, train_end, val_start = chronological_split(IDX[:4], 0.999)
    assert split == 3
    assert pd.Timestamp(val_start) > pd.Timestamp(train_end)


# ---------------------------------------------------------------------------
# Metrics, and the benchmark C4 requires
# ---------------------------------------------------------------------------

def test_perfect_predictions_score_perfectly():
    m = evaluate([1.0, 2.0, 3.0, 4.0], [1.0, 2.0, 3.0, 4.0])
    assert m["rmse"] == 0.0 and m["mae"] == 0.0
    assert m["r2"] == pytest.approx(1.0)
    assert m["direction_accuracy"] == pytest.approx(100.0)


def test_rmse_and_mae_are_the_textbook_quantities():
    m = evaluate([1.0, 2.0], [2.0, 4.0])      # errors +1, +2
    assert m["mae"] == pytest.approx(1.5)
    assert m["rmse"] == pytest.approx(math.sqrt((1 + 4) / 2))


def test_direction_is_measured_against_the_previous_ACTUAL():
    """Not against the previous prediction — that would score the model's own
    smoothness rather than whether it called the move.

    Both calls here are correct relative to the PRECEDING ACTUAL: actual goes
    10 -> 11 (up) and the prediction 10.5 is above 10; then 11 -> 10.5 (down)
    and the prediction 10.8 is below 11. So 100%. Note the first prediction
    (0.0) is never scored — there is no preceding actual for it.
    """
    m = evaluate([10.0, 11.0, 10.5], [0.0, 10.5, 10.8])
    assert m["direction_accuracy"] == pytest.approx(100.0)


def test_one_wrong_directional_call_scores_fifty_percent():
    """The counterpart, so the test above cannot pass by always returning 100.

    actual 10 -> 11 (up) but the prediction 9.5 is BELOW 10, so that call is
    wrong; 11 -> 10.5 (down) and 10.8 is below 11, so that one is right.
    """
    m = evaluate([10.0, 11.0, 10.5], [0.0, 9.5, 10.8])
    assert m["direction_accuracy"] == pytest.approx(50.0)


def test_direction_ignores_the_models_own_smoothness():
    """If direction were computed from consecutive PREDICTIONS, a monotonically
    rising forecast would score 100% against a falling actual. It must not."""
    m = evaluate([10.0, 9.0, 8.0], [0.0, 10.5, 11.0])   # predictions rise, actual falls
    assert m["direction_accuracy"] == pytest.approx(0.0)


def test_flat_actuals_do_not_count_as_a_directional_call():
    m = evaluate([5.0, 5.0, 5.0], [5.0, 6.0, 4.0])
    assert math.isnan(m["direction_accuracy"])


def test_a_constant_actual_series_has_no_r2():
    m = evaluate([3.0, 3.0, 3.0], [3.0, 3.1, 2.9])
    assert math.isnan(m["r2"])


def test_mismatched_lengths_are_refused():
    with pytest.raises(DartsTrainingError):
        evaluate([1.0, 2.0], [1.0])
    with pytest.raises(DartsTrainingError):
        evaluate([], [])


def test_the_naive_baseline_carries_the_last_known_value_forward():
    """C4's mandatory benchmark. On price LEVELS this scores near-perfectly,
    which is exactly why a model's R² is unreadable without it beside."""
    actual = [10.0, 10.2, 10.1, 10.4]
    base = naive_baseline(actual, last_train_value=9.9)
    # carried = [9.9, 10.0, 10.2, 10.1]
    assert base["mae"] == pytest.approx(np.mean([0.1, 0.2, 0.1, 0.3]))


def test_the_naive_baseline_is_strong_on_a_random_walk():
    """Demonstrates the trap on synthetic data rather than asserting it: a
    near-random-walk level series gives the naive predictor a high R²."""
    rng = np.random.default_rng(0)
    level = 20 + np.cumsum(rng.normal(0, 0.2, 300))
    base = naive_baseline(level[1:], last_train_value=level[0])
    assert base["r2"] > 0.9, base["r2"]


# ---------------------------------------------------------------------------
# Model construction (Phase 2b)
# ---------------------------------------------------------------------------
#
# `darts` is installed in the prediction-service IMAGE, not on a developer
# host, so these skip rather than fail outside the container. They are the
# tests that actually matter for Phase 2b and are run inside the image.

TORCH_TYPES = ["BlockRNN", "RNN", "TCN", "Transformer", "TFT",
               "NBeats", "NHits", "DLinear", "NLinear", "TiDE"]
REGRESSION_TYPES = ["XGBoost", "LightGBM", "RandomForest"]


def _window(icl=12, ocl=3):
    from app.services.darts_trainer import TrainingWindow
    return TrainingWindow(total_rows=300, train_rows=240, validation_rows=60,
                          input_chunk_length=icl, output_chunk_length=ocl)


def _past_only_plan():
    from app.services.darts_trainer import CovariatePlan
    return CovariatePlan(past_columns=("rsi_14",))


@pytest.mark.parametrize("model_type", TORCH_TYPES + REGRESSION_TYPES)
def test_every_model_type_constructs(model_type):
    pytest.importorskip("darts")
    from app.services.darts_trainer import build_model

    model = build_model(model_type, _window(), _past_only_plan(), None)
    assert model is not None


def test_rnn_is_built_without_an_output_chunk_length():
    """RNNModel does not accept it — passing one is a TypeError from inside the
    library, which is exactly the kind of error this module exists to prevent
    reaching the operator."""
    pytest.importorskip("darts")
    from darts.models import RNNModel

    from app.services.darts_trainer import build_model

    model = build_model("RNN", _window(), _past_only_plan(), None)
    assert isinstance(model, RNNModel)


def test_tft_is_built_so_it_can_fit_without_future_covariates():
    """TFT needs future input. Since indicators cannot be future covariates,
    the common case here has none, so `add_relative_index` must be set or fit
    raises."""
    pytest.importorskip("darts")
    from app.services.darts_trainer import build_model

    model = build_model("TFT", _window(), _past_only_plan(), None)
    assert model is not None


def test_regression_capability_follows_the_PLAN_not_the_class():
    """The Phase 1 finding, enforced: XGBModel only supports past covariates if
    `lags_past_covariates` was supplied at construction, so the operator's
    choice has to reach the constructor."""
    pytest.importorskip("darts")
    from app.services.darts_trainer import CovariatePlan, build_model

    with_past = build_model("XGBoost", _window(), CovariatePlan(past_columns=("rsi",)), None)
    assert with_past.supports_past_covariates

    without = build_model("XGBoost", _window(), CovariatePlan(), None)
    assert not without.supports_past_covariates, (
        "a model built from an empty plan must not claim covariate support — "
        "fit() would then demand a series that does not exist")


def test_a_future_plan_grants_future_capability():
    pytest.importorskip("darts")
    from app.services.darts_trainer import CovariatePlan, build_model

    plan = CovariatePlan(past_columns=("rsi",), future_columns=("dayofweek",))
    model = build_model("XGBoost", _window(), plan, None)
    assert model.supports_past_covariates and model.supports_future_covariates


def test_torch_models_are_pinned_to_cpu():
    """The image ships CPU-only torch on purpose. A model claiming GPU and
    silently falling back would be worse than an explicit setting."""
    pytest.importorskip("darts")
    from app.services.darts_trainer import CPU_TRAINER_KWARGS, build_model

    assert CPU_TRAINER_KWARGS["accelerator"] == "cpu"
    model = build_model("BlockRNN", _window(), _past_only_plan(), None)
    assert model.trainer_params.get("accelerator") == "cpu"


def test_config_overrides_epochs_and_seed():
    pytest.importorskip("darts")
    from app.services.darts_trainer import build_model

    model = build_model("BlockRNN", _window(), _past_only_plan(),
                        {"n_epochs": 3, "random_state": 7})
    assert model.n_epochs == 3


def test_an_unknown_model_type_is_refused_readably():
    pytest.importorskip("darts")
    from app.services.darts_trainer import DartsTrainingError, build_model

    with pytest.raises(DartsTrainingError) as e:
        build_model("Nonsense", _window(), _past_only_plan(), None)
    assert "Nonsense" in str(e.value)


def test_catboost_is_installed_and_constructs():
    """The catalogue advertises CatBoost, the UI seeds its parameter fields, so
    it has to be buildable. This test previously tolerated BOTH states
    ("constructs, or raises a readable error") because the package was absent;
    `catboost` is now a declared requirement, so tolerating the absence would
    let a dropped dependency pass silently.

    Worth pinning because darts hides the failure: `from darts.models import
    CatBoostModel` SUCCEEDS without the package — the class is a stub that
    raises ImportError at CONSTRUCTION. An import probe therefore reports a
    complete catalogue while this entry cannot be built.
    """
    pytest.importorskip("darts")
    from app.services.darts_trainer import build_model

    model = build_model("CatBoost", _window(), _past_only_plan(), None)
    assert model is not None
    assert type(model).__name__ == "CatBoostModel"


def test_every_catalogue_regression_type_can_be_built():
    """No entry may be advertised and unbuildable — the gap CatBoost was in."""
    pytest.importorskip("darts")
    from app.services.darts_trainer import REGRESSION_MODELS, build_model

    for model_type in sorted(REGRESSION_MODELS):
        assert build_model(model_type, _window(), _past_only_plan(), None) is not None


@pytest.mark.parametrize("model_type",
                         ["BlockRNN", "TCN", "Transformer"] + REGRESSION_TYPES)
def test_built_models_actually_fit_with_past_covariates(model_type):
    """Construction is not usefulness — the Phase 1 lesson. These fit for real
    on a short synthetic series with a past covariate attached."""
    pytest.importorskip("darts")
    import logging

    from darts import TimeSeries

    from app.services.darts_trainer import build_model

    logging.getLogger("pytorch_lightning").setLevel(logging.ERROR)
    idx = pd.bdate_range("2024-01-01", periods=160)
    rng = np.random.default_rng(1)
    target = TimeSeries.from_series(
        pd.Series(np.linspace(10, 14, 160) + rng.normal(0, .1, 160), index=idx))
    past = TimeSeries.from_series(pd.Series(rng.normal(0, 1, 160), index=idx), )

    model = build_model(model_type, _window(), _past_only_plan(), {"n_epochs": 1})
    model.fit(target, past_covariates=past)
    out = model.predict(3, past_covariates=past)
    assert len(out) == 3


def test_rnn_fits_with_FUTURE_covariates_only():
    """RNNModel takes future covariates and not past ones — found by fitting,
    after a test that wrongly handed it a past covariate failed. The calendar
    series is the legitimate future covariate here, and it must extend beyond
    the target for Darts to accept it."""
    pytest.importorskip("darts")
    import logging

    from darts import TimeSeries

    from app.services.darts_trainer import build_model, calendar_frame, extend_index

    logging.getLogger("pytorch_lightning").setLevel(logging.ERROR)
    idx = pd.bdate_range("2024-01-01", periods=160)
    rng = np.random.default_rng(2)
    target = TimeSeries.from_series(
        pd.Series(np.linspace(10, 14, 160) + rng.normal(0, .1, 160), index=idx))
    cal = TimeSeries.from_dataframe(calendar_frame(extend_index(idx, 10)))

    from app.services.darts_trainer import CovariatePlan
    model = build_model("RNN", _window(), CovariatePlan(future_columns=("dayofweek",)),
                        {"n_epochs": 1})
    model.fit(target, future_covariates=cal)
    assert len(model.predict(3, future_covariates=cal)) == 3


def test_a_past_only_plan_is_refused_for_a_future_only_model():
    """Silently ignoring four configured indicators would be the same class of
    quiet behaviour as the rest of this week's findings."""
    from app.services.darts_trainer import CovariateError, plan_covariates

    with pytest.raises(CovariateError) as e:
        plan_covariates(["rsi_14", "sma_20"], {"rsi_14": "past", "sma_20": "past"},
                        model_supports_future=True, model_supports_past=False)
    msg = str(e.value)
    assert "rsi_14" in msg and "ignored entirely" in msg


# ---------------------------------------------------------------------------
# End-to-end orchestration (Phase 2b)
# ---------------------------------------------------------------------------

def _frame(n=320, seed=3):
    """A price-like level series plus two indicator columns."""
    idx = pd.bdate_range("2023-01-02", periods=n)
    rng = np.random.default_rng(seed)
    close = 20 + np.cumsum(rng.normal(0, 0.15, n))
    return pd.DataFrame(
        {"close": close,
         "rsi_14": 50 + rng.normal(0, 8, n),
         "sma_20": pd.Series(close, index=idx).rolling(20, min_periods=1).mean().to_numpy()},
        index=idx)


@pytest.mark.parametrize("model_type", ["BlockRNN", "XGBoost", "DLinear"])
def test_run_darts_training_produces_auditable_output(model_type):
    pytest.importorskip("darts")
    import logging
    logging.getLogger("pytorch_lightning").setLevel(logging.ERROR)
    from app.services.darts_trainer import run_darts_training

    out = run_darts_training(
        _frame(), model_type=model_type,
        indicator_columns=["rsi_14", "sma_20"],
        covariate_types={"rsi_14": "past", "sma_20": "past"},
        train_ratio=0.85, config={"n_epochs": 1, "input_chunk_length": 20,
                                  "output_chunk_length": 5})
    assert out["engine"] == "darts" and out["model_type"] == model_type
    acc = out["data_accounting"]
    assert acc["training_samples"] + acc["validation_samples"] == acc["rows_used"]
    assert pd.Timestamp(acc["validation_start_date"]) > pd.Timestamp(acc["train_end_date"])
    # every returned row is held-out, and recomputable
    assert out["predictions"] and all(p["in_sample"] is False for p in out["predictions"])
    recomputed = math.sqrt(sum((p["predicted_price"] - p["actual_price"]) ** 2
                               for p in out["predictions"]) / len(out["predictions"]))
    assert recomputed == pytest.approx(out["metrics"]["rmse"], rel=1e-6), (
        "the reported rmse must be reproducible from the returned rows — the #110 lesson")


def test_the_naive_benchmark_travels_with_the_metrics():
    """C4: a reader must not be able to see r2 without seeing what
    'tomorrow = today' scores on the same slice."""
    pytest.importorskip("darts")
    from app.services.darts_trainer import run_darts_training

    out = run_darts_training(
        _frame(), model_type="XGBoost",
        indicator_columns=["rsi_14"], covariate_types={"rsi_14": "past"},
        train_ratio=0.85, config={"input_chunk_length": 20, "output_chunk_length": 5})
    assert set(out["naive"]) == set(out["metrics"])
    assert isinstance(out["beats_naive_rmse"], bool)


def test_indicators_reach_the_model_as_past_covariates():
    pytest.importorskip("darts")
    from app.services.darts_trainer import run_darts_training

    out = run_darts_training(
        _frame(), model_type="XGBoost",
        indicator_columns=["rsi_14", "sma_20"],
        covariate_types={"rsi_14": "past", "sma_20": "past"},
        train_ratio=0.85, config={"input_chunk_length": 20, "output_chunk_length": 5})
    assert out["covariates"]["past"] == ["rsi_14", "sma_20"]


def test_a_future_marked_indicator_fails_the_whole_run():
    """Not a warning buried in a log — the run stops and names the problem."""
    pytest.importorskip("darts")
    from app.services.darts_trainer import CovariateError, run_darts_training

    with pytest.raises(CovariateError) as e:
        run_darts_training(
            _frame(), model_type="XGBoost",
            indicator_columns=["rsi_14"], covariate_types={"rsi_14": "future"},
            train_ratio=0.85)
    assert "rsi_14" in str(e.value)


def test_a_frame_without_the_price_column_is_refused():
    from app.services.darts_trainer import DartsTrainingError, run_darts_training

    with pytest.raises(DartsTrainingError):
        run_darts_training(_frame().drop(columns=["close"]), model_type="XGBoost",
                           indicator_columns=[], covariate_types={})


def test_a_missing_indicator_column_is_refused_before_fitting():
    from app.services.darts_trainer import DartsTrainingError, run_darts_training

    with pytest.raises(DartsTrainingError) as e:
        run_darts_training(_frame(), model_type="XGBoost",
                           indicator_columns=["not_computed"], covariate_types={})
    assert "not_computed" in str(e.value)


def test_a_validation_span_shorter_than_the_output_window_is_refused():
    pytest.importorskip("darts")
    from app.services.darts_trainer import DartsTrainingError, run_darts_training

    with pytest.raises(DartsTrainingError) as e:
        run_darts_training(_frame(n=200), model_type="XGBoost",
                           indicator_columns=[], covariate_types={},
                           train_ratio=0.99,
                           config={"input_chunk_length": 20, "output_chunk_length": 10})
    assert "validation rows" in str(e.value)


def _irregular_frame(n=320, seed=4):
    """A frame with HOLIDAY GAPS, like real trading data.

    The test that was missing. Every earlier fixture used `pd.bdate_range`,
    which carries a clean `B` frequency, so none of them could reproduce the
    failure real ACB data produced:
        ValueError: The time index is missing the `freq` attribute...
    Vietnamese market holidays (Tet and others) remove whole runs of business
    days, so no frequency can be inferred from the index.
    """
    idx = pd.bdate_range("2023-01-02", periods=n + 20)
    drop = set(idx[40:48]) | set(idx[150:153]) | {idx[200]}   # holiday runs
    idx = pd.DatetimeIndex([d for d in idx if d not in drop])[:n]
    assert idx.freq is None, "fixture must have no inferable frequency"
    rng = np.random.default_rng(seed)
    close = 20 + np.cumsum(rng.normal(0, 0.15, n))
    return pd.DataFrame(
        {"close": close,
         "rsi_14": 50 + rng.normal(0, 8, n),
         "sma_20": pd.Series(close).rolling(20, min_periods=1).mean().to_numpy()},
        index=idx)


def test_the_fixture_really_has_no_inferable_frequency():
    """Guards the guard — if pandas ever infers a freq here, the test below
    stops exercising the bug it was written for."""
    assert _irregular_frame().index.freq is None
    assert pd.infer_freq(_irregular_frame().index) is None


@pytest.mark.parametrize("model_type", ["BlockRNN", "XGBoost"])
def test_training_survives_market_holiday_gaps(model_type):
    """The real-data failure, reproduced and fixed.

    Darts needs a regular frequency; trading bars have none. The series are
    therefore indexed by BAR NUMBER, which is also what the models mean — an
    input_chunk_length of 30 is thirty trading bars.
    """
    pytest.importorskip("darts")
    import logging
    logging.getLogger("pytorch_lightning").setLevel(logging.ERROR)
    from app.services.darts_trainer import run_darts_training

    out = run_darts_training(
        _irregular_frame(), model_type=model_type,
        indicator_columns=["rsi_14", "sma_20"],
        covariate_types={"rsi_14": "past", "sma_20": "past"},
        train_ratio=0.85,
        config={"n_epochs": 1, "input_chunk_length": 20, "output_chunk_length": 5})
    assert out["predictions"]
    assert out["metrics"]["rmse"] >= 0


# A real XGBoost fit over the full fixture, which takes ~38s on an idle machine
# against pytest.ini's 30s global limit — so it passed only when nothing else was
# running and failed under load on UNMODIFIED code (verified by stashing, 2026-11-02).
# A latent CI flake rather than a logic risk, and GitHub runners are slower than
# this box. Given room instead of being marked `slow`, because it guards the #110
# date-alignment fix and is worth running on every CI pass.
@pytest.mark.timeout(180)
def test_output_rows_still_carry_real_dates_despite_positional_indexing():
    """The index is positional; the REPORT must still be dated, or a reader
    cannot line predictions up against anything."""
    pytest.importorskip("darts")
    from app.services.darts_trainer import run_darts_training

    frame = _irregular_frame()
    out = run_darts_training(
        frame, model_type="XGBoost",
        indicator_columns=["rsi_14"], covariate_types={"rsi_14": "past"},
        train_ratio=0.85, config={"input_chunk_length": 20, "output_chunk_length": 5})
    dates = [p["date"] for p in out["predictions"]]
    assert dates == sorted(dates)
    assert pd.Timestamp(dates[0]) in frame.index


# ===========================================================================
# Scaling (Backlog #109 Phase 2b, added after the first real run)
# ===========================================================================
# The first real BlockRNN run returned forecasts with sd 0.18 around a flat
# 19.44 against actuals of sd 0.79 — a near-constant. Unscaled inputs (price
# ~20, RSI 0-100, volume ~1e6) saturate a network's first layer. These tests
# cover the fix and, more importantly, the leak the fix could easily introduce.


def _ramp(n=100, lo=10.0, hi=30.0):
    from darts import TimeSeries
    return TimeSeries.from_values(np.linspace(lo, hi, n))


def test_scaling_round_trips_back_to_original_units():
    """inverse_transform(transform(x)) == x, or the payload lies about prices."""
    pytest.importorskip("darts")
    from app.services.darts_trainer import scale_for_training
    s = _ramp()
    scaled, scaler = scale_for_training(s, split=70)
    back = scaler.inverse_transform(scaled).values().ravel()
    assert np.allclose(back, s.values().ravel())


def test_scaler_maps_the_training_span_into_unit_range():
    pytest.importorskip("darts")
    from app.services.darts_trainer import scale_for_training
    scaled, _ = scale_for_training(_ramp(), split=70)
    train = scaled.values().ravel()[:70]
    assert train.min() == pytest.approx(0.0, abs=1e-9)
    assert train.max() == pytest.approx(1.0, abs=1e-9)


def test_scaler_is_fitted_on_training_span_only():
    """C1. Fitting on the full series would leak the validation span's range
    into training — the preprocessing leak that makes metrics look better.

    Proved by mutation rather than by reading the code: move the validation
    tail far away and the TRAINING values must not budge. If the scaler were
    fitted on everything, every training value would change.
    """
    pytest.importorskip("darts")
    from app.services.darts_trainer import scale_for_training
    from darts import TimeSeries

    base = np.linspace(10.0, 30.0, 100)
    moved = base.copy()
    moved[70:] = moved[70:] * 100.0          # validation tail, wildly different

    a, _ = scale_for_training(TimeSeries.from_values(base), split=70)
    b, _ = scale_for_training(TimeSeries.from_values(moved), split=70)

    assert np.allclose(a.values().ravel()[:70], b.values().ravel()[:70])
    # And the moved tail must land outside the unit range, which is the
    # positive evidence that it was transformed by a train-only scaler.
    assert b.values().ravel()[70:].max() > 1.0


def test_scaling_a_none_series_yields_none():
    """Models without covariates pass None through, so this is on the hot path."""
    pytest.importorskip("darts")
    from app.services.darts_trainer import scale_for_training
    scaled, scaler = scale_for_training(None, split=10)
    assert scaled is None and scaler is None


def test_scaled_fit_tracks_a_series_a_constant_cannot():
    """The defect's signature was a near-constant forecast. On a clean
    deterministic signal a working pipeline must beat the best constant.

    Asserting a PROPERTY (beats the mean predictor), not an rmse value — per
    CLAUDE.md, magnitudes from a simulator are not expected values.

    NOT a ramp, which was this test's first draft and failed at rmse 5.07 vs
    1.74. That failure was correct: a gradient-boosted tree predicts a
    piecewise constant and CANNOT extrapolate above the largest target it
    trained on, so a monotone series whose validation span leaves the training
    range is the one shape it must lose on. A bounded oscillation keeps the
    validation values inside the training range, so the test measures the
    pipeline rather than a known limit of the model family.
    """
    pytest.importorskip("darts")
    from app.services.darts_trainer import run_darts_training

    n = 400
    idx = pd.bdate_range("2024-01-01", periods=n)
    close = 25.0 + 5.0 * np.sin(2.0 * np.pi * np.arange(n) / 20.0)
    frame = pd.DataFrame({"close": close}, index=idx)
    out = run_darts_training(
        frame,
        model_type="LightGBM",
        indicator_columns=[],
        covariate_types={},
        train_ratio=0.8,
        price_column="close",
    )
    actual = np.array([p["actual_price"] for p in out["predictions"]])
    predicted = np.array([p["predicted_price"] for p in out["predictions"]])
    const_rmse = float(np.sqrt(np.mean((actual - actual.mean()) ** 2)))
    model_rmse = float(np.sqrt(np.mean((actual - predicted) ** 2)))
    assert model_rmse < const_rmse


# ---------------------------------------------------------------------------
# Backlog #116 — a covariate that is constant in the training span but not in
# validation is not merely weak, it is HARMFUL, and must be refused.
#
# Measured on POW with #106's news covariates: the news corpus began after the
# 80/20 boundary, so news_intensity was zero in all 545 training bars and peaked
# at 50.0 in validation. The scaler is fitted on [:split] only (correctly, C1),
# so it sees a zero-RANGE column; sklearn's MinMax leaves such a column
# unscaled, and a validation value of 50 then arrives among features scaled into
# [0,1] and saturates layer one. rmse 0.4323 -> 0.9601, r2 +0.605 -> -0.948.
#
# Same class of guard as MIN_TRAINING_WINDOWS: refuse rather than return numbers
# that look like results. Not news-specific — any sparse covariate can do this.
# ---------------------------------------------------------------------------

def _frame_with(col_values, n=100):
    idx = pd.bdate_range("2024-01-01", periods=n)
    return pd.DataFrame({"close": np.linspace(10, 20, n), "feat": col_values}, index=idx)


def test_a_column_constant_in_training_and_varying_in_validation_is_refused():
    from app.services.darts_trainer import constant_in_train_only
    vals = [0.0] * 80 + list(np.linspace(1, 50, 20))
    assert constant_in_train_only(_frame_with(vals), ["feat"], 80) == ["feat"]


def test_a_column_constant_in_training_and_constant_elsewhere_is_still_refused():
    """The variance test alone misses this: validation is constant too, just at
    a different value. Training still never sees 50, so it still saturates."""
    from app.services.darts_trainer import constant_in_train_only
    vals = [0.0] * 80 + [50.0] * 20
    assert constant_in_train_only(_frame_with(vals), ["feat"], 80) == ["feat"]


def test_a_column_that_varies_in_training_is_fine():
    from app.services.darts_trainer import constant_in_train_only
    vals = list(np.linspace(0, 5, 80)) + list(np.linspace(5, 50, 20))
    assert constant_in_train_only(_frame_with(vals), ["feat"], 80) == []


def test_a_column_constant_everywhere_at_one_value_is_not_an_offender():
    """Dead weight, not a trap: the scaler leaves it alone and it degrades
    nothing. Refusing here would block a training run for no benefit."""
    from app.services.darts_trainer import constant_in_train_only
    assert constant_in_train_only(_frame_with([0.0] * 100), ["feat"], 80) == []


def test_a_sparse_but_present_training_signal_is_fine():
    """A feature that fires rarely in training is weak, not harmful — the model
    has at least seen its range."""
    from app.services.darts_trainer import constant_in_train_only
    vals = [0.0] * 78 + [30.0, 12.0] + [0.0] * 10 + [50.0] * 10
    assert constant_in_train_only(_frame_with(vals), ["feat"], 80) == []


def test_only_the_named_columns_are_checked():
    from app.services.darts_trainer import constant_in_train_only
    f = _frame_with([0.0] * 80 + [9.0] * 20)
    assert constant_in_train_only(f, [], 80) == []
    assert constant_in_train_only(f, ["missing_column"], 80) == []


def test_every_offender_is_named_not_just_the_first():
    from app.services.darts_trainer import constant_in_train_only
    idx = pd.bdate_range("2024-01-01", periods=100)
    f = pd.DataFrame({
        "close": np.linspace(10, 20, 100),
        "a": [0.0] * 80 + [5.0] * 20,
        "ok": np.linspace(1, 2, 100),
        "b": [0.0] * 80 + [7.0] * 20,
    }, index=idx)
    assert constant_in_train_only(f, ["a", "ok", "b"], 80) == ["a", "b"]


def test_training_refuses_a_train_constant_covariate_and_says_what_to_do():
    pytest.importorskip("darts")
    from app.services.darts_trainer import DartsTrainingError, run_darts_training
    n = 400
    idx = pd.bdate_range("2024-01-01", periods=n)
    close = 25.0 + 5.0 * np.sin(2.0 * np.pi * np.arange(n) / 20.0)
    # Mirrors the POW shape: the feature only ever fires after the split.
    news = np.zeros(n)
    news[int(n * 0.8) + 5:] = 50.0
    frame = pd.DataFrame({"close": close, "news_intensity": news}, index=idx)
    with pytest.raises(DartsTrainingError) as exc:
        run_darts_training(frame, model_type="LightGBM",
                           indicator_columns=["news_intensity"],
                           covariate_types={"news_intensity": "past"},
                           train_ratio=0.8, price_column="close")
    msg = str(exc.value)
    assert "news_intensity" in msg
    assert "training" in msg.lower()
    # It must tell the operator how to proceed, not merely refuse.
    assert "range" in msg.lower() or "remove" in msg.lower()


def test_training_still_runs_when_the_covariate_varies_in_training():
    """The guard must not block a legitimate run — the counterpart that stops it
    from being a blanket refusal."""
    pytest.importorskip("darts")
    from app.services.darts_trainer import run_darts_training
    n = 400
    idx = pd.bdate_range("2024-01-01", periods=n)
    close = 25.0 + 5.0 * np.sin(2.0 * np.pi * np.arange(n) / 20.0)
    rng = np.random.default_rng(0)
    frame = pd.DataFrame({"close": close, "news_intensity": rng.random(n)}, index=idx)
    out = run_darts_training(frame, model_type="LightGBM",
                             indicator_columns=["news_intensity"],
                             covariate_types={"news_intensity": "past"},
                             train_ratio=0.8, price_column="close")
    assert out["metrics"]["rmse"] > 0


# ---------------------------------------------------------------------------
# Backlog #126 — the fitted model survives training, and can forecast later
# ---------------------------------------------------------------------------
#
# WHAT THIS SECTION IS ABOUT. The darts path used to return metrics and throw
# the fitted model away, so model_instances.file_path stayed NULL and
# POST /solutions/predict — which loads a model from that column — answered
# "Model file not found at None" for every darts-trained solution. Training
# reported success and the Predict button could never work, on what has been
# the DEFAULT engine since 2026-10-30.


def _fit(model_type="XGBoost", n=320, **config):
    """Train once and hand back (fitted state, frame) for a forecast."""
    from app.services.darts_trainer import run_darts_training

    cfg = {"n_epochs": 1, "input_chunk_length": 20, "output_chunk_length": 5}
    cfg.update(config)
    frame = _frame(n=n)
    out = run_darts_training(
        frame, model_type=model_type,
        indicator_columns=["rsi_14", "sma_20"],
        covariate_types={"rsi_14": "past", "sma_20": "past"},
        train_ratio=0.85, config=cfg)
    return out, frame


def test_training_returns_everything_a_later_forecast_needs():
    """The model alone is not enough: a forecast has to transform its inputs
    with the SAME scalers, and read the same covariate columns in the same
    order, or the model meets a different problem than it was fitted on."""
    pytest.importorskip("darts")
    out, _ = _fit()
    fitted = out["fitted"]
    assert fitted["model"] is not None
    assert fitted["target_scaler"] is not None
    assert fitted["past_scaler"] is not None, (
        "the covariate scaler used to be discarded — a forecast cannot be "
        "reproduced without it")
    assert fitted["past_columns"] == ["rsi_14", "sma_20"]
    assert fitted["output_chunk_length"] == 5
    assert fitted["input_chunk_length"] == 20


@pytest.mark.parametrize("model_type", ["XGBoost", "DLinear"])
def test_a_forecast_follows_the_training_without_refitting(model_type):
    """The whole point of #126: predict with the model training produced."""
    pytest.importorskip("darts")
    import logging
    logging.getLogger("pytorch_lightning").setLevel(logging.ERROR)
    from app.services.darts_trainer import run_darts_forecast

    out, frame = _fit(model_type)
    state = {k: v for k, v in out["fitted"].items() if k != "model"}
    predict_start = frame.index[-10]

    res = run_darts_forecast(out["fitted"]["model"], state, frame,
                             predict_start=predict_start, horizon=5)

    assert res["engine"] == "darts"
    assert len(res["future"]) == 5
    assert all(p["predicted_price"] > 0 for p in res["future"])
    # The forecast lies beyond the last bar, which is what makes it a forecast.
    assert all(pd.Timestamp(p["date"]) > frame.index[-1] for p in res["future"])
    # The backtest covers the requested window and nothing before it.
    assert res["backtest"]
    assert all(pd.Timestamp(p["date"]) >= predict_start for p in res["backtest"])
    assert all(pd.Timestamp(p["date"]) <= frame.index[-1] for p in res["backtest"])


def test_the_backtest_prices_are_in_price_units_not_scaler_units():
    """A forecast returned in scaler units (0..1) would plot as a flat line at
    the bottom of a chart whose prices are ~20 — and every metric would still
    be finite, so nothing downstream would complain."""
    pytest.importorskip("darts")
    from app.services.darts_trainer import run_darts_forecast

    out, frame = _fit()
    state = {k: v for k, v in out["fitted"].items() if k != "model"}
    res = run_darts_forecast(out["fitted"]["model"], state, frame,
                             predict_start=frame.index[-10], horizon=5)
    level = float(frame["close"].iloc[-1])
    for p in res["backtest"] + res["future"]:
        assert 0.3 * level < p["predicted_price"] < 3 * level, p


def test_a_horizon_beyond_the_output_chunk_is_capped_and_disclosed():
    """MEASURED AGAINST darts 0.48.1, not assumed: with past covariates that
    stop at the last bar, predict(n) raises for n > output_chunk_length — "the
    provided past_covariates do not extend far enough into the future" — for
    DLinear and XGBoost alike. Extending them would mean inventing indicator
    values, i.e. future prices, which is the C1 leak this engine refuses.

    So the cap is a property of the problem. What matters is that it is SAID."""
    pytest.importorskip("darts")
    from app.services.darts_trainer import run_darts_forecast

    out, frame = _fit(output_chunk_length=5)
    state = {k: v for k, v in out["fitted"].items() if k != "model"}
    res = run_darts_forecast(out["fitted"]["model"], state, frame,
                             predict_start=frame.index[-3], horizon=30)
    assert res["horizon"] == 5
    assert res["requested_horizon"] == 30
    assert len(res["future"]) == 5
    assert any("horizon shortened" in w for w in res["warnings"]), res["warnings"]


def test_a_horizon_inside_the_output_chunk_is_not_capped():
    """Non-vacuity for the cap: it must not fire on a horizon that fits."""
    pytest.importorskip("darts")
    from app.services.darts_trainer import run_darts_forecast

    out, frame = _fit(output_chunk_length=5)
    state = {k: v for k, v in out["fitted"].items() if k != "model"}
    res = run_darts_forecast(out["fitted"]["model"], state, frame,
                             predict_start=frame.index[-3], horizon=3)
    assert res["horizon"] == 3 and len(res["future"]) == 3
    assert not any("horizon shortened" in w for w in res["warnings"])


def test_a_window_entirely_in_the_future_still_forecasts():
    """Predicting from a date after the last bar is the normal live case: there
    is nothing to backtest, and the forecast must still be produced."""
    pytest.importorskip("darts")
    from app.services.darts_trainer import run_darts_forecast

    out, frame = _fit()
    state = {k: v for k, v in out["fitted"].items() if k != "model"}
    res = run_darts_forecast(out["fitted"]["model"], state, frame,
                             predict_start=frame.index[-1] + pd.Timedelta(days=30),
                             horizon=5)
    assert res["backtest"] == []
    assert len(res["future"]) == 5


def test_a_missing_fitted_column_is_refused_rather_than_filled():
    """The tabular path fills an absent feature with zeros and logs a warning.
    Here that would feed the model a dead covariate and return a forecast that
    looks fine — the silent-substitution class of #109/#110. Refuse instead."""
    pytest.importorskip("darts")
    from app.services.darts_trainer import DartsTrainingError, run_darts_forecast

    out, frame = _fit()
    state = {k: v for k, v in out["fitted"].items() if k != "model"}
    with pytest.raises(DartsTrainingError, match="missing columns"):
        run_darts_forecast(out["fitted"]["model"], state,
                           frame.drop(columns=["sma_20"]),
                           predict_start=frame.index[-10], horizon=5)


def test_too_little_history_before_the_window_is_refused_readably():
    """Fewer bars than the model's lookback cannot produce a backtest. Darts
    would raise from three frames down; this says what to do about it."""
    pytest.importorskip("darts")
    from app.services.darts_trainer import DartsTrainingError, run_darts_forecast

    out, frame = _fit(input_chunk_length=20)
    state = {k: v for k, v in out["fitted"].items() if k != "model"}
    short = frame.iloc[-15:]            # 15 bars for a 20-bar lookback
    with pytest.raises(DartsTrainingError, match="bar"):
        run_darts_forecast(out["fitted"]["model"], state, short,
                           predict_start=short.index[-5], horizon=5)


def test_the_scalers_are_reused_and_not_refitted_on_prediction_data():
    """C1. Re-fitting a scaler at prediction time would both move the model's
    inputs under it and fit on data after the training span. Two frames that
    differ only AFTER the backtest window must give the same backtest."""
    pytest.importorskip("darts")
    from app.services.darts_trainer import run_darts_forecast

    out, frame = _fit()
    state = {k: v for k, v in out["fitted"].items() if k != "model"}
    predict_start = frame.index[-12]

    base = run_darts_forecast(out["fitted"]["model"], state, frame,
                              predict_start=predict_start, horizon=5)
    # Blow up the last two bars by a factor a refit scaler could not ignore.
    tampered = frame.copy()
    tampered.iloc[-2:, tampered.columns.get_loc("close")] *= 40
    after = run_darts_forecast(out["fitted"]["model"], state, tampered,
                               predict_start=predict_start, horizon=5)

    unchanged = [b for b, a in zip(base["backtest"], after["backtest"])
                 if pd.Timestamp(b["date"]) < frame.index[-2]]
    assert unchanged, "the comparison would be vacuous with no earlier points"
    for b, a in zip(base["backtest"], after["backtest"]):
        if pd.Timestamp(b["date"]) < frame.index[-2]:
            assert b["predicted_price"] == pytest.approx(a["predicted_price"]), (
                "a prediction for an earlier date moved when LATER data changed "
                "— the scaler is being refitted at prediction time")
