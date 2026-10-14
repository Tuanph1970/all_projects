"""Backlog #79 phase 1 — dump CAUSAL pattern scans for the outcome study.

Not a test (pytest ignores it: no test_ prefix). Run from the service dir:

    PYTHONPATH=. python3 tests/causal_scan_dump.py

Writes /tmp/p79_scans.jsonl. Reads /tmp/all_bars.tsv (symbol, date, OHLCV,
tab-separated) which the Sessions Log entry for 2026-10-14 shows how to
extract from MySQL.

The two services both have a top-level `app` package, so the study runs in
two phases rather than one process: this one scans, and
decision-helper-service/tests/outcome_study.py evaluates.
"""

import collections
import json
import pandas as pd
from app.services.patterns import (
    run_reversal_detectors, run_continuation_detectors, run_trap_detectors,
)

WINDOW = 250          # what the service scans
STEP = 5              # sample every 5th bar
FORWARD = 20          # bars of forward return we need to exist
KEEP = ("pattern_name", "pattern_type", "found", "key_bars",
        "neckline", "measured_move_target")

rows = collections.defaultdict(list)
for line in open("/tmp/all_bars.tsv"):
    s, d, o, hi, lo, c, v = line.rstrip("\n").split("\t")
    rows[s].append((d, float(o), float(hi), float(lo), float(c), float(v)))

out = open("/tmp/p79_scans.jsonl", "w")
n = 0
for sym, bars in sorted(rows.items()):
    df_all = pd.DataFrame(bars, columns=["date", "open", "high", "low", "close", "volume"])
    last_t = len(bars) - FORWARD - 1
    for t in range(WINDOW, last_t + 1, STEP):
        # STRICT CAUSALITY: slice first, then scan. Never scan the full series
        # and index into it.
        frame = df_all.iloc[t - WINDOW + 1: t + 1].reset_index(drop=True)
        matches = (run_reversal_detectors(frame)
                   + run_continuation_detectors(frame)
                   + run_trap_detectors(frame))
        pats = []
        for m in matches:
            rec = {k: getattr(m, k) for k in KEEP}
            ev = m.volume_evidence or {}
            comp = (ev.get("components") or {}).get("breakout volume") or {}
            rec["volume_evidence"] = {
                "direction": ev.get("direction"),
                "components": {"breakout volume": {"breakout_bar": comp.get("breakout_bar")}},
            }
            pats.append(rec)
        out.write(json.dumps({
            "symbol": sym, "t": t, "lookback_bars": len(frame), "patterns": pats,
        }) + "\n")
        n += 1
    print(f"  {sym}: {n} cumulative scans", flush=True)
out.close()
print(f"DONE {n} causal scans -> /tmp/p79_scans.jsonl")
