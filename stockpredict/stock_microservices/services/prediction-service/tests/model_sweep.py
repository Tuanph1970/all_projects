#!/usr/bin/env python3
"""Train every model architecture on every engine and report what breaks.

A PRE-RELEASE BUG SWEEP, driven entirely through the gateway API against the
price history already in the database. No frontend, no fixtures, no mocks: this
exercises the same path a user does.

WHY IT CHECKS THE RESULT AND NOT THE EXIT CODE. Every interesting bug this
project has had in the training path returned HTTP 200 and stored a number:

  * #109 — the darts engine produced a FLAT forecast because normalisation was
    missing. Training "succeeded"; every predicted day was the same value.
  * #110 — four of fourteen architectures fell through DARTS_TO_ML_MAP to the
    xgboost default because the map held `RNNModel` while the catalogue stores
    `RNN`. All four trained happily and reported someone else's model.
  * #109 again — the tabular engine trained a gradient booster and labelled the
    result 'TFT', with nothing in the payload to say so.

So a cell passes here only if the run completed AND the stored result names the
engine that was asked for, names the architecture that was asked for, discloses
a substitution when one happened, carries finite non-degenerate metrics, and
produces a forecast that actually varies.

USAGE
    python tests/model_sweep.py --help
    python tests/model_sweep.py                      # all 14 x both engines
    python tests/model_sweep.py --engines darts      # one engine
    python tests/model_sweep.py --models TFT,XGBoost --epochs 2
    python tests/model_sweep.py --keep               # leave the rows for inspection

Epochs default to a small number on purpose: the sweep is looking for breakage
and mislabelling across 28 combinations, not for the best achievable score. Pass
--epochs to raise it.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import statistics
import sys
import time
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any, Optional

import urllib.error
import urllib.request

# ---------------------------------------------------------------------------
# The matrix
# ---------------------------------------------------------------------------

#: URL names accepted by POST /models/{name}, mirroring MODEL_TYPE_MAP in
#: app/api/routes.py. Kept as a literal so the sweep can run without importing
#: the service, and kept HONEST by tests/test_model_sweep.py, which fails if the
#: server's map gains or loses an entry — drift shows up as a test failure rather
#: than as an architecture silently never swept.
MODEL_URL_NAMES = (
    "blockrnn", "rnn", "tcn", "transformer", "tft", "nbeats", "nhits",
    "dlinear", "nlinear", "xgboost", "lightgbm", "randomforest",
    "catboost", "tide",
)

#: Catalogue names the TABULAR engine can train genuinely; everything else is a
#: documented substitution (see TABULAR_NATIVE_BACKENDS in solution_routes.py).
#: Duplicated here so the sweep can VERIFY the disclosure rather than trust it.
TABULAR_NATIVE = {"XGBoost", "LightGBM", "RandomForest", "CatBoost", "LinearRegression"}

ENGINES = ("tabular", "darts")

#: Tree/boosting architectures, which take n_estimators and want a learning
#: rate two orders of magnitude larger than a neural net does.
BOOSTER_URL_NAMES = frozenset({"xgboost", "lightgbm", "randomforest", "catboost"})

DEFAULT_GATEWAY = os.environ.get("GATEWAY_URL", "http://localhost:18004")
PREFIX = "/stock_helper/api/v2"


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------

class Api:
    def __init__(self, gateway: str, token: str, timeout: float = 90.0):
        self.base = gateway.rstrip("/") + PREFIX
        self.token = token
        self.timeout = timeout

    #: The gateway rate-limits (traefik/dynamic.yml: average 100 per minute,
    #: and 30 per minute on some routes). A 429 is the GATEWAY talking, not the
    #: service failing, so retrying is correct and reporting it as a model
    #: failure is not — the second full run reported 26 phantom failures that
    #: way, which is worse than no sweep at all because it would mask a real one.
    RATE_LIMIT_RETRIES = 6

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
                with urllib.request.urlopen(req, timeout=self.timeout) as r:
                    raw = r.read().decode()
                    return json.loads(raw) if raw.strip() else {}
            except urllib.error.HTTPError as e:
                if e.code == 429 and attempt < self.RATE_LIMIT_RETRIES:
                    # Honour Retry-After when the gateway sends one; otherwise
                    # back off, since the window is per-minute.
                    wait = delay
                    try:
                        wait = max(wait, float(e.headers.get("Retry-After") or 0))
                    except (TypeError, ValueError):
                        pass
                    time.sleep(wait)
                    delay = min(delay * 2, 60.0)
                    continue
                detail = e.read().decode()[:300]
                raise ApiError(f"HTTP {e.code} {method} {path}: {detail}") from None
            except Exception as e:                   # noqa: BLE001
                raise ApiError(f"{type(e).__name__} {method} {path}: {e}") from None
        raise ApiError(f"rate-limited {method} {path} after "
                       f"{self.RATE_LIMIT_RETRIES} retries")

    get = lambda self, p: self._call("GET", p)                      # noqa: E731
    post = lambda self, p, b=None: self._call("POST", p, b or {})   # noqa: E731
    delete = lambda self, p: self._call("DELETE", p)                # noqa: E731


class ApiError(RuntimeError):
    pass


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
# One cell of the matrix
# ---------------------------------------------------------------------------

@dataclass
class Cell:
    model: str                 # catalogue name, e.g. "TFT"
    engine: str
    ok: bool = False
    seconds: float = 0.0
    problems: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    metrics: dict = field(default_factory=dict)

    @property
    def verdict(self) -> str:
        if self.ok and not self.problems:
            return "PASS"
        return "FAIL"


def _finite(x: Any) -> bool:
    try:
        return math.isfinite(float(x))
    except (TypeError, ValueError):
        return False


def judge(cell: Cell, requested_model: str, metrics: dict, forecast: Optional[list]) -> None:
    """Everything that must hold for a run to count as working."""
    cell.metrics = metrics
    p = cell.problems

    if not metrics:
        p.append("no training_metrics_json was stored")
        return

    # --- the model that ran is the model that was asked for (#110) ----------
    got_model = metrics.get("model_type")
    if got_model and got_model != requested_model:
        p.append(f"result names model {got_model!r}, asked for {requested_model!r}")

    # --- the engine that ran is the engine that was asked for (#109) --------
    got_engine = metrics.get("engine")
    if got_engine is None:
        cell.notes.append("result does not record the engine")
    elif got_engine != cell.engine:
        p.append(f"result names engine {got_engine!r}, asked for {cell.engine!r}")

    # --- a substitution must be disclosed, not implied (#109) --------------
    if cell.engine == "tabular":
        expected_sub = requested_model not in TABULAR_NATIVE
        declared = metrics.get("backend_substituted")
        if declared is None:
            p.append("tabular result does not declare backend_substituted")
        elif bool(declared) != expected_sub:
            p.append(f"backend_substituted={declared!r}, expected {expected_sub!r} "
                     f"for {requested_model!r}")

    # --- metrics must be real numbers --------------------------------------
    for key in ("rmse", "mae", "r2"):
        if key not in metrics:
            p.append(f"metric {key!r} missing")
        elif not _finite(metrics[key]):
            p.append(f"metric {key}={metrics[key]!r} is not finite")

    rmse = metrics.get("rmse")
    if _finite(rmse) and float(rmse) == 0.0:
        # A perfect fit on held-out data means the target leaked into the
        # features, not that the model is excellent.
        p.append("rmse is exactly 0 — suspect target leakage")

    for key in ("training_samples", "validation_samples"):
        v = metrics.get(key)
        if v is None:
            cell.notes.append(f"{key} not reported")
        elif int(v) <= 0:
            p.append(f"{key}={v} — nothing was {key.split('_')[0]}ed on")

    # --- the C4 benchmark, where the engine provides it --------------------
    if "beats_naive_rmse" in metrics:
        if not _finite(metrics.get("naive_rmse")):
            p.append("naive benchmark present but naive_rmse is not finite")
        elif not metrics["beats_naive_rmse"]:
            # NOT a failure. A model losing to naive is a result, and silently
            # treating it as breakage would hide the opposite problem.
            #
            # The numbers are formatted only when BOTH are finite. Formatting
            # them unconditionally raised TypeError on a None rmse — so the
            # sweep crashed precisely when it had found a broken metric, which
            # is the one moment it must survive to report.
            if _finite(metrics.get("rmse")) and _finite(metrics.get("naive_rmse")):
                cell.notes.append(
                    f"does not beat naive (rmse {float(metrics['rmse']):.4g} vs "
                    f"{float(metrics['naive_rmse']):.4g})")
            else:
                cell.notes.append("does not beat naive")
    else:
        cell.notes.append("no naive benchmark in result")

    # --- the forecast has to actually move (#109's flat-forecast bug) ------
    if forecast is None:
        cell.notes.append("no forecast retrieved; flatness unchecked")
    elif len(forecast) < 2:
        cell.notes.append(f"forecast too short to judge ({len(forecast)} point)")
    else:
        vals = [float(v) for v in forecast if _finite(v)]
        if len(vals) < 2:
            p.append("forecast contains no finite values")
        elif statistics.pstdev(vals) == 0.0:
            p.append(f"forecast is FLAT — every one of {len(vals)} days is {vals[0]!r}")

    cell.ok = not p


# ---------------------------------------------------------------------------
# Driving one combination
# ---------------------------------------------------------------------------

def run_cell(api: Api, url_name: str, engine: str, args) -> tuple[Cell, list[int], list[int]]:
    """Returns the cell plus the model and solution ids created, for cleanup."""
    models: list[int] = []
    solutions: list[int] = []
    cell = Cell(model=url_name, engine=engine)
    started = time.time()

    try:
        # PER-FAMILY DEFAULTS, because one config is not valid for both.
        #
        # The sweep originally sent learning_rate=0.001 to everything — a
        # reasonable rate for a neural net and a PATHOLOGICAL one for a
        # gradient booster, which at ~100 rounds then barely learns and
        # predicts a constant. The sweep duly reported "XGBoost/darts:
        # forecast is FLAT" and I nearly filed it as a service defect.
        # Measured: lr=0.001 is flat at 100 AND 200 rounds, varies at 2000,
        # and lr=0.1 varies immediately. The harness was the problem.
        #
        # Deliberately still STRINGS: that is what the UI writes into
        # config_json, so the sweep keeps exercising the coercion path that
        # #124 fixed rather than quietly bypassing it.
        cfg = {
            "model_name": f"sweep-{url_name}-{engine}",
            "model_sub_type": "LSTM" if url_name in ("blockrnn", "rnn") else "",
            "input_chunk_length": str(args.input_chunk),
            "output_chunk_length": str(args.horizon),
        }
        if url_name in BOOSTER_URL_NAMES:
            cfg.update({"n_estimators": "200", "max_depth": "6",
                        "learning_rate": "0.1"})
        else:
            cfg.update({"n_epochs": str(args.epochs), "batch_size": "16",
                        "learning_rate": "0.001", "hidden_dim": "16",
                        "n_rnn_layers": "1", "dropout": "0"})
        created = api.post(f"/models/{url_name}", cfg)
        model_id = created.get("id") or created.get("model_id") or (created.get("data") or {}).get("id")
        if not model_id:
            cell.problems.append(f"model create returned no id: {str(created)[:120]}")
            return cell, models, solutions
        models.append(int(model_id))
        cell.model = created.get("model_type") or url_name

        sol = api.post("/solutions/create", {
            "solution_name": f"sweep-{url_name}-{engine}",
            "model_id": int(model_id),
            "ticker": args.ticker,
            "user_id": args.user_id,
            "created_by": args.user_id,
            "start_training_date": args.start,
            "end_training_date": args.end,
            "train_validation_ratio": 0.8,
        })
        sol_id = sol.get("id") or sol.get("solution_id") or (sol.get("data") or {}).get("id")
        if not sol_id:
            cell.problems.append(f"solution create returned no id: {str(sol)[:120]}")
            return cell, models, solutions
        solutions.append(int(sol_id))

        api.post("/solutions/train", {
            "id": int(sol_id), "engine": engine,
            "start_date": args.start, "end_date": args.end,
            "validation": True, "train_ratio": 0.8,
        })

        status = poll(api, int(sol_id), args.timeout)
        if status.get("status") != "completed":
            cell.problems.append(
                f"status={status.get('status')!r}: "
                f"{str(status.get('error') or status.get('message'))[:200]}")
            return cell, models, solutions

        result = status.get("result") or {}
        metrics = normalise(result)
        forecast = extract_forecast(result)
        if forecast is None:
            forecast = fetch_forecast(api, int(sol_id), args)
        judge(cell, cell.model, metrics, forecast)

    except ApiError as e:
        cell.problems.append(str(e)[:240])
    except Exception as e:                           # noqa: BLE001
        cell.problems.append(f"{type(e).__name__}: {e}"[:240])
    finally:
        cell.seconds = time.time() - started
    return cell, models, solutions


def poll(api: Api, solution_id: int, timeout: float) -> dict:
    """Poll with a WIDENING interval, because the gateway budget is per minute.

    A flat 2-second poll is what broke the second full run: one cell took 64
    seconds, spent ~32 polls on it, and exhausted the 100-per-minute allowance
    for every cell after it. Backing off keeps a slow model from starving the
    rest of the sweep.
    """
    deadline = time.time() + timeout
    last: dict = {"status": "unknown"}
    wait = 2.0
    while time.time() < deadline:
        try:
            last = api.get(f"/solutions/{solution_id}/training-status")
        except ApiError as e:
            return {"status": "poll_failed", "error": str(e)}
        if last.get("status") in ("completed", "failed"):
            return last
        time.sleep(wait)
        wait = min(wait * 1.5, 15.0)
    # A run that never leaves "training" is itself a finding: the task died
    # without recording a failure, so nothing would ever have reported it.
    return {"status": "timeout",
            "message": f"still {last.get('status')!r} after {timeout:.0f}s "
                       f"(progress {last.get('progress')})"}


def normalise(result: dict) -> dict:
    """Flatten the two engines' result shapes into one set of keys.

    THE TWO PATHS NEST DIFFERENTLY, and reading them as if they matched is how a
    sweep reports a phantom defect. Measured against the live payloads:

      * darts puts the benchmark at result["naive"]["rmse"]; the tabular path
        has no naive block at all.
      * sample counts sit at result["training_samples"] on the tabular path and
        only inside result["data_accounting"] on the darts path.
      * the engine and model names come from describe_tabular_backend() on the
        tabular path and from explicit keys on the darts path.

    My first version read the metrics from GET /solutions/models instead, which
    returns only id/name/type/covariates — no metrics column — so every cell
    reported "no training_metrics_json was stored" and the sweep looked broken
    when the training was fine. The authoritative copy for a just-finished run
    is the completed status payload.
    """
    out = dict(result or {})
    acct = out.get("data_accounting") or {}
    for key in ("training_samples", "validation_samples", "features_used",
                "bars_fetched", "rows_dropped_to_warmup"):
        if key not in out and key in acct:
            out[key] = acct[key]
    naive = out.get("naive")
    if isinstance(naive, dict) and "naive_rmse" not in out:
        if "rmse" in naive:
            out["naive_rmse"] = naive["rmse"]
        if "r2" in naive:
            out["naive_r2"] = naive["r2"]
    return out


def extract_forecast(result: dict) -> Optional[list]:
    """The predicted series, which both engines return under "predictions"."""
    preds = (result or {}).get("predictions")
    if not isinstance(preds, list) or not preds:
        return None
    if isinstance(preds[0], dict):
        for vk in ("predicted_price", "value", "close", "prediction", "yhat", "y"):
            if vk in preds[0]:
                return [row.get(vk) for row in preds]
        return None
    return preds


def fetch_forecast(api: Api, solution_id: int, args) -> Optional[list]:
    """A forecast, so flatness can be checked — #109's bug was a flat series."""
    for body in ({"id": solution_id, "days": args.horizon},
                 {"solution_id": solution_id, "days": args.horizon}):
        try:
            res = api.post("/solutions/predict", body)
        except ApiError:
            continue
        for key in ("predictions", "forecast", "values", "data"):
            seq = res.get(key) if isinstance(res, dict) else None
            if isinstance(seq, list) and seq:
                if isinstance(seq[0], dict):
                    for vk in ("predicted_price", "value", "close", "prediction", "yhat"):
                        if vk in seq[0]:
                            return [row.get(vk) for row in seq]
                else:
                    return seq
    return None


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def report(cells: list[Cell]) -> int:
    width = max((len(c.model) for c in cells), default=10) + 1
    print()
    print("=" * 96)
    print("MODEL SWEEP")
    print("=" * 96)
    print(f"{'model':<{width}} {'engine':<9} {'verdict':<7} {'secs':>6}  detail")
    print("-" * 96)
    for c in sorted(cells, key=lambda x: (x.model.lower(), x.engine)):
        detail = "; ".join(c.problems) if c.problems else "; ".join(c.notes)
        print(f"{c.model:<{width}} {c.engine:<9} {c.verdict:<7} {c.seconds:>6.1f}  {detail[:58]}")
        for extra in (c.problems[1:] if len(c.problems) > 1 else []):
            print(f"{'':<{width}} {'':<9} {'':<7} {'':>6}  {extra[:58]}")

    failed = [c for c in cells if c.verdict == "FAIL"]
    print("-" * 96)
    print(f"{len(cells) - len(failed)} passed, {len(failed)} failed, of {len(cells)}")
    if failed:
        print()
        print("FAILURES IN FULL")
        for c in failed:
            print(f"\n  {c.model} / {c.engine}")
            for pr in c.problems:
                print(f"    - {pr}")
    notes = [(c, n) for c in cells for n in c.notes]
    if notes:
        print()
        print("NOTES (not failures)")
        for c, n in notes:
            print(f"  {c.model}/{c.engine}: {n}")
    return 1 if failed else 0


# ---------------------------------------------------------------------------

def main() -> int:
    today = date.today()
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--gateway", default=DEFAULT_GATEWAY)
    ap.add_argument("--email", default=os.environ.get("SWEEP_EMAIL", ""))
    ap.add_argument("--password", default=os.environ.get("SWEEP_PASSWORD", ""))
    ap.add_argument("--token", default=os.environ.get("SWEEP_TOKEN", ""))
    ap.add_argument("--user-id", type=int, default=1)
    ap.add_argument("--ticker", default="FPT")
    ap.add_argument("--models", default="", help="comma-separated URL names; default all")
    ap.add_argument("--engines", default=",".join(ENGINES))
    ap.add_argument("--epochs", type=int, default=2,
                    help="small by default: this looks for breakage, not for score")
    ap.add_argument("--input-chunk", type=int, default=14)
    ap.add_argument("--horizon", type=int, default=5)
    ap.add_argument("--start", default=str(today - timedelta(days=900)))
    ap.add_argument("--end", default=str(today - timedelta(days=1)))
    ap.add_argument("--timeout", type=float, default=420.0,
                    help="per-run polling budget, seconds")
    ap.add_argument("--pace", type=float, default=1.5,
                    help="seconds between cells; the gateway allows ~100 req/min")
    ap.add_argument("--keep", action="store_true",
                    help="do not delete the solutions and models created")
    args = ap.parse_args()

    token = args.token or (login(args.gateway, args.email, args.password)
                           if args.email and args.password else "")
    if not token:
        print("need --token, or --email/--password (or SWEEP_* env vars)", file=sys.stderr)
        return 2
    api = Api(args.gateway, token)

    names = [n.strip().lower() for n in args.models.split(",") if n.strip()] or list(MODEL_URL_NAMES)
    engines = [e.strip() for e in args.engines.split(",") if e.strip()]
    unknown = [n for n in names if n not in MODEL_URL_NAMES]
    if unknown:
        print(f"unknown model name(s): {unknown}\nknown: {list(MODEL_URL_NAMES)}", file=sys.stderr)
        return 2

    print(f"sweeping {len(names)} model(s) x {len(engines)} engine(s) "
          f"= {len(names) * len(engines)} runs on {args.ticker} "
          f"[{args.start} .. {args.end}], {args.epochs} epoch(s), "
          f"{args.timeout:.0f}s budget each")

    cells: list[Cell] = []
    created_models: list[int] = []
    created_solutions: list[int] = []
    try:
        for name in names:
            for engine in engines:
                print(f"  -> {name}/{engine} ...", flush=True)
                if cells:
                    time.sleep(args.pace)      # stay inside the gateway budget
                cell, m, s = run_cell(api, name, engine, args)
                created_models += m
                created_solutions += s
                cells.append(cell)
                print(f"     {cell.verdict} in {cell.seconds:.1f}s"
                      + (f" — {cell.problems[0][:70]}" if cell.problems else ""))
    except KeyboardInterrupt:
        print("\ninterrupted; reporting what completed and cleaning up", file=sys.stderr)
    finally:
        if args.keep:
            print(f"\n--keep: left solutions {created_solutions} and models {created_models}")
        else:
            cleanup(api, created_solutions, created_models)

    return report(cells)


def cleanup(api: Api, solutions: list[int], models: list[int]) -> None:
    """Remove what the sweep created. Runs even after an interrupt, because
    28 abandoned solutions is a mess somebody else has to find."""
    for sid in solutions:
        try:
            api.delete(f"/solutions/{sid}")
        except ApiError as e:
            print(f"  cleanup: solution {sid} not deleted: {e}", file=sys.stderr)
    for mid in models:
        try:
            api.delete(f"/models/{mid}")
        except ApiError as e:
            print(f"  cleanup: model {mid} not deleted: {e}", file=sys.stderr)
    print(f"cleaned up {len(solutions)} solution(s) and {len(models)} model(s)")


if __name__ == "__main__":
    raise SystemExit(main())
