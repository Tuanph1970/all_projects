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
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

from app.services.patterns import (
    run_continuation_detectors,
    run_reversal_detectors,
    run_trap_detectors,
)
from app.services.patterns.base import PatternMatch
from app.services.patterns.volume import DEFAULT_BASELINE_WINDOW

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


def _hs_top(rng: np.random.Generator, leg: int = 8) -> PlantedFrame:
    """H&S top. Ch 7: heavy left shoulder, *decidedly lighter* right shoulder,
    and the break of the neckline is where activity picks up. Head volume is
    deliberately left unscripted — E&M say it is not a tell."""
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
    break_bar = off + 5 * leg
    volume = _scripted_volume(
        close.size,
        rng,
        ramps=[
            (off, ls_peak + 2, 1.6, 2.4),          # heavy left shoulder
            (rs_peak - leg, rs_peak + 2, 1.0, 0.55),  # decidedly lighter right
        ],
        bursts=[(break_bar, 2.8, 4)],              # pick-up on the break
    )
    return PlantedFrame(
        "hs_top", _frame(close, volume),
        "left shoulder heavy, right shoulder light, break on expansion",
        "E&M Ch 7", "Head and Shoulders",
    )


def _inv_hs(rng: np.random.Generator, leg: int = 8) -> PlantedFrame:
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
    break_bar = off + 5 * leg
    volume = _scripted_volume(
        close.size,
        rng,
        ramps=[(off + 3 * leg, break_bar, 0.8, 2.0)],   # builds into the break
        bursts=[(break_bar, 3.5, 5)],                   # the mandatory burst
    )
    return PlantedFrame(
        "inv_hs", _frame(close, volume),
        "volume builds through the right shoulder, burst on the upside break",
        "E&M Ch 7", "Inverse Head and Shoulders",
    )


def _double_top(rng: np.random.Generator, leg: int = 8) -> PlantedFrame:
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
        ],
        bursts=[(off + 4 * leg - 2, 2.2, 3)],
    )
    return PlantedFrame(
        "double_top", _frame(close, volume),
        "second top on lighter volume than the first",
        "E&M Ch 7", "Double Top",
    )


def _double_bottom(rng: np.random.Generator, leg: int = 8) -> PlantedFrame:
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
        ramps=[(second_low - leg, second_low + 1, 1.2, 0.5)],   # quiet retest
        bursts=[(off + 4 * leg - 2, 3.0, 4)],                   # confirming push
    )
    return PlantedFrame(
        "double_bottom", _frame(close, volume),
        "quiet second low, volume on the confirming advance",
        "E&M Ch 7", "Double Bottom",
    )


def _bull_flag(rng: np.random.Generator) -> PlantedFrame:
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
        ],
    )
    return PlantedFrame(
        "bull_flag", _frame(close, volume),
        "heavy pole, volume dries up through the flag",
        "E&M Ch 8, Ch 11", "Flag",
    )


def _symmetrical_triangle(rng: np.random.Generator, n_bars: int = 80) -> PlantedFrame:
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
        ramps=[(off, close.size, 2.2, 0.4)],
    )
    wobble = 1.0 + 0.25 * np.sin(2 * math.pi * np.arange(close.size) / 9.0)
    volume = np.maximum(np.round(volume * wobble), 1.0)
    return PlantedFrame(
        "symmetrical_triangle", _frame(close, volume),
        "volume diminishes irregularly toward the apex",
        "E&M Ch 8", "Symmetrical Triangle",
    )


def planted_frames(seed: int = 20261012) -> List[PlantedFrame]:
    """The planted set for `H1`, one frame per E&M volume condition.

    Seeded, so `H6` determinism is testable and a failure is reproducible.
    """
    rng = np.random.default_rng(seed)
    return [
        _hs_top(rng),
        _inv_hs(rng),
        _double_top(rng),
        _double_bottom(rng),
        _bull_flag(rng),
        _symmetrical_triangle(rng),
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
    """
    null_name: str
    volume_source: str
    n_surrogates: int
    length: int
    detections_per_surrogate: float
    detections_by_pattern: Dict[str, float]
    confidence_pct95_overall: float
    confidence_pct95_by_pattern: Dict[str, float]
    n_detections_total: int = 0
    n_surviving: Optional[int] = None
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
    all_conf: List[float] = []
    total = 0
    surviving = 0

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
            per_pattern_counts[match.pattern_name] = per_pattern_counts.get(match.pattern_name, 0) + 1
            per_pattern_conf.setdefault(match.pattern_name, []).append(float(match.confidence))
            all_conf.append(float(match.confidence))

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
        n_detections_total=total,
        n_surviving=None if thresholds is None else surviving,
    )
