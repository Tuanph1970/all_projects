"""VT-4 — what the funnel emits when there is nothing to find.

THE NUMBER THIS PRODUCES IS NOT A DIAGNOSTIC, IT IS PART OF THE OUTPUT. The
project's standing constraint C4 requires a pattern detector to be reported
beside a random-walk null FPR, and EC-S5 repeats it for this module: a funnel
that fires as often on noise as on real data has no content, however plausible
its shortlist reads. A candidate list shown without this number invites the
reader to assume selectivity that has never been measured.

Calibration, measured on this database 2026-11-09 across 122,820 daily returns
with seam-sized moves excluded: SD of daily log returns **2.405%**, mean
**+0.0079%/day**. The drift is kept rather than zeroed — a pure martingale would
fail FR-SCAN-TREND's prior-advance clause almost always and would flatter the
funnel by testing it against a market that never rises.

WHAT A LOW NUMBER HERE DOES AND DOES NOT PROVE. It establishes that the funnel
is selective against noise — necessary, and not sufficient. It says nothing
about whether the names it DOES emit go up, which is VT-5 and needs months of
persisted live runs. Quoting this figure as evidence of edge would be exactly
the overclaim C4 exists to prevent.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Dict, List, Optional, Sequence

from app.services.signal.base import OHLCVBar

#: Measured on `stock_prices`, 93 symbols, 2021-03-15..2026-11-06.
VN_DAILY_LOG_SD = 0.02405
VN_DAILY_LOG_MEAN = 0.000079

#: Intraday range as a multiple of the day's absolute return, so synthetic bars
#: have a plausible high/low rather than high == low == close. A degenerate bar
#: would make every true range tiny and hand the squeeze test a free pass.
INTRADAY_RANGE_MULTIPLE = 1.6


@dataclass(frozen=True)
class NullFprResult:
    trials: int
    universe_size: int
    bars_per_symbol: int
    trials_with_candidates: int
    total_candidates: int
    symbols_tested: int

    @property
    def trial_fpr(self) -> float:
        """Share of synthetic universes that produced ANY candidate — the rate
        at which a user opening the screen on noise would see something."""
        return self.trials_with_candidates / self.trials if self.trials else 0.0

    @property
    def symbol_fpr(self) -> float:
        """Share of synthetic SYMBOLS admitted. The stricter reading, and the
        one comparable with the live funnel's qualified-over-ranked ratio."""
        return self.total_candidates / self.symbols_tested if self.symbols_tested else 0.0


def random_walk(
    rng: random.Random,
    bars: int,
    *,
    start_price: float = 30.0,
    daily_log_sd: float = VN_DAILY_LOG_SD,
    daily_log_mean: float = VN_DAILY_LOG_MEAN,
    base_volume: float = 1_500_000.0,
    first_date: date = date(2020, 1, 2),
) -> List[OHLCVBar]:
    """A geometric random walk with VN-calibrated daily volatility.

    Volume is lognormal and INDEPENDENT of price, which is the point: any
    volume dry-up the funnel finds in this series is coincidence, so
    FR-SCAN-SQUEEZE has nothing real to detect and its hit rate here is pure
    false-positive rate.
    """
    out: List[OHLCVBar] = []
    price = start_price
    day = first_date
    for _ in range(bars):
        prev = price
        step = rng.gauss(daily_log_mean, daily_log_sd)
        price = prev * math.exp(step)
        half = abs(price - prev) * INTRADAY_RANGE_MULTIPLE / 2.0 + prev * 0.001
        mid = (price + prev) / 2.0
        out.append(OHLCVBar(
            date=day,
            open=prev,
            high=max(prev, price) + half,
            low=max(0.01, min(prev, price) - half),
            close=price,
            volume=max(1.0, rng.lognormvariate(math.log(base_volume), 0.45)),
        ))
        day += timedelta(days=1)
    return out


def estimate_null_fpr(
    run_scan_fn,
    config,
    *,
    trials: int = 50,
    universe_size: int = 93,
    bars_per_symbol: int = 400,
    seed: int = 20261109,
    start_price: float = 30.0,
) -> NullFprResult:
    """Run the real funnel over `trials` synthetic universes.

    `run_scan_fn` and `config` are injected rather than imported so this module
    cannot drift out of step with the funnel it is supposed to be measuring —
    the null is computed by the SAME code path that produces the live list, not
    by a reimplementation of it.

    Seeded, so the reported figure is reproducible (NFR-S2).
    """
    rng = random.Random(seed)
    with_candidates = 0
    total = 0
    tested = 0
    for _ in range(trials):
        universe: Dict[str, List[OHLCVBar]] = {
            f"N{i:03d}": random_walk(rng, bars_per_symbol, start_price=start_price)
            for i in range(universe_size)
        }
        as_of = max(b.date for s in universe.values() for b in s)
        report = run_scan_fn(universe, as_of, config)
        n = len(report.candidates) + len(report.excess_qualified)
        total += n
        tested += report.ranked_universe
        if n:
            with_candidates += 1
    return NullFprResult(
        trials=trials,
        universe_size=universe_size,
        bars_per_symbol=bars_per_symbol,
        trials_with_candidates=with_candidates,
        total_candidates=total,
        symbols_tested=tested,
    )
