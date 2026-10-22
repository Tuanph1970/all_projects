"""EM-5 L3 / GATE A — does the SLOPE earn anything?

    PYTHONPATH=. python3 tests/em5_gate_a_study.py [bars.tsv] [n_symbols] [stride]

Not a test. The question the previous five E&M candidates kept circling
without asking directly.

A trendline is a **sloping level** drawn through the same swing pivots that
EM-2's horizontal levels come from. EM-2 established that levels are **real**
(every arm beat a matched-distance null) and that **no elaboration beat
counting touches**. EM-7 established that the throwback to a level is **real**
and that the tactic built on it **loses money**.

So:

> Does a **trendline** break carry information that a **horizontal level
> through the same anchors** does not?

PRE-REGISTERED CRITERION (plan §5, fixed before this file was written)
-----------------------------------------------------------------------
> Arm T must beat Arm H at **two or more** of the 10/20/60-session horizons,
> clustered **by symbol**, with **event counts reported for both arms**.
>
> **On failure: stop.** No `L4`, no Phase B, and EM-5 is recorded as what it
> would then be — a re-derivation of EM-2's levels with extra steps.

The comparison, fixed in the plan rather than here
---------------------------------------------------
A line is anchored on two confirmed pivots at `p1` (earlier) and `p2` (later).

* **Arm T** — the trendline's first decisive penetration (`FR-EM-L5`).
* **Arm H** — the first break of the **horizontal at `p2`**, the most recent
  anchor price, via EM-7 T1's shipped `detect_level_breaks`. `p2` is chosen
  because that is exactly the level EM-2 and EM-7 actually use: a horizontal
  sitting at a pivot. Same pivots, same bars, **slope the only difference**.
* **Arm H-mid** — robustness: the horizontal at the mean of `p1` and `p2`.

Both arms are restricted to **confirmed** lines (≥3 contacts), so the
restriction is inherited identically rather than applied to one side. `L1`
measured 89 admissible lines per bar, most resting on exactly two anchors —
without that restriction a "break" would mean "something happened to one of
89 lines".

Why a stride is safe here, when `#87` showed it is not for episodes
-------------------------------------------------------------------
Lines are **discovered** on a stride, not sampled on one. A line's anchors are
fixed, so once confirmed it stays discoverable for hundreds of bars — unlike
`#87`'s low-MEI episodes, which were short and clustered and which a stride
stepped straight over. Events are then deduplicated per `(bar, direction)`
and sampled with greedy non-overlap, so the stride never touches the event
sample.
"""
from __future__ import annotations

import math
import os
import statistics
import sys
from collections import defaultdict
from datetime import date
from typing import Dict, List, Optional, Sequence, Set, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.backtest.market_features import (  # noqa: E402
    atr_series,
    detect_level_breaks,
)
from app.services.market_context.trendline import (  # noqa: E402
    KIND_UP,
    Trendline,
    admissible_lines,
)
from app.services.market_context.trendline_breaks import (  # noqa: E402
    count_contacts,
    detect_penetration,
)
from app.services.signal.base import OHLCVBar  # noqa: E402

HORIZONS = (10, 20, 60)
MIN_CONTACTS = 3
#: 3% is E&M's figure for a stock, 2% for the averages; the ATR arm is the
#: declared alternative the plan requires. Reported side by side.
PEN_SETTINGS = (("3% (book)", 0.03, None),
                ("2% (averages)", 0.02, None),
                ("1.0 ATR", None, 1.0))
MIN_EVENTS = 8


def load(path: str) -> Dict[str, List[OHLCVBar]]:
    rows: Dict[str, List[OHLCVBar]] = defaultdict(list)
    with open(path) as fh:
        for line in fh:
            p = line.rstrip("\n").split("\t")
            if len(p) >= 7:
                rows[p[0]].append(OHLCVBar(
                    date=date.fromisoformat(p[1]), open=float(p[2]),
                    high=float(p[3]), low=float(p[4]), close=float(p[5]),
                    volume=int(float(p[6]))))
    return {s: sorted(b, key=lambda x: x.date) for s, b in rows.items()}


def _pct_penetration(bars, line, atr, pct, atr_mult) -> Optional[int]:
    """First decisive close beyond the line, by percent OR in ATR units."""
    up = line.kind == KIND_UP
    for i in range(line.b_index + 1, len(bars)):
        c = bars[i].close
        if c <= 0:
            continue
        v = line.value_at(i)
        if v <= 0:
            continue
        beyond = (v - c) if up else (c - v)
        if beyond <= 0:
            continue
        if pct is not None:
            if beyond / v >= pct:
                return i
        else:
            a = atr[i]
            if a is not None and a > 0 and beyond >= a * atr_mult:
                return i
    return None


def _forward(bars: Sequence[OHLCVBar], i: int, horizon: int,
             up: bool) -> Optional[float]:
    """Return in the direction of the break, in percent. Both ends guarded —
    13 zero-price vendor bars exist (`#93`), and guarding only the entry is
    the mistake EM-7's T4 study made."""
    j = i + horizon
    if j >= len(bars):
        return None
    e, x = bars[i].close, bars[j].close
    if e <= 0 or x <= 0:
        return None
    return ((x / e - 1.0) if up else (e / x - 1.0)) * 100.0


def _non_overlapping(events: Sequence[Tuple[int, bool]], horizon: int):
    kept, last = [], -10 ** 9
    for bar, up in sorted(events):
        if bar - last >= horizon:
            kept.append((bar, up))
            last = bar
    return kept


def sweep_symbol(bars: Sequence[OHLCVBar], stride: int,
                 pct: Optional[float], atr_mult: Optional[float]) -> Dict[str, List]:
    atr = atr_series(bars)
    n = len(bars)

    # --- discover distinct CONFIRMED lines on a stride ---------------------
    seen: Set[Tuple] = set()
    lines: List[Trendline] = []
    for t in range(300, n, stride):
        for ln in admissible_lines(bars, at_index=t):
            key = (ln.kind, ln.a_index, ln.b_index)
            if key in seen:
                continue
            seen.add(key)
            lines.append(ln)

    t_events: Set[Tuple[int, bool]] = set()
    h_events: Set[Tuple[int, bool]] = set()
    m_events: Set[Tuple[int, bool]] = set()

    for ln in lines:
        up_line = ln.kind == KIND_UP
        broke_up = not up_line                      # UP line breaks DOWN

        # --- Arm T ---------------------------------------------------------
        pen = _pct_penetration(bars, ln, atr, pct, atr_mult)
        if pen is not None and count_contacts(bars, ln, pen, atr=atr) >= MIN_CONTACTS:
            t_events.add((pen, broke_up))

            # --- Arms H and H-mid, inheriting the same confirmed line ------
            role = "support" if up_line else "resistance"
            for price, bucket in ((ln.b_price, h_events),
                                  ((ln.a_price + ln.b_price) / 2.0, m_events)):
                brks = detect_level_breaks(bars, price, role=role,
                                           first_bar=ln.b_index, atr=atr)
                if brks:
                    bucket.add((brks[0]["bar_index"], broke_up))

    out: Dict[str, List] = {}
    for name, ev in (("T", t_events), ("H", h_events), ("H-mid", m_events)):
        per_h = {}
        for h in HORIZONS:
            rets = []
            for bar, up in _non_overlapping(sorted(ev), h):
                r = _forward(bars, bar, h, up)
                if r is not None:
                    rets.append(r)
            per_h[h] = rets
        out[name] = [len(ev), per_h]
    return out


def paired_t(diffs: Sequence[float]) -> Optional[float]:
    if len(diffs) < 3:
        return None
    sd = statistics.stdev(diffs)
    if sd <= 0:
        return None
    return statistics.fmean(diffs) / (sd / math.sqrt(len(diffs)))


def sign_p(wins: int, n: int) -> float:
    if n == 0:
        return 1.0
    tail = sum(math.comb(n, k) for k in range(0, min(wins, n - wins) + 1))
    return min(1.0, 2.0 * tail / (2 ** n))


def main() -> None:
    path = sys.argv[1] if len(sys.argv) > 1 else "/tmp/deep_bars.tsv"
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    stride = int(sys.argv[3]) if len(sys.argv) > 3 else 25

    data = load(path)
    symbols = sorted(data)
    if limit:
        symbols = symbols[:limit]

    print("=" * 100, flush=True)
    print("EM-5 L3 / GATE A — does the slope earn anything?", flush=True)
    print("=" * 100, flush=True)
    print(f"  {len(symbols)} symbols | line discovery stride {stride} | "
          f"confirmed lines only (>={MIN_CONTACTS} contacts)", flush=True)
    print(f"  Arm T  = trendline penetration", flush=True)
    print(f"  Arm H  = horizontal at p2 (the most recent anchor) — "
          f"same pivots, slope the only difference", flush=True)
    print(f"  Arm H-mid = horizontal at mean(p1, p2), robustness", flush=True)
    print(f"  CRITERION: T beats H at >=2 of {HORIZONS} horizons, "
          f"symbol-clustered, event counts reported\n", flush=True)

    verdict: Dict[str, int] = {}
    for label, pct, atr_mult in PEN_SETTINGS:
        per_symbol: Dict[str, Dict[str, List]] = {}
        for i, sym in enumerate(symbols, 1):
            bars = data[sym]
            if len(bars) < 500:
                continue
            res = sweep_symbol(bars, stride, pct, atr_mult)
            if res["T"][0] >= MIN_EVENTS and res["H"][0] >= MIN_EVENTS:
                per_symbol[sym] = res
            if i % 10 == 0:
                print(f"    ... [{label}] {i}/{len(symbols)} symbols, "
                      f"{len(per_symbol)} usable", flush=True)

        print("-" * 100)
        print(f"PENETRATION = {label}   ({len(per_symbol)} symbols)")
        print(f"  {'arm':8s} {'events':>8s} {'h':>4s} {'obs':>6s} {'mean %':>8s} "
              f"{'vs T':>8s} {'t':>7s} {'symbols better':>16s}")
        if not per_symbol:
            print("  no usable symbols at this setting")
            verdict[label] = 0
            continue

        totals = {a: sum(per_symbol[s][a][0] for s in per_symbol)
                  for a in ("T", "H", "H-mid")}
        passes = 0
        for h in HORIZONS:
            means = {}
            for arm in ("T", "H", "H-mid"):
                vals = [statistics.fmean(per_symbol[s][arm][1][h])
                        for s in per_symbol if per_symbol[s][arm][1][h]]
                means[arm] = vals
            for arm in ("T", "H", "H-mid"):
                vals = means[arm]
                if not vals:
                    continue
                obs = sum(len(per_symbol[s][arm][1][h]) for s in per_symbol)
                if arm == "T":
                    print(f"  {arm:8s} {totals[arm]:>8d} {h:>4d} {obs:>6d} "
                          f"{statistics.fmean(vals):>+7.3f} {'—':>8s} {'—':>7s} {'—':>16s}")
                    continue
                common = [s for s in per_symbol
                          if per_symbol[s]["T"][1][h] and per_symbol[s][arm][1][h]]
                diffs = [statistics.fmean(per_symbol[s]["T"][1][h])
                         - statistics.fmean(per_symbol[s][arm][1][h]) for s in common]
                t = paired_t(diffs)
                wins = sum(1 for d in diffs if d > 0)
                if arm == "H" and t is not None and t > 1.96:
                    passes += 1
                print(f"  {arm:8s} {totals[arm]:>8d} {h:>4d} {obs:>6d} "
                      f"{statistics.fmean(vals):>+7.3f} "
                      f"{(statistics.fmean(diffs) if diffs else float('nan')):>+7.3f} "
                      f"{('n/a' if t is None else f'{t:+.2f}'):>7s} "
                      f"{wins}/{len(diffs)} p={sign_p(wins, len(diffs)):.3f}")
        verdict[label] = passes
        print(f"  -> T beats H at {passes} of {len(HORIZONS)} horizons")

    primary = verdict.get("3% (book)", 0)
    print("\n" + "=" * 100)
    print(f"GATE A (penetration = 3%, the book's figure) -> "
          f"{'PASS' if primary >= 2 else 'FAIL'}  "
          f"[{primary} of {len(HORIZONS)} horizons]")
    print(f"  all settings: " + ", ".join(f"{k} {v}/3" for k, v in verdict.items()))
    if primary < 2:
        print("  Pre-registered consequence: STOP. No L4, no Phase B. EM-5 is a")
        print("  re-derivation of EM-2's levels with extra steps.")
    print("=" * 100)


if __name__ == "__main__":
    main()
