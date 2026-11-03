"""Backlog #118 — the pieces a chart narrator needs that nothing else here computes.

WHAT THIS MODULE IS *NOT*. It is not a second indicator library. `analysis_service`
already computes RSI, MACD, Bollinger, SMA 20/50/200, EMA, ATR, Stochastic, OBV,
Fibonacci, swing pivots, support/resistance (with touches, breaks, volume strength,
age decay and role reversal) and a TREND/RANGE regime with ADX. #118 narrates
*those*; re-deriving them here would create two answers to the same question. This
module holds only the four things the narrator needs and the codebase genuinely
lacked, each checked against `docs/srs_gap_analysis.md` conventions:

  1. `find_corporate_action_gaps` — the honesty gate (Backlog #119).
  2. `detect_candles`            — Doji / Hammer / Shooting Star / Engulfing.
  3. `detect_rsi_divergence`     — price and momentum disagreeing.
  4. `price_channel`             — the two rails, fitted to swing pivots.

EVERY FUNCTION IS PURE and takes a DataFrame. No HTTP, no session, no settings. That
is deliberate: the narrator's correctness is the whole feature, and a pure function
can be driven over adversarial inputs in a unit test without a broker, a database or
a live market. `analysis_service` does the I/O and passes bars in.

OUTPUT IS A CODE PLUS NUMBERS, NEVER A SENTENCE. The app ships English and
Vietnamese (`en.json`/`vi.json`) and the owner's requirements for #118 were written
in Vietnamese. If this module returned prose it would have to pick a language, and
the other locale would silently get the wrong one. So each finding carries an i18n
`code` and the `params` the template needs, and the frontend renders it. The
consequence worth stating: a new finding is not user-visible until BOTH locales have
a string for its code, and `test_narrative.py` asserts exactly that.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

import numpy as np
import pandas as pd

from stock_common.analytics.corporate_actions import (
    MAX_BELIEVABLE_DAILY_MOVE_PCT as _SHARED_MAX_MOVE_PCT,
    find_price_seams,
)

# ---------------------------------------------------------------------------
# Finding
# ---------------------------------------------------------------------------

#: A reading the narrator can state. `severity` is the *direction of the
#: evidence*, not a recommendation: "bearish" means this particular reading
#: leans down, and the strategy section is what weighs them against each other.
SEVERITIES = ("info", "bullish", "bearish", "warning")


@dataclass(frozen=True)
class Finding:
    code: str
    params: Dict[str, Any] = field(default_factory=dict)
    severity: str = "info"

    def __post_init__(self) -> None:
        if self.severity not in SEVERITIES:
            raise ValueError(f"unknown severity {self.severity!r}")

    def as_dict(self) -> Dict[str, Any]:
        return {"code": self.code, "params": dict(self.params), "severity": self.severity}


# ---------------------------------------------------------------------------
# 1. The honesty gate (Backlog #119)
# ---------------------------------------------------------------------------

#: Re-exported from the shared detector so the #118 narrator and the
#: stock-data-service repair path cannot disagree about what counts as an
#: impossible move. See stock_common.analytics.corporate_actions for the
#: reasoning and the measured VN board limits.
MAX_BELIEVABLE_DAILY_MOVE_PCT = _SHARED_MAX_MOVE_PCT


def find_corporate_action_gaps(
    ohlc: pd.DataFrame,
    *,
    max_move_pct: float = MAX_BELIEVABLE_DAILY_MOVE_PCT,
) -> List[Dict[str, Any]]:
    """Overnight moves too large to have been trading (Backlog #119).

    A thin DataFrame adapter over `stock_common.analytics.find_price_seams`.
    The detection logic lives in stock-common because TWO services need it and
    they must agree: analysis-service narrates the seam, stock-data-service
    repairs it. A second local copy is how the two drift.

    WHAT THE SEAM ACTUALLY IS, since it changes what the narrator should say.
    The stored TCB series falls -33.8% overnight on 2026-10-27, which no VN
    board permits. But vnstock/VCI returns a CONTINUOUS series across that date
    -- the provider restates the whole prior history on a share-count event.
    The discontinuity is our own ingestion: `_top_up_prices` appends only bars
    after the last stored date, so restated history never lands on rows already
    held. So this is a DATA FAULT we introduced, not an unadjusted provider
    feed, and the fix is to re-pull the symbol rather than to compute a local
    adjustment.

    Returns dicts (not PriceSeam) because the narrator's params go straight out
    as JSON.
    """
    closes = _column(ohlc, "close")
    if closes is None or len(closes) < 2:
        return []
    seams = find_price_seams(
        closes.tolist(), _dates(ohlc), max_move_pct=max_move_pct)
    return [s.as_dict() for s in seams]


def gap_findings(gaps: Sequence[Dict[str, Any]]) -> List[Finding]:
    """The gate as a narrator finding. Severity is `warning`, never directional.

    A corporate-action gap is NOT bearish. Calling a -34% stock dividend
    "bearish" is the exact error this gate exists to prevent, so it must not be
    reintroduced by the severity field.
    """
    if not gaps:
        return []
    worst = max(gaps, key=lambda g: abs(g["move_pct"]))
    return [Finding(
        code="narrative.data.corporate_action_gap",
        params={
            "count": len(gaps),
            "date": worst["date"],
            "move_pct": worst["move_pct"],
            "prev_close": worst["prev_close"],
            "close": worst["close"],
            "ratio": worst["ratio"],
        },
        severity="warning",
    )]


# ---------------------------------------------------------------------------
# 2. Candlestick reversals
# ---------------------------------------------------------------------------

#: A body this small relative to the session's range is "no decision" — the
#: classical Doji. 10% is the common textbook figure.
DOJI_BODY_RATIO = 0.10
#: A hammer's lower shadow must dominate its body this many times over.
HAMMER_SHADOW_RATIO = 2.0
#: ...and its upper shadow must be no more than this share of the range, or the
#: candle is a spinning top rather than a hammer.
HAMMER_UPPER_MAX_RATIO = 0.25


def detect_candles(ohlc: pd.DataFrame, *, lookback: int = 3) -> List[Finding]:
    """Single- and two-bar reversal candles on the most recent `lookback` bars.

    Scoped to the right edge on purpose. A Hammer forty bars ago is history, not
    a signal, and listing every candle in the window would bury the one that
    matters. The bar's position is reported so the reader knows whether it is
    today's candle or last week's.

    CONTEXT IS NOT CHECKED HERE. Edwards & Magee are explicit that a Hammer only
    means reversal after a decline, and Engulfing only after a move the other
    way. That context lives in the trend section the narrator already has, so
    this returns the *shape* and the narrator combines it. Returning "Hammer
    (bullish)" with no decline behind it would be the vacuous version.
    """
    need = ("open", "high", "low", "close")
    cols = {c: _column(ohlc, c) for c in need}
    if any(v is None for v in cols.values()) or len(ohlc) < 2:
        return []

    o, h, l, c = (cols[k].to_numpy(dtype=float) for k in need)
    n = len(c)
    out: List[Finding] = []
    dates = _dates(ohlc)
    start = max(1, n - max(1, int(lookback)))

    for i in range(start, n):
        if not all(np.isfinite(x) for x in (o[i], h[i], l[i], c[i])):
            continue
        rng = h[i] - l[i]
        if rng <= 0:
            continue  # a limit-locked or untraded bar has no shape to read
        body = abs(c[i] - o[i])
        upper = h[i] - max(o[i], c[i])
        lower = min(o[i], c[i]) - l[i]
        ago = n - 1 - i
        base = {"date": dates[i], "bars_ago": ago}

        # ORDER MATTERS, and getting it wrong is silent. The first version of
        # this chain tested Doji first, and every hammer vanished: a hammer's
        # body is SMALL BY DEFINITION, so 0.5 on a 5.2 range is 9.6% and lands
        # inside the 10% Doji threshold. The narrator would have been incapable
        # of ever saying "hammer", with no error anywhere to show it.
        #
        # The classical distinction is not body size but SHADOW SYMMETRY. A
        # small body with one dominant shadow is a hammer or shooting star (the
        # dragonfly and gravestone forms), and both carry direction. A plain
        # Doji is a small body with BALANCED shadows and carries only
        # indecision. So the directional shapes are tested first and the Doji
        # catches what is left.
        if lower >= HAMMER_SHADOW_RATIO * body and upper <= HAMMER_UPPER_MAX_RATIO * rng:
            out.append(Finding("narrative.candle.hammer", base, "bullish"))
        elif upper >= HAMMER_SHADOW_RATIO * body and lower <= HAMMER_UPPER_MAX_RATIO * rng:
            out.append(Finding("narrative.candle.shooting_star", base, "bearish"))
        elif body / rng <= DOJI_BODY_RATIO:
            out.append(Finding("narrative.candle.doji", base, "info"))

        # Two-bar engulfing. Compared on the BODIES (open..close), which is the
        # classical definition; comparing high/low instead would be an "outside
        # bar" and is a different pattern.
        po, pc = o[i - 1], c[i - 1]
        if all(np.isfinite(x) for x in (po, pc)) and abs(pc - po) > 0:
            prev_down, prev_up = pc < po, pc > po
            cur_up, cur_down = c[i] > o[i], c[i] < o[i]
            if prev_down and cur_up and o[i] <= pc and c[i] >= po:
                out.append(Finding("narrative.candle.bullish_engulfing", base, "bullish"))
            elif prev_up and cur_down and o[i] >= pc and c[i] <= po:
                out.append(Finding("narrative.candle.bearish_engulfing", base, "bearish"))
    return out


# ---------------------------------------------------------------------------
# 3. RSI divergence
# ---------------------------------------------------------------------------

def detect_rsi_divergence(
    ohlc: pd.DataFrame,
    rsi: Sequence[float],
    *,
    window: int = 5,
    min_separation: int = 5,
    max_lookback: int = 60,
) -> List[Finding]:
    """Price and momentum disagreeing at consecutive swings.

    Bearish: price prints a HIGHER high while RSI prints a LOWER high — the move
    is being made on less force than the one before it. Bullish is the mirror.

    `rsi` must be the per-bar RSI series aligned to `ohlc` (same length, same
    order). A misaligned series would silently compare a price pivot to an
    unrelated momentum reading, so the length is checked rather than trusted.

    `min_separation` keeps the two pivots from being the same swing seen twice,
    and `max_lookback` keeps a divergence from a quarter ago out of today's
    narration.
    """
    highs, lows = _column(ohlc, "high"), _column(ohlc, "low")
    if highs is None or lows is None:
        return []
    r = np.asarray(list(rsi), dtype=float)
    if len(r) != len(ohlc) or len(ohlc) < 2 * max(1, int(window)) + 2:
        return []

    hv, lv = highs.to_numpy(dtype=float), lows.to_numpy(dtype=float)
    dates = _dates(ohlc)
    n = len(hv)
    lo_bound = max(0, n - max_lookback)
    out: List[Finding] = []

    def _pivots(values: np.ndarray, kind: str) -> List[int]:
        idx = []
        w = max(1, int(window))
        for i in range(w, len(values) - w):
            if i < lo_bound or not np.isfinite(values[i]):
                continue
            seg = values[i - w:i + w + 1]
            if not np.all(np.isfinite(seg)):
                continue
            if kind == "high" and values[i] == seg.max() and values[i] > seg.min():
                idx.append(i)
            elif kind == "low" and values[i] == seg.min() and values[i] < seg.max():
                idx.append(i)
        return idx

    for kind, prices, code, sev in (
        ("high", hv, "narrative.divergence.bearish_rsi", "bearish"),
        ("low", lv, "narrative.divergence.bullish_rsi", "bullish"),
    ):
        piv = _pivots(prices, kind)
        if len(piv) < 2:
            continue
        b = piv[-1]
        # Walk backwards for the most recent pivot far enough away to be a
        # different swing.
        a = next((p for p in reversed(piv[:-1]) if b - p >= min_separation), None)
        if a is None or not (np.isfinite(r[a]) and np.isfinite(r[b])):
            continue
        higher_price = prices[b] > prices[a]
        lower_rsi = r[b] < r[a]
        diverging = (higher_price and lower_rsi) if kind == "high" else (
            prices[b] < prices[a] and r[b] > r[a])
        if diverging:
            out.append(Finding(code, {
                "from_date": dates[a], "to_date": dates[b],
                "from_price": round(float(prices[a]), 2),
                "to_price": round(float(prices[b]), 2),
                "from_rsi": round(float(r[a]), 1),
                "to_rsi": round(float(r[b]), 1),
                "bars_ago": n - 1 - b,
            }, sev))
    return out


# ---------------------------------------------------------------------------
# 4. Price channel
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Channel:
    upper_now: float
    lower_now: float
    upper_slope: float
    lower_slope: float
    position_pct: float   # 0 = on the lower rail, 100 = on the upper rail
    pivots_used: int

    def as_dict(self) -> Dict[str, Any]:
        return {
            "upper_now": round(self.upper_now, 2),
            "lower_now": round(self.lower_now, 2),
            "upper_slope": round(self.upper_slope, 4),
            "lower_slope": round(self.lower_slope, 4),
            "position_pct": round(self.position_pct, 1),
            "pivots_used": self.pivots_used,
        }


def price_channel(
    ohlc: pd.DataFrame,
    *,
    window: int = 5,
    min_pivots: int = 2,
) -> Optional[Channel]:
    """Two rails fitted by least squares through swing highs and swing lows.

    Returns None — rather than a straight line through one point — when either
    rail has fewer than `min_pivots` swings. A "channel" drawn through a single
    high is a number with no evidence behind it, and the narrator must be able to
    say nothing. That is why `min_pivots` cannot be 1.
    """
    highs, lows = _column(ohlc, "high"), _column(ohlc, "low")
    if highs is None or lows is None or len(ohlc) < 2 * window + 1:
        return None
    hv, lv = highs.to_numpy(dtype=float), lows.to_numpy(dtype=float)
    n = len(hv)

    def _swings(values: np.ndarray, kind: str) -> List[int]:
        idx = []
        for i in range(window, n - window):
            seg = values[i - window:i + window + 1]
            if not np.all(np.isfinite(seg)):
                continue
            if kind == "high" and values[i] == seg.max() and values[i] > seg.min():
                idx.append(i)
            elif kind == "low" and values[i] == seg.min() and values[i] < seg.max():
                idx.append(i)
        return idx

    hi_idx, lo_idx = _swings(hv, "high"), _swings(lv, "low")
    if len(hi_idx) < min_pivots or len(lo_idx) < min_pivots:
        return None

    def _fit(idx: List[int], values: np.ndarray) -> tuple[float, float]:
        slope, intercept = np.polyfit(np.asarray(idx, dtype=float),
                                      values[idx].astype(float), 1)
        return float(slope), float(intercept)

    us, ui = _fit(hi_idx, hv)
    ls, li = _fit(lo_idx, lv)
    x = float(n - 1)
    upper, lower = us * x + ui, ls * x + li
    if not (np.isfinite(upper) and np.isfinite(lower)):
        return None

    closes = _column(ohlc, "close")
    last = float(closes.to_numpy(dtype=float)[-1]) if closes is not None else np.nan
    width = upper - lower
    # The rails can cross (a wedge). Position is then meaningless rather than
    # huge, so it is clamped and the caller still sees the two rails.
    pos = 50.0 if width <= 0 or not np.isfinite(last) else \
        max(0.0, min(100.0, (last - lower) / width * 100.0))

    return Channel(upper_now=upper, lower_now=lower, upper_slope=us,
                   lower_slope=ls, position_pct=pos,
                   pivots_used=len(hi_idx) + len(lo_idx))


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _column(df: pd.DataFrame, name: str) -> Optional[pd.Series]:
    if df is None or not isinstance(df, pd.DataFrame) or name not in df.columns:
        return None
    try:
        return pd.to_numeric(df[name], errors="coerce")
    except (TypeError, ValueError):
        return None


def _dates(df: pd.DataFrame) -> List[Optional[str]]:
    """ISO date strings, or None where absent. Never raises on a missing column."""
    if "date" not in getattr(df, "columns", ()):
        return [None] * len(df)
    out: List[Optional[str]] = []
    for v in df["date"].tolist():
        try:
            out.append(pd.Timestamp(v).date().isoformat())
        except (TypeError, ValueError):
            out.append(None)
    return out


# ---------------------------------------------------------------------------
# 5. Chart patterns, read from chart-decomp-service (Backlog #118)
# ---------------------------------------------------------------------------

#: Percentile of the random-walk null a detection's score must exceed before
#: chart-decomp calls it `noteworthy` (FR-FPR-2, NullFPRParams.noteworthy_pct).
#: Duplicated here only to STATE it in the narration; the flag itself always
#: comes from the service, never recomputed.
NOTEWORTHY_PERCENTILE = 95.0

#: Fallback recency window for direct callers. `get_narrative` overrides it
#: with THE LENGTH OF THE DISPLAYED CHART, which is the principled rule: the
#: text describes what the reader can see, exactly as the named S/R levels do.
#:
#: This default was the whole window at first and that was measurably wrong.
#: On real FPT bars the pattern service returned six formations and the most
#: recent ended 106 bars (about five months) back -- narrating those beside
#: today's RSI invites them to be read as live signals. But a fixed 60 is just
#: as arbitrary in the other direction: it would hide a formation plainly
#: visible on a 180-bar chart. Tying it to the display resolves both.
PATTERN_RECENT_BARS = 60

#: Conventional direction per pattern. THIS MAPPING IS OURS, not the detector's
#: -- chart-decomp reports the SHAPE and (at multi-scale) a `directional_bias`,
#: and where it supplies one we use it. The fallback below is the standard
#: Edwards & Magee reading, and a symmetric triangle is deliberately neutral
#: because the book is explicit that it resolves either way.
PATTERN_DIRECTION = {
    "Head & Shoulders": "bearish",
    "Inverse Head & Shoulders": "bullish",
    "Double Top": "bearish",
    "Double Bottom": "bullish",
    "Bear Flag": "bearish",
    "Bull Flag": "bullish",
    "Bear Pennant": "bearish",
    "Bull Pennant": "bullish",
    "Ascending Triangle": "bullish",
    "Descending Triangle": "bearish",
    "Symmetric Triangle": "info",
}


def pattern_direction(name: str, reported_bias: Optional[str] = None) -> str:
    """Severity for a pattern: the service's bias if it gave one, else the map."""
    if reported_bias:
        b = str(reported_bias).strip().lower()
        if b in ("bullish", "bearish"):
            return b
        if b in ("neutral", "none", "info"):
            return "info"
    return PATTERN_DIRECTION.get(name, "info")


def chart_pattern_findings(
    detections: Sequence[Dict[str, Any]],
    fpr_by_pattern: Optional[Dict[str, float]] = None,
    *,
    bars_total: int,
    recent_bars: int = PATTERN_RECENT_BARS,
) -> List[Finding]:
    """Narrate chart patterns ONLY as strongly as the null benchmark allows.

    This is the part of #118 most likely to mislead, so it is the part most
    constrained. `chart-decomp-service` detects eleven shapes and, when asked
    for the C4 null benchmark, reports two numbers that matter far more than
    the detection itself:

      * `noteworthy` -- whether the score beat the 95th percentile of scores
        the SAME detector produces on random walks of the same length and
        volatility;
      * `fpr_by_pattern` -- detections per random-walk series. Note this is a
        RATE, not a probability: measured on FPT it was 1.25 for Descending
        Triangle, meaning an average coin-flip chart contains more than one.

    Measured on real FPT bars, six patterns were detected and NOT ONE was
    noteworthy -- Head & Shoulders scored at the 6.1st percentile of the null.
    Announcing "Head & Shoulders detected" on that evidence is exactly the
    fluent-invention failure this feature avoids by not using an LLM, so:

      * a noteworthy pattern is narrated as a finding with its direction;
      * patterns that are NOT noteworthy produce ONE finding saying shapes are
        present but no stronger than chance -- never a list that reads like
        signals;
      * with no null benchmark available, patterns are reported as UNVALIDATED
        rather than silently promoted to signals.
    """
    rows = [d for d in (detections or []) if isinstance(d, dict)]
    if not rows:
        return [Finding("narrative.pattern.none", {}, "info")]

    cutoff = max(0, int(bars_total) - max(1, int(recent_bars)))
    recent = [d for d in rows if int(d.get("end_index") or 0) >= cutoff]
    if not recent:
        return [Finding("narrative.pattern.none_recent", {
            "count": len(rows), "recent_bars": int(recent_bars)}, "info")]

    rates = fpr_by_pattern or {}
    graded = [d for d in recent if d.get("noteworthy") is not None]
    if not graded:
        names = sorted({str(d.get("pattern")) for d in recent})
        return [Finding("narrative.pattern.unvalidated", {
            "count": len(recent), "names": ", ".join(names)}, "warning")]

    out: List[Finding] = []
    noteworthy = [d for d in graded if d.get("noteworthy")]
    for d in sorted(noteworthy, key=lambda x: -(x.get("score") or 0.0)):
        name = str(d.get("pattern"))
        out.append(Finding("narrative.pattern.noteworthy", {
            "name": name,
            "score": round(float(d.get("score") or 0.0), 2),
            "percentile": round(float(d.get("null_percentile") or 0.0), 1),
            "threshold": NOTEWORTHY_PERCENTILE,
            "expected_in_noise": round(float(rates.get(name, 0.0)), 2),
            "bars_ago": max(0, int(bars_total) - 1 - int(d.get("end_index") or 0)),
        }, pattern_direction(name, d.get("directional_bias"))))

    unremarkable = [d for d in graded if not d.get("noteworthy")]
    if unremarkable:
        best = max(unremarkable, key=lambda x: float(x.get("null_percentile") or 0.0))
        names = sorted({str(d.get("pattern")) for d in unremarkable})
        out.append(Finding("narrative.pattern.not_noteworthy", {
            "count": len(unremarkable),
            "names": ", ".join(names),
            "best_name": str(best.get("pattern")),
            "best_percentile": round(float(best.get("null_percentile") or 0.0), 1),
            "threshold": NOTEWORTHY_PERCENTILE,
            "expected_in_noise": round(float(rates.get(str(best.get("pattern")), 0.0)), 2),
        }, "info"))
    return out
