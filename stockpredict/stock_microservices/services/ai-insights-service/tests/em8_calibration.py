"""EM-8 M2 — the objective-completion calibration (question (a)).

    PYTHONPATH=. python3 tests/em8_calibration.py [bars.tsv] [n_symbols]

Not a test. The measurement the register called *"the highest
information-per-hour of anything in this register, because it measures
machinery already shipped and in use"*.

The question
------------
Every one of the 13 detectors emits a `measured_move_target`, and
`decision-helper`'s `target_module` consumes it at **priority 1**. Nothing has
ever recorded whether those objectives are reached. E&M are explicit that they
are **minima** — H&S *"most emphatically … only a minimum"* — and equally
explicit that moves *with* the trend cannot be estimated at all.

PRE-REGISTERED CRITERION (plan §4, fixed before this file was written)
-----------------------------------------------------------------------
> For each E&M family, the completion rate within N sessions must exceed a
> **matched random-entry null** at **two or more** of N ∈ {10, 20, 60},
> clustered **by symbol**. Multiplicity: the ≥2-of-3 rule is itself a
> consistency filter, and **Holm** applies across families for any headline
> claim. The full table is published whatever it shows.
>
> **This is not a stop** — either result is reported and the work continues.

Why the window is 250 bars, and not "all history"
--------------------------------------------------
The detectors **search the whole frame they are handed**, so what they find at
bar *t* depends on how much history you give them. Measured: a trailing
200-bar slice disagrees with the full prefix on **76%** of (symbol, bar)
points. There is therefore no "correct" full-history detection to approximate
— and no need for one, because production is already windowed:
`decision-helper` requests `lookback_bars=250` (`market/client.py:158`) and
`insights_service` does `df.tail(250)`. The calibration replicates **exactly
that**, because the thing being calibrated is what the system does.

Method
------
* **Causality (C1).** The frame at bar *t* ends at *t*. The outcome window is
  `t+1 … t+N`, read afterwards.
* **The signal bar is the DETECTION bar**, never the pattern's key bar. A
  detector run at *t* may return a pattern whose head sits 80 bars earlier;
  measuring from there would credit it with moves that happened before it was
  knowable. (The same look-ahead EM-6 D1's first test contained.)
* **Episodes (`EC-M3`).** The same pattern is re-detected on many consecutive
  bars. Two detections with the same **absolute key bars** are the same
  pattern, and only the **earliest** is kept — which is also the first bar at
  which it was knowable.
* **Non-overlap (`EC-M4`).** Greedy, per symbol and horizon, over every
  qualifying episode — never a stride (`#87`).
* **Vacuous objectives (`EC-M1`)** — already behind price at *t* — are
  excluded and counted. Including them would score a free success.
* **Short tails (`EC-M2`)** excluded and counted.
* **E&M's rules and ours are never pooled** (`FR-EM-M4`).
"""
from __future__ import annotations

import math
import os
import random
import statistics
import sys
from collections import defaultdict
from typing import Dict, List, Optional, Sequence, Tuple

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.patterns.continuation import run_continuation_detectors  # noqa: E402
from app.services.patterns.reversal import run_reversal_detectors  # noqa: E402
from app.services.patterns.trap import run_trap_detectors  # noqa: E402

#: Exactly what production hands the detectors. See the module docstring.
WINDOW = 250

HORIZONS = (10, 20, 60)
NULL_DRAWS = 40                 # random entries per real observation

#: A family-horizon cell counts as passing only with at least this many
#: symbols behind it. `two_sided_p` is a normal approximation, which is
#: indefensible on three clusters -- and the smoke run on 3 symbols duly
#: produced a "survives" verdict from a cell with two. Reported either way;
#: it just cannot PASS.
MIN_SYMBOLS = 10
RNG_SEED = 20261021
MIN_BARS = WINDOW + max(HORIZONS) + 20

#: E&M give these families a measuring rule (master-list items 117-123).
EM_FAMILIES: Dict[str, str] = {
    "Head and Shoulders": "H&S (117)",
    "Inverse Head and Shoulders": "H&S (117)",
    "Double Top": "Double (123)",
    "Double Bottom": "Double (123)",
    "Flag": "Flag/Pennant (120)",
    "Pennant": "Flag/Pennant (120)",
    "Symmetrical Triangle": "Triangle (118)",
    "Ascending Triangle": "Triangle (118)",
    "Descending Triangle": "Triangle (118)",
    "Gap (runaway)": "Runaway gap (121)",
}

#: Ours, not the book's. Reported separately and never quoted as evidence
#: about E&M's rules (`FR-EM-M4`).
OUR_FAMILIES: Dict[str, str] = {
    "Wide-Ranging Day": "[ours] Wide-Ranging Day",
    "Bull Trap": "[ours] Trap",
    "Bear Trap": "[ours] Trap",
}


def family_of(pattern_name: str) -> Optional[str]:
    if pattern_name in EM_FAMILIES:
        return EM_FAMILIES[pattern_name]
    if pattern_name in OUR_FAMILIES:
        return OUR_FAMILIES[pattern_name]
    return None            # gap subtypes with no rule; they carry no objective


# ---------------------------------------------------------------------------
# data
# ---------------------------------------------------------------------------

def load(path: str) -> Dict[str, pd.DataFrame]:
    rows: Dict[str, List[Tuple]] = defaultdict(list)
    with open(path) as fh:
        for line in fh:
            p = line.rstrip("\n").split("\t")
            if len(p) >= 7:
                rows[p[0]].append((p[1], float(p[2]), float(p[3]),
                                   float(p[4]), float(p[5]), float(p[6])))
    out: Dict[str, pd.DataFrame] = {}
    for sym, rs in rows.items():
        if len(rs) < MIN_BARS:
            continue
        df = pd.DataFrame(sorted(rs), columns=["date", "open", "high",
                                               "low", "close", "volume"])
        out[sym] = df
    return out


# ---------------------------------------------------------------------------
# detection sweep
# ---------------------------------------------------------------------------

class Observation:
    __slots__ = ("symbol", "bar", "family", "pattern", "entry", "objective",
                 "up", "distance")

    def __init__(self, symbol, bar, family, pattern, entry, objective):
        self.symbol, self.bar = symbol, bar
        self.family, self.pattern = family, pattern
        self.entry, self.objective = entry, objective
        self.up = objective > entry
        self.distance = abs(objective - entry)


def sweep_symbol(symbol: str, df: pd.DataFrame) -> List[Observation]:
    """Every pattern episode in one symbol, earliest detection kept."""
    ohlc = df[["open", "high", "low", "close", "volume"]]
    close = df["close"].to_numpy(dtype=float)
    seen: Dict[Tuple, Observation] = {}

    for t in range(WINDOW, len(df)):
        start = t - WINDOW + 1
        frame = ohlc.iloc[start:t + 1].reset_index(drop=True)
        try:
            matches = (run_reversal_detectors(frame)
                       + run_continuation_detectors(frame)
                       + run_trap_detectors(frame))
        except Exception:  # noqa: BLE001 — a detector bug must not stop the sweep
            continue

        for m in matches:
            if m.measured_move_target is None:
                continue
            fam = family_of(m.pattern_name)
            if fam is None:
                continue
            # Absolute key bars identify the pattern itself (EC-M3).
            key = (m.pattern_name, tuple(b + start for b in (m.key_bars or ())))
            if key in seen:
                continue
            seen[key] = Observation(symbol, t, fam, m.pattern_name,
                                    float(close[t]), float(m.measured_move_target))
    return sorted(seen.values(), key=lambda o: o.bar)


# ---------------------------------------------------------------------------
# outcomes
# ---------------------------------------------------------------------------

def reached(df: pd.DataFrame, bar: int, horizon: int,
            objective: float, up: bool) -> Optional[bool]:
    """Did price touch the objective in `bar+1 .. bar+horizon`?"""
    end = bar + horizon
    if end >= len(df):
        return None                                  # EC-M2
    if up:
        return bool(df["high"].iloc[bar + 1:end + 1].max() >= objective)
    return bool(df["low"].iloc[bar + 1:end + 1].min() <= objective)


def excursion(df: pd.DataFrame, bar: int, horizon: int,
              obs: Observation) -> Optional[float]:
    """Maximum favourable excursion as a multiple of the objective distance.

    1.0 means price arrived exactly at the objective; 3.0 means it ran three
    times as far. This is what makes E&M's "minimum" claim measurable rather
    than rhetorical (`FR-EM-M5`).
    """
    end = bar + horizon
    if end >= len(df) or obs.distance <= 0:
        return None
    if obs.up:
        best = float(df["high"].iloc[bar + 1:end + 1].max()) - obs.entry
    else:
        best = obs.entry - float(df["low"].iloc[bar + 1:end + 1].min())
    return best / obs.distance


def null_rate(df: pd.DataFrame, obs: Observation, horizon: int,
              rng: random.Random) -> Optional[float]:
    """Matched random-entry null: same symbol, same direction, same DISTANCE.

    Matching on distance is the whole point — a nearer objective completes
    more often, so an unmatched null would measure the targets' *nearness*
    instead of the patterns' *information* (EM-2's construction).
    """
    hi = len(df) - horizon - 1
    if hi <= WINDOW or obs.distance <= 0:
        return None
    hits = 0
    for _ in range(NULL_DRAWS):
        t = rng.randint(WINDOW, hi)
        entry = float(df["close"].iloc[t])
        target = entry + obs.distance if obs.up else entry - obs.distance
        if reached(df, t, horizon, target, obs.up):
            hits += 1
    return hits / NULL_DRAWS


def non_overlapping(obs: Sequence[Observation], horizon: int) -> List[Observation]:
    kept, last = [], -10 ** 9
    for o in obs:
        if o.bar - last >= horizon:
            kept.append(o)
            last = o.bar
    return kept


# ---------------------------------------------------------------------------
# inference
# ---------------------------------------------------------------------------

def paired_t(diffs: Sequence[float]) -> Optional[float]:
    if len(diffs) < 3:
        return None
    sd = statistics.stdev(diffs)
    if sd <= 0:
        return None
    return statistics.fmean(diffs) / (sd / math.sqrt(len(diffs)))


def holm(pvals: Dict[str, float], alpha: float = 0.05) -> Dict[str, bool]:
    """Holm step-down across families. A family whose every cell was too thin
    to judge arrives with p = 1.0 and cannot survive, which is correct."""
    ordered = sorted(pvals.items(), key=lambda kv: kv[1])
    out, n = {}, len(ordered)
    for i, (k, p) in enumerate(ordered):
        if p <= alpha / (n - i):
            out[k] = True
        else:
            out[k] = False
            for k2, _ in ordered[i + 1:]:
                out[k2] = False
            break
    return out


def two_sided_p(t: Optional[float], n: int) -> float:
    """Normal approximation; n is reported beside it so the reader can judge."""
    if t is None:
        return 1.0
    z = abs(t)
    return math.erfc(z / math.sqrt(2.0))


def main() -> None:
    path = sys.argv[1] if len(sys.argv) > 1 else "/tmp/deep_bars.tsv"
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 0

    data = load(path)
    symbols = sorted(data)
    if limit:
        symbols = symbols[:limit]

    print("=" * 104, flush=True)
    print("EM-8 M2 — objective-completion calibration", flush=True)
    print("=" * 104, flush=True)
    print(f"  {len(symbols)} symbols, "
          f"{sum(len(data[s]) for s in symbols)} bars, window = {WINDOW} "
          f"(production's lookback_bars)", flush=True)
    print(f"  horizons {HORIZONS}, null draws {NULL_DRAWS}/observation, "
          f"clustered by symbol", flush=True)

    rng = random.Random(RNG_SEED)
    # family -> horizon -> symbol -> (real hits, n, null sum)
    agg: Dict[str, Dict[int, Dict[str, List[float]]]] = defaultdict(
        lambda: defaultdict(lambda: defaultdict(lambda: [0.0, 0.0, 0.0])))
    excursions: Dict[str, Dict[int, List[float]]] = defaultdict(lambda: defaultdict(list))
    detections = vacuous = short_tail = 0
    per_family_episodes: Dict[str, int] = defaultdict(int)

    for n_done, sym in enumerate(symbols, 1):
        df = data[sym]
        obs = sweep_symbol(sym, df)
        detections += len(obs)

        usable = []
        for o in obs:
            if (o.up and o.objective <= o.entry) or ((not o.up) and o.objective >= o.entry):
                vacuous += 1                      # EC-M1
                continue
            usable.append(o)
            per_family_episodes[o.family] += 1

        for h in HORIZONS:
            for o in non_overlapping(usable, h):
                r = reached(df, o.bar, h, o.objective, o.up)
                if r is None:
                    short_tail += 1               # EC-M2
                    continue
                nr = null_rate(df, o, h, rng)
                if nr is None:
                    continue
                cell = agg[o.family][h][sym]
                cell[0] += 1.0 if r else 0.0
                cell[1] += 1.0
                cell[2] += nr
                if r:
                    ex = excursion(df, o.bar, h, o)
                    if ex is not None:
                        excursions[o.family][h].append(ex)
        if n_done % 10 == 0:
            print(f"    ... {n_done}/{len(symbols)} symbols, "
                  f"{detections} episodes", flush=True)

    print(f"\n  episodes {detections}   excluded: vacuous {vacuous} (EC-M1), "
          f"short tail {short_tail} (EC-M2)", flush=True)

    for label, fams in (("E&M's measuring rules", sorted(set(EM_FAMILIES.values()))),
                        ("ours, not the book's", sorted(set(OUR_FAMILIES.values())))):
        print("\n" + "-" * 104)
        print(label.upper())
        print("-" * 104)
        print(f"{'family':22s} {'h':>4s} {'syms':>5s} {'obs':>6s} {'reached':>8s} "
              f"{'null':>7s} {'edge':>7s} {'t':>7s} {'p':>8s} "
              f"{'median overrun':>15s}")
        pvals: Dict[str, float] = {}
        passes: Dict[str, int] = defaultdict(int)
        for fam in fams:
            best_p = 1.0
            for h in HORIZONS:
                cells = agg[fam][h]
                diffs, tot_obs, tot_hit, tot_null = [], 0.0, 0.0, 0.0
                for sym, (hits, n, nullsum) in cells.items():
                    if n <= 0:
                        continue
                    diffs.append(hits / n - nullsum / n)
                    tot_obs += n
                    tot_hit += hits
                    tot_null += nullsum
                if not diffs or tot_obs <= 0:
                    print(f"{fam:22s} {h:>4d} {'-':>5s} {'0':>6s}   no observations")
                    continue
                t = paired_t(diffs)
                p = two_sided_p(t, len(diffs))
                edge = tot_hit / tot_obs - tot_null / tot_obs
                enough = len(diffs) >= MIN_SYMBOLS
                if enough and t is not None and t > 0 and p <= 0.05:
                    passes[fam] += 1
                # One-sided, deliberately: the criterion is that completion
                # must EXCEED the null. Feeding a negative cell's p-value into
                # Holm would let a family that is significantly WORSE than
                # chance print "survives" -- which is exactly what the first
                # full run did for Double, Flag/Pennant and H&S.
                if enough and t is not None and t > 0:
                    best_p = min(best_p, p)
                ex = excursions[fam][h]
                ex_s = f"{statistics.median(ex):.2f}x" if ex else "n/a"
                thin = "" if len(diffs) >= MIN_SYMBOLS else "  thin"
                print(f"{fam:22s} {h:>4d} {len(diffs):>5d} {int(tot_obs):>6d} "
                      f"{tot_hit/tot_obs:>7.1%} {tot_null/tot_obs:>6.1%} "
                      f"{edge:>+6.1%} {('n/a' if t is None else f'{t:+.2f}'):>7s} "
                      f"{p:>8.4f} {ex_s:>15s}{thin}")
            pvals[fam] = best_p
        if pvals:
            survived = holm(pvals)
            print(f"\n  {'family':22s} {'horizons passing':>17s} {'>=2 of 3':>10s} "
                  f"{'Holm':>8s}")
            for fam in fams:
                print(f"  {fam:22s} {passes[fam]:>17d} "
                      f"{('YES' if passes[fam] >= 2 else 'no'):>10s} "
                      f"{('survives' if survived.get(fam) else 'no'):>8s}")

    print("\n" + "=" * 104)
    print("'reached' = objective touched within the horizon; 'null' = matched "
          "random-entry rate (same symbol,")
    print("direction and objective DISTANCE). 'overrun' = max favourable "
          "excursion / objective distance,")
    print("median over the cases that completed — E&M call every objective a "
          "MINIMUM, and this is that claim.")
    print("=" * 104)


if __name__ == "__main__":
    main()
