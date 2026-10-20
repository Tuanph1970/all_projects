"""Backlog #81 — should `volume_factor` have a ceiling above 1.0?

    PYTHONPATH=. python3 tests/em1_factor_ceiling_study.py

The question
------------
`FR-EM-V7` chose deliberately asymmetric bounds, ``[0.5, 1.15]``, on the
reasoning that "E&M's volume evidence discredits better than it promotes" — so
1.15 was already the smaller half. `#70` then made the significance gate
well-posed and `#80`-era measurement showed the consequence: against a bar set
at the **geometry-only** 95th percentile, EM-1 moves null survivors from 4.6%
to **21.7%**. A lucky volume reading on a random walk can be lifted across a
bar that was set without volume.

That is not a contradiction — the mean comparison still passes, so volume
lowers noise confidence *on average*. It is an upper-tail effect. The question
is whether that tail buys anything.

CRITERION, FIXED BEFORE THE RUN
-------------------------------
A ceiling above 1.0 earns its place only if it **increases detection power at
a fixed false-positive rate**:

    For each candidate ceiling, set the gate at that configuration's OWN null
    95th percentile per pattern — which holds the false-positive rate at 5% by
    construction — and measure the share of PLANTED patterns that clear their
    own pattern's gate. The ceiling is justified only if that true-positive
    rate rises with it.

If power is flat or falls, the ceiling promotes noise as readily as signal, it
is buying nothing, and it should be 1.0 — volume should only ever discredit.

This is a single point on a ROC curve held at one FPR, which is the only fair
way to compare: comparing raw confidences across ceilings would reward the
ceiling for inflating every number.
"""
from __future__ import annotations

from typing import Dict, List, Tuple

import app.services.patterns.volume as volume_mod

from tests.volume_harness import (
    bar_pattern_frames,
    consolidation_frames,
    detect_all,
    planted_frames,
    run_null,
)

N_SURROGATES = 200
LENGTH = 250
VOLATILITY = 0.015
SEED = 20261020

CEILINGS = (1.0, 1.05, 1.15, 1.30, 1.60)


def _all_planted() -> List:
    """Every planted set the harness builds, for the largest honest sample."""
    out = []
    for builder in (planted_frames, consolidation_frames, bar_pattern_frames):
        try:
            out.extend(builder())
        except Exception:  # noqa: BLE001 — a builder that cannot run is skipped
            continue
    return out


def measure(ceiling: float) -> Dict[str, float]:
    original = volume_mod.FACTOR_CEILING
    volume_mod.FACTOR_CEILING = ceiling
    try:
        # 1. The null, at THIS ceiling, gives the per-pattern 5% gate.
        report = run_null(
            null_name="synthetic",
            n_surrogates=N_SURROGATES,
            length=LENGTH,
            volatility=VOLATILITY,
            seed=SEED,
        )
        gates = report.confidence_pct95_by_pattern

        # 2. Planted patterns, at the same ceiling, against those gates.
        hits = tested = 0
        for planted in _all_planted():
            for match in detect_all(planted.frame):
                if match.pattern_name != planted.target_pattern:
                    continue
                gate = gates.get(match.pattern_name)
                if gate is None:
                    continue
                tested += 1
                if float(match.confidence) > gate:
                    hits += 1

        return {
            "ceiling": ceiling,
            "tpr": hits / tested if tested else 0.0,
            "hits": hits,
            "tested": tested,
            "null_mean_conf": report.mean_confidence,
            "null_detections": report.detections_per_surrogate,
        }
    finally:
        volume_mod.FACTOR_CEILING = original


if __name__ == "__main__":
    print("Backlog #81 — detection power at a fixed 5% false-positive rate\n")
    print(f"{'ceiling':>9}{'planted cleared':>18}{'TPR':>8}"
          f"{'null mean conf':>16}{'null det/surr':>15}")
    rows: List[Tuple[float, float]] = []
    for c in CEILINGS:
        r = measure(c)
        rows.append((c, r["tpr"]))
        print(f"{r['ceiling']:>9.2f}{r['hits']:>10d}/{r['tested']:<7d}"
              f"{r['tpr']:>7.1%}{r['null_mean_conf']:>16.4f}"
              f"{r['null_detections']:>15.3f}")

    base = dict(rows).get(1.0, 0.0)
    best = max(rows, key=lambda kv: kv[1])
    print(f"\nCRITERION: a ceiling above 1.0 must RAISE the true-positive rate.")
    print(f"   ceiling 1.00 -> TPR {base:.1%}")
    print(f"   best above 1.0 -> ceiling {best[0]:.2f} at TPR {best[1]:.1%}")
    gain = best[1] - base
    verdict = ("KEEP a ceiling above 1.0" if gain > 0.0 and best[0] > 1.0
               else "SET THE CEILING TO 1.0 — it buys nothing")
    print(f"   difference {gain:+.1%}  ->  {verdict}")
