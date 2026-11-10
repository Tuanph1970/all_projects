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

# ── Flag shape (lá cờ) ─────────────────────────────────────────────────────
#
# RELATIONSHIP TO ai-insights' FlagDetector, stated because EC-S3 forbids
# reinventing it. The parameters below MIRROR
# `ai-insights-service/app/services/patterns/continuation.py::FlagDetector`
# one for one, and the geometry test is the same test: a pole of
# `pole_min_atr_multiple x ATR` that is mostly linear, followed by a channel
# ending at the last bar whose highs AND lows both slope counter to the pole,
# retracing no more than `flag_max_retrace` of the pole.
#
# Why it is not called directly. decision-helper does not import ai-insights
# code — it consumes that service's pattern payload over HTTP and adapts it
# (`signal/failed_signal.py::adapt_ai_insights_patterns`), and
# `tests/test_phase_k.py` skips wholesale when the package is not importable. A
# nightly scan making one HTTP call per symbol would break the offline CLI and
# the VT-2 determinism harness, both of which must run with no services up.
#
# And the two answer different questions. FlagDetector returns a *pattern* for
# narration — confidence, measured-move target, pole bars — scored for a chart
# the user is reading. This returns a *base window* for a screen: boundaries the
# squeeze, MA-proximity and pivot stages then measure. Same geometry, different
# output, which is why `tests/test_scanner_base.py` cross-checks the two against
# the same planted series rather than letting them drift apart silently.
# If they ever disagree, the fix is to lift the geometry into `stock-common` the
# way `find_price_seams` was lifted — not to patch one side.
DEFAULT_FLAG_POLE_MIN_BARS = 4
DEFAULT_FLAG_POLE_MAX_BARS = 25
DEFAULT_FLAG_MIN_BARS = 3
DEFAULT_FLAG_MAX_BARS = 15
DEFAULT_FLAG_POLE_MIN_ATR_MULTIPLE = 2.0
DEFAULT_FLAG_MAX_RETRACE = 0.50
DEFAULT_FLAG_POLE_LINEARITY_MIN = 0.55

#: Base shapes. Qullamaggie names both: "nền phẳng (flat base) hoặc lá cờ (flag)".
SHAPE_FLAT = "FLAT"
SHAPE_FLAG = "FLAG"

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
    #: wearing a base's clothes. Gated for FLAT only — a flag is SUPPOSED to
    #: drift against its pole, which is the whole reason flags were invisible
    #: to the flat-base test.
    drift_over_depth: float
    shape: str = SHAPE_FLAT
    #: The pole this flag hangs off, as indices into the same bar sequence.
    #: None for FLAT — a flat base has no pole. Instrumentation for Backlog
    #: #141: the pole-relative squeeze and dry-up variants need the thrust the
    #: pause is being compared against, and re-deriving it in the study would
    #: be a second implementation of the search in `detect_flag_base`, free to
    #: drift from it. Carries no clause and gates nothing.
    pole_start_index: Optional[int] = None
    pole_end_index: Optional[int] = None


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


def _linreg_slope(values: Sequence[float]) -> float:
    """Least-squares slope over 0..n-1. Mirrors `continuation.py::_linreg`."""
    n = len(values)
    if n < 2:
        return 0.0
    xm = (n - 1) / 2.0
    ym = sum(values) / n
    ss = sum((i - xm) ** 2 for i in range(n))
    if ss == 0:
        return 0.0
    return sum((i - xm) * (v - ym) for i, v in enumerate(values)) / ss


def detect_flag_base(
    bars: Sequence[OHLCVBar],
    *,
    pole_min_bars: int = DEFAULT_FLAG_POLE_MIN_BARS,
    pole_max_bars: int = DEFAULT_FLAG_POLE_MAX_BARS,
    flag_min_bars: int = DEFAULT_FLAG_MIN_BARS,
    flag_max_bars: int = DEFAULT_FLAG_MAX_BARS,
    pole_min_atr_multiple: float = DEFAULT_FLAG_POLE_MIN_ATR_MULTIPLE,
    flag_max_retrace: float = DEFAULT_FLAG_MAX_RETRACE,
    pole_linearity_min: float = DEFAULT_FLAG_POLE_LINEARITY_MIN,
) -> Optional[BaseWindow]:
    """A BULL flag ending at the last bar — pole, then a tight pullback.

    BULL ONLY, deliberately. The scanner is a long-side discovery funnel; a bear
    flag is a real pattern and an irrelevant one here, and admitting it would put
    falling stocks on a list headed "candidates".

    Why the flat-base test cannot find these. `detect_base` requires
    drift/depth <= 0.5 — price must finish near where it began. A flag finishes
    DOWN, counter to its pole, by design: that is what the pullback is. So the
    very test that separates a base from a trend is the test that hides a flag,
    and a separate shape is the only honest way to cover both.

    The geometry mirrors ai-insights' `FlagDetector` (see the note by the
    constants above): a pole of at least `pole_min_atr_multiple x ATR` that is
    mostly linear rather than a zigzag, then a channel whose highs AND lows both
    slope down, retracing at most `flag_max_retrace` of the pole height.
    """
    if flag_min_bars < 3:
        raise ValueError(f"a flag needs at least 3 bars to have thirds, got {flag_min_bars}")

    n = len(bars)
    atr = atr_series(list(bars))

    # LONGEST FLAG FIRST — a second divergence from FlagDetector, and the same
    # reasoning as `detect_base`'s flattest-wins rule: a search order must not
    # pick the answer. Shortest-first reported a 3-bar flag for EVERY planted
    # pullback from 6 to 10 bars, because the last three bars of any pullback
    # satisfy the constraints once retrace is measured from the pole. The flag
    # IS the whole pullback, and its length feeds the squeeze thirds and the
    # pivot, so under-reporting it corrupts both.
    for flag_len in range(min(flag_max_bars, n - 1), flag_min_bars - 1, -1):
        flag_start = n - flag_len
        pole_end = flag_start - 1
        if pole_end < pole_min_bars - 1:
            break

        ref_atr = atr[pole_end] if pole_end < len(atr) and atr[pole_end] else None
        if not ref_atr:
            valid = [a for a in atr if a]
            ref_atr = (sum(valid) / len(valid)) if valid else None
        if not ref_atr or ref_atr <= 0:
            continue

        for pole_len in range(pole_min_bars, min(pole_max_bars + 1, pole_end + 1)):
            pole_start = pole_end - pole_len + 1
            pole_close = [float(b.close) for b in bars[pole_start: pole_end + 1]]
            pole_move = pole_close[-1] - pole_close[0]
            if pole_move <= 0:
                continue                      # bull only
            if pole_move < pole_min_atr_multiple * ref_atr:
                continue
            # THE POLE MUST END AT ITS OWN TOP. "Cây sào" is the move up to the
            # pause; a window that already turned down is not a pole, it is a
            # pole plus the start of the pullback.
            #
            # Without this the retrace cap is trivially evadable by SHORTENING
            # the flag: pole_end is pinned to flag_start - 1, so a shorter flag
            # pushes the pole window over the pullback's first bars, which both
            # lowers the measured peak and inflates pole_move. A 53%-retrace
            # pullback came back as a 3-bar flag off a 9-bar "pole" whose last
            # bar was already 3.2 below its own high.
            if pole_close[-1] < max(pole_close):
                continue
            # Linearity: the move must be mostly one-directional, not a zigzag
            # that happens to end higher.
            slope = _linreg_slope(pole_close)
            if abs(slope * (pole_len - 1)) < pole_linearity_min * pole_move:
                continue

            flag = bars[flag_start:]
            flag_highs = [float(b.high) for b in flag]
            if _linreg_slope(flag_highs) > 0:
                continue
            if _linreg_slope([float(b.low) for b in flag]) > 0:
                continue

            # THE FLAG'S HIGH MUST SIT IN ITS FIRST THIRD — i.e. the window
            # declines FROM its start. Without this, longest-first lets the flag
            # swallow the pole: a test planted 8 pole bars and a 4-bar pullback
            # and got back a 9-bar "flag" containing 5 pole bars, with the quiet
            # pre-pole drift reinterpreted as the pole. Both slope tests passed,
            # because a big fall after a big rise still regresses downward.
            #
            # This is the same failure as `detect_base`'s old longest-admissible
            # rule, in mirror image: a search order was picking the answer. A
            # pullback peaks where it begins, and that is the property to assert.
            if flag_highs.index(max(flag_highs)) > max(1, (flag_len - 1) // 3):
                continue
            # RETRACE IS MEASURED FROM THE POLE'S TOP, NOT WITHIN THE FLAG.
            #
            # This DIVERGES from FlagDetector, which uses
            # `abs(fg_close[-1] - fg_close[0])` — the move across the flag
            # window only. A test caught why that matters: because the flag must
            # end at the last bar and the search runs shortest-first, ANY
            # pullback however deep contains a shallow final 3-bar window, and a
            # long pole window reaching back over the pullback's first bars can
            # still net positive and pass linearity. A 66%-retrace pullback was
            # therefore admitted as a 3-bar flag.
            #
            # "Hồi không quá 50% cây sào" means measured from the top of the
            # pole, which is what this does. The divergence is deliberate and
            # the cross-check test asserts agreement on a clean planted flag
            # rather than identical thresholds in every corner.
            # Measured from the PEAK OF THE MOVE — the higher of the pole's
            # final close and the flag's own high. Neither alone is right:
            # measuring from the flag's high loses the first bar's drop off the
            # pole (a 53%-retrace pullback read as 47% and was admitted), and
            # measuring from the pole alone was what let the flag swallow the
            # pole before the first-third test above closed that off.
            peak = max(pole_close[-1], max(flag_highs))
            retrace = peak - float(flag[-1].close)
            if retrace > flag_max_retrace * pole_move:
                continue

            high = max(float(b.high) for b in flag)
            low = min(float(b.low) for b in flag)
            first_close = float(flag[0].close)
            if low <= 0 or first_close <= 0:
                continue
            depth = (high / low - 1.0) * 100.0
            drift = (float(flag[-1].close) / first_close - 1.0) * 100.0
            return BaseWindow(
                start_index=flag_start, end_index=n - 1, length=flag_len,
                high=high, low=low, depth_pct=depth, drift_pct=drift,
                drift_over_depth=(0.0 if depth <= 0 else abs(drift) / depth),
                shape=SHAPE_FLAG,
                pole_start_index=pole_start,
                pole_end_index=pole_end,
            )
    return None


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
    allow_flag: bool = True,
    squeeze_max_ratio: float = DEFAULT_SQUEEZE_MAX_RATIO,
    dryup_max_ratio: float = DEFAULT_DRYUP_MAX_RATIO,
    ma_proximity_pct: float = DEFAULT_MA_PROXIMITY_PCT,
) -> BaseAssessment:
    """The S-2 verdict, with every clause reported pass or fail (NFR-S3)."""
    # FLAT FIRST, FLAG ONLY AS A FALLBACK, and the order is load-bearing: a flat
    # base has absorbed supply across a longer sideways stretch, which is the
    # mechanism the setup rests on, while a flag is a brief pause inside a move.
    # Searching flag-first would reclassify existing flat bases as 3-bar flags
    # and quietly change every candidate the scanner already produced. Running it
    # second means flags can only ADD names, never alter or remove one — a
    # property `test_scanner_base.py` asserts rather than assumes.
    window = detect_base(
        bars, min_bars=min_bars, max_bars=max_bars,
        max_depth_pct=max_depth_pct, max_drift_pct=max_drift_pct,
        max_drift_over_depth=max_drift_over_depth,
    )
    if window is None and allow_flag:
        window = detect_flag_base(bars)
    if window is None:
        return BaseAssessment(
            symbol, False,
            (TrendClause("base_found", False,
                         f"no {min_bars}-{max_bars} bar window ending today is within "
                         f"{max_depth_pct:.0f}% deep, {max_drift_pct:.0f}% flat and "
                         f"drift/depth <= {max_drift_over_depth:.2f}"
                         + (", and no bull flag either" if allow_flag else "")),),
            None, None, None, None,
        )

    squeeze = measure_squeeze(bars, window)
    mas = measure_ma_proximity(bars, proximity_pct=ma_proximity_pct)
    pivot = find_pivot(bars, window)

    clauses = [
        TrendClause("base_found", True,
                    f"{window.shape} {window.length} bars, {window.depth_pct:.1f}% deep, "
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
