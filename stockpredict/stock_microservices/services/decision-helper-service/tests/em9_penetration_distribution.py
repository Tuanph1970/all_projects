"""EM-9 — where does the penetration filter actually bind?

Not a test (pytest ignores it). Run from the service dir:

    PYTHONPATH=. python3 tests/em9_penetration_distribution.py

Reads /tmp/all_bars.tsv (symbol, date, OHLCV; tab-separated) — see the Sessions
Log entry for 2026-10-14 for the MySQL extract.

Reports, per signal kind, the distribution of ACTUAL penetration and the share
of signals that would survive each candidate threshold. This is the half of
EM-9's evidence that the backtest cannot show: the backtest says what the
outcome is, this says which kinds a given threshold would silence.

The S/R kinds need an S/R payload and only fire in RANGE regime, which is why
they are gathered here with `compute_sr_levels` rather than alongside the trend
signals.
"""

import collections
import statistics
from datetime import date

from app.services.confirmation.layer import _extract_trigger_level
from app.services.backtest.market_features import compute_sr_levels
from app.services.signal.base import OHLCVBar
from app.services.signal.range.sr_bounce_breakout import detect_sr_signal

bars_by_sym = collections.defaultdict(list)
for line in open("/tmp/all_bars.tsv"):
    sym, day, op, hi, lo, cl, vol = line.rstrip("\n").split("\t")
    y, m, d = (int(x) for x in day.split("-"))
    bars_by_sym[sym].append(OHLCVBar(date=date(y, m, d), open=float(op), high=float(hi),
                                     low=float(lo), close=float(cl), volume=float(vol)))

pens = collections.defaultdict(list)
for sym in sorted(bars_by_sym):
    bars = bars_by_sym[sym]
    for t in range(300, len(bars), 5):
        so_far = bars[: t + 1]
        sr = compute_sr_levels(so_far)
        if not sr:
            continue
        sig = detect_sr_signal(so_far, bars[t].date, sr)
        if not sig:
            continue
        lvl = _extract_trigger_level(sig)
        if not lvl or lvl <= 0:
            continue
        p = ((sig.trigger_price - lvl) / lvl if sig.direction == "LONG"
             else (lvl - sig.trigger_price) / lvl)
        pens[sig.kind].append(p * 100.0)

print(f"  {'signal kind':18s} {'n':>6} {'median':>8} {'p75':>8} {'p90':>8} "
      f"{'>=0.3%':>8} {'>=0.5%':>8} {'>=1%':>7} {'>=2%':>7} {'>=3%':>7}")
for kind, vals in sorted(pens.items()):
    v = sorted(x for x in vals if x == x)
    if not v:
        continue
    sh = lambda th: sum(1 for x in v if x >= th) / len(v)   # noqa: E731
    print(f"  {kind:18s} {len(v):>6} {statistics.median(v):>8.3f} "
          f"{v[int(len(v)*0.75)]:>8.3f} {v[int(len(v)*0.90)]:>8.3f} "
          f"{sh(0.3):>8.0%} {sh(0.5):>8.0%} {sh(1.0):>7.0%} {sh(2.0):>7.0%} {sh(3.0):>7.0%}")
