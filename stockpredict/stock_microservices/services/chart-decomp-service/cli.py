"""chart-decompose CLI — command-line access to the chart_decomp library.

Repaired (B1, CD-701): all stale facade calls fixed to match the current
keyword-argument API; decompose / forecast / backtest / patterns subcommands
added per SRS §I.4.3.

Usage examples
--------------
  # Decompose a price series (MODWT by default)
  python cli.py decompose prices.csv --col close --method modwt --level 6

  # HAR or VMD-HAR volatility forecast
  python cli.py forecast log_rv.csv --col log_rv --model vmd-har --out fc.csv

  # Vol-targeting backtest
  python cli.py backtest --returns r.csv --forecast f.csv --target-vol 0.15

  # Hurst exponent (pass returns, not prices — FR-HURST)
  python cli.py hurst returns.csv --col returns

  # CWT scalogram summary
  python cli.py cwt prices.csv --col close

  # Full pattern pipeline (Part II)
  python cli.py patterns prices.csv --col close --k-drop 1 --threshold 0.08
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_col(path: str, col: str) -> np.ndarray:
    rows = []
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(float(row[col]))
    return np.asarray(rows, dtype=np.float64)


def _save_csv(path: str, header: list[str], rows: list[list]) -> None:
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    print(f"Saved → {path}")


# ---------------------------------------------------------------------------
# decompose  (SRS §I.4.3 — replaces bare 'modwt' subcommand)
# ---------------------------------------------------------------------------

def cmd_decompose(args: argparse.Namespace) -> None:
    import chart_decomp as cd

    x = _load_col(args.input, args.col)
    method = args.method.lower()

    if method == "modwt":
        result = cd.modwt(x, wavelet=args.wavelet, level=args.level)
        recon = result.reconstruct()
        err = float(np.max(np.abs(x - recon)))
        print(f"MODWT  levels={result.level}  wavelet={result.wavelet}  "
              f"recon_err={err:.2e}  COI={result.coi_widths}")
        if args.output:
            header = ["approximation"] + [f"detail_{j+1}" for j in range(result.level)]
            rows = [[result.approximation[i]] + [d[i] for d in result.details]
                    for i in range(len(x))]
            _save_csv(args.output, header, rows)

    elif method == "cwt":
        result = cd.cwt_scalogram(x, wavelet=args.wavelet)
        print(json.dumps({
            "shape": list(result.power.shape),
            "freq_min": float(result.frequencies.min()),
            "freq_max": float(result.frequencies.max()),
            "coi_min":  float(result.coi.min()),
        }, indent=2))

    elif method in ("emd", "eemd"):
        fn = cd.eemd if method == "eemd" else cd.emd
        result = fn(x)
        recon = result.reconstruct()
        err = float(np.max(np.abs(x - recon)))
        print(f"{method.upper()}  n_imfs={result.n_imfs}  recon_err={err:.2e}")
        if args.output:
            header = [f"imf_{j}" for j in range(result.n_imfs)]
            rows = [[result.imfs[j, i] for j in range(result.n_imfs)]
                    for i in range(len(x))]
            _save_csv(args.output, header, rows)

    elif method == "vmd":
        result = cd.vmd(x, K=args.level)  # --level repurposed as K for VMD
        recon = result.reconstruct()
        err = float(np.max(np.abs(x - recon)))
        print(f"VMD  K={result.K}  recon_err={err:.2e}  "
              f"center_freqs={[round(f,4) for f in result.center_frequencies.tolist()]}")

    else:
        print(f"Unknown method '{args.method}'. Choose: modwt cwt emd eemd vmd",
              file=sys.stderr)
        sys.exit(1)


# ---------------------------------------------------------------------------
# forecast  (SRS §I.4.3)
# ---------------------------------------------------------------------------

def cmd_forecast(args: argparse.Namespace) -> None:
    import chart_decomp as cd

    log_rv = _load_col(args.input, args.col)
    model = args.model.lower().replace("-", "_")

    if model in ("har", "har_forecast"):
        result = cd.har_forecast(log_rv)
    elif model in ("vmd_har", "vmd_har_forecast"):
        result = cd.vmd_har_forecast(log_rv)
    else:
        print(f"Unknown model '{args.model}'. Choose: har vmd-har", file=sys.stderr)
        sys.exit(1)

    print(f"Model: {args.model}  OOS points: {result.n_oos}")
    for k, v in result.metrics.items():
        if v is not None:
            print(f"  {k}: {v:.4f}" if isinstance(v, float) else f"  {k}: {v}")

    if args.out:
        _save_csv(args.out,
                  ["timestamp", "prediction", "actual"],
                  [[t, p, a] for t, p, a in
                   zip(result.timestamps, result.predictions, result.actuals)])


# ---------------------------------------------------------------------------
# backtest  (SRS §I.4.3)
# ---------------------------------------------------------------------------

def cmd_backtest(args: argparse.Namespace) -> None:
    import chart_decomp as cd

    returns  = _load_col(args.returns,  args.ret_col)
    forecast = _load_col(args.forecast, args.fc_col)

    result = cd.vol_target_backtest(
        returns, forecast,
        target_ann_vol=args.target_vol,
        max_leverage=args.max_leverage,
        cost_bps=args.cost_bps,
    )

    print("Vol-target backtest metrics:")
    for k, v in result.metrics.items():
        print(f"  {k}: {v:.4f}" if isinstance(v, float) else f"  {k}: {v}")

    if args.out:
        _save_csv(args.out,
                  ["pnl_gross", "pnl_net", "position", "turnover"],
                  [[g, n, p, t] for g, n, p, t in
                   zip(result.pnl_gross, result.pnl_net,
                       result.positions, result.turnover)])


# ---------------------------------------------------------------------------
# hurst  (fixed: stale cd.hurst_wavelet(x, params) call)
# ---------------------------------------------------------------------------

def cmd_hurst(args: argparse.Namespace) -> None:
    import chart_decomp as cd

    x = _load_col(args.input, args.col)
    # FR-HURST: input should be returns, not price levels.
    # The estimator now emits a UserWarning if it detects a non-stationary input.
    result = cd.hurst_wavelet(x, wavelet=args.wavelet, j_range=(args.j_lo, args.j_hi))
    print(f"Hurst exponent : {result.H:.4f}")
    print(f"Slope          : {result.slope:.4f}")
    print(f"Intercept      : {result.intercept:.4f}")


# ---------------------------------------------------------------------------
# cwt  (fixed: stale cd.cwt_scalogram(x, params) call)
# ---------------------------------------------------------------------------

def cmd_cwt(args: argparse.Namespace) -> None:
    import chart_decomp as cd

    x = _load_col(args.input, args.col)
    result = cd.cwt_scalogram(x, wavelet=args.wavelet)
    print(json.dumps({
        "shape":    list(result.power.shape),
        "freq_min": float(result.frequencies.min()),
        "freq_max": float(result.frequencies.max()),
        "coi_min":  float(result.coi.min()),
    }, indent=2))


# ---------------------------------------------------------------------------
# patterns  (Part II — new in B1)
# ---------------------------------------------------------------------------

def cmd_patterns(args: argparse.Namespace) -> None:
    import chart_decomp as cd

    x = _load_col(args.input, args.col)
    result = cd.run_pattern_pipeline(
        x,
        denoise_params=cd.DenoiseParams(k_drop=args.k_drop),
        swing_params=cd.SwingParams(threshold=args.threshold),
        compute_fpr=args.fpr,
    )

    print(f"Swings   : {len(result.swings)}")
    print(f"Patterns : {len(result.detections)}")
    for d in result.detections:
        flag = " [EDGE?]" if not d.confirmed else ""
        print(f"  {d.pattern:30s} start={d.start_index:4d} end={d.end_index:4d} "
              f"score={d.score:.2f}{flag}")

    if result.fpr_by_pattern:
        print("Null FPR:")
        for pat, fpr in result.fpr_by_pattern.items():
            print(f"  {pat}: {fpr:.3f}")


# ---------------------------------------------------------------------------
# versions  (B4 — NFR-RP2 version provenance)
# ---------------------------------------------------------------------------

def cmd_versions(args: argparse.Namespace) -> None:  # noqa: ARG001
    import chart_decomp as cd
    print(json.dumps(cd.get_versions(), indent=2))


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="chart-decompose",
        description="Chart Decomposition & Multi-Scale Analysis CLI  (SRS §I.4.3)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # decompose (SRS §I.4.3 primary subcommand)
    p = sub.add_parser("decompose", help="Decompose a series (MODWT/CWT/EMD/VMD)")
    p.add_argument("input",          help="CSV file path")
    p.add_argument("--col",          default="close")
    p.add_argument("--method",       default="modwt",
                   choices=["modwt", "cwt", "emd", "eemd", "vmd"])
    p.add_argument("--wavelet",      default="sym8")
    p.add_argument("--level",        type=int, default=6,
                   help="MODWT levels J or VMD modes K")
    p.add_argument("--output", "--out", dest="output",
                   help="Output CSV path")
    p.set_defaults(func=cmd_decompose)

    # forecast (SRS §I.4.3)
    p = sub.add_parser("forecast", help="Walk-forward HAR or VMD-HAR forecast")
    p.add_argument("input",          help="CSV with log-RV column")
    p.add_argument("--col",          default="log_rv")
    p.add_argument("--model",        default="har", choices=["har", "vmd-har"])
    p.add_argument("--out",          help="Output CSV for predictions")
    p.set_defaults(func=cmd_forecast)

    # backtest (SRS §I.4.3)
    p = sub.add_parser("backtest", help="Vol-targeting backtest")
    p.add_argument("--returns",      required=True, help="CSV with returns")
    p.add_argument("--forecast",     required=True, help="CSV with vol forecasts")
    p.add_argument("--ret-col",      default="return")
    p.add_argument("--fc-col",       default="vol_forecast")
    p.add_argument("--target-vol",   type=float, default=0.15)
    p.add_argument("--max-leverage", type=float, default=3.0)
    p.add_argument("--cost-bps",     type=float, default=2.0)
    p.add_argument("--out",          help="Output CSV for positions/PnL")
    p.set_defaults(func=cmd_backtest)

    # hurst
    p = sub.add_parser("hurst", help="Wavelet Hurst exponent (pass returns, not prices)")
    p.add_argument("input")
    p.add_argument("--col",    default="returns")
    p.add_argument("--wavelet", default="db4")
    p.add_argument("--j-lo",   type=int, default=2)
    p.add_argument("--j-hi",   type=int, default=8)
    p.set_defaults(func=cmd_hurst)

    # cwt
    p = sub.add_parser("cwt", help="CWT scalogram summary")
    p.add_argument("input")
    p.add_argument("--col",     default="close")
    p.add_argument("--wavelet", default="cmor1.5-1.0")
    p.set_defaults(func=cmd_cwt)

    # patterns (Part II)
    p = sub.add_parser("patterns", help="Pattern detection pipeline (Part II)")
    p.add_argument("input",          help="CSV file with price series")
    p.add_argument("--col",          default="close")
    p.add_argument("--k-drop",       type=int, default=1,
                   help="MODWT bands to drop in denoising")
    p.add_argument("--threshold",    type=float, default=0.08,
                   help="Swing significance threshold (range fraction)")
    p.add_argument("--fpr",          action="store_true",
                   help="Compute null false-positive rates (slower)")
    p.set_defaults(func=cmd_patterns)

    # versions (B4)
    p = sub.add_parser("versions", help="Print library and dependency versions (NFR-RP2)")
    p.set_defaults(func=cmd_versions)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
