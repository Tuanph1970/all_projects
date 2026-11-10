"""Backlog #141 — are the squeeze and MA clauses measuring the wrong thing on a FLAG?

    PYTHONPATH=.:../../stock-common python3 tests/s2b_flag_calibration.py <bars.tsv>

Not a test. Read-only: loads bars, runs the UNMODIFIED production funnel over
every trading day, and re-evaluates the three post-shape clauses on the FLAG
windows it finds under one pre-registered alternative each.

PRE-REGISTERED in `docs/backlog141_flag_calibration_preregistration.md`, written
and committed BEFORE this file existed (commit f3cecc5f). Every constant below is
copied from that document. None may be tuned against this script's output, and
the decision rule in §9 is implemented here as code rather than applied by hand
afterwards -- `verdict()` prints ADOPT or KEEP and has no third branch.

WHY ONE PRODUCTION SCAN PER DATE COVERS ALL EIGHT ARMS. The flag detector runs
only as a fallback when no flat base is found, and the three clauses under study
run only AFTER a window is chosen. So no threshold in this study can change WHICH
window is detected -- the arms differ exclusively in the three clause verdicts on
FLAG windows. Re-running the funnel eight times would produce identical windows
at eight times the cost, and would invite the belief that something upstream
moved.

WHAT THIS CANNOT DO. It cannot estimate edge, for the same reason S-5a could not:
episodes arrive in bursts and 5.5 years of VN data holds one bear market. It
answers one question -- does re-specifying three measures admit flags that are no
worse than the candidates the screen already produces -- and the pre-registered
answer to a thin sample is KEEP, not "adopt and watch".
"""
from __future__ import annotations

import random
import statistics
import sys
from dataclasses import dataclass
from datetime import date
from typing import Dict, List, Optional, Sequence, Tuple

from stock_common.analytics import MAX_BELIEVABLE_DAILY_MOVE_PCT

from app.services.backtest.market_features import atr_series
from app.services.scanner.base import (
    MA_FAST, MA_MEDIUM, SHAPE_FLAG, SHAPE_FLAT, BaseWindow, true_ranges,
)
from app.services.scanner.screen import KNOWN_PROVIDER_SEAMS, ScanConfig, run_scan
from app.services.scanner.trend import SMA_SLOW, sma_at
from app.services.signal.base import OHLCVBar
from tests.s1_momentum_scan import load_bars

# ── Pre-registered constants. DO NOT TUNE. ────────────────────────────────
# Production settings (P), from base.py. Repeated, not imported, so that a
# later production change cannot silently redefine what this study compared.
P_SQUEEZE_MAX_RATIO = 0.75
P_DRYUP_MAX_RATIO = 0.80
P_MA_PROXIMITY_PCT = 8.0

# Shape-specific alternatives (S), prereg §4. Same cut-offs where a cut-off
# survives: only the DENOMINATOR changes, from the flag's own first third /
# own mean to the pole. §4.3 is the one that drops a bound, because a fixed
# percentage bound on MA distance is the thing that cannot be right for a
# window sitting immediately after a thrust.
S_SQUEEZE_MAX_RATIO = 0.75          # last-third TR / mean POLE TR
S_DRYUP_MAX_RATIO = 0.80            # last-third volume / mean POLE volume
S_MA_MAX_ATR = 5.0                  # (close - MA20) / ATR20
ATR_PERIOD = 20

HORIZONS: Tuple[int, ...] = (5, 10, 20)
EPISODE_GAP_BARS = 20
PIVOT_WINDOW_BARS = 20
RANDOM_SEED = 20261110
MIN_EPISODES = 20                   # §7 -- a TEST cell below this means KEEP
SEAM_PCT = MAX_BELIEVABLE_DAILY_MOVE_PCT
TRAIN_END = date(2024, 6, 30)       # §5; TEST is everything after

CLAUSES = ("range_contraction", "volume_dryup", "ma_hugging")
#: §4.4 -- eight arms are reported, exactly one is adoptable.
ARMS: Tuple[str, ...] = ("PPP", "PPS", "PSP", "PSS", "SPP", "SPS", "SSP", "SSS")
PRIMARY_ARM = "SSS"
BASELINE_ARM = "PPP"


# ---------------------------------------------------------------------------
# The three clauses, re-evaluated under P and S on a FLAG window
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ClauseRatios:
    """Every quantity both variants need, measured once per flag window.

    Ratios, not booleans, for the reason `SqueezeMetrics` gives: the number is
    what a later calibration needs, and a hidden boolean cannot be re-read.
    """
    flag_range_ratio: Optional[float]     # last-third TR / first-third TR   (P)
    pole_range_ratio: Optional[float]     # last-third TR / mean pole TR     (S)
    flag_volume_ratio: Optional[float]    # last third / flag mean           (P)
    pole_volume_ratio: Optional[float]    # last third / mean pole volume    (S)
    ma_dist_fast_pct: Optional[float]
    ma_dist_medium_pct: Optional[float]
    ma_dist_medium_atr: Optional[float]   # (close - MA20) / ATR20           (S)


def _mean(vals: Sequence[Optional[float]]) -> Optional[float]:
    clean = [v for v in vals if v is not None]
    return sum(clean) / len(clean) if clean else None


def measure_clause_ratios(bars: Sequence[OHLCVBar], w: BaseWindow) -> ClauseRatios:
    """All four squeeze ratios plus the three MA distances, on one window.

    The pole denominators use `w.pole_start_index` / `w.pole_end_index`, the
    instrumentation added for this study. They are None for FLAT, so the
    pole-relative ratios are None there and no S arm can be evaluated on a flat
    base -- which is §1's requirement that this study not touch flat verdicts.
    """
    tr = true_ranges(bars)
    lo, hi = w.start_index, w.end_index + 1
    third = w.length // 3

    first_tr = _mean(tr[lo:lo + third]) if third >= 1 else None
    last_tr = _mean(tr[hi - third:hi]) if third >= 1 else None
    vols = [float(b.volume) for b in bars[lo:hi]]
    flag_mean_vol = (sum(vols) / len(vols)) if vols else None
    last_vol = (sum(vols[-third:]) / third) if (vols and third >= 1) else None

    pole_tr = pole_vol = None
    if w.pole_start_index is not None and w.pole_end_index is not None:
        ps, pe = w.pole_start_index, w.pole_end_index + 1
        pole_tr = _mean(tr[ps:pe])
        pvols = [float(b.volume) for b in bars[ps:pe]]
        pole_vol = (sum(pvols) / len(pvols)) if pvols else None

    def ratio(num: Optional[float], den: Optional[float]) -> Optional[float]:
        if num is None or den is None or den <= 0:
            return None
        return num / den

    close = float(bars[-1].close)
    fast, medium = sma_at(bars, MA_FAST), sma_at(bars, MA_MEDIUM)
    atr = atr_series(list(bars), ATR_PERIOD)
    latest_atr = atr[-1] if atr else None
    d_fast = ((close - fast) / close * 100.0) if (fast is not None and close > 0) else None
    d_med = ((close - medium) / close * 100.0) if (medium is not None and close > 0) else None
    d_med_atr = (((close - medium) / latest_atr)
                 if (medium is not None and latest_atr) else None)

    return ClauseRatios(
        flag_range_ratio=ratio(last_tr, first_tr),
        pole_range_ratio=ratio(last_tr, pole_tr),
        flag_volume_ratio=ratio(last_vol, flag_mean_vol),
        pole_volume_ratio=ratio(last_vol, pole_vol),
        ma_dist_fast_pct=d_fast,
        ma_dist_medium_pct=d_med,
        ma_dist_medium_atr=d_med_atr,
    )


def clause_passes(r: ClauseRatios, clause: str, variant: str) -> bool:
    """One clause under one variant. A ratio that is not computable FAILS, which
    is production's rule (`squeeze.range_ratio is not None and ...`) and must not
    quietly become a pass just because an S denominator is missing."""
    if clause == "range_contraction":
        if variant == "P":
            return r.flag_range_ratio is not None and r.flag_range_ratio <= P_SQUEEZE_MAX_RATIO
        return r.pole_range_ratio is not None and r.pole_range_ratio <= S_SQUEEZE_MAX_RATIO
    if clause == "volume_dryup":
        if variant == "P":
            return r.flag_volume_ratio is not None and r.flag_volume_ratio <= P_DRYUP_MAX_RATIO
        return r.pole_volume_ratio is not None and r.pole_volume_ratio <= S_DRYUP_MAX_RATIO
    if clause == "ma_hugging":
        if r.ma_dist_fast_pct is None or r.ma_dist_medium_pct is None:
            return False
        below = r.ma_dist_fast_pct >= 0.0 and r.ma_dist_medium_pct >= 0.0
        if variant == "P":
            return (below and r.ma_dist_fast_pct <= P_MA_PROXIMITY_PCT
                    and r.ma_dist_medium_pct <= P_MA_PROXIMITY_PCT)
        # S: trend intact, extension bounded in the stock's OWN volatility units.
        return below and r.ma_dist_medium_atr is not None and r.ma_dist_medium_atr <= S_MA_MAX_ATR
    raise ValueError(clause)


def arm_admits(r: ClauseRatios, arm: str) -> bool:
    return all(clause_passes(r, c, v) for c, v in zip(CLAUSES, arm))


# ---------------------------------------------------------------------------
# Forward measurement -- identical to S-5a §4, for comparability (prereg §6)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Episode:
    symbol: str
    scan_date: date
    shape: str
    returns: Dict[int, float]
    excess: Dict[int, float]
    pivot_cleared: Optional[bool]


def forward_return(bars: Sequence[OHLCVBar], i: int, horizon: int) -> Optional[float]:
    if i + horizon >= len(bars):
        return None
    start, end = float(bars[i].close), float(bars[i + horizon].close)
    return None if start <= 0 else (end / start - 1.0) * 100.0


def window_has_seam(bars: Sequence[OHLCVBar], i: int, horizon: int) -> bool:
    for j in range(i + 1, min(i + horizon + 1, len(bars))):
        prev, cur = float(bars[j - 1].close), float(bars[j].close)
        if prev > 0 and abs((cur / prev - 1.0) * 100.0) > SEAM_PCT:
            return True
    return False


def cleared_pivot(bars: Sequence[OHLCVBar], i: int, pivot: float) -> Optional[bool]:
    """Any CLOSE in the next 20 bars above the pivot. Close, not high: on a tran
    day the high IS the ceiling and nothing fills there."""
    if i + PIVOT_WINDOW_BARS >= len(bars):
        return None
    return any(float(b.close) > pivot for b in bars[i + 1: i + 1 + PIVOT_WINDOW_BARS])


def cleared_prior_high(bars: Sequence[OHLCVBar], i: int) -> Optional[bool]:
    """The like-for-like level, for arms that have no base (S-5a's reasoning)."""
    if i + PIVOT_WINDOW_BARS >= len(bars) or i < PIVOT_WINDOW_BARS:
        return None
    level = max(float(b.high) for b in bars[i - PIVOT_WINDOW_BARS + 1: i + 1])
    return any(float(b.close) > level for b in bars[i + 1: i + 1 + PIVOT_WINDOW_BARS])


def describe(values: Sequence[float], label: str) -> str:
    n = len(values)
    if n < MIN_EPISODES:
        return f"    {label:<30} UNDERPOWERED (n={n}, floor {MIN_EPISODES})"
    q = statistics.quantiles(values, n=4)
    return (f"    {label:<30} n={n:<5} mean {statistics.mean(values):+7.2f}%"
            f"  median {statistics.median(values):+7.2f}%"
            f"  IQR [{q[0]:+.2f}, {q[2]:+.2f}]")


def rate(flags: Sequence[Optional[bool]], label: str) -> str:
    vals = [f for f in flags if f is not None]
    n = len(vals)
    if n < MIN_EPISODES:
        return f"    {label:<30} UNDERPOWERED (n={n}, floor {MIN_EPISODES})"
    return f"    {label:<30} n={n:<5} {sum(vals)/n:6.1%}"


def episodes_from(rows: Sequence[Tuple[int, str, date, str, float]],
                  measure) -> List[Episode]:
    """Collapse per-date admissions into episodes (§3), then measure forward.

    `rows` is (ordinal, symbol, date, shape, pivot) sorted by ordinal. A symbol
    re-admitted within EPISODE_GAP_BARS of its previous admission is the same
    episode -- a stock sits in its base for weeks, and counting candidate-days
    would inflate n by an order of magnitude and narrow every interval to
    meaninglessness.
    """
    last_seen: Dict[str, int] = {}
    out: List[Episode] = []
    for ordinal, symbol, d, shape, pivot in rows:
        prev = last_seen.get(symbol)
        last_seen[symbol] = ordinal
        if prev is not None and ordinal - prev < EPISODE_GAP_BARS:
            continue
        ep = measure(symbol, d, shape, pivot)
        if ep is not None:
            out.append(ep)
    return out


def verdict(flag_eps: Sequence[Episode], flat_eps: Sequence[Episode],
            rand_excess: Dict[int, List[float]]) -> Tuple[bool, List[str]]:
    """§9's decision rule, as code. No third branch, and no judgement call left
    for whoever reads the output -- that is the point of pre-registering it."""
    lines: List[str] = []
    n = len(flag_eps)
    ok_n = n >= MIN_EPISODES
    lines.append(f"  1. n >= {MIN_EPISODES} flag episodes on TEST          "
                 f"n={n}  ->  {'PASS' if ok_n else 'FAIL'}")

    def clear_rate(eps: Sequence[Episode]) -> Optional[float]:
        vals = [e.pivot_cleared for e in eps if e.pivot_cleared is not None]
        return (sum(vals) / len(vals)) if vals else None

    fl, ft = clear_rate(flag_eps), clear_rate(flat_eps)
    ok_clear = fl is not None and ft is not None and fl >= ft
    lines.append(f"  2. pivot clearance >= ARM-FLAT                "
                 f"{'n/a' if fl is None else f'{fl:.1%}'} vs "
                 f"{'n/a' if ft is None else f'{ft:.1%}'}  ->  "
                 f"{'PASS' if ok_clear else 'FAIL'}")

    ex20 = [e.excess[20] for e in flag_eps if 20 in e.excess]
    m20 = statistics.mean(ex20) if ex20 else None
    ok_pos = m20 is not None and m20 >= 0
    lines.append(f"  3. mean excess 20-bar return >= 0             "
                 f"{'n/a' if m20 is None else f'{m20:+.2f}%'}  ->  "
                 f"{'PASS' if ok_pos else 'FAIL'}")

    rnd = statistics.mean(rand_excess[20]) if rand_excess.get(20) else None
    ok_rnd = m20 is not None and rnd is not None and m20 >= rnd
    lines.append(f"  4. mean excess 20-bar >= ARM-RANDOM           "
                 f"{'n/a' if m20 is None else f'{m20:+.2f}%'} vs "
                 f"{'n/a' if rnd is None else f'{rnd:+.2f}%'}  ->  "
                 f"{'PASS' if ok_rnd else 'FAIL'}")

    return (ok_n and ok_clear and ok_pos and ok_rnd), lines


def main(argv: List[str]) -> int:
    path = argv[1] if len(argv) > 1 else "bars.tsv"
    bars_by_symbol = load_bars(path)
    if not bars_by_symbol:
        print(f"no bars loaded from {path}", file=sys.stderr)
        return 1
    for sym in bars_by_symbol:
        bars_by_symbol[sym] = sorted(bars_by_symbol[sym], key=lambda b: b.date)

    index: Dict[str, Dict[date, int]] = {
        s: {b.date: i for i, b in enumerate(bars)} for s, bars in bars_by_symbol.items()
    }
    all_dates = sorted({b.date for bars in bars_by_symbol.values() for b in bars})
    # max_candidates=0: measure the FUNNEL, not the top-20 cut, exactly as S-5a
    # did. Admitting flags could otherwise push flat names off a 20-row list and
    # mix two effects in one number.
    cfg = ScanConfig(seam_allowlist=KNOWN_PROVIDER_SEAMS, max_candidates=0)
    scan_dates = all_dates[SMA_SLOW + 5: -max(HORIZONS) - 1]

    print("Backlog #141 -- shape-specific squeeze/MA thresholds for FLAG bases")
    print("  pre-registered: docs/backlog141_flag_calibration_preregistration.md")
    print(f"  universe {len(bars_by_symbol)} symbols | {all_dates[0]} .. {all_dates[-1]} "
          f"| {len(scan_dates)} scan dates")
    print(f"  TRAIN <= {TRAIN_END} | TEST > {TRAIN_END}\n")

    # arm -> list of (ordinal, symbol, date, shape, pivot)
    admitted: Dict[str, List[Tuple[int, str, date, str, float]]] = {a: [] for a in ARMS}
    flat_rows: List[Tuple[int, str, date, str, float]] = []
    liq_rows: List[Tuple[int, str, date]] = []
    flag_windows = 0
    ratio_dump: List[ClauseRatios] = []

    for ordinal, d in enumerate(scan_dates):
        report = run_scan(bars_by_symbol, d, cfg)
        if not report.ranked_universe:
            continue
        for c in report.candidates:
            liq_rows.append((ordinal, c.symbol, d))
        for t in report.failed_trend:
            liq_rows.append((ordinal, t.symbol, d))
        for b in report.failed_base:
            liq_rows.append((ordinal, b.symbol, d))

        # Every name that reached the base stage, passed or failed. A FLAT
        # window is recorded as-is; a FLAG window is re-evaluated per arm.
        reached = [c.base for c in report.candidates if c.base is not None] + \
                  list(report.failed_base)
        for base in reached:
            w = base.window
            if w is None or base.pivot is None:
                continue
            if w.shape == SHAPE_FLAT:
                if base.passed:
                    flat_rows.append((ordinal, base.symbol, d, SHAPE_FLAT, base.pivot.level))
                continue
            if w.shape != SHAPE_FLAG:
                continue
            flag_windows += 1
            bars = bars_by_symbol[base.symbol]
            upto = bars[: index[base.symbol][d] + 1]
            r = measure_clause_ratios(upto, w)
            ratio_dump.append(r)
            for arm in ARMS:
                if arm_admits(r, arm):
                    admitted[arm].append((ordinal, base.symbol, d, SHAPE_FLAG, base.pivot.level))

    def measure(symbol: str, d: date, shape: str, pivot: float) -> Optional[Episode]:
        bars = bars_by_symbol[symbol]
        i = index[symbol].get(d)
        if i is None:
            return None
        rets: Dict[int, float] = {}
        for h in HORIZONS:
            if window_has_seam(bars, i, h):
                return None                               # §8
            v = forward_return(bars, i, h)
            if v is None:
                return None                               # §8
            rets[h] = v
        return Episode(symbol, d, shape, rets, {}, cleared_pivot(bars, i, pivot))

    # Same-date liquid-universe mean, for the excess in §6.
    liq_by_date: Dict[date, Dict[int, List[float]]] = {}
    for ordinal, symbol, d in liq_rows:
        bars = bars_by_symbol[symbol]
        i = index[symbol].get(d)
        if i is None:
            continue
        for h in HORIZONS:
            if window_has_seam(bars, i, h):
                continue
            v = forward_return(bars, i, h)
            if v is not None:
                liq_by_date.setdefault(d, {}).setdefault(h, []).append(v)

    def with_excess(eps: Sequence[Episode]) -> List[Episode]:
        out: List[Episode] = []
        for e in eps:
            ex: Dict[int, float] = {}
            for h, v in e.returns.items():
                pool = liq_by_date.get(e.scan_date, {}).get(h)
                if pool:
                    ex[h] = v - (sum(pool) / len(pool))
            out.append(Episode(e.symbol, e.scan_date, e.shape, e.returns, ex, e.pivot_cleared))
        return out

    def split(eps: Sequence[Episode]) -> Tuple[List[Episode], List[Episode]]:
        return ([e for e in eps if e.scan_date <= TRAIN_END],
                [e for e in eps if e.scan_date > TRAIN_END])

    # ── Arm counts ─────────────────────────────────────────────────────────
    print(f"FLAG WINDOWS FOUND: {flag_windows} (symbol-days reaching the base "
          f"stage with no flat base)\n")
    print("ARM COUNTS -- flag symbol-days admitted, and episodes after the "
          f"{EPISODE_GAP_BARS}-bar grouping")
    print(f"    {'arm':<6} {'admitted':>9} {'episodes':>9} {'TRAIN':>7} {'TEST':>7}")
    arm_eps: Dict[str, List[Episode]] = {}
    for arm in ARMS:
        eps = with_excess(episodes_from(sorted(admitted[arm]), measure))
        arm_eps[arm] = eps
        tr, te = split(eps)
        note = ""
        if arm == BASELINE_ARM:
            note = "  <- production, today"
        elif arm == PRIMARY_ARM:
            note = "  <- the only adoptable arm (§4.4)"
        print(f"    {arm:<6} {len(admitted[arm]):>9} {len(eps):>9} "
              f"{len(tr):>7} {len(te):>7}{note}")

    # ── §5 gate: are the arms mechanically distinguishable on TRAIN? ───────
    tr_p, _ = split(arm_eps[BASELINE_ARM])
    tr_s, _ = split(arm_eps[PRIMARY_ARM])
    print(f"\n§5 TRAIN GATE -- does {PRIMARY_ARM} admit more flags than "
          f"{BASELINE_ARM}?  {len(tr_s)} vs {len(tr_p)}")
    if len(tr_s) <= len(tr_p):
        print("    NO. The re-specified measures do not change the verdict. "
              "Study stops here (§5).")
        print("\nVERDICT: KEEP production thresholds.")
        return 0
    print("    yes -- proceeding to the held-out comparison")

    # ── Benchmarks on TEST ─────────────────────────────────────────────────
    rng = random.Random(RANDOM_SEED)
    flat_eps = with_excess(episodes_from(sorted(flat_rows), measure))
    _, flat_test = split(flat_eps)
    _, s_test = split(arm_eps[PRIMARY_ARM])

    # §6.1: a SAME-SIZE draw, seeded. The first cut of this script drew 10x for
    # a tighter benchmark and that is a deviation, however well-meant: §6.1 fixed
    # the size, condition 4 compares against this arm, and widening a benchmark
    # after seeing the result is how a pre-registration stops meaning anything.
    # The 10x figure is reported in Part 2 as a PRECISION NOTE only -- it decides
    # nothing. A 35-name draw is noisy, and that noise was pre-registered.
    liq_pool = [(o, s, d) for (o, s, d) in liq_rows if d > TRAIN_END]
    rand_rows = rng.sample(liq_pool, min(len(s_test), len(liq_pool)))
    rand_eps: List[Episode] = []
    for _, symbol, d in rand_rows:
        bars = bars_by_symbol[symbol]
        i = index[symbol].get(d)
        if i is None:
            continue
        e = measure(symbol, d, "RANDOM", 0.0)
        if e is None:
            continue
        e = with_excess([e])[0]
        rand_eps.append(Episode(e.symbol, e.scan_date, e.shape, e.returns, e.excess,
                                cleared_prior_high(bars, i)))
    rand_excess = {h: [e.excess[h] for e in rand_eps if h in e.excess] for h in HORIZONS}

    print(f"\nTEST PERIOD ({TRAIN_END} .. {all_dates[-1]}) -- "
          f"{PRIMARY_ARM} flags vs the benchmarks (§6.1)")
    for h in HORIZONS:
        print(f"  +{h} bars, excess vs same-date liquid mean")
        print(describe([e.excess[h] for e in s_test if h in e.excess], f"{PRIMARY_ARM} flags"))
        print(describe([e.excess[h] for e in flat_test if h in e.excess], "ARM-FLAT"))
        print(describe(rand_excess[h], "ARM-RANDOM"))
    print("  breakout within 20 bars, on close")
    print(rate([e.pivot_cleared for e in s_test], f"{PRIMARY_ARM} flags (own pivot)"))
    print(rate([e.pivot_cleared for e in flat_test], "ARM-FLAT (own pivot)"))
    print(rate([e.pivot_cleared for e in rand_eps], "ARM-RANDOM (prior high)"))

    # ── §9 ────────────────────────────────────────────────────────────────
    print("\n§9 DECISION RULE -- pre-committed, all four must pass")
    adopt, lines = verdict(s_test, flat_test, rand_excess)
    for ln in lines:
        print(ln)
    print(f"\nVERDICT: {'ADOPT ' + PRIMARY_ARM + ' for FLAG windows' if adopt else 'KEEP production thresholds'}")
    if not adopt:
        print("    Per §9 a single failure means keep. The flag shape stays at "
              "~0 contribution\n    and #141 closes negative, which costs nothing: "
              "the detector remains, tested,\n    behind a shape that admits almost nothing.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
