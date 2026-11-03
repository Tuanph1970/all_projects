"""Relative volume — a bar's volume against its own trailing median.

Backlog #117. stock-data-service needs this to publish an unusual-volume
reading with each price event: it is the only service that holds the price
history, and the alert consumer in portfolio-service sees one event at a time
with no trailing window of its own.

WHY A SECOND HOME FOR AN EXISTING ALGORITHM, stated plainly because duplicated
logic is usually the wrong answer. The original lives in ai-insights-service's
`patterns/volume.py` (FR-EM-V1), a 1,680-line EM-1 module with heavy validated
test coverage, where this primitive's constants, dataclass and three helpers are
woven through the file. Extracting it would put EM-1's measured work at risk to
start a feature that does not need that risk. So the algorithm is reproduced
here EXACTLY, and `ai-insights-service/tests/test_shared_volume_agreement.py`
asserts the two agree on randomised inputs — divergence becomes a test failure
rather than a silent disagreement, which is the same device that now ties the
secrets guard to docker-compose and the event pattern to its publisher.

THE THREE DECISIONS INHERITED FROM EM-1, all load-bearing:

1. **The baseline is a MEDIAN, not a mean.** E&M care about climax days
   precisely because they are extreme (Ch 10, Ch 28). A mean baseline absorbs
   one such day and masks the next; a median does not move.
2. **Per-symbol only.** E&M are explicit that "high" means high *for that
   stock in that period*, never an absolute share count — so there is no
   cross-symbol volume threshold anywhere in this system.
3. **Zero is data, but cannot be a denominator.** A halt or a dormant session
   is kept in the baseline, because dropping zeros would turn a dormant stretch
   into a normal one. When the whole window is dead the question changes to
   "what was the level the last time this traded", so the window widens and
   counts only trading bars — otherwise the reading drifts with the *length* of
   the dormancy, which is arithmetic rather than evidence (E&M's Dormant
   Bottom, Ch 7: "weeks of no sales" ending in "a sudden inexplicable flurry").

Unavailability is always an explicit unknown with a reason, never a zero or a
one. A caller must fall back to neutral rather than read an absent baseline as
low volume.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Optional, Sequence

#: Trailing bars behind the bar being judged.
DEFAULT_BASELINE_WINDOW = 100
#: Below this many usable prior bars there is no baseline at all (EM-1 EC-V4).
MIN_BASELINE_BARS = 10
#: How far back the zero-baseline path may widen past a dead window (EC-V2).
MAX_WIDEN_FACTOR = 4


@dataclass(frozen=True)
class RelativeVolume:
    """One bar's volume measured against its own trailing history.

    `value` is None whenever no causal baseline could be formed; `reason` then
    says why, and callers must fall back to neutral.
    """

    value: Optional[float]
    baseline: Optional[float] = None
    bars_used: int = 0
    reason: str = ""

    @property
    def known(self) -> bool:
        return self.value is not None


def _usable(value: Any) -> Optional[float]:
    """Coerce one raw volume cell to a usable float, or None.

    None and NaN are *missing* and are skipped. Zero is kept: it is data.
    """
    if value is None:
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(out) or math.isinf(out) or out < 0:
        return None
    return out


def _median(values: Sequence[float]) -> float:
    ordered = sorted(values)
    n = len(ordered)
    mid = n // 2
    if n % 2:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2.0


def _baseline_from(
    volume: Sequence[Any],
    index: int,
    window: int,
    *,
    nonzero_only: bool = False,
) -> tuple[Optional[float], int]:
    """Median of the usable bars in `[index-window, index)`.

    Strictly BEFORE `index` — that is the whole of causality here. A reading
    for bar i must not see bar i's own neighbours from the future.
    """
    if index <= 0:
        return None, 0
    start = max(0, index - window)
    usable = [v for v in (_usable(x) for x in volume[start:index]) if v is not None]
    if nonzero_only:
        usable = [v for v in usable if v > 0.0]
    if len(usable) < MIN_BASELINE_BARS:
        return None, len(usable)
    return _median(usable), len(usable)


def relative_volume(
    volume: Sequence[Any],
    index: int,
    baseline_window: int = DEFAULT_BASELINE_WINDOW,
    min_bars: int = MIN_BASELINE_BARS,
) -> RelativeVolume:
    """Volume at `index` as a ratio of its trailing median.

    Never raises. Every unavailability path returns an unknown with a reason:
    out-of-range index, missing cell, too little history, or a dormant window
    that cannot produce a denominator.
    """
    if index < 0 or index >= len(volume):
        return RelativeVolume(None, reason="index_out_of_range")

    here = _usable(volume[index])
    if here is None:
        return RelativeVolume(None, reason="missing_volume")

    baseline, bars_used = _baseline_from(volume, index, baseline_window)
    if baseline is None:
        return RelativeVolume(None, bars_used=bars_used, reason="insufficient_history")

    if baseline == 0.0:
        baseline, bars_used = _baseline_from(
            volume, index, baseline_window * MAX_WIDEN_FACTOR, nonzero_only=True
        )
        if baseline is None or baseline == 0.0:
            return RelativeVolume(
                None, baseline=0.0, bars_used=bars_used, reason="dormant_no_baseline"
            )

    if bars_used < min_bars:
        return RelativeVolume(None, bars_used=bars_used, reason="insufficient_history")

    return RelativeVolume(
        value=here / baseline, baseline=baseline, bars_used=bars_used, reason=""
    )
