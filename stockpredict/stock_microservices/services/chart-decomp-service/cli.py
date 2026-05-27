"""chart-decompose CLI — quick command-line access to the chart_decomp library.

Usage examples
--------------
  # MODWT on a CSV column
  python cli.py modwt prices.csv --col close --level 6 --wavelet sym8

  # HAR forecast from a log-RV CSV
  python cli.py har log_rv.csv --col log_rv --out forecast.csv

  # Hurst exponent
  python cli.py hurst prices.csv --col close

  # CWT scalogram (outputs JSON)
  python cli.py cwt prices.csv --col close --n-scales 64
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np


def _load_series(path: str, col: str) -> np.ndarray:
    import csv
    rows = []
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(float(row[col]))
    return np.asarray(rows, dtype=np.float64)


def cmd_modwt(args: argparse.Namespace) -> None:
    import chart_decomp as cd
    from chart_decomp.domain.value_objects import MODWTParams

    x = _load_series(args.input, args.col)
    params = MODWTParams(wavelet=args.wavelet, level=args.level)
    result = cd.modwt(x, params)

    recon = result.reconstruct()
    err = float(np.max(np.abs(x - recon)))
    print(f"MODWT levels: {result.level}  wavelet: {result.wavelet}")
    print(f"Reconstruction error: {err:.2e}")
    print(f"COI widths: {result.coi_widths}")

    if args.out:
        import csv
        with open(args.out, "w", newline="") as f:
            w = csv.writer(f)
            header = ["approximation"] + [f"detail_{j+1}" for j in range(result.level)]
            w.writerow(header)
            for i in range(len(x)):
                w.writerow(
                    [result.approximation[i]] + [d[i] for d in result.details]
                )
        print(f"Saved to {args.out}")


def cmd_hurst(args: argparse.Namespace) -> None:
    import chart_decomp as cd
    from chart_decomp.domain.value_objects import HurstParams

    x = _load_series(args.input, args.col)
    params = HurstParams(wavelet=args.wavelet, j_lo=args.j_lo, j_hi=args.j_hi)
    result = cd.hurst_wavelet(x, params)
    print(f"Hurst exponent: {result.hurst:.4f}")
    print(f"Slope: {result.slope:.4f}  Intercept: {result.intercept:.4f}")


def cmd_har(args: argparse.Namespace) -> None:
    import chart_decomp as cd

    log_rv = _load_series(args.input, args.col)
    result = cd.har_forecast(log_rv)
    print("HAR forecast metrics:")
    for k, v in result.metrics.items():
        print(f"  {k}: {v:.4f}")

    if args.out:
        import csv
        with open(args.out, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["timestamp", "prediction", "actual"])
            for t, p, a in zip(result.timestamps, result.predictions, result.actuals):
                w.writerow([t, p, a])
        print(f"Saved to {args.out}")


def cmd_cwt(args: argparse.Namespace) -> None:
    import chart_decomp as cd
    from chart_decomp.domain.value_objects import CWTParams

    x = _load_series(args.input, args.col)
    params = CWTParams(wavelet=args.wavelet, n_scales=args.n_scales)
    result = cd.cwt_scalogram(x, params)
    summary = {
        "shape": list(result.power.shape),
        "freq_min": float(result.frequencies.min()),
        "freq_max": float(result.frequencies.max()),
        "coi_min": float(result.coi.min()),
    }
    print(json.dumps(summary, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="chart-decompose",
        description="Chart Decomposition & Multi-Scale Analysis CLI",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # modwt
    p_modwt = sub.add_parser("modwt", help="MODWT decomposition")
    p_modwt.add_argument("input", help="CSV file path")
    p_modwt.add_argument("--col", default="close", help="Column name")
    p_modwt.add_argument("--level", type=int, default=6)
    p_modwt.add_argument("--wavelet", default="sym8")
    p_modwt.add_argument("--out", help="Output CSV path")
    p_modwt.set_defaults(func=cmd_modwt)

    # hurst
    p_hurst = sub.add_parser("hurst", help="Wavelet Hurst exponent")
    p_hurst.add_argument("input", help="CSV file path")
    p_hurst.add_argument("--col", default="close")
    p_hurst.add_argument("--wavelet", default="db4")
    p_hurst.add_argument("--j-lo", type=int, default=2)
    p_hurst.add_argument("--j-hi", type=int, default=8)
    p_hurst.set_defaults(func=cmd_hurst)

    # har
    p_har = sub.add_parser("har", help="HAR volatility forecast")
    p_har.add_argument("input", help="CSV file with log-RV column")
    p_har.add_argument("--col", default="log_rv")
    p_har.add_argument("--out", help="Output CSV path for forecast")
    p_har.set_defaults(func=cmd_har)

    # cwt
    p_cwt = sub.add_parser("cwt", help="CWT scalogram")
    p_cwt.add_argument("input", help="CSV file path")
    p_cwt.add_argument("--col", default="close")
    p_cwt.add_argument("--wavelet", default="cmor1.5-1.0")
    p_cwt.add_argument("--n-scales", type=int, default=64)
    p_cwt.set_defaults(func=cmd_cwt)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
