#!/usr/bin/env python3
"""Drive the full create -> indicators -> train -> PREDICT round trip per model.

A PRE-RELEASE USAGE SWEEP. Backend API only, through the gateway, against the
price history already in the database — no frontend, no fixtures, no mocks.

HOW THIS DIFFERS FROM tests/model_sweep.py, which already sweeps 14 models x 2
engines: that sweep tunes the model to keep training honest (it sends epochs, a
per-family learning rate, a short input chunk) and it stops at TRAINING. It asks
"does every architecture train and report itself truthfully?".

This script asks the other question, the one a release needs answered:

    a user who changes NOTHING — takes the default parameters, picks four
    indicators off the four dropdowns, trains on a couple of years and then
    presses Predict — does anything break in front of them?

So every departure from that user's path is deliberate:

  * PARAMETERS ARE THE SERVER'S OWN DEFAULTS, fetched from
    GET /models/parameters/default-values and sent back unmodified. Not a config
    this script invented. If a model type has no defaults row, that is reported
    rather than papered over with a guess — the Solutions form has nothing to
    pre-fill in that case either.
  * THE ENGINE IS NOT SENT, because the Solutions UI does not send one
    (TrainingSolution.js formSubmit). Whatever DEFAULT_TRAINING_ENGINE is at the
    time is what a real user gets, and that is what must work.
  * THE INDICATORS ARE RANDOM, one from each of the four groups the selector
    offers (IndicatorSelector.js: trend / momentum / volatility / volume), with
    each indicator's own default parameters. Random because a bug that only
    appears for ICHIMOKU-plus-STOCH_RSI is still a bug a user will find; the
    seed is printed so any failure can be replayed exactly.
  * THE PREDICTION WINDOW IS THE MODEL'S OWN HORIZON: start = the business day
    after the last training day, end = start + output_chunk_length - 1 business
    days, which is what PredictSolution.js fills in for the user.

WHAT COUNTS AS A FAILURE HERE IS NOT A BAD FORECAST. The numbers are allowed to
be terrible — this is a 300-epoch default on two years of one ticker. A cell
fails when the APPLICATION misbehaves: a step 4xx/5xx-es, training never
finishes, the stored indicators are not the ones chosen, the horizon the service
returns is not the horizon that was asked for, a payload the UI reads is absent,
or a value that must be a number is null, negative or not finite.

USAGE
    python tests/predict_roundtrip.py --help
    python tests/predict_roundtrip.py --token "$TOK"              # default 7 models
    python tests/predict_roundtrip.py --token "$TOK" --models xgboost
    python tests/predict_roundtrip.py --token "$TOK" --other-half # the other 7
    python tests/predict_roundtrip.py --token "$TOK" --engine tabular
    python tests/predict_roundtrip.py --token "$TOK" --seed 7 --keep

A token comes from scripts/mint_test_token.py, or pass --email/--password.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import random
import statistics
import sys
import time
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any, Iterable, Optional

import urllib.error
import urllib.request

# ---------------------------------------------------------------------------
# The matrix
# ---------------------------------------------------------------------------

#: URL names accepted by POST /models/{name}; mirrors MODEL_TYPE_MAP in
#: app/api/routes.py. Same literal as model_sweep.MODEL_URL_NAMES, and
#: tests/test_predict_roundtrip.py fails if the two drift apart or if either
#: drifts from the server's map — so an architecture cannot quietly stop being
#: swept.
MODEL_URL_NAMES = (
    "blockrnn", "rnn", "tcn", "transformer", "tft", "nbeats", "nhits",
    "dlinear", "nlinear", "xgboost", "lightgbm", "randomforest",
    "catboost", "tide",
)

#: HALF the catalogue, which is what was asked for. Chosen to span the two
#: families rather than to be the first seven alphabetically: four neural
#: architectures (which train through torch and own an input/output chunk) and
#: three tree ensembles (which are lag-based and whose default horizon is 1).
#: A bug in either family's plumbing shows up in this half.
DEFAULT_HALF = ("blockrnn", "tcn", "nbeats", "dlinear",
                "xgboost", "lightgbm", "randomforest")
OTHER_HALF = tuple(n for n in MODEL_URL_NAMES if n not in DEFAULT_HALF)

#: The four dropdowns of the solution's indicator selector, in the order the UI
#: lays them out. The endpoint returns more groups than this (support_resistance,
#: price_transform, bill_williams); the selector offers exactly these four, so
#: these four are what a user can actually choose and what gets swept.
INDICATOR_GROUPS = ("trend", "momentum", "volatility", "volume")

#: Request-body key per group, as IndicatorSelector.handleSave builds it.
GROUP_REQUEST_KEY = {g: f"{g}_indicator" for g in INDICATOR_GROUPS}

#: Backlog #105 — an indicator is always a PAST covariate, and the selector no
#: longer offers the choice. Sent explicitly so the sweep exercises the same
#: body the UI sends rather than relying on the server's default.
COVARIATE_TYPE = "past"

#: Two years of calendar history, as the brief specifies ("2 year data for
#: example"). Trading days are ~250/year, so this is ~500 rows before any
#: indicator warm-up is deducted.
TRAINING_WINDOW_DAYS = 730

#: What PredictSolution.js falls back to when the trained model reports no
#: horizon, and what the backend's own prediction_dates block uses.
FALLBACK_HORIZON = 10

DEFAULT_GATEWAY = os.environ.get("GATEWAY_URL", "http://localhost:18004")
PREFIX = "/stock_helper/api/v2"


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------

class ApiError(RuntimeError):
    """A transport or HTTP-status failure, carrying the status for judging.

    The status matters to the caller and not only to the message: a 400 from
    /solutions/predict is a user-visible application bug, while a 429 is the
    gateway pacing this script and means nothing about the service.
    """

    def __init__(self, message: str, status: Optional[int] = None):
        super().__init__(message)
        self.status = status


class Api:
    #: The gateway rate-limits (traefik/dynamic.yml: ~100/min, 30/min on some
    #: routes). A 429 is the GATEWAY talking, not the service failing, so it is
    #: retried rather than reported — model_sweep.py learned this the hard way
    #: when a full run produced 26 phantom failures.
    RATE_LIMIT_RETRIES = 6

    def __init__(self, gateway: str, token: str, timeout: float = 180.0):
        self.base = gateway.rstrip("/") + PREFIX
        self.token = token
        self.timeout = timeout
        self.calls = 0

    def _call(self, method: str, path: str, body: Optional[dict] = None) -> Any:
        url = self.base + path
        data = json.dumps(body).encode() if body is not None else None
        delay = 5.0
        for attempt in range(self.RATE_LIMIT_RETRIES + 1):
            req = urllib.request.Request(url, data=data, method=method)
            req.add_header("Authorization", f"Bearer {self.token}")
            if data:
                req.add_header("Content-Type", "application/json")
            try:
                self.calls += 1
                with urllib.request.urlopen(req, timeout=self.timeout) as r:
                    raw = r.read().decode()
                    return json.loads(raw) if raw.strip() else {}
            except urllib.error.HTTPError as e:
                if e.code == 429 and attempt < self.RATE_LIMIT_RETRIES:
                    wait = delay
                    try:
                        wait = max(wait, float(e.headers.get("Retry-After") or 0))
                    except (TypeError, ValueError):
                        pass
                    time.sleep(wait)
                    delay = min(delay * 2, 60.0)
                    continue
                detail = e.read().decode()[:400]
                raise ApiError(f"HTTP {e.code} {method} {path}: {detail}",
                               status=e.code) from None
            except Exception as e:                   # noqa: BLE001
                raise ApiError(f"{type(e).__name__} {method} {path}: {e}") from None
        raise ApiError(f"rate-limited {method} {path} after "
                       f"{self.RATE_LIMIT_RETRIES} retries", status=429)

    def get(self, path: str) -> Any:
        return self._call("GET", path)

    def post(self, path: str, body: Optional[dict] = None) -> Any:
        return self._call("POST", path, body if body is not None else {})

    def delete(self, path: str) -> Any:
        return self._call("DELETE", path)


def login(gateway: str, email: str, password: str) -> str:
    req = urllib.request.Request(
        gateway.rstrip("/") + PREFIX + "/auth/login",
        data=json.dumps({"email": email, "password": password}).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=30) as r:
        tok = json.loads(r.read().decode()).get("access_token")
    if not tok:
        raise SystemExit("login returned no access_token")
    return tok


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------

def finite(x: Any) -> bool:
    try:
        return math.isfinite(float(x))
    except (TypeError, ValueError):
        return False


def as_int(x: Any) -> Optional[int]:
    """Defaults arrive as STRINGS ('10'), which is what the form posts."""
    try:
        return int(float(x))
    except (TypeError, ValueError):
        return None


def parse_day(s: Any) -> Optional[date]:
    if not s:
        return None
    text = str(s)[:10]
    try:
        return datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError:
        return None


def next_business_day(d: date) -> date:
    """The backend's own rule (solution_routes.py: `while weekday() >= 5`).

    No holiday calendar on either side, so this script must not invent one —
    the point is to ask for the window the UI would ask for.
    """
    nxt = d + timedelta(days=1)
    while nxt.weekday() >= 5:
        nxt += timedelta(days=1)
    return nxt


def add_business_days(d: date, n: int) -> date:
    out = d
    for _ in range(max(0, n)):
        out = next_business_day(out)
    return out


def first_id(payload: Any, *keys: str) -> Optional[int]:
    """Pull an id out of a payload whose shape differs per endpoint."""
    if not isinstance(payload, dict):
        return None
    nested = payload.get("data") if isinstance(payload.get("data"), dict) else {}
    for key in keys:
        for src in (payload, nested):
            if src.get(key) is not None:
                try:
                    return int(src[key])
                except (TypeError, ValueError):
                    continue
    return None


def values_of(points: Iterable[Any], *keys: str) -> list[float]:
    """Numeric series out of [{'tradingdate':..,'close':..}, ...] or [1,2,3]."""
    out: list[float] = []
    for row in points or []:
        if isinstance(row, dict):
            for k in keys:
                if k in row:
                    if finite(row[k]):
                        out.append(float(row[k]))
                    break
        elif finite(row):
            out.append(float(row))
    return out


# ---------------------------------------------------------------------------
# One model's round trip
# ---------------------------------------------------------------------------

@dataclass
class Run:
    url_name: str
    model_type: str = ""
    engine_asked: str = "(service default)"
    engine_ran: str = ""
    seconds: float = 0.0
    #: How far it got, so a table row says where it died without reading the log.
    stage: str = "start"
    indicators: dict = field(default_factory=dict)
    train_window: tuple[str, str] = ("", "")
    horizon: Optional[int] = None
    predict_window: tuple[str, str] = ("", "")
    #: Lengths of the four series the Prediction tab draws, for the report.
    series_sizes: dict = field(default_factory=dict)
    problems: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    metrics: dict = field(default_factory=dict)
    model_id: Optional[int] = None
    solution_id: Optional[int] = None

    @property
    def verdict(self) -> str:
        return "PASS" if not self.problems else "FAIL"


def pick_window(avail_start: Optional[date], avail_end: Optional[date],
                rng: random.Random, window_days: int) -> tuple[date, date]:
    """A random training range that still holds `window_days` of history.

    Randomised on purpose — a fixed range would hide anything that depends on
    where in the series the data sits. Bounded so the range is always INSIDE
    what the ticker actually has: a start before the first bar trains on less
    data than the brief requires and would make a thin-data failure look like a
    model failure.
    """
    today = date.today()
    hard_end = min(avail_end or today, today - timedelta(days=1))
    hard_start = avail_start or (hard_end - timedelta(days=window_days))
    earliest_end = hard_start + timedelta(days=window_days)
    if earliest_end >= hard_end:
        # Not enough history to slide the window: use everything available.
        return hard_start, hard_end
    slack = (hard_end - earliest_end).days
    end = hard_end - timedelta(days=rng.randint(0, slack))
    return end - timedelta(days=window_days), end


def choose_indicators(groups: dict, rng: random.Random) -> tuple[dict, list[str]]:
    """One indicator per dropdown, with that indicator's own defaults."""
    chosen: dict = {}
    missing: list[str] = []
    for group in INDICATOR_GROUPS:
        options = groups.get(group) or []
        if not options:
            missing.append(group)
            continue
        pick = rng.choice(options)
        chosen[group] = {
            "id": pick.get("id"),
            "name": pick.get("name"),
            "covariate_type": COVARIATE_TYPE,
            "parameters": pick.get("default_parameters") or {},
        }
    return chosen, missing


def judge_indicator_storage(run: Run, stored: Any) -> None:
    """What came back must be what was chosen.

    Worth checking because the write and the read are separate SQL paths over
    `solution_indicators`, and a silently dropped row trains a different model
    than the one the user configured — with nothing on screen to say so.
    """
    if not isinstance(stored, dict):
        run.problems.append(f"GET indicators returned {type(stored).__name__}, "
                            f"expected an object keyed by group")
        return
    for group, want in run.indicators.items():
        got = stored.get(group)
        if not isinstance(got, dict) or got.get("id") is None:
            run.problems.append(
                f"{group} indicator {want['name']} (id {want['id']}) was saved "
                f"but is absent from GET /solutions/<id>/indicators")
            continue
        if as_int(got.get("id")) != as_int(want["id"]):
            run.problems.append(
                f"{group} indicator came back as id {got.get('id')}, "
                f"saved id {want['id']} ({want['name']})")
        got_params = got.get("parameters")
        if isinstance(got_params, str):
            try:
                got_params = json.loads(got_params)
            except json.JSONDecodeError:
                pass
        if want["parameters"] and got_params != want["parameters"]:
            run.problems.append(
                f"{group} indicator parameters round-tripped as {got_params!r}, "
                f"saved {want['parameters']!r}")


def judge_training(run: Run, status: dict) -> dict:
    """Training has to finish, and the result has to carry usable numbers."""
    result = status.get("result") or {}
    metrics = dict(result)
    run.engine_ran = str(result.get("engine") or "")
    if not run.engine_ran:
        run.notes.append("training result does not name the engine that ran")

    for key in ("rmse", "mae", "r2"):
        if key not in result:
            run.problems.append(f"training result has no {key}")
        elif not finite(result[key]):
            run.problems.append(f"training {key}={result[key]!r} is not finite")

    # PREDICTION_DATES IS WHAT THE PREDICT TAB PRE-FILLS FROM. Its absence is
    # not a modelling flaw, it is the Predict form opening blank after a
    # successful training — exactly the class of defect this sweep is for.
    dates = result.get("prediction_dates")
    if not isinstance(dates, dict):
        run.problems.append(
            "training result carries no prediction_dates block, so the Predict "
            "tab has no start/end date to offer after training")
    else:
        declared = as_int(dates.get("output_chunk_length"))
        if declared is None:
            run.notes.append("prediction_dates has no output_chunk_length")
        elif run.horizon is not None and declared != run.horizon:
            run.problems.append(
                f"prediction_dates.output_chunk_length={declared} but the "
                f"model was created with output_chunk_length={run.horizon}")
        if parse_day(dates.get("prediction_start_date")) != parse_day(
                next_business_day(parse_day(run.train_window[1]))):
            run.notes.append(
                f"prediction_dates.prediction_start_date="
                f"{dates.get('prediction_start_date')!r}, this script asked "
                f"from {run.predict_window[0]}")
    return metrics


def judge_prediction(run: Run, res: Any, want_start: date, want_end: date,
                     horizon: int) -> None:
    """The payload the Prediction tab draws, judged as plumbing, not accuracy."""
    if not isinstance(res, dict):
        run.problems.append(f"predict returned {type(res).__name__}, expected an object")
        return

    future = res.get("future")
    backtest = res.get("predict")
    actual = res.get("actual")

    if not isinstance(future, list) or not future:
        run.problems.append("predict returned no `future` series — the forecast "
                            "the user pressed the button for is empty")
    else:
        # THE FORECAST MUST BE AS LONG AS THE MODEL'S OWN HORIZON.
        #
        # ATTRIBUTION CORRECTED. The first version of this rule said "asked for
        # a 10-day horizon (2023-04-06..2023-04-19) and got 5 points", which
        # blamed the wrong thing: `start_date`/`end_date` govern the BACKTEST
        # series, and measurement showed those are honoured exactly — a
        # ten-business-day window returns ten `actual` and ten `predict` points.
        # What ignores the request is `future`, the forward forecast, whose
        # length comes from predict_days or DEFAULT_PREDICTION_DAYS and never
        # from the model's configured output_chunk_length. Had the message been
        # left as it was, the obvious "fix" would have been to make the backtest
        # window drive the forecast length — changing correct behaviour to chase
        # a mis-worded test.
        if len(future) != horizon:
            run.problems.append(
                f"the model was created with output_chunk_length={horizon} but "
                f"the forecast is {len(future)} day(s) long — `future` ignores "
                f"the model's own horizon")
        declared = as_int(res.get("future_days"))
        if declared is not None and declared != len(future):
            run.problems.append(
                f"future_days={declared} but `future` holds {len(future)} points")
        vals = values_of(future, "close", "predicted_price", "value")
        if len(vals) != len(future):
            run.problems.append(
                f"{len(future) - len(vals)} of {len(future)} forecast points "
                f"have no finite price")
        elif min(vals) <= 0:
            run.problems.append(f"forecast contains a non-positive price: {min(vals)}")
        elif len(vals) > 1 and statistics.pstdev(vals) == 0.0:
            # #52 and #109 were both exactly this: one number repeated.
            run.problems.append(
                f"forecast is FLAT — all {len(vals)} days are {vals[0]!r}")
        days = [parse_day(r.get("tradingdate") or r.get("date"))
                for r in future if isinstance(r, dict)]
        days = [d for d in days if d]
        if days:
            if min(days) < want_start:
                run.problems.append(
                    f"forecast starts {min(days)}, before the requested "
                    f"{want_start} — it overlaps the training period")
            if any(d.weekday() >= 5 for d in days):
                weekend = [str(d) for d in days if d.weekday() >= 5]
                run.problems.append(f"forecast lands on non-trading days: {weekend}")
            if len(set(days)) != len(days):
                run.problems.append("forecast repeats a date")

    run.series_sizes = {k: (len(res[k]) if isinstance(res.get(k), list) else None)
                        for k in ("chart", "actual", "predict", "future")}

    # The backtest line and the actual line are drawn on the same axis; equal
    # length is what makes them comparable, and the UI zips them.
    #
    # EMPTINESS IS CHECKED BEFORE EQUALITY, because the first version of this
    # function only compared the two lengths — and 0 == 0, so a response with
    # every series empty passed. That is the response the tabular engine
    # actually returns for a short window: HTTP 200, all four series empty,
    # metrics null. The check that was supposed to catch the worst case was
    # vacuous precisely in it.
    if isinstance(backtest, list) and isinstance(actual, list):
        if not backtest and not actual:
            # WHY THIS IS NOT ONE RULE BUT THREE. An empty backtest has three
            # causes and only two are defects, so the flat version of this rule
            # produced a false positive on the first verification run: it failed
            # a window of 2024-04-29..30, which is Reunification Day and Labour
            # Day — the exchange was shut, so there was correctly nothing to
            # backtest. Reporting that as a bug would have been a harness error
            # presented as a service error.
            #
            # `chart` is the discriminator because it is drawn from the same
            # feature frame: empty chart means the frame itself produced
            # nothing (#128's symptom), while a populated chart whose dates
            # skip the window means the market was closed through it.
            chart_days = [parse_day(r.get("date") or r.get("tradingdate"))
                          for r in (res.get("chart") or []) if isinstance(r, dict)]
            chart_days = [d for d in chart_days if d]
            if not chart_days:
                run.problems.append(
                    "predict returned 200 with every series empty — the feature "
                    "frame produced no rows and the Prediction tab draws a blank "
                    "chart with no error")
            elif any(want_start <= d <= want_end for d in chart_days):
                run.problems.append(
                    f"predict returned 200 with `actual` AND `predict` empty even "
                    f"though it has chart data inside {want_start}..{want_end} — "
                    f"bars existed in the window and were not returned")
            else:
                run.notes.append(
                    f"no backtest: the market has no session between {want_start} "
                    f"and {want_end} (holiday window), so there was nothing to "
                    f"compare against")
        elif len(backtest) != len(actual):
            run.problems.append(
                f"`predict` has {len(backtest)} points and `actual` has "
                f"{len(actual)} — the two chart series cannot be paired")
        bad = [r for r in backtest
               if not isinstance(r, dict) or not finite(r.get("close"))]
        if bad:
            run.problems.append(f"{len(bad)} backtest point(s) have no finite close")
        # The requested window governs THIS series, and measurement says the
        # service honours it. Pinned so that a change made for the forecast
        # length cannot quietly start serving a different range here.
        out_of_range = sorted({str(d) for d in
                               (parse_day(r.get("tradingdate") or r.get("date"))
                                for r in backtest if isinstance(r, dict))
                               if d and not (want_start <= d <= want_end)})
        if out_of_range:
            run.problems.append(
                f"backtest covers dates outside the requested "
                f"{want_start}..{want_end}: {out_of_range[:5]}")
    else:
        run.notes.append("predict returned no `predict`/`actual` pair to compare")

    if not isinstance(res.get("chart"), list) or not res.get("chart"):
        run.notes.append("predict returned an empty `chart` series "
                         "(the Prediction tab draws its context from this)")

    metrics = res.get("metrics")
    if not isinstance(metrics, dict):
        run.notes.append("predict returned no metrics block")
    else:
        for key in ("rmse", "mae", "r2"):
            if key in metrics and metrics[key] is not None and not finite(metrics[key]):
                run.problems.append(f"predict metric {key}={metrics[key]!r} is not finite")

    if res.get("train_status") and res["train_status"] != "predicted":
        run.notes.append(f"predict left train_status={res['train_status']!r}")


def run_one(api: Api, url_name: str, defaults_by_type: dict, groups: dict,
            avail: tuple[Optional[date], Optional[date]], args,
            rng: random.Random) -> Run:
    run = Run(url_name=url_name)
    run.engine_asked = args.engine or "(service default)"
    started = time.time()
    try:
        # --- 1. create the model with the server's own defaults, unmodified --
        run.stage = "create-model"
        defaults = defaults_by_type.get(url_name)
        if defaults is None:
            run.problems.append(
                f"no row in GET /models/parameters/default-values for this type, "
                f"so the Solutions form has nothing to pre-fill and 'create with "
                f"defaults' is not possible")
            return run
        body = {"model_name": f"rt-{url_name}-{int(time.time())}", **defaults}
        created = api.post(f"/models/{url_name}", body)
        run.model_id = first_id(created, "model_id", "id")
        if not run.model_id:
            run.problems.append(f"model create returned no id: {str(created)[:160]}")
            return run
        run.model_type = created.get("model_type") or url_name
        echoed = created.get("configuration")
        if isinstance(echoed, dict):
            dropped = sorted(k for k, v in defaults.items()
                             if k not in echoed and k != "model_sub_type")
            if dropped:
                run.problems.append(
                    f"these default parameters were sent and are missing from the "
                    f"created model's configuration: {dropped}")
        run.horizon = as_int(defaults.get("output_chunk_length"))
        if run.horizon is None:
            run.notes.append(
                f"defaults carry no output_chunk_length; using the UI's fallback "
                f"of {FALLBACK_HORIZON} days for the prediction window")
            run.horizon = FALLBACK_HORIZON
        elif run.horizon < 1:
            run.problems.append(f"default output_chunk_length={run.horizon} is unusable")
            return run

        # --- 2. four random indicators, one per dropdown --------------------
        run.stage = "create-solution"
        start, end = pick_window(avail[0], avail[1], rng, args.window_days)
        run.train_window = (str(start), str(end))
        sol = api.post("/solutions/create", {
            "solution_name": f"rt-{url_name}-{int(time.time())}",
            "model_id": run.model_id,
            "ticker": args.ticker,
            "user_id": args.user_id,
            "created_by": args.user_id,
            "start_training_date": str(start),
            "end_training_date": str(end),
            "train_validation_ratio": args.train_ratio,
        })
        run.solution_id = first_id(sol, "solution_id", "id")
        if not run.solution_id:
            run.problems.append(f"solution create returned no id: {str(sol)[:160]}")
            return run

        run.stage = "set-indicators"
        chosen, missing = choose_indicators(groups, rng)
        if missing:
            run.problems.append(
                f"GET /predict/indicators offers nothing for {missing}, so the "
                f"selector's dropdown(s) would be empty")
        run.indicators = chosen
        api.post(f"/solutions/{run.solution_id}/indicators/set",
                 {GROUP_REQUEST_KEY[g]: {"id": c["id"],
                                         "covariate_type": c["covariate_type"],
                                         "parameters": c["parameters"]}
                  for g, c in chosen.items()})
        judge_indicator_storage(
            run, api.get(f"/solutions/{run.solution_id}/indicators"))

        # --- 3. train on the random two-year window ------------------------
        run.stage = "train"
        # The UI's body, field for field (TrainingSolution.formSubmit). `engine`
        # is absent unless asked for, because the UI never sends one.
        train_body = {
            "id": run.solution_id,
            "validation": True,
            "train_ratio": args.train_ratio,
            "start_date": str(start),
            "end_date": str(end),
            "include_news": False,
            "news_halflife_days": 5,
        }
        if args.engine:
            train_body["engine"] = args.engine
        api.post("/solutions/train", train_body)
        status = poll(api, run.solution_id, args.timeout)
        if status.get("status") != "completed":
            run.problems.append(
                f"training ended {status.get('status')!r}: "
                f"{str(status.get('error') or status.get('message'))[:260]}")
            return run
        run.metrics = judge_training(run, status)

        # --- 4 & 5. predict over the model's own horizon -------------------
        run.stage = "predict"
        p_start = next_business_day(end)
        p_end = add_business_days(p_start, run.horizon - 1)
        run.predict_window = (str(p_start), str(p_end))
        res = api.post("/solutions/predict", {
            "id": run.solution_id,
            "start_date": str(p_start),
            "end_date": str(p_end),
        })
        judge_prediction(run, res, p_start, p_end, run.horizon)
        run.stage = "done"

    except ApiError as e:
        run.problems.append(f"[{run.stage}] {e}"[:400])
    except Exception as e:                           # noqa: BLE001
        run.problems.append(f"[{run.stage}] {type(e).__name__}: {e}"[:400])
    finally:
        run.seconds = time.time() - started
    return run


def poll(api: Api, solution_id: int, timeout: float) -> dict:
    """Poll with a WIDENING interval, because the gateway budget is per minute.

    Default parameters mean 300-500 epochs, so a run here is far longer than in
    model_sweep.py; a flat 2-second poll would spend the whole per-minute
    allowance on one model and starve the rest of the sweep.
    """
    deadline = time.time() + timeout
    last: dict = {"status": "unknown"}
    wait = 3.0
    while time.time() < deadline:
        try:
            last = api.get(f"/solutions/{solution_id}/training-status")
        except ApiError as e:
            return {"status": "poll_failed", "error": str(e)}
        if last.get("status") in ("completed", "failed"):
            return last
        time.sleep(wait)
        wait = min(wait * 1.4, 20.0)
    # A run that never leaves "training" is itself a finding: the task died
    # without recording a failure, so nothing would ever have reported it.
    return {"status": "timeout",
            "message": f"still {last.get('status')!r} after {timeout:.0f}s "
                       f"(progress {last.get('progress')})"}


# ---------------------------------------------------------------------------
# Setup fetches
# ---------------------------------------------------------------------------

def fetch_defaults(api: Api) -> dict:
    """Default parameters per model type, keyed by the URL name used to create.

    Matched case-insensitively because the catalogue spells types `BlockRNN`
    while the create route takes `blockrnn`.
    """
    rows = api.get("/models/parameters/default-values")
    out: dict = {}
    for row in rows if isinstance(rows, list) else []:
        model_type = str(row.get("model_type_") or "")
        key = model_type.lower().replace(" ", "")
        if key in MODEL_URL_NAMES:
            out[key] = {k: v for k, v in row.items() if k != "model_type_"}
    return out


def fetch_availability(api: Api, ticker: str) -> tuple[Optional[date], Optional[date]]:
    try:
        rng = api.get(f"/solutions/ticker/time_range/{ticker}")
    except ApiError:
        return None, None
    return parse_day(rng.get("start_date")), parse_day(rng.get("end_date"))


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def report(runs: list[Run], args, seed: int) -> int:
    width = max((len(r.url_name) for r in runs), default=10) + 1
    print()
    print("=" * 100)
    print("PREDICTION ROUND-TRIP SWEEP — default parameters, random indicators, "
          "train then predict")
    print(f"ticker {args.ticker} | engine {args.engine or '(service default)'} | "
          f"seed {seed} | window {args.window_days}d")
    print("=" * 100)
    print(f"{'model':<{width}} {'verdict':<7} {'stage':<14} {'horizon':>7} "
          f"{'secs':>7}  detail")
    print("-" * 100)
    for r in sorted(runs, key=lambda x: x.url_name):
        detail = (r.problems or r.notes or [""])[0]
        print(f"{r.url_name:<{width}} {r.verdict:<7} {r.stage:<14} "
              f"{(r.horizon if r.horizon is not None else '-')!s:>7} "
              f"{r.seconds:>7.1f}  {detail[:46]}")

    failed = [r for r in runs if r.problems]
    print("-" * 100)
    print(f"{len(runs) - len(failed)} passed, {len(failed)} failed, of {len(runs)}")

    print()
    print("WHAT EACH RUN ACTUALLY DID")
    for r in sorted(runs, key=lambda x: x.url_name):
        inds = ", ".join(f"{g}={c['name']}" for g, c in r.indicators.items()) or "-"
        print(f"  {r.url_name}: train {r.train_window[0]}..{r.train_window[1]} "
              f"-> predict {r.predict_window[0] or '-'}..{r.predict_window[1] or '-'} "
              f"({r.horizon} d), engine ran {r.engine_ran or '?'}")
        print(f"      indicators: {inds}")
        if r.metrics:
            got = {k: r.metrics.get(k) for k in ("rmse", "mae", "r2") if k in r.metrics}
            print(f"      training: {got}")
        if r.series_sizes:
            print(f"      predict payload sizes: {r.series_sizes}")

    if failed:
        print()
        print("FAILURES IN FULL")
        for r in failed:
            print(f"\n  {r.url_name} (died at {r.stage}, solution "
                  f"{r.solution_id}, model {r.model_id})")
            for p in r.problems:
                print(f"    - {p}")

    notes = [(r, n) for r in runs for n in r.notes]
    if notes:
        print()
        print("NOTES (not failures)")
        for r, n in notes:
            print(f"  {r.url_name}: {n}")

    # The same defect reported by seven models is ONE defect. Grouping it keeps
    # a systemic break from reading as seven unrelated ones.
    if failed:
        buckets: dict[str, list[str]] = {}
        for r in failed:
            for p in r.problems:
                key = p.split("—")[0].split(":")[0].strip()[:70]
                buckets.setdefault(key, []).append(r.url_name)
        print()
        print("DISTINCT PROBLEMS, most widespread first")
        for key, names in sorted(buckets.items(), key=lambda kv: -len(kv[1])):
            print(f"  [{len(names)}/{len(runs)}] {key}")
            print(f"        {', '.join(sorted(set(names)))}")
    return 1 if failed else 0


def cleanup(api: Api, runs: list[Run]) -> None:
    """Remove what the sweep created; abandoned solutions are somebody's mess."""
    sols = [r.solution_id for r in runs if r.solution_id]
    models = [r.model_id for r in runs if r.model_id]
    for sid in sols:
        try:
            api.delete(f"/solutions/{sid}")
        except ApiError as e:
            print(f"  cleanup: solution {sid} not deleted: {e}", file=sys.stderr)
    for mid in models:
        try:
            api.delete(f"/models/{mid}")
        except ApiError as e:
            print(f"  cleanup: model {mid} not deleted: {e}", file=sys.stderr)
    print(f"cleaned up {len(sols)} solution(s) and {len(models)} model(s)")


# ---------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--gateway", default=DEFAULT_GATEWAY)
    ap.add_argument("--email", default=os.environ.get("SWEEP_EMAIL", ""))
    ap.add_argument("--password", default=os.environ.get("SWEEP_PASSWORD", ""))
    ap.add_argument("--token", default=os.environ.get("SWEEP_TOKEN", ""))
    ap.add_argument("--user-id", type=int, default=1)
    ap.add_argument("--ticker", default="FPT")
    ap.add_argument("--models", default="",
                    help="comma-separated URL names; default: the seven in DEFAULT_HALF")
    ap.add_argument("--other-half", action="store_true",
                    help=f"sweep the other seven instead: {', '.join(OTHER_HALF)}")
    ap.add_argument("--engine", default="",
                    help="force 'tabular' or 'darts'; default sends none, as the UI does")
    ap.add_argument("--window-days", type=int, default=TRAINING_WINDOW_DAYS,
                    help="calendar days of training history (default ~2 years)")
    ap.add_argument("--train-ratio", type=float, default=0.8)
    ap.add_argument("--seed", type=int, default=None,
                    help="replay a previous run's indicator and date choices")
    ap.add_argument("--timeout", type=float, default=1800.0,
                    help="per-model training budget; defaults mean 300-500 epochs")
    ap.add_argument("--pace", type=float, default=2.0,
                    help="seconds between models; the gateway allows ~100 req/min")
    ap.add_argument("--keep", action="store_true",
                    help="leave the models and solutions behind for inspection")
    args = ap.parse_args()

    token = args.token or (login(args.gateway, args.email, args.password)
                           if args.email and args.password else "")
    if not token:
        print("need --token, or --email/--password (or SWEEP_* env vars). "
              "scripts/mint_test_token.py prints one.", file=sys.stderr)
        return 2

    if args.models:
        names = [n.strip().lower() for n in args.models.split(",") if n.strip()]
    elif args.other_half:
        names = list(OTHER_HALF)
    else:
        names = list(DEFAULT_HALF)
    unknown = [n for n in names if n not in MODEL_URL_NAMES]
    if unknown:
        print(f"unknown model name(s): {unknown}\nknown: {list(MODEL_URL_NAMES)}",
              file=sys.stderr)
        return 2
    if args.engine and args.engine not in ("tabular", "darts"):
        print(f"--engine must be 'tabular' or 'darts', got {args.engine!r}",
              file=sys.stderr)
        return 2

    seed = args.seed if args.seed is not None else random.randrange(1 << 30)
    rng = random.Random(seed)
    api = Api(args.gateway, token)

    defaults_by_type = fetch_defaults(api)
    groups = api.get("/predict/indicators")
    if not isinstance(groups, dict):
        print(f"GET /predict/indicators returned {type(groups).__name__}; "
              f"cannot choose indicators", file=sys.stderr)
        return 2
    avail = fetch_availability(api, args.ticker)

    print(f"{len(names)} model(s) on {args.ticker}: {', '.join(names)}")
    print(f"seed {seed} (pass --seed {seed} to replay the same choices)")
    print(f"ticker history {avail[0]} .. {avail[1]}; "
          f"training window {args.window_days} calendar days")
    print(f"engine: {args.engine or 'not sent — whatever the service defaults to'}")
    print(f"defaults available for {len(defaults_by_type)} of "
          f"{len(MODEL_URL_NAMES)} model types")

    runs: list[Run] = []
    try:
        for name in names:
            if runs:
                time.sleep(args.pace)
            print(f"\n  -> {name} ...", flush=True)
            run = run_one(api, name, defaults_by_type, groups, avail, args, rng)
            runs.append(run)
            print(f"     {run.verdict} at {run.stage} in {run.seconds:.1f}s"
                  + (f" — {run.problems[0][:90]}" if run.problems else ""))
    except KeyboardInterrupt:
        print("\ninterrupted; reporting what completed and cleaning up",
              file=sys.stderr)
    finally:
        if args.keep:
            print("\n--keep: left "
                  f"solutions {[r.solution_id for r in runs if r.solution_id]} and "
                  f"models {[r.model_id for r in runs if r.model_id]}")
        else:
            cleanup(api, runs)

    return report(runs, args, seed)


if __name__ == "__main__":
    raise SystemExit(main())
