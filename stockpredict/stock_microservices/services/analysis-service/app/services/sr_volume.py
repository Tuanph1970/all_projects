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

# A per-touch NEIGHBOURHOOD span runs from `pivot - window` to the pivot
# itself, so it is `window + 1` bars long. If that falls below
# MIN_CONGESTION_BARS, `congestion_span` refuses every touch and the whole
# volume path goes quietly dark: volume_strength, price_cog and
# adjusted_strength all come back None for every level, with no error raised
# anywhere and the EM-2 arms simply absent from any study.
#
# Found at `W1` with DEFAULT_NEIGHBOURHOOD=1, where the sweep's small-sample
# flag was the only thing that noticed (docs/em2_s_sweep.md). Guarded at
# import so a future edit to either constant fails loudly instead.
assert DEFAULT_NEIGHBOURHOOD + 1 >= MIN_CONGESTION_BARS, (
    f"DEFAULT_NEIGHBOURHOOD={DEFAULT_NEIGHBOURHOOD} yields a "
    f"{DEFAULT_NEIGHBOURHOOD + 1}-bar per-touch span, below "
    f"MIN_CONGESTION_BARS={MIN_CONGESTION_BARS}. Every congestion_span() call "
    f"would return None and the entire volume path would silently disable."
)

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


# ===========================================================================
# S4 — per-touch aggregation
#
# `S1` measured that a congestion is local to a VISIT: `_find_sr_levels`
# clusters every visit to a price across the whole window, so a cluster-wide
# span is most of the frame and its relative volume collapses towards 1.0
# (0.61x-1.18x across real levels, against 0.48x-2.44x measured per touch).
# `MAX_CONGESTION_BARS` makes the cluster-wide call fail loudly; the functions
# below are the right shape — one span per touch, then an aggregate.
# ===========================================================================


class Aggregation(str, Enum):
    """How a level's per-visit volume readings combine into one strength.

    ``SUM`` — add the per-visit relative readings. The closer reading of E&M
    Ch 13's "volume transacted there": a level revisited three times on heavy
    trade has absorbed more supply than one visited once. It therefore grows
    with the number of visits, which means it is **partly** a touch count
    again — the thing `FR-EM-S1` set out to replace.

    ``MAX`` — take the heaviest single visit. Insensitive to how often the
    level was revisited, so it is a purer volume statement, but it discards
    the accumulation that E&M's argument rests on.

    Neither is obviously right, so both ship and `H-S1` chooses on evidence
    rather than on preference (the open question `S4` inherits from `S1`).
    """
    SUM = "sum"
    MAX = "max"


DEFAULT_AGGREGATION = Aggregation.SUM


def touch_spans(
    ohlc: Any,
    touch_bars: Sequence[int],
    mode: SpanMode = SpanMode.NEIGHBOURHOOD,
    window: int = DEFAULT_NEIGHBOURHOOD,
    level_price: Optional[float] = None,
    tolerance_pct: float = DEFAULT_TOLERANCE_PCT,
) -> list:
    """One congestion span per touch, with overlaps merged.

    Merging matters: two touches three bars apart would otherwise contribute
    the same bars twice, inflating both the summed volume and the centre of
    gravity. The merge makes the result a function of the bars actually
    involved rather than of how the pivot detector happened to split them.
    """
    spans = []
    for bar in sorted(set(int(b) for b in touch_bars)):
        span = congestion_span(
            ohlc, [bar], mode=mode, window=window,
            level_price=level_price, tolerance_pct=tolerance_pct,
        )
        if span is not None:
            spans.append(span)
    if not spans:
        return []

    merged = [spans[0]]
    for start, end in spans[1:]:
        last_start, last_end = merged[-1]
        if start <= last_end + 1:
            merged[-1] = (last_start, max(last_end, end))
        else:
            merged.append((start, end))
    return merged


def aggregate_level_volume(
    ohlc: Any,
    touch_bars: Sequence[int],
    aggregation: Aggregation = DEFAULT_AGGREGATION,
    mode: SpanMode = SpanMode.NEIGHBOURHOOD,
    window: int = DEFAULT_NEIGHBOURHOOD,
    level_price: Optional[float] = None,
    baseline_window: int = DEFAULT_BASELINE_WINDOW,
) -> LevelVolume:
    """`FR-EM-S1` — a level's strength as the volume transacted at it.

    Calls `relative_level_volume` once per merged touch span and combines the
    readings by ``aggregation`` (see `Aggregation`: SUM adds the visits, MAX
    takes the heaviest). Always **relative** to the symbol's own trailing
    volume, never an absolute share count.

    Returns an unknown `LevelVolume` — not a zero — when no span could be
    measured, so the caller falls back to the touch count rather than reading
    the absence as "no interest at this level" (`EC-S1`, `EC-S2`).
    """
    spans = touch_spans(
        ohlc, touch_bars, mode=mode, window=window, level_price=level_price,
    )
    if not spans:
        return LevelVolume(None, reason="no_usable_span")

    readings = []
    totals = 0.0
    bars_used = 0
    thin_any = False
    for start, end in spans:
        lv = relative_level_volume(ohlc, start, end, baseline_window=baseline_window)
        thin_any = thin_any or lv.thin_volume
        if lv.known:
            readings.append(lv.value)
            totals += lv.total_volume or 0.0
            bars_used += lv.bars_used

    if not readings:
        return LevelVolume(
            None, reason="no_usable_reading", thin_volume=thin_any,
        )

    value = sum(readings) if aggregation is Aggregation.SUM else max(readings)
    return LevelVolume(
        value=value,
        total_volume=totals,
        bars_used=bars_used,
        reason="",
        thin_volume=thin_any,
    )


def level_price_cog(
    ohlc: Any,
    touch_bars: Sequence[int],
    mode: SpanMode = SpanMode.NEIGHBOURHOOD,
    window: int = DEFAULT_NEIGHBOURHOOD,
    level_price: Optional[float] = None,
) -> Optional[float]:
    """`FR-EM-S2` — the level's centre of gravity across all its visits.

    The volume-weighted mean CLOSE over the merged touch spans. Spans are
    weighted by the volume they actually carry, so a single heavy visit pulls
    the level towards itself — which is the behaviour E&M describe when they
    say to average the old congestion's closes.

    **An approximation, by requirement** (`NFR-S2`): daily bars carry no
    intraday distribution, so this is a volume-weighted close and must never be
    described as volume at price.

    ``None`` when no span carries usable volume — a dormant level has no centre
    of gravity, and returning 0.0 would place it at zero.
    """
    spans = touch_spans(
        ohlc, touch_bars, mode=mode, window=window, level_price=level_price,
    )
    if not spans:
        return None

    closes = _column(ohlc, "close")
    volumes = _column(ohlc, "volume")
    if not closes or not volumes:
        return None

    weighted = 0.0
    weight = 0.0
    for start, end in spans:
        for i in range(start, end + 1):
            if i < 0 or i >= len(closes):
                continue
            v = _usable(volumes[i])
            c = _usable(closes[i])
            if v is None or c is None or v <= 0:
                continue
            weighted += c * v
            weight += v

    if weight <= 0:
        return None
    return weighted / weight


# ===========================================================================
# S5 — role reversal and break history (`FR-EM-S3`, `EC-S4`)
#
# E&M Ch 13, the half they say casual chart readers never grasp: "a former
# Top, once surpassed, becomes a Bottom zone; an old Bottom, once penetrated,
# becomes a Top zone." A penetrated level is not spent — it changes sides.
# ===========================================================================

#: How far beyond a level a close must sit to count as a decisive penetration,
#: in multiples of the symbol's own trailing ATR.
#:
#: ATR multiples rather than a percentage, by requirement. `FR-EM-S3` forbids
#: inventing a number and points at EM-9, which measured that one percentage
#: is structurally wrong across kinds: median penetration ran from 0.56%
#: (SR_BOUNCE) to 4.47% (SR_BREAKOUT), an eightfold spread, so the book's 3%
#: is "nearly inert for one and nearly total for the other"
#: (docs/em9_penetration_filter_sweep.md). The same objection applies across
#: symbols: 2% through a level is decisive on a quiet large cap and is daily
#: noise on a volatile small cap. `FR-EM-S10` sweeps this at `W1`.
BREAK_ATR_MULTIPLE = 0.5

#: Wilder's period, matching `analysis_service._calculate_atr` so the two
#: never disagree about what a symbol's volatility is.
ATR_PERIOD = 14


def trailing_atr(ohlc: Any, period: int = ATR_PERIOD):
    """Wilder's ATR, aligned to the frame.

    Deliberately the same formulation as `AnalysisService._calculate_atr` —
    EM-1's `S1` note applies here too: do not invent a second vocabulary for
    an idea the codebase already has. It is reimplemented rather than imported
    only because importing the service into this module would make a cycle.

    Causal by construction: `ewm` reads each bar and its predecessors, never
    its successors, and `min_periods` keeps the warm-up NaN rather than
    back-filling it from the future.
    """
    import pandas as pd

    if not isinstance(ohlc, pd.DataFrame) or len(ohlc) == 0:
        return pd.Series(dtype=float)
    for col in ("high", "low", "close"):
        if col not in ohlc.columns:
            return pd.Series([float("nan")] * len(ohlc))

    high = ohlc["high"].astype(float)
    low = ohlc["low"].astype(float)
    close = ohlc["close"].astype(float)
    prev_close = close.shift(1)
    tr = pd.concat(
        [(high - low), (high - prev_close).abs(), (low - prev_close).abs()],
        axis=1,
    ).max(axis=1)
    return tr.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()


def detect_breaks(
    ohlc: Any,
    level_price: float,
    first_bar: int = 0,
    declared_type: Any = None,
    atr_multiple: float = BREAK_ATR_MULTIPLE,
    period: int = ATR_PERIOD,
    atr: Any = None,
) -> list:
    """`FR-EM-S3` — every decisive penetration of ``level_price``, in order.

    A penetration is **against the level's current role**, and the role
    alternates as the level is broken. That asymmetry is the whole of E&M's
    Ch 13 mechanic and it is not optional: a *support* is penetrated when
    price closes decisively **below** it — price being above a support is
    simply where price lives, not a break. Once that support has been
    penetrated it becomes resistance, and the next thing that counts is a
    decisive close back **above**.

    Without the alternation this function reports a support as "broken
    upward" on every ordinary rally, which is both meaningless and enough to
    swamp the real breaks. A quiet-fixture test caught exactly that.

    The starting role is ``declared_type`` when given; otherwise it is
    inferred from which side of the level price sits on at ``first_bar``,
    deterministically.

    Staying beyond records **one** break, not one per bar: a level penetrated
    once and left behind has been broken once, and counting every subsequent
    bar would make the history a function of how long the frame happens to be.

    Scanning starts at ``first_bar`` — normally the level's first touch —
    because a crossing that predates the level is not a penetration of it.

    Returns an empty list rather than raising when the frame is too short to
    form an ATR. That matters: a zero or NaN ATR would otherwise make every
    crossing look infinitely decisive.

    ``atr`` lets a caller pass a precomputed series. `_find_sr_levels` does,
    because the ATR is a property of the frame and not of the level: computing
    it per level turned a 12-second test suite into a two-minute one.
    """
    import math as _math

    from app.models.schemas import SRBreak

    closes = _column(ohlc, "close")
    if not closes or level_price <= 0:
        return []

    if atr is None:
        atr = trailing_atr(ohlc, period=period)
    dates = None
    try:
        if hasattr(ohlc, "columns") and "date" in ohlc.columns:
            dates = ohlc["date"].astype(str).tolist()
    except Exception:  # noqa: BLE001 — a malformed date column must not break levels
        dates = None

    from app.models.schemas import SRLevelType

    start = max(0, int(first_bar))

    # Which way a penetration has to go to count. +1 means "a decisive close
    # ABOVE is the break" (the level is acting as resistance); -1 means a
    # decisive close BELOW is the break (acting as support).
    if declared_type == SRLevelType.SUPPORT:
        wanted = -1
    elif declared_type == SRLevelType.RESISTANCE:
        wanted = 1
    else:
        # FLIP, or unspecified: infer from the side price is on when the scan
        # begins. Above the level it is acting as support, below it as
        # resistance. Deterministic, and it matches what the chart shows.
        wanted = -1
        for i in range(start, len(closes)):
            c = _usable(closes[i])
            if c is None:
                continue
            wanted = -1 if c >= level_price else 1
            break

    # Vectorised candidate search. The role alternation below is inherently
    # sequential, but deciding *which bars are beyond the band at all* is not,
    # and doing that per bar in Python cost 30s on the H-S1 harness — over
    # pytest.ini's own 30s timeout. Only the candidate bars are then walked.
    import numpy as _np

    # Take the column straight from the frame where we can: the list
    # round-trip in `_column` is two O(n) conversions per level, and
    # `_find_sr_levels` calls this once per level.
    try:
        close_arr = ohlc["close"].to_numpy(dtype=float, copy=False)
    except (AttributeError, KeyError, TypeError, ValueError):
        close_arr = _np.asarray(
            [c if isinstance(c, (int, float)) else _np.nan for c in closes],
            dtype=float,
        )
    try:
        band_arr = _np.asarray(atr, dtype=float) * atr_multiple
    except (TypeError, ValueError):
        return []
    if band_arr.shape[0] != close_arr.shape[0]:
        return []

    valid = _np.isfinite(close_arr) & _np.isfinite(band_arr) & (band_arr > 0)
    above = valid & (close_arr >= level_price + band_arr)
    below = valid & (close_arr <= level_price - band_arr)
    candidates = _np.flatnonzero((above | below))
    candidates = candidates[candidates >= start]

    out = []
    for i in candidates:
        i = int(i)
        beyond = above[i] if wanted > 0 else below[i]
        if not beyond:
            continue
        close = float(close_arr[i])
        band = float(band_arr[i])

        out.append(SRBreak(
            direction="up" if wanted > 0 else "down",
            bar_index=i,
            date=dates[i] if dates and i < len(dates) else str(i),
            penetration_atr=round(abs(close - level_price) / (band / atr_multiple), 4),
            penetration_pct=round(abs(close - level_price) / level_price * 100.0, 4),
        ))
        # The role has now flipped, so the next thing that counts is a
        # penetration back the other way (`EC-S4`).
        wanted = -wanted

    return out


def effective_level_type(declared: Any, breaks: Sequence[Any]) -> Any:
    """`FR-EM-S3` + `EC-S4` — the type the break history implies.

    The **most recent** penetration decides: broken downward, the level now
    sits above price and acts as resistance; broken upward, it acts as
    support. With no breaks the declared pivot-composition type stands.

    `FLIP` is left alone. It is a tie in pivot composition, not a reversal,
    and the SRS is explicit that the two concepts must stay distinguishable —
    which is why this returns a *separate* answer rather than overwriting the
    declared type.
    """
    from app.models.schemas import SRLevelType

    if not breaks:
        return declared
    last = breaks[-1]
    direction = getattr(last, "direction", None)
    if direction == "down":
        return SRLevelType.RESISTANCE
    if direction == "up":
        return SRLevelType.SUPPORT
    return declared


# ===========================================================================
# S6 — attack count (`FR-EM-S4`)
#
# E&M Ch 13: each repelled attack consumes some of a level's power, and "it is
# an odds-on assumption that a third attack at a Resistance Level will succeed
# in penetrating it."
#
# This section implements the COUNT only. Whether strength should decrease
# with it is E&M's prediction, not a parameter, and `H-S3` measures it before
# any weighting is allowed to ship.
# ===========================================================================

#: How close a close must come to count as an approach, in ATR multiples.
#: Wider than `BREAK_ATR_MULTIPLE` so that "near the level" and "through the
#: level" are distinct regions. `FR-EM-S10` sweeps it at `W1`.
ATTACK_PROXIMITY_ATR = 0.75


@dataclass(frozen=True)
class LevelAttack:
    """One approach to a level, and how it ended.

    ``penetrated`` separates E&M's two outcomes: an attack proper is an
    approach that was *repelled*, while one that succeeded is a penetration
    and belongs to the break history. Keeping both on the record — rather
    than only the repulsions — is what lets `H-S3` compute a penetration rate
    by attempt ordinal.
    """
    bar_index: int
    penetrated: bool


def detect_attacks(
    ohlc: Any,
    level_price: float,
    first_bar: int = 0,
    declared_type: Any = None,
    proximity_atr: float = ATTACK_PROXIMITY_ATR,
    atr_multiple: float = BREAK_ATR_MULTIPLE,
    period: int = ATR_PERIOD,
    atr: Any = None,
) -> list:
    """`FR-EM-S4` — every approach to ``level_price``, in order, with its outcome.

    An **approach** opens when a close comes within ``proximity_atr`` x ATR of
    the level. It resolves as whichever happens first:

    * **penetration** — a close beyond the level by ``atr_multiple`` x ATR in
      the direction that counts for the level's current role; or
    * **repulsion** — a close back on the defending side, at least the
      proximity distance away from the level.

    Those two regions are disjoint, so an approach is never both. One entry
    per approach, not per bar: a level price loiters near for twenty bars has
    been attacked once, and counting bars would make the figure a function of
    how long price happened to dawdle.

    The role alternates on a penetration, exactly as in `detect_breaks` — a
    support can only be attacked from above until it has been broken.

    Returns an empty list rather than raising when there is no usable ATR.
    """
    import numpy as _np

    from app.models.schemas import SRLevelType

    closes = _column(ohlc, "close")
    if not closes or level_price <= 0:
        return []

    if atr is None:
        atr = trailing_atr(ohlc, period=period)

    try:
        close_arr = ohlc["close"].to_numpy(dtype=float, copy=False)
    except (AttributeError, KeyError, TypeError, ValueError):
        close_arr = _np.asarray(
            [c if isinstance(c, (int, float)) else _np.nan for c in closes],
            dtype=float,
        )
    try:
        atr_arr = _np.asarray(atr, dtype=float)
    except (TypeError, ValueError):
        return []
    if atr_arr.shape[0] != close_arr.shape[0]:
        return []

    start = max(0, int(first_bar))

    if declared_type == SRLevelType.SUPPORT:
        wanted = -1
    elif declared_type == SRLevelType.RESISTANCE:
        wanted = 1
    else:
        wanted = -1
        for i in range(start, len(close_arr)):
            if _np.isfinite(close_arr[i]):
                wanted = -1 if close_arr[i] >= level_price else 1
                break

    out = []
    open_at = None  # bar index where the current approach began
    for i in range(start, len(close_arr)):
        close = close_arr[i]
        band = atr_arr[i] if i < atr_arr.shape[0] else float("nan")
        if not _np.isfinite(close) or not _np.isfinite(band) or band <= 0:
            continue

        near_band = float(band) * proximity_atr
        break_band = float(band) * atr_multiple
        distance = float(close) - level_price

        beyond = distance >= break_band if wanted > 0 else distance <= -break_band
        # "Retreated" means back on the side the level is defending, far
        # enough away that the approach is plainly over.
        retreated = -distance >= near_band if wanted > 0 else distance >= near_band

        if open_at is None:
            if abs(distance) <= near_band:
                open_at = i
                # An approach already through the level on the bar it opens
                # resolves immediately.
                if beyond:
                    out.append(LevelAttack(bar_index=open_at, penetrated=True))
                    open_at = None
                    wanted = -wanted
            continue

        if beyond:
            out.append(LevelAttack(bar_index=open_at, penetrated=True))
            open_at = None
            wanted = -wanted
        elif retreated:
            out.append(LevelAttack(bar_index=open_at, penetrated=False))
            open_at = None

    return out


def repelled_attacks(attacks: Sequence[Any]) -> int:
    """`FR-EM-S4`'s `attacks` field: approaches that were turned away.

    A penetration is not an attack in E&M's sense — it is the thing the
    attacks were failing to do — and it is already on the break history, so
    counting it here would double-count one event.
    """
    return sum(1 for a in attacks if not getattr(a, "penetrated", False))


# ===========================================================================
# S7 — age decay (`FR-EM-S5`) and distance-away (`FR-EM-S6`)
#
# The second and third of E&M's three criteria for a level's potential
# (Ch 13); volume was the first, at `S4`.
# ===========================================================================

#: Bars over which half the decayable strength is lost.
#:
#: E&M speak in years — "one or two years old is more effective than four or
#: five" — and a year is ~250 trading sessions. A 250-bar scan window
#: therefore cannot see the distinction they are drawing: `age_bars` spans at
#: most one year inside a single window, so this decay is a weak effect by
#: construction and the figure below is a scale, not a reproduction of the
#: book's claim. `FR-EM-S10` sweeps it at `W1`, and the limitation is recorded
#: in the plan rather than hidden here.
AGE_HALFLIFE_BARS = 120

#: The floor, which `FR-EM-S5` makes binding: E&M are explicit that an old
#: level "does not lose all of its potency by any means", so the decay
#: approaches this and stops. A decay to zero would misread the book.
AGE_DECAY_FLOOR = 0.4

#: E&M's distance-away rule: little real supply from a bottom unless price
#: later fell more than this far under it. Their figure, for 1950s NYSE
#: issues, and a default rather than a trusted constant (`FR-EM-S10`).
DISTANCE_AWAY_PCT = 10.0

#: What a level without that excursion is multiplied by. `FR-EM-S6` says
#: suppress, not drop: a level with no trapped interest behind it is weak
#: evidence, not absent evidence.
DISTANCE_SUPPRESSION = 0.5


def age_decay(age_bars: Any, halflife: int = AGE_HALFLIFE_BARS,
              floor: float = AGE_DECAY_FLOOR) -> float:
    """`FR-EM-S5` — the age multiplier, in ``[floor, 1]``.

    Exponential decay from 1 towards ``floor``, halving the *decayable* part
    every ``halflife`` bars, so a very old level keeps exactly ``floor`` of
    its strength rather than losing all of it.
    """
    try:
        age = float(age_bars)
    except (TypeError, ValueError):
        return 1.0
    if not (age > 0) or math.isnan(age):
        return 1.0
    if halflife <= 0:
        return floor

    span = 1.0 - floor
    value = floor + span * (0.5 ** (age / float(halflife)))
    # Pin the asymptote so a very old level reports the floor exactly rather
    # than a number indistinguishable from it — the test asserts equality.
    if value - floor < 1e-9:
        return floor
    return value


def level_excursion_pct(
    ohlc: Any,
    level_price: float,
    first_bar: int = 0,
) -> Optional[float]:
    """`FR-EM-S6` — how far price has travelled away from the level since it
    formed, as a percentage of the level, taking the **maximum**.

    The maximum rather than the current distance, because the mechanism is
    about holders who are already trapped: a level price once sat 20% away
    from retains the owners that move created, even if price has since come
    back to within 2%.

    Scanning starts at ``first_bar`` — normally the level's first touch —
    because a holder is trapped by what happened *after* he transacted there,
    not before.
    """
    closes = _column(ohlc, "close")
    if not closes or level_price <= 0:
        return None
    start = max(0, int(first_bar))
    if start >= len(closes):
        return None

    worst = 0.0
    seen = False
    for i in range(start, len(closes)):
        c = _usable(closes[i])
        if c is None:
            continue
        seen = True
        worst = max(worst, abs(c - level_price) / level_price * 100.0)
    return worst if seen else None


def adjusted_level_strength(
    volume_strength: Optional[float],
    age_bars: Any,
    excursion_pct: Optional[float],
    distance_pct: float = DISTANCE_AWAY_PCT,
    suppression: float = DISTANCE_SUPPRESSION,
    halflife: int = AGE_HALFLIFE_BARS,
    floor: float = AGE_DECAY_FLOOR,
) -> Optional[float]:
    """The EM-2 composite: volume strength, aged and distance-suppressed.

    Deliberately a **separate** figure from ``volume_strength``, which stays
    raw. `S6` established that rule: a measure E&M predicted (the
    third-attack weighting) turned out not to hold, and folding modifiers into
    the raw measurement would have made that impossible to see. `H-S1` decides
    whether anything should read this.

    ``None`` when there is no volume strength to adjust — the caller falls
    back to the touch count, as everywhere else in EM-2. An **unknown**
    excursion does not suppress: unknown is not "no excursion".
    """
    if volume_strength is None:
        return None

    out = float(volume_strength) * age_decay(age_bars, halflife=halflife, floor=floor)
    if excursion_pct is not None and float(excursion_pct) < distance_pct:
        out *= suppression
    return out
