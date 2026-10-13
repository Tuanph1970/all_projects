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
from typing import Any, Callable, Dict, List, Optional, Sequence

# --- Defaults ---------------------------------------------------------------
# Every number here is a *default pending the S2 sweep* (FR-EM-V11), never a
# trusted constant and never a test assertion. E&M's own figures come from
# 1940s-60s NYSE issues.

# SWEPT at S2 (FR-EM-V11), not inherited. 100 beat 50 on H1 separation on
# 12/12 independent shuffle seeds (+0.0135 +/- 0.0080 paired), beat it on the
# textbook-vs-adverse gap, and gave the most balanced verdict distribution on
# 18 real symbols. Availability is unaffected: `_baseline_from` degrades to
# whatever history exists above MIN_BASELINE_BARS, so 100% of detections still
# score even at the 100-bar lookback the UI requests. It is also the better
# reading of E&M's "high for that stock in that period" — ~5 months rather
# than ~2.5. Evidence: docs/em1_s2_parameter_sweep.md.
DEFAULT_BASELINE_WINDOW = 100  # trailing bars behind the bar being judged

#: The SECOND, much longer baseline (`FR-EM-V5` row 11, SRS open question 3).
#: Ch 10.1's One-Day Reversal requires "volume exceeding anything for months",
#: which is not a statement about the last fifty bars. ~120 trading bars is
#: roughly six months on a VN daily series.
LONG_BASELINE_WINDOW = 120

#: Compared against a high **percentile** of that long window rather than its
#: maximum. "Anything for months" reads as a maximum, but `EC-V5` requires
#: robustness to one absurd vendor print, and a maximum would let a single bad
#: row suppress every one-day reversal behind it — permanently and silently.
#: The 98th percentile of 120 bars is the second or third heaviest bar: the
#: same statement in substance, bounded against one bad row. `S2` sweeps it.
LONG_BASELINE_PERCENTILE = 98.0

#: `rvol` at or above which a gap's volume counts as "extraordinary" for the
#: purposes of Ch 12's exhaustion test. A default pending the S2 sweep.
GAP_EXHAUSTION_RVOL = 3.0

#: How much of the gap the following bars must carry before the advance counts
#: as "commensurate". Below this, with extraordinary volume, the gap is an
#: exhaustion gap rather than a runaway.
GAP_FOLLOW_THROUGH_FRACTION = 0.5
MIN_BASELINE_BARS = 10         # below this there is no usable baseline (EC-V4)
MAX_WIDEN_FACTOR = 4           # how far back EC-V2 may widen past a dead window
MIN_TREND_BARS = 4             # below this a direction verdict is meaningless

# Factor bounds (FR-EM-V7). Deliberately asymmetric: E&M's volume evidence is
# better at discrediting a formation than at promoting one, so the floor sits
# further from neutral than the ceiling. V4 composes with these.
# SWEPT at S2. Tightening the floor to 0.4 buys more noise suppression
# (-15.2% vs -11.7% on H2) but lets volume cut a confidence by 60%, which is
# more authority than "volume is corroboration, not the finding" allows.
# Raising the ceiling actively HURTS suppression (1.30 -> -9.9%) by upgrading
# noise. (0.5, 1.15) is kept as the balance, now with evidence rather than as
# a guess. Evidence: docs/em1_s2_parameter_sweep.md.
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
    #: `FR-EM-V5` row 10: the one case where volume changes a pattern's
    #: **label** rather than only its score. ``None`` everywhere else.
    reclassify_to: Optional[str] = None

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


def _percentile(values: Sequence[float], percentile: float) -> float:
    """Linear-interpolated percentile, computed without numpy so this module
    stays a plain-Python primitive layer like the rest of its helpers."""
    ordered = sorted(values)
    if not ordered:
        return 0.0
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * min(100.0, max(0.0, percentile)) / 100.0
    low = int(math.floor(position))
    high = min(len(ordered) - 1, low + 1)
    weight = position - low
    return ordered[low] * (1.0 - weight) + ordered[high] * weight


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


# --- V4: the asymmetry rule (FR-EM-V3) --------------------------------------

@dataclass(frozen=True)
class BreakoutRule:
    """`FR-EM-V3` encoded as **data**, one instance per direction.

    The SRS calls the asymmetry *"the single most important requirement in this
    document, and the one a naive 'volume confirms everything' implementation
    gets wrong"*. Edwards & Magee, Ch 7:

        "It takes buying to put stocks up, but they can fall of their own
        weight."

    So an upside break **requires** expansion and is penalised without it,
    while a downside break treats expansion as optional corroboration and is
    **not** penalised by its absence.

    It is a rule object rather than a branch inside each detector for one
    concrete reason: `FR-EM-V5` requires that the inverse head-and-shoulders
    **not** reuse the top's rule inverted, and that the H&S bottom carry the
    strongest penalty in the set. Those are new *instances* of this class
    (task V5), not new conditionals — and `FR-EM-V4`'s non-monotone case,
    where more volume scores *lower* on a downside triangle break, extends the
    same object (task V6). A branch per detector is how the inversion silently
    becomes a sign error later.

    Fields
    ------
    confirm_rvol    : the `rvol` at or above which volume counts as expansion.
    confirm_reward  : score credit when it is met, in ``[0, 0.5]``.
    dull_penalty    : score debit when expansion is required and absent, in
                      ``[0, 0.5]``. Exactly ``0.0`` is what "absence SHALL NOT
                      penalise" means, and it is asserted as such.

    Every number is a default pending the `S2` sweep (`FR-EM-V11`), never a
    constant from the book treated as truth.
    """
    direction: str
    expansion_required: bool
    confirm_rvol: float = 1.5
    confirm_reward: float = 0.5
    dull_penalty: float = 0.5
    #: `FR-EM-V4`: the rvol at or above which *more* volume makes the break
    #: WORSE, not better — E&M Ch 8's shakeout. ``None`` means the rule is
    #: monotone, which every rule before V6a was.
    suspect_above_rvol: Optional[float] = None
    suspect_penalty: float = 0.5

    def __post_init__(self) -> None:
        if self.expansion_required and self.dull_penalty <= 0.0:
            raise ValueError("a rule requiring expansion must penalise its absence")
        if not self.expansion_required and self.dull_penalty != 0.0:
            raise ValueError(
                "FR-EM-V3: where expansion is only corroborating, its absence "
                "must not penalise — dull_penalty must be exactly 0.0"
            )
        if self.suspect_above_rvol is not None:
            if self.suspect_above_rvol <= self.confirm_rvol:
                raise ValueError(
                    "FR-EM-V4: the suspect threshold must sit ABOVE the confirming "
                    "one, or there is no corroborating band between them and the "
                    "rule is monotone after all"
                )
            if self.suspect_penalty <= 0.0:
                raise ValueError("a suspect band with no penalty is not a suspect band")


#: Upside break — E&M's "it takes buying to put stocks up". The default for
#: any bullish pattern without a condition of its own. Its penalty is
#: deliberately *not* the maximum: `FR-EM-V5` reserves the strongest penalty in
#: the set for the head-and-shoulders bottom (`INVERSE_HS_BREAKOUT`, task V5),
#: which is the one case E&M state as near-absolute.
BULLISH_BREAKOUT = BreakoutRule(
    direction="bullish", expansion_required=True, confirm_reward=0.5, dull_penalty=0.4
)

#: Downside break — "they can fall of their own weight". Corroboration is
#: worth less than required evidence being met, hence the smaller reward, and
#: its absence costs nothing at all.
BEARISH_BREAKOUT = BreakoutRule(
    direction="bearish", expansion_required=False, confirm_reward=0.3, dull_penalty=0.0
)

BREAKOUT_RULES: Dict[str, BreakoutRule] = {
    "bullish": BULLISH_BREAKOUT,
    "bearish": BEARISH_BREAKOUT,
}

#: The user-facing vocabulary for a verdict (`FR-EM-V9` renders these).
#: ``suspect`` is `FR-EM-V4`'s non-monotone case and is produced from task V6.
VERDICT_CONFIRMS = "confirms"
VERDICT_NEUTRAL = "neutral"
VERDICT_CONTRADICTS = "contradicts"
VERDICT_SUSPECT = "suspect"


def _graded_score(
    margin: float, *, required: bool, reward: float = 0.5, penalty: float = 0.5
) -> float:
    """The one scoring shape every condition in this module uses.

    ``margin`` is the condition's satisfaction, normalised: ``>= 0`` means met,
    by that relative amount, saturating at ``1.0``; negative means unmet, by
    that relative shortfall.

    Met conditions earn half their reward at the threshold and the rest as the
    margin grows, so a verdict is graded rather than a step — a step cannot be
    swept (`FR-EM-V11`) and would let a near-constant satisfy `H1`. Unmet
    conditions cost nothing unless they were **required**, which is exactly the
    "required / corroborating" vocabulary `FR-EM-V5` is written in.
    """
    if margin >= 0.0:
        return 0.5 + reward * (0.5 + 0.5 * min(1.0, margin))
    if not required:
        return 0.5
    return 0.5 - penalty * min(1.0, -margin)


def _suspect_score(margin: float, penalty: float) -> float:
    """`FR-EM-V4` — the mirror of `_graded_score`'s met branch, below neutral.

    Crossing a suspect threshold costs half the penalty immediately, because a
    shakeout is a categorical read rather than a matter of degree, and the rest
    accrues as the excess grows.
    """
    return 0.5 - penalty * (0.5 + 0.5 * min(1.0, max(0.0, margin)))


def score_breakout(rvol: float, rule: BreakoutRule) -> float:
    """Breakout volume as a score in ``[0, 1]``, where **0.5 is "no
    information"** rather than "bad".

    Above ``confirm_rvol`` the score rises: half the reward is credited at the
    threshold itself and the rest is earned as `rvol` climbs to twice it, so
    the verdict is graded rather than a step — a step cannot be swept
    (`FR-EM-V11`) and would make `H1` satisfiable by a near-constant.

    Below the threshold the two directions part company, which is the whole of
    `FR-EM-V3`: a required expansion that is missing is graded down toward
    ``rvol = 0``, whereas a merely corroborating one returns exactly 0.5 —
    missing evidence, not adverse evidence.
    """
    if rule.suspect_above_rvol is not None and rvol >= rule.suspect_above_rvol:
        # FR-EM-V4. Past this point the curve TURNS DOWN: a break on
        # extraordinary volume is read as a shakeout rather than as
        # conviction, so the same evidence that corroborated a moment ago now
        # counts against the pattern. This is the one place in the module
        # where more volume is worse, and it is deliberate.
        excess = (rvol - rule.suspect_above_rvol) / rule.suspect_above_rvol
        return _suspect_score(excess, rule.suspect_penalty)

    margin = (rvol - rule.confirm_rvol) / rule.confirm_rvol
    return _graded_score(
        margin,
        required=rule.expansion_required,
        reward=rule.confirm_reward,
        penalty=rule.dull_penalty,
    )


def factor_from_score(score: float) -> float:
    """Map a score in ``[0, 1]`` onto the `FR-EM-V7` multiplier.

    Piecewise linear and monotone through the three fixed points that make the
    mapping meaningful: ``0.0 -> FACTOR_FLOOR``, ``0.5 -> 1.0`` (a score of
    "no information" must not move the confidence at all), and
    ``1.0 -> FACTOR_CEILING``.

    The two halves have different slopes because the bounds are deliberately
    asymmetric: E&M's volume evidence is better at discrediting a formation
    than at promoting one. Bounded by construction, so no verdict can erase a
    geometrically excellent pattern or manufacture a poor one — volume is
    corroboration, not the finding.
    """
    score = min(1.0, max(0.0, score))
    if score >= 0.5:
        return NEUTRAL_FACTOR + (score - 0.5) / 0.5 * (FACTOR_CEILING - NEUTRAL_FACTOR)
    return NEUTRAL_FACTOR - (0.5 - score) / 0.5 * (NEUTRAL_FACTOR - FACTOR_FLOOR)


def verdict_label(score: float) -> str:
    if score > 0.5:
        return VERDICT_CONFIRMS
    if score < 0.5:
        return VERDICT_CONTRADICTS
    return VERDICT_NEUTRAL


@dataclass(frozen=True)
class BreakoutEvent:
    """A located penetration and the direction it went.

    The direction is carried separately from ``pattern_type`` because the
    symmetrical triangle has none — it reports ``"neutral"`` and can resolve
    either way, and `FR-EM-V5` gives the two resolutions **opposite**
    treatment: an upside break requires expansion, a downside break on heavy
    volume is suspect. So the direction has to come from the break itself.
    """
    bar: int
    direction: str
    boundary: float


def _boundaries(match: Any) -> tuple:
    """The upper and lower levels a penetration is measured against.

    Directional patterns publish the one that matters as ``neckline``. The
    symmetrical triangle publishes the upper line as ``neckline`` and the
    lower line only implicitly — but exactly, since
    ``details["target_dn"] = breakout_l - pattern_height``
    (`continuation.py`), so the lower line is recoverable by addition rather
    than by re-fitting the trendline or guessing at it.
    """
    neckline = getattr(match, "neckline", None)
    if neckline is None:
        return None, None
    details = getattr(match, "details", {}) or {}
    if "target_dn" in details and "pattern_height" in details:
        try:
            return float(neckline), float(details["target_dn"]) + float(details["pattern_height"])
        except (TypeError, ValueError):
            return float(neckline), None
    return float(neckline), None


def breakout_event(match: Any, ohlc: Any) -> Optional[BreakoutEvent]:
    """Locate the penetration and say which way it went, or ``None``.

    For a pattern with a direction, the boundary is ``neckline`` and the
    direction is the pattern's own. For a ``neutral`` pattern, both boundaries
    are used and whichever is pierced first decides the direction.

    Causality (C1) holds trivially: every bar examined is at or before the last
    bar of the frame, which *is* the prediction time, and no bar before the
    formation is consulted.
    """
    key_bars = getattr(match, "key_bars", None)
    if not key_bars:
        return None
    upper, lower = _boundaries(match)
    if upper is None:
        return None
    try:
        close = ohlc["close"].to_numpy(dtype=float)
    except (KeyError, TypeError, AttributeError):
        return None

    pattern_type = getattr(match, "pattern_type", "")
    for i in range(int(key_bars[-1]) + 1, len(close)):
        if pattern_type == "bullish" and close[i] > upper:
            return BreakoutEvent(i, "bullish", upper)
        if pattern_type == "bearish" and close[i] < upper:
            return BreakoutEvent(i, "bearish", upper)
        if pattern_type not in ("bullish", "bearish"):
            if close[i] > upper:
                return BreakoutEvent(i, "bullish", upper)
            if lower is not None and close[i] < lower:
                return BreakoutEvent(i, "bearish", lower)
    return None


def breakout_bar(match: Any, ohlc: Any) -> Optional[int]:
    """The bar on which the pattern's boundary was penetrated, or ``None``.

    The operative event for `FR-EM-V3` is the break, and no detector reports
    its index — they report the formation's ``key_bars`` and the ``neckline``
    that is the break *level*. So the bar is located as the first one after the
    formation whose close penetrates that level in the pattern's own direction.

    ``None`` is a real and common answer, not a failure: a formation that has
    not broken out yet has no breakout volume to judge. `V3`'s null run shows
    roughly half of directional detections are in that state at any moment.

    Causality (C1) holds trivially — every bar examined is at or before the
    last bar of the frame, which *is* the prediction time. There is no look
    past the right edge, and no bar before the formation is consulted.
    """
    if getattr(match, "pattern_type", "") not in BREAKOUT_RULES:
        return None
    event = breakout_event(match, ohlc)
    return None if event is None else event.bar


def evaluate_breakout_volume(
    match: Any,
    ohlc: Any,
    baseline_window: int = DEFAULT_BASELINE_WINDOW,
) -> VolumeVerdict:
    """`FR-EM-V3` + `FR-EM-V7` — the volume verdict on one detection.

    This is the **generic** breakout rule: it applies the direction asymmetry
    at the penetration bar and nothing else. The per-detector conditions of
    `FR-EM-V5` — the shoulders' relative volume, the flag drying up, the
    triangle's suspect downside break — are tasks V5 and V6, and will refine
    or replace this verdict per detector rather than sit beside it.

    Every unavailability path returns ``VolumeVerdict.neutral`` (factor exactly
    ``1.0``, score ``None``), because unknown must never read as "volume
    contradicts" (`FR-EM-V7`, `EC-V1`–`EC-V4`). ``match`` and ``ohlc`` are
    duck-typed so this module stays independent of ``base.py``, which imports
    it.
    """
    try:
        if "volume" not in ohlc:
            return VolumeVerdict.neutral("no_volume_column")
        volume = ohlc["volume"].to_numpy(dtype=float)
    except (KeyError, TypeError, AttributeError):
        return VolumeVerdict.neutral("no_volume_column")

    rule = BREAKOUT_RULES.get(getattr(match, "pattern_type", ""))
    if rule is None:
        # A neutral-typed pattern (the symmetrical triangle, a common gap) has
        # no direction, so the asymmetry has nothing to apply. Its own
        # condition is FR-EM-V5, task V6.
        return VolumeVerdict.neutral("no_directional_rule")

    bar = breakout_bar(match, ohlc)
    if bar is None:
        return VolumeVerdict.neutral("no_breakout_yet")

    rv = relative_volume(volume, bar, baseline_window)
    if not rv.known:
        return VolumeVerdict.neutral(
            rv.reason or "rvol_unavailable",
            thin_volume=rv.reason in {"dormant_no_baseline", "insufficient_history"},
        )

    score = score_breakout(rv.value, rule)
    # Key order is fixed: the UI renders this dict in order, and `H6`'s
    # determinism assertion compares it.
    evidence: Dict[str, Any] = {
        "status": "known",
        "verdict": verdict_label(score),
        "condition": "breakout volume",
        "direction": rule.direction,
        "expansion_required": rule.expansion_required,
        "rvol": round(float(rv.value), 3),
        "confirm_rvol": rule.confirm_rvol,
        "baseline": round(float(rv.baseline or 0.0), 1),
        "baseline_window": baseline_window,
        "bars_used": rv.bars_used,
        "breakout_bar": bar,
        "citation": "E&M Ch 7",
    }
    return VolumeVerdict(
        score=round(score, 6), factor=round(factor_from_score(score), 6), evidence=evidence
    )


# --- V5: per-detector conditions (FR-EM-V5) ---------------------------------
#
# Three condition shapes cover every reversal rule in the book, and they are
# different shapes on purpose. E&M do not state one condition four times with
# different numbers; they state a *comparison* for the head-and-shoulders top
# (one shoulder against the other), a *direction* for the bottom (volume
# building through the formation), and a *level* for the double bottom (a
# second low that is conspicuously dull). Collapsing them into one
# parametrised rule would lose the distinction the book insists on — which is
# why `tests/test_volume_reversal_rules.py` asserts on the rule objects and
# not only on their output.
#
# Anchors are **positions within `match.key_bars`**, not bar indices, so a rule
# is written in terms of the formation ("the right shoulder") rather than in
# terms of a frame it has never seen.

#: Half-width of the window read around an anchor bar. `swing_window` is the
#: detectors' own notion of a swing's extent (`reversal.py` defaults it to 3),
#: so a shoulder is read over the same bars the detector called a shoulder.
ANCHOR_WINDOW = 3


def _anchor_span(
    key_bars: Sequence[int],
    anchor: int,
    n: int,
    window: int,
    to_anchor: Optional[int] = None,
    start_offset: int = 0,
) -> Optional[tuple]:
    """Bar range for a condition, clipped to the frame.

    With ``to_anchor`` it is the span **between** two key bars — which is how
    V6a expresses "through the flag" (``key_bars[2]`` to ``key_bars[3]``) and
    "the mast" (``key_bars[0]`` to ``key_bars[1]``). Without it, a window of
    ``±window`` around a single key bar, which is how V5 expresses "the right
    shoulder". Both are needed: a shoulder is a *point* in the formation, a
    flag is an *interval*.
    """
    if anchor >= len(key_bars):
        return None
    if to_anchor is not None:
        if to_anchor >= len(key_bars):
            return None
        start = int(key_bars[anchor]) + start_offset
        end = min(n, int(key_bars[to_anchor]) + 1)
    else:
        centre = int(key_bars[anchor])
        start, end = max(0, centre - window), min(n, centre + window + 1)
    start = max(0, start)
    if end <= start:
        return None
    return start, end


@dataclass(frozen=True)
class SpanRatio:
    """One formation span's typical `rvol` against another's.

    The head-and-shoulders top's condition (Ch 6, *"the right shoulder on
    decidedly less volume"*) and the double top's (Ch 9, *"less volume on the
    second top"*) are both of this shape: evidence is the **comparison**, not
    either level on its own.
    """
    label: str
    a_anchor: int
    b_anchor: int
    expect: str                 # "a_lower" | "a_higher"
    ratio: float                # the threshold the comparison must clear
    required: bool
    weight: float = 1.0
    citation: str = ""
    #: Set either to compare the span BETWEEN two key bars instead of a window
    #: around one — "through the flag" against "the mast".
    a_to_anchor: Optional[int] = None
    b_to_anchor: Optional[int] = None
    #: `FR-EM-V4`: a ratio this far the wrong way inverts the pattern rather
    #: than merely failing its condition. On a flag, a consolidation trading as
    #: heavily as the thrust that created it is no longer a pause — Ch 11's
    #: "minor reversal area". Carried here as well as on `SpanTrend` because a
    #: detected flag span is often only three bars, too short for a rank trend
    #: to be readable at all, so the ratio is the only place the inversion can
    #: be expressed.
    suspect_at: Optional[float] = None
    suspect_penalty: float = 0.5

    def anchors_include(self, anchor: int) -> bool:
        return anchor in (self.a_anchor, self.b_anchor)

    @property
    def kind(self) -> str:
        return "ratio"

    def evaluate(self, volume, key_bars, n, window, baseline_window, _end):
        a = _anchor_span(key_bars, self.a_anchor, n, window, self.a_to_anchor)
        b = _anchor_span(key_bars, self.b_anchor, n, window, self.b_to_anchor)
        if a is None or b is None:
            return None, {"verdict": "unknown", "reason": "anchor_out_of_range", "value": None}
        rv_a = span_relative_volume(volume, a[0], a[1], baseline_window)
        rv_b = span_relative_volume(volume, b[0], b[1], baseline_window)
        if not rv_a.known or not rv_b.known or rv_b.value == 0.0:
            return None, {"verdict": "unknown", "reason": "span_unavailable", "value": None}

        ratio = rv_a.value / rv_b.value
        wrong_way = ratio if self.expect == "a_lower" else 1.0 / max(ratio, 1e-9)
        if self.suspect_at is not None and wrong_way >= self.suspect_at:
            excess = (wrong_way - self.suspect_at) / self.suspect_at
            score = _suspect_score(excess, self.suspect_penalty)
            verdict = VERDICT_SUSPECT
        else:
            margin = (
                (self.ratio - ratio) / self.ratio
                if self.expect == "a_lower"
                else (ratio - self.ratio) / self.ratio
            )
            score = _graded_score(margin, required=self.required)
            verdict = verdict_label(score)
        return score, {
            "verdict": verdict,
            "value": round(ratio, 3),
            "threshold": self.ratio,
            "expect": self.expect,
            "required": self.required,
            "a_rvol": round(rv_a.value, 3),
            "b_rvol": round(rv_b.value, 3),
            "citation": self.citation,
        }


@dataclass(frozen=True)
class SpanLevel:
    """One span's `rvol` against an absolute threshold.

    The double bottom's *"conspicuously dull and rounded"* second low (Ch 9) is
    a level, not a comparison: `rvol` is already normalised against the
    symbol's own trailing history, so "dull" is a statement about that number
    directly.
    """
    label: str
    anchor: int
    expect: str                 # "low" | "high"
    threshold: float
    required: bool
    weight: float = 1.0
    citation: str = ""
    to_anchor: Optional[int] = None
    start_offset: int = 0

    def anchors_include(self, anchor: int) -> bool:
        return anchor == self.anchor

    def evaluate(self, volume, key_bars, n, window, baseline_window, _end):
        span = _anchor_span(
            key_bars, self.anchor, n, window, self.to_anchor, self.start_offset
        )
        if span is None:
            return None, {"verdict": "unknown", "reason": "anchor_out_of_range", "value": None}
        rv = span_relative_volume(volume, span[0], span[1], baseline_window)
        if not rv.known:
            return None, {"verdict": "unknown", "reason": rv.reason or "span_unavailable", "value": None}

        margin = (
            (self.threshold - rv.value) / self.threshold
            if self.expect == "low"
            else (rv.value - self.threshold) / self.threshold
        )
        score = _graded_score(margin, required=self.required)
        return score, {
            "verdict": verdict_label(score),
            "value": round(rv.value, 3),
            "threshold": self.threshold,
            "expect": self.expect,
            "required": self.required,
            "citation": self.citation,
        }


@dataclass(frozen=True)
class SpanTrend:
    """The *direction* of volume from an anchor to the end of the formation.

    The inverse head-and-shoulders' condition (Ch 7, volume must **build**
    through the head and the right-shoulder rally) is a direction, and this is
    the shape that makes the bottom's rule structurally unlike the top's — the
    requirement that the bottom not be the top inverted.
    """
    label: str
    from_anchor: int
    expect: str                 # "building" | "drying"
    threshold: float
    required: bool
    weight: float = 1.0
    citation: str = ""
    #: `FR-EM-V4`: a trend this far in the WRONG direction is not merely an
    #: unmet condition, it inverts the pattern's meaning. Ch 11 on flags:
    #: "high or irregular volume inside the pattern turns it into a minor
    #: reversal area". ``None`` leaves the condition monotone.
    suspect_at: Optional[float] = None
    suspect_penalty: float = 0.5

    def anchors_include(self, anchor: int) -> bool:
        return anchor == self.from_anchor

    def evaluate(self, volume, key_bars, n, window, _baseline_window, end):
        if self.from_anchor >= len(key_bars):
            return None, {"verdict": "unknown", "reason": "anchor_out_of_range", "value": None}
        start = int(key_bars[self.from_anchor])
        stop = min(n, (end if end is not None else int(key_bars[-1]) + window) + 1)
        trend = volume_trend(volume, start, stop)
        if not trend.known:
            return None, {"verdict": "unknown", "reason": trend.reason or "span_too_short", "value": None}

        signed = trend.value if self.expect == "building" else -trend.value
        if self.suspect_at is not None and -signed >= self.suspect_at:
            # Moving decisively the wrong way: an inversion, not a shortfall.
            excess = (-signed - self.suspect_at) / max(1e-9, 1.0 - self.suspect_at)
            score = _suspect_score(excess, self.suspect_penalty)
            verdict = VERDICT_SUSPECT
        else:
            margin = (signed - self.threshold) / max(1e-9, 1.0 - self.threshold)
            score = _graded_score(margin, required=self.required)
            verdict = verdict_label(score)
        return score, {
            "verdict": verdict,
            "value": round(trend.value, 3),
            "threshold": self.threshold,
            "expect": self.expect,
            "required": self.required,
            "bars_used": trend.bars_used,
            "citation": self.citation,
        }


@dataclass(frozen=True)
class BarExtreme:
    """One bar's volume against a high percentile of a **long** trailing window.

    `FR-EM-V5` row 11 and SRS open question 3. Ch 10.1's One-Day Reversal
    requires *"volume exceeding anything for months"*, so this is the only
    condition in the module that does not use ``baseline_window`` — the whole
    point is that the comparison window is a different, much longer one.

    A percentile rather than a maximum, for `EC-V5`'s reason: see
    `LONG_BASELINE_PERCENTILE`.
    """
    label: str
    anchor: int
    window: int = LONG_BASELINE_WINDOW
    percentile: float = LONG_BASELINE_PERCENTILE
    threshold: float = 1.0
    required: bool = True
    weight: float = 1.0
    citation: str = ""

    def anchors_include(self, anchor: int) -> bool:
        return anchor == self.anchor

    def evaluate(self, volume, key_bars, n, _window, _baseline_window, _end):
        if self.anchor >= len(key_bars):
            return None, {"verdict": "unknown", "reason": "anchor_out_of_range", "value": None}
        index = int(key_bars[self.anchor])
        here = _usable(volume[index]) if 0 <= index < n else None
        if here is None:
            return None, {"verdict": "unknown", "reason": "missing_volume", "value": None}

        start = max(0, index - self.window)
        prior = [v for v in (_usable(x) for x in volume[start:index]) if v is not None]
        if len(prior) < MIN_BASELINE_BARS:
            return None, {
                "verdict": "unknown", "reason": "insufficient_long_history",
                "value": None, "window": self.window,
            }

        reference = _percentile(prior, self.percentile)
        if reference <= 0.0:
            return None, {
                "verdict": "unknown", "reason": "dormant_long_window",
                "value": None, "window": self.window,
            }

        ratio = here / reference
        margin = (ratio - self.threshold) / self.threshold
        score = _graded_score(margin, required=self.required)
        return score, {
            "verdict": verdict_label(score),
            "value": round(ratio, 3),
            "threshold": self.threshold,
            "window": self.window,
            "percentile": self.percentile,
            "reference": round(reference, 1),
            "bars_used": len(prior),
            "required": self.required,
            "citation": self.citation,
        }


#: The head-and-shoulders bottom's breakout rule — the strongest in the set.
#: E&M, Ch 7: *"there must be a conspicuous burst of volume on the neckline
#: penetration. Without it, don't trust the breakout."* Strictest on both
#: axes: it demands more volume before it is satisfied (`confirm_rvol`) and it
#: costs more when it is not (`dull_penalty`).
INVERSE_HS_BREAKOUT = BreakoutRule(
    direction="bullish",
    expansion_required=True,
    confirm_rvol=2.0,
    confirm_reward=0.5,
    dull_penalty=0.5,
)


@dataclass(frozen=True)
class PatternVolumeRule:
    """One detector's volume condition set (`FR-EM-V5`).

    ``unscored_note`` records what the rule deliberately does **not** look at,
    which for the head-and-shoulders top is load-bearing rather than
    decorative: E&M report that of confirmed tops roughly a third are heavier
    on the left shoulder, a third about equal and a third heavier on the head,
    so head volume carries no information and scoring it would fit noise.
    """
    pattern_name: str
    breakout: Optional[BreakoutRule]
    conditions: tuple
    citation: str
    breakout_weight: float = 1.0
    unscored_note: str = ""
    #: Set instead of ``breakout`` when the two resolutions of one formation
    #: get **opposite** treatment and the direction is not known until the
    #: break happens — the symmetrical triangle, whose upside break requires
    #: expansion while its downside break on heavy volume is suspect.
    breakout_by_direction: Optional[Dict[str, BreakoutRule]] = None
    #: Set only by the gap family. A callable ``(match, ohlc) -> Optional[str]``
    #: returning the new ``pattern_name``, so the dispatcher stays generic and
    #: the one detector that re-labels declares that it does.
    reclassify: Optional[Callable[..., Optional[str]]] = None

    def breakout_for(self, direction: str) -> Optional[BreakoutRule]:
        if self.breakout_by_direction is not None:
            return self.breakout_by_direction.get(direction)
        return self.breakout

    def all_breakouts(self) -> List[BreakoutRule]:
        """Every breakout rule this pattern can use — for tests and sweeps."""
        if self.breakout_by_direction is not None:
            return list(self.breakout_by_direction.values())
        return [] if self.breakout is None else [self.breakout]


PATTERN_RULES: Dict[str, PatternVolumeRule] = {
    # key_bars = [left shoulder, trough 1, head, trough 2, right shoulder]
    "Head and Shoulders": PatternVolumeRule(
        pattern_name="Head and Shoulders",
        breakout=BEARISH_BREAKOUT,
        conditions=(
            SpanRatio(
                label="right shoulder lighter than left",
                a_anchor=4, b_anchor=0, expect="a_lower",
                ratio=0.75, required=True, citation="E&M Ch 6",
            ),
        ),
        citation="E&M Ch 6",
        unscored_note=(
            "head volume is deliberately not scored: of confirmed tops ~1/3 are "
            "heavier on the left shoulder, ~1/3 equal, ~1/3 heavier on the head"
        ),
    ),
    "Inverse Head and Shoulders": PatternVolumeRule(
        pattern_name="Inverse Head and Shoulders",
        breakout=INVERSE_HS_BREAKOUT,
        conditions=(
            SpanTrend(
                label="volume builds through the head and right-shoulder rally",
                from_anchor=2, expect="building",
                threshold=0.1, required=True, citation="E&M Ch 7",
            ),
        ),
        citation="E&M Ch 7",
        # The burst is the near-absolute here, so it outweighs the build.
        breakout_weight=2.0,
        unscored_note="the price pattern is the top inverted; the volume pattern is not",
    ),
    # key_bars = [first peak, trough, second peak]
    "Double Top": PatternVolumeRule(
        pattern_name="Double Top",
        breakout=BEARISH_BREAKOUT,
        conditions=(
            SpanRatio(
                label="second top lighter than the first",
                a_anchor=2, b_anchor=0, expect="a_lower",
                ratio=0.8, required=True, citation="E&M Ch 9",
            ),
        ),
        citation="E&M Ch 9",
    ),
    # key_bars = [first trough, peak, second trough]
    "Double Bottom": PatternVolumeRule(
        pattern_name="Double Bottom",
        breakout=BULLISH_BREAKOUT,
        conditions=(
            SpanLevel(
                label="second bottom conspicuously dull",
                anchor=2, expect="low",
                threshold=0.8, required=True, citation="E&M Ch 9",
            ),
        ),
        citation="E&M Ch 9",
    ),
}


#: Ch 8, the ascending triangle: resolution runs about 9:1 to the upside, so
#: an upside break without expansion is a failed requirement.
ASCENDING_BREAKOUT = BreakoutRule(
    direction="bullish", expansion_required=True, confirm_rvol=1.5,
    confirm_reward=0.5, dull_penalty=0.45,
)

#: Ch 8, the descending triangle: downside resolution, so volume only
#: corroborates — and `FR-EM-V4`'s inversion applies, an *extreme* downside
#: break being a 2-3 day shakeout rather than conviction. This is the rule
#: whose scoring curve rises and then falls.
DESCENDING_BREAKOUT = BreakoutRule(
    direction="bearish", expansion_required=False, confirm_rvol=1.5,
    confirm_reward=0.3, dull_penalty=0.0,
    suspect_above_rvol=3.0, suspect_penalty=0.45,
)

#: The symmetrical triangle resolving upward — Ch 8's "expands on the
#: breakout", required because the formation itself predicts nothing.
SYMMETRICAL_UP_BREAKOUT = BreakoutRule(
    direction="bullish", expansion_required=True, confirm_rvol=1.5,
    confirm_reward=0.5, dull_penalty=0.45,
)

#: The symmetrical triangle resolving downward. E&M call a high-volume
#: downside break suspect *"especially out near the apex"*; a break located
#: after the final pivot of a converging formation is near the apex by
#: construction, so no separate apex-distance measure is taken here — a
#: refinement recorded for the `S2` sweep rather than guessed at now.
#: The suspect threshold is lower than the descending triangle's because this
#: is the book's worst offender for false moves.
SYMMETRICAL_DOWN_BREAKOUT = BreakoutRule(
    direction="bearish", expansion_required=False, confirm_rvol=1.5,
    confirm_reward=0.2, dull_penalty=0.0,
    suspect_above_rvol=2.5, suspect_penalty=0.5,
)

_TRIANGLE_DRYING = dict(
    label="volume diminishes toward the apex",
    from_anchor=0, expect="drying", threshold=0.15, required=True,
    citation="E&M Ch 8",
)

PATTERN_RULES.update({
    # key_bars = [pole_start, pole_end, flag_start, last bar]
    "Flag": PatternVolumeRule(
        pattern_name="Flag",
        breakout=None,
        # A flag takes its direction from the pole, so the generic asymmetric
        # rules apply to its resumption: a bull flag breaking up needs volume,
        # a bear flag breaking down does not. Declared per direction rather
        # than left implicit so the rule *says* it has a breakout condition,
        # and the dispatcher can report "no break yet" instead of silently
        # omitting the row.
        breakout_by_direction={"bullish": BULLISH_BREAKOUT, "bearish": BEARISH_BREAKOUT},
        conditions=(
            SpanRatio(
                label="flag volume markedly below the mast",
                a_anchor=2, a_to_anchor=3, b_anchor=0, b_to_anchor=1,
                expect="a_lower", ratio=0.6, required=True, citation="E&M Ch 11",
                suspect_at=1.0,
            ),
            SpanTrend(
                label="volume dries up continuously through the flag",
                from_anchor=2, expect="drying", threshold=0.1, required=False,
                suspect_at=0.3, citation="E&M Ch 11",
            ),
        ),
        citation="E&M Ch 11",
        unscored_note=(
            "expansion inside the flag is suspect, not merely unhelpful: it "
            "turns a continuation into a minor reversal area"
        ),
    ),
    # key_bars = [pole_start, pole_end, pennant_start, last bar]
    "Pennant": PatternVolumeRule(
        pattern_name="Pennant",
        breakout=None,
        breakout_by_direction={"bullish": BULLISH_BREAKOUT, "bearish": BEARISH_BREAKOUT},
        conditions=(
            SpanRatio(
                label="pennant volume markedly below the mast",
                a_anchor=2, a_to_anchor=3, b_anchor=0, b_to_anchor=1,
                expect="a_lower", ratio=0.5, required=True, citation="E&M Ch 11",
                suspect_at=0.9,
            ),
            SpanTrend(
                # Stricter than the flag: "volume dries up even faster,
                # sometimes to almost nothing".
                label="volume dries up continuously through the pennant",
                from_anchor=2, expect="drying", threshold=0.25, required=False,
                suspect_at=0.3, citation="E&M Ch 11",
            ),
        ),
        citation="E&M Ch 11",
    ),
    # key_bars = the trendline pivots, in order
    "Symmetrical Triangle": PatternVolumeRule(
        pattern_name="Symmetrical Triangle",
        breakout=None,
        breakout_by_direction={
            "bullish": SYMMETRICAL_UP_BREAKOUT,
            "bearish": SYMMETRICAL_DOWN_BREAKOUT,
        },
        conditions=(SpanTrend(**_TRIANGLE_DRYING),),
        citation="E&M Ch 8",
        # The book's worst offender for false moves, so volume gets more say
        # here than on the other two triangles.
        breakout_weight=2.0,
        unscored_note="a high-volume downside break near the apex is suspect, not confirming",
    ),
    "Ascending Triangle": PatternVolumeRule(
        pattern_name="Ascending Triangle",
        breakout=ASCENDING_BREAKOUT,
        conditions=(SpanTrend(**_TRIANGLE_DRYING),),
        citation="E&M Ch 8",
    ),
    "Descending Triangle": PatternVolumeRule(
        pattern_name="Descending Triangle",
        breakout=DESCENDING_BREAKOUT,
        conditions=(SpanTrend(**_TRIANGLE_DRYING),),
        citation="E&M Ch 8",
    ),
})


def reclassify_gap(match: Any, ohlc: Any) -> Optional[str]:
    """`FR-EM-V5` row 10 — Ch 12's exhaustion test, or ``None`` to leave the
    label alone.

    E&M recognise an exhaustion gap by *"extraordinary volume with price
    failing to advance commensurately"* on the day after. That is a **volume**
    rule, and `continuation.py`'s classifier has no volume to read: it sees a
    gap in the trend direction that has not been filled and calls it a
    *runaway*. So this is the one place EM-1 changes a label.

    **Deliberately narrow** (SRS open question 4). Only the exhaustion case is
    re-classified, because it is the only one the SRS says the current
    classifier cannot express. Separating *breakaway* from *runaway* on volume
    is plausible but has no evidence behind it yet, so it stays geometry-driven
    until the `S2` sweep — inventing a second re-labelling rule here would be
    exactly the unverified claim `CLAUDE.md` forbids.

    Both halves of the rule are required. Extraordinary volume that *does*
    carry price is a breakaway or a runaway, and a stall on ordinary volume is
    just a stall; only the conjunction is an exhaustion gap.
    """
    details = getattr(match, "details", {}) or {}
    key_bars = getattr(match, "key_bars", None)
    if not key_bars or details.get("gap_type") == "exhaustion":
        return None

    gap_bar = int(key_bars[-1])
    try:
        volume = ohlc["volume"].to_numpy(dtype=float)
        close = ohlc["close"].to_numpy(dtype=float)
    except (KeyError, TypeError, AttributeError):
        return None

    rv = relative_volume(volume, gap_bar, DEFAULT_BASELINE_WINDOW)
    if not rv.known or rv.value < GAP_EXHAUSTION_RVOL:
        return None

    gap_size = float(details.get("gap_size") or 0.0)
    if gap_size <= 0.0:
        return None

    # "The day after" — read the bars that exist, never past the right edge
    # (C1): the frame's last bar IS the prediction time.
    after = close[gap_bar + 1: gap_bar + 4]
    if after.size == 0:
        return None

    sign = 1.0 if details.get("gap_direction") == "up" else -1.0
    advance = float((after.max() if sign > 0 else after.min()) - close[gap_bar]) * sign
    if advance >= GAP_FOLLOW_THROUGH_FRACTION * gap_size:
        return None

    return "Gap (exhaustion)"


#: ``to_anchor=1`` with the same anchor reads **exactly one bar** — the gap
#: itself. A gap is a single-bar event, so the default ±`ANCHOR_WINDOW` window
#: would take the median of seven bars and wash the gap's own volume out
#: entirely: measured, a gap on nine times its baseline scored *neutral*
#: because the six ordinary bars around it dominated the median.
_GAP_VOLUME_CONDITION = SpanLevel(
    label="volume on the gap",
    anchor=1, to_anchor=1, expect="high", threshold=1.5,
    required=False, citation="E&M Ch 12",
)

_TRAP_CONDITION = SpanLevel(
    # The span starts AFTER the penetration — see `_anchor_span`'s start_offset.
    label="no follow-through volume after the penetration",
    anchor=0, to_anchor=1, start_offset=1,
    expect="low", threshold=0.9, required=True, citation="E&M Ch 13, Ch 35",
)

_TRAP_NOTE = (
    "volume's role is INVERTED here: a genuine break is nearly always followed "
    "by a marked volume pickup, so the ABSENCE of follow-through is the trap's "
    "signature and raises confidence rather than lowering it"
)

PATTERN_RULES.update({
    # key_bars = [bar before the gap, the gap bar]
    **{
        name: PatternVolumeRule(
            pattern_name=name,
            breakout=None,
            conditions=(_GAP_VOLUME_CONDITION,),
            citation="E&M Ch 12",
            reclassify=reclassify_gap,
            unscored_note=(
                "volume may RE-LABEL this gap as an exhaustion gap: extraordinary "
                "volume with price failing to advance commensurately (Ch 12)"
            ),
        )
        for name in ("Gap (common)", "Gap (breakaway)", "Gap (runaway)")
    },
    # Already exhaustion: scored, but not re-labelled again.
    "Gap (exhaustion)": PatternVolumeRule(
        pattern_name="Gap (exhaustion)",
        breakout=None,
        conditions=(_GAP_VOLUME_CONDITION,),
        citation="E&M Ch 12",
        reclassify=reclassify_gap,
        unscored_note="an exhaustion gap is already a volume reading; it is not re-labelled again",
    ),
    # key_bars = [the wide bar]
    "Wide-Ranging Day": PatternVolumeRule(
        pattern_name="Wide-Ranging Day",
        breakout=None,
        conditions=(
            BarExtreme(
                label="volume exceeding anything for months",
                anchor=0, required=True, citation="E&M Ch 10.1",
            ),
        ),
        citation="E&M Ch 10, Ch 10.1",
        unscored_note=(
            "without volume exceeding anything for months this is an ordinary "
            "wide day, not a One-Day Reversal"
        ),
    ),
    # key_bars = [penetration bar, reversion bar]
    "Bull Trap": PatternVolumeRule(
        pattern_name="Bull Trap", breakout=None,
        conditions=(_TRAP_CONDITION,), citation="E&M Ch 13, Ch 35",
        unscored_note=_TRAP_NOTE,
    ),
    "Bear Trap": PatternVolumeRule(
        pattern_name="Bear Trap", breakout=None,
        conditions=(_TRAP_CONDITION,), citation="E&M Ch 13, Ch 35",
        unscored_note=_TRAP_NOTE,
    ),
})


def evaluate_pattern_volume(
    match: Any,
    ohlc: Any,
    baseline_window: int = DEFAULT_BASELINE_WINDOW,
    anchor_window: int = ANCHOR_WINDOW,
) -> VolumeVerdict:
    """`FR-EM-V5` — the volume verdict for one detection, via its own rule.

    Dispatches on ``pattern_name`` through `PATTERN_RULES`. A pattern with no
    entry falls back to `evaluate_breakout_volume`, the generic asymmetric
    breakout rule from V4 — so the detectors V6 has not reached yet keep the
    verdict they already had instead of losing it.

    Components are averaged by weight, with "unknown" components dropped rather
    than counted as zero (`EC-V1`): a condition that cannot be read is missing
    evidence, and the conditions that *can* be read are still evidence. If none
    can be read, the result is neutral.
    """
    rule = PATTERN_RULES.get(getattr(match, "pattern_name", ""))
    if rule is None:
        return evaluate_breakout_volume(match, ohlc, baseline_window)

    try:
        if "volume" not in ohlc:
            return VolumeVerdict.neutral("no_volume_column")
        volume = ohlc["volume"].to_numpy(dtype=float)
    except (KeyError, TypeError, AttributeError):
        return VolumeVerdict.neutral("no_volume_column")

    key_bars = list(getattr(match, "key_bars", []) or [])
    if not key_bars:
        return VolumeVerdict.neutral("no_key_bars")

    n = len(volume)
    event = breakout_event(match, ohlc)
    bar = None if event is None else event.bar
    components: Dict[str, Any] = {}
    weighted: List[tuple] = []

    for condition in rule.conditions:
        score, detail = condition.evaluate(
            volume, key_bars, n, anchor_window, baseline_window, bar
        )
        components[condition.label] = detail
        if score is not None:
            weighted.append((condition.weight, score))

    if rule.breakout is not None or rule.breakout_by_direction is not None:
        breakout = rule.breakout_for(event.direction) if event is not None else None
        if bar is None or breakout is None:
            components["breakout volume"] = {
                "verdict": "unknown",
                "reason": "no_breakout_yet" if bar is None else "no_rule_for_direction",
                "value": None,
            }
        else:
            rv = relative_volume(volume, bar, baseline_window)
            if not rv.known:
                components["breakout volume"] = {
                    "verdict": "unknown", "reason": rv.reason or "rvol_unavailable", "value": None
                }
            else:
                score = score_breakout(rv.value, breakout)
                suspect = (
                    breakout.suspect_above_rvol is not None
                    and rv.value >= breakout.suspect_above_rvol
                )
                components["breakout volume"] = {
                    "verdict": VERDICT_SUSPECT if suspect else verdict_label(score),
                    "value": round(rv.value, 3),
                    "threshold": breakout.confirm_rvol,
                    "suspect_above": breakout.suspect_above_rvol,
                    "required": breakout.expansion_required,
                    "direction": breakout.direction,
                    "score": round(score, 6),
                    "breakout_bar": bar,
                    "citation": rule.citation,
                }
                weighted.append((rule.breakout_weight, score))

    if not weighted:
        return VolumeVerdict.neutral("no_readable_condition")

    total = sum(w for w, _ in weighted)
    score = sum(w * s for w, s in weighted) / total
    evidence: Dict[str, Any] = {
        "status": "known",
        "verdict": verdict_label(score),
        "pattern": rule.pattern_name,
        "direction": getattr(match, "pattern_type", ""),
        "components": components,
        "baseline_window": baseline_window,
        "anchor_window": anchor_window,
        "citation": rule.citation,
    }
    if rule.unscored_note:
        evidence["not_scored"] = rule.unscored_note

    reclassified: Optional[str] = None
    if rule.reclassify is not None:
        try:
            candidate = rule.reclassify(match, ohlc)
        except Exception:  # noqa: BLE001 — NFR-V1: never drop a detection
            candidate = None
        if candidate and candidate != getattr(match, "pattern_name", ""):
            reclassified = candidate
            evidence["reclassified_from"] = match.pattern_name
            evidence["reclassified_to"] = candidate

    return VolumeVerdict(
        score=round(score, 6),
        factor=round(factor_from_score(score), 6),
        evidence=evidence,
        reclassify_to=reclassified,
    )


# --- V7: the climactic-volume flag (FR-EM-V6) -------------------------------

#: `rvol` against the LONG baseline at or above which volume counts as extreme.
#: A climax is extreme *against months*, not against the last fifty bars — the
#: same reasoning as `FR-EM-V5` row 11. Default pending the `S2` sweep.
# SWEPT at S2 against 9,646 real bars over 18 symbols, because at the original
# 2.5 the flag fired ZERO times — it was unreachable, not merely rare
# (Backlog #72). rvol was the binding gate, not progress: 2.5 yielded nothing
# at ANY progress threshold. 2.0 fires on 2 bars / 2 symbols, which is the
# once-in-years event E&M describe; 1.5 would give 12 bars / 8 symbols, too
# common for a "climax".
CLIMAX_RVOL = 2.0

#: Net progress, measured in typical-move units, at or below which the bar's
#: price did not go anywhere worth that volume. Ch 12's phrase is "failing to
#: advance commensurately"; this is that phrase made arithmetic.
# Loosened from 0.6 with the same evidence. A climax bar plunges and snaps
# back, so its close-to-close progress is small but rarely near zero, and on
# real VN data extreme volume essentially always carries SOME move.
CLIMAX_PROGRESS_RATIO = 1.0


@dataclass(frozen=True)
class ClimaxFlag:
    """One bar read as climactic (`FR-EM-V6`).

    Ch 10's selling climax, Ch 28's *"prepare to retire into your shell"* and
    Ch 12's exhaustion gap are the same observation three times: enormous
    volume that buys almost no net movement. Where price plunges and snaps
    back inside the session, the snap-back is exactly what makes the progress
    non-commensurate.

    **Evidence only in this slice.** The flag is returned on the scan response
    and deliberately never reaches a `PatternMatch`, so nothing downstream can
    begin scoring with it by accident. Acting on it — E&M's "cancel further
    commitments in that direction" — belongs to decision-helper and is a
    separate Phase-0 candidate.
    """
    bar_index: int
    rvol_long: float
    progress_ratio: float
    window: int
    reason: str
    citation: str = "E&M Ch 10, Ch 28"


def detect_volume_climax(
    ohlc: Any,
    long_window: int = LONG_BASELINE_WINDOW,
    percentile: float = LONG_BASELINE_PERCENTILE,
    rvol_threshold: float = CLIMAX_RVOL,
    progress_threshold: float = CLIMAX_PROGRESS_RATIO,
) -> Optional[ClimaxFlag]:
    """`FR-EM-V6` — the most recent climactic bar in the frame, or ``None``.

    Independent of any pattern, which is why it is a reading on the frame
    rather than a condition inside a rule. Both halves of the definition are
    required: extreme volume that *does* carry price is a breakout or a
    one-day reversal, not a climax, and treating every heavy day as a warning
    would make the flag worthless.

    The scale for "commensurate" is the **median absolute close-to-close
    move** over the same long window, which keeps this module free of any
    dependency on the detectors' ATR helper and is robust to one wild bar by
    construction (`EC-V5`).

    Scans backwards from the most recent bar, so a live reading reports the
    latest climax rather than the first one in the window. Causality (C1)
    holds: the baseline for bar ``i`` reads only bars before ``i``, and no bar
    after ``i`` is consulted at all.
    """
    try:
        if "volume" not in ohlc:
            return None
        volume = ohlc["volume"].to_numpy(dtype=float)
        close = ohlc["close"].to_numpy(dtype=float)
    except (KeyError, TypeError, AttributeError):
        return None

    n = len(close)
    if n < long_window // 2 or n < MIN_BASELINE_BARS + 2:
        return None

    for i in range(n - 1, 0, -1):
        start = max(0, i - long_window)
        prior_volume = [v for v in (_usable(x) for x in volume[start:i]) if v is not None]
        here = _usable(volume[i])
        if here is None or len(prior_volume) < long_window // 2:
            continue

        reference = _percentile(prior_volume, percentile)
        if reference <= 0.0:
            continue
        rvol_long = here / reference
        if rvol_long < rvol_threshold:
            continue

        moves = [abs(close[j] - close[j - 1]) for j in range(max(1, start + 1), i)]
        typical = _median(moves) if moves else 0.0
        if typical <= 0.0:
            continue

        progress_ratio = abs(close[i] - close[i - 1]) / typical
        if progress_ratio > progress_threshold:
            # Volume was extreme but price went somewhere with it. That is a
            # breakout or a one-day reversal, and the rules for those already
            # read it — flagging it here as well would double-count.
            continue

        return ClimaxFlag(
            bar_index=i,
            rvol_long=round(float(rvol_long), 3),
            progress_ratio=round(float(progress_ratio), 3),
            window=long_window,
            reason=(
                f"volume {rvol_long:.1f}x the {percentile:.0f}th percentile of "
                f"{long_window} bars, with net progress {progress_ratio:.2f}x a "
                f"typical day"
            ),
        )
    return None
