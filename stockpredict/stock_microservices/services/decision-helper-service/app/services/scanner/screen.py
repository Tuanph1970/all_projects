"""S-1 funnel — FR-SCAN-UNIV, FR-SCAN-LIQ, FR-SCAN-SEAM, then rank and template.

Order is not arbitrary. Each stage is cheaper than the one after it and removes
names the next stage would otherwise have to reason about, and — the part that
actually matters — THE SEAM GATE RUNS BEFORE THE RANKING. A seam is a stored
overnight move no Vietnamese board permits (`stock_common.analytics`), and on a
126-bar horizon it does not mis-state one bar, it mis-states the whole return:
TCB's -33.8% share-count event would have planted that symbol at the bottom of
the cross-section for six months. Ranking first and filtering after would leave
every OTHER symbol's percentile computed against a contaminated population.

THE BASE STAGE RUNS LAST, AFTER THE TEMPLATE. Base detection is the most
expensive stage and the most specific, so it reasons only about names already
known to be liquid, strong and in an uptrend. Running it earlier would find
tidy consolidations in falling stocks — true as geometry, useless as a setup.

A candidate that clears every stage is *a liquid, strong name resting in a
tightening base with a pivot overhead*. That is Qullamaggie's setup; it is still
not a buy signal — entry, stop and size belong to the decision engine (EC-S6),
and whether the setup has edge on VN equities belongs to VT-5.

Causality (EC-S1) is enforced in exactly one place — `_window`, which cuts every
symbol's bars at `as_of` before any stage sees them. That single cut is what
VT-1 tests.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date
from typing import Dict, FrozenSet, List, Mapping, Optional, Sequence, Tuple

from stock_common.analytics import MAX_BELIEVABLE_DAILY_MOVE_PCT, find_price_seams

from app.services.scanner.base import (
    DEFAULT_BASE_MAX_BARS,
    DEFAULT_BASE_MAX_DEPTH_PCT,
    DEFAULT_BASE_MAX_DRIFT_OVER_DEPTH,
    DEFAULT_BASE_MAX_DRIFT_PCT,
    DEFAULT_BASE_MIN_BARS,
    DEFAULT_DRYUP_MAX_RATIO,
    DEFAULT_MA_PROXIMITY_PCT,
    DEFAULT_SQUEEZE_MAX_RATIO,
    BaseAssessment,
    assess_base,
)
from app.services.scanner.momentum import (
    DEFAULT_HORIZONS,
    MomentumRank,
    profile_momentum,
    rank_cross_section,
)
from app.services.scanner.trend import (
    DEFAULT_ADVANCE_LOOKBACK,
    DEFAULT_MIN_PRIOR_ADVANCE_PCT,
    TrendTemplate,
    assess_trend,
    required_bars,
)
from app.services.signal.base import OHLCVBar
from app.services.universe.liquidity import LiquidityResult, assess_liquidity

logger = logging.getLogger(__name__)

#: Liquidity floor in **VND** of average daily turnover (EC-S4).
#:
#: Qullamaggie's "300.000 đến 500.000 cổ phiếu/phiên" is a share count, which is
#: meaningless across VN's price range — 500k shares of a 7,000 VND small-cap and
#: of a 200,000 VND blue chip are not the same market. 5 tỷ/phiên is the
#: starting value, chosen as a round number in the right order of magnitude and
#: NOT yet calibrated against anything; VT-5 is where it earns or loses its place.
DEFAULT_MIN_AVG_DAILY_VALUE = 5_000_000_000.0

#: VND per stored price unit.
#:
#: NOT COSMETIC — it is a factor of 1,000 on the only threshold in this phase.
#: vnstock/VCI quotes Vietnamese equities in THOUSANDS of VND and we store that
#: verbatim: VIC's close reads 233.69 for a 233,690 VND share. `assess_liquidity`
#: multiplies close by volume, so its `avg_daily_value` is in thousands of VND
#: too — VIC measures 875,755,182 over the last 50 sessions, which is 875 tỷ/day,
#: not 876 triệu. Comparing that number directly against a VND threshold is off
#: by three orders of magnitude in the direction that silently passes everything.
#: Kept as config rather than folded into the constant so a source that one day
#: stores real VND is a one-line change and not a silent re-calibration.
DEFAULT_PRICE_UNIT_VND = 1_000.0

#: Qullamaggie's "khối lượng giao dịch trung bình 50 phiên gần nhất".
DEFAULT_LIQUIDITY_LOOKBACK = 50

#: "Chọn ra khoảng 10 đến 20 cổ phiếu đẹp nhất."
DEFAULT_MAX_CANDIDATES = 20

#: Symbols whose price seam SURVIVED a full re-pull, and so is the provider's
#: own record of a real session rather than the Backlog #119 ingestion artefact
#: (SRS 2.4). These are classified, not excluded.
#:
#: Lives here rather than in the CLI that first needed it: the API, the nightly
#: job and the CLI must agree about which seams are real, and three copies of a
#: list like this is how they stop agreeing. VTP 2022-11-16 (+17.13%) was on
#: UPCoM at the time, where the band is +/-15% and a reference reset widens it.
KNOWN_PROVIDER_SEAMS: FrozenSet[str] = frozenset({"VTP"})


@dataclass(frozen=True)
class SeamFinding:
    symbol: str
    bar_date: Optional[str]
    prev_close: float
    close: float
    move_pct: float
    ratio: Optional[float]


@dataclass(frozen=True)
class ScanConfig:
    horizons: Tuple[int, ...] = DEFAULT_HORIZONS
    horizon_weights: Optional[Mapping[int, float]] = None
    min_bars: int = 150
    liquidity_lookback: int = DEFAULT_LIQUIDITY_LOOKBACK
    min_avg_daily_value: float = DEFAULT_MIN_AVG_DAILY_VALUE   # VND
    min_avg_daily_volume: float = 0.0                          # shares
    price_unit_vnd: float = DEFAULT_PRICE_UNIT_VND
    min_prior_advance_pct: float = DEFAULT_MIN_PRIOR_ADVANCE_PCT
    advance_lookback: int = DEFAULT_ADVANCE_LOOKBACK
    max_candidates: int = DEFAULT_MAX_CANDIDATES
    #: S-2 stages. `require_base` False reproduces the S-1 funnel exactly, which
    #: is how the two phases stay comparable on the same data.
    require_base: bool = True
    base_min_bars: int = DEFAULT_BASE_MIN_BARS
    base_max_bars: int = DEFAULT_BASE_MAX_BARS
    base_max_depth_pct: float = DEFAULT_BASE_MAX_DEPTH_PCT
    base_max_drift_pct: float = DEFAULT_BASE_MAX_DRIFT_PCT
    base_max_drift_over_depth: float = DEFAULT_BASE_MAX_DRIFT_OVER_DEPTH
    squeeze_max_ratio: float = DEFAULT_SQUEEZE_MAX_RATIO
    dryup_max_ratio: float = DEFAULT_DRYUP_MAX_RATIO
    ma_proximity_pct: float = DEFAULT_MA_PROXIMITY_PCT
    seam_max_move_pct: float = MAX_BELIEVABLE_DAILY_MOVE_PCT
    #: Symbols whose seam SURVIVED a full re-pull and is therefore provider
    #: data, not our ingestion artefact (SRS 2.4). Those are classified, not
    #: excluded: the gate is here to drop seams the repair path can still fix,
    #: and excluding a real UPCoM session is the detector crying wolf.
    seam_allowlist: FrozenSet[str] = frozenset()

    def min_avg_value_in_price_units(self) -> float:
        """The VND floor restated in the units `assess_liquidity` actually
        measures, which is what gets compared."""
        if self.price_unit_vnd <= 0:
            raise ValueError("price_unit_vnd must be positive")
        return self.min_avg_daily_value / self.price_unit_vnd

    def effective_min_bars(self) -> int:
        """`min_bars` raised to whatever the stages actually need — SMA200, the
        longest momentum horizon, the advance window. Configuring 150 and then
        silently failing every SMA200 clause is the failure mode this closes."""
        return max(
            self.min_bars,
            max(self.horizons) + 1,
            required_bars(self.advance_lookback),
            self.liquidity_lookback,
        )


@dataclass(frozen=True)
class ScanCandidate:
    rank: int                       # 1-based position in the final list
    momentum: MomentumRank
    trend: TrendTemplate
    liquidity: LiquidityResult
    #: None when `require_base` is off — the S-1 funnel, reproduced.
    base: Optional[BaseAssessment] = None

    @property
    def symbol(self) -> str:
        return self.momentum.symbol


@dataclass(frozen=True)
class ScanReport:
    as_of: date
    universe_total: int
    required_bars: int
    ranked_universe: int
    candidates: Tuple[ScanCandidate, ...]
    excluded_no_bars: Tuple[str, ...] = ()
    excluded_insufficient_history: Tuple[str, ...] = ()
    excluded_price_seam: Tuple[SeamFinding, ...] = ()
    flagged_price_seam: Tuple[SeamFinding, ...] = ()
    excluded_illiquid: Tuple[LiquidityResult, ...] = ()
    failed_trend: Tuple[TrendTemplate, ...] = ()
    failed_base: Tuple[BaseAssessment, ...] = ()
    #: Names that PASSED every stage but fell outside `max_candidates`. They are
    #: not a rejection bucket, they are the shortlist's tail — carried because
    #: without them `accounting()` would not balance and "qualified" would be
    #: indistinguishable from "qualified and shown".
    excess_qualified: Tuple[str, ...] = ()

    def accounting(self) -> Dict[str, int]:
        """Every symbol in the universe lands in exactly one bucket. A scanner
        that quietly loses names is indistinguishable from one that found
        nothing (FR-SCAN-UNIV), so the totals are made checkable."""
        counts = {
            "no_bars": len(self.excluded_no_bars),
            "insufficient_history": len(self.excluded_insufficient_history),
            "price_seam": len(self.excluded_price_seam),
            "illiquid": len(self.excluded_illiquid),
            "failed_trend": len(self.failed_trend),
            "failed_base": len(self.failed_base),
            "candidates": len(self.candidates),
            "excess_qualified": len(self.excess_qualified),
        }
        counts["accounted"] = sum(counts.values())
        counts["universe_total"] = self.universe_total
        return counts


def _window(bars: Sequence[OHLCVBar], as_of: date) -> List[OHLCVBar]:
    """THE causality cut (EC-S1). Sorted by date, then truncated at `as_of`.

    Sorting here rather than trusting the caller is deliberate: an unsorted
    series would make `bars[-1]` an arbitrary bar and every return in the module
    silently wrong, and the sort is cheap next to the cost of that being true.
    """
    return sorted((b for b in bars if b.date <= as_of), key=lambda b: b.date)


def _seams(symbol: str, bars: Sequence[OHLCVBar], max_move_pct: float) -> List[SeamFinding]:
    found = find_price_seams(
        [float(b.close) for b in bars],
        [b.date.isoformat() for b in bars],
        max_move_pct=max_move_pct,
    )
    return [
        SeamFinding(symbol, s.date, s.prev_close, s.close, s.move_pct, s.ratio)
        for s in found
    ]


def run_scan(
    bars_by_symbol: Mapping[str, Sequence[OHLCVBar]],
    as_of: date,
    config: Optional[ScanConfig] = None,
) -> ScanReport:
    """Run the S-1 funnel over a universe and return a ranked shortlist."""
    cfg = config or ScanConfig()
    need = cfg.effective_min_bars()

    no_bars: List[str] = []
    short: List[str] = []
    seam_excluded: List[SeamFinding] = []
    seam_flagged: List[SeamFinding] = []
    illiquid: List[LiquidityResult] = []
    survivors: Dict[str, List[OHLCVBar]] = {}
    liquidity: Dict[str, LiquidityResult] = {}

    for symbol in sorted(bars_by_symbol):
        window = _window(bars_by_symbol[symbol], as_of)
        if not window:
            no_bars.append(symbol)
            continue
        if len(window) < need:
            short.append(symbol)
            continue

        seams = _seams(symbol, window, cfg.seam_max_move_pct)
        if seams:
            if symbol in cfg.seam_allowlist:
                seam_flagged.extend(seams)
            else:
                seam_excluded.extend(seams)
                continue

        liq = assess_liquidity(
            window,
            ticker=symbol,
            lookback=cfg.liquidity_lookback,
            min_avg_value=cfg.min_avg_value_in_price_units(),
            min_avg_volume=cfg.min_avg_daily_volume,
        )
        if not liq.passed:
            illiquid.append(liq)
            continue

        survivors[symbol] = window
        liquidity[symbol] = liq

    ranked = rank_cross_section(
        [profile_momentum(s, b, cfg.horizons) for s, b in survivors.items()],
        cfg.horizon_weights,
    )

    failed_trend: List[TrendTemplate] = []
    failed_base: List[BaseAssessment] = []
    candidates: List[ScanCandidate] = []
    for mom in ranked:
        bars = survivors[mom.symbol]
        tmpl = assess_trend(
            mom.symbol, bars,
            min_prior_advance_pct=cfg.min_prior_advance_pct,
            advance_lookback=cfg.advance_lookback,
        )
        if not tmpl.passed:
            failed_trend.append(tmpl)
            continue

        base: Optional[BaseAssessment] = None
        if cfg.require_base:
            base = assess_base(
                mom.symbol, bars,
                min_bars=cfg.base_min_bars,
                max_bars=cfg.base_max_bars,
                max_depth_pct=cfg.base_max_depth_pct,
                max_drift_pct=cfg.base_max_drift_pct,
                max_drift_over_depth=cfg.base_max_drift_over_depth,
                squeeze_max_ratio=cfg.squeeze_max_ratio,
                dryup_max_ratio=cfg.dryup_max_ratio,
                ma_proximity_pct=cfg.ma_proximity_pct,
            )
            if not base.passed:
                failed_base.append(base)
                continue

        candidates.append(
            ScanCandidate(len(candidates) + 1, mom, tmpl, liquidity[mom.symbol], base))

    # The cut happens AFTER the template, so `max_candidates` means "the 20 best
    # names that qualify", not "whatever qualifies among the 20 strongest".
    excess: List[str] = []
    if cfg.max_candidates > 0 and len(candidates) > cfg.max_candidates:
        excess = [c.symbol for c in candidates[cfg.max_candidates:]]
        candidates = candidates[: cfg.max_candidates]

    # A momentum-complete symbol that is neither a candidate nor a trend failure
    # would be a leak in the accounting; `rank_cross_section` drops incomplete
    # profiles, and `need` already guarantees completeness, so this holds.
    return ScanReport(
        as_of=as_of,
        universe_total=len(bars_by_symbol),
        required_bars=need,
        ranked_universe=len(ranked),
        candidates=tuple(candidates),
        excluded_no_bars=tuple(no_bars),
        excluded_insufficient_history=tuple(short),
        excluded_price_seam=tuple(seam_excluded),
        flagged_price_seam=tuple(seam_flagged),
        excluded_illiquid=tuple(illiquid),
        failed_trend=tuple(failed_trend),
        failed_base=tuple(failed_base),
        excess_qualified=tuple(excess),
    )
