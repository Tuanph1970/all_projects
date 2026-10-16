"""EM-2 / S6 — `H-S3`: is the third attack odds-on to penetrate?

Test-support, not a test module (no ``test_`` prefix).

Edwards & Magee, Ch 13:

    "It is an odds-on assumption that a third attack at a Resistance Level
    will succeed in penetrating it."

That is a **falsifiable prediction**, not a parameter. `FR-EM-S4` and the plan
are both explicit: measure the first / second / third-attack penetration rate
on VN data against a coin flip, report it either way, and **if the third
attack is not odds-on, the weighting does not ship** and the count stays as
evidence only.

Odds-on means more likely than not: a penetration rate above 50%.

Method
------
For each level built causally at a test date, walk its approach sequence in
order (`detect_attacks`) and record, for each ordinal — first approach,
second, third, fourth-or-later — whether that approach ended in a
penetration. Aggregating across levels and symbols gives a penetration rate
per ordinal.

Two things this deliberately does **not** do:

* It does not condition on the level surviving. Every level's approach
  sequence is read in full, so a level that broke on its first approach
  contributes a penetration at ordinal 1 rather than vanishing from the
  sample. Dropping those would guarantee a rising rate by construction.
* It does not reuse the hit-rate harness's outcome rule. That rule asks
  "did price reverse near this level", which is a different question from
  "did this approach break through", and conflating them would make the
  answer depend on `H-S1`'s thresholds.

Run it directly::

    PYTHONPATH=. python3 tests/sr_attack_study.py
"""
from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Tuple
from unittest.mock import MagicMock

from app.services.analysis_service import AnalysisService
from app.services.sr_volume import detect_attacks, trailing_atr

from tests.sr_hitrate_harness import (
    STEP,
    WINDOW,
    _selected,
    _shipped_levels,
    source_bars,
)

MAX_ORDINAL = 4  # 4 means "fourth or later"


def run_attack_study(
    max_symbols: int = 32,
    step: int = STEP,
    window: int = WINDOW,
) -> Tuple[Dict[int, Dict[str, int]], str, int]:
    """Penetration counts by approach ordinal.

    Returns ``({ordinal: {"n": .., "penetrated": ..}}, source_label, levels)``.
    """
    bars, label = source_bars()
    bars = _selected(bars, max_symbols)
    svc = AnalysisService(session=MagicMock())

    counts: Dict[int, Dict[str, int]] = defaultdict(lambda: {"n": 0, "penetrated": 0})
    levels_seen = 0

    for symbol in sorted(bars):
        df = bars[symbol]
        for t in range(window, len(df), step):
            # C1: slice first, then build. The approach sequence is read only
            # from bars inside the window the level was built from.
            frame = df.iloc[t - window + 1: t + 1].reset_index(drop=True)
            try:
                atr = trailing_atr(frame)
            except Exception:  # noqa: BLE001
                continue

            for lvl in _shipped_levels(svc, frame):
                levels_seen += 1
                first_bar = min(tch.bar_index for tch in lvl.touches)
                approaches = detect_attacks(
                    frame, lvl.price, first_bar=first_bar,
                    declared_type=lvl.type, atr=atr,
                )
                for ordinal, attack in enumerate(approaches, start=1):
                    key = min(ordinal, MAX_ORDINAL)
                    counts[key]["n"] += 1
                    if attack.penetrated:
                        counts[key]["penetrated"] += 1

    return dict(counts), label, levels_seen


def report(counts: Dict[int, Dict[str, int]], label: str, levels: int) -> List[str]:
    import math

    lines = [
        f"H-S3 — third-attack study   source={label}   levels={levels:,}",
        "",
        f"{'approach':<16}{'n':>8}{'penetrated':>13}{'rate':>9}{'vs 50%':>12}",
    ]
    for ordinal in sorted(counts):
        c = counts[ordinal]
        n, pen = c["n"], c["penetrated"]
        if not n:
            continue
        rate = pen / n
        se = math.sqrt(0.25 / n)
        z = (rate - 0.5) / se
        name = f"{ordinal}th or later" if ordinal >= MAX_ORDINAL else {
            1: "1st", 2: "2nd", 3: "3rd",
        }[ordinal]
        verdict = "odds-on" if rate > 0.5 and abs(z) > 1.96 else (
            "ns" if abs(z) <= 1.96 else "against"
        )
        lines.append(
            f"{name:<16}{n:>8,}{pen:>13,}{rate:>8.1%}{z:>+9.2f}  {verdict}"
        )
    return lines


if __name__ == "__main__":
    counts, label, levels = run_attack_study()
    print("\n".join(report(counts, label, levels)))
