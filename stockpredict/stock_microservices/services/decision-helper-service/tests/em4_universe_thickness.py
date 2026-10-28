"""Backlog #100 — is EM-4's bottoms verdict an artefact of a thin universe?

    PYTHONPATH=. python3 tests/em4_universe_thickness.py

Pre-registered in `docs/backlog100_em4_universe_thickness.md`, Part 1,
committed at `fb1765de` **before this file was written**. Nothing here may be
tuned against its own output.

The question. MEI is the share of a *universe* in a bullish major trend, and
`MIN_UNIVERSE = 10` admits a reading computed on ten symbols. Magee kept ~100
charts, and `#87` flagged that a reading off 11 "is not the same instrument as
one off 92". `#99` settled the bottoms claim — fails 0 of 3 — but on a series
that mixes both instruments.

The threshold, fixed in Part 1 on a stated principle rather than on what it
does to the result: a reading taken on a **minority** of the universe is a
different instrument, not a thin version of the same one, so the line is half
the 92-symbol dump.

Everything else is #99's, untouched: DECILE, WARMUP_POINTS, the expanding
trailing decile, every qualifying day, and the moving-block bootstrap at
L = 2h with B = 2000 and seed 20261027.
"""
from __future__ import annotations

from statistics import mean
from typing import List

from app.services.breadth.mei import MeiPoint, compute_mei_series

from tests.em4_mei_study import (
    HORIZONS,
    WARMUP_POINTS,
    load_bars,
    load_index,
    low_flags,
    phase_independent_table,
)

#: Pre-registered: half of the 92-symbol universe. Not the 30 that happened to
#: be measured while #100 was opened, and not tuned to anything.
MIN_CLASSIFIED = 46

#: Pre-registered power floor. Raising the threshold cuts n in the arm that was
#: already binding, so a horizon thinner than this is reported as underpowered
#: rather than as evidence either way.
MIN_LOW_OBSERVATIONS = 30

#: Reported beside the primary, never instead of it: a pass that exists at one
#: cut-off and nowhere else is "not robust", per Part 1's constraint 3.
SWEEP = (10, 20, 30, 46, 60, 80)


def thicker_than(series: List[MeiPoint], threshold: int) -> List[MeiPoint]:
    """Readings computed on at least `threshold` classified symbols.

    Equivalent to `compute_mei_series(bars, min_universe=threshold)` because
    `classified`, `bullish` and `mei` are computed per day independently of
    `min_universe`, which only decides whether the day is emitted. Asserted
    against a real recomputation in `main` rather than left as a claim — the
    whole item turns on this filter meaning what it says.
    """
    return [p for p in series if p.classified >= threshold]


def main() -> None:
    bars, bars_label = load_bars()
    index, index_label = load_index()
    print(f"universe = {len(bars)} symbols  ({bars_label})")
    print(f"market   = {index_label}\n")

    series = compute_mei_series(bars)
    print(f"MEI at MIN_UNIVERSE=10: {len(series)} readings, "
          f"{series[0].day} -> {series[-1].day}")

    # The correctness check that the whole item rests on.
    direct = compute_mei_series(bars, min_universe=MIN_CLASSIFIED)
    filtered = thicker_than(series, MIN_CLASSIFIED)
    same = ([p.day for p in direct] == [p.day for p in filtered]
            and [p.mei for p in direct] == [p.mei for p in filtered])
    print(f"filter == recomputation at {MIN_CLASSIFIED}: {same} "
          f"({len(direct)} vs {len(filtered)} readings)")
    if not same:
        raise SystemExit("filter is NOT equivalent to recomputation — stop; "
                         "every number below would be unattributable")

    print(f"\n{'=' * 78}")
    print(f"PRIMARY - MIN_CLASSIFIED = {MIN_CLASSIFIED} (half of 92), "
          f"pre-registered")
    print(f"{'=' * 78}")
    thick = filtered
    print(f"readings: {len(series)} -> {len(thick)} "
          f"({len(thick) / len(series) * 100:.1f}% kept), "
          f"{thick[0].day} -> {thick[-1].day}")
    sizes = [p.classified for p in thick]
    print(f"classified at those readings: min {min(sizes)}, "
          f"median {sorted(sizes)[len(sizes) // 2]}, max {max(sizes)}\n")

    print(f"{'horizon':>8}{'n low':>7}{'n other':>9}{'edge':>9}{'t boot':>9}"
          f"{'2.5 pct':>9}{'disc':>6}{'power':>12}")
    passes = testable = 0
    for h, n_low, n_oth, edge, t_boot, low_pct, disc in phase_independent_table(
            thick, index):
        powered = n_low >= MIN_LOW_OBSERVATIONS
        testable += 1 if powered else 0
        sig = powered and t_boot is not None and t_boot > 1.96
        passes += 1 if sig else 0
        print(f"{h:>8}{n_low:>7}{n_oth:>9}{edge:>+8.2f}%"
              f"{(t_boot if t_boot is not None else float('nan')):>+9.2f}"
              f"{(low_pct if low_pct is not None else float('nan')):>+8.2f}%"
              f"{disc:>6}"
              f"{('ok' if powered else 'UNDERPOWERED'):>12}"
              f"  {'SIG' if sig else 'ns'}")

    print(f"\nCRITERION (inherited from #87): significant at more than one "
          f"horizon -> {passes} of {len(HORIZONS)}")
    print(f"POWER FLOOR (pre-registered, >= {MIN_LOW_OBSERVATIONS} low obs): "
          f"{testable} of {len(HORIZONS)} horizons testable")
    if testable < 2:
        print("  -> UNDERPOWERED OVERALL. The thin-universe caveat stays OPEN;\n"
              "     this market's history cannot answer #100.")
    elif passes >= 2:
        print("  -> PASSES. Treat as a SECOND INSTRUMENT TRIED, with the\n"
              "     multiplicity stated; check the sweep below before any headline.")
    else:
        print("  -> FAILS with adequate power. #87/#90's thin-universe caveat is\n"
              "     ANSWERED: the verdict does not depend on thin readings.")

    print(f"\n{'=' * 78}")
    print("SECONDARY (pre-registered, reported never instead of the primary):")
    print("the full sweep, so a result existing at one cut-off is visible as such")
    print(f"{'=' * 78}")
    print(f"{'min_cls':>8}{'readings':>10}" + "".join(
        f"{'n' + str(h):>6}{'t' + str(h):>8}" for h in HORIZONS))
    for threshold in SWEEP:
        sub = thicker_than(series, threshold)
        if len(sub) < 400:
            print(f"{threshold:>8}{len(sub):>10}   too few readings to estimate")
            continue
        cells = ""
        for h, n_low, _, _, t_boot, _, _ in phase_independent_table(sub, index):
            cells += f"{n_low:>6}" + (
                f"{t_boot:>+8.2f}" if t_boot is not None else f"{'n/a':>8}")
        print(f"{threshold:>8}{len(sub):>10}{cells}")

    print("\nFor orientation only (not a test): forward returns by thickness,")
    print("low-MEI arm at h60. Derived with the same classification as the")
    print("estimator, but carrying each observation's own `classified` count —")
    print("zipping `forward_observations` against a series slice would MISALIGN,")
    print("because it skips days the index has no price for.")
    horizon = 60
    flags = low_flags(series)
    thin: List[float] = []
    thick_rets: List[float] = []
    for i in range(WARMUP_POINTS, len(series) - horizon):
        if not flags[i]:
            continue
        d0, d1 = series[i].day, series[i + horizon].day
        if d0 not in index or d1 not in index or index[d0] <= 0:
            continue
        ret = (index[d1] / index[d0] - 1.0) * 100.0
        (thick_rets if series[i].classified >= MIN_CLASSIFIED else thin).append(ret)
    for label, xs in (("thin (<46)", thin), (f"thick (>={MIN_CLASSIFIED})", thick_rets)):
        if xs:
            print(f"   {label:<14} n={len(xs):>4}  mean {mean(xs):+7.2f}%")
        else:
            print(f"   {label:<14} n=   0")


if __name__ == "__main__":
    main()
