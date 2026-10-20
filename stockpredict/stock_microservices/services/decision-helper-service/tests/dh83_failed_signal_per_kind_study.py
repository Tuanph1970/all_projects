"""Backlog #83 — do the ten live failed-signal verdicts predict anything?

    PYTHONPATH=. python3 tests/dh83_failed_signal_per_kind_study.py

The exposure
------------
Ten verdict kinds reach the **live recommendation path**
(`decision/orchestrator.py`) and shape what a user is shown. None has ever
been validated:

* `#79` measured the two **pattern-based** kinds over 6,797 causal scans.
  Neither predicted anything, and `HS_TARGET_FAILURE/SHORT` was significantly
  **backwards** — it implied SHORT and the stock then outperformed by 1.4%.
  Both were demoted below `OVERRIDE_THRESHOLD` as a result.
* `#82` measured the remaining ten **as a group** inside the backtest and
  found them no better than nothing; the override was switched off there. But
  that was one pooled verdict on a measurement bench, not the live path, and
  it could not say *which* kinds were carrying the result.

So this is the per-kind study `#83` asked for, on the shape `#79` established.

Method, following #79
---------------------
* **Causal**: the frame is sliced *before* scanning, so each scan sees only
  bars up to its own date. S/R levels are recomputed from that same slice.
* **Non-overlapping**: samples are spaced at least `horizon` bars apart per
  symbol, because consecutive days' forward windows overlap almost entirely
  and overlapping windows inflate significance.
* **Against a baseline on the same bars**: the comparison is the no-verdict
  forward return over the identical sampled dates, not an unconditional
  average over a different population.
* **Signed by the verdict's own claim**: a LONG verdict is right when price
  rises, a SHORT verdict when it falls. The *directional edge* is therefore
  `(mean - baseline) x (+1 for LONG, -1 for SHORT)`. Positive means the
  verdict added value in the direction it implied.

CRITERION, FIXED BEFORE THE RUN
-------------------------------
Three outcomes per kind, and each has a different consequence:

  KEEP      directional edge positive and significant at MORE THAN ONE
            horizon -> the kind is validated and stays on the payload.
  REMOVE    edge significantly NEGATIVE at any horizon -> actively
            misleading; it must be removed or inverted, not merely demoted.
  UNVALIDATED  indistinguishable from the baseline -> not evidence. It should
            stop being surfaced as a verdict, which is #83's stated remedy.

"Indistinguishable" is not a pass. A verdict shown to a user asserts
something; one that cannot be shown to assert anything is noise with a label.
"""
from __future__ import annotations

import math
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

from app.services.backtest.market_features import compute_sr_levels
from app.services.signal.failed_signal import detect_failed_signals

from tests.failed_signal_override_study import load_bars

WINDOW = 120          # bars handed to the detectors
WARMUP = 150
HORIZONS = (10, 20, 60)
MAX_SYMBOLS = 32


def scan(bars_by_symbol, horizon: int):
    """Returns (per-(kind,direction) forward returns, baseline forward returns)."""
    fired: Dict[Tuple[str, str], List[float]] = defaultdict(list)
    baseline: List[float] = []

    for sym in sorted(bars_by_symbol)[:MAX_SYMBOLS]:
        bars = bars_by_symbol[sym]
        if len(bars) < WARMUP + horizon + 10:
            continue
        # Non-overlapping: step by the horizon so no two forward windows share
        # a bar within a symbol.
        for t in range(WARMUP, len(bars) - horizon - 1, horizon):
            window = bars[t - WINDOW + 1: t + 1]
            if len(window) < WINDOW:
                continue
            fwd = (bars[t + horizon].close - bars[t].close) / bars[t].close * 100.0

            try:
                sr = compute_sr_levels(window)
                verdicts = detect_failed_signals(window, bars[t].date, sr)
            except Exception:  # noqa: BLE001 — a detector bug must not end the study
                continue

            if verdicts:
                for v in verdicts:
                    fired[(v.kind, v.direction)].append(fwd)
            else:
                baseline.append(fwd)

    return fired, baseline


def welch(a: List[float], b: List[float]) -> Optional[float]:
    if len(a) < 2 or len(b) < 2:
        return None
    ma, mb = sum(a) / len(a), sum(b) / len(b)
    va = sum((x - ma) ** 2 for x in a) / (len(a) - 1)
    vb = sum((x - mb) ** 2 for x in b) / (len(b) - 1)
    se = math.sqrt(va / len(a) + vb / len(b))
    return (ma - mb) / se if se else None


if __name__ == "__main__":
    bars = load_bars()
    # kind -> horizon -> (n, edge, t)
    table: Dict[Tuple[str, str], Dict[int, Tuple[int, float, Optional[float]]]] = \
        defaultdict(dict)

    for h in HORIZONS:
        fired, base = scan(bars, h)
        base_mean = sum(base) / len(base) if base else 0.0
        print(f"horizon {h:>3} sessions: baseline n={len(base)}, "
              f"mean {base_mean:+.2f}%")
        for key, vals in sorted(fired.items()):
            if len(vals) < 2:
                continue
            mean = sum(vals) / len(vals)
            sign = 1.0 if key[1] == "LONG" else -1.0
            edge = (mean - base_mean) * sign
            t = welch(vals, base)
            table[key][h] = (len(vals), edge, (t * sign) if t is not None else None)

    print(f"\n{'kind / direction':<34}", end="")
    for h in HORIZONS:
        print(f"{'n':>6}{f'edge@{h}':>10}{'t':>7}", end="")
    print("   VERDICT")

    for key in sorted(table):
        print(f"{key[0] + ' / ' + key[1]:<34}", end="")
        sig_pos = sig_neg = 0
        for h in HORIZONS:
            cell = table[key].get(h)
            if not cell:
                print(f"{'-':>6}{'-':>10}{'-':>7}", end="")
                continue
            n, edge, t = cell
            print(f"{n:>6}{edge:>+10.2f}{(t if t is not None else 0):>+7.2f}", end="")
            if t is not None and t > 1.96:
                sig_pos += 1
            elif t is not None and t < -1.96:
                sig_neg += 1
        if sig_neg:
            verdict = "REMOVE (backwards)"
        elif sig_pos >= 2:
            verdict = "KEEP"
        else:
            verdict = "UNVALIDATED"
        print(f"   {verdict}")
