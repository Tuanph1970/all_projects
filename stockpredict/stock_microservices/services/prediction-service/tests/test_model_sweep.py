"""The sweep's model list must not drift from the server's (Backlog: pre-release).

tests/model_sweep.py holds the 14 URL names as a literal so it can run without
importing the service. That literal is the obvious thing to fall behind: add a
fifteenth architecture to MODEL_TYPE_MAP and the sweep would keep reporting
"14 passed" while never touching the new one — a green sweep that proves less
than it did yesterday, which is worse than a red one.

These tests make that drift a test failure instead.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

from app.api.routes import MODEL_TYPE_MAP
from app.api.solution_routes import (
    DARTS_TO_ML_MAP,
    SUPPORTED_TRAINING_ENGINES,
    TABULAR_NATIVE_BACKENDS,
)

_SPEC = importlib.util.spec_from_file_location(
    "model_sweep", Path(__file__).parent / "model_sweep.py")
sweep = importlib.util.module_from_spec(_SPEC)
# Registered BEFORE exec: the @dataclass on Cell resolves its annotations via
# sys.modules[cls.__module__], which is None for a module loaded by spec alone —
# dataclasses then raises AttributeError at import time, before any test runs.
sys.modules["model_sweep"] = sweep
_SPEC.loader.exec_module(sweep)


def test_the_sweep_covers_every_creatable_architecture():
    """Every key of MODEL_TYPE_MAP, and nothing that is not one."""
    assert set(sweep.MODEL_URL_NAMES) == set(MODEL_TYPE_MAP)


def test_the_sweep_covers_every_supported_engine():
    assert set(sweep.ENGINES) == set(SUPPORTED_TRAINING_ENGINES)


def test_the_substitution_table_matches_the_service():
    """The sweep VERIFIES the backend_substituted disclosure, so its own idea of
    which models are native has to be the service's idea. If these diverge the
    sweep would report a correct disclosure as a defect, or miss a wrong one."""
    assert sweep.TABULAR_NATIVE == set(TABULAR_NATIVE_BACKENDS)


def test_every_swept_architecture_is_known_to_the_darts_map():
    """A catalogue name missing from DARTS_TO_ML_MAP falls through to the
    xgboost default — #110, where four of fourteen were silently the same
    model. The sweep would catch it at runtime; this catches it at desk."""
    missing = [m for m in MODEL_TYPE_MAP.values() if m not in DARTS_TO_ML_MAP]
    assert missing == [], f"not in DARTS_TO_ML_MAP: {missing}"


# ---------------------------------------------------------------------------
# The judgement, which is the part that finds bugs
# ---------------------------------------------------------------------------

def _cell(engine="darts", model="TFT"):
    return sweep.Cell(model=model, engine=engine)


GOOD = {
    "engine": "darts", "model_type": "TFT", "rmse": 0.77, "mae": 0.63, "r2": 0.05,
    "training_samples": 671, "validation_samples": 53,
    "naive_rmse": 0.29, "beats_naive_rmse": False,
}
RISING = [10.0, 10.4, 10.9, 11.1, 11.6]


def test_a_healthy_run_passes():
    c = _cell()
    sweep.judge(c, "TFT", dict(GOOD), RISING)
    assert c.verdict == "PASS", c.problems


def test_a_flat_forecast_fails():
    """#109: the darts engine trained happily and predicted the same value every
    day because normalisation was missing. Nothing in the metrics said so."""
    c = _cell()
    sweep.judge(c, "TFT", dict(GOOD), [11.0] * 5)
    assert c.verdict == "FAIL"
    assert any("FLAT" in p for p in c.problems)


def test_a_result_naming_the_wrong_model_fails():
    """#110: four architectures fell through to xgboost and reported it."""
    c = _cell()
    sweep.judge(c, "TFT", {**GOOD, "model_type": "XGBoost"}, RISING)
    assert c.verdict == "FAIL"
    assert any("asked for 'TFT'" in p for p in c.problems)


def test_a_result_naming_the_wrong_engine_fails():
    c = _cell(engine="tabular")
    sweep.judge(c, "XGBoost", {**GOOD, "engine": "darts", "model_type": "XGBoost",
                               "backend_substituted": False}, RISING)
    assert c.verdict == "FAIL"
    assert any("engine" in p for p in c.problems)


def test_an_undisclosed_tabular_substitution_fails():
    """#109: the tabular engine cannot build a TFT, so it must SAY it trained a
    booster instead. A result claiming the substitution did not happen is the
    exact defect that row was about."""
    c = _cell(engine="tabular")
    sweep.judge(c, "TFT", {**GOOD, "engine": "tabular", "backend_substituted": False}, RISING)
    assert c.verdict == "FAIL"
    assert any("backend_substituted" in p for p in c.problems)


def test_a_correctly_disclosed_substitution_passes():
    """Non-vacuity for the test above: an honest substitution is not a defect."""
    c = _cell(engine="tabular")
    sweep.judge(c, "TFT", {**GOOD, "engine": "tabular", "backend_substituted": True}, RISING)
    assert c.verdict == "PASS", c.problems


def test_a_native_tabular_model_must_not_claim_substitution():
    c = _cell(engine="tabular")
    sweep.judge(c, "XGBoost", {**GOOD, "engine": "tabular", "model_type": "XGBoost",
                               "backend_substituted": True}, RISING)
    assert c.verdict == "FAIL"


def test_missing_disclosure_fails_rather_than_being_assumed_fine():
    c = _cell(engine="tabular")
    m = {**GOOD, "engine": "tabular", "model_type": "TFT"}
    m.pop("backend_substituted", None)
    sweep.judge(c, "TFT", m, RISING)
    assert c.verdict == "FAIL"


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), "n/a", None])
def test_a_non_finite_metric_fails(bad):
    c = _cell()
    sweep.judge(c, "TFT", {**GOOD, "rmse": bad}, RISING)
    assert c.verdict == "FAIL"


def test_a_zero_rmse_is_treated_as_leakage_not_excellence():
    c = _cell()
    sweep.judge(c, "TFT", {**GOOD, "rmse": 0.0}, RISING)
    assert c.verdict == "FAIL"
    assert any("leakage" in p for p in c.problems)


def test_training_on_nothing_fails():
    c = _cell()
    sweep.judge(c, "TFT", {**GOOD, "validation_samples": 0}, RISING)
    assert c.verdict == "FAIL"


def test_an_empty_result_fails_loudly():
    c = _cell()
    sweep.judge(c, "TFT", {}, RISING)
    assert c.verdict == "FAIL"
    assert any("no training_metrics_json" in p for p in c.problems)


def test_losing_to_naive_is_a_note_and_not_a_failure():
    """A model worse than naive is a RESULT. Failing the sweep on it would hide
    the opposite problem — and the one real stored run on this install
    (BlockRNN, rmse 0.77 vs naive 0.30) loses, so treating it as breakage would
    make the sweep red for a reason that is not a bug."""
    c = _cell()
    sweep.judge(c, "TFT", dict(GOOD), RISING)
    assert c.verdict == "PASS"
    assert any("does not beat naive" in n for n in c.notes)


def test_an_unretrievable_forecast_is_a_note_not_a_pass_disguised_as_proof():
    """If the forecast could not be fetched, flatness is UNCHECKED — the cell
    must say so rather than imply the check ran and passed."""
    c = _cell()
    sweep.judge(c, "TFT", dict(GOOD), None)
    assert c.verdict == "PASS"
    assert any("flatness unchecked" in n for n in c.notes)
