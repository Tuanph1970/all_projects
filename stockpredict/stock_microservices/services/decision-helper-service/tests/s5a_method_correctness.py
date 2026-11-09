"""S-5a — does the scanner's output BEHAVE like the method claims?

    PYTHONPATH=.:../../stock-common python3 tests/s5a_method_correctness.py <bars.tsv>

Not a test, and not a backtest of a trading system. Read-only: it loads bars,
runs the UNMODIFIED production funnel over every trading day, and measures what
happened next.

PRE-REGISTERED in `docs/s5a_method_correctness_preregistration.md`, written
BEFORE this file existed. Every constant below is copied from that document and
none may be tuned against this script's own output. The repo's rule, from
`tests/em4_universe_thickness.py`: nothing here may be fitted to its own result.

WHAT THIS CANNOT DO, stated here because the output will look like it can.
Candidates arrive in bursts; 5.5 years of VN data holds one bear market. This
study is evidence about MECHANISM — does a candidate clear its own pivot more
often than a random liquid name, do returns depend on regime the way the trend
template implies — and NOT an estimate of edge. Every number it prints carries
that caveat, because a return figure lifted out of here and quoted as a forecast
would be exactly the overclaim C4 exists to prevent.
"""
from __future__ import annotations

import random
import statistics
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from typing import Dict, List, Optional, Sequence, Tuple

from stock_common.analytics import MAX_BELIEVABLE_DAILY_MOVE_PCT

from app.services.scanner.screen import KNOWN_PROVIDER_SEAMS, ScanConfig, run_scan
from app.services.scanner.trend import SMA_SLOW, sma_at
from app.services.signal.base import OHLCVBar
from app.services.universe.liquidity import assess_liquidity
from tests.s1_momentum_scan import load_bars

# ── Pre-registered constants (§3-§8). DO NOT TUNE. ─────────────────────────
HORIZONS: Tuple[int, ...] = (5, 10, 20)
EPISODE_GAP_BARS = 20
PIVOT_WINDOW_BARS = 20
BROAD_REGIME_SHARE = 0.50
RANDOM_SEED = 20261109
MIN_EPISODES_PER_CELL = 10
SEAM_PCT = MAX_BELIEVABLE_DAILY_MOVE_PCT


@dataclass(frozen=True)
class Outcome:
    symbol: str
    scan_date: date
    regime: str                      # BROAD | NARROW
    returns: Dict[int, float]        # horizon -> % return from the episode close
    excess: Dict[int, float]         # the same, minus the same-date ARM-LIQ mean
    pivot_cleared: Optional[bool]       # candidate's OWN base pivot
    cleared_prior_high: Optional[bool]  # like-for-like metric, all three arms
    held_ma20: Optional[bool]


def forward_return(bars: Sequence[OHLCVBar], i: int, horizon: int) -> Optional[float]:
    """Return from close[i] to close[i+horizon], or None if it runs off the end.

    §8: a window past the last stored bar is DROPPED, never shortened — a 20-bar
    horizon silently measured over 11 bars is a different question.
    """
    if i + horizon >= len(bars):
        return None
    start, end = float(bars[i].close), float(bars[i + horizon].close)
    return None if start <= 0 else (end / start - 1.0) * 100.0


def window_has_seam(bars: Sequence[OHLCVBar], i: int, horizon: int) -> bool:
    """§8: a share-count event is not a return."""
    for j in range(i + 1, min(i + horizon + 1, len(bars))):
        prev, cur = float(bars[j - 1].close), float(bars[j].close)
        if prev > 0 and abs((cur / prev - 1.0) * 100.0) > SEAM_PCT:
            return True
    return False


def cleared_pivot(bars: Sequence[OHLCVBar], i: int, pivot: float) -> Optional[bool]:
    """Any CLOSE in the next PIVOT_WINDOW_BARS above the pivot.

    Close, not high, and deliberately: on a trần day the high IS the ceiling and
    nothing fills there, so a high-based test would credit the method with
    breakouts nobody could have taken.
    """
    if i + PIVOT_WINDOW_BARS >= len(bars):
        return None
    return any(float(b.close) > pivot for b in bars[i + 1: i + 1 + PIVOT_WINDOW_BARS])


def cleared_prior_high(bars: Sequence[OHLCVBar], i: int) -> Optional[bool]:
    """Any close in the next 20 bars above the trailing 20-bar HIGH at `i`.

    THE LIKE-FOR-LIKE METRIC. ARM-LIQ and ARM-RANDOM have no base and therefore
    no pivot, so comparing a candidate's pivot clearance against nothing would be
    a statistic with no benchmark — which §5 forbids. Every arm has a trailing
    high, so this is the same question asked of all three: did it break out of
    its own recent range? The candidates' true-pivot rate is reported beside it,
    and the two differ only in how the level was chosen.
    """
    if i + PIVOT_WINDOW_BARS >= len(bars) or i < PIVOT_WINDOW_BARS:
        return None
    level = max(float(b.high) for b in bars[i - PIVOT_WINDOW_BARS + 1: i + 1])
    return any(float(b.close) > level for b in bars[i + 1: i + 1 + PIVOT_WINDOW_BARS])


def held_ma20(bars: Sequence[OHLCVBar], i: int) -> Optional[bool]:
    """Did price stay above its MA20 for the next 20 bars? The method's own exit
    rule — "chỉ bán hết khi giá đóng cửa nằm dưới đường MA này"."""
    if i + PIVOT_WINDOW_BARS >= len(bars):
        return None
    for j in range(i + 1, i + 1 + PIVOT_WINDOW_BARS):
        ma = sma_at(bars[: j + 1], 20)
        if ma is not None and float(bars[j].close) < ma:
            return False
    return True


def describe(values: Sequence[float], label: str, unit: str = "%") -> str:
    n = len(values)
    if n < MIN_EPISODES_PER_CELL:
        return f"    {label:<34} UNDERPOWERED (n={n}, floor {MIN_EPISODES_PER_CELL})"
    q1, q3 = statistics.quantiles(values, n=4)[0], statistics.quantiles(values, n=4)[2]
    return (f"    {label:<34} n={n:<5} mean {statistics.mean(values):+7.2f}{unit}"
            f"  median {statistics.median(values):+7.2f}{unit}"
            f"  IQR [{q1:+.2f}, {q3:+.2f}]")


def rate(flags: Sequence[Optional[bool]], label: str) -> str:
    vals = [f for f in flags if f is not None]
    n = len(vals)
    if n < MIN_EPISODES_PER_CELL:
        return f"    {label:<34} UNDERPOWERED (n={n}, floor {MIN_EPISODES_PER_CELL})"
    return f"    {label:<34} n={n:<5} {sum(vals)/n:6.1%}"


def main(argv: List[str]) -> int:
    path = argv[1] if len(argv) > 1 else "bars.tsv"
    bars_by_symbol = load_bars(path)
    if not bars_by_symbol:
        print(f"no bars loaded from {path}", file=sys.stderr)
        return 1

    # Index every symbol's bars by date once; the scan is re-run per date but the
    # forward lookups must not re-sort 93 series 1,100 times.
    index: Dict[str, Dict[date, int]] = {
        s: {b.date: i for i, b in enumerate(bars)} for s, bars in bars_by_symbol.items()
    }
    all_dates = sorted({b.date for bars in bars_by_symbol.values() for b in bars})

    cfg = ScanConfig(seam_allowlist=KNOWN_PROVIDER_SEAMS, max_candidates=0)
    rng = random.Random(RANDOM_SEED)

    # Scan every date that can carry a full funnel AND a full forward window.
    scan_dates = [d for d in all_dates[SMA_SLOW + 5: -max(HORIZONS) - 1]]
    print(f"S-5a — method correctness. Pre-registered: "
          f"docs/s5a_method_correctness_preregistration.md")
    print(f"  universe {len(bars_by_symbol)} symbols | {all_dates[0]} .. {all_dates[-1]} "
          f"| {len(scan_dates)} scan dates")
    print(f"  production ScanConfig() defaults, unmodified\n")

    last_seen: Dict[str, int] = {}          # symbol -> ordinal of its last candidacy
    candidates: List[Outcome] = []
    arm_liq: List[Outcome] = []
    arm_rand: List[Outcome] = []
    dates_with_candidates = 0

    for ordinal, d in enumerate(scan_dates):
        report = run_scan(bars_by_symbol, d, cfg)
        if not report.ranked_universe:
            continue

        # Breadth from the scan's OWN trend clauses (§6) — no new indicator.
        templates = list(report.failed_trend) + [c.trend for c in report.candidates]
        above = sum(1 for t in templates
                    if t.close is not None and t.sma_slow is not None and t.close > t.sma_slow)
        regime = "BROAD" if above / max(1, len(templates)) > BROAD_REGIME_SHARE else "NARROW"

        # ARM-LIQ: everything that passed the liquidity floor = ranked universe.
        liq_symbols = [c.symbol for c in report.candidates] + \
                      [t.symbol for t in report.failed_trend] + \
                      [b.symbol for b in report.failed_base]

        def measure(symbol: str, pivot: Optional[float]) -> Optional[Outcome]:
            bars = bars_by_symbol[symbol]
            i = index[symbol].get(d)
            if i is None:
                return None
            rets: Dict[int, float] = {}
            for h in HORIZONS:
                if window_has_seam(bars, i, h):
                    return None                      # §8
                r = forward_return(bars, i, h)
                if r is None:
                    return None                      # §8
                rets[h] = r
            return Outcome(
                symbol=symbol, scan_date=d, regime=regime, returns=rets, excess={},
                pivot_cleared=cleared_pivot(bars, i, pivot) if pivot is not None else None,
                cleared_prior_high=cleared_prior_high(bars, i),
                held_ma20=held_ma20(bars, i),
            )

        liq_outcomes = [o for o in (measure(s, None) for s in liq_symbols) if o]
        if not liq_outcomes:
            continue
        liq_mean = {h: statistics.mean(o.returns[h] for o in liq_outcomes) for h in HORIZONS}

        def with_excess(o: Outcome) -> Outcome:
            return Outcome(o.symbol, o.scan_date, o.regime, o.returns,
                           {h: o.returns[h] - liq_mean[h] for h in HORIZONS},
                           o.pivot_cleared, o.cleared_prior_high, o.held_ma20)

        arm_liq.extend(with_excess(o) for o in liq_outcomes)

        # EPISODES (§3): first candidacy after >= EPISODE_GAP_BARS of absence.
        fresh = []
        for c in report.candidates:
            prev = last_seen.get(c.symbol)
            last_seen[c.symbol] = ordinal
            if prev is not None and ordinal - prev < EPISODE_GAP_BARS:
                continue
            o = measure(c.symbol, c.base.pivot.level if c.base and c.base.pivot else None)
            if o:
                fresh.append(with_excess(o))
        if fresh:
            dates_with_candidates += 1
            candidates.extend(fresh)
            # ARM-RANDOM: same size, same date, seeded (§5).
            pool = [o for o in liq_outcomes if o.symbol not in {f.symbol for f in fresh}]
            for o in rng.sample(pool, min(len(fresh), len(pool))):
                arm_rand.append(with_excess(o))

    # ── Report ────────────────────────────────────────────────────────────
    print(f"EPISODES: {len(candidates)} across {dates_with_candidates} dates "
          f"(gap {EPISODE_GAP_BARS} bars) | ARM-LIQ observations {len(arm_liq)} "
          f"| ARM-RANDOM {len(arm_rand)}\n")

    print("PRIMARY — excess forward return vs the SAME-DATE liquid-universe mean")
    print("  (same-date differencing removes the market factor; §4)")
    for h in HORIZONS:
        print(f"  +{h} bars")
        print(describe([o.excess[h] for o in candidates], "candidates"))
        print(describe([o.excess[h] for o in arm_rand], "ARM-RANDOM"))
    print()

    print("SECONDARY — breakout within 20 bars, measured on CLOSE (§4)")
    print("  Like-for-like across all three arms: closed above its own trailing")
    print("  20-bar high. The arms have no base, so this is the only level all")
    print("  three share (§5 forbids a statistic with no benchmark).")
    print(rate([o.cleared_prior_high for o in candidates], "candidates"))
    print(rate([o.cleared_prior_high for o in arm_rand], "ARM-RANDOM"))
    print(rate([o.cleared_prior_high for o in arm_liq], "ARM-LIQ (all liquid names)"))
    print("  And the candidates against their OWN base pivot, which is the level")
    print("  the method actually draws:")
    print(rate([o.pivot_cleared for o in candidates], "candidates clear their base pivot"))
    print()

    print("REGIME SPLIT (§6) — pre-registered expectation: BROAD > NARROW")
    for reg in ("BROAD", "NARROW"):
        sub = [o for o in candidates if o.regime == reg]
        print(f"  {reg} ({len(sub)} episodes)")
        for h in HORIZONS:
            print(describe([o.excess[h] for o in sub], f"candidate excess +{h}"))
    print()

    print("THE METHOD'S OWN EXIT RULE — holding MA20 for 20 bars (§9)")
    held = [o for o in candidates if o.held_ma20 is True]
    lost = [o for o in candidates if o.held_ma20 is False]
    for h in HORIZONS:
        print(describe([o.excess[h] for o in held], f"held MA20, excess +{h}"))
        print(describe([o.excess[h] for o in lost], f"lost MA20, excess +{h}"))
    print()

    print("READ THIS BESIDE EVERY NUMBER ABOVE")
    print("  Evidence about MECHANISM, not an estimate of edge. Candidates arrive in")
    print("  bursts and 5.5 years of VN data holds one bear market, so no significance")
    print("  test is run and none should be inferred. A return figure quoted from here")
    print("  as a forecast is the overclaim C4 exists to prevent.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
