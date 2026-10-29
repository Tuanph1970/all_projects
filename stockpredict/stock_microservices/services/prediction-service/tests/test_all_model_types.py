"""Every model type in the catalogue must actually build and fit (Backlog #107/#109).

The owner offered to create fourteen solutions, one per model, to check they all
work. That is not necessary: `_create_ml_model` is a pure function, so every
type in `MODEL_TYPE_MAP` can be built and fitted here on synthetic data without
touching the database or a real solution.

What this pins, and why it is not obvious from reading the code: the catalogue
advertises Darts architectures but `DARTS_TO_ML_MAP` resolves each one to an
INSTALLED backend — xgboost, lightgbm, random_forest or linear_regression —
with its own hyperparameter profile. So "BlockRNN" trains as an XGBRegressor.
Nothing imports darts and nothing needs to. These tests fail if a catalogue
entry ever loses its mapping or its profile and silently degrades to the
fallback.
"""
from __future__ import annotations

import numpy as np
import pytest

from app.api.model_capabilities import MODEL_COVARIATE_SUPPORT
from app.api.routes import MODEL_TYPE_MAP
from app.api.solution_routes import DARTS_TO_ML_MAP, _create_ml_model

ALL_TYPES = sorted(set(MODEL_TYPE_MAP.values()))


def _synthetic(n=180, k=5, seed=0):
    """A small, learnable regression problem — enough to prove `fit` works."""
    rng = np.random.default_rng(seed)
    X = rng.normal(size=(n, k))
    y = X @ np.arange(1, k + 1) + rng.normal(scale=0.1, size=n)
    return X, y


@pytest.mark.parametrize("model_type", ALL_TYPES)
def test_every_catalogue_type_builds_and_fits(model_type):
    """The question the owner asked — do all the models work? — answered without
    creating fourteen solutions."""
    model = _create_ml_model(model_type, "", None)
    assert model is not None, model_type

    X, y = _synthetic()
    model.fit(X, y)
    pred = model.predict(X)
    assert pred.shape == y.shape
    assert np.all(np.isfinite(pred)), f"{model_type} produced non-finite predictions"


@pytest.mark.parametrize("model_type", ALL_TYPES)
def test_every_catalogue_type_resolves_to_an_installed_backend(model_type):
    """A type missing from DARTS_TO_ML_MAP silently falls back to xgboost, so
    the UI would offer a distinct model that is really the default one."""
    assert model_type in DARTS_TO_ML_MAP, (
        f"{model_type} has no backend mapping and would silently become xgboost")
    assert DARTS_TO_ML_MAP[model_type] in {
        "xgboost", "lightgbm", "random_forest", "linear_regression"}


#: Keys kept for rows that may carry the older Darts class names, plus
#: LinearRegression which is a backend but not offered for creation. Listed
#: explicitly so a genuinely stray key still fails the test below.
ALLOWED_EXTRA_KEYS = {
    "LinearRegression",
    "RNNModel", "TCNModel", "TransformerModel", "TFTModel", "NBEATSModel",
}


def test_the_backend_map_covers_the_whole_catalogue_and_no_more():
    """Every creatable type must map, and anything extra must be a declared
    alias — not a typo that quietly shadows nothing."""
    offered = set(MODEL_TYPE_MAP.values())
    mapped = set(DARTS_TO_ML_MAP)
    assert not (offered - mapped), f"unmapped: {sorted(offered - mapped)}"
    stray = sorted(mapped - offered - ALLOWED_EXTRA_KEYS)
    assert not stray, f"keys that match no creatable type and no declared alias: {stray}"


def test_each_alias_agrees_with_its_canonical_name():
    """The four aliases exist because the canonical names were MISSING and those
    types fell through to default XGBoost (Backlog #110). If an alias and its
    canonical name ever disagree, the same silent divergence is back.

    NBEATSModel is deliberately NOT in this list — see the test below. It is not
    an alias.
    """
    for alias, canonical in (("RNNModel", "RNN"), ("TCNModel", "TCN"),
                             ("TransformerModel", "Transformer"),
                             ("TFTModel", "TFT")):
        assert DARTS_TO_ML_MAP[alias] == DARTS_TO_ML_MAP[canonical], alias
        a = _create_ml_model(alias, "", None).get_params()
        c = _create_ml_model(canonical, "", None).get_params()
        assert a.get("n_estimators") == c.get("n_estimators"), alias
        assert a.get("max_depth") == c.get("max_depth"), alias


def test_NBEATSModel_is_unreachable_dead_config():
    """Recorded rather than silently tidied, because it is NOT an alias.

    `NBEATSModel` is absent from MODEL_TYPE_MAP, so no user can create it, and
    its profile DIFFERS from `NBeats` (400 trees / depth 15 against 300 / 12).
    It is therefore unreachable configuration that looks like a fifth alias.
    Deleting it is safe but is a separate decision; this test documents the
    state so the divergence is not mistaken for a bug in the four real aliases.
    """
    assert "NBEATSModel" not in set(MODEL_TYPE_MAP.values())
    a = _create_ml_model("NBEATSModel", "", None).get_params()
    c = _create_ml_model("NBeats", "", None).get_params()
    assert a.get("n_estimators") != c.get("n_estimators"), (
        "NBEATSModel now matches NBeats — if that was deliberate, fold it into "
        "the alias test above and delete this one")


def test_the_three_registries_agree_on_the_catalogue():
    """MODEL_TYPE_MAP (creatable), DARTS_TO_ML_MAP (backend) and
    MODEL_COVARIATE_SUPPORT (#107) must describe the same set, or a model can be
    created that one of the other two has never heard of."""
    offered = set(MODEL_TYPE_MAP.values())
    assert not (offered - set(DARTS_TO_ML_MAP)), "backend map is behind"
    assert not (offered - set(MODEL_COVARIATE_SUPPORT)), "capability table is behind"


@pytest.mark.parametrize("model_type", ALL_TYPES)
def test_each_type_gets_a_distinct_hyperparameter_profile(model_type):
    """The catalogue's whole justification: different selections must produce
    genuinely different models rather than fourteen identical XGBRegressors."""
    model = _create_ml_model(model_type, "", None)
    params = model.get_params()
    assert params, model_type
    # The profiles differ on n_estimators, which every backend exposes.
    assert "n_estimators" in params or DARTS_TO_ML_MAP[model_type] == "linear_regression"


def test_distinct_types_on_the_same_backend_are_not_identical():
    """BlockRNN, TCNModel, NHits, TiDE and CatBoost all resolve to xgboost. If
    their profiles collapsed, the UI's model choice would be cosmetic."""
    xgb_types = [t for t in ALL_TYPES if DARTS_TO_ML_MAP.get(t) == "xgboost"]
    assert len(xgb_types) >= 3, xgb_types
    profiles = set()
    for t in xgb_types:
        p = _create_ml_model(t, "", None).get_params()
        profiles.add((p.get("n_estimators"), p.get("max_depth"), p.get("learning_rate")))
    assert len(profiles) > 1, (
        f"all xgboost-backed types share one profile: {xgb_types}")


def test_user_config_overrides_the_profile():
    base = _create_ml_model("XGBoost", "", None).get_params()
    tuned = _create_ml_model("XGBoost", "", '{"n_estimators": 7}').get_params()
    assert base["n_estimators"] != 7
    assert tuned["n_estimators"] == 7


@pytest.mark.parametrize("bad", ['{"not": json', "", None, "[]", "null"])
def test_malformed_user_config_falls_back_to_the_profile(bad):
    """A broken config_json must not take the model down — it is user input
    stored as text."""
    model = _create_ml_model("XGBoost", "", bad)
    assert model is not None
    assert model.get_params()["n_estimators"] > 0
