"""EM-4 — the Magee Evaluative Index (E&M Ch 38).

Magee: keep daily charts on ~100 stocks, mark each **+** or **−** by its major
trend, total them — *"if 75 are plus, the market looks 75% Bullish to you."*

`compute_regime` stands in for his eye: TREND_UP is his **+**. That
substitution makes the measure mechanical where his was expert, which is a
change in character and not only in convenience — so these tests pin the
*construction*, and `tests/em4_mei_study.py` tests whether the mechanical
version carries the information he claimed.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Dict, List

import pytest

from app.services.breadth.mei import (
    MIN_UNIVERSE,
    compute_mei_series,
    percentile_of,
)
from app.services.signal.base import OHLCVBar


def _series(slope: float, n: int = 120, start: float = 100.0) -> List[OHLCVBar]:
    """A clean trend: `slope` per bar as a fraction."""
    out = []
    price = start
    day = date(2022, 1, 3)
    for _ in range(n):
        price *= (1.0 + slope)
        out.append(OHLCVBar(date=day, open=price, high=price * 1.005,
                            low=price * 0.995, close=price, volume=1_000_000))
        day += timedelta(days=1)
    return out


def _universe(n_up: int, n_down: int, n_flat: int = 0) -> Dict[str, List[OHLCVBar]]:
    u: Dict[str, List[OHLCVBar]] = {}
    for i in range(n_up):
        u[f"UP{i}"] = _series(+0.004)
    for i in range(n_down):
        u[f"DN{i}"] = _series(-0.004)
    for i in range(n_flat):
        u[f"FL{i}"] = _series(0.0)
    return u


# ---------------------------------------------------------------------------
# The construction
# ---------------------------------------------------------------------------

class TestConstruction:

    def test_all_advancing_reads_one_hundred_percent(self):
        series = compute_mei_series(_universe(n_up=12, n_down=0))
        assert series
        assert series[-1].mei == pytest.approx(100.0)

    def test_all_declining_reads_zero(self):
        series = compute_mei_series(_universe(n_up=0, n_down=12))
        assert series[-1].mei == pytest.approx(0.0)

    def test_magees_example_reads_as_he_states_it(self):
        """"If 75 are plus, the market looks 75% Bullish to you." Built as 15
        advancing and 5 declining — the ratio, not the count, is the claim."""
        series = compute_mei_series(_universe(n_up=15, n_down=5))
        assert series[-1].mei == pytest.approx(75.0)
        assert series[-1].bullish == 15
        assert series[-1].bearish == 5

    def test_range_counts_against_bullish_in_the_primary_measure(self):
        """RANGE is not a plus. `mei` is "what share of the market is
        advancing", so a flat stock lowers it."""
        series = compute_mei_series(_universe(n_up=10, n_down=0, n_flat=10))
        assert series[-1].mei == pytest.approx(50.0)
        assert series[-1].neutral == 10

    def test_the_binary_reading_excludes_neutral_as_magee_did(self):
        """He marked + or − with no third option, so the binary variant drops
        RANGE from the denominator. Both are reported; they answer different
        questions."""
        point = compute_mei_series(_universe(n_up=10, n_down=0, n_flat=10))[-1]
        assert point.mei == pytest.approx(50.0)
        assert point.mei_excluding_neutral == pytest.approx(100.0)

    def test_the_binary_reading_is_none_when_nothing_has_direction(self):
        point = compute_mei_series(_universe(n_up=0, n_down=0, n_flat=14))[-1]
        assert point.mei_excluding_neutral is None


# ---------------------------------------------------------------------------
# Causality — the binding constraint
# ---------------------------------------------------------------------------

class TestCausality:

    def test_appending_future_bars_changes_no_past_reading(self):
        """Magee's index is a running judgement, not a retrospective one. If a
        later bar could move an earlier reading, every study built on the
        series would be contaminated."""
        universe = _universe(n_up=8, n_down=6)
        cut = 90
        past = {s: b[:cut] for s, b in universe.items()}

        before = compute_mei_series(past)
        after = compute_mei_series(universe)
        after_trimmed = [p for p in after if p.day <= before[-1].day]

        assert [(p.day, p.mei) for p in before] == [
            (p.day, p.mei) for p in after_trimmed
        ]

    def test_the_percentile_window_is_strictly_the_past(self):
        """An "extreme" is only definable against a distribution, and using
        the whole series would be look-ahead."""
        series = compute_mei_series(_universe(n_up=8, n_down=6))
        assert percentile_of(series, 0) is None
        mid = percentile_of(series, len(series) // 2)
        assert mid is None or 0.0 <= mid <= 100.0


# ---------------------------------------------------------------------------
# Thin and ragged data
# ---------------------------------------------------------------------------

class TestThinData:

    def test_a_universe_below_the_minimum_yields_nothing(self):
        """Magee kept ~100 charts. A reading off three would be noise wearing
        a percentage sign, so it is withheld rather than reported."""
        assert compute_mei_series(_universe(n_up=2, n_down=1)) == []

    def test_the_minimum_is_stated_not_implicit(self):
        assert MIN_UNIVERSE >= 10

    def test_symbols_with_different_calendars_are_handled(self):
        """Symbols list at different times and halt independently, so the
        calendars do not line up. A symbol contributes only from its own
        first bar."""
        universe = _universe(n_up=12, n_down=0)
        late = _series(-0.004, n=40)
        shift = timedelta(days=60)
        universe["LATE"] = [
            OHLCVBar(date=b.date + shift, open=b.open, high=b.high,
                     low=b.low, close=b.close, volume=b.volume)
            for b in late
        ]
        series = compute_mei_series(universe)
        assert series
        assert max(p.classified for p in series) >= 12

    def test_an_empty_universe_is_inert(self):
        assert compute_mei_series({}) == []


class TestDeterminism:

    def test_repeated_runs_are_identical(self):
        universe = _universe(n_up=9, n_down=5)
        assert compute_mei_series(universe) == compute_mei_series(universe)
