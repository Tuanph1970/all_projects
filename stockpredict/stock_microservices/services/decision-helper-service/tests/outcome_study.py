"""Backlog #79 phase 2 — evaluate the dumped scans against a baseline.

Not a test (pytest ignores it). Run from the service dir after phase 1:

    PYTHONPATH=. python3 tests/outcome_study.py

Reports mean forward return after each verdict against the no-verdict
baseline on the same bars, on NON-OVERLAPPING windows. Results and their
reading: docs/dh79_failed_signal_outcome_study.md.
"""

import collections
import json
import math
import statistics
from datetime import date
from app.services.signal.failed_signal import (
    adapt_ai_insights_patterns, _hs_target_failure, _double_top_break,
)
from app.services.signal.base import OHLCVBar

bars_by_sym = collections.defaultdict(list)
for line in open("/tmp/all_bars.tsv"):
    sym, day, op, hi, lo, cl, vol = line.rstrip("\n").split("\t")
    year, month, dom = (int(x) for x in day.split("-"))
    bars_by_sym[sym].append(OHLCVBar(
        date=date(year, month, dom), open=float(op), high=float(hi),
        low=float(lo), close=float(cl), volume=float(vol),
    ))

recs = [json.loads(line) for line in open("/tmp/p79_scans.jsonl")]

def evaluate(min_gap, horizon):
    """min_gap: require samples at least this far apart, per symbol, so the
    forward windows do not overlap."""
    fired = collections.defaultdict(list)
    base = []
    syms = collections.defaultdict(set)
    last_t = {}
    for rec in recs:
        sym, t = rec["symbol"], rec["t"]
        if sym in last_t and t - last_t[sym] < min_gap:
            continue
        last_t[sym] = t
        bars = bars_by_sym[sym]
        if t + horizon >= len(bars):
            continue
        fwd = (bars[t+horizon].close - bars[t].close) / bars[t].close * 100.0
        adapted = adapt_ai_insights_patterns(rec, last_close=bars[t].close)
        hits = []
        if adapted:
            window = bars[t-rec["lookback_bars"]+1: t+1]
            for fn in (_hs_target_failure, _double_top_break):
                result = fn(window, len(window) - 1, adapted)
                if result:
                    hits.append(result)
        if hits:
            for result in hits:
                fired[(result.kind, result.direction)].append(fwd)
                syms[(result.kind, result.direction)].add(sym)
        else:
            base.append(fwd)
    return fired, base, syms

def welch(a, b):
    """Welch's t statistic — unequal variances, which these have."""
    if len(a) < 5 or len(b) < 5:
        return float("nan")
    se = math.sqrt(statistics.variance(a) / len(a) + statistics.variance(b) / len(b))
    if not se:
        return float("nan")
    return (statistics.mean(a) - statistics.mean(b)) / se

for horizon in (10, 20):
    print(f"  === horizon {horizon} bars, NON-OVERLAPPING samples (gap >= {horizon}) ===")
    fired, base, syms = evaluate(horizon, horizon)
    print(f"      baseline n={len(base)} mean={statistics.mean(base):+.3f}%")
    for key in sorted(fired, key=lambda k: -len(fired[k])):
        a = fired[key]
        print(f"      {key[0]+' / '+key[1]:32s} n={len(a):4d} syms={len(syms[key]):2d} "
              f"mean={statistics.mean(a):+7.3f}% diff={statistics.mean(a)-statistics.mean(base):+7.3f} "
              f"t={welch(a, base):+6.2f}")
    print()
