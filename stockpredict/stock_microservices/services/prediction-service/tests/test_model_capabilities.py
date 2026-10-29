"""Backlog #107 — which covariate kinds each model type accepts.

These flags gate what the Solutions UI offers: `SolutionModal` reads
`past_covariate` / `future_covariate` off each model and hands them to
`IndicatorSelector` as `hasPastCovariate` / `hasFutureCovariate`, which decides
whether a user may mark an indicator past, future or both.

They were never populated. The create path inserted `model_instances` without
them, so every row fell to the column default of `0` and the UI concluded that
no model accepts any covariate — while `solution_1` had four past covariates
attached to a BlockRNN whose own flags said it took none.

A *future* covariate must be known over the forecast horizon at prediction
time, so a wrong flag here is not cosmetic: it is where look-ahead bias gets
configured in by hand (Backlog #104, #105).
"""
from __future__ import annotations

import inspect

import pytest

from app.api.model_capabilities import (
    MODEL_COVARIATE_SUPPORT,
    SEED_DISAGREEMENTS,
    covariate_support,
)
from app.api.routes import MODEL_TYPE_MAP


def test_every_offered_model_type_has_a_capability_entry():
    """The bound-default guard, in the form that bites here.

    `MODEL_TYPE_MAP` is what the API will accept when creating a model. A type
    a user can create but the table does not know falls to the conservative
    `(False, False)`, silently forbidding every covariate for it — the exact
    symptom this item was raised to fix, just for a different type.
    """
    missing = sorted(set(MODEL_TYPE_MAP.values()) - set(MODEL_COVARIATE_SUPPORT))
    assert not missing, (
        f"creatable model types with no capability entry: {missing} — they would "
        f"silently accept no covariates")


def test_the_table_does_not_claim_types_the_api_will_not_create():
    """The converse: a stale entry is dead weight that misleads the next reader."""
    extra = sorted(set(MODEL_COVARIATE_SUPPORT) - set(MODEL_TYPE_MAP.values()))
    assert not extra, f"capability entries for non-creatable types: {extra}"


def test_blockrnn_is_past_only_and_rnn_is_future_only():
    """The asymmetry that is easy to get backwards — and that the existing
    `tbl_model_field` seed does get backwards, offering both kinds for each."""
    assert covariate_support("BlockRNN") == (True, False)
    assert covariate_support("RNN") == (False, True)


@pytest.mark.parametrize("model_type", ["TFT", "DLinear", "NLinear", "TiDE",
                                        "XGBoost", "LightGBM", "RandomForest",
                                        "CatBoost"])
def test_models_that_take_both_kinds(model_type):
    assert covariate_support(model_type) == (True, True)


@pytest.mark.parametrize("model_type", ["TCN", "Transformer", "NBeats", "NHits"])
def test_models_that_take_past_only(model_type):
    assert covariate_support(model_type) == (True, False)


@pytest.mark.parametrize("bad", [None, "", "   ", "Nonsense", "blockrnn"])
def test_an_unknown_type_is_refused_conservatively(bad):
    """`(False, False)` deliberately.

    Note `blockrnn` lower-case is NOT canonical: `MODEL_TYPE_MAP` maps it TO
    `BlockRNN`, and the canonical form is what lands in
    `model_instances.model_type`. Looking up the raw key must not accidentally
    succeed, or the two spellings would disagree.

    Conservative is the right direction: refusing a legitimate slot is visible
    and complainable, permitting an illegitimate one is not.
    """
    assert covariate_support(bad) == (False, False)


def test_whitespace_around_a_stored_type_is_tolerated():
    assert covariate_support(" TFT ") == (True, True)


def test_no_model_claims_future_without_past_except_RNN():
    """A property, not a list: future-but-not-past is unusual enough that a new
    one should be deliberate. RNN is the documented exception."""
    odd = sorted(name for name, (past, future) in MODEL_COVARIATE_SUPPORT.items()
                 if future and not past)
    assert odd == ["RNN"], odd


def test_every_entry_supports_at_least_one_kind():
    """A `(False, False)` entry would be indistinguishable from an unknown type,
    which is how the original defect looked from the UI."""
    dead = sorted(n for n, caps in MODEL_COVARIATE_SUPPORT.items()
                  if caps == (False, False))
    assert not dead, dead


def test_the_seed_disagreement_note_names_real_types():
    """Keeps the recorded note honest: every type it accuses must exist."""
    unknown = sorted(set(SEED_DISAGREEMENTS) - set(MODEL_COVARIATE_SUPPORT))
    assert not unknown, unknown


# ---------------------------------------------------------------------------
# The wiring — the flags must reach the two places that gate the UI
# ---------------------------------------------------------------------------

def test_the_create_path_populates_both_flags():
    """The actual defect: the INSERT omitted them, so the column default won."""
    from app.api import routes

    src = inspect.getsource(routes)
    assert "covariate_support(model_type)" in src, (
        "the create path no longer derives the flags")
    assert '"past_covariate": int(past_cov)' in src
    assert '"future_covariate": int(future_cov)' in src


def test_the_models_endpoint_derives_rather_than_trusting_stored_flags():
    """Existing rows all carry 0/0, so trusting the column would leave the UI
    wrong until someone ran a migration. Deriving on read fixes history for
    free and keeps a single source of truth in code."""
    from app.api import solution_routes

    src = inspect.getsource(solution_routes)
    assert 'covariate_support(item.get("model_type"))' in src, (
        "get_predict_models no longer derives the flags from the model type")
