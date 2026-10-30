"""A Darts training core for solutions (Backlog #109, Phase 2).

Pure functions only — no database, no HTTP, no filesystem. The orchestration in
`api/solution_routes.py` keeps all the I/O, so everything here is testable
offline, which is how the project's other stats modules are built
(`event-reaction-lib` follows the same rule).

This sits BESIDE the existing tabular pipeline rather than replacing it. That
pipeline works, so the Darts path is selected explicitly and a regression is
one flag away from being undone.

Why Darts at all, when the tabular path already trains
------------------------------------------------------
The catalogue advertises fourteen architectures that `DARTS_TO_ML_MAP` resolved
to three gradient boosters with different hyperparameters. Those are real
models but they are not BlockRNN or TFT, and a result labelled "TFT" that is
LightGBM misleads whoever reads it. Darts supplies the real architectures and,
more importantly here, the **past/future covariate API** the Solutions UI was
already built around.

THE COVARIATE RULE THIS MODULE ENFORCES
---------------------------------------
A **future** covariate must be known over the forecast horizon at prediction
time. Darts enforces this structurally: a future covariate series has to extend
beyond the end of the target, or `fit`/`predict` raises.

A technical indicator cannot satisfy that. SMA, RSI, MACD and Bollinger are
deterministic functions of price, so knowing them over the horizon means
knowing future prices. Feeding one as a future covariate is look-ahead bias
with extra steps (Backlog #104, #105).

So:
  * indicators  -> PAST covariates only;
  * calendar features (day-of-week, month, day-of-month) -> FUTURE covariates,
    because they are genuinely known in advance for any future date;
  * an indicator marked `future` by the operator is REFUSED, loudly.

Refusing is deliberate. Silently demoting it to a past covariate would be the
same class of behaviour this codebase has been removing all week: a quiet
decision nobody can see. `CovariateError` names the offending indicators so the
operator can fix the solution.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

#: Minimum rows a model needs beyond its input window before training is
#: worth attempting. Below this the fit succeeds and means nothing.
MIN_TRAINING_WINDOWS = 50


class DartsTrainingError(RuntimeError):
    """Training cannot proceed. Carries an operator-readable reason."""


class CovariateError(DartsTrainingError):
    """A covariate assignment that cannot be honoured without leaking."""


#: Per-architecture window defaults, in trading days. `input_chunk_length` is
#: the lookback each model reads; `output_chunk_length` is how far it predicts
#: in one shot.
#:
#: These are sized for THIS data, not copied from the Darts tutorials: a
#: three-year request yields roughly 700 usable bars, so a 60-bar window leaves
#: about 640 training windows. Tutorials routinely use 2-4x these on datasets
#: ten times the size. Overriding is per-solution via config_json.
DEFAULT_WINDOWS: Dict[str, Tuple[int, int]] = {
    "BlockRNN":     (30, 5),
    "RNN":          (30, 1),    # RNNModel predicts one step at a time
    "TCN":          (30, 5),
    "Transformer":  (30, 5),
    "TFT":          (30, 5),
    "NBeats":       (30, 5),
    "NHits":        (30, 5),
    "DLinear":      (30, 5),
    "NLinear":      (30, 5),
    "TiDE":         (30, 5),
    # Regression models take `lags` rather than a chunk length; the first value
    # is reused as the lag count so one config shape covers every model.
    "XGBoost":      (30, 5),
    "LightGBM":     (30, 5),
    "RandomForest": (30, 5),
    "CatBoost":     (30, 5),
}

#: Models that take `lags`/`lags_past_covariates` instead of chunk lengths.
#: Their covariate capability is CONSTRUCTION-dependent, verified against darts
#: 0.48.1: XGBModel(lags=12) reports (past=0, future=0), and only gains each
#: capability when the matching `lags_*_covariates` argument is supplied. So the
#: operator's covariate choice has to reach the constructor, not just the fit.
REGRESSION_MODELS = frozenset({"XGBoost", "LightGBM", "RandomForest", "CatBoost"})


@dataclass(frozen=True)
class CovariatePlan:
    """What will actually be fed to the model, after the rules above."""
    past_columns: Tuple[str, ...] = ()
    future_columns: Tuple[str, ...] = ()
    refused: Tuple[str, ...] = ()
    calendar_features: Tuple[str, ...] = ()

    @property
    def uses_past(self) -> bool:
        return bool(self.past_columns)

    @property
    def uses_future(self) -> bool:
        return bool(self.future_columns)


@dataclass
class TrainingWindow:
    """The chronological split, reported so a reader can audit it."""
    total_rows: int
    train_rows: int
    validation_rows: int
    input_chunk_length: int
    output_chunk_length: int
    train_end: Optional[str] = None
    validation_start: Optional[str] = None
    warnings: List[str] = field(default_factory=list)


def plan_covariates(
    indicator_columns: Sequence[str],
    covariate_types: Dict[str, str],
    *,
    model_supports_future: bool,
    model_supports_past: bool = True,
    allow_calendar_future: bool = True,
) -> CovariatePlan:
    """Decide which series become past covariates and which become future ones.

    `covariate_types` maps an indicator column to `past`, `future` or `both` as
    the operator chose it on the solution.

    An indicator marked `future` (or `both`) is REFUSED rather than demoted,
    because a price-derived series cannot be known over the horizon. The caller
    turns `CovariateError` into a failed training run naming the indicators, so
    the operator can correct the solution instead of silently getting something
    other than what they asked for.
    """
    past: List[str] = []
    refused: List[str] = []

    for col in indicator_columns:
        kind = (covariate_types.get(col) or "past").strip().lower()
        if kind in ("past", ""):
            past.append(col)
        elif kind in ("future", "both"):
            # `both` is refused for the same reason as `future`: honouring half
            # of it silently would be worse than refusing it.
            refused.append(col)
        else:
            raise CovariateError(
                f"indicator {col!r} has covariate_type {kind!r}; expected "
                f"'past', 'future' or 'both'")

    if refused:
        raise CovariateError(
            "these indicators are marked as future covariates: "
            + ", ".join(sorted(refused))
            + ". A future covariate must be KNOWN over the forecast horizon, and "
              "a technical indicator is a function of price, so its future "
              "values are not knowable without the future prices. Mark them "
              "'past', or use calendar features for genuine future covariates.")

    # Found in Phase 2b by fitting, not by reading: RNNModel accepts FUTURE
    # covariates and NOT past ones (verified against darts 0.48.1). Since a
    # technical indicator can only ever be a past covariate, an RNN solution
    # with indicators attached cannot use them at all. Dropping them silently
    # would mean the operator configured four indicators and got a model that
    # never saw one — so this refuses, for the same reason a future-marked
    # indicator is refused above.
    if past and not model_supports_past:
        raise CovariateError(
            "this model accepts only FUTURE covariates, but the solution "
            "attaches indicators, which can only be past covariates: "
            + ", ".join(sorted(past))
            + ". Those indicators would be ignored entirely. Choose a model "
              "that takes past covariates, or remove them from the solution.")

    calendar: Tuple[str, ...] = ()
    future: List[str] = []
    if model_supports_future and allow_calendar_future:
        calendar = ("dayofweek", "month", "day")
        future = list(calendar)

    return CovariatePlan(
        past_columns=tuple(past),
        future_columns=tuple(future),
        refused=(),
        calendar_features=calendar,
    )


def calendar_frame(index: pd.DatetimeIndex) -> pd.DataFrame:
    """Genuinely-known-ahead features for any date, future dates included.

    This is what a future covariate legitimately looks like: the values for
    next month are computable today because they depend on the calendar and
    nothing else.
    """
    return pd.DataFrame(
        {
            "dayofweek": index.dayofweek.astype("float64"),
            "month": index.month.astype("float64"),
            "day": index.day.astype("float64"),
        },
        index=index,
    )


def extend_index(index: pd.DatetimeIndex, periods: int) -> pd.DatetimeIndex:
    """`periods` business days beyond `index`, for building future covariates.

    Darts requires a future covariate to cover the forecast horizon, so the
    calendar series must run past the end of the target.
    """
    if periods <= 0 or len(index) == 0:
        return index
    extra = pd.bdate_range(index[-1] + pd.Timedelta(days=1), periods=periods)
    return index.append(extra)


def resolve_windows(
    model_type: str,
    config: Optional[dict],
    available_rows: int,
) -> TrainingWindow:
    """Window lengths for this model, clamped to what the data can support.

    The clamp matters and is reported rather than applied quietly: a 60-bar
    window on 700 rows is fine, the same window on 90 rows is not, and a model
    that silently trains on eight windows produces numbers that look like
    results.
    """
    base_in, base_out = DEFAULT_WINDOWS.get(model_type, (30, 5))
    cfg = config or {}
    icl = int(cfg.get("input_chunk_length", base_in))
    ocl = int(cfg.get("output_chunk_length", base_out))
    warnings: List[str] = []

    if icl < 1 or ocl < 1:
        raise DartsTrainingError(
            f"input/output chunk lengths must be positive, got {icl}/{ocl}")

    # Each training window consumes icl + ocl rows.
    usable = available_rows - (icl + ocl)
    if usable < MIN_TRAINING_WINDOWS:
        shrunk = max(5, (available_rows - ocl - MIN_TRAINING_WINDOWS))
        if shrunk < icl:
            warnings.append(
                f"input_chunk_length reduced {icl} -> {shrunk}: {available_rows} "
                f"rows cannot support {MIN_TRAINING_WINDOWS} training windows at "
                f"the requested length")
            icl = shrunk
        usable = available_rows - (icl + ocl)
    if usable < MIN_TRAINING_WINDOWS:
        raise DartsTrainingError(
            f"only {available_rows} usable rows: not enough for {MIN_TRAINING_WINDOWS} "
            f"training windows even at the shortest sensible lookback. Request a "
            f"longer date range or choose fewer long-warm-up indicators.")

    return TrainingWindow(
        total_rows=available_rows,
        train_rows=0,
        validation_rows=0,
        input_chunk_length=icl,
        output_chunk_length=ocl,
        warnings=warnings,
    )


def chronological_split(
    index: pd.DatetimeIndex, train_ratio: float
) -> Tuple[int, Optional[str], Optional[str]]:
    """`(split_index, train_end, validation_start)` — never shuffled.

    Shuffling a time series leaks the future into the past. The existing
    tabular pipeline gets this right (`train_test_split(..., shuffle=False)`)
    and so does this one; stated because it is the single easiest thing to get
    wrong here.
    """
    if not 0.0 < train_ratio < 1.0:
        raise DartsTrainingError(f"train_ratio must be in (0, 1), got {train_ratio}")
    n = len(index)
    split = int(n * train_ratio)
    if split < 1 or split >= n:
        raise DartsTrainingError(
            f"train_ratio {train_ratio} leaves {split} training rows of {n}")
    return (
        split,
        index[split - 1].strftime("%Y-%m-%d"),
        index[split].strftime("%Y-%m-%d"),
    )


def evaluate(actual: Sequence[float], predicted: Sequence[float]) -> Dict[str, float]:
    """RMSE / MAE / R² / direction accuracy on the held-out slice.

    Direction is measured against the PREVIOUS ACTUAL value, which is the
    question a trader asks ("up or down from here?"). Computing it from
    consecutive predictions instead would score the model's own smoothness.
    """
    a = np.asarray(actual, dtype="float64")
    p = np.asarray(predicted, dtype="float64")
    if a.shape != p.shape or a.size == 0:
        raise DartsTrainingError(
            f"cannot evaluate {a.size} actuals against {p.size} predictions")

    err = p - a
    rmse = float(np.sqrt(np.mean(err ** 2)))
    mae = float(np.mean(np.abs(err)))
    sst = float(np.sum((a - a.mean()) ** 2))
    r2 = float(1.0 - np.sum(err ** 2) / sst) if sst > 0 else float("nan")

    if a.size > 1:
        actual_dir = np.sign(a[1:] - a[:-1])
        pred_dir = np.sign(p[1:] - a[:-1])
        moved = actual_dir != 0
        direction = (float(np.mean(actual_dir[moved] == pred_dir[moved]) * 100.0)
                     if moved.any() else float("nan"))
    else:
        direction = float("nan")

    return {"rmse": rmse, "mae": mae, "r2": r2, "direction_accuracy": direction}


def naive_baseline(actual: Sequence[float], last_train_value: float) -> Dict[str, float]:
    """The benchmark CLAUDE.md C4 requires, computed on the same slice.

    "Tomorrow equals today" explains almost all the variance of a price LEVEL,
    so an R² near 1 proves nothing on its own. Reporting this beside the model
    is what makes the model's number readable — and on this project's own data
    the naive R² came out 0.9943 against a model's 0.9954.
    """
    a = np.asarray(actual, dtype="float64")
    carried = np.concatenate(([last_train_value], a[:-1]))
    return evaluate(a, carried)


# ---------------------------------------------------------------------------
# Model construction (Backlog #109 Phase 2b)
# ---------------------------------------------------------------------------
#
# Each architecture has a different signature, which is the whole reason this
# lives in one audited place rather than in the route handler:
#
#   * RNNModel takes NO output_chunk_length — it predicts one step at a time
#     and uses `training_length` instead;
#   * TFTModel requires future covariates OR `add_relative_index=True`,
#     otherwise it raises at fit;
#   * the regression models take `lags` / `lags_past_covariates` /
#     `lags_future_covariates`, and their covariate capability only exists if
#     those arguments are supplied — verified against darts 0.48.1, where
#     XGBModel(lags=12) reports (past=0, future=0).
#
# So the covariate PLAN has to reach the constructor, not just the fit call.

#: Keep every torch fit on CPU and quiet. The host has an RTX 3060 and Docker
#: exposes the nvidia runtime, so switching to "gpu" is a one-word change — but
#: the image ships CPU-only torch deliberately (Backlog #109), and a model that
#: silently fell back to CPU while claiming GPU would be worse than an explicit
#: setting.
CPU_TRAINER_KWARGS = {
    "accelerator": "cpu",
    "enable_progress_bar": False,
    "enable_model_summary": False,
    "logger": False,
}

DEFAULT_EPOCHS = 20


def build_model(
    model_type: str,
    window: TrainingWindow,
    plan: CovariatePlan,
    config: Optional[dict] = None,
):
    """Construct the real Darts model for `model_type`.

    Raises `DartsTrainingError` with a readable reason rather than letting an
    ImportError or a TypeError from deep inside the library surface to the
    operator.
    """
    cfg = dict(config or {})
    icl = window.input_chunk_length
    ocl = window.output_chunk_length
    epochs = int(cfg.get("n_epochs", DEFAULT_EPOCHS))
    seed = int(cfg.get("random_state", 42))

    torch_kwargs = dict(
        input_chunk_length=icl,
        output_chunk_length=ocl,
        n_epochs=epochs,
        random_state=seed,
        pl_trainer_kwargs=dict(CPU_TRAINER_KWARGS),
    )

    try:
        if model_type in REGRESSION_MODELS:
            return _build_regression(model_type, icl, ocl, plan, cfg)
        return _build_torch(model_type, torch_kwargs, icl, epochs, seed)
    except DartsTrainingError:
        raise
    except ImportError as exc:
        raise DartsTrainingError(
            f"{model_type} needs a package that is not installed: {exc}. "
            f"Install it or remove {model_type} from the catalogue."
        ) from exc
    except Exception as exc:  # noqa: BLE001 — the library raises many types
        raise DartsTrainingError(
            f"could not construct {model_type}: {type(exc).__name__}: {exc}"
        ) from exc


def _build_torch(model_type: str, kwargs: dict, icl: int, epochs: int, seed: int):
    from darts.models import (
        BlockRNNModel,
        DLinearModel,
        NBEATSModel,
        NHiTSModel,
        NLinearModel,
        RNNModel,
        TCNModel,
        TFTModel,
        TiDEModel,
        TransformerModel,
    )

    if model_type == "RNN":
        # No output_chunk_length: RNNModel is recurrent and forecasts one step
        # at a time, driven by `training_length`.
        return RNNModel(
            input_chunk_length=icl,
            training_length=max(icl + 1, icl * 2),
            n_epochs=epochs,
            random_state=seed,
            pl_trainer_kwargs=dict(CPU_TRAINER_KWARGS),
        )
    if model_type == "TFT":
        # TFT needs SOME future input. `add_relative_index` supplies a
        # positional index so it can fit when no genuine future covariate is
        # available — which is the common case here, since indicators cannot be
        # future covariates.
        return TFTModel(add_relative_index=True, **kwargs)

    builders = {
        "BlockRNN": BlockRNNModel,
        "TCN": TCNModel,
        "Transformer": TransformerModel,
        "NBeats": NBEATSModel,
        "NHits": NHiTSModel,
        "DLinear": DLinearModel,
        "NLinear": NLinearModel,
        "TiDE": TiDEModel,
    }
    if model_type not in builders:
        raise DartsTrainingError(f"no Darts constructor for model type {model_type!r}")
    return builders[model_type](**kwargs)


def _build_regression(model_type: str, icl: int, ocl: int, plan: CovariatePlan, cfg: dict):
    from darts.models import CatBoostModel, LightGBMModel, RandomForest, XGBModel

    # The covariate arguments are what GRANT the capability, so they are
    # supplied only when the plan actually has those series. Passing
    # lags_past_covariates with no past covariates makes fit() demand a series
    # that does not exist.
    kwargs: Dict[str, object] = {"lags": icl, "output_chunk_length": ocl}
    if plan.uses_past:
        kwargs["lags_past_covariates"] = icl
    if plan.uses_future:
        # Future lags may reach forward; 0 means "the value at the predicted
        # step", which is the point of a known-ahead series.
        kwargs["lags_future_covariates"] = (icl, ocl)

    builders = {
        "XGBoost": XGBModel,
        "LightGBM": LightGBMModel,
        "RandomForest": RandomForest,
        "CatBoost": CatBoostModel,
    }
    if model_type not in builders:
        raise DartsTrainingError(f"no Darts constructor for model type {model_type!r}")
    if model_type == "LightGBM":
        kwargs["verbose"] = -1
    for key in ("n_estimators", "max_depth", "learning_rate"):
        if key in cfg:
            kwargs[key] = cfg[key]
    return builders[model_type](**kwargs)


# ---------------------------------------------------------------------------
# Orchestration (Backlog #109 Phase 2b)
# ---------------------------------------------------------------------------

# --------------------------------------------------------------------------
# Scaling (found by the first real run, not by the tests)
# --------------------------------------------------------------------------
#: Columns handed to these models span wildly different magnitudes: a price of
#: ~20, an RSI of 0-100, a MACD near 0, and a volume in the millions. A
#: gradient-boosted tree splits on each column independently and does not
#: care. A neural network does: with raw inputs the first layer saturates and
#: the output collapses onto its bias.
#:
#: That is not a hypothesis. The first real BlockRNN run on ACB produced
#: forecasts with sd 0.18 around a flat 19.44 while the actuals moved
#: 20.15 -> 22.80 (sd 0.79) — a near-constant, which is also why the
#: one-step-ahead and whole-span protocols returned the SAME rmse to four
#: decimals. Missing normalisation is a pipeline defect, not model tuning.
#:
#: THE SCALER IS FITTED ON THE TRAINING SPAN ONLY (C1). Fitting it on the full
#: series would leak the validation span's min/max into training — the
#: textbook preprocessing leak, and invisible in the metrics because it makes
#: them look better. `scale_for_training` takes `split` for exactly this
#: reason and `test_scaler_is_fitted_on_training_span_only` mutates the
#: validation tail to prove the training values do not move.


def scale_for_training(series, split: int):
    """Return `(scaled_series, scaler)` with the scaler fitted on `[:split]`.

    Uniform across model families on purpose: scaling is neutral for trees and
    load-bearing for networks, so one path is simpler than a per-model branch
    and every engine's numbers stay comparable.
    """
    from darts.dataprocessing.transformers import Scaler

    if series is None:
        return None, None
    scaler = Scaler()
    scaler.fit(series[:split])
    return scaler.transform(series), scaler


def run_darts_training(
    feature_df: pd.DataFrame,
    *,
    model_type: str,
    indicator_columns: Sequence[str],
    covariate_types: Dict[str, str],
    train_ratio: float = 0.8,
    config: Optional[dict] = None,
    price_column: str = "close",
) -> Dict[str, object]:
    """Fit one Darts model on a prepared frame and report auditable results.

    Still free of I/O: the caller supplies the frame and persists whatever comes
    back. `feature_df` must be indexed by date, contain `price_column`, and
    carry one column per entry in `indicator_columns`.

    The target is the price LEVEL, matching the existing tabular pipeline so the
    two engines stay comparable. Note what that means for reading the output:
    on levels a carried-forward baseline is already near-perfect, which is why
    `naive` is returned beside `metrics` rather than left to the reader to
    construct (CLAUDE.md C4).
    """
    # Validate the inputs BEFORE importing darts, so a malformed frame is
    # reported as such even where the library is absent (it ships in the
    # service image, not on a developer host). Input validation that needs a
    # heavy optional dependency is validation nobody runs.
    if price_column not in feature_df.columns:
        raise DartsTrainingError(f"frame has no {price_column!r} column")
    if not isinstance(feature_df.index, pd.DatetimeIndex):
        raise DartsTrainingError("feature_df must be indexed by date")

    frame = feature_df.sort_index()
    missing = [c for c in indicator_columns if c not in frame.columns]
    if missing:
        raise DartsTrainingError(f"indicator columns absent from the frame: {missing}")

    from darts import TimeSeries

    # 1. What may be fed to this model, given what it can accept.
    caps_past, caps_future = _model_capabilities(model_type)
    plan = plan_covariates(
        list(indicator_columns), covariate_types,
        model_supports_future=caps_future, model_supports_past=caps_past)

    # 2. Windows, clamped to the data and reported.
    window = resolve_windows(model_type, config, len(frame))
    split, train_end, val_start = chronological_split(frame.index, train_ratio)
    window.train_rows, window.validation_rows = split, len(frame) - split
    window.train_end, window.validation_start = train_end, val_start

    if window.validation_rows <= window.output_chunk_length:
        raise DartsTrainingError(
            f"only {window.validation_rows} validation rows for an "
            f"output_chunk_length of {window.output_chunk_length}; lower "
            f"train_ratio or shorten the output window")

    # 3. Series, on a POSITIONAL index rather than the calendar.
    #
    # Found by running real data after synthetic tests passed: Darts requires a
    # regular frequency, and real trading bars do not have one. A business-day
    # index survives weekends but not market holidays — Vietnamese Tet alone
    # breaks `B` inference — and darts raises
    #     "The time index is missing the `freq` attribute, and the frequency
    #      could not be directly inferred"
    # My tests used pd.bdate_range, which has a clean freq, so they could never
    # have caught this.
    #
    # Filling the holidays would mean inventing price bars. Instead the series
    # are indexed by BAR NUMBER, which is what the models actually mean: an
    # `input_chunk_length` of 30 is thirty trading bars, not thirty calendar
    # days. Calendar covariates keep their meaning because their VALUES still
    # come from each bar's real date (below); only the index is positional.
    # `frame.index` is retained for reporting, so output rows still carry dates.
    n_rows = len(frame)
    target = TimeSeries.from_values(
        frame[price_column].astype("float64").to_numpy())
    past_cov = (TimeSeries.from_values(
        frame[list(plan.past_columns)].astype("float64").to_numpy())
        if plan.uses_past else None)
    future_cov = None
    if plan.uses_future:
        # Values from the real dates, extended by business days past the end so
        # the series covers the forecast horizon as Darts requires.
        extended = extend_index(frame.index, window.output_chunk_length + 1)
        future_cov = TimeSeries.from_values(
            calendar_frame(extended).to_numpy()[: n_rows + window.output_chunk_length + 1])

    # 3b. Scale, with every scaler fitted on the TRAINING SPAN ONLY (C1).
    target, target_scaler = scale_for_training(target, split)
    past_cov, _ = scale_for_training(past_cov, split)
    future_cov, _ = scale_for_training(future_cov, split)

    train_target = target[:split]

    # 4. Fit on the training span only.
    model = build_model(model_type, window, plan, config)
    fit_kwargs: Dict[str, object] = {}
    if past_cov is not None:
        fit_kwargs["past_covariates"] = past_cov
    if future_cov is not None:
        fit_kwargs["future_covariates"] = future_cov
    model.fit(train_target, **fit_kwargs)

    # 5. ONE-STEP-AHEAD forecasts across the held-out span.
    #
    # Corrected after the first real run. `predict(53)` forecasts the entire
    # validation span in a single call, so the model extends auto-regressively
    # on its own output and the error compounds: BlockRNN scored r2 = -8.93
    # against a naive 0.86, which reads as a catastrophic model and is really a
    # different, far harder task. The tabular engine makes 53 separate
    # one-step-ahead forecasts, so comparing the two that way was meaningless.
    #
    # `historical_forecasts` with forecast_horizon=1 and retrain=False walks the
    # validation span re-anchoring on each ACTUAL bar — the same question the
    # tabular engine answers, and the same question a trader asks.
    horizon = window.validation_rows
    hf = model.historical_forecasts(
        target,
        **fit_kwargs,
        start=split,
        forecast_horizon=1,
        stride=1,
        retrain=False,
        last_points_only=True,
        verbose=False,
    )
    # Back to price units before anything is measured or reported, so the
    # metrics and the payload are in the same units as the tabular engine's.
    predicted = np.asarray(
        target_scaler.inverse_transform(hf).values(), dtype="float64").ravel()
    actual = frame[price_column].iloc[split:split + len(predicted)].to_numpy(dtype="float64")
    cut = min(len(actual), len(predicted))
    actual, predicted = actual[:cut], predicted[:cut]
    if cut == 0:
        raise DartsTrainingError(
            "historical_forecasts produced no points; the validation span may be "
            "shorter than the model's lookback")

    metrics = evaluate(actual, predicted)
    naive = naive_baseline(actual, float(frame[price_column].iloc[split - 1]))

    dates = frame.index[split:split + len(actual)]
    predictions = [
        {
            "date": d.strftime("%Y-%m-%d"),
            "actual_price": float(a),
            "predicted_price": float(p),
            "in_sample": False,
        }
        for d, a, p in zip(dates, actual, predicted)
    ]

    return {
        "engine": "darts",
        "model_type": model_type,
        "metrics": metrics,
        # C4: the benchmark travels WITH the figure it must beat, so a reader
        # cannot see r2 without seeing what "tomorrow = today" scores.
        "naive": naive,
        "beats_naive_rmse": bool(metrics["rmse"] < naive["rmse"]),
        "covariates": {
            "past": list(plan.past_columns),
            "future": list(plan.future_columns),
        },
        "data_accounting": {
            "rows_used": int(len(frame)),
            "training_samples": window.train_rows,
            "validation_samples": window.validation_rows,
            "input_chunk_length": window.input_chunk_length,
            "output_chunk_length": window.output_chunk_length,
            "train_end_date": window.train_end,
            "validation_start_date": window.validation_start,
            "window_warnings": list(window.warnings),
        },
        "predictions": predictions,
    }


def _model_capabilities(model_type: str) -> Tuple[bool, bool]:
    """What this architecture can accept, from the hand-kept table.

    Deliberately NOT read from a constructed Darts instance: for the regression
    models the answer depends on the arguments we are about to choose, so
    asking the library first would be circular. The table expresses the
    ceiling; `build_model` then supplies only the lags the plan justifies.
    """
    from app.api.model_capabilities import covariate_support

    return covariate_support(model_type)
