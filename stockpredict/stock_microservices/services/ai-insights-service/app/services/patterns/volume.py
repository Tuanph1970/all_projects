"""EM-1 / V1 — volume primitives for the chart-pattern detectors.

Satisfies `FR-EM-V1` (relative volume) and `FR-EM-V2` (volume trend) of
`docs/SRS_edwards_magee_volume.md`. This module holds **primitives only** —
no pattern rules. The per-detector conditions (`FR-EM-V5`) and the scoring
composition (`FR-EM-V7`) arrive in tasks V4–V6 and build on what is here.

Why these particular primitives
-------------------------------
Edwards & Magee are explicit that volume is judged **relative**: *"high" means
high for that stock in that period*, never an absolute share count (Ch 6). So
there is no such thing as a cross-symbol volume threshold in this system, and
every reading below is a ratio against that symbol's own recent history.

Two design choices are load-bearing and are tested as such:

1. **The baseline is a median, not a mean.** E&M care about climax days
   precisely because they are extreme (Ch 10 selling climax, Ch 28 *"prepare to
   retire into your shell"*). A mean baseline would absorb one such day and
   mask the next; the median does not move.

2. **Everything is causal (C1).** The baseline at bar ``i`` reads only bars
   strictly before ``i``. There is no whole-frame normalisation anywhere in
   this file — no ``volume / volume.mean()``, no global z-score. `H4` in
   ``tests/test_volume_rules.py`` appends future bars and asserts that no past
   reading moves, so a later refactor to a vectorised whole-column form fails
   loudly rather than quietly leaking.

Unavailability is a first-class outcome, not an error: the upstream column is
``nullable`` (`stock-data-service/app/models/domain.py:103`), and E&M's own
Dormant Bottom (Ch 7) — *"weeks of no sales, a fly-specked chart"* — is a real
shape among thin VN tickers. Unknown therefore reads as **neutral** (factor
exactly ``1.0``), never as adverse evidence (`EC-V1`, `EC-V2`, `EC-V8`).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

# --- Defaults ---------------------------------------------------------------
# Every number here is a *default pending the S2 sweep* (FR-EM-V11), never a
# trusted constant and never a test assertion. E&M's own figures come from
# 1940s-60s NYSE issues.

DEFAULT_BASELINE_WINDOW = 50   # trailing bars behind the bar being judged
MIN_BASELINE_BARS = 10         # below this there is no usable baseline (EC-V4)
MAX_WIDEN_FACTOR = 4           # how far back EC-V2 may widen past a dead window
MIN_TREND_BARS = 4             # below this a direction verdict is meaningless

# Factor bounds (FR-EM-V7). Deliberately asymmetric: E&M's volume evidence is
# better at discrediting a formation than at promoting one, so the floor sits
# further from neutral than the ceiling. V4 composes with these.
NEUTRAL_FACTOR = 1.0
FACTOR_FLOOR = 0.5
FACTOR_CEILING = 1.15


# --- Result types -----------------------------------------------------------

@dataclass(frozen=True)
class RelativeVolume:
    """One bar's volume measured against its own trailing history.

    ``value`` is ``None`` whenever no causal baseline could be formed; in that
    case ``reason`` says why, and callers must fall back to neutral rather than
    treating the absence as low volume.
    """
    value: Optional[float]
    baseline: Optional[float] = None
    bars_used: int = 0
    reason: str = ""

    @property
    def known(self) -> bool:
        return self.value is not None


@dataclass(frozen=True)
class VolumeTrendResult:
    """Direction of volume across a span, in ``[-1, +1]``.

    Negative = drying up (the flag/pennant/triangle condition, Ch 8 and 11);
    positive = expanding (the inverse-H&S condition, Ch 7).
    """
    value: Optional[float]
    bars_used: int = 0
    reason: str = ""

    @property
    def known(self) -> bool:
        return self.value is not None


@dataclass(frozen=True)
class VolumeVerdict:
    """The shape V4 will return per detector: a score, the multiplier it
    implies, and the evidence behind it.

    ``score`` is ``None`` for unknown — never ``0.0``, which would be
    indistinguishable from "volume actively contradicts" (`FR-EM-V7`).
    ``evidence`` is ordered and human-readable because E&M's rules *are* the
    product feature here; a bare number would hide them from the user.
    """
    score: Optional[float]
    factor: float
    evidence: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def neutral(cls, reason: str = "no_volume_data", *, thin_volume: bool = False) -> "VolumeVerdict":
        """The sentinel for every unavailability path (`H5`).

        Key ordering is fixed so `H6` determinism holds on the evidence dict.
        """
        evidence: Dict[str, Any] = {"status": "unknown", "reason": reason}
        if thin_volume:
            evidence["thin_volume"] = True
        return cls(score=None, factor=NEUTRAL_FACTOR, evidence=evidence)


# --- Internals --------------------------------------------------------------

def _usable(value: Any) -> Optional[float]:
    """Coerce one raw volume cell to a usable float, or ``None``.

    ``None`` and ``NaN`` are *missing* and get skipped. Zero is **data** — a
    halt or a genuinely dormant session — and is kept, because dropping it
    would silently turn a dormant stretch into a normal one. What zero cannot
    do is serve as a denominator, which is what `EC-V2`'s widening handles.
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


def _average_ranks(values: Sequence[float]) -> List[float]:
    """Ranks with ties averaged — the standard correction, so a long flat
    stretch does not fabricate a direction."""
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        shared = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            ranks[order[k]] = shared
        i = j + 1
    return ranks


def _spearman(xs: Sequence[float], ys: Sequence[float]) -> Optional[float]:
    """Rank correlation, computed without scipy.

    Rank-based by requirement (`FR-EM-V2`, `EC-V5`): one absurd vendor print
    can move a rank by at most the number of positions it jumps, whereas an OLS
    slope on raw volume would be dragged bodily towards it.
    """
    rx = _average_ranks(xs)
    ry = _average_ranks(ys)
    n = len(rx)
    mx = sum(rx) / n
    my = sum(ry) / n
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den_x = math.sqrt(sum((a - mx) ** 2 for a in rx))
    den_y = math.sqrt(sum((b - my) ** 2 for b in ry))
    if den_x == 0.0 or den_y == 0.0:
        # No variation on one side — a perfectly flat span carries no
        # direction. 0.0 is the honest answer, not None: we *know* it is flat.
        return 0.0
    return num / (den_x * den_y)


def _baseline_from(
    volume: Sequence[Any],
    index: int,
    window: int,
    *,
    nonzero_only: bool = False,
) -> tuple[Optional[float], int]:
    """Median of the usable bars in ``[index-window, index)`` — strictly
    before ``index``, which is the whole of C1 in this module.

    ``nonzero_only`` is used **only** by `EC-V2`'s widening path. Dropping
    zeros in the normal path would turn a dormant stretch into a normal one,
    which is exactly what ``_usable`` keeps zeros in order to prevent; but when
    the window is already known to be dead, the question has changed to "what
    was the level the last time this thing traded", and a median that still
    counts the dead bars answers a different question — one whose answer moves
    with the length of the dormancy rather than with the market.
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


# --- Public API -------------------------------------------------------------

def relative_volume(
    volume: Sequence[Any],
    index: int,
    baseline_window: int = DEFAULT_BASELINE_WINDOW,
    min_bars: int = MIN_BASELINE_BARS,
) -> RelativeVolume:
    """`FR-EM-V1` — volume at ``index`` as a ratio of its trailing median.

    Returns an unknown ``RelativeVolume`` rather than raising, for every
    unavailability path: out-of-range index, missing cell, too few prior bars,
    or a baseline that cannot serve as a denominator.
    """
    if index < 0 or index >= len(volume):
        return RelativeVolume(None, reason="index_out_of_range")

    here = _usable(volume[index])
    if here is None:
        return RelativeVolume(None, reason="missing_volume")

    baseline, bars_used = _baseline_from(volume, index, baseline_window)
    if baseline is None:
        return RelativeVolume(None, bars_used=bars_used, reason="insufficient_history")

    # EC-V2: zero is data, but it cannot be a denominator. Fall back to the
    # level that prevailed the last time the symbol actually traded — E&M's
    # Dormant Bottom (Ch 7), where "weeks of no sales" end in "a sudden
    # inexplicable flurry" and the flurry is the signal.
    #
    # The widened baseline counts only trading bars, so the reading does not
    # drift with the *length* of the dormancy. Blending dead bars into the
    # median makes rvol a function of how many zeros happened to fall inside
    # the widened window, which is arithmetic, not evidence.
    if baseline == 0.0:
        baseline, bars_used = _baseline_from(
            volume,
            index,
            baseline_window * MAX_WIDEN_FACTOR,
            nonzero_only=True,
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


def span_relative_volume(
    volume: Sequence[Any],
    start: int,
    end: int,
    baseline_window: int = DEFAULT_BASELINE_WINDOW,
) -> RelativeVolume:
    """Typical relative volume across ``[start, end)``.

    Each bar is measured against **its own** trailing baseline, so the result
    stays causal for any span ending at or before the bar under judgement
    (`H4`). The aggregate is a median again, for the same reason as the
    baseline itself.

    V5/V6 need this constantly — "volume on the left shoulder", "volume through
    the flag" — so it lives here rather than being reinvented per detector.
    """
    if start < 0 or end > len(volume) or end <= start:
        return RelativeVolume(None, reason="empty_span")

    readings = [
        rv.value
        for rv in (relative_volume(volume, i, baseline_window) for i in range(start, end))
        if rv.value is not None
    ]
    if not readings:
        return RelativeVolume(None, reason="no_usable_bars")

    return RelativeVolume(value=_median(readings), bars_used=len(readings), reason="")


def volume_trend(
    volume: Sequence[Any],
    start: int,
    end: int,
    min_bars: int = MIN_TREND_BARS,
) -> VolumeTrendResult:
    """`FR-EM-V2` — direction of volume across ``[start, end)``, in ``[-1, +1]``.

    Negative means drying up, which is the condition on flags, pennants and
    triangles (*"volume diminishes irregularly but noticeably toward the
    apex"*, Ch 8). Positive means building, which is the condition on the
    inverse head-and-shoulders (Ch 7).

    Rank-based, so one bad print cannot flip the verdict (`EC-V5`).
    """
    if start < 0 or end > len(volume) or end <= start:
        return VolumeTrendResult(None, reason="empty_span")

    pairs = [
        (float(i), v)
        for i, v in ((i, _usable(volume[i])) for i in range(start, end))
        if v is not None
    ]
    if len(pairs) < min_bars:
        return VolumeTrendResult(None, bars_used=len(pairs), reason="span_too_short")

    xs = [p[0] for p in pairs]
    ys = [p[1] for p in pairs]
    rho = _spearman(xs, ys)
    if rho is None:
        return VolumeTrendResult(None, bars_used=len(pairs), reason="no_variation")

    return VolumeTrendResult(
        value=max(-1.0, min(1.0, rho)), bars_used=len(pairs), reason=""
    )
