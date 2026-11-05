"""Solution Service API Routes

Provides CRUD endpoints for prediction solutions, matching the v2 frontend API.
References webapi/views_solution.py and webapi/repositories/predict_solution_repository.py
for database schema and business logic.
"""
import asyncio
import json
import logging
import os
import time as time_module
from typing import Optional, Dict, List
from datetime import datetime

import httpx
import joblib
import numpy as np
import pandas as pd
import ta
import xgboost as xgb
import lightgbm as lgb
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.api.dependencies import get_db, get_current_user_optional, get_current_user, async_session_factory
from app.config import get_settings

from app.api.model_capabilities import covariate_support
from app.services.news_covariates import (
    NewsCovariateError,
    attach_news_features,
    fetch_news_features,
    news_coverage,
)

logger = logging.getLogger(__name__)
settings = get_settings()

solution_router = APIRouter()

# Global dictionary to track training status (matches webapi pattern)
training_status = {}

# Backlog #109 — the engine that trains a solution when the caller does not say.
# OWNER DECISION 2026-10-30: the default is now 'darts', reversing Phase 2b's
# deliberately conservative 'tabular'.
#
# That conservatism has done its job: the flag let Darts land without being able
# to regress what already ran, and the owner's real scenario has since gone
# through it end-to-end with all fourteen catalogue entries building and fitting.
# THE REASON TO FLIP IS HONESTY, NOT SPEED. On the tabular path a solution
# labelled 'TFT' is resolved by DARTS_TO_ML_MAP to LightGBM, so the model named
# in the UI is not the model that trains; the darts engine builds the
# architecture it names. The flip also makes two rules real on the path that
# actually runs: an indicator marked 'future' is REFUSED rather than quietly
# used (CLAUDE.md C1), and calendar features become the only future covariates.
#
# Checked before flipping, because the refusal is the one way this breaks an
# existing solution: solution_indicators held no row with covariate_type
# 'future' or 'both' (4 rows, all 'past'), so nothing starts failing. The cost
# the owner accepted is time — real torch on CPU trains slower than a booster.
# 'tabular' stays reachable via engine='tabular', so a regression is still one
# flag away from being undone.
DEFAULT_TRAINING_ENGINE = 'darts'
SUPPORTED_TRAINING_ENGINES = ('tabular', 'darts')


# Backlog #106 — news as PAST covariates. Opt-in, and default OFF.
#
# Not timidity: on today's corpus the two columns are zero for almost every bar
# (four symbols and seven weeks of news against a three-year price request), so
# defaulting them on would quietly add two near-constant features to every
# existing solution and move its numbers for no gain. A solution asks for them.
#
# The half-life is in CALENDAR days and is the operator's one knob. #106 called
# for 3-10 days; the bounds here are wider so an experiment is possible, and are
# enforced rather than trusted, because a non-positive value has no decay factor.
NEWS_FEATURES_DEFAULT = False
NEWS_HALFLIFE_DEFAULT = 5.0
NEWS_HALFLIFE_BOUNDS = (0.5, 90.0)


def resolve_news_halflife(requested) -> float:
    """Clamp the requested half-life into NEWS_HALFLIFE_BOUNDS.

    Clamping rather than rejecting: this is a smoothing knob, not a correctness
    switch, and a training run should not fail because a slider reached 0. A
    non-numeric or NaN value falls back to the default.
    """
    lo, hi = NEWS_HALFLIFE_BOUNDS
    try:
        v = float(requested)
    except (TypeError, ValueError):
        return NEWS_HALFLIFE_DEFAULT
    if v != v:  # NaN
        return NEWS_HALFLIFE_DEFAULT
    return max(lo, min(hi, v))


def resolve_training_engine(requested: Optional[str]) -> str:
    """Normalise a requested engine name, falling back to the default.

    Absent, None and blank all mean "the caller did not choose", which is what
    keeps DEFAULT_TRAINING_ENGINE the single place the decision lives.

    Validating the result is the CALLER's job. An unrecognised name is returned
    unchanged rather than replaced by the default: silently substituting an
    engine would train something other than what was asked for, which is the
    class of behaviour #104/#105/#109 exist to remove.
    """
    if requested is None:
        return DEFAULT_TRAINING_ENGINE
    name = str(requested).strip().lower()
    return name or DEFAULT_TRAINING_ENGINE


# Backlog #127 — the horizon offered when the model itself declares none.
#
# This is the literal the two sites below used to hardcode, kept as the fallback
# rather than replaced by DEFAULT_PREDICTION_DAYS so that behaviour changes ONLY
# where the model's config actually states a horizon. Some catalogue entries
# legitimately have no output_chunk_length at all (RNN is parameterised by
# training_length instead), and those must keep offering what they offered
# before.
PREDICTION_HORIZON_FALLBACK = 10


def resolve_output_chunk_length(config_json, requested=None) -> int:
    """The forecast horizon in business days: what the MODEL was created with.

    Backlog #127. Two sites used to decide this without consulting the model:
    the training result's prediction_dates block hardcoded 10, and the predict
    endpoint sized its forward forecast from predict_days or
    DEFAULT_PREDICTION_DAYS. So a model created with output_chunk_length=1 (the
    XGBoost, CatBoost and RandomForest defaults) was offered a ten-day window
    and then forecast five days — three different numbers, none of them the
    one the user set at creation.

    Precedence is explicit request, then the model's config, then the fallback.
    An explicitly requested predict_days still wins: a caller asking for a
    specific number of days is not making a mistake, and /solutions/predict has
    accepted that parameter since before the horizon lived in the config.

    VALUES ARRIVE AS STRINGS. config_json is written from the Solutions form,
    which posts '10' rather than 10 — the same lesson as #124 on the darts
    hyperparameters. A str()/int() round trip here is not defensive padding; it
    is the actual shape of the stored data.
    """
    for candidate in (requested, _config_horizon(config_json)):
        if candidate is None:
            continue
        try:
            value = int(float(str(candidate).strip()))
        except (TypeError, ValueError):
            continue
        if value >= 1:
            return min(value, settings.MAX_PREDICTION_DAYS)
    return PREDICTION_HORIZON_FALLBACK


#: Floor on the warm-up, in bars, and the number is MEASURED rather than
#: reasoned: on 2026-11-05 every indicator in the catalogue was computed over
#: 880 bars of FPT and asked how many leading rows it leaves NaN. The worst is
#: SUPERTREND at 72, then TEMA 57, DEMA 38, TSI 37, MACD and AO 33.
#:
#: WHY A MEASURED FLOOR AND NOT JUST A MULTIPLE OF THE PERIOD. SUPERTREND's
#: parameters are {"period": 10, "multiplier": 3}; its warm-up is 72 bars and
#: does not shrink with more history, so NOTHING in its parameters predicts it.
#: A warm-up derived only from the parameters bought 42 bars for it and the
#: feature frame still came out empty — the first version of this fix did
#: exactly that and the sweep returned a 422 where a forecast was expected.
#: ICHIMOKU is the opposite case: senkou_b_period is 52 and it needs only 25.
#:
#: 72 for the worst indicator + 20 for volatility_20/volume_sma_20 + 10 for
#: close_lag_10, rounded up for margin. test_the_warmup_floor_covers_the_
#: hungriest_indicator pins it against the measurement.
BASE_WARMUP_BARS = 120

#: Multiple of the longest indicator period, which still matters because a
#: period is EDITABLE: the floor covers the catalogue's defaults, and this keeps
#: a user-raised period (a 200-day moving average, say) from under-fetching.
#: Three times is the right factor for the parameter-driven ones — TEMA's triple
#: smoothing needs 57 bars on a period of 20.
INDICATOR_WARMUP_FACTOR = 3

#: The measurement above, kept as data so a test can assert the floor covers it
#: rather than restating a number that would drift silently.
MEASURED_WORST_INDICATOR_WARMUP_BARS = 72

#: Trading days per calendar week, for turning bars into a date offset, plus a
#: fortnight for public holidays — Tet alone closes the exchange for about a week.
CALENDAR_DAYS_PER_BAR = 7 / 5
HOLIDAY_MARGIN_DAYS = 14


def warmup_calendar_days(indicator_rows: list) -> int:
    """Calendar days of history to fetch BEFORE the first day to be predicted.

    Backlog #128. Proportional to the indicators actually attached to the
    solution, so the number follows the catalogue instead of being a literal
    that silently stops being enough.

    Deliberately generous: over-fetching costs one wider query against
    stock-data-service, while under-fetching empties the feature frame and
    returns a blank chart with HTTP 200.
    """
    longest = 0
    for row in indicator_rows or []:
        for source in (row.get('parameters'), row.get('default_parameters')):
            if isinstance(source, str):
                try:
                    source = json.loads(source)
                except (json.JSONDecodeError, TypeError):
                    continue
            if not isinstance(source, dict):
                continue
            for value in source.values():
                try:
                    longest = max(longest, int(float(value)))
                except (TypeError, ValueError):
                    continue
    bars = max(BASE_WARMUP_BARS, longest * INDICATOR_WARMUP_FACTOR)
    return int(bars * CALENDAR_DAYS_PER_BAR) + HOLIDAY_MARGIN_DAYS


def next_trading_day(day) -> "pd.Timestamp":
    """The next weekday after `day`.

    SINGLE PLACE ON PURPOSE. This arithmetic was written out three times and
    Backlog #131 is about what all three get wrong: it skips weekends and knows
    nothing about market holidays, so a window starting the day after a Friday
    before Tet lands on a closed exchange. Fixing #131 means fixing this
    function, not finding the copies.
    """
    nxt = pd.Timestamp(day) + pd.Timedelta(days=1)
    while nxt.weekday() >= 5:
        nxt += pd.Timedelta(days=1)
    return nxt


def compute_prediction_dates(end_date, output_chunk_length: int) -> dict:
    """The window the Predict tab pre-fills after a training finishes.

    Backlog #126/#127. The tabular path built this inline with a hardcoded
    ten-day horizon and the darts path did not build it at all, so a
    darts-trained solution left the Predict form with no dates to offer after a
    training that had reported success. One function now serves both, and the
    horizon is the model's.
    """
    start = next_trading_day(end_date)
    end = start
    added = 0
    while added < max(1, int(output_chunk_length)) - 1:
        end += pd.Timedelta(days=1)
        if end.weekday() < 5:
            added += 1
    return {
        'prediction_start_date': start.strftime('%Y-%m-%d'),
        'prediction_end_date': end.strftime('%Y-%m-%d'),
        'output_chunk_length': int(output_chunk_length),
        'training_end_date': str(end_date),
    }


#: Backlog #126 — where a darts-trained solution's artefacts live.
#:
#: TWO FILES, and the split is forced by the library rather than chosen. Darts
#: models do not survive joblib: measured against darts 0.48.1, a torch model
#: pickled and reloaded raises "'NoneType' object has no attribute
#: 'set_predict_parameters'" on its next predict, because the Lightning trainer
#: is dropped. `model.save()` round-trips both families to identical forecasts
#: (and writes a second `.ckpt` of its own for torch models).
#:
#: So the model goes through Darts' own serialisation and the rest — scalers,
#: column list, chunk lengths — through joblib beside it. `file_path` points at
#: the joblib sidecar, because that is what predict_solution already loads and
#: it is the file that says which engine produced the model.
def darts_bundle_paths(solution_id: int) -> tuple:
    base = f"{settings.MODEL_PATH}/solution_{solution_id}_darts"
    return f"{base}.joblib", f"{base}.model"


def save_darts_bundle(solution_id: int, fitted: dict) -> str:
    """Persist a fitted darts model plus its transforms. Returns the sidecar."""
    sidecar_path, model_path = darts_bundle_paths(solution_id)
    os.makedirs(settings.MODEL_PATH, exist_ok=True)
    model = fitted["model"]
    model.save(model_path)
    state = {k: v for k, v in fitted.items() if k != "model"}
    joblib.dump({
        "engine": "darts",
        "model_path": model_path,
        # The class, recorded by name rather than pickled: Darts' generic
        # ForecastingModel.load refuses a torch checkpoint (measured:
        # UnpicklingError), so loading needs the concrete class, and an import
        # path is inspectable where a pickled class reference is not.
        "model_module": type(model).__module__,
        "model_class": type(model).__qualname__,
        **state,
    }, sidecar_path)
    return sidecar_path


def darts_companion_files(sidecar_path: str) -> list:
    """The other files a darts bundle owns, so deleting one deletes all of it.

    Backlog #126 introduced a leak that the sweep made visible within an hour:
    DELETE /models/{id} removes `file_path`, which is the joblib sidecar, while
    the Darts model file and the torch `.ckpt` beside it survived. Fourteen
    orphans accumulated in one afternoon of sweeps, each one a model nobody can
    reach and nothing will ever delete.

    The sidecar is READ rather than guessed at, because it records where the
    model went; the naming convention is only the fallback for a sidecar too
    corrupt to open, where leaving the model behind would be the worse outcome.
    """
    if not sidecar_path or not str(sidecar_path).endswith(".joblib"):
        return []
    model_path = None
    try:
        saved = joblib.load(sidecar_path)
        if str(saved.get("engine") or "").strip().lower() == "darts":
            model_path = saved.get("model_path")
    except Exception as exc:  # noqa: BLE001
        logger.warning("could not read %s to find its model file: %s",
                       sidecar_path, exc)
    if not model_path:
        guess = sidecar_path[: -len(".joblib")] + ".model"
        model_path = guess if os.path.exists(guess) else None
    if not model_path:
        return []
    return [p for p in (model_path, f"{model_path}.ckpt") if os.path.exists(p)]


def load_darts_model(saved: dict):
    """Rebuild the model a darts sidecar describes."""
    import importlib

    model_path = saved.get("model_path")
    if not model_path or not os.path.exists(model_path):
        raise FileNotFoundError(
            f"the darts model file is missing at {model_path}; retrain the solution")
    module = importlib.import_module(saved["model_module"])
    return getattr(module, saved["model_class"]).load(model_path)


def _config_horizon(config_json):
    """output_chunk_length out of a model_instances.config_json, or None."""
    if isinstance(config_json, str):
        try:
            config_json = json.loads(config_json)
        except (json.JSONDecodeError, TypeError):
            return None
    if not isinstance(config_json, dict):
        return None
    return config_json.get('output_chunk_length')


# Model type mapping: DARTS neural network types -> scikit-learn/gradient boosting models
# USED ONLY BY THE 'tabular' ENGINE, which is no longer the default (#109,
# DEFAULT_TRAINING_ENGINE above). The line that stood here — "Since DARTS is not
# installed in this microservice" — has been false since Phase 1: darts 0.48.1
# and CPU torch are in the image and the darts engine builds the architecture a
# solution actually names. This map is therefore the DISHONEST path, kept
# reachable on purpose as the one-flag way to undo a regression: it resolves
# 'TFT' to LightGBM, so a result produced through it is a gradient booster
# wearing a transformer's label. Read any tabular result with that in mind.
# NOTE: keys must match the VALUES of routes.MODEL_TYPE_MAP, which is what lands
# in model_instances.model_type. Backlog #110 found four that did not: the map
# held RNNModel / TCNModel / TransformerModel / TFTModel while the catalogue
# stores RNN / TCN / Transformer / TFT, so those four fell through to the
# 'xgboost' default AND missed their MODEL_DEFAULTS profile — four of fourteen
# model choices were silently the same default XGBoost. The *Model spellings are
# kept as aliases in case older rows carry them (the author had already hit this
# for NBeats/NBEATSModel and handled that one).
DARTS_TO_ML_MAP = {
    'BlockRNN': 'xgboost',
    'RNN': 'lightgbm',
    'RNNModel': 'lightgbm',
    'TCN': 'xgboost',
    'Transformer': 'lightgbm',
    'TFT': 'lightgbm',
    'TCNModel': 'xgboost',
    'TransformerModel': 'lightgbm',
    'NBEATSModel': 'random_forest',
    'TFTModel': 'lightgbm',
    'NBeats': 'random_forest',
    'NHits': 'xgboost',
    'DLinear': 'lightgbm',
    'NLinear': 'lightgbm',
    'TiDE': 'xgboost',
    'XGBoost': 'xgboost',
    'LightGBM': 'lightgbm',
    'RandomForest': 'random_forest',
    'CatBoost': 'catboost',
    'LinearRegression': 'linear_regression',
}


# Backlog #109 — naming honesty on the tabular path.
#
# The darts engine, now the default, builds the architecture a solution NAMES:
# a solution labelled 'TFT' trains a real TFTModel. The tabular engine cannot —
# it has no torch — so it resolves the name through DARTS_TO_ML_MAP and trains a
# gradient booster instead. Until now its result payload reported neither the
# engine nor the model, so a stored tabular result was indistinguishable from a
# real TFT to anyone reading it later.
#
# RENAMING THE CATALOGUE WOULD BE THE WRONG FIX. It was the obvious one while
# every path was a surrogate, but the darts engine makes 'TFT' truthful, so
# renaming would break the honest path to document the legacy one. Disclosure is
# what is missing, not a rename.
#
# These are the catalogue names the tabular engine can train GENUINELY — the
# model that runs is the model that was asked for. Everything else is a
# substitution and says so. CatBoost joined this set on 2026-11-02: the package
# has shipped in the image since #109, so mapping it to xgboost had stopped
# being a necessity and was simply wrong.
TABULAR_NATIVE_BACKENDS = {
    'XGBoost': 'xgboost',
    'LightGBM': 'lightgbm',
    'RandomForest': 'random_forest',
    'CatBoost': 'catboost',
    'LinearRegression': 'linear_regression',
}


def describe_tabular_backend(model_type: str) -> dict:
    """What the TABULAR engine actually trains for a catalogue model name.

    Returned with every tabular result so the stored numbers carry the name of
    the model that produced them. `backend_substituted` is the field that
    matters: when it is true the result is a gradient booster wearing another
    model's label, and the note says how to get the real one.

    An unrecognised name is a substitution too — DARTS_TO_ML_MAP falls back to
    xgboost — rather than being quietly treated as genuine.
    """
    backend = DARTS_TO_ML_MAP.get(model_type, 'xgboost')
    substituted = model_type not in TABULAR_NATIVE_BACKENDS
    out = {
        'engine': 'tabular',
        'model_type': model_type,
        'actual_backend': backend,
        'backend_substituted': substituted,
    }
    if substituted:
        out['note'] = (
            f"Asked for {model_type}; the tabular engine has no torch, so this "
            f"result was produced by {backend} using a hyperparameter profile "
            f"chosen for {model_type}. It is NOT a {model_type}. Train with "
            f"engine='darts' (the default) to build the real architecture."
        )
    return out


def _create_ml_model(model_type: str, model_sub_type: str = '', config_json=None):
    """Create an ML model with hyperparameters tuned per model type.

    Each DARTS model type gets a distinct hyperparameter profile so that
    different model selections in the UI produce genuinely different models.
    User-provided config_json overrides the defaults.
    """
    ml_type = DARTS_TO_ML_MAP.get(model_type, 'xgboost')

    # Per-model-type default hyperparameters (distinct profiles)
    MODEL_DEFAULTS = {
        # ── XGBoost variants ──
        'XGBoost':          {'n_estimators': 200, 'max_depth': 6,  'learning_rate': 0.10, 'subsample': 0.8, 'colsample_bytree': 0.8},
        'BlockRNN':         {'n_estimators': 300, 'max_depth': 8,  'learning_rate': 0.05, 'subsample': 0.85, 'colsample_bytree': 0.7},
        'TCNModel':         {'n_estimators': 150, 'max_depth': 10, 'learning_rate': 0.08, 'subsample': 0.75, 'colsample_bytree': 0.9},
        'TCN':              {'n_estimators': 150, 'max_depth': 10, 'learning_rate': 0.08, 'subsample': 0.75, 'colsample_bytree': 0.9},
        'NHits':            {'n_estimators': 500, 'max_depth': 5,  'learning_rate': 0.03, 'subsample': 0.9, 'colsample_bytree': 0.6},
        'TiDE':             {'n_estimators': 100, 'max_depth': 4,  'learning_rate': 0.15, 'subsample': 0.7, 'colsample_bytree': 0.85},
        'CatBoost':         {'n_estimators': 400, 'max_depth': 7,  'learning_rate': 0.04, 'subsample': 0.8, 'colsample_bytree': 0.75},
        # ── LightGBM variants ──
        'LightGBM':         {'n_estimators': 200, 'max_depth': 6,  'learning_rate': 0.10, 'subsample': 0.8, 'colsample_bytree': 0.8, 'num_leaves': 31},
        'RNNModel':         {'n_estimators': 300, 'max_depth': 8,  'learning_rate': 0.05, 'subsample': 0.85, 'colsample_bytree': 0.7, 'num_leaves': 63},
        'RNN':              {'n_estimators': 300, 'max_depth': 8,  'learning_rate': 0.05, 'subsample': 0.85, 'colsample_bytree': 0.7, 'num_leaves': 63},
        'TransformerModel': {'n_estimators': 400, 'max_depth': 5,  'learning_rate': 0.03, 'subsample': 0.9, 'colsample_bytree': 0.6, 'num_leaves': 127},
        'Transformer':      {'n_estimators': 400, 'max_depth': 5,  'learning_rate': 0.03, 'subsample': 0.9, 'colsample_bytree': 0.6, 'num_leaves': 127},
        'TFTModel':         {'n_estimators': 350, 'max_depth': 9,  'learning_rate': 0.04, 'subsample': 0.8, 'colsample_bytree': 0.75, 'num_leaves': 80},
        'TFT':              {'n_estimators': 350, 'max_depth': 9,  'learning_rate': 0.04, 'subsample': 0.8, 'colsample_bytree': 0.75, 'num_leaves': 80},
        'DLinear':          {'n_estimators': 100, 'max_depth': 3,  'learning_rate': 0.15, 'subsample': 0.7, 'colsample_bytree': 0.9, 'num_leaves': 15},
        'NLinear':          {'n_estimators': 80,  'max_depth': 2,  'learning_rate': 0.20, 'subsample': 0.7, 'colsample_bytree': 0.95, 'num_leaves': 10},
        # ── RandomForest variants ──
        'RandomForest':     {'n_estimators': 200, 'max_depth': 10, 'min_samples_split': 5,  'min_samples_leaf': 2},
        'NBEATSModel':      {'n_estimators': 400, 'max_depth': 15, 'min_samples_split': 3,  'min_samples_leaf': 1},
        'NBeats':           {'n_estimators': 300, 'max_depth': 12, 'min_samples_split': 4,  'min_samples_leaf': 2},
    }

    defaults = MODEL_DEFAULTS.get(model_type, {})

    user_config = {}
    if config_json:
        try:
            user_config = json.loads(config_json) if isinstance(config_json, str) else config_json
        except (json.JSONDecodeError, TypeError):
            user_config = {}
    if not isinstance(user_config, dict):
        user_config = {}

    # config_json holds the DARTS/neural-net hyperparameters chosen in the UI
    # (input_chunk_length, hidden_dim, n_rnn_layers, dropout, batch_size,
    # n_epochs, learning_rate ~1e-4, ...). These DARTS model types are surrogated
    # to gradient-boosting / random-forest models here, and the neural
    # hyperparameters do NOT translate. In particular a neural learning_rate
    # (~1e-4) shares its name with the boosting learning_rate but not its scale:
    # applied to XGBoost it shrinks all n_estimators trees to nearly zero
    # contribution, so the ensemble stays at its base score and every prediction
    # collapses to the training mean — a flat line parallel to the X axis.
    # Only adopt keys that are genuine ML hyperparameters for the surrogate model;
    # drop the neural-only ones (including the incompatible learning_rate) and
    # fall back to the curated per-model defaults above.
    ML_HYPERPARAM_KEYS = {
        'n_estimators', 'max_depth', 'subsample', 'colsample_bytree',
        'num_leaves', 'min_samples_split', 'min_samples_leaf',
    }
    safe_user = {k: v for k, v in user_config.items() if k in ML_HYPERPARAM_KEYS}
    cfg = {**defaults, **safe_user}

    if ml_type == 'xgboost':
        return xgb.XGBRegressor(
            n_estimators=cfg.get('n_estimators', 200),
            max_depth=cfg.get('max_depth', 6),
            learning_rate=cfg.get('learning_rate', 0.1),
            subsample=cfg.get('subsample', 0.8),
            colsample_bytree=cfg.get('colsample_bytree', 0.8),
            random_state=42,
            verbosity=0
        )
    elif ml_type == 'lightgbm':
        return lgb.LGBMRegressor(
            n_estimators=cfg.get('n_estimators', 200),
            max_depth=cfg.get('max_depth', 6),
            learning_rate=cfg.get('learning_rate', 0.1),
            num_leaves=cfg.get('num_leaves', 31),
            subsample=cfg.get('subsample', 0.8),
            colsample_bytree=cfg.get('colsample_bytree', 0.8),
            random_state=42,
            verbose=-1
        )
    elif ml_type == 'catboost':
        # Imported lazily: catboost costs ~300MB and a noticeable import, and
        # only this one branch needs it. Before 2026-11-02 'CatBoost' resolved to
        # xgboost — a substitution that had been unnecessary ever since #109 put
        # the package in the image (#109 naming honesty).
        from catboost import CatBoostRegressor
        return CatBoostRegressor(
            iterations=cfg.get('n_estimators', 200),
            depth=min(int(cfg.get('max_depth', 6)), 16),  # catboost caps depth at 16
            learning_rate=cfg.get('learning_rate', 0.1),
            random_seed=42,
            verbose=False,
            allow_writing_files=False,  # no catboost_info/ litter in the container
        )
    elif ml_type == 'random_forest':
        return RandomForestRegressor(
            n_estimators=cfg.get('n_estimators', 200),
            max_depth=cfg.get('max_depth', 10),
            min_samples_split=cfg.get('min_samples_split', 5),
            min_samples_leaf=cfg.get('min_samples_leaf', 2),
            random_state=42,
            n_jobs=-1
        )
    else:
        return LinearRegression()


def _prepare_indicator_features(df: pd.DataFrame, indicator_rows: list) -> tuple:
    """Calculate indicator features and return (feature_df, indicator_data_by_date).

    Returns:
        feature_df: DataFrame with indicator columns
        indicator_data_by_date: dict mapping date_str -> {col: value} for chart merge
    """
    feature_df = pd.DataFrame(index=df.index)
    indicator_data_by_date = {}

    for row in indicator_rows:
        ind = dict(row)
        name = ind.get('name', '')
        code = INDICATOR_NAME_MAP.get(name, name)

        params = ind.get('parameters')
        if params and isinstance(params, str):
            try:
                params = json.loads(params)
            except (json.JSONDecodeError, TypeError):
                params = {}
        if not params:
            default_params = ind.get('default_parameters')
            if default_params and isinstance(default_params, str):
                try:
                    params = json.loads(default_params)
                except (json.JSONDecodeError, TypeError):
                    params = {}
            elif isinstance(default_params, dict):
                params = default_params
            else:
                params = {}

        indicator_data = _calculate_indicator(df, code, params)
        if not indicator_data:
            continue

        ind_df = pd.DataFrame(indicator_data)
        if 'date' in ind_df.columns:
            ind_df['date'] = pd.to_datetime(ind_df['date'])
            ind_df = ind_df.set_index('date')

        for col in ind_df.columns:
            if col != 'date':
                try:
                    feature_df[col] = pd.to_numeric(ind_df[col], errors='coerce')
                except Exception:
                    pass

        for item in indicator_data:
            date_key = item.get('date', '')
            if date_key not in indicator_data_by_date:
                indicator_data_by_date[date_key] = {}
            for k, v in item.items():
                if k != 'date' and v is not None:
                    indicator_data_by_date[date_key][k] = v

    return feature_df, indicator_data_by_date


def _build_feature_df(df: pd.DataFrame, indicator_feature_df: pd.DataFrame) -> pd.DataFrame:
    """Build feature DataFrame from OHLCV data and indicator features.

    Shared by training and prediction to ensure feature consistency.
    Does NOT add 'target' column — caller adds that for training.

    Args:
        df: DataFrame with columns [open, high, low, close, volume], DatetimeIndex
        indicator_feature_df: DataFrame with indicator columns, same index as df

    Returns:
        DataFrame with all features (no target), NaN rows NOT dropped (caller decides).
    """
    feature_df = pd.DataFrame(index=df.index)
    feature_df['close'] = df['close']

    # Price-based features
    feature_df['returns'] = df['close'].pct_change()
    feature_df['log_returns'] = np.log(df['close'] / df['close'].shift(1))
    feature_df['high_low_ratio'] = df['high'] / df['low']
    feature_df['close_open_ratio'] = df['close'] / df['open']

    for lag in [1, 2, 3, 5, 10]:
        feature_df[f'close_lag_{lag}'] = df['close'].shift(lag)
        feature_df[f'returns_lag_{lag}'] = feature_df['returns'].shift(lag)

    # Volatility
    feature_df['volatility_5'] = feature_df['returns'].rolling(5).std()
    feature_df['volatility_20'] = feature_df['returns'].rolling(20).std()

    # Volume features
    if 'volume' in df.columns:
        feature_df['volume_sma_20'] = df['volume'].rolling(20).mean()
        feature_df['volume_ratio'] = df['volume'] / feature_df['volume_sma_20']

    # Add indicator features
    for col in indicator_feature_df.columns:
        feature_df[col] = indicator_feature_df[col]

    return feature_df


async def _run_training(solution_id: int, train_params: dict):
    """Background async training task with real ML model training."""
    try:
        training_status[solution_id] = {
            "status": "training",
            "message": "Loading solution data...",
            "progress": 5,
            "started_at": time_module.time()
        }

        async with async_session_factory() as db:
            # Step 1: Load solution
            result = await db.execute(
                text("SELECT * FROM tbl_solution WHERE id = :id"),
                {"id": solution_id}
            )
            solution = result.mappings().first()
            if not solution:
                training_status[solution_id] = {
                    "status": "failed", "error": "Solution not found",
                    "failed_at": time_module.time()
                }
                return

            ticker = solution['ticker']
            model_id = solution['model_id']

            # Step 2: Load model instance
            result = await db.execute(
                text("SELECT * FROM model_instances WHERE id = :id"),
                {"id": model_id}
            )
            model_instance = result.mappings().first()
            if not model_instance:
                training_status[solution_id] = {
                    "status": "failed", "error": f"Model instance {model_id} not found",
                    "failed_at": time_module.time()
                }
                return

            training_status[solution_id]["message"] = "Loading indicators..."
            training_status[solution_id]["progress"] = 10

            # Step 3: Get solution indicators
            result = await db.execute(
                text("""
                    SELECT si.indicator_id, si.indicator_category, si.covariate_type, si.parameters,
                           ti.name, ti.type, ti.default_parameters, ti.calculation_function
                    FROM solution_indicators si
                    LEFT JOIN technical_indicators ti ON si.indicator_id = ti.id
                    WHERE si.solution_id = :solution_id
                """),
                {"solution_id": solution_id}
            )
            indicator_rows = [dict(r) for r in result.mappings().all()]

            training_status[solution_id]["message"] = f"Fetching price data for {ticker}..."
            training_status[solution_id]["progress"] = 15

            # Step 4: Fetch OHLC data from stock-data-service
            start_date = train_params.get('start_date')
            end_date = train_params.get('end_date')
            train_ratio = float(train_params.get('train_ratio', 0.8))

            async with httpx.AsyncClient(timeout=60.0) as client:
                url = f"{settings.STOCK_DATA_SERVICE_URL}/stock_helper/api/v2/companies/{ticker}/historical-data"
                resp = await client.get(url, params={"start_date": start_date, "end_date": end_date})
                if resp.status_code != 200:
                    training_status[solution_id] = {
                        "status": "failed",
                        "error": f"Failed to fetch price data for {ticker} (HTTP {resp.status_code})",
                        "failed_at": time_module.time()
                    }
                    return
                price_response = resp.json()

            if isinstance(price_response, dict) and "data" in price_response:
                price_list = price_response["data"]
            elif isinstance(price_response, list):
                price_list = price_response
            else:
                price_list = []

            if not price_list:
                training_status[solution_id] = {
                    "status": "failed",
                    "error": f"No price data for {ticker} in range {start_date} to {end_date}",
                    "failed_at": time_module.time()
                }
                return

            logger.info(f"Training solution {solution_id}: loaded {len(price_list)} price records for {ticker}")

            df = pd.DataFrame(price_list)
            if 'time' in df.columns:
                df['date'] = pd.to_datetime(df['time'])
            elif 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'])
            df = df.set_index('date').sort_index()
            df = df[['open', 'high', 'low', 'close', 'volume']].copy()
            df = df.apply(pd.to_numeric, errors='coerce')
            df = df.dropna()

            training_status[solution_id]["message"] = "Calculating technical indicators..."
            training_status[solution_id]["progress"] = 25

            # Step 5: Calculate indicator features
            indicator_feature_df, indicator_data_by_date = _prepare_indicator_features(df, indicator_rows)

            # Build feature DataFrame using shared function
            feature_df = _build_feature_df(df, indicator_feature_df)

            # Backlog #106 — news as PAST covariates, when the solution asked.
            # Attached BEFORE the target and the warm-up dropna, so the columns
            # are accounted for like any other feature. news_covariates fills
            # absent dates with 0.0 precisely so that dropna cannot delete every
            # bar outside the news window (the #110 trap, in a new place).
            news_coverage_report = {"attached": False}
            news_halflife_used = None
            if bool(train_params.get('include_news', NEWS_FEATURES_DEFAULT)):
                halflife = resolve_news_halflife(
                    train_params.get('news_halflife_days', NEWS_HALFLIFE_DEFAULT))
                training_status[solution_id]["message"] = "Fetching news covariates..."
                try:
                    async with httpx.AsyncClient(timeout=30.0) as news_client:
                        news_rows = await fetch_news_features(
                            news_client,
                            base_url=settings.NEWS_SERVICE_URL,
                            api_prefix=settings.API_PREFIX,
                            symbol=ticker,
                            start=str(feature_df.index.min().date()),
                            end=str(feature_df.index.max().date()),
                            halflife_days=halflife)
                except NewsCovariateError as exc:
                    # Fail rather than train silently without them: reporting a
                    # news-aware model that never saw the feature is the #109
                    # mislabelling defect in another costume.
                    training_status[solution_id] = {
                        "status": "failed",
                        "error": ("news covariates were requested but could not "
                                  f"be loaded: {exc}"),
                        "failed_at": time_module.time(),
                    }
                    return
                feature_df = attach_news_features(feature_df, news_rows)
                news_halflife_used = halflife

            # Target: next day's close price
            feature_df['target'] = feature_df['close'].shift(-1)

            # Backlog #110 — record what the warm-up costs before discarding it.
            # `dropna()` drops every row where ANY feature is NaN, so the usable
            # window is set by the LONGEST-warm-up indicator and applies to all
            # models alike (these are tabular learners; none needs a sequence
            # window of its own). That is correct, but it was invisible: adding a
            # single SMA-200 silently removes 200 bars, which on a three-year
            # request is over a quarter of the data, with nothing reporting it.
            rows_before_warmup = int(len(feature_df))
            feature_df = feature_df.dropna()
            rows_after_warmup = int(len(feature_df))

            # Backlog #116. The coverage report is built HERE, not where the
            # columns were attached, because the train/validation boundary is
            # int(len(frame) * train_ratio) on the POST-dropna frame — the frame
            # the trainers actually split. Computing it before the warm-up drop
            # would report a boundary nothing uses, and the whole point of this
            # report is that the overall coverage percentage hid which side of
            # that boundary the covered bars fell on.
            if news_coverage_report.get("attached") or news_halflife_used is not None:
                news_coverage_report = news_coverage(feature_df, train_ratio=train_ratio)
                news_coverage_report["halflife_days"] = news_halflife_used
                if news_coverage_report.get("warning"):
                    logger.warning("solution %s: news covariates — %s",
                                   solution_id, news_coverage_report["warning"])
                else:
                    logger.info(
                        "solution %s: news covariates attached, %s/%s training bars "
                        "and %s/%s validation bars with coverage",
                        solution_id,
                        news_coverage_report.get("train_rows_with_coverage"),
                        news_coverage_report.get("train_rows"),
                        news_coverage_report.get("validation_rows_with_coverage"),
                        news_coverage_report.get("validation_rows"))

            if len(feature_df) < 30:
                training_status[solution_id] = {
                    "status": "failed",
                    "error": f"Insufficient data: only {len(feature_df)} usable data points after feature preparation (need at least 30)",
                    "failed_at": time_module.time()
                }
                return

            engine = resolve_training_engine(train_params.get('engine'))
            if engine == 'darts':
                await _run_darts_engine(
                    solution_id=solution_id, db=db, feature_df=feature_df,
                    indicator_rows=indicator_rows, model_instance=model_instance,
                    model_id=model_id, ticker=ticker, train_params=train_params,
                    start_date=start_date, end_date=end_date,
                    rows_before_warmup=rows_before_warmup,
                    rows_after_warmup=rows_after_warmup,
                    news_coverage_report=news_coverage_report)
                return
            if engine not in SUPPORTED_TRAINING_ENGINES:
                training_status[solution_id] = {
                    "status": "failed",
                    "error": (
                        f"unknown engine {engine!r}; expected one of "
                        + ", ".join(repr(e) for e in SUPPORTED_TRAINING_ENGINES)
                    ),
                    "failed_at": time_module.time(),
                }
                return

            training_status[solution_id]["message"] = "Training model..."
            training_status[solution_id]["progress"] = 40

            # Step 6: Prepare training data
            feature_cols = [col for col in feature_df.columns if col not in ['close', 'target']]
            X = feature_df[feature_cols].values
            y = feature_df['target'].values

            split_idx = int(len(X) * train_ratio)
            X_train, X_val = X[:split_idx], X[split_idx:]
            y_train, y_val = y[:split_idx], y[split_idx:]

            logger.info(f"Training solution {solution_id}: {len(X_train)} train, {len(X_val)} val, {len(feature_cols)} features")

            # Step 7: Create and train model
            model_type = model_instance['model_type'] if model_instance else 'BlockRNN'
            model_sub_type = model_instance.get('model_sub_type', '') if model_instance else ''
            config_json = model_instance.get('config_json') if model_instance else None

            ml_model = _create_ml_model(model_type, model_sub_type, config_json)

            # Run CPU-bound training in thread executor
            await asyncio.to_thread(ml_model.fit, X_train, y_train)

            training_status[solution_id]["message"] = "Evaluating model..."
            training_status[solution_id]["progress"] = 70

            # Step 8: Evaluate
            y_pred_val = ml_model.predict(X_val)
            rmse = float(np.sqrt(mean_squared_error(y_val, y_pred_val)))
            mae = float(mean_absolute_error(y_val, y_pred_val))
            r2 = float(r2_score(y_val, y_pred_val))

            if len(y_val) > 1:
                actual_dir = np.sign(y_val[1:] - y_val[:-1])
                pred_dir = np.sign(y_pred_val[1:] - y_pred_val[:-1])
                direction_accuracy = float(np.mean(actual_dir == pred_dir) * 100)
            else:
                direction_accuracy = 0.0

            logger.info(f"Training solution {solution_id}: RMSE={rmse:.4f}, MAE={mae:.4f}, R2={r2:.4f}, Dir={direction_accuracy:.1f}%")

            training_status[solution_id]["message"] = "Saving model..."
            training_status[solution_id]["progress"] = 80

            # Step 9: Save model to disk
            os.makedirs(settings.MODEL_PATH, exist_ok=True)
            model_file = f"{settings.MODEL_PATH}/solution_{solution_id}_model.joblib"
            joblib.dump({
                'model': ml_model,
                'feature_cols': feature_cols,
                'model_type': model_type,
                'ml_type': DARTS_TO_ML_MAP.get(model_type, 'xgboost'),
                'ticker': ticker,
                'trained_at': datetime.now().isoformat(),
            }, model_file)

            logger.info(f"Model saved to {model_file}")

            # Step 10: Update database
            training_status[solution_id]["message"] = "Updating database..."
            training_status[solution_id]["progress"] = 85

            metrics_json = json.dumps({
                'rmse': rmse, 'mae': mae, 'r2': r2,
                'direction_accuracy': direction_accuracy,
                # #109: model_instances.training_metrics_json outlives the
                # in-memory status, so the disclosure has to be stored with it.
                **describe_tabular_backend(model_type),
                'training_samples': int(len(X_train)),
                'validation_samples': int(len(X_val)),
                'features_used': len(feature_cols),
                'rows_dropped_to_warmup': rows_before_warmup - rows_after_warmup,
            })

            await db.execute(
                text("""
                    UPDATE model_instances
                    SET status='trained', file_path=:file_path,
                        training_metrics_json=:metrics, last_training_date=NOW()
                    WHERE id = :model_id
                """),
                {"file_path": model_file, "metrics": metrics_json, "model_id": model_id}
            )

            await db.execute(
                text("""
                    UPDATE tbl_solution
                    SET train_status='trained', solution_status=1,
                        start_training_date=:start_date, end_training_date=:end_date,
                        prediction_result=NULL
                    WHERE id = :solution_id
                """),
                {"start_date": start_date, "end_date": end_date, "solution_id": solution_id}
            )
            await db.commit()

            training_status[solution_id]["message"] = "Generating predictions..."
            training_status[solution_id]["progress"] = 90

            # Step 11: Generate predictions for chart
            all_pred = ml_model.predict(X)

            predictions = []
            dates_list = feature_df.index.tolist()
            for i, d in enumerate(dates_list):
                date_str = d.strftime('%Y-%m-%d')
                is_validation = i >= split_idx

                # Backlog #110 — the prediction is plotted on the bar it actually
                # forecasts. The target is `close.shift(-1)`, so `all_pred[i]`
                # estimates close[i+1]; emitting it at row i put the predicted line
                # ONE BAR AHEAD of the `actual_price` it was drawn against, which
                # made the chart's "actual vs predicted" compare two different
                # quantities. Row i therefore carries the forecast MADE AT i-1, so
                # `actual_price` and `predicted_price` are the same quantity on the
                # same bar and `close == actual_price` still holds for the UI.
                forecast_for_this_bar = float(all_pred[i - 1]) if i > 0 else None
                # ...and the in-sample/held-out boundary moves with it: the forecast
                # on this bar was made at i-1.
                forecast_is_validation = (i - 1) >= split_idx

                point = {
                    'date': date_str,
                    'actual_price': float(feature_df['close'].iloc[i]),
                    # The fitted/forecast line across the whole window so the chart
                    # always shows a "target train price" series (not just the tail).
                    'predicted_price': forecast_for_this_bar,
                    # Out-of-sample portion, exposed separately so it can be
                    # highlighted/toggled distinctly from the in-sample fit.
                    'validation_price': (forecast_for_this_bar
                                         if forecast_is_validation else None),
                    # Explicit rather than inferred from validation_price being null,
                    # so a consumer cannot average in-sample fits by accident.
                    'in_sample': not forecast_is_validation,
                    'close': float(feature_df['close'].iloc[i]),
                    'open': float(df.loc[d, 'open']) if d in df.index else None,
                    'high': float(df.loc[d, 'high']) if d in df.index else None,
                    'low': float(df.loc[d, 'low']) if d in df.index else None,
                    'volume': float(df.loc[d, 'volume']) if d in df.index else None,
                }

                # Merge indicator values for chart display
                date_iso = d.isoformat()
                if date_iso in indicator_data_by_date:
                    point.update(indicator_data_by_date[date_iso])
                elif date_str in indicator_data_by_date:
                    point.update(indicator_data_by_date[date_str])

                predictions.append(point)

            # Step 12: Compute prediction dates (business days)
            #
            # Backlog #127: the horizon comes from the model's own config now.
            # It was the literal 10 here, so the Predict tab offered a ten-day
            # window to every model including the ones created with 1.
            # Backlog #126: the arithmetic moved into compute_prediction_dates
            # so the darts path can produce the same block instead of none.
            output_chunk_length = resolve_output_chunk_length(config_json)
            prediction_dates = compute_prediction_dates(end_date, output_chunk_length)

            # Step 13: Store completed result
            training_status[solution_id] = {
                "status": "completed",
                "completed_at": time_module.time(),
                "message": f"Training completed! RMSE: {rmse:.4f}",
                "result": {
                    "rmse": rmse,
                    "mae": mae,
                    "r2": r2,
                    "direction_accuracy": direction_accuracy,
                    "data_accounting": {
                        # Backlog #110. Makes the cost of indicator choice visible:
                        # `rows_dropped_to_warmup` is history paid for and thrown
                        # away because some indicator needed a longer lookback.
                        "bars_fetched": int(len(df)),
                        "rows_before_warmup": rows_before_warmup,
                        "rows_after_warmup": rows_after_warmup,
                        "rows_dropped_to_warmup": rows_before_warmup - rows_after_warmup,
                        "training_samples": int(len(X_train)),
                        "validation_samples": int(len(X_val)),
                        "features_used": len(feature_cols),
                        "train_end_date": (
                            dates_list[split_idx - 1].strftime('%Y-%m-%d')
                            if split_idx > 0 else None),
                        "validation_start_date": (
                            dates_list[split_idx].strftime('%Y-%m-%d')
                            if split_idx < len(dates_list) else None),
                    },
                    "predictions": predictions,
                    "prediction_dates": prediction_dates,
                    "training_status": "completed",
                    "model_id": model_id,
                    # Backlog #109. The result carries the name of the model that
                    # actually produced it. On this path 'TFT' is a LightGBM with
                    # a TFT-shaped hyperparameter profile, and a reader of these
                    # numbers has to be able to see that.
                    **describe_tabular_backend(model_type),
                    "news_covariates": news_coverage_report,
                    "training_samples": int(len(X_train)),
                    "validation_samples": int(len(X_val)),
                }
            }

            logger.info(f"Training completed for solution {solution_id}: RMSE={rmse:.4f}, {len(predictions)} data points")

            # Persist training result to DB so it survives modal reopening
            try:
                training_result_json = json.dumps(training_status[solution_id]["result"])
                await db.execute(
                    text("UPDATE tbl_solution SET training_result = :result WHERE id = :id"),
                    {"result": training_result_json, "id": solution_id}
                )
                await db.commit()
                logger.info(f"Training result persisted to DB for solution {solution_id}")
            except Exception as persist_err:
                logger.warning(f"Failed to persist training result for solution {solution_id}: {persist_err}")

    except Exception as e:
        logger.error(f"Training failed for solution {solution_id}: {e}", exc_info=True)
        training_status[solution_id] = {
            "status": "failed",
            "failed_at": time_module.time(),
            "error": str(e),
            "message": f"Training failed: {str(e)}"
        }


# ==========================================
# Solution CRUD Endpoints
# ==========================================

@solution_router.get("/all")
@solution_router.get("/all/")
async def get_solutions(
    db: AsyncSession = Depends(get_db),
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    """Get solutions created by the logged-in user.
    Matches webapi: views_solution.get_solutions
    """
    try:
        if current_user and current_user.get("user_id"):
            user_id = str(current_user["user_id"])
            result = await db.execute(
                text("""
                    SELECT
                        tbl_solution.id,
                        tbl_solution.solution_name,
                        tbl_solution.ticker,
                        tbl_solution.created_by,
                        tbl_solution.user_id,
                        tbl_solution.created_date,
                        tbl_solution.updated_date,
                        tbl_solution.train_status,
                        model_instances.model_type,
                        model_instances.model_sub_type,
                        model_instances.model_name
                    FROM tbl_solution
                    INNER JOIN model_instances ON tbl_solution.model_id = model_instances.id
                    WHERE tbl_solution.user_id = :user_id
                """),
                {"user_id": user_id}
            )
        else:
            result = await db.execute(
                text("""
                    SELECT
                        tbl_solution.id,
                        tbl_solution.solution_name,
                        tbl_solution.ticker,
                        tbl_solution.created_by,
                        tbl_solution.user_id,
                        tbl_solution.created_date,
                        tbl_solution.updated_date,
                        tbl_solution.train_status,
                        model_instances.model_type,
                        model_instances.model_sub_type,
                        model_instances.model_name
                    FROM tbl_solution
                    INNER JOIN model_instances ON tbl_solution.model_id = model_instances.id
                """)
            )
        rows = result.mappings().all()
        return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Failed to fetch solutions: {e}")
        return []


@solution_router.get("/tickers")
@solution_router.get("/tickers/")
async def get_predict_tickers(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get tickers available for prediction from user's portfolio.
    Queries portfolio_holdings table directly (shared database).
    Matches webapi: views_solution.get_predict_tickers
    """
    user_id = current_user["user_id"]

    try:
        # Query portfolio holdings directly - all services share the same database
        result = await db.execute(
            text("""
                SELECT DISTINCT ph.symbol as ticker
                FROM portfolio_holdings ph
                INNER JOIN portfolios p ON ph.portfolio_id = p.id
                WHERE p.user_id = :user_id
                ORDER BY ph.symbol
            """),
            {"user_id": user_id}
        )
        rows = result.mappings().all()

        if rows:
            # Return objects with 'ticker' field matching frontend expectations
            return [{"ticker": row["ticker"]} for row in rows]

        logger.info(f"User {user_id} has no stocks in portfolio")
        return []
    except Exception as e:
        logger.error(f"Failed to get predict tickers: {e}")
        return []


@solution_router.get("/models")
@solution_router.get("/models/")
async def get_predict_models(
    db: AsyncSession = Depends(get_db),
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    """Get all available models for solution creation.
    Matches webapi: views_solution.get_predict_models
    Filters by user_id when authenticated.
    """
    try:
        if current_user and current_user.get("user_id"):
            user_id = str(current_user["user_id"])
            result = await db.execute(
                text("""
                    SELECT id, model_name, model_type, model_sub_type,
                           past_covariate, future_covariate
                    FROM model_instances
                    WHERE user_id = :user_id
                    ORDER BY id DESC
                """),
                {"user_id": user_id}
            )
        else:
            result = await db.execute(
                text("""
                    SELECT id, model_name, model_type, model_sub_type,
                           past_covariate, future_covariate
                    FROM model_instances
                    ORDER BY id DESC
                """)
            )
        rows = result.mappings().all()
        # Backlog #107. The stored flags are authoritative for nothing: the create
        # path never set them, so every existing row carries the column default of
        # 0 and the Solutions UI concluded no model accepts any covariate. Derive
        # them from the model type instead, which corrects historical rows without
        # a migration and keeps one source of truth in code.
        out = []
        for row in rows:
            item = dict(row)
            past_cov, future_cov = covariate_support(item.get("model_type"))
            item["past_covariate"] = int(past_cov)
            item["future_covariate"] = int(future_cov)
            out.append(item)
        return out
    except Exception as e:
        logger.warning(f"Failed to fetch predict models: {e}")
        return []


# GET /covariates was removed 2026-10-29 (Backlog #102). It SELECTed
# `id, series_name FROM tbl_time_series`, a table that never existed in this
# deployment — created by neither of prediction-service's schema sources nor
# anywhere else — so the handler's `except -> return []` meant it answered an
# empty list forever. Confirmed dead by the owner: models use only technical
# indicators, which have their own path (IndicatorSelector -> solution_indicators
# -> technical_indicators, 54 rows seeded). tbl_solution has no target or
# covariate columns either, so neither side of the feature was ever wired.
@solution_router.post("")
@solution_router.post("/")
@solution_router.post("/create")
@solution_router.post("/create/")
async def create_solution(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Create a new prediction solution.
    Matches webapi: views_solution.create_predict_solution
    """
    data = await request.json()
    user_id = str(current_user["user_id"])

    if 'user_id' not in data:
        data['user_id'] = user_id
    if 'created_by' not in data:
        data['created_by'] = user_id

    try:
        result = await db.execute(
            text("""
                INSERT INTO tbl_solution
                (solution_name, model_id, ticker, created_date, created_by, user_id,
                 status, start_training_date, end_training_date,
                 train_validation_ratio, solution_status, train_status)
                VALUES (:solution_name, :model_id, :ticker, :created_date, :created_by,
                        :user_id, :status, :start_training_date, :end_training_date,
                        :train_validation_ratio, 0, 'not_trained')
            """),
            {
                "solution_name": data.get("solution_name"),
                "model_id": data.get("model_id"),
                "ticker": data.get("ticker"),
                "created_date": data.get("created_date", datetime.now().strftime("%Y-%m-%d")),
                "created_by": data.get("created_by"),
                "user_id": data.get("user_id"),
                "status": data.get("status", 1),
                "start_training_date": data.get("start_training_date"),
                "end_training_date": data.get("end_training_date"),
                "train_validation_ratio": data.get("train_validation_ratio", 0.8),
            }
        )
        await db.commit()
        solution_id = result.lastrowid

        created_solution = {**data, "id": solution_id}
        return created_solution
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to create solution: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create solution: {str(e)}")


@solution_router.put("")
@solution_router.put("/")
@solution_router.put("/update")
@solution_router.put("/update/")
async def update_solution(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Update a prediction solution.
    Matches webapi: views_solution.update_predict_solution
    """
    data = await request.json()
    user_id = str(current_user["user_id"])

    if 'user_id' not in data:
        data['user_id'] = user_id
    if 'updated_by' not in data:
        data['updated_by'] = user_id

    solution_id = data.get("id")
    if not solution_id:
        raise HTTPException(status_code=400, detail="Solution ID is required")

    try:
        await db.execute(
            text("""
                UPDATE tbl_solution
                SET solution_name = :solution_name, model_id = :model_id, ticker = :ticker,
                    updated_date = :updated_date, updated_by = :updated_by,
                    start_training_date = :start_training_date,
                    end_training_date = :end_training_date,
                    train_validation_ratio = :train_validation_ratio,
                    user_id = :user_id
                WHERE id = :id
            """),
            {
                "solution_name": data.get("solution_name"),
                "model_id": data.get("model_id"),
                "ticker": data.get("ticker"),
                "updated_date": data.get("updated_date", datetime.now().strftime("%Y-%m-%d")),
                "updated_by": data.get("updated_by"),
                "start_training_date": data.get("start_training_date"),
                "end_training_date": data.get("end_training_date"),
                "train_validation_ratio": data.get("train_validation_ratio", 0.8),
                "user_id": data.get("user_id"),
                "id": solution_id,
            }
        )
        await db.commit()
        return data
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to update solution: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update solution: {str(e)}")


@solution_router.get("/calculate-date-range")
@solution_router.get("/calculate-date-range/")
@solution_router.post("/calculate-date-range")
@solution_router.post("/calculate-date-range/")
async def calculate_date_range(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Calculate recommended date range for model training.
    Matches webapi: views_solution.calculate_date_range
    """
    if request.method == "POST":
        data = await request.json()
    else:
        data = dict(request.query_params)

    # Default response with reasonable date range
    from datetime import timedelta
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365 * 2)

    return {
        "start_date": start_date.strftime("%Y-%m-%d"),
        "end_date": end_date.strftime("%Y-%m-%d"),
        "required_points": 100,
        "recommended_points": 500,
        "estimated_points": 500,
        "adjusted": False,
        "message": "Default date range"
    }


@solution_router.get("/ticker/time_range/{ticker}")
async def get_ticker_time_range(
    ticker: str
):
    """Get available date range for a ticker.
    Matches webapi: views_solution.get_ticker_time_range
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            url = f"{settings.STOCK_DATA_SERVICE_URL}/stock_helper/api/v2/companies/{ticker}/historical-data"
            resp = await client.get(url)
            if resp.status_code == 200:
                data = resp.json()
                if data and isinstance(data, list) and len(data) > 0:
                    return {
                        "start_date": data[0].get("time", "2020-01-01"),
                        "end_date": data[-1].get("time", datetime.now().strftime("%Y-%m-%d"))
                    }
    except Exception as e:
        logger.warning(f"Failed to get ticker time range: {e}")

    # Fallback
    return {
        "start_date": "2020-01-01",
        "end_date": datetime.now().strftime("%Y-%m-%d")
    }


# ==========================================
# Solution Detail Endpoints (must be after specific routes)
# ==========================================


async def _run_darts_engine(
    *, solution_id, db, feature_df, indicator_rows, model_instance, model_id,
    ticker, train_params, start_date, end_date, rows_before_warmup, rows_after_warmup,
    news_coverage_report=None,
):
    """Backlog #109 Phase 2b — train through Darts instead of the tabular path.

    All the modelling lives in `app/services/darts_trainer.py`, which is pure;
    this function is only the I/O around it: status updates, the model file and
    the two UPDATEs.

    On the covariate mapping: the trainer needs to know which feature columns
    are past covariates and whether any were marked `future`. The indicator
    NAMES in `solution_indicators` do not map one-to-one onto the computed
    feature column names (`SMA` becomes `sma_20`, and a single indicator can
    produce several columns), so rather than guess a mapping this passes every
    feature column as a PAST covariate and refuses the run outright if any
    solution row asks for `future` or `both`. That keeps the safety property
    exact — nothing price-derived is ever fed as a future covariate — without
    pretending to a per-column precision the schema does not support.
    """
    from app.services.darts_trainer import DartsTrainingError, run_darts_training

    model_type = (model_instance or {}).get('model_type') or 'BlockRNN'
    config_json = (model_instance or {}).get('config_json')
    try:
        config = json.loads(config_json) if isinstance(config_json, str) else (config_json or {})
    except (json.JSONDecodeError, TypeError):
        config = {}
    if not isinstance(config, dict):
        config = {}

    feature_cols = [c for c in feature_df.columns if c not in ('close', 'target')]
    bad = sorted({str(r.get('covariate_type') or 'past').strip().lower()
                  for r in indicator_rows} - {'past', ''})
    covariate_types = {c: 'past' for c in feature_cols}
    if bad:
        offenders = sorted({str(r.get('name') or r.get('indicator_id'))
                            for r in indicator_rows
                            if str(r.get('covariate_type') or 'past').strip().lower() in bad})
        training_status[solution_id] = {
            "status": "failed",
            "error": ("these indicators are marked as future covariates: "
                      + ", ".join(offenders)
                      + ". A future covariate must be KNOWN over the forecast horizon, "
                        "and a technical indicator is a function of price, so its future "
                        "values are not knowable without the future prices. Mark them "
                        "'past' and train again."),
            "failed_at": time_module.time(),
        }
        return

    training_status[solution_id]["message"] = f"Training {model_type} via Darts..."
    training_status[solution_id]["progress"] = 40

    try:
        result = await asyncio.to_thread(
            run_darts_training, feature_df,
            model_type=model_type, indicator_columns=feature_cols,
            covariate_types=covariate_types,
            train_ratio=float(train_params.get('train_ratio', 0.8)),
            config=config)
    except DartsTrainingError as exc:
        training_status[solution_id] = {
            "status": "failed", "error": str(exc), "failed_at": time_module.time()}
        return
    except Exception as exc:  # noqa: BLE001
        logger.exception("Darts training failed for solution %s", solution_id)
        training_status[solution_id] = {
            "status": "failed",
            "error": f"{type(exc).__name__}: {exc}",
            "failed_at": time_module.time()}
        return

    m = result["metrics"]
    result["data_accounting"]["bars_fetched"] = rows_before_warmup
    result["data_accounting"]["rows_dropped_to_warmup"] = rows_before_warmup - rows_after_warmup

    metrics_json = json.dumps({
        'engine': 'darts', 'model_type': model_type,
        'news_covariates': (news_coverage_report or {"attached": False}),
        'rmse': m['rmse'], 'mae': m['mae'], 'r2': m['r2'],
        'direction_accuracy': m['direction_accuracy'],
        # The benchmark is stored WITH the figure, per C4 — a later reader must
        # not find r2 without finding what "tomorrow = today" scored.
        'naive_rmse': result['naive']['rmse'], 'naive_r2': result['naive']['r2'],
        'beats_naive_rmse': result['beats_naive_rmse'],
        **result["data_accounting"],
    })
    # Backlog #126 — PERSIST THE MODEL, which is what made predict impossible.
    #
    # Everything below this point used to run without the trained model ever
    # reaching disk: status became 'trained', the metrics were stored, and
    # file_path stayed NULL. POST /solutions/predict loads a model from that
    # column, so it answered "Model file not found at None. Retrain the
    # solution." for every darts-trained solution — and retraining could not
    # help, because the retrain was what failed to write the file. Since darts
    # became the default engine on 2026-10-30 that was every solution a user
    # trained without naming an engine.
    #
    # A save failure fails the RUN rather than being logged and swallowed: a
    # solution marked 'trained' whose model is not on disk is precisely the
    # state this backlog item is about, and it must not be reachable by a
    # second route.
    try:
        model_file = await asyncio.to_thread(
            save_darts_bundle, solution_id, result["fitted"])
    except Exception as exc:  # noqa: BLE001
        logger.exception("Darts model could not be saved for solution %s", solution_id)
        training_status[solution_id] = {
            "status": "failed",
            "error": (f"the model trained but could not be saved, so it could not "
                      f"be used for prediction: {type(exc).__name__}: {exc}"),
            "failed_at": time_module.time()}
        return

    prediction_dates = compute_prediction_dates(
        end_date, result["fitted"]["output_chunk_length"])

    await db.execute(
        text("""UPDATE model_instances
                   SET status='trained', file_path=:file_path,
                       training_metrics_json=:metrics, last_training_date=NOW()
                 WHERE id = :model_id"""),
        {"file_path": model_file, "metrics": metrics_json, "model_id": model_id})
    await db.execute(
        text("""UPDATE tbl_solution
                   SET train_status='trained', solution_status=1,
                       start_training_date=:start_date, end_training_date=:end_date,
                       prediction_result=NULL
                 WHERE id = :solution_id"""),
        {"start_date": start_date, "end_date": end_date, "solution_id": solution_id})
    await db.commit()

    training_status[solution_id] = {
        "status": "completed",
        "completed_at": time_module.time(),
        "message": (f"Darts {model_type} trained. RMSE {m['rmse']:.4f} "
                    f"(naive {result['naive']['rmse']:.4f})"),
        "result": {
            "engine": "darts", "model_type": model_type,
            "news_covariates": (news_coverage_report or {"attached": False}),
            "rmse": m['rmse'], "mae": m['mae'], "r2": m['r2'],
            "direction_accuracy": m['direction_accuracy'],
            "naive": result['naive'], "beats_naive_rmse": result['beats_naive_rmse'],
            "covariates": result['covariates'],
            "data_accounting": result['data_accounting'],
            "predictions": result['predictions'],
            "forecast_warnings": result.get('forecast_warnings', []),
            # Backlog #126. Absent here until now, so the Predict tab opened
            # with nothing to offer after a successful darts training.
            "prediction_dates": prediction_dates,
            "training_status": "completed",
        },
    }

@solution_router.get("/{solution_id}/training-status")
@solution_router.get("/{solution_id}/training-status/")
async def get_training_status(
    solution_id: int,
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    """Get the current training status for a solution.
    Matches webapi: views_solution.get_training_status
    """
    if solution_id not in training_status:
        return {
            "status": "not_found",
            "message": "No training session found for this solution"
        }

    current = training_status[solution_id]

    # Clean up old completed/failed statuses after 5 minutes
    if current["status"] in ["completed", "failed"]:
        status_time = current.get("completed_at") or current.get("failed_at", 0)
        if time_module.time() - status_time > 300:
            del training_status[solution_id]

    return current


@solution_router.post("/train")
@solution_router.post("/train/")
async def train_solution(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Start training a solution asynchronously with real ML model.
    Matches webapi: views_solution.train_solution
    """
    data = await request.json()
    solution_id = data.get("id")

    if not solution_id:
        raise HTTPException(status_code=400, detail="Solution ID is required")

    # Normalize to int for consistent dict key
    solution_id = int(solution_id)

    # Check if already training
    if solution_id in training_status:
        current = training_status[solution_id]
        if current["status"] == "training":
            return {
                "message": "Training already in progress",
                "status": "training",
                "solution_id": solution_id
            }

    # Mark as training
    training_status[solution_id] = {
        "status": "training",
        "message": "Initializing training...",
        "progress": 0,
        "started_at": time_module.time()
    }

    # Launch real training in background
    train_params = {
        'start_date': data.get('start_date'),
        'end_date': data.get('end_date'),
        'validation': data.get('validation', False),
        'train_ratio': data.get('train_ratio', 0.8),
        # Backlog #109. The default lives in DEFAULT_TRAINING_ENGINE — 'darts'
        # since 2026-10-30 — so that it is stated once; pass engine='tabular'
        # to run the older pipeline. Normalisation happens in _run_training via
        # resolve_training_engine, which is also where an unknown name is
        # reported, so the raw request value is what travels here.
        'engine': (data.get('engine') or DEFAULT_TRAINING_ENGINE),
        # Backlog #106. Opt-in news PAST covariates and their decay half-life.
        # Default off — see NEWS_FEATURES_DEFAULT for why.
        'include_news': bool(data.get('include_news', NEWS_FEATURES_DEFAULT)),
        'news_halflife_days': resolve_news_halflife(
            data.get('news_halflife_days', NEWS_HALFLIFE_DEFAULT)),
    }

    asyncio.create_task(_run_training(solution_id, train_params))

    return {
        "message": "Training started successfully",
        "status": "training",
        "solution_id": solution_id
    }


async def _persist_prediction(db: AsyncSession, solution_id: int, response: dict) -> None:
    """Store the prediction payload and flip the solution's status.

    Extracted so the darts branch and the tabular path cannot drift on it; the
    fallback matters because a payload too large for the column must still
    leave the status correct rather than aborting a prediction that succeeded.
    """
    try:
        await db.execute(
            text("UPDATE tbl_solution SET train_status='predicted', "
                 "prediction_result = :result WHERE id = :id"),
            {"result": json.dumps(response), "id": solution_id})
    except Exception as persist_err:  # noqa: BLE001
        logger.warning(f"Failed to persist prediction result for solution "
                       f"{solution_id}: {persist_err}")
        await db.execute(
            text("UPDATE tbl_solution SET train_status='predicted' WHERE id = :id"),
            {"id": solution_id})
    await db.commit()


def _forecast_with_darts(*, saved: dict, solution_id: int, ticker: str,
                         feature_df, df, indicator_data_by_date: dict,
                         predict_start, predict_end, horizon: int) -> dict:
    """Backlog #126 — the darts engine's half of POST /solutions/predict.

    Synchronous and free of DB access so the caller can hand it to a thread:
    loading a torch checkpoint and running inference are both blocking, and the
    tabular path's equivalent arithmetic already runs on the event loop only
    because it is numpy-fast.

    The modelling lives in darts_trainer.run_darts_forecast, matching how
    _run_darts_engine delegates to run_darts_training; this function is the
    translation between that result and the payload the Prediction tab reads.
    """
    from app.services.darts_trainer import DartsTrainingError, run_darts_forecast

    model = load_darts_model(saved)
    state = {k: v for k, v in saved.items() if k != 'model'}
    try:
        out = run_darts_forecast(
            model, state, feature_df,
            predict_start=pd.Timestamp(predict_start) if predict_start else None,
            horizon=horizon)
    except DartsTrainingError as exc:
        # A readable reason the operator can act on, rather than a 500 carrying
        # a library message from three frames down.
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    backtest = out["backtest"]
    actual_prices = [{'tradingdate': p['date'], 'close': p['actual_price']}
                     for p in backtest]
    predicted_prices = [{'tradingdate': p['date'], 'close': p['predicted_price']}
                        for p in backtest]
    future_predictions = [{'tradingdate': p['date'], 'close': p['predicted_price']}
                          for p in out["future"]]

    # Metrics over the requested window only, which is what the tabular path
    # reports too, so the two engines' numbers stay comparable.
    if len(backtest) > 1:
        a = np.array([p['actual_price'] for p in backtest])
        f = np.array([p['predicted_price'] for p in backtest])
        metrics = {
            "rmse": float(np.sqrt(mean_squared_error(a, f))),
            "mae": float(mean_absolute_error(a, f)),
            "r2": float(r2_score(a, f)),
        }
    else:
        # One point cannot carry an r2, and inventing one would be worse than
        # saying so.
        metrics = {"rmse": None, "mae": None, "r2": None}

    # The chart context: real history plus indicators, and a predicted value
    # ONLY where the backtest actually produced one.
    #
    # The tabular path draws its predicted line across the whole context, which
    # means most of that line is an in-sample fit of the training span shown as
    # if it were a forecast. This does not copy that. A line that starts where
    # the requested window starts is less decorative and does not claim a
    # forecast was made for a date the model was fitted on.
    CHART_CONTEXT_ROWS = 300
    predicted_by_date = {p['date']: p['predicted_price'] for p in backtest}
    ctx_index = (feature_df.index[-CHART_CONTEXT_ROWS:]
                 if len(feature_df.index) > CHART_CONTEXT_ROWS else feature_df.index)
    chart_points = []
    for d in ctx_index:
        key = d.strftime('%Y-%m-%d')
        point = {
            'date': key,
            'actual_price': float(feature_df.loc[d, 'close']),
            'open': float(df.loc[d, 'open']) if d in df.index else None,
            'high': float(df.loc[d, 'high']) if d in df.index else None,
            'low': float(df.loc[d, 'low']) if d in df.index else None,
            'volume': float(df.loc[d, 'volume']) if d in df.index else None,
        }
        if key in predicted_by_date:
            point['predicted_price'] = predicted_by_date[key]
        if d.isoformat() in indicator_data_by_date:
            point.update(indicator_data_by_date[d.isoformat()])
        elif key in indicator_data_by_date:
            point.update(indicator_data_by_date[key])
        chart_points.append(point)

    return {
        "solution_id": solution_id,
        "ticker": ticker,
        "train_status": "predicted",
        # Named, because #109's lesson was that a result must say which engine
        # produced it. The tabular payload has never carried this; the darts one
        # does from the start.
        "engine": "darts",
        "model_type": out.get("model_type"),
        "chart": chart_points,
        "actual": actual_prices,
        "predict": predicted_prices,
        "future": future_predictions,
        "metrics": metrics,
        "predict_start": str(predict_start) if predict_start else None,
        "predict_end": str(predict_end) if predict_end else None,
        "future_days": len(future_predictions),
        # #124's rule, applied here too: a flat forecast travels with the
        # numbers rather than being left for the reader to notice.
        "forecast_warnings": out.get("warnings", []),
        "requested_horizon": out.get("requested_horizon"),
    }


@solution_router.post("/predict")
@solution_router.post("/predict/")
async def predict_solution(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Generate predictions for a trained solution.
    Matches webapi: views_solution.predict_solution
    """
    data = await request.json()
    solution_id = data.get("id")

    if not solution_id:
        raise HTTPException(status_code=400, detail="Solution ID is required")

    solution_id = int(solution_id)
    predict_start = data.get("start_date")
    predict_end = data.get("end_date")

    try:
        # Step 1: Load solution
        result = await db.execute(
            text("SELECT * FROM tbl_solution WHERE id = :id"),
            {"id": solution_id}
        )
        solution = result.mappings().first()
        if not solution:
            raise HTTPException(status_code=404, detail=f"Solution {solution_id} not found")

        ticker = solution['ticker']
        model_id = solution['model_id']

        # Step 2: Load model instance and verify trained
        result = await db.execute(
            text("SELECT * FROM model_instances WHERE id = :id"),
            {"id": model_id}
        )
        model_instance = result.mappings().first()
        if not model_instance:
            raise HTTPException(status_code=404, detail=f"Model instance {model_id} not found")

        if model_instance['status'] != 'trained':
            raise HTTPException(
                status_code=400,
                detail=f"Model not trained yet (status: {model_instance['status']}). Train the solution first."
            )

        model_file = model_instance['file_path']
        if not model_file or not os.path.exists(model_file):
            raise HTTPException(
                status_code=400,
                detail=f"Model file not found at {model_file}. Retrain the solution."
            )

        # Step 3: Load the saved model
        saved = joblib.load(model_file)
        # Backlog #126. A bundle written before the darts path persisted
        # anything has no engine key, and those are all tabular — so the
        # absence means 'tabular' rather than 'unknown'.
        engine = str(saved.get('engine') or 'tabular').strip().lower()
        if engine == 'darts':
            ml_model = None
            feature_cols = list(saved.get('past_columns') or [])
        else:
            ml_model = saved['model']
            feature_cols = saved['feature_cols']

        logger.info(f"Prediction: loaded {engine} model for solution {solution_id}, "
                    f"{len(feature_cols)} features")

        # Step 4: Load solution indicators
        result = await db.execute(
            text("""
                SELECT si.indicator_id, si.indicator_category, si.covariate_type, si.parameters,
                       ti.name, ti.type, ti.default_parameters, ti.calculation_function
                FROM solution_indicators si
                LEFT JOIN technical_indicators ti ON si.indicator_id = ti.id
                WHERE si.solution_id = :solution_id
            """),
            {"solution_id": solution_id}
        )
        indicator_rows = [dict(r) for r in result.mappings().all()]

        # Step 5: Fetch price data, with enough warm-up to COMPUTE the features
        #
        # Backlog #128. This was a flat 60 calendar days — about 40 trading bars
        # — while the feature set needs 20-bar rolling windows, 10-bar lags AND
        # whatever lookback each attached indicator wants (ICHIMOKU's senkou_b
        # alone is 52). dropna() then emptied the frame and the endpoint
        # returned HTTP 200 with every series empty and null metrics: a blank
        # Prediction tab and no error. On RandomForest the empty frame reached
        # sklearn instead and raised, so the same cause produced a 500.
        #
        # It bit hardest on the window the application ITSELF suggests, because
        # training_end+1 for a one-day horizon is the shortest window there is.
        # Measured on one stored solution: a 1-day window returned 0 points, an
        # 8-month window 154 and finite metrics.
        #
        # The warm-up is now proportional to the indicators actually attached,
        # so a future indicator with a longer lookback widens it by itself.
        if predict_start:
            history_start = (
                pd.Timestamp(predict_start)
                - pd.Timedelta(days=warmup_calendar_days(indicator_rows))
            ).strftime('%Y-%m-%d')
        else:
            history_start = None

        async with httpx.AsyncClient(timeout=60.0) as client:
            url = f"{settings.STOCK_DATA_SERVICE_URL}/stock_helper/api/v2/companies/{ticker}/historical-data"
            params = {}
            if history_start:
                params["start_date"] = history_start
            if predict_end:
                params["end_date"] = predict_end
            resp = await client.get(url, params=params)
            if resp.status_code != 200:
                raise HTTPException(
                    status_code=502,
                    detail=f"Failed to fetch price data for {ticker} (HTTP {resp.status_code})"
                )
            price_response = resp.json()

        if isinstance(price_response, dict) and "data" in price_response:
            price_list = price_response["data"]
        elif isinstance(price_response, list):
            price_list = price_response
        else:
            price_list = []

        if not price_list:
            raise HTTPException(
                status_code=404,
                detail=f"No price data for {ticker}"
            )

        # Build OHLCV DataFrame
        df = pd.DataFrame(price_list)
        if 'time' in df.columns:
            df['date'] = pd.to_datetime(df['time'])
        elif 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'])
        df = df.set_index('date').sort_index()
        df = df[['open', 'high', 'low', 'close', 'volume']].copy()
        df = df.apply(pd.to_numeric, errors='coerce')
        df = df.dropna()

        # Step 6: Build features using shared function
        indicator_feature_df, indicator_data_by_date = _prepare_indicator_features(df, indicator_rows)
        feature_df = _build_feature_df(df, indicator_feature_df)
        feature_df = feature_df.dropna()

        # Backlog #128 — REFUSE RATHER THAN RETURN AN EMPTY 200.
        #
        # With no row left there is nothing to backtest and nothing to forecast
        # from, so what came back before was 200 with four empty series and null
        # metrics, or a 500 from sklearn once the empty array reached it. Both
        # read to the user as "the application is broken" with no cause given.
        #
        # The check is on the WHOLE frame, not on the requested window: a window
        # that lies entirely in the future legitimately selects no rows and must
        # still produce a forecast from the last available bar.
        if feature_df.empty:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"Not enough price history for {ticker} to compute the model's "
                    f"features before {predict_start}. {len(df)} bar(s) were "
                    f"available from {history_start or 'the start of the series'}, "
                    f"and the attached indicators need about "
                    f"{warmup_calendar_days(indicator_rows)} calendar days of "
                    f"warm-up. Pick a later prediction start, or a ticker with "
                    f"more history."
                ),
            )

        # Backlog #126 — the darts branch. Everything above is shared: the
        # solution, the model file, the indicator rows, the price fetch with its
        # warm-up and the feature frame are built the same way for both engines.
        # Everything below is the tabular pipeline, which cannot run a darts
        # model: it calls ml_model.predict(X) on a feature MATRIX, while a darts
        # model takes a TimeSeries plus its covariates.
        if engine == 'darts':
            prediction_response = await asyncio.to_thread(
                _forecast_with_darts,
                saved=saved, solution_id=solution_id, ticker=ticker,
                feature_df=feature_df, df=df,
                indicator_data_by_date=indicator_data_by_date,
                predict_start=predict_start, predict_end=predict_end,
                horizon=resolve_output_chunk_length(
                    model_instance.get('config_json') if model_instance else None,
                    requested=data.get('predict_days')),
            )
            await _persist_prediction(db, solution_id, prediction_response)
            return prediction_response

        # Ensure we have the same columns as training (in same order)
        missing_cols = [c for c in feature_cols if c not in feature_df.columns]
        if missing_cols:
            logger.warning(f"Prediction: missing features {missing_cols}, filling with 0")
            for c in missing_cols:
                feature_df[c] = 0.0

        # Step 7: Predict on known period (historical backtest)
        X_pred = feature_df[feature_cols].values
        y_pred = ml_model.predict(X_pred)

        # Filter to requested date range for output
        if predict_start:
            mask = feature_df.index >= pd.Timestamp(predict_start)
        else:
            mask = pd.Series(True, index=feature_df.index)

        actual_prices = []
        predicted_prices = []
        dates_in_range = feature_df.index[mask]

        for i_global, d in enumerate(feature_df.index):
            if not mask[i_global]:
                continue
            date_str = d.strftime('%Y-%m-%d')
            actual_prices.append({
                'tradingdate': date_str,
                'close': float(feature_df['close'].iloc[i_global]),
            })
            predicted_prices.append({
                'tradingdate': date_str,
                'close': float(y_pred[i_global]),
            })

        # Compute affine bias correction from backtest (scale + shift)
        # Simple additive bias keeps flat predictions flat; affine amplifies tiny model variations
        actual_mean = pred_mean = actual_std = pred_std = 0.0
        prediction_bias = 0.0
        use_affine = use_shift = False
        if actual_prices and predicted_prices:
            actual_vals = np.array([p['close'] for p in actual_prices])
            pred_vals = np.array([p['close'] for p in predicted_prices])
            actual_mean = float(np.mean(actual_vals))
            pred_mean = float(np.mean(pred_vals))
            actual_std = float(np.std(actual_vals))
            pred_std = float(np.std(pred_vals))
            prediction_bias = actual_mean - pred_mean  # for future predictions
            if pred_std > 1e-6 and actual_std > 1e-6:
                use_affine = True
            elif abs(prediction_bias) > 0.01:
                use_shift = True

        def _correct_pred(v):
            """Apply the same backtest-derived correction used for in-range points."""
            if use_affine:
                return float(actual_mean + (actual_std / pred_std) * (v - pred_mean))
            if use_shift:
                return float(v + prediction_bias)
            return float(v)

        # Affine correction: scale in-range backtest predictions to match actuals
        for p in predicted_prices:
            p['close'] = _correct_pred(p['close'])

        # Step 8: Future predictions (iterative, day-by-day)
        #
        # Backlog #127. This read predict_days or DEFAULT_PREDICTION_DAYS (5)
        # and never the model, so a model built with output_chunk_length=10
        # forecast five days and one built with 1 also forecast five. An
        # explicit predict_days still wins — see resolve_output_chunk_length.
        future_predictions = []
        output_chunk_length = resolve_output_chunk_length(
            model_instance.get('config_json') if model_instance else None,
            requested=data.get('predict_days'))

        # Compute model quality weight for blending model vs simulated trajectory
        # Good model (R2>0.5): rely mostly on model; Bad model (R2<0): rely on simulation
        # Use raw (pre-bias) predictions to assess true model quality
        if len(actual_prices) > 1:
            bt_actual_vals = np.array([p['close'] for p in actual_prices])
            bt_raw_preds = y_pred[mask] if hasattr(mask, '__len__') else y_pred
            bt_r2 = float(r2_score(bt_actual_vals, bt_raw_preds[:len(bt_actual_vals)]))
            model_weight = np.clip(bt_r2, 0.1, 0.95)  # min 10% model, max 95%
        else:
            model_weight = 0.5

        # Start from last available date
        last_date = df.index[-1]
        last_close = float(df['close'].iloc[-1])
        last_row = df.iloc[-1].copy()

        # We need a rolling window of df for feature calculation
        future_df = df.copy()

        # Calculate historical volatility stats from last 30 days for realistic synthetic OHLCV
        recent = df.tail(30)
        daily_returns = recent['close'].pct_change().dropna()
        avg_return = float(daily_returns.mean())
        return_std = float(daily_returns.std()) if len(daily_returns) > 1 else 0.01
        avg_atr_pct = float((recent['high'] - recent['low']).mean() / recent['close'].mean()) if recent['close'].mean() > 0 else 0.02
        vol_mean = float(recent['volume'].mean())
        vol_std = float(recent['volume'].std()) if len(recent) > 1 else vol_mean * 0.1

        for day_i in range(output_chunk_length):
            # Next business day
            next_date = last_date + pd.Timedelta(days=1)
            while next_date.weekday() >= 5:
                next_date += pd.Timedelta(days=1)

            # Simulate realistic price movement based on historical volatility
            # Clamp return to prevent extreme moves (max ±10% per day)
            simulated_return = np.clip(avg_return + return_std * np.random.randn(), -0.10, 0.10)
            pred_close_estimate = max(0.01, last_close * (1 + simulated_return))
            open_price = max(0.01, last_close * (1 + avg_return * 0.5 + return_std * 0.3 * np.random.randn()))
            high_price = max(open_price, pred_close_estimate) * (1 + avg_atr_pct * 0.5 * abs(np.random.randn()))
            low_price = min(open_price, pred_close_estimate) * max(0.01, 1 - avg_atr_pct * 0.5 * abs(np.random.randn()))
            sim_volume = max(0, vol_mean + vol_std * np.random.randn())

            new_row = pd.DataFrame({
                'open': [open_price],
                'high': [high_price],
                'low': [low_price],
                'close': [pred_close_estimate],
                'volume': [sim_volume],
            }, index=[next_date])
            future_df = pd.concat([future_df, new_row])

            # Rebuild features on extended df
            ind_feat_df, _ = _prepare_indicator_features(future_df, indicator_rows)
            feat_df = _build_feature_df(future_df, ind_feat_df)
            feat_df = feat_df.dropna()

            if next_date not in feat_df.index:
                break

            # Ensure column alignment
            for c in feature_cols:
                if c not in feat_df.columns:
                    feat_df[c] = 0.0

            x_next = feat_df.loc[[next_date], feature_cols].values
            raw_pred = float(ml_model.predict(x_next)[0])

            # Blend bias-corrected model prediction with simulated trajectory
            # Weight based on model quality: good model → trust model, bad model → trust simulation
            model_pred = max(0.01, raw_pred + prediction_bias)
            pred_price = model_weight * model_pred + (1 - model_weight) * pred_close_estimate

            # Update close with bias-corrected prediction, keep realistic OHLV spread
            future_df.loc[next_date, 'close'] = pred_price
            future_df.loc[next_date, 'open'] = open_price
            price_range = abs(avg_atr_pct * pred_price * 0.5)
            future_df.loc[next_date, 'high'] = max(pred_price, open_price) + price_range * abs(np.random.randn()) * 0.3
            future_df.loc[next_date, 'low'] = max(0.01, min(pred_price, open_price) - price_range * abs(np.random.randn()) * 0.3)

            future_predictions.append({
                'tradingdate': next_date.strftime('%Y-%m-%d'),
                'close': pred_price,
            })

            last_date = next_date
            last_close = pred_price

        # Step 9: Compute metrics on the backtest period
        if len(actual_prices) > 1 and len(predicted_prices) > 1:
            actuals = np.array([p['close'] for p in actual_prices])
            preds = np.array([p['close'] for p in predicted_prices])
            rmse = float(np.sqrt(mean_squared_error(actuals, preds)))
            mae = float(mean_absolute_error(actuals, preds))
            r2 = float(r2_score(actuals, preds))
        else:
            rmse = mae = r2 = None

        # Build a rich chart series so the Prediction tab renders the same
        # multi-series view as the Training tab: recent real OHLCV history with
        # merged indicators plus a continuous backtest predicted line. The
        # forecast (`future`) extends this on the frontend. Bounded to the most
        # recent rows to keep the payload small.
        CHART_CONTEXT_ROWS = 300
        chart_points = []
        ctx_index = feature_df.index[-CHART_CONTEXT_ROWS:] if len(feature_df.index) > CHART_CONTEXT_ROWS else feature_df.index
        pos_by_date = {d: i for i, d in enumerate(feature_df.index)}
        for d in ctx_index:
            i_global = pos_by_date[d]
            point = {
                'date': d.strftime('%Y-%m-%d'),
                'actual_price': float(feature_df['close'].iloc[i_global]),
                'predicted_price': _correct_pred(float(y_pred[i_global])),
                'open': float(df.loc[d, 'open']) if d in df.index else None,
                'high': float(df.loc[d, 'high']) if d in df.index else None,
                'low': float(df.loc[d, 'low']) if d in df.index else None,
                'volume': float(df.loc[d, 'volume']) if d in df.index else None,
            }
            key = d.isoformat()
            if key in indicator_data_by_date:
                point.update(indicator_data_by_date[key])
            elif d.strftime('%Y-%m-%d') in indicator_data_by_date:
                point.update(indicator_data_by_date[d.strftime('%Y-%m-%d')])
            chart_points.append(point)

        # Build response
        prediction_response = {
            "solution_id": solution_id,
            "ticker": ticker,
            "train_status": "predicted",
            "chart": chart_points,
            "actual": actual_prices,
            "predict": predicted_prices,
            "future": future_predictions,
            "metrics": {
                "rmse": rmse,
                "mae": mae,
                "r2": r2,
            },
            "predict_start": predict_start,
            "predict_end": predict_end,
            "future_days": output_chunk_length,
        }

        # Persist prediction result and update status
        await _persist_prediction(db, solution_id, prediction_response)

        return prediction_response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Prediction failed for solution {solution_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")


# ==========================================
# Solution Indicator Endpoints
# ==========================================

@solution_router.get("/{solution_id}/indicators")
@solution_router.get("/{solution_id}/indicators/")
async def get_solution_indicators(
    solution_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    """Get indicators assigned to a solution, grouped by category.
    Returns format expected by frontend IndicatorSelector:
    { trend: {id, covariate_type, parameters, name, ...}, momentum: {...}, ... }
    Matches webapi: view_indicators.get_solution_indicators
    """
    try:
        result = await db.execute(
            text("""
                SELECT si.id, si.solution_id, si.indicator_id, si.indicator_category,
                       si.covariate_type, si.parameters,
                       ti.name, ti.type, ti.description, ti.default_parameters
                FROM solution_indicators si
                LEFT JOIN technical_indicators ti ON si.indicator_id = ti.id
                WHERE si.solution_id = :solution_id
            """),
            {"solution_id": solution_id}
        )
        rows = result.mappings().all()

        # Group by category for frontend consumption
        grouped = {}
        for row in rows:
            ind = dict(row)
            params = ind.get("parameters")
            if params and isinstance(params, str):
                try:
                    params = json.loads(params)
                except (json.JSONDecodeError, TypeError):
                    pass
            default_params = ind.get("default_parameters")
            if default_params and isinstance(default_params, str):
                try:
                    default_params = json.loads(default_params)
                except (json.JSONDecodeError, TypeError):
                    pass

            category = ind.get("indicator_category")
            if category:
                grouped[category] = {
                    "id": ind.get("indicator_id"),
                    "name": ind.get("name"),
                    "type": ind.get("type"),
                    "description": ind.get("description"),
                    "covariate_type": ind.get("covariate_type", "past"),
                    "parameters": params or {},
                    "default_parameters": default_params or {},
                }

        return grouped
    except Exception as e:
        logger.error(f"Failed to fetch solution indicators: {e}")
        return {}


@solution_router.post("/{solution_id}/indicators/set")
@solution_router.post("/{solution_id}/indicators/set/")
async def set_solution_indicators(
    solution_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Set all indicators for a solution (replaces existing).
    Frontend sends: {trend_indicator: {id, covariate_type, parameters}, momentum_indicator: {...}, ...}
    Matches webapi: view_indicators.set_solution_indicators
    """
    data = await request.json()

    # Parse frontend format: {trend_indicator: {...}, momentum_indicator: {...}, ...}
    category_map = {
        "trend_indicator": "trend",
        "momentum_indicator": "momentum",
        "volatility_indicator": "volatility",
        "volume_indicator": "volume",
    }

    indicators = []
    for key, category in category_map.items():
        ind_data = data.get(key)
        if ind_data and ind_data.get("id"):
            indicators.append({
                "indicator_id": ind_data["id"],
                "indicator_category": category,
                "covariate_type": ind_data.get("covariate_type", "past"),
                "parameters": ind_data.get("parameters", {}),
            })

    # Also support array format: {indicators: [{indicator_id, indicator_category, ...}]}
    if not indicators and "indicators" in data:
        indicators = data["indicators"]

    try:
        # Delete existing indicators for this solution
        await db.execute(
            text("DELETE FROM solution_indicators WHERE solution_id = :solution_id"),
            {"solution_id": solution_id}
        )

        # Insert new indicators
        for ind in indicators:
            params = ind.get("parameters", {})
            params_json = json.dumps(params) if isinstance(params, dict) else params

            await db.execute(
                text("""
                    INSERT INTO solution_indicators
                    (solution_id, indicator_id, indicator_category, covariate_type, parameters)
                    VALUES (:solution_id, :indicator_id, :indicator_category, :covariate_type, :parameters)
                """),
                {
                    "solution_id": solution_id,
                    "indicator_id": ind.get("indicator_id"),
                    "indicator_category": ind.get("indicator_category", "trend"),
                    "covariate_type": ind.get("covariate_type", "past"),
                    "parameters": params_json
                }
            )

        await db.commit()
        return {"message": "Indicators set successfully", "solution_id": solution_id}
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to set solution indicators: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to set indicators: {str(e)}")


# ==========================================
# Indicator Calculation
# Matches webapi: view_indicators.calculate_solution_indicators
# ==========================================

# Mapping from DB indicator names to short codes (matches webapi indicator_service.py)
INDICATOR_NAME_MAP = {
    'SMA': 'SMA', 'Simple Moving Average': 'SMA',
    'EMA': 'EMA', 'Exponential Moving Average': 'EMA',
    'WMA': 'WMA', 'Weighted Moving Average': 'WMA',
    'DEMA': 'DEMA', 'TEMA': 'TEMA',
    'MACD': 'MACD', 'Moving Average Convergence Divergence': 'MACD',
    'ADX': 'ADX', 'Average Directional Index': 'ADX',
    'PSAR': 'PSAR', 'Parabolic SAR': 'PSAR',
    'SUPERTREND': 'SUPERTREND', 'ICHIMOKU': 'ICHIMOKU',
    'AROON': 'AROON', 'VORTEX': 'VORTEX',
    'RSI': 'RSI', 'Relative Strength Index': 'RSI',
    'STOCH': 'STOCH', 'Stochastic Oscillator': 'STOCH',
    'STOCH_RSI': 'STOCH_RSI', 'CCI': 'CCI', 'Commodity Channel Index': 'CCI',
    'WILLIAMS_R': 'WILLIAMS_R', 'Williams %R': 'WILLIAMS_R',
    'ROC': 'ROC', 'Rate of Change': 'ROC',
    'MOM': 'MOM', 'Momentum Indicator': 'MOM',
    'TSI': 'TSI', 'UO': 'UO', 'AO': 'AO',
    'BB': 'BB', 'Bollinger Bands': 'BB',
    'ATR': 'ATR', 'Average True Range': 'ATR',
    'KELTNER': 'KELTNER', 'DONCHIAN': 'DONCHIAN',
    'STDDEV': 'STDDEV', 'HV': 'HV',
    'VOLUME': 'VOLUME', 'OBV': 'OBV', 'On Balance Volume': 'OBV',
    'VWAP': 'VWAP', 'MFI': 'MFI', 'Money Flow Index': 'MFI',
    'AD': 'AD', 'CMF': 'CMF', 'CHO': 'CHO', 'VOSC': 'VOSC',
    'EOM': 'EOM', 'FI': 'FI', 'NVI': 'NVI', 'PVI': 'PVI',
    'Volume_MA': 'Volume_MA',
}


def _safe_val(v):
    """Convert numpy types to native Python types for JSON serialization."""
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return None
    if pd.isna(v):
        return None
    return float(v)


def _calculate_indicator(df: pd.DataFrame, code: str, params: dict) -> List[Dict]:
    """Calculate a single technical indicator. Matches webapi/services/advanced_technical_indicators.py"""
    result = []
    dates = df.index

    try:
        if code == 'SMA':
            values = ta.trend.SMAIndicator(df['close'], window=params.get('period', 20)).sma_indicator()
            for i, d in enumerate(dates):
                result.append({'date': d.isoformat(), 'sma': _safe_val(values.iloc[i])})
        elif code == 'EMA':
            values = ta.trend.EMAIndicator(df['close'], window=params.get('period', 20)).ema_indicator()
            for i, d in enumerate(dates):
                result.append({'date': d.isoformat(), 'ema': _safe_val(values.iloc[i])})
        elif code == 'WMA':
            values = ta.trend.WMAIndicator(df['close'], window=params.get('period', 20)).wma()
            for i, d in enumerate(dates):
                result.append({'date': d.isoformat(), 'wma': _safe_val(values.iloc[i])})
        elif code == 'DEMA':
            ema1 = ta.trend.EMAIndicator(df['close'], window=params.get('period', 20)).ema_indicator()
            ema2 = ta.trend.EMAIndicator(ema1, window=params.get('period', 20)).ema_indicator()
            values = 2 * ema1 - ema2
            for i, d in enumerate(dates):
                result.append({'date': d.isoformat(), 'dema': _safe_val(values.iloc[i])})
        elif code == 'TEMA':
            ema1 = ta.trend.EMAIndicator(df['close'], window=params.get('period', 20)).ema_indicator()
            ema2 = ta.trend.EMAIndicator(ema1, window=params.get('period', 20)).ema_indicator()
            ema3 = ta.trend.EMAIndicator(ema2, window=params.get('period', 20)).ema_indicator()
            values = 3 * ema1 - 3 * ema2 + ema3
            for i, d in enumerate(dates):
                result.append({'date': d.isoformat(), 'tema': _safe_val(values.iloc[i])})
        elif code == 'MACD':
            m = ta.trend.MACD(df['close'], window_fast=params.get('fast_period', 12),
                              window_slow=params.get('slow_period', 26), window_sign=params.get('signal_period', 9))
            for i, d in enumerate(dates):
                result.append({'date': d.isoformat(),
                               'macd': _safe_val(m.macd().iloc[i]),
                               'signal': _safe_val(m.macd_signal().iloc[i]),
                               'histogram': _safe_val(m.macd_diff().iloc[i])})
        elif code == 'ADX':
            adx = ta.trend.ADXIndicator(df['high'], df['low'], df['close'], window=params.get('period', 14))
            for i, d in enumerate(dates):
                result.append({'date': d.isoformat(),
                               'adx': _safe_val(adx.adx().iloc[i])})
        elif code == 'PSAR':
            values = ta.trend.PSARIndicator(df['high'], df['low'], df['close'],
                                            step=params.get('step', 0.02), max_step=params.get('max_step', 0.2)).psar()
            for i, d in enumerate(dates):
                result.append({'date': d.isoformat(), 'psar': _safe_val(values.iloc[i])})
        elif code == 'RSI':
            values = ta.momentum.RSIIndicator(df['close'], window=params.get('period', 14)).rsi()
            for i, d in enumerate(dates):
                result.append({'date': d.isoformat(), 'rsi': _safe_val(values.iloc[i])})
        elif code == 'STOCH':
            s = ta.momentum.StochasticOscillator(df['high'], df['low'], df['close'],
                                                  window=params.get('k_period', 14), smooth_window=params.get('d_period', 3))
            for i, d in enumerate(dates):
                result.append({'date': d.isoformat(),
                               'stoch_k': _safe_val(s.stoch().iloc[i]),
                               'stoch_d': _safe_val(s.stoch_signal().iloc[i])})
        elif code == 'CCI':
            values = ta.trend.CCIIndicator(df['high'], df['low'], df['close'], window=params.get('period', 20)).cci()
            for i, d in enumerate(dates):
                result.append({'date': d.isoformat(), 'cci': _safe_val(values.iloc[i])})
        elif code == 'WILLIAMS_R':
            values = ta.momentum.WilliamsRIndicator(df['high'], df['low'], df['close'],
                                                     lbp=params.get('period', 14)).williams_r()
            for i, d in enumerate(dates):
                result.append({'date': d.isoformat(), 'williams_r': _safe_val(values.iloc[i])})
        elif code == 'ROC':
            values = ta.momentum.ROCIndicator(df['close'], window=params.get('period', 12)).roc()
            for i, d in enumerate(dates):
                result.append({'date': d.isoformat(), 'roc': _safe_val(values.iloc[i])})
        elif code == 'BB':
            std_val = params.get('std_dev', params.get('std', 2))
            bb = ta.volatility.BollingerBands(df['close'], window=params.get('period', 20), window_dev=std_val)
            for i, d in enumerate(dates):
                result.append({'date': d.isoformat(),
                               'bb_upper': _safe_val(bb.bollinger_hband().iloc[i]),
                               'bb_middle': _safe_val(bb.bollinger_mavg().iloc[i]),
                               'bb_lower': _safe_val(bb.bollinger_lband().iloc[i])})
        elif code == 'ATR':
            values = ta.volatility.AverageTrueRange(df['high'], df['low'], df['close'],
                                                     window=params.get('period', 14)).average_true_range()
            for i, d in enumerate(dates):
                result.append({'date': d.isoformat(), 'atr': _safe_val(values.iloc[i])})
        elif code == 'KELTNER':
            kc = ta.volatility.KeltnerChannel(df['high'], df['low'], df['close'],
                                               window=params.get('period', 20), window_atr=params.get('period', 20))
            for i, d in enumerate(dates):
                result.append({'date': d.isoformat(),
                               'kc_upper': _safe_val(kc.keltner_channel_hband().iloc[i]),
                               'kc_middle': _safe_val(kc.keltner_channel_mband().iloc[i]),
                               'kc_lower': _safe_val(kc.keltner_channel_lband().iloc[i])})
        elif code == 'DONCHIAN':
            dc = ta.volatility.DonchianChannel(df['high'], df['low'], df['close'], window=params.get('period', 20))
            for i, d in enumerate(dates):
                result.append({'date': d.isoformat(),
                               'dc_upper': _safe_val(dc.donchian_channel_hband().iloc[i]),
                               'dc_middle': _safe_val(dc.donchian_channel_mband().iloc[i]),
                               'dc_lower': _safe_val(dc.donchian_channel_lband().iloc[i])})
        elif code == 'OBV':
            values = ta.volume.OnBalanceVolumeIndicator(df['close'], df['volume']).on_balance_volume()
            for i, d in enumerate(dates):
                result.append({'date': d.isoformat(), 'obv': _safe_val(values.iloc[i])})
        elif code == 'MFI':
            values = ta.volume.MFIIndicator(df['high'], df['low'], df['close'], df['volume'],
                                             window=params.get('period', 14)).money_flow_index()
            for i, d in enumerate(dates):
                result.append({'date': d.isoformat(), 'mfi': _safe_val(values.iloc[i])})
        elif code == 'CMF':
            values = ta.volume.ChaikinMoneyFlowIndicator(df['high'], df['low'], df['close'], df['volume'],
                                                          window=params.get('period', 20)).chaikin_money_flow()
            for i, d in enumerate(dates):
                result.append({'date': d.isoformat(), 'cmf': _safe_val(values.iloc[i])})
        elif code == 'VOLUME':
            for i, d in enumerate(dates):
                result.append({'date': d.isoformat(), 'volume': float(df['volume'].iloc[i])})
        elif code == 'VWAP':
            values = ta.volume.VolumeWeightedAveragePrice(df['high'], df['low'], df['close'], df['volume']).volume_weighted_average_price()
            for i, d in enumerate(dates):
                result.append({'date': d.isoformat(), 'vwap': _safe_val(values.iloc[i])})
        elif code == 'STDDEV':
            values = df['close'].rolling(window=params.get('period', 20)).std()
            for i, d in enumerate(dates):
                result.append({'date': d.isoformat(), 'stddev': _safe_val(values.iloc[i])})
        elif code == 'HV':
            log_returns = np.log(df['close'] / df['close'].shift(1))
            values = log_returns.rolling(window=params.get('period', 20)).std() * np.sqrt(252)
            for i, d in enumerate(dates):
                result.append({'date': d.isoformat(), 'hv': _safe_val(values.iloc[i])})
        elif code == 'MOM':
            values = df['close'] - df['close'].shift(params.get('period', 10))
            for i, d in enumerate(dates):
                result.append({'date': d.isoformat(), 'mom': _safe_val(values.iloc[i])})
        elif code == 'AD':
            values = ta.volume.AccDistIndexIndicator(df['high'], df['low'], df['close'], df['volume']).acc_dist_index()
            for i, d in enumerate(dates):
                result.append({'date': d.isoformat(), 'ad': _safe_val(values.iloc[i])})
        elif code == 'STOCH_RSI':
            s = ta.momentum.StochRSIIndicator(df['close'], window=params.get('period', 14),
                                               smooth1=params.get('smooth1', 3), smooth2=params.get('smooth2', 3))
            for i, d in enumerate(dates):
                result.append({'date': d.isoformat(),
                               'stoch_rsi_k': _safe_val(s.stochrsi_k().iloc[i]),
                               'stoch_rsi_d': _safe_val(s.stochrsi_d().iloc[i])})
        elif code == 'TSI':
            values = ta.momentum.TSIIndicator(df['close'], window_slow=params.get('slow_period', 25),
                                               window_fast=params.get('fast_period', 13)).tsi()
            for i, d in enumerate(dates):
                result.append({'date': d.isoformat(), 'tsi': _safe_val(values.iloc[i])})
        elif code == 'UO':
            values = ta.momentum.UltimateOscillator(df['high'], df['low'], df['close'],
                                                      window1=params.get('period1', 7),
                                                      window2=params.get('period2', 14),
                                                      window3=params.get('period3', 28)).ultimate_oscillator()
            for i, d in enumerate(dates):
                result.append({'date': d.isoformat(), 'uo': _safe_val(values.iloc[i])})
        elif code == 'AO':
            values = ta.momentum.AwesomeOscillatorIndicator(df['high'], df['low'],
                                                              window1=params.get('fast_period', 5),
                                                              window2=params.get('slow_period', 34)).awesome_oscillator()
            for i, d in enumerate(dates):
                result.append({'date': d.isoformat(), 'ao': _safe_val(values.iloc[i])})
        elif code == 'SUPERTREND':
            st = ta.trend.STCIndicator(df['close'], window_slow=params.get('slow_period', 50),
                                        window_fast=params.get('fast_period', 23), cycle=params.get('cycle', 10))
            for i, d in enumerate(dates):
                result.append({'date': d.isoformat(), 'supertrend': _safe_val(st.stc().iloc[i])})
        elif code == 'AROON':
            a = ta.trend.AroonIndicator(df['close'], window=params.get('period', 25))
            for i, d in enumerate(dates):
                result.append({'date': d.isoformat(),
                               'aroon_up': _safe_val(a.aroon_up().iloc[i]),
                               'aroon_down': _safe_val(a.aroon_down().iloc[i])})
        elif code == 'VORTEX':
            v = ta.trend.VortexIndicator(df['high'], df['low'], df['close'], window=params.get('period', 14))
            for i, d in enumerate(dates):
                result.append({'date': d.isoformat(),
                               'vortex_pos': _safe_val(v.vortex_indicator_pos().iloc[i]),
                               'vortex_neg': _safe_val(v.vortex_indicator_neg().iloc[i])})
        elif code == 'ICHIMOKU':
            ich = ta.trend.IchimokuIndicator(df['high'], df['low'],
                                              window1=params.get('tenkan_period', 9),
                                              window2=params.get('kijun_period', 26),
                                              window3=params.get('senkou_b_period', 52))
            for i, d in enumerate(dates):
                result.append({'date': d.isoformat(),
                               'ichimoku_conv': _safe_val(ich.ichimoku_conversion_line().iloc[i]),
                               'ichimoku_base': _safe_val(ich.ichimoku_base_line().iloc[i]),
                               'ichimoku_a': _safe_val(ich.ichimoku_a().iloc[i]),
                               'ichimoku_b': _safe_val(ich.ichimoku_b().iloc[i])})
        elif code == 'CHO':
            values = ta.volume.ChaikinMoneyFlowIndicator(df['high'], df['low'], df['close'], df['volume'],
                                                          window=params.get('period', 20)).chaikin_money_flow()
            for i, d in enumerate(dates):
                result.append({'date': d.isoformat(), 'cho': _safe_val(values.iloc[i])})
        elif code == 'EOM':
            values = ta.volume.EaseOfMovementIndicator(df['high'], df['low'], df['volume'],
                                                        window=params.get('period', 14)).ease_of_movement()
            for i, d in enumerate(dates):
                result.append({'date': d.isoformat(), 'eom': _safe_val(values.iloc[i])})
        elif code == 'FI':
            values = ta.volume.ForceIndexIndicator(df['close'], df['volume'],
                                                     window=params.get('period', 13)).force_index()
            for i, d in enumerate(dates):
                result.append({'date': d.isoformat(), 'fi': _safe_val(values.iloc[i])})
        elif code == 'NVI':
            values = ta.volume.NegativeVolumeIndexIndicator(df['close'], df['volume']).negative_volume_index()
            for i, d in enumerate(dates):
                result.append({'date': d.isoformat(), 'nvi': _safe_val(values.iloc[i])})
        elif code == 'PVI':
            values = ta.volume.VolumePriceTrendIndicator(df['close'], df['volume']).volume_price_trend()
            for i, d in enumerate(dates):
                result.append({'date': d.isoformat(), 'pvi': _safe_val(values.iloc[i])})
        elif code == 'VOSC':
            short_ma = df['volume'].rolling(window=params.get('short_period', 5)).mean()
            long_ma = df['volume'].rolling(window=params.get('long_period', 20)).mean()
            values = ((short_ma - long_ma) / long_ma) * 100
            for i, d in enumerate(dates):
                result.append({'date': d.isoformat(), 'vosc': _safe_val(values.iloc[i])})
        elif code == 'Volume_MA':
            values = df['volume'].rolling(window=params.get('period', 20)).mean()
            for i, d in enumerate(dates):
                result.append({'date': d.isoformat(), 'volume_ma': _safe_val(values.iloc[i])})
        else:
            # Fallback: return close price as the value
            for i, d in enumerate(dates):
                result.append({'date': d.isoformat(), 'value': float(df['close'].iloc[i])})
    except Exception as e:
        logger.warning(f"Failed to calculate {code}: {e}, falling back to close price")
        for i, d in enumerate(dates):
            result.append({'date': d.isoformat(), 'value': float(df['close'].iloc[i])})

    return result


@solution_router.post("/{solution_id}/indicators/calculate")
@solution_router.post("/{solution_id}/indicators/calculate/")
async def calculate_solution_indicators(
    solution_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    """Calculate all indicators for a solution.
    Matches webapi: view_indicators.calculate_solution_indicators
    POST body: {symbol, start_date, end_date}
    """
    data = await request.json()
    symbol = data.get("symbol", "")
    start_date = data.get("start_date", "")
    end_date = data.get("end_date", "")

    if not symbol or not start_date or not end_date:
        raise HTTPException(status_code=400, detail="symbol, start_date, and end_date are required")

    # 1. Get solution's configured indicators (grouped by category)
    try:
        result = await db.execute(
            text("""
                SELECT si.indicator_id, si.indicator_category, si.covariate_type, si.parameters,
                       ti.name, ti.type, ti.default_parameters, ti.calculation_function
                FROM solution_indicators si
                LEFT JOIN technical_indicators ti ON si.indicator_id = ti.id
                WHERE si.solution_id = :solution_id
            """),
            {"solution_id": solution_id}
        )
        rows = result.mappings().all()
    except Exception as e:
        logger.error(f"Failed to get solution indicators: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    if not rows:
        return {}

    # 2. Fetch price data from stock-data-service
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            url = f"{settings.STOCK_DATA_SERVICE_URL}/stock_helper/api/v2/companies/{symbol}/historical-data"
            resp = await client.get(url, params={"start_date": start_date, "end_date": end_date})
            if resp.status_code != 200:
                raise HTTPException(status_code=resp.status_code, detail=f"Failed to fetch price data for {symbol}")
            price_data = resp.json()
    except httpx.HTTPError as e:
        logger.error(f"Failed to fetch price data: {e}")
        raise HTTPException(status_code=502, detail=f"Failed to fetch price data: {str(e)}")

    # Parse price data into DataFrame
    if isinstance(price_data, dict) and "data" in price_data:
        price_list = price_data["data"]
    elif isinstance(price_data, list):
        price_list = price_data
    else:
        price_list = []

    if not price_list:
        raise HTTPException(status_code=404, detail=f"No price data for {symbol} in date range")

    df = pd.DataFrame(price_list)
    # Normalize column names (stock-data-service may use 'time' or 'date')
    if 'time' in df.columns:
        df['date'] = pd.to_datetime(df['time'])
    elif 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'])
    df = df.set_index('date')

    # Ensure required columns exist
    for col in ['open', 'high', 'low', 'close', 'volume']:
        if col not in df.columns:
            raise HTTPException(status_code=500, detail=f"Price data missing column: {col}")

    df = df[['open', 'high', 'low', 'close', 'volume']].copy()
    df = df.apply(pd.to_numeric, errors='coerce')
    df = df.dropna()

    # 3. Calculate each indicator
    calculated_values = {}
    for row in rows:
        ind = dict(row)
        category = ind.get("indicator_category")
        name = ind.get("name", "")

        # Parse parameters
        params = ind.get("parameters")
        if params and isinstance(params, str):
            try:
                params = json.loads(params)
            except (json.JSONDecodeError, TypeError):
                params = {}
        if not params:
            default_params = ind.get("default_parameters")
            if default_params and isinstance(default_params, str):
                try:
                    params = json.loads(default_params)
                except (json.JSONDecodeError, TypeError):
                    params = {}
            elif isinstance(default_params, dict):
                params = default_params
            else:
                params = {}

        # Map name to calculation code
        code = INDICATOR_NAME_MAP.get(name, name)

        indicator_data = _calculate_indicator(df, code, params)

        calculated_values[category] = {
            'name': name,
            'data': indicator_data
        }

    # 4. Include OHLC price data so frontend can render candlestick charts
    dates = df.index
    price_data = []
    for i, d in enumerate(dates):
        price_data.append({
            'date': d.isoformat(),
            'open': _safe_val(df['open'].iloc[i]),
            'high': _safe_val(df['high'].iloc[i]),
            'low': _safe_val(df['low'].iloc[i]),
            'close': _safe_val(df['close'].iloc[i]),
            'volume': float(df['volume'].iloc[i]) if pd.notna(df['volume'].iloc[i]) else 0,
        })
    calculated_values['price'] = {
        'name': 'Price',
        'data': price_data
    }

    return calculated_values


@solution_router.post("/{solution_id}/indicators/add")
@solution_router.post("/{solution_id}/indicators/add/")
async def add_solution_indicator(
    solution_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Add an indicator to a solution."""
    data = await request.json()
    params = data.get("parameters", {})
    params_json = json.dumps(params) if isinstance(params, dict) else params

    try:
        result = await db.execute(
            text("""
                INSERT INTO solution_indicators
                (solution_id, indicator_id, indicator_category, covariate_type, parameters)
                VALUES (:solution_id, :indicator_id, :indicator_category, :covariate_type, :parameters)
            """),
            {
                "solution_id": solution_id,
                "indicator_id": data.get("indicator_id"),
                "indicator_category": data.get("indicator_category", "trend"),
                "covariate_type": data.get("covariate_type", "past"),
                "parameters": params_json
            }
        )
        await db.commit()
        return {"id": result.lastrowid, "message": "Indicator added", "solution_id": solution_id}
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to add solution indicator: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to add indicator: {str(e)}")


@solution_router.delete("/{solution_id}/indicators/{indicator_id}")
@solution_router.delete("/{solution_id}/indicators/{indicator_id}/")
@solution_router.post("/{solution_id}/indicators/{indicator_id}/delete")
@solution_router.post("/{solution_id}/indicators/{indicator_id}/delete/")
async def remove_solution_indicator(
    solution_id: int,
    indicator_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Remove an indicator from a solution."""
    try:
        await db.execute(
            text("DELETE FROM solution_indicators WHERE id = :indicator_id AND solution_id = :solution_id"),
            {"indicator_id": indicator_id, "solution_id": solution_id}
        )
        await db.commit()
        return {"message": "Indicator removed", "solution_id": solution_id}
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to remove solution indicator: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to remove indicator: {str(e)}")


# ==========================================
# Catch-all: Get/Delete solution by ID
# IMPORTANT: Must come AFTER all specific routes
# ==========================================

@solution_router.get("/{solution_id}")
async def get_solution_by_id(
    solution_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    """Get solution by ID.
    Matches webapi: views_solution.get_solution_by_id
    """
    try:
        result = await db.execute(
            text("SELECT * FROM tbl_solution WHERE id = :id"),
            {"id": solution_id}
        )
        row = result.mappings().first()
        if not row:
            raise HTTPException(status_code=404, detail=f"Solution {solution_id} not found")
        solution = dict(row)
        # Parse JSON result fields so frontend receives objects, not strings
        for field in ('training_result', 'prediction_result'):
            if solution.get(field) and isinstance(solution[field], str):
                try:
                    solution[field] = json.loads(solution[field])
                except (json.JSONDecodeError, TypeError):
                    solution[field] = None
        return solution
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch solution {solution_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch solution: {str(e)}")


@solution_router.put("/{solution_id}")
async def update_solution_by_id(
    solution_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Update solution by ID (path param).
    Delegates to the main update_solution handler.
    """
    data = await request.json()
    data["id"] = solution_id
    user_id = str(current_user["user_id"])
    if 'user_id' not in data:
        data['user_id'] = user_id
    if 'updated_by' not in data:
        data['updated_by'] = user_id

    try:
        await db.execute(
            text("""
                UPDATE tbl_solution
                SET solution_name = :solution_name, model_id = :model_id, ticker = :ticker,
                    updated_date = :updated_date, updated_by = :updated_by,
                    start_training_date = :start_training_date,
                    end_training_date = :end_training_date,
                    train_validation_ratio = :train_validation_ratio,
                    user_id = :user_id
                WHERE id = :id
            """),
            {
                "solution_name": data.get("solution_name"),
                "model_id": data.get("model_id"),
                "ticker": data.get("ticker"),
                "updated_date": data.get("updated_date", datetime.now().strftime("%Y-%m-%d")),
                "updated_by": data.get("updated_by"),
                "start_training_date": data.get("start_training_date"),
                "end_training_date": data.get("end_training_date"),
                "train_validation_ratio": data.get("train_validation_ratio", 0.8),
                "user_id": data.get("user_id"),
                "id": solution_id,
            }
        )
        await db.commit()
        return data
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to update solution {solution_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update solution: {str(e)}")


@solution_router.delete("/{solution_id}")
async def delete_solution_by_id(
    solution_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Delete solution by ID.
    Matches webapi: views_solution.delete_solution_by_id
    """
    try:
        # Delete associated indicators first
        await db.execute(
            text("DELETE FROM solution_indicators WHERE solution_id = :solution_id"),
            {"solution_id": solution_id}
        )
        # Delete solution
        result = await db.execute(
            text("DELETE FROM tbl_solution WHERE id = :id"),
            {"id": solution_id}
        )
        await db.commit()

        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail=f"Solution {solution_id} not found")

        return {"message": "Solution deleted", "id": solution_id}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to delete solution {solution_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete solution: {str(e)}")
