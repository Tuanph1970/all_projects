"""EM-9 — sweep the breakout penetration filter (Backlog #69).

Not a test (pytest ignores it). Run from the service dir:

    PYTHONPATH=. python3 tests/em9_penetration_sweep.py


E&M master-list item 128 says 3% of price for a stock (2% for averages);
`confirmation/layer.py` uses 0.3–0.5% by signal kind. Both are defensible — the
book charted 1950s NYSE issues by hand — but the divergence is undocumented and
unmeasured. The register's mandatory C4 benchmark is a threshold sweep on VN
data reporting hit rate and signal count at each level.

`MIN_PENETRATION` is read inside `confirm()` at call time, so patching the dict
really does change behaviour (unlike a default argument).
"""
import collections
import statistics
from datetime import date

from app.services.backtest.harness import BacktestConfig, run_backtest_on_bars
from app.services.confirmation import layer
from app.services.signal.base import OHLCVBar

CURRENT = dict(layer.MIN_PENETRATION)
KINDS = tuple(CURRENT)
LEVELS = [None, 0.003, 0.005, 0.01, 0.015, 0.02, 0.03]   # None = leave as shipped

bars_by_sym = collections.defaultdict(list)
for line in open("/tmp/all_bars.tsv"):
    sym, day, op, hi, lo, cl, vol = line.rstrip("\n").split("\t")
    y, m, d = (int(x) for x in day.split("-"))
    bars_by_sym[sym].append(OHLCVBar(date=date(y, m, d), open=float(op), high=float(hi),
                                     low=float(lo), close=float(cl), volume=float(vol)))

symbols = sorted(bars_by_sym)
print(f"  EM-9 sweep — {len(symbols)} symbols, {len(LEVELS)} levels\n")
print(f"  {'level':>10} {'trades':>8} {'win rate':>9} {'expectancy':>11} {'net P&L':>12} {'profit factor':>14}")

for level in LEVELS:
    if level is None:
        layer.MIN_PENETRATION.update(CURRENT)
        label = "shipped"
    else:
        layer.MIN_PENETRATION.update({k: level for k in KINDS})
        label = f"{level*100:.1f}%"

    trades = wins = 0
    net = 0.0
    expectancies, pfs = [], []
    for sym in symbols:
        bars = bars_by_sym[sym]
        # trailing_stop_mode pinned by Backlog #101: the class default moved to
        # "BASING_POINT", and this study's published numbers are ATR ones.
        cfg = BacktestConfig(ticker=sym, start_date=bars[300].date,
                             end_date=bars[-1].date, trailing_stop_mode="ATR")
        r = run_backtest_on_bars(cfg, bars).stats
        trades += r.num_trades
        wins += r.num_wins
        net += r.total_net_pnl
        if r.num_trades:
            expectancies.append(r.expectancy)
        if r.profit_factor is not None:
            pfs.append(r.profit_factor)
    wr = wins / trades if trades else float("nan")
    exp = statistics.mean(expectancies) if expectancies else float("nan")
    pf = statistics.median(pfs) if pfs else float("nan")
    print(f"  {label:>10} {trades:>8} {wr:>9.3f} {exp:>11.2f} {net:>12,.0f} {pf:>14.3f}", flush=True)

layer.MIN_PENETRATION.update(CURRENT)
