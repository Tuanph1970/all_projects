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
