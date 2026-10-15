"""EM-2 / S1 — volume primitives for support & resistance levels.

Satisfies `FR-EM-S1` (groundwork) and `FR-EM-S2`'s span question from
`docs/SRS_edwards_magee_sr_levels.md`. **Primitives only** — nothing in
`_find_sr_levels` reads these yet; that is task `S4`.

Why this exists
---------------
`analysis_service.py` `_find_sr_levels` scores a level by `len(cluster)` — a
touch count. Edwards & Magee spend Ch 13 arguing that is the wrong measure: a
level's power comes from **the volume that changed hands there**, the supply
trapped above a buyer's cost, not from how often price has since visited. On
that account a level touched twice on heavy trade outranks one touched five
times on thin trade.

Deliberately mirroring EM-1
---------------------------
`ai-insights/app/services/patterns/volume.py` already solved the
relative-volume problem: a causal trailing **median** baseline,
`MIN_BASELINE_BARS` below which there is no usable baseline, and a `_usable`
coercion that treats NULL as missing while keeping zero as data. It lives in a
different service and cannot be imported, so this module mirrors its shape,
edge-case handling and naming **on purpose** rather than inventing a second
vocabulary for one idea (`S1`'s "reuse, do not reinvent" requirement).

The deliberate divergences, so a reader is not left guessing:

* EM-1 measures **one bar** against its history; a level is a **span** of bars,
  so `relative_level_volume` compares the span's mean bar volume to the median
  bar volume before it.
* EM-1's `EC-V2` widens a dead baseline window to find the last real trade. A
  level is not a moment, so the equivalent here is simply to report
  `thin_volume` and let the caller fall back to the touch count (`EC-S1`).

Causality (C1) is binding
-------------------------
A level is scored **as of its own formation**: a span never extends past the
level's last pivot, and the baseline reads only bars strictly before the span.
Reading later bars would score a level with hindsight it did not have.
`H-S4` in `tests/test_sr_volume.py` appends future bars and asserts no past
reading moves, so a later refactor to a whole-column vectorised form fails
loudly instead of leaking quietly.

What this module does NOT claim
------------------------------
It is **not** volume-at-price. `volume_weighted_price` is a volume-weighted
*close*, because daily bars carry no intraday distribution. `NFR-S2` forbids
calling it volume-at-price in code, docs or UI; E&M assumed a distribution the
data cannot supply, and this is the closest honest substitute.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional, Sequence, Tuple

# --- Defaults ---------------------------------------------------------------
# Mirrored from EM-1, which settled them by a measured sweep
# (docs/em1_s2_parameter_sweep.md). `FR-EM-S10` still requires them re-swept in
# this context at task `W1` — inherited-and-documented is not the same as
# measured-here — but diverging from them without evidence would be worse.

DEFAULT_BASELINE_WINDOW = 100   # trailing bars before the span, for the baseline
MIN_BASELINE_BARS = 10          # below this there is no usable baseline
MIN_CONGESTION_BARS = 3         # below this a span has nothing to average (EC-S3)

#: Above this, a span is not a congestion and the function refuses to answer.
#:
#: MEASURED at S1 against real levels, and it settles SRS open question 2 in a
#: way neither candidate definition anticipated. `_find_sr_levels` clusters
#: every visit to a price across the whole window, so a cluster's touches are
#: scattered: FPT's strongest level spanned bars 114-220, TCB's 21-243 — 226 of
#: 250 bars. Feeding that to either span mode produces "the congestion is most
#: of the year", and the resulting strength is uninformative: across those
#: levels the relative-volume readings spanned just 0.61x-1.18x.
#:
#: Measured per TOUCH instead — one localised span per visit — the same levels
#: produced 0.48x-2.44x, a spread 3.4 times wider. So a congestion is local to
#: a visit, and a level's strength is an aggregate over its visits. `S4` must
#: therefore call this per touch, and this guard makes a cluster-wide call fail
#: loudly rather than return a number that means nothing.
#:
#: 30 bars is ~6 weeks, which is a congestion area in E&M's sense (Ch 13) and
#: not a year. `FR-EM-S10` sweeps it at `W1`.
MAX_CONGESTION_BARS = 30
DEFAULT_NEIGHBOURHOOD = 3       # pivot +/- this, in NEIGHBOURHOOD mode
DEFAULT_TOLERANCE_PCT = 2.0     # matches _find_sr_levels' own cluster tolerance

#: A span whose bars are this fraction zero-volume or fewer is still usable;
#: above it the level is reported thin (`EC-S2`).
MAX_DORMANT_FRACTION = 0.5


class SpanMode(str, Enum):
    """The two candidate congestion definitions of SRS open question 2.

    Both are implemented so `H-S1` can choose between them with evidence at
    `S4`, rather than the choice being guessed now.

    ``NEIGHBOURHOOD`` — the pivot bars plus a fixed window. Cheap, and
    independent of how price behaved around them.

    ``CONTIGUOUS`` — the unbroken run during which price stayed within the
    cluster tolerance of the level. Closest to what E&M mean by a "congestion
    area", and costs a scan.
    """
    NEIGHBOURHOOD = "neighbourhood"
    CONTIGUOUS = "contiguous"


@dataclass(frozen=True)
class LevelVolume:
    """A level's volume, measured against the symbol's own recent history.

    ``value`` is ``None`` whenever no causal baseline could be formed; in that
    case ``reason`` says why and the caller must fall back to the touch count
    rather than reading the absence as "no interest here" (`EC-S1`).
    """
    value: Optional[float]
    total_volume: Optional[float] = None
    baseline: Optional[float] = None
    bars_used: int = 0
    reason: str = ""
    thin_volume: bool = False

    @property
    def known(self) -> bool:
        return self.value is not None


# --- Internals (mirroring EM-1's helpers by name) ---------------------------

def _usable(value: Any) -> Optional[float]:
    """Coerce one raw volume cell to a usable float, or ``None``.

    ``None`` and ``NaN`` are *missing* and get skipped. Zero is **data** — a
    halt, or a genuinely dormant session — and is kept, because dropping it
    would silently turn a dormant congestion into a normal one. Identical
    reasoning to EM-1's `_usable`.
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
    if not n:
        return 0.0
    mid = n // 2
    if n % 2:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2.0


def _column(ohlc: Any, name: str) -> Optional[list]:
    try:
        if name not in ohlc:
            return None
        return list(ohlc[name])
    except (KeyError, TypeError, AttributeError):
        return None


# --- FR-EM-S2: the congestion span ------------------------------------------

def congestion_span(
    ohlc: Any,
    pivot_bars: Sequence[int],
    mode: SpanMode = SpanMode.NEIGHBOURHOOD,
    window: int = DEFAULT_NEIGHBOURHOOD,
    level_price: Optional[float] = None,
    tolerance_pct: float = DEFAULT_TOLERANCE_PCT,
) -> Optional[Tuple[int, int]]:
    """The bar range ``(start, end)`` that constitutes a level's congestion.

    Inclusive of both ends. ``None`` when there is nothing usable — no pivots,
    an empty frame, a span below `MIN_CONGESTION_BARS` (`EC-S3`), or a span
    **above** `MAX_CONGESTION_BARS`, which means the caller has handed over a
    scattered cluster rather than a congestion. See that constant: this is the
    measured answer to SRS open question 2, and the refusal is deliberate —
    call this once per touch, not once per cluster.

    **The span never extends past the last pivot**, in either mode. That is the
    whole of C1 in this function: a level's volume is what traded while it was
    forming, not what has traded since.
    """
    closes = _column(ohlc, "close")
    if not closes or not pivot_bars:
        return None

    n = len(closes)
    pivots = sorted(int(p) for p in pivot_bars if 0 <= int(p) < n)
    if not pivots:
        return None

    first, last = pivots[0], pivots[-1]

    # Two different things can make a span too wide, and they need opposite
    # answers.
    #
    # A scattered PIVOT SPREAD means the caller handed over a whole cluster
    # rather than one congestion — refuse, per MAX_CONGESTION_BARS.
    if (last - first + 1) > MAX_CONGESTION_BARS:
        return None
    #
    # A long contiguous RUN is different: a wide sideways area is a STRONG
    # level in E&M's terms (Ch 13), so refusing to measure it would throw away
    # the information. The walk below is bounded instead, keeping the bars
    # nearest the pivots.

    if mode is SpanMode.CONTIGUOUS:
        anchor = level_price if level_price is not None else closes[last]
        if anchor and anchor > 0:
            tol = abs(anchor) * tolerance_pct / 100.0
            end = last          # never past the last pivot: that is C1 here
            floor = max(0, end - MAX_CONGESTION_BARS + 1)
            start = first
            while start - 1 >= floor and abs(closes[start - 1] - anchor) <= tol:
                start -= 1
        else:
            start, end = first, last
    else:
        start = max(0, first - window)
        end = min(last, n - 1)

    start = max(0, min(start, n - 1))
    end = max(0, min(end, n - 1, last))
    if end < start:
        return None
    length = end - start + 1
    if length < MIN_CONGESTION_BARS or length > MAX_CONGESTION_BARS:
        return None
    return start, end


# --- FR-EM-S2: the centre of gravity ----------------------------------------

def volume_weighted_price(ohlc: Any, start: int, end: int) -> Optional[float]:
    """`FR-EM-S2` — the volume-weighted mean CLOSE over ``[start, end]``.

    E&M call the precise level the "centre of gravity" of the old congestion.
    With daily bars this is the closest honest substitute, and `NFR-S2` forbids
    describing it as volume-at-price.

    ``None`` when the span is empty or carries no usable volume: a dormant span
    has no centre of gravity, and returning ``0.0`` would place the level at
    zero, which is worse than admitting ignorance (`EC-S1`).
    """
    closes = _column(ohlc, "close")
    volumes = _column(ohlc, "volume")
    if not closes or not volumes:
        return None
    n = min(len(closes), len(volumes))
    if start < 0 or end >= n or end < start:
        return None

    weighted = 0.0
    total = 0.0
    for i in range(start, end + 1):
        vol = _usable(volumes[i])
        price = _usable(closes[i])
        if vol is None or price is None:
            continue          # NULL is missing: it leaves BOTH sums (EC-S1)
        weighted += price * vol
        total += vol
    if total <= 0.0:
        return None
    return weighted / total


# --- FR-EM-S1: strength as volume -------------------------------------------

def relative_level_volume(
    ohlc: Any,
    start: int,
    end: int,
    baseline_window: int = DEFAULT_BASELINE_WINDOW,
    min_bars: int = MIN_BASELINE_BARS,
) -> LevelVolume:
    """`FR-EM-S1` — the congestion's volume relative to the symbol's own history.

    The span's **mean** bar volume divided by the **median** bar volume over the
    `baseline_window` bars strictly before it. Never an absolute share count:
    E&M are explicit that "high" means high for that stock in that period
    (Ch 6), so there is no such thing as a cross-symbol volume threshold here.

    The baseline is a median for the same reason as EM-1's: one absurd vendor
    print, or one genuine climax day, would inflate a mean and make every later
    level look quiet by comparison.

    Returns an unknown `LevelVolume` rather than raising, on every
    unavailability path, so the caller can fall back to the touch count and say
    why (`EC-S1`, `EC-S2`, `EC-S3`).
    """
    volumes = _column(ohlc, "volume")
    if not volumes:
        return LevelVolume(None, reason="volume_unavailable")
    n = len(volumes)
    if start < 0 or end >= n or end < start:
        return LevelVolume(None, reason="empty_span")

    span_raw = [_usable(volumes[i]) for i in range(start, end + 1)]
    span = [v for v in span_raw if v is not None]
    if not span:
        return LevelVolume(None, reason="volume_unavailable")

    # EC-S2: zero is data, but a span that is mostly dormant cannot carry a
    # strength claim. Flag it rather than scoring it, so the UI can say why.
    dormant = sum(1 for v in span if v == 0.0) / len(span)
    thin = dormant > MAX_DORMANT_FRACTION

    base_start = max(0, start - baseline_window)
    prior = [v for v in (_usable(volumes[i]) for i in range(base_start, start))
             if v is not None]
    if len(prior) < min_bars:
        return LevelVolume(
            None, bars_used=len(prior), reason="insufficient_history",
            thin_volume=thin,
        )

    baseline = _median(prior)
    total = sum(span)
    if baseline <= 0.0:
        # The whole baseline window was dormant. Unlike EM-1's EC-V2 there is
        # nothing to widen towards that would mean anything for a level, so
        # this reports thin and defers to the touch count.
        return LevelVolume(
            None, total_volume=total, baseline=baseline,
            bars_used=len(prior), reason="dormant_baseline", thin_volume=True,
        )

    mean_span = total / len(span)
    return LevelVolume(
        value=mean_span / baseline,
        total_volume=total,
        baseline=baseline,
        bars_used=len(prior),
        reason="",
        thin_volume=thin,
    )
