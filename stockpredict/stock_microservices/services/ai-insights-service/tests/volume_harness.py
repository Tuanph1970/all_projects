"""Test-support for the EM-1 volume harnesses `H1` and `H2`.

**This module is test-support code. It is not shipped and nothing under
``app/`` may import it.** It exists because `H1` (volume shuffle) and `H2`
(null-FPR on surrogates) both need the same three things — OHLCV frames whose
volume is deliberately *aligned* with price, a way to destroy only that
alignment, and a uniform way to run every detector and summarise the result.

Why the existing planted fixtures could not be reused as-is
-----------------------------------------------------------
``tests/test_reversal_patterns.py`` and ``tests/test_continuation_patterns.py``
plant textbook geometry, but every one of their frames carries
``volume = 1000`` on every bar. A constant column is invariant under
permutation, so a shuffle test built on those fixtures would pass for any
implementation, including a decorative one. The builders here therefore keep
the same analytic price geometry (so the shipped detectors still fire) and add
the part that is actually under test: a volume script drawn from Edwards &
Magee's own conditions.

Two construction details are load-bearing:

1. **The lead-in.** Each frame is prefixed with ``LEAD_IN_BARS`` quiet bars.
   `FR-EM-V1`'s baseline is a trailing median over ``DEFAULT_BASELINE_WINDOW``
   bars and `EC-V4` returns *unknown* below ``MIN_BASELINE_BARS``, so without a
   lead-in the left shoulder of a planted H&S has no causal baseline and the
   whole harness would measure the unavailability path instead of the rule.
   The lead-in carries a small deterministic oscillation rather than being
   perfectly flat, so ATR-based detectors are not handed a zero range.

2. **Volume is scripted from the price construction, never fitted to it.**
   The burst and ramp bars are computed from the same indices that draw the
   geometry, so the alignment is exact by construction and a permutation is
   the only thing the shuffle test changes.

The two nulls (`H2`)
--------------------
The SRS records, as a real limitation, that a price-volume rule needs a volume
*process* for its null and that inventing one is itself a modelling choice. So
there are two generators here and the requirement must hold under both:

* ``synthetic_volume`` — a parametric AR(1)-in-log-volume process. Clean, but
  its shape is an assumption.
* ``block_bootstrap_volume`` — resamples contiguous blocks of a *supplied*
  volume series, preserving that series' marginal distribution and its
  short-range clustering exactly, with no parametric assumption.

``source_volume_series()`` supplies the series for the second null. It returns
a committed synthetic series by default, and reads a real one from the CSV at
``$EM1_VOLUME_FIXTURE`` when that is set — the seam task `S2` uses to run the
sweep against an actual symbol. Until then the second null is non-parametric
*with respect to that synthetic source*, which is weaker than non-parametric
with respect to the market, and is reported as such rather than overclaimed.
"""
from __future__ import annotations

import math
import os
from dataclasses import asdict, dataclass, field, replace
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

from app.services.patterns import (
    run_continuation_detectors,
    run_reversal_detectors,
    run_trap_detectors,
)
from app.services.patterns.base import PatternMatch
from app.services.patterns.volume import DEFAULT_BASELINE_WINDOW, breakout_event

# --- Harness constants ------------------------------------------------------

#: Quiet bars prepended to every planted frame so the first scored bar has a
#: full causal baseline behind it (see module docstring, point 1).
LEAD_IN_BARS = DEFAULT_BASELINE_WINDOW + 10

#: Nominal share count the scripted multipliers are applied to. Arbitrary:
#: every rule in `FR-EM-V1` is a ratio, so only the multipliers matter.
BASE_VOLUME = 1_000_000.0

#: Multiplicative lognormal noise on scripted volume. Enough that a real rule
#: must read the script rather than an exact number, small enough that the
#: script survives.
VOLUME_NOISE_SIGMA = 0.18


# --- The V4 seam ------------------------------------------------------------

class VolumeScorerMissing(RuntimeError):
    """Raised when a harness asks a `PatternMatch` for the `FR-EM-V7` fields
    that task `V4` has not added yet.

    This is the seam that lets `H1` be written now and be *red for the right
    reason*. The tests that depend on a scorer are marked
    ``xfail(strict=True, raises=VolumeScorerMissing)``: while V4 is pending
    they fail with this specific type and the suite stays green; the moment V4
    lands they XPASS, and ``strict`` turns that into a failure demanding the
    markers come off. Any *other* failure inside them is reported as a genuine
    failure, so the marker cannot hide a broken harness.
    """


def volume_score_of(match: PatternMatch) -> Optional[float]:
    """`FR-EM-V7`'s ``volume_score``, or raise if V4 has not landed."""
    if not hasattr(match, "volume_score"):
        raise VolumeScorerMissing(
            "PatternMatch has no 'volume_score' — EM-1 task V4 (PatternMatch "
            "composition + the asymmetry rule) is not implemented yet."
        )
    return match.volume_score


def geometric_confidence_of(match: PatternMatch) -> float:
    """The geometry-only confidence, before any volume weighting.

    Deliberately tolerant of both eras: it reads ``geometric_confidence`` once
    V4 adds it, and falls back to ``confidence`` today, when confidence *is*
    geometry. That is what lets the invariance test
    (``geometric_confidence`` is bit-identical under a volume shuffle) be
    green now and stay green afterwards, rather than being rewritten at V4 —
    a test that gets rewritten alongside the code it guards has stopped
    guarding it.
    """
    value = getattr(match, "geometric_confidence", None)
    return float(match.confidence if value is None else value)


# --- Frame construction -----------------------------------------------------

def _piecewise_linear(segments: Sequence[Tuple[float, float, int]]) -> np.ndarray:
    """Concatenate ``(start, end, length)`` segments into one linear series.

    Mirrors the helper in the planted-pattern test modules, including the
    dropped junction point, so the geometry this harness plants is the same
    geometry those suites already prove the detectors find.
    """
    parts: List[np.ndarray] = []
    for i, (start, end, length) in enumerate(segments):
        seg = np.linspace(start, end, length, endpoint=True)
        if i > 0:
            seg = seg[1:]
        parts.append(seg)
    return np.concatenate(parts)


def _lead_in(level: float, bars: int = LEAD_IN_BARS) -> np.ndarray:
    """Quiet bars before the pattern: a small fixed oscillation around
    ``level``. Not flat, so ATR and range-based detectors see a non-zero
    range; too small to register as a swing at the detectors' tolerances."""
    idx = np.arange(bars, dtype=float)
    return level + 0.3 * np.sin(2 * math.pi * idx / 7.0)


def _scripted_volume(
    n: int,
    rng: np.random.Generator,
    *,
    bursts: Sequence[Tuple[int, float, int]] = (),
    ramps: Sequence[Tuple[int, int, float, float]] = (),
    base: float = BASE_VOLUME,
    noise_sigma: float = VOLUME_NOISE_SIGMA,
) -> np.ndarray:
    """Volume as a multiplier curve over ``base``, plus lognormal noise.

    ``bursts``: ``(index, multiplier, decay_bars)`` — a climax or breakout
    burst that decays geometrically back toward 1.0 over ``decay_bars``.
    ``ramps``: ``(start, end, from_mult, to_mult)`` — a geometric ramp across
    ``[start, end)``, which is how "volume dries up toward the apex" (Ch 8)
    and "volume builds through the right shoulder" (Ch 7) are expressed.

    Ramps are applied first, then bursts multiply on top, so a pattern can dry
    up through its consolidation *and* explode on the break — which is the
    single most common E&M script and the one a shuffle most clearly destroys.
    """
    mult = np.ones(n, dtype=float)

    for start, end, from_mult, to_mult in ramps:
        start = max(0, start)
        end = min(n, end)
        if end <= start:
            continue
        span = end - start
        steps = np.linspace(0.0, 1.0, span, endpoint=True) if span > 1 else np.zeros(1)
        # Geometric, not linear: volume is a positive scale, and E&M read it
        # multiplicatively ("twice the recent average"), never additively.
        mult[start:end] *= from_mult * (to_mult / from_mult) ** steps

    for index, peak, decay in bursts:
        if not 0 <= index < n:
            continue
        mult[index] *= peak
        for k in range(1, decay + 1):
            j = index + k
            if j >= n:
                break
            mult[j] *= 1.0 + (peak - 1.0) * (0.5 ** k)

    noise = rng.lognormal(mean=0.0, sigma=noise_sigma, size=n)
    return np.maximum(np.round(base * mult * noise), 1.0)


def _frame(
    close: np.ndarray,
    volume: np.ndarray,
    *,
    hl_pad: float = 0.5,
    high: Optional[np.ndarray] = None,
    low: Optional[np.ndarray] = None,
) -> pd.DataFrame:
    close = np.asarray(close, dtype=float)
    return pd.DataFrame({
        "open": close,
        "high": close + hl_pad if high is None else np.asarray(high, dtype=float),
        "low": close - hl_pad if low is None else np.asarray(low, dtype=float),
        "close": close,
        "volume": np.asarray(volume, dtype=float),
    })


# --- Planted frames, one per E&M volume condition ---------------------------

@dataclass(frozen=True)
class PlantedFrame:
    """A planted pattern plus the E&M condition its volume script encodes.

    ``condition`` is carried so a harness failure says *which* rule the
    shuffle was supposed to break, rather than only that an average moved.
    ``target_pattern`` is the ``pattern_name`` the frame was drawn for, so a
    test can assert on the planted pattern specifically as well as on the
    whole detector sweep.

    A note on incidental detections: because these frames are drawn from
    piecewise-linear legs, a leg steeper than ``hl_pad`` leaves a literal
    bar-to-bar gap, so ``GapDetector`` fires on most of them. That is a
    property of analytic fixtures — the planted-pattern suites share it — not
    a detector fault, and it is why the aggregate assertions are reported both
    over all detections and over ``target_pattern`` alone.
    """
    name: str
    frame: pd.DataFrame
    condition: str
    citation: str
    target_pattern: str = ""


def _hs_top(rng: np.random.Generator, leg: int = 8, *, textbook: bool = True) -> PlantedFrame:
    """H&S top. Ch 7: heavy left shoulder, *decidedly lighter* right shoulder,
    and the break of the neckline is where activity picks up. Head volume is
    deliberately left unscripted — E&M say it is not a tell.

    ``textbook=False`` reverses only the shoulder weighting — heavy right,
    light left — leaving the geometry bit-identical. That pair is what lets a
    test say the rule reads its *condition* rather than the shape.
    """
    base, shoulder, head = 100.0, 10.0, 18.0
    body = _piecewise_linear([
        (base, base + shoulder, leg + 1),
        (base + shoulder, base, leg + 1),
        (base, base + head, leg + 1),
        (base + head, base, leg + 1),
        (base, base + shoulder, leg + 1),
        (base + shoulder, base - 3, leg + 1),
    ])
    close = np.concatenate([_lead_in(base), body])
    off = LEAD_IN_BARS
    ls_peak = off + leg
    rs_peak = off + 4 * leg
    volume = _scripted_volume(
        close.size,
        rng,
        ramps=[
            (off, ls_peak + 2, 1.6, 2.4),             # heavy left shoulder
            (rs_peak - leg, rs_peak + 2, 1.0, 0.55),  # decidedly lighter right
        ] if textbook else [
            (off, ls_peak + 2, 1.0, 0.6),             # adverse: light left
            (rs_peak - leg, rs_peak + 2, 1.6, 2.6),   # adverse: heavy right
        ],
    )
    return PlantedFrame(
        "hs_top", _frame(close, volume),
        "left shoulder heavy, right shoulder light, break on expansion",
        "E&M Ch 7", "Head and Shoulders",
    )


def _inv_hs(rng: np.random.Generator, leg: int = 8, *, textbook: bool = True) -> PlantedFrame:
    """Inverse H&S. Ch 7's near-absolute: a bottom *requires* the breakout
    burst — "it takes buying to put stocks up" — and volume builds through the
    right shoulder rather than drying up."""
    base, shoulder, head = 100.0, 10.0, 18.0
    body = _piecewise_linear([
        (base, base - shoulder, leg + 1),
        (base - shoulder, base, leg + 1),
        (base, base - head, leg + 1),
        (base - head, base, leg + 1),
        (base, base - shoulder, leg + 1),
        (base - shoulder, base + 3, leg + 1),
    ])
    close = np.concatenate([_lead_in(base), body])
    off = LEAD_IN_BARS
    drawn_break = off + 5 * leg
    volume = _scripted_volume(
        close.size,
        rng,
        # The adverse case is the one E&M single out: a bottom whose volume
        # dries up instead of building, and whose penetration carries no burst.
        ramps=[(off + 3 * leg, drawn_break, 0.8, 2.0)] if textbook
        else [(off + 3 * leg, close.size, 1.6, 0.5)],
    )
    return PlantedFrame(
        "inv_hs", _frame(close, volume),
        "volume builds through the right shoulder, burst on the upside break",
        "E&M Ch 7", "Inverse Head and Shoulders",
    )


def _double_top(rng: np.random.Generator, leg: int = 8, *, textbook: bool = True) -> PlantedFrame:
    """Double top. Ch 7: the second top makes its high on *lighter* volume
    than the first — the distribution tell."""
    base, peak_h, trough_d = 100.0, 15.0, 8.0
    peak = base + peak_h
    trough = peak - trough_d
    body = _piecewise_linear([
        (base, peak, leg + 1),
        (peak, trough, leg + 1),
        (trough, peak, leg + 1),
        (peak, base - 3, leg + 1),
    ])
    close = np.concatenate([_lead_in(base), body])
    off = LEAD_IN_BARS
    first_peak = off + leg
    second_peak = off + 3 * leg
    volume = _scripted_volume(
        close.size,
        rng,
        ramps=[
            (off, first_peak + 2, 1.5, 2.3),
            (second_peak - leg, second_peak + 2, 1.0, 0.6),
        ] if textbook else [
            (off, first_peak + 2, 1.0, 0.6),
            (second_peak - leg, second_peak + 2, 1.5, 2.4),
        ],
    )
    return PlantedFrame(
        "double_top", _frame(close, volume),
        "second top on lighter volume than the first",
        "E&M Ch 7", "Double Top",
    )


def _double_bottom(rng: np.random.Generator, leg: int = 8, *, textbook: bool = True) -> PlantedFrame:
    """Double bottom. Ch 7, read through the asymmetry of `FR-EM-V3`: the
    second low is quiet, and the confirming push through the intervening peak
    must carry volume."""
    base, trough_d, peak_h = 100.0, 15.0, 8.0
    trough = base - trough_d
    peak = trough + peak_h
    body = _piecewise_linear([
        (base, trough, leg + 1),
        (trough, peak, leg + 1),
        (peak, trough, leg + 1),
        (trough, base + 3, leg + 1),
    ])
    close = np.concatenate([_lead_in(base), body])
    off = LEAD_IN_BARS
    second_low = off + 3 * leg
    volume = _scripted_volume(
        close.size,
        rng,
        # "Conspicuously dull and rounded" (Ch 9) vs a loud retest.
        ramps=[(second_low - leg, second_low + 1, 1.2, 0.5)] if textbook
        else [(second_low - leg, second_low + 1, 1.0, 2.2)],
    )
    return PlantedFrame(
        "double_bottom", _frame(close, volume),
        "quiet second low, volume on the confirming advance",
        "E&M Ch 7", "Double Bottom",
    )


def _bull_flag(rng: np.random.Generator, *, textbook: bool = True) -> PlantedFrame:
    """Bull flag. Ch 8/11: a heavy pole, volume *drying up* through the flag,
    and expansion on the resumption. The drying-up span is what
    ``volume_trend`` was built to read."""
    base, pole_bars, pole_h, flag_bars, retrace = 100.0, 6, 15.0, 8, 3.0
    body = _piecewise_linear([
        (base, base, 25),
        (base, base + pole_h, pole_bars + 1),
        (base + pole_h, base + pole_h - retrace, flag_bars + 1),
    ])
    close = np.concatenate([_lead_in(base), body])
    off = LEAD_IN_BARS
    pole_start = off + 25
    flag_start = pole_start + pole_bars
    volume = _scripted_volume(
        close.size,
        rng,
        ramps=[
            (pole_start, flag_start, 1.8, 3.0),                  # heavy pole
            (flag_start, close.size, 1.4, 0.45),                 # dries up
        ] if textbook else [
            (pole_start, flag_start, 1.8, 3.0),
            # Ch 11's inversion: high volume INSIDE the flag turns it from a
            # continuation into a minor reversal area.
            (flag_start, close.size, 1.0, 2.8),
        ],
    )
    return PlantedFrame(
        "bull_flag", _frame(close, volume),
        "heavy pole, volume dries up through the flag",
        "E&M Ch 8, Ch 11", "Flag",
    )


def _symmetrical_triangle(
    rng: np.random.Generator, n_bars: int = 80, *, textbook: bool = True
) -> PlantedFrame:
    """Symmetrical triangle. Ch 8: *"volume diminishes irregularly but
    noticeably toward the apex"*, then the break carries activity."""
    base, start_amp = 100.0, 18.0
    bars = np.arange(n_bars, dtype=float)
    amplitude = start_amp * (1.0 - bars / n_bars)
    body = base + amplitude * np.sin(2 * math.pi * bars / 10)
    close = np.concatenate([_lead_in(base), body])
    off = LEAD_IN_BARS
    volume = _scripted_volume(
        close.size,
        rng,
        # "Irregularly" matters: a monotone decay would be readable by a
        # trend measure that is not rank-based, which would let a weaker
        # implementation pass. The sine term keeps it bumpy.
        ramps=[(off, close.size, 2.2, 0.4)] if textbook
        else [(off, close.size, 0.45, 2.3)],      # adverse: swells to the apex
    )
    wobble = 1.0 + 0.25 * np.sin(2 * math.pi * np.arange(close.size) / 9.0)
    volume = np.maximum(np.round(volume * wobble), 1.0)
    return PlantedFrame(
        "symmetrical_triangle", _frame(close, volume),
        "volume diminishes irregularly toward the apex",
        "E&M Ch 8", "Symmetrical Triangle",
    )


def with_breakout_burst(planted: PlantedFrame, multiplier: float) -> PlantedFrame:
    """Put the breakout burst on the bar the **detector** calls the break.

    Why this is a second phase rather than another entry in ``bursts``: the
    builders know where the geometry *draws* the penetration, but a detector
    locates it from its own ``neckline``, and the two differ by several bars —
    an H&S top drawn to break at bar 100 is detected as breaking at 107,
    because the neckline sits at the trough lows and the final leg takes that
    long to close below it.

    The original V2 fixtures put the burst at the drawn index, which left
    ``rvol`` at the operative bar sitting around 0.95 — flat. Nothing noticed,
    because nothing read volume until V4. So the burst is now applied *after*
    detection, at ``breakout_bar``, which is the bar the rule under test will
    actually read. The fixture now plants what it claims to plant.

    Decays geometrically over the following bars, the way the breakout-day
    volume spurt does rather than reverting in one session. A ``multiplier``
    below 1.0 suppresses instead, which is how the adverse fixtures express a
    break that creeps through its boundary on dying volume.

    Uses ``breakout_event`` rather than ``breakout_bar`` so it also works for a
    ``neutral`` pattern such as the symmetrical triangle, whose direction is
    only known once the penetration is located.
    """
    matches = [m for m in detect_all(planted.frame) if m.pattern_name == planted.target_pattern]
    if not matches:
        return planted
    event = breakout_event(matches[0], planted.frame)
    if event is None:
        return planted
    bar = event.bar

    frame = planted.frame.copy(deep=True)
    volume = frame["volume"].to_numpy(dtype=float).copy()
    for k in range(4):
        if bar + k < volume.size:
            volume[bar + k] *= 1.0 + (multiplier - 1.0) * (0.5 ** k)
    frame["volume"] = np.maximum(np.round(volume), 1.0)
    return replace(planted, frame=frame)


def planted_frames(seed: int = 20261012) -> List[PlantedFrame]:
    """The planted set for `H1`, one frame per E&M volume condition.

    Seeded, so `H6` determinism is testable and a failure is reproducible.
    """
    rng = np.random.default_rng(seed)
    # The burst multipliers mirror the emphasis E&M put on each break: the
    # inverse H&S "conspicuous burst" is the strongest, the double top's
    # downside confirmation the mildest. Defaults pending the S2 sweep.
    return [
        with_breakout_burst(_hs_top(rng), 2.8),
        with_breakout_burst(_inv_hs(rng), 3.5),
        with_breakout_burst(_double_top(rng), 2.2),
        with_breakout_burst(_double_bottom(rng), 3.0),
        _bull_flag(rng),               # no break in the frame — V6's condition
        _symmetrical_triangle(rng),    # pattern_type "neutral" — V6's condition
    ]


def _bull_pennant(rng: np.random.Generator, *, textbook: bool = True) -> PlantedFrame:
    """Bull pennant with explicit converging channels (the shape
    `PennantDetector` needs), and Ch 11's volume script: a spurt on the mast,
    then *"volume dries up even faster than a flag, sometimes to almost
    nothing"*.

    ``textbook=False`` is the inversion E&M warn about: high or irregular
    volume **inside** the consolidation, which turns it from a continuation
    into a minor reversal area (`FR-EM-V4`).
    """
    base, n_base, pole_bars, pole_height, pennant_bars = 100.0, 25, 6, 15.0, 8
    pole_top = base + pole_height
    lead = _lead_in(base)
    n_total = lead.size + n_base + pole_bars + pennant_bars
    close = np.zeros(n_total)
    high = np.zeros(n_total)
    low = np.zeros(n_total)
    close[: lead.size] = lead
    high[: lead.size] = lead + 0.5
    low[: lead.size] = lead - 0.5

    off = lead.size
    for i in range(n_base):
        close[off + i], high[off + i], low[off + i] = base, base + 0.5, base - 0.5
    pole_start = off + n_base
    for j in range(pole_bars):
        i = pole_start + j
        close[i] = base + (j + 1) * pole_height / pole_bars
        high[i], low[i] = close[i] + 0.5, close[i] - 0.5
    pn_start = pole_start + pole_bars
    for j in range(pennant_bars):
        t = j / max(pennant_bars - 1, 1)
        upper = (pole_top - 1.0) - 3.0 * t
        lower = (pole_top - 7.0) + 3.0 * t
        close[pn_start + j] = (upper + lower) / 2
        high[pn_start + j], low[pn_start + j] = upper, lower

    volume = _scripted_volume(
        n_total,
        rng,
        ramps=[
            (pole_start, pn_start, 1.8, 3.2),          # the mast's spurt
            (pn_start, n_total, 1.0, 0.18),            # dries to almost nothing
        ] if textbook else [
            (pole_start, pn_start, 1.8, 3.2),
            (pn_start, n_total, 0.9, 2.6),             # adverse: expands inside
        ],
    )
    return PlantedFrame(
        "bull_pennant", _frame(close, volume, high=high, low=low),
        "mast spurt, then volume dries up even faster than a flag",
        "E&M Ch 11", "Pennant",
    )


def _ascending_triangle(rng: np.random.Generator, *, textbook: bool = True) -> PlantedFrame:
    """Flat resistance with rising lows. Ch 8: resolution runs about 9:1 to
    the upside, so breakout expansion is **required** here."""
    base, resistance, n_bars = 100.0, 120.0, 80
    bars = np.arange(n_bars, dtype=float)
    low_line = base + (resistance - base) * bars / n_bars
    amplitude = resistance - low_line
    body = low_line + amplitude * (np.sin(2 * math.pi * bars / 12) + 1) / 2
    close = np.concatenate([_lead_in(base), body])
    off = LEAD_IN_BARS
    volume = _scripted_volume(
        close.size, rng,
        ramps=[(off, close.size, 2.2, 0.45)] if textbook
        else [(off, close.size, 0.5, 2.4)],       # adverse: swells to the apex
    )
    return PlantedFrame(
        "ascending_triangle", _frame(close, volume),
        "volume diminishes toward the apex; upside break needs expansion",
        "E&M Ch 8", "Ascending Triangle",
    )


def _descending_triangle(rng: np.random.Generator, *, textbook: bool = True) -> PlantedFrame:
    """Descending highs with flat support. Ch 8: downside resolution, so
    breakout volume only corroborates — and an *extreme* downside break is
    suspect (`FR-EM-V4`), a 2-3 day shakeout."""
    base, top, n_bars = 80.0, 120.0, 80
    bars = np.arange(n_bars, dtype=float)
    high_line = top - (top - base) * bars / n_bars
    amplitude = high_line - base
    body = base + amplitude * (np.sin(2 * math.pi * bars / 12) + 1) / 2
    close = np.concatenate([_lead_in(base + (top - base) / 2.0), body])
    off = LEAD_IN_BARS
    volume = _scripted_volume(
        close.size, rng,
        ramps=[(off, close.size, 2.0, 0.5)] if textbook
        else [(off, close.size, 0.5, 2.2)],
    )
    return PlantedFrame(
        "descending_triangle", _frame(close, volume),
        "volume diminishes toward the apex; downside break corroborating only",
        "E&M Ch 8", "Descending Triangle",
    )


def consolidation_frames(seed: int = 20261014, *, textbook: bool = True) -> List[PlantedFrame]:
    """The five `V6a` formations: flag, pennant and the three triangles.

    Separate from ``planted_frames`` because their conditions are about volume
    *through the formation* rather than at a penetration, and because three of
    them did not exist before V6a needed them.
    """
    rng = np.random.default_rng(seed)
    # The symmetrical triangle is the one formation here that penetrates a
    # boundary inside its own frame, so its pair has to be consistent end to
    # end. Ch 8 is a two-part statement — volume "diminishes irregularly but
    # noticeably toward the apex, THEN expands on the breakout" — and a
    # fixture that dried up and then crept through on nothing would be
    # planting a textbook formation with a false-move resolution.
    return [
        _bull_flag(rng, textbook=textbook),
        _bull_pennant(rng, textbook=textbook),
        with_breakout_burst(
            _symmetrical_triangle(rng, textbook=textbook), 2.5 if textbook else 0.35
        ),
        _ascending_triangle(rng, textbook=textbook),
        _descending_triangle(rng, textbook=textbook),
    ]


def _exhaustion_gap(rng: np.random.Generator, *, textbook: bool = True) -> PlantedFrame:
    """A gap in an established advance, then price failing to carry on.

    Ch 12's exhaustion gap is recognised by *"extraordinary volume with price
    failing to advance commensurately"* on the day after — a **volume** rule
    that the shipped classifier has no way to express, which is why it calls
    this frame a *runaway* gap on geometry alone. The textbook variant is the
    one case where EM-1 re-labels a pattern rather than only scoring it.

    ``textbook=False`` keeps the same gap and the same advance continuing, on
    ordinary volume: a genuine runaway, which must be left alone.
    """
    rise = np.linspace(100.0, 128.0, 40)
    lead = _lead_in(100.0)
    gap_open = rise[-1] * 1.05
    drift = np.linspace(0.0, -0.6, 6) if textbook else np.linspace(0.0, 4.0, 6)
    close = np.concatenate([lead, rise, gap_open + drift])
    gap_bar = lead.size + 40

    high, low = close + 0.4, close - 0.4
    low[gap_bar] = gap_open - 0.1          # the gap itself: low[i] > high[i-1]
    volume = _scripted_volume(
        close.size, rng, bursts=[(gap_bar, 9.0 if textbook else 1.6, 2)]
    )
    return PlantedFrame(
        "exhaustion_gap", _frame(close, volume, high=high, low=low),
        "extraordinary volume with price failing to advance commensurately",
        "E&M Ch 12", "Gap (runaway)",
    )


def _one_day_reversal(rng: np.random.Generator, *, textbook: bool = True) -> PlantedFrame:
    """A wide-range bar closing near its high after a decline.

    Ch 10.1: a true One-Day Reversal requires *"volume exceeding anything for
    months"*, which is a **long**-lookback measure and not the 50-bar baseline
    every other rule uses. Without that volume it is an ordinary wide day and
    must score low. The lead-in is long enough for that long window to exist.
    """
    lead = _lead_in(100.0, bars=150)
    decline = np.linspace(100.0, 82.0, 25)
    tail = 6
    close = np.concatenate([lead, decline, np.full(tail, 82.0)])
    bar = close.size - tail

    high, low = close + 0.4, close - 0.4
    high[bar], low[bar] = close[bar] + 6.0, close[bar] - 6.0
    close[bar] = low[bar] + 0.85 * (high[bar] - low[bar])   # closes in the upper half
    volume = _scripted_volume(
        close.size, rng, bursts=[(bar, 12.0 if textbook else 1.2, 1)]
    )
    return PlantedFrame(
        "one_day_reversal", _frame(close, volume, high=high, low=low),
        "volume exceeding anything for months",
        "E&M Ch 10.1", "Wide-Ranging Day",
    )


def _bull_trap(rng: np.random.Generator, *, textbook: bool = True) -> PlantedFrame:
    """Resistance touched twice, pierced, then given back.

    Ch 13/35: a genuine break is *"nearly always followed by sudden
    acceleration and a marked volume pickup"* **after** the penetration. So
    here volume works the other way round from everywhere else in EM-1 — the
    **absence** of follow-through is the trap's signature, and therefore
    *raises* confidence that it is a trap.

    ``textbook=True`` is the trap: the pierce is not followed through on
    volume. ``textbook=False`` has heavy follow-through, which argues the break
    was real and the trap reading is wrong.
    """
    lead = _lead_in(100.0)
    seg = np.concatenate([
        np.linspace(100, 112, 9),
        np.linspace(112, 104, 9)[1:],
        np.linspace(104, 112, 9)[1:],
        np.linspace(112, 105, 9)[1:],
        np.linspace(105, 116, 7)[1:],      # the pierce
        np.linspace(116, 103, 7)[1:],      # and the reversion
    ])
    close = np.concatenate([lead, seg])
    volume = _scripted_volume(close.size, rng)
    planted = PlantedFrame(
        "bull_trap", _frame(close, volume),
        "a penetration with no follow-through volume is the trap signature",
        "E&M Ch 13, Ch 35", "Bull Trap",
    )
    return with_follow_through_volume(planted, 0.3 if textbook else 3.0)


def with_follow_through_volume(planted: PlantedFrame, multiple: float) -> PlantedFrame:
    """Scale the volume on the bars **after** the detected penetration.

    Two-phase for the same reason ``with_breakout_burst`` is: the builder knows
    where it *drew* the pierce, but `TrapDetector` locates the penetration and
    the reversion itself, from its own clustered support/resistance levels, and
    the two differ — this fixture draws the pierce at bar 93 and the detector
    reports 99/100. A first attempt scaled the drawn bars and moved the reading
    by 0.03, which is noise.

    So the span is taken from ``key_bars`` after detection: ``(penetration,
    reversion]``, exactly the bars the rule reads.
    """
    matches = [m for m in detect_all(planted.frame) if m.pattern_name == planted.target_pattern]
    if not matches:
        return planted
    key_bars = matches[0].key_bars
    if len(key_bars) < 2:
        return planted

    frame = planted.frame.copy(deep=True)
    volume = frame["volume"].to_numpy(dtype=float).copy()
    start, end = int(key_bars[0]) + 1, min(volume.size, int(key_bars[1]) + 1)
    volume[start:end] *= multiple
    frame["volume"] = np.maximum(np.round(volume), 1.0)
    return replace(planted, frame=frame)


def _volume_climax(rng: np.random.Generator, *, textbook: bool = True) -> PlantedFrame:
    """A selling-climax bar: enormous volume, a wide range, and almost no net
    progress because price plunged and snapped back inside the session.

    `FR-EM-V6` defines climactic as *extreme `rvol` against a long baseline
    **and** price progress not commensurate*, and the snap-back is what makes
    the progress non-commensurate — Ch 10's selling climax, Ch 28's "prepare
    to retire into your shell".

    The pair differs **only** in the volume on that one bar, so a test can say
    the flag reads volume rather than shape. Deliberately contrasts with
    ``_one_day_reversal``, which also spikes volume but *does* make its move,
    and must therefore not be flagged.
    """
    lead = _lead_in(100.0, bars=150)
    decline = np.linspace(100.0, 86.0, 20)
    close = np.concatenate([lead, decline, np.full(3, 86.0)])
    bar = close.size - 3

    high, low = close + 0.4, close - 0.4
    low[bar] = close[bar] - 9.0          # the plunge
    high[bar] = close[bar] + 0.6
    # close[bar] stays at the prior level: the snap-back, so net progress is
    # tiny against a range that is anything but.
    volume = _scripted_volume(
        close.size, rng, bursts=[(bar, 10.0 if textbook else 1.1, 0)]
    )
    return PlantedFrame(
        "selling_climax", _frame(close, volume, high=high, low=low),
        "extreme volume with price progress not commensurate",
        "E&M Ch 10, Ch 28", "",
    )


def climax_frames(seed: int = 20261016, *, textbook: bool = True) -> List[PlantedFrame]:
    """`FR-EM-V6`'s pair. Not a pattern fixture — the climax flag is
    independent of any detector, which is the whole point of the requirement.
    """
    rng = np.random.default_rng(seed)
    return [_volume_climax(rng, textbook=textbook)]


def bar_pattern_frames(seed: int = 20261015, *, textbook: bool = True) -> List[PlantedFrame]:
    """The three `V6b` formations: gap, one-day reversal, trap.

    Grouped apart from the others because each reads volume at or just after a
    **single bar** rather than across a formation, and because all three invert
    or extend the usual reading — the gap re-labels, the one-day reversal needs
    a second much longer baseline, and the trap rewards volume's absence.
    """
    rng = np.random.default_rng(seed)
    return [
        _exhaustion_gap(rng, textbook=textbook),
        _one_day_reversal(rng, textbook=textbook),
        _bull_trap(rng, textbook=textbook),
    ]


def with_resolution(
    frame: pd.DataFrame,
    direction: str,
    *,
    bars: int = 6,
    move: float = 0.06,
    volume_multiple: float = 1.0,
) -> pd.DataFrame:
    """Append a breakout leg so a consolidation's **breakout** rule can be read.

    All five V6a formations are detected while still unresolved — which is the
    point of a flag or a triangle, and why their formation conditions are the
    primary evidence. But `FR-EM-V4`'s suspect rule and Ch 8's
    "upside break requires expansion" are statements about the *penetration*,
    so a resolved frame has to be built deliberately.

    ``volume_multiple`` is applied against the trailing median, so it is the
    `rvol` the breakout bars will read — which is what lets a test sweep the
    rule from dull through confirming to suspect.

    Known limitation, recorded because it shaped the test suite: extending a
    **flag or pennant** this way makes the detector stop reporting it, since
    the added leg changes the pole-and-consolidation structure it matched on.
    Those two are therefore tested on their formation conditions only.
    """
    close = frame["close"].to_numpy(dtype=float)
    volume = frame["volume"].to_numpy(dtype=float)
    sign = 1.0 if direction == "bullish" else -1.0
    leg = close[-1] * (1.0 + sign * move * np.linspace(1.0 / bars, 1.0, bars))
    recent = volume[-DEFAULT_BASELINE_WINDOW:]
    baseline = float(np.median(recent[recent > 0]))
    leg_volume = np.full(bars, max(1.0, round(baseline * volume_multiple)))

    return pd.DataFrame({
        "open": np.concatenate([frame["open"].to_numpy(dtype=float), leg]),
        "high": np.concatenate([frame["high"].to_numpy(dtype=float), leg + 0.5]),
        "low": np.concatenate([frame["low"].to_numpy(dtype=float), leg - 0.5]),
        "close": np.concatenate([close, leg]),
        "volume": np.concatenate([volume, leg_volume]),
    })


def adverse_frames(seed: int = 20261013) -> List[PlantedFrame]:
    """The same four reversal geometries with the **opposite** volume script,
    and deliberately **no breakout burst**.

    Pairing these against ``planted_frames`` is the cleanest statement that a
    rule reads its E&M condition and not the shape: the price series are
    identical bit for bit, so any difference in the verdict came from volume.

    Only the four reversal frames are built. The flag and triangle conditions
    are span measures that no rule reads until V6, so an "adverse" variant of
    them would assert nothing today.
    """
    rng = np.random.default_rng(seed)
    return [
        _hs_top(rng, textbook=False),
        _inv_hs(rng, textbook=False),
        _double_top(rng, textbook=False),
        _double_bottom(rng, textbook=False),
    ]


# --- The shuffle (H1) -------------------------------------------------------

def shuffle_volume(frame: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    """Permute the ``volume`` column and nothing else.

    A permutation is the right surrogate for this question because it leaves
    volume's marginal distribution exactly intact — same bars, same share
    counts, same median, same outliers — and destroys only the alignment with
    price. So anything that changes must be reading the price-volume
    *relationship*, which is precisely what E&M describe and what `H1` is
    there to prove the implementation reads.
    """
    out = frame.copy(deep=True)
    out["volume"] = rng.permutation(frame["volume"].to_numpy())
    return out


# --- Volume nulls (H2) ------------------------------------------------------

def synthetic_volume(
    length: int,
    rng: np.random.Generator,
    *,
    base: float = BASE_VOLUME,
    persistence: float = 0.75,
    sigma: float = 0.45,
) -> np.ndarray:
    """Null #1 — a parametric AR(1) process in log-volume.

    Volume clusters (busy days follow busy days) and is right-skewed, so an
    AR(1) in logs is the least-assuming process that is not obviously
    unrealistic. It is still an assumption, which is exactly why
    ``block_bootstrap_volume`` exists alongside it.
    """
    log_dev = np.zeros(length, dtype=float)
    shocks = rng.normal(0.0, sigma, size=length)
    for i in range(1, length):
        log_dev[i] = persistence * log_dev[i - 1] + shocks[i]
    return np.maximum(np.round(base * np.exp(log_dev)), 1.0)


def block_bootstrap_volume(
    source: Sequence[float],
    length: int,
    rng: np.random.Generator,
    *,
    block_bars: int = 10,
) -> np.ndarray:
    """Null #2 — resample contiguous blocks of ``source``.

    Blocks rather than single bars, because drawing i.i.d. bars would destroy
    volume clustering and produce a null that is easier to beat than reality.
    ``block_bars`` is the usual trade-off: long enough to carry clustering,
    short enough that the result is not a copy of the source.

    No parametric assumption is made about the source's shape, so whatever is
    supplied — including a real symbol's series via ``source_volume_series`` —
    comes through with its marginal distribution and short-range dependence
    intact.
    """
    src = np.asarray(source, dtype=float)
    if src.size == 0:
        raise ValueError("block bootstrap needs a non-empty source series")
    block_bars = max(1, min(block_bars, src.size))
    out = np.empty(length, dtype=float)
    filled = 0
    while filled < length:
        start = int(rng.integers(0, src.size - block_bars + 1))
        take = min(block_bars, length - filled)
        out[filled:filled + take] = src[start:start + take]
        filled += take
    return np.maximum(np.round(out), 1.0)


def source_volume_series(length: int = 750) -> Tuple[np.ndarray, str]:
    """The series null #2 bootstraps, plus a label saying what it actually is.

    Returns the CSV at ``$EM1_VOLUME_FIXTURE`` when set (one column named
    ``volume``, or a single unnamed column) — the seam task `S2` uses to run
    the sweep against a real symbol. Otherwise a committed synthetic series.

    The label is returned rather than assumed because the strength of the
    `H2` claim depends on it, and a harness that silently substitutes
    synthetic data for market data would overstate its own result.
    """
    path = os.environ.get("EM1_VOLUME_FIXTURE")
    if path:
        df = pd.read_csv(path)
        column = "volume" if "volume" in df.columns else df.columns[0]
        series = df[column].to_numpy(dtype=float)
        series = series[np.isfinite(series) & (series > 0)]
        if series.size < 50:
            raise ValueError(f"{path}: need >= 50 usable volume bars, got {series.size}")
        return series, f"real:{os.path.basename(path)}"
    return synthetic_volume(length, np.random.default_rng(104729)), "synthetic-source"


def random_walk_ohlcv(
    length: int,
    volatility: float,
    volume: Sequence[float],
    rng: np.random.Generator,
    *,
    start: float = 100.0,
) -> pd.DataFrame:
    """A random-walk OHLCV frame: no genuine pattern by construction, and —
    the point of the null for *this* slice — volume drawn independently of
    price, so no genuine price-volume relationship either.

    The intraday range is proportional to price rather than additive, so the
    surrogate's bar ranges stay comparable in percentage terms across the path
    the way a real series' do.
    """
    steps = rng.normal(0.0, volatility, size=length)
    close = start * np.exp(np.cumsum(steps))
    span = np.abs(rng.normal(0.0, volatility, size=length)) + volatility * 0.5
    return _frame(
        close,
        np.asarray(volume, dtype=float)[:length],
        high=close * (1.0 + span),
        low=close * (1.0 - span),
    )


# --- Running the detectors and summarising ----------------------------------

def detect_all(frame: pd.DataFrame) -> List[PatternMatch]:
    """Every shipped detector against one frame, found matches only.

    Uses the same three runners the API aggregator uses, so the harness
    measures the production path rather than a hand-picked subset.
    """
    return (
        run_reversal_detectors(frame)
        + run_continuation_detectors(frame)
        + run_trap_detectors(frame)
    )


@dataclass(frozen=True)
class NullReport:
    """What `H2` measures, per null.

    ``detections_per_surrogate`` is the headline false-positive rate: how often
    the shipped detectors fire on series that contain nothing. ``*_pct95`` is
    the significance gate — a real detection has to clear what the null
    produces 95% of the time before it means anything.

    ``confidence_*`` and ``geometric_*`` are recorded **separately and both**,
    because `FR-EM-V7` makes ``confidence`` a composite that V4 deliberately
    moves. Only the geometric series is comparable across V4, so that is the
    one the baseline-drift test watches; the composite series is what the
    survivor gate is measured on. Before V4 the two are identical, which is
    itself worth having on record.
    """
    null_name: str
    volume_source: str
    n_surrogates: int
    length: int
    detections_per_surrogate: float
    detections_by_pattern: Dict[str, float]
    confidence_pct95_overall: float
    confidence_pct95_by_pattern: Dict[str, float]
    geometric_pct95_overall: float = 0.0
    geometric_pct95_by_pattern: Dict[str, float] = field(default_factory=dict)
    n_detections_total: int = 0
    n_surviving: Optional[int] = None
    mean_confidence: float = 0.0
    mean_geometric: float = 0.0
    n_tied_at_gate: Optional[int] = None
    notes: Dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _pct95(values: Sequence[float]) -> float:
    if not len(values):
        return 0.0
    return float(np.percentile(np.asarray(values, dtype=float), 95))


def run_null(
    null_name: str,
    n_surrogates: int,
    length: int,
    volatility: float,
    *,
    seed: int,
    volume_source: Optional[Sequence[float]] = None,
    volume_source_label: str = "",
    block_bars: int = 10,
    thresholds: Optional[Dict[str, float]] = None,
) -> NullReport:
    """Run the detectors over ``n_surrogates`` random-walk OHLCV frames.

    ``volume_source`` selects the null: ``None`` draws volume from
    ``synthetic_volume`` (null #1), a supplied series block-bootstraps it
    (null #2). Everything is driven from one seeded ``Generator``, so the whole
    report is reproducible from ``seed`` alone — which the determinism test
    relies on and which makes a drifting baseline a real signal rather than
    sampling noise.

    ``thresholds`` turns on the survivor count: with a *fixed*, externally
    supplied threshold per pattern, ``n_surviving`` is how many null detections
    clear it. The fixed part is what makes the number mean anything — counting
    detections above the run's *own* 95th percentile would return 5% by
    construction, whatever the detector does. So `H2`'s second requirement is
    stated against the geometry-only thresholds recorded in the committed
    baseline, and EM-1 has to lower the count that clears them.

    A pattern absent from ``thresholds`` never appeared in the null at all, so
    any detection of it counts as surviving — the same convention as
    ``chart-decomp-lib``'s ``is_noteworthy``, where never firing on noise makes
    a detection unconditionally significant — and strict ``>``, the same
    comparison that module uses, so the two null harnesses in this repo answer
    the significance question identically.
    """
    rng = np.random.default_rng(seed)
    per_pattern_counts: Dict[str, int] = {}
    per_pattern_conf: Dict[str, List[float]] = {}
    per_pattern_geom: Dict[str, List[float]] = {}
    all_conf: List[float] = []
    all_geom: List[float] = []
    total = 0
    surviving = 0
    tied = 0

    for _ in range(n_surrogates):
        if volume_source is None:
            volume = synthetic_volume(length, rng)
        else:
            volume = block_bootstrap_volume(volume_source, length, rng, block_bars=block_bars)
        frame = random_walk_ohlcv(length, volatility, volume, rng)
        for match in detect_all(frame):
            total += 1
            if thresholds is not None:
                gate = thresholds.get(match.pattern_name)
                if gate is None or float(match.confidence) > gate:
                    surviving += 1
                if gate is not None and abs(geometric_confidence_of(match) - gate) < 1e-9:
                    tied += 1
            per_pattern_counts[match.pattern_name] = per_pattern_counts.get(match.pattern_name, 0) + 1
            per_pattern_conf.setdefault(match.pattern_name, []).append(float(match.confidence))
            all_conf.append(float(match.confidence))
            geometric = geometric_confidence_of(match)
            per_pattern_geom.setdefault(match.pattern_name, []).append(geometric)
            all_geom.append(geometric)

    return NullReport(
        null_name=null_name,
        volume_source=volume_source_label or ("synthetic-process" if volume_source is None else "supplied"),
        n_surrogates=n_surrogates,
        length=length,
        detections_per_surrogate=round(total / n_surrogates, 6),
        detections_by_pattern={
            k: round(v / n_surrogates, 6) for k, v in sorted(per_pattern_counts.items())
        },
        confidence_pct95_overall=round(_pct95(all_conf), 6),
        confidence_pct95_by_pattern={
            k: round(_pct95(v), 6) for k, v in sorted(per_pattern_conf.items())
        },
        geometric_pct95_overall=round(_pct95(all_geom), 6),
        geometric_pct95_by_pattern={
            k: round(_pct95(v), 6) for k, v in sorted(per_pattern_geom.items())
        },
        n_detections_total=total,
        n_surviving=None if thresholds is None else surviving,
        mean_confidence=round(float(np.mean(all_conf)) if all_conf else 0.0, 6),
        mean_geometric=round(float(np.mean(all_geom)) if all_geom else 0.0, 6),
        n_tied_at_gate=None if thresholds is None else tied,
    )


# --- V4 / H3 support: mirrored geometry, identical volume ------------------

def mirrored_pair(base: float = 100.0, leg: int = 8) -> Tuple[PlantedFrame, PlantedFrame]:
    """A bearish H&S top and its exact mirror, an inverse H&S, sharing one
    **constant** volume column.

    This is the fixture `FR-EM-V3` names: *"the same geometry mirrored, with
    the same flat breakout volume, must score lower bullish than bearish"*.

    Three things make it a fair test of the asymmetry and nothing else:

    * the bullish close series is ``2*base - bearish``, so the geometry is a
      reflection to the bit, and ``hl_pad`` is symmetric so high/low mirror too;
    * the volume column is **literally constant**, so ``rvol`` at every bar is
      exactly ``1.0`` and the comparison cannot turn on a noise draw;
    * both frames get the *same* array object's values, so there is no
      asymmetry anywhere except the one under test — the direction.
    """
    body = _piecewise_linear([
        (base, base + 10.0, leg + 1),
        (base + 10.0, base, leg + 1),
        (base, base + 18.0, leg + 1),
        (base + 18.0, base, leg + 1),
        (base, base + 10.0, leg + 1),
        (base + 10.0, base - 3.0, leg + 1),
    ])
    bearish_close = np.concatenate([_lead_in(base), body])
    bullish_close = 2.0 * base - bearish_close
    volume = np.full(bearish_close.size, BASE_VOLUME, dtype=float)

    return (
        PlantedFrame(
            "mirror_bearish", _frame(bearish_close, volume),
            "downside break on flat volume — expansion is corroboration only",
            "E&M Ch 7", "Head and Shoulders",
        ),
        PlantedFrame(
            "mirror_bullish", _frame(bullish_close, volume),
            "upside break on flat volume — expansion is required evidence",
            "E&M Ch 7", "Inverse Head and Shoulders",
        ),
    )


def with_burst_at(frame: pd.DataFrame, index: int, multiplier: float) -> pd.DataFrame:
    """Copy of ``frame`` with one bar's volume multiplied.

    Used to turn a flat-volume fixture into an expanding-volume one *at the
    bar the production locator actually picked*, so the reward tests aim at
    the real breakout event rather than a bar the test guessed at.
    """
    out = frame.copy(deep=True)
    volume = out["volume"].to_numpy(dtype=float).copy()
    volume[index] *= multiplier
    out["volume"] = volume
    return out


def single_match(frame: pd.DataFrame, pattern_name: str) -> PatternMatch:
    """The one detection named ``pattern_name``, or a clear assertion."""
    matches = [m for m in detect_all(frame) if m.pattern_name == pattern_name]
    assert len(matches) == 1, (
        f"expected exactly one {pattern_name!r}, got {[m.pattern_name for m in matches]}"
    )
    return matches[0]
