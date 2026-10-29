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
