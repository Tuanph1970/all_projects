"""S-2 — FR-SCAN-BASE, FR-SCAN-SQUEEZE, FR-SCAN-MA, FR-SCAN-LEVEL.

What separates a stock that is RESTING from one that is merely trending.

Qullamaggie's setup is an advance, then a pause: *"cổ phiếu ngừng tăng và đi
ngang để hấp thụ lực chốt lời"*, with the range tightening (*"biên độ dao động
giá thu hẹp dần"*), volume drying up (*"khối lượng giao dịch kiệt quệ"*) and
MA10/MA20 catching up from below. S-1 finds names in a liquid uptrend; this
module decides whether they are coiled or already extended.

WHAT REJECTS AN EXTENDED NAME, since nothing here is called `is_extended`. A
stock that has just run hard cannot produce a qualifying base ending today: the
run makes the window's depth too large and its net drift too big, and both are
hard limits. The rejection is a consequence of what a base IS, not a separate
test bolted on — which matters because a separate test would need its own
threshold and would drift away from the base definition it was meant to mirror.

ON EC-S3 AND THE FLAG DETECTORS. The SRS says to reuse ai-insights'
`FlagDetector`/`PennantDetector` for the flag-shaped case and write only the
flat base. That reuse is NOT done here, deliberately: this service does not
import ai-insights code — it consumes that service's pattern payload over HTTP
and adapts it (`signal/failed_signal.py::adapt_ai_insights_patterns`), and
`tests/test_phase_k.py` skips wholesale when the package is not importable. A
nightly scan that made one HTTP call per symbol would also break the offline CLI
and the determinism harness. So the flat/consolidation base is implemented here
as pure local code, and the flag-shaped case is left as an injection seam for
S-3, where the service surface exists. Forking FlagDetector into this package
would have been the actual EC-S3 violation; not calling it yet is a sequencing
choice, recorded so it is not mistaken for an oversight.

Strictly causal (EC-S1): every function reads a bar sequence the caller has
already cut at the scan date, and the base always ENDS at the last bar.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

from app.services.backtest.market_features import atr_series
from app.services.scanner.trend import TrendClause, sma_at
from app.services.signal.base import OHLCVBar

#: "kéo dài từ vài tuần đến vài tháng" — a few weeks to a few months.
DEFAULT_BASE_MIN_BARS = 10
DEFAULT_BASE_MAX_BARS = 60

#: High-to-low of the consolidation, as a percent of its low. A range deeper
#: than this is a correction the stock is recovering from, not a pause inside an
#: advance — the distinction Qullamaggie draws between a base and a drawdown.
DEFAULT_BASE_MAX_DEPTH_PCT = 25.0

#: Net move from the base's first close to its last. "Đi ngang" means the stock
#: STOPPED going up: a window drifting +20% is still advancing and a window
#: drifting -20% is still falling. Symmetric, because both disqualify.
DEFAULT_BASE_MAX_DRIFT_PCT = 15.0

#: Net drift as a fraction of the window's own depth — and this is the test that
#: actually distinguishes a base from a trend.
#:
#: AN ABSOLUTE DRIFT LIMIT ALONE DOES NOT WORK, which a test caught rather than
#: review: drift shrinks with window length, so ANY persistent trend has some
#: window short enough to clear a fixed percentage. A stock rising 0.5/bar for
#: 300 bars produced a "45-bar base" at 14.9% drift — under the 15% limit and
#: not a base by any reading.
#:
#: Depth-relative drift is length-invariant and says what a base IS. Inside a
#: consolidation price oscillates and finishes near where it began, so the net
#: move is a small part of the range travelled. Inside a trend price marches
#: from one end of the range to the other and the two are nearly equal — that
#: 45-bar window scored 0.96. The default rejects anything above half.
DEFAULT_BASE_MAX_DRIFT_OVER_DEPTH = 0.5

#: Mean true range of the base's last third over its first third. Below 1.0 is
#: contraction; the default asks for a visible tightening, not merely non-expansion.
DEFAULT_SQUEEZE_MAX_RATIO = 0.75

#: Mean volume of the last third over the base's own mean. "Cạn cung."
DEFAULT_DRYUP_MAX_RATIO = 0.80

#: MA10/MA20 must sit BELOW price and within this much of it.
DEFAULT_MA_PROXIMITY_PCT = 8.0
MA_FAST = 10
MA_MEDIUM = 20


@dataclass(frozen=True)
class BaseWindow:
    """The consolidation, indexed against the bar sequence it was found in.
    `end_index` is always the last bar — a base that ended a month ago is
    history, not a setup."""
    start_index: int
    end_index: int
    length: int
    high: float
    low: float
    depth_pct: float
    drift_pct: float
    #: |drift| / depth. Near 0 is a true consolidation, near 1 is a trend
    #: wearing a base's clothes.
    drift_over_depth: float


@dataclass(frozen=True)
class SqueezeMetrics:
    """Reported as RATIOS, never as bare booleans. The number is what a reader
    compares between two candidates and what a later calibration needs; a
    hidden boolean throws that away and cannot be re-tuned after the fact."""
    range_ratio: Optional[float]
    volume_ratio: Optional[float]
    first_third_tr: Optional[float]
    last_third_tr: Optional[float]
    base_mean_volume: Optional[float]
    last_third_volume: Optional[float]


@dataclass(frozen=True)
class MAProximity:
    ma_fast: Optional[float]
    ma_medium: Optional[float]
    dist_fast_pct: Optional[float]     # (close - MA)/close, positive = MA below price
    dist_medium_pct: Optional[float]
    hugging: bool


@dataclass(frozen=True)
class Pivot:
    """The level a breakout clears (FR-SCAN-LEVEL). `distance_pct` of 0 means
    price is AT the pivot, which is the trigger rather than a disqualification."""
    level: float
    distance_pct: float
    distance_atr: Optional[float]


@dataclass(frozen=True)
class BaseAssessment:
    symbol: str
    passed: bool
    clauses: Tuple[TrendClause, ...]
    window: Optional[BaseWindow]
    squeeze: Optional[SqueezeMetrics]
    moving_averages: Optional[MAProximity]
    pivot: Optional[Pivot]

    def failed_clauses(self) -> Tuple[str, ...]:
        return tuple(c.name for c in self.clauses if not c.passed)


def true_ranges(bars: Sequence[OHLCVBar]) -> List[Optional[float]]:
    """TR aligned to `bars`; index 0 is None because it has no previous close.

    Not `atr_series`: that one smooths with Wilder's EMA across the WHOLE
    series, which would carry pre-base volatility into the base's first third
    and flatten exactly the contraction this module is looking for. The squeeze
    needs unsmoothed ranges confined to the window.
    """
    out: List[Optional[float]] = [None] * len(bars)
    for i in range(1, len(bars)):
        pc = bars[i - 1].close
        out[i] = max(bars[i].high - bars[i].low,
                     abs(bars[i].high - pc),
                     abs(bars[i].low - pc))
    return out


def detect_base(
    bars: Sequence[OHLCVBar],
    *,
    min_bars: int = DEFAULT_BASE_MIN_BARS,
    max_bars: int = DEFAULT_BASE_MAX_BARS,
    max_depth_pct: float = DEFAULT_BASE_MAX_DEPTH_PCT,
    max_drift_pct: float = DEFAULT_BASE_MAX_DRIFT_PCT,
    max_drift_over_depth: float = DEFAULT_BASE_MAX_DRIFT_OVER_DEPTH,
) -> Optional[BaseWindow]:
    """The FLATTEST admissible consolidation ending at the last bar, or None.

    Admissible = within `max_depth_pct`, `max_drift_pct` and
    `max_drift_over_depth`. Among those, the one with the lowest drift/depth
    wins; ties go to the LONGER window, because a longer base has absorbed more
    supply and that is the mechanism the setup rests on.

    WHY NOT SIMPLY THE LONGEST ADMISSIBLE WINDOW, which is what this did first.
    Because the longest admissible window is chosen by the THRESHOLD, not by the
    data. Greedily extending backwards stops exactly when a cap trips, so on a
    planted 30-bar base following a steady advance it returned 43 bars with a
    drift/depth of 0.49 — it had swallowed 13 bars of the run and halted on the
    0.50 cap. Three different fixture shapes all returned length 43 and a ratio
    of 0.49-0.50, which is the signature of a cap being measured rather than a
    pattern. The contamination then propagates: those run bars land in the
    squeeze's FIRST third, inflating it, so `range_ratio` reports a contraction
    the base did not have.

    Minimising drift/depth makes the boundary data-driven. The genuinely flat
    stretch scores near 0 and wins outright; windows reaching back into the
    advance score near its slope and lose. The caps stay as admissibility
    filters, but no longer choose the answer.
    """
    if min_bars < 3:
        raise ValueError(f"a base needs at least 3 bars to have thirds, got {min_bars}")
    if max_bars < min_bars:
        raise ValueError(f"max_bars {max_bars} is below min_bars {min_bars}")

    n = len(bars)
    best: Optional[BaseWindow] = None
    best_key: Optional[Tuple[float, int]] = None
    for length in range(min(max_bars, n), min_bars - 1, -1):
        window = bars[n - length:]
        high = max(float(b.high) for b in window)
        low = min(float(b.low) for b in window)
        if low <= 0:
            continue
        depth = (high / low - 1.0) * 100.0
        if depth > max_depth_pct:
            continue
        first_close = float(window[0].close)
        if first_close <= 0:
            continue
        drift = (float(window[-1].close) / first_close - 1.0) * 100.0
        if abs(drift) > max_drift_pct:
            continue
        # A depth of zero means a perfectly flat window: a base by definition,
        # and the ratio is 0 rather than 0/0.
        ratio = 0.0 if depth <= 0 else abs(drift) / depth
        if ratio > max_drift_over_depth:
            continue
        # Rounded so float noise cannot decide between two equally flat
        # windows; the length tie-break must be what settles those.
        key = (round(ratio, 9), -length)
        if best_key is None or key < best_key:
            best_key = key
            best = BaseWindow(
                start_index=n - length, end_index=n - 1, length=length,
                high=high, low=low, depth_pct=depth, drift_pct=drift,
                drift_over_depth=ratio,
            )
    return best


def measure_squeeze(bars: Sequence[OHLCVBar], window: BaseWindow) -> SqueezeMetrics:
    """Range contraction and volume dry-up across the base's thirds.

    The first third's TR needs the bar BEFORE the base to compute, so the ranges
    are taken over the full series and then sliced — still causal, since TR at
    `i` reads only `i` and `i-1`.
    """
    tr = true_ranges(bars)
    lo, hi = window.start_index, window.end_index + 1
    third = window.length // 3
    if third < 1:
        return SqueezeMetrics(None, None, None, None, None, None)

    def _mean(vals: Sequence[Optional[float]]) -> Optional[float]:
        clean = [v for v in vals if v is not None]
        return sum(clean) / len(clean) if clean else None

    first_tr = _mean(tr[lo:lo + third])
    last_tr = _mean(tr[hi - third:hi])
    vols = [float(b.volume) for b in bars[lo:hi]]
    base_vol = sum(vols) / len(vols) if vols else None
    last_vol = sum(vols[-third:]) / third if vols else None

    return SqueezeMetrics(
        range_ratio=(last_tr / first_tr) if (first_tr and last_tr is not None and first_tr > 0) else None,
        volume_ratio=(last_vol / base_vol) if (base_vol and last_vol is not None and base_vol > 0) else None,
        first_third_tr=first_tr,
        last_third_tr=last_tr,
        base_mean_volume=base_vol,
        last_third_volume=last_vol,
    )


def measure_ma_proximity(
    bars: Sequence[OHLCVBar],
    *,
    proximity_pct: float = DEFAULT_MA_PROXIMITY_PCT,
) -> MAProximity:
    """MA10/MA20 relative to the last close. Positive distance = MA below price."""
    close = float(bars[-1].close)
    fast = sma_at(bars, MA_FAST)
    medium = sma_at(bars, MA_MEDIUM)
    if close <= 0 or fast is None or medium is None:
        return MAProximity(fast, medium, None, None, False)
    d_fast = (close - fast) / close * 100.0
    d_medium = (close - medium) / close * 100.0
    hugging = 0.0 <= d_fast <= proximity_pct and 0.0 <= d_medium <= proximity_pct
    return MAProximity(fast, medium, d_fast, d_medium, hugging)


def find_pivot(bars: Sequence[OHLCVBar], window: BaseWindow) -> Pivot:
    """The base's upper boundary and how far price sits under it."""
    close = float(bars[-1].close)
    atr = atr_series(list(bars))
    latest_atr = atr[-1] if atr else None
    return Pivot(
        level=window.high,
        distance_pct=(window.high / close - 1.0) * 100.0 if close > 0 else 0.0,
        distance_atr=((window.high - close) / latest_atr) if latest_atr else None,
    )


def assess_base(
    symbol: str,
    bars: Sequence[OHLCVBar],
    *,
    min_bars: int = DEFAULT_BASE_MIN_BARS,
    max_bars: int = DEFAULT_BASE_MAX_BARS,
    max_depth_pct: float = DEFAULT_BASE_MAX_DEPTH_PCT,
    max_drift_pct: float = DEFAULT_BASE_MAX_DRIFT_PCT,
    max_drift_over_depth: float = DEFAULT_BASE_MAX_DRIFT_OVER_DEPTH,
    squeeze_max_ratio: float = DEFAULT_SQUEEZE_MAX_RATIO,
    dryup_max_ratio: float = DEFAULT_DRYUP_MAX_RATIO,
    ma_proximity_pct: float = DEFAULT_MA_PROXIMITY_PCT,
) -> BaseAssessment:
    """The S-2 verdict, with every clause reported pass or fail (NFR-S3)."""
    window = detect_base(
        bars, min_bars=min_bars, max_bars=max_bars,
        max_depth_pct=max_depth_pct, max_drift_pct=max_drift_pct,
        max_drift_over_depth=max_drift_over_depth,
    )
    if window is None:
        return BaseAssessment(
            symbol, False,
            (TrendClause("base_found", False,
                         f"no {min_bars}-{max_bars} bar window ending today is within "
                         f"{max_depth_pct:.0f}% deep, {max_drift_pct:.0f}% flat and "
                         f"drift/depth <= {max_drift_over_depth:.2f}"),),
            None, None, None, None,
        )

    squeeze = measure_squeeze(bars, window)
    mas = measure_ma_proximity(bars, proximity_pct=ma_proximity_pct)
    pivot = find_pivot(bars, window)

    clauses = [
        TrendClause("base_found", True,
                    f"{window.length} bars, {window.depth_pct:.1f}% deep, "
                    f"{window.drift_pct:+.1f}% drift (drift/depth {window.drift_over_depth:.2f})"),
        TrendClause(
            "range_contraction",
            squeeze.range_ratio is not None and squeeze.range_ratio <= squeeze_max_ratio,
            f"last third TR / first third TR = {squeeze.range_ratio:.2f}, need <= {squeeze_max_ratio:.2f}"
            if squeeze.range_ratio is not None else "range ratio not computable",
        ),
        TrendClause(
            "volume_dryup",
            squeeze.volume_ratio is not None and squeeze.volume_ratio <= dryup_max_ratio,
            f"last third volume / base mean = {squeeze.volume_ratio:.2f}, need <= {dryup_max_ratio:.2f}"
            if squeeze.volume_ratio is not None else "volume ratio not computable",
        ),
        TrendClause(
            "ma_hugging", mas.hugging,
            f"MA{MA_FAST} {mas.dist_fast_pct:+.1f}% / MA{MA_MEDIUM} {mas.dist_medium_pct:+.1f}% "
            f"below price, need both in 0..{ma_proximity_pct:.0f}%"
            if mas.dist_fast_pct is not None and mas.dist_medium_pct is not None
            else "moving averages not computable",
        ),
    ]
    return BaseAssessment(
        symbol=symbol,
        passed=all(c.passed for c in clauses),
        clauses=tuple(clauses),
        window=window,
        squeeze=squeeze,
        moving_averages=mas,
        pivot=pivot,
    )
