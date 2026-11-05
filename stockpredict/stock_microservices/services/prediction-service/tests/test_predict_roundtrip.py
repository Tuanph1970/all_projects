"""Guards for tests/predict_roundtrip.py (Backlog #125: pre-release usage sweep).

TWO JOBS, and they fail for different reasons.

1. DRIFT. The sweep holds the 14 URL names and the four indicator groups as
   literals so it can run without importing the service. Those literals are the
   obvious thing to fall behind: add a fifteenth architecture and the sweep would
   go on reporting "7 of 14 swept" while never touching the new one — a green
   sweep that proves less than it did yesterday.

2. THE JUDGEMENT. The sweep's value is entirely in what it calls a failure, and
   that code has already been wrong once in a way that mattered: the first
   version compared len(predict) with len(actual) and nothing else, so a
   response with EVERY series empty passed, because 0 == 0. That is the exact
   response the tabular engine returns for a short prediction window. The check
   meant to catch the worst case was vacuous precisely in it, so each rule here
   is pinned by a test that fails if the rule stops firing — and, where it could
   go vacuous, by a companion that fails if it starts firing on healthy input.
"""
from __future__ import annotations

import importlib.util
import inspect
import sys
from datetime import date
from pathlib import Path

import pytest

from app.api.routes import MODEL_TYPE_MAP
from app.api.solution_routes import set_solution_indicators

_SPEC = importlib.util.spec_from_file_location(
    "predict_roundtrip", Path(__file__).parent / "predict_roundtrip.py")
rt = importlib.util.module_from_spec(_SPEC)
# Registered BEFORE exec, for the same reason test_model_sweep.py does it: the
# @dataclass on Run resolves its annotations via sys.modules[cls.__module__],
# which is None for a module loaded by spec alone, and dataclasses then raises
# at import time — before any test gets to run.
sys.modules["predict_roundtrip"] = rt
_SPEC.loader.exec_module(rt)

_SWEEP_SPEC = importlib.util.spec_from_file_location(
    "model_sweep", Path(__file__).parent / "model_sweep.py")
sweep = importlib.util.module_from_spec(_SWEEP_SPEC)
sys.modules.setdefault("model_sweep", sweep)
_SWEEP_SPEC.loader.exec_module(sweep)


# ---------------------------------------------------------------------------
# 1. Drift
# ---------------------------------------------------------------------------

def test_the_sweep_knows_every_creatable_architecture():
    assert set(rt.MODEL_URL_NAMES) == set(MODEL_TYPE_MAP)


def test_the_two_sweeps_hold_the_same_model_list():
    """Two scripts, two literals, one catalogue. Letting them diverge means one
    sweep silently covers an architecture the other does not."""
    assert set(rt.MODEL_URL_NAMES) == set(sweep.MODEL_URL_NAMES)


def test_the_default_selection_is_exactly_half_the_catalogue():
    """The brief asked for half the models in one run. If the catalogue grows to
    15, 'seven' stops being half and this says so rather than drifting."""
    assert len(rt.DEFAULT_HALF) == len(rt.MODEL_URL_NAMES) // 2


def test_the_two_halves_partition_the_catalogue_without_overlap():
    """--other-half has to be the complement, or some model is never swept by
    either invocation and nobody would notice which."""
    assert set(rt.DEFAULT_HALF) | set(rt.OTHER_HALF) == set(rt.MODEL_URL_NAMES)
    assert not set(rt.DEFAULT_HALF) & set(rt.OTHER_HALF)


def test_the_default_half_spans_both_engine_families():
    """A half made only of tree ensembles would exercise one code path twice and
    the other not at all."""
    trees = {"xgboost", "lightgbm", "randomforest", "catboost"}
    assert set(rt.DEFAULT_HALF) & trees
    assert set(rt.DEFAULT_HALF) - trees


def test_the_indicator_request_keys_are_the_keys_the_route_reads():
    """The sweep posts {trend_indicator: ...}. The route's own category_map is
    local to the function, so its SOURCE is the only honest reference — and a
    renamed key would otherwise make the sweep save nothing while reporting
    that it saved four indicators."""
    source = inspect.getsource(set_solution_indicators)
    for group, key in rt.GROUP_REQUEST_KEY.items():
        assert f'"{key}"' in source, f"{group}: route does not read {key}"
        assert f'"{group}"' in source, f"route does not map {key} to {group}"


def test_an_indicator_is_a_past_covariate():
    """Backlog #105 — a technical indicator is a function of price, so its
    future values are not knowable. The server refuses future/both."""
    assert rt.COVARIATE_TYPE == "past"


def test_the_training_window_really_is_about_two_years():
    assert 700 <= rt.TRAINING_WINDOW_DAYS <= 760


# ---------------------------------------------------------------------------
# Helpers that decide the dates
# ---------------------------------------------------------------------------

def test_the_day_after_a_friday_is_a_monday():
    assert rt.next_business_day(date(2026, 2, 6)) == date(2026, 2, 9)


def test_the_day_after_a_wednesday_is_a_thursday():
    assert rt.next_business_day(date(2026, 2, 4)) == date(2026, 2, 5)


def test_a_horizon_never_lands_on_a_weekend():
    start = rt.next_business_day(date(2026, 2, 2))
    span = [start] + [rt.add_business_days(start, i) for i in range(1, 10)]
    assert all(d.weekday() < 5 for d in span), span


def test_defaults_arriving_as_strings_are_read_as_numbers():
    """GET /models/parameters/default-values returns '10', not 10 — that is what
    the form posts. Reading it as a string would make every horizon check fail
    for a reason that is not a bug."""
    assert rt.as_int("10") == 10
    assert rt.as_int("0.0") == 0
    assert rt.as_int(None) is None
    assert rt.as_int("n/a") is None


def test_the_training_window_stays_inside_the_available_history():
    """A start before the first bar trains on less data than the brief requires,
    and a thin-data failure would then look like a model failure."""
    import random
    avail_start, avail_end = date(2020, 1, 1), date(2026, 11, 1)
    for seed in range(40):
        start, end = rt.pick_window(avail_start, avail_end,
                                    random.Random(seed), rt.TRAINING_WINDOW_DAYS)
        assert start >= avail_start, (seed, start)
        assert end <= avail_end, (seed, end)
        assert (end - start).days == rt.TRAINING_WINDOW_DAYS


def test_the_window_shrinks_rather_than_overrunning_a_short_history():
    start, end = rt.pick_window(date(2026, 1, 1), date(2026, 6, 1),
                                __import__("random").Random(0), 730)
    assert start == date(2026, 1, 1)
    assert end <= date(2026, 6, 1)


def test_the_same_seed_replays_the_same_choices():
    """The report prints the seed so a failure can be reproduced. If the seed did
    not determine the choices, that promise would be a lie."""
    import random
    groups = {g: [{"id": i, "name": f"{g}{i}", "default_parameters": {"period": i}}
                  for i in range(1, 6)] for g in rt.INDICATOR_GROUPS}
    first, _ = rt.choose_indicators(groups, random.Random(99))
    again, _ = rt.choose_indicators(groups, random.Random(99))
    assert first == again


def test_an_empty_dropdown_is_reported_rather_than_skipped():
    import random
    groups = {g: [{"id": 1, "name": "X", "default_parameters": {}}]
              for g in rt.INDICATOR_GROUPS}
    groups["volatility"] = []
    chosen, missing = rt.choose_indicators(groups, random.Random(0))
    assert missing == ["volatility"]
    assert "volatility" not in chosen


# ---------------------------------------------------------------------------
# 2. The judgement: the prediction payload
# ---------------------------------------------------------------------------

P_START = date(2026, 2, 3)        # a Tuesday
HORIZON = 5


def _run(horizon: int = HORIZON) -> "rt.Run":
    r = rt.Run(url_name="tft")
    r.horizon = horizon
    r.train_window = ("2024-02-03", "2026-02-02")
    return r


def _series(days: list[str], values: list[float]) -> list[dict]:
    return [{"tradingdate": d, "close": v} for d, v in zip(days, values)]


FUTURE_DAYS = ["2026-02-03", "2026-02-04", "2026-02-05", "2026-02-06", "2026-02-09"]
RISING = [95.0, 95.4, 96.1, 95.8, 96.6]


def _payload(**over) -> dict:
    body = {
        "solution_id": 1,
        "ticker": "FPT",
        "train_status": "predicted",
        "chart": [{"date": "2026-01-30", "actual_price": 94.0,
                   "predicted_price": 93.6}],
        "actual": _series(["2026-02-03", "2026-02-04"], [93.5, 94.0]),
        "predict": _series(["2026-02-03", "2026-02-04"], [93.2, 93.9]),
        "future": _series(FUTURE_DAYS, RISING),
        "metrics": {"rmse": 2.07, "mae": 1.57, "r2": 0.79},
        "future_days": HORIZON,
    }
    body.update(over)
    return body


def _judge(payload, horizon: int = HORIZON) -> "rt.Run":
    r = _run(horizon)
    rt.judge_prediction(r, payload, P_START,
                        rt.add_business_days(P_START, horizon - 1), horizon)
    return r


def test_a_healthy_prediction_passes():
    """Non-vacuity for everything below: if this failed, the rules would be
    rejecting correct payloads and every FAIL in a sweep would be noise."""
    r = _judge(_payload())
    assert r.verdict == "PASS", r.problems


def test_an_all_empty_payload_fails_even_though_the_series_lengths_agree():
    """THE REGRESSION THIS FILE EXISTS FOR. len(predict) == len(actual) holds at
    zero, so the original check passed the one response that matters most: 200
    OK, four empty series, null metrics, a blank chart and no error on screen."""
    r = _judge(_payload(chart=[], actual=[], predict=[], future=[],
                        metrics={"rmse": None, "mae": None, "r2": None},
                        future_days=5))
    assert r.verdict == "FAIL"
    assert any("every series empty" in p for p in r.problems), r.problems


def test_a_holiday_window_is_a_note_and_not_a_failure():
    """FALSE POSITIVE FOUND IN VERIFICATION, 2026-11-05. The flat form of the
    rule above failed a request for 2024-04-30 — Reunification Day, with the
    exchange shut from the 29th to the 1st. An empty backtest is CORRECT there,
    and reporting it as a service defect would have been a harness error wearing
    a service error's clothes. The chart tells the two apart: it is populated,
    and none of its dates fall in the window."""
    r = _judge(_payload(
        actual=[], predict=[],
        chart=[{"date": "2026-01-29", "actual_price": 94.0, "predicted_price": 93.6},
               {"date": "2026-01-30", "actual_price": 94.2, "predicted_price": 93.9}],
        metrics={"rmse": None, "mae": None, "r2": None}))
    assert r.verdict == "PASS", r.problems
    assert any("holiday window" in n for n in r.notes), r.notes


def test_an_empty_backtest_over_a_window_that_HAS_bars_still_fails():
    """Non-vacuity for the exemption: the market being open is the whole
    difference. Chart data inside the requested window means bars existed and
    the backtest dropped them, which is a defect again."""
    r = _judge(_payload(
        actual=[], predict=[],
        chart=[{"date": d, "actual_price": 94.0, "predicted_price": 93.6}
               for d in FUTURE_DAYS],
        metrics={"rmse": None, "mae": None, "r2": None}))
    assert r.verdict == "FAIL"
    assert any("were not returned" in p for p in r.problems), r.problems


def test_an_empty_forecast_fails():
    r = _judge(_payload(future=[], future_days=0))
    assert r.verdict == "FAIL"
    assert any("no `future` series" in p for p in r.problems)


def test_a_forecast_shorter_than_the_models_horizon_fails():
    """#127. The model was created with output_chunk_length=5 and the forecast
    is two days long, because `future` is sized from DEFAULT_PREDICTION_DAYS.

    THE MESSAGE IS PART OF THE ASSERTION. An earlier version blamed the
    requested start/end window, which measurement showed IS honoured — acting
    on that wording would have meant changing correct behaviour."""
    r = _judge(_payload(future=_series(FUTURE_DAYS[:2], RISING[:2]), future_days=2))
    assert r.verdict == "FAIL"
    assert any("output_chunk_length=5" in p and "ignores" in p
               for p in r.problems), r.problems


def test_a_backtest_outside_the_requested_window_fails():
    """The dates in the request govern the backtest series. Pinned so a fix
    aimed at the forecast length cannot start serving a different range here."""
    r = _judge(_payload(
        actual=_series(["2026-01-29", "2026-02-04"], [93.5, 94.0]),
        predict=_series(["2026-01-29", "2026-02-04"], [93.2, 93.9])))
    assert r.verdict == "FAIL"
    assert any("outside the requested" in p for p in r.problems), r.problems


def test_a_backtest_filling_the_requested_window_passes():
    """Non-vacuity for the rule above: the honoured case must stay a PASS."""
    r = _judge(_payload(
        actual=_series(FUTURE_DAYS, RISING),
        predict=_series(FUTURE_DAYS, [v - 0.3 for v in RISING])))
    assert r.verdict == "PASS", r.problems


def test_future_days_disagreeing_with_the_series_fails():
    r = _judge(_payload(future_days=10))
    assert r.verdict == "FAIL"
    assert any("future_days=10" in p for p in r.problems)


def test_a_flat_forecast_fails():
    """#52 and #109 were both this: one number repeated down the column."""
    r = _judge(_payload(future=_series(FUTURE_DAYS, [95.0] * 5)))
    assert r.verdict == "FAIL"
    assert any("FLAT" in p for p in r.problems)


@pytest.mark.parametrize("bad", [None, float("nan"), "n/a"])
def test_a_forecast_point_without_a_price_fails(bad):
    broken = _series(FUTURE_DAYS, RISING)
    broken[2]["close"] = bad
    r = _judge(_payload(future=broken))
    assert r.verdict == "FAIL"
    assert any("no finite price" in p for p in r.problems)


def test_a_non_positive_price_fails():
    r = _judge(_payload(future=_series(FUTURE_DAYS, [95.0, 95.4, 0.0, 95.8, 96.6])))
    assert r.verdict == "FAIL"
    assert any("non-positive" in p for p in r.problems)


def test_a_forecast_reaching_back_into_the_training_period_fails():
    """Predicting days the model was fitted on is not a forecast, and on this
    screen it would be drawn as one."""
    days = ["2026-01-30"] + FUTURE_DAYS[1:]
    r = _judge(_payload(future=_series(days, RISING)))
    assert r.verdict == "FAIL"
    assert any("before the requested" in p for p in r.problems)


def test_a_forecast_on_a_weekend_fails():
    days = FUTURE_DAYS[:4] + ["2026-02-07"]      # a Saturday
    r = _judge(_payload(future=_series(days, RISING)))
    assert r.verdict == "FAIL"
    assert any("non-trading" in p for p in r.problems)


def test_a_repeated_forecast_date_fails():
    days = FUTURE_DAYS[:4] + [FUTURE_DAYS[3]]
    r = _judge(_payload(future=_series(days, RISING)))
    assert r.verdict == "FAIL"
    assert any("repeats a date" in p for p in r.problems)


def test_unpairable_chart_series_fail():
    r = _judge(_payload(predict=_series(["2026-02-03"], [93.9])))
    assert r.verdict == "FAIL"
    assert any("cannot be paired" in p for p in r.problems)


def test_a_non_finite_predict_metric_fails():
    r = _judge(_payload(metrics={"rmse": float("inf"), "mae": 1.5, "r2": 0.7}))
    assert r.verdict == "FAIL"


def test_null_predict_metrics_are_tolerated_when_the_series_are_present():
    """A null metric on a one-day window is arithmetic, not a bug: r2 needs two
    points. Failing on it would make a legitimate single-day horizon unreportable."""
    r = _judge(_payload(metrics={"rmse": None, "mae": None, "r2": None}))
    assert r.verdict == "PASS", r.problems


def test_the_payload_sizes_are_recorded_for_the_report():
    r = _judge(_payload())
    assert r.series_sizes == {"chart": 1, "actual": 2, "predict": 2, "future": 5}


def test_a_one_day_horizon_is_not_judged_for_flatness():
    """The tree ensembles default to output_chunk_length=1. A single point has no
    spread, and calling that flat would fail three models for free."""
    r = _judge(_payload(future=_series(FUTURE_DAYS[:1], RISING[:1]), future_days=1,
                        actual=_series(FUTURE_DAYS[:1], [93.5]),
                        predict=_series(FUTURE_DAYS[:1], [93.2])),
               horizon=1)
    assert r.verdict == "PASS", r.problems


# ---------------------------------------------------------------------------
# The judgement: training
# ---------------------------------------------------------------------------

def _status(**over) -> dict:
    result = {
        "engine": "tabular", "rmse": 3.02, "mae": 2.41, "r2": 0.36,
        "prediction_dates": {
            "prediction_start_date": "2026-02-03",
            "prediction_end_date": "2026-02-09",
            "output_chunk_length": HORIZON,
            "training_end_date": "2026-02-02",
        },
    }
    result.update(over)
    return {"status": "completed", "result": result}


def test_a_healthy_training_result_passes():
    r = _run()
    r.predict_window = ("2026-02-03", "2026-02-09")
    rt.judge_training(r, _status())
    assert r.verdict == "PASS", r.problems


def test_a_missing_prediction_dates_block_fails():
    """Not a modelling flaw — the Predict tab opens with no dates to offer after
    a training that reported success. The darts engine returns no such block."""
    status = _status()
    status["result"].pop("prediction_dates")
    r = _run()
    rt.judge_training(r, status)
    assert r.verdict == "FAIL"
    assert any("no prediction_dates" in p for p in r.problems)


def test_a_horizon_the_model_was_not_created_with_fails():
    """The tabular path hardcodes output_chunk_length=10 in this block, so a
    model created with 1 is offered a 10-day window."""
    r = _run(horizon=1)
    r.predict_window = ("2026-02-03", "2026-02-03")
    rt.judge_training(r, _status())
    assert r.verdict == "FAIL"
    assert any("output_chunk_length=10" in p or "output_chunk_length=5" in p
               for p in r.problems), r.problems


@pytest.mark.parametrize("key", ["rmse", "mae", "r2"])
def test_a_missing_training_metric_fails(key):
    status = _status()
    status["result"].pop(key)
    r = _run()
    rt.judge_training(r, status)
    assert r.verdict == "FAIL"


def test_a_non_finite_training_metric_fails():
    r = _run()
    rt.judge_training(r, _status(rmse=float("nan")))
    assert r.verdict == "FAIL"


def test_an_unnamed_engine_is_a_note_not_a_failure():
    """Which engine ran is reporting, not correctness — but a sweep that cannot
    say which path it exercised must admit it rather than imply darts."""
    status = _status()
    status["result"].pop("engine")
    r = _run()
    r.predict_window = ("2026-02-03", "2026-02-09")
    rt.judge_training(r, status)
    assert r.verdict == "PASS", r.problems
    assert any("does not name the engine" in n for n in r.notes)


# ---------------------------------------------------------------------------
# The judgement: the indicators the user chose
# ---------------------------------------------------------------------------

CHOSEN = {
    "trend": {"id": 10, "name": "ICHIMOKU", "covariate_type": "past",
              "parameters": {"tenkan_period": 9}},
    "momentum": {"id": 2, "name": "CCI", "covariate_type": "past",
                 "parameters": {"period": 20}},
}


def _stored(**over) -> dict:
    out = {g: {"id": c["id"], "covariate_type": "past",
               "parameters": c["parameters"]} for g, c in CHOSEN.items()}
    out.update(over)
    return out


def test_indicators_that_round_trip_intact_pass():
    r = _run()
    r.indicators = CHOSEN
    rt.judge_indicator_storage(r, _stored())
    assert r.verdict == "PASS", r.problems


def test_a_dropped_indicator_fails():
    """The write and the read are separate SQL paths; a lost row trains a
    different model than the one configured, with nothing on screen to say so."""
    r = _run()
    r.indicators = CHOSEN
    stored = _stored()
    stored.pop("momentum")
    rt.judge_indicator_storage(r, stored)
    assert r.verdict == "FAIL"
    assert any("absent from GET" in p for p in r.problems)


def test_an_indicator_coming_back_as_a_different_one_fails():
    r = _run()
    r.indicators = CHOSEN
    rt.judge_indicator_storage(r, _stored(trend={"id": 1, "parameters": {}}))
    assert r.verdict == "FAIL"
    assert any("came back as id 1" in p for p in r.problems)


def test_altered_indicator_parameters_fail():
    r = _run()
    r.indicators = CHOSEN
    rt.judge_indicator_storage(
        r, _stored(momentum={"id": 2, "parameters": {"period": 14}}))
    assert r.verdict == "FAIL"
    assert any("round-tripped" in p for p in r.problems)


def test_parameters_stored_as_a_json_string_are_still_compared_by_value():
    """`parameters` is a JSON column written with json.dumps; whether it reads
    back as a dict or a string is not a defect, and treating it as one would
    make every run fail for a non-bug."""
    r = _run()
    r.indicators = CHOSEN
    rt.judge_indicator_storage(
        r, _stored(momentum={"id": 2, "parameters": '{"period": 20}'}))
    assert r.verdict == "PASS", r.problems


def test_a_non_object_indicator_response_fails():
    r = _run()
    r.indicators = CHOSEN
    rt.judge_indicator_storage(r, [])
    assert r.verdict == "FAIL"
    assert any("expected an object" in p for p in r.problems)
