"""EM-3 — the basing-point stop engine (E&M Ch 28, Bassetti Ch 28.1).

Bassetti calls Ch 28 *"of absolutely basic importance"*. Its four rules, as he
numbers them:

  1. A high is made, recognised by no higher prices for the moment.
  2. Prices recede to a candidate low; watch each later day whose range lies
     **completely outside** the candidate's range.
  3. When **three such days** occur before a new low, the candidate becomes a
     **basing point** — raise the stop to x% under the low of that day.
  4. When a new high exceeds the previous high by **3%**, a new basing point
     is set at the low of that new-high day.

Stops are **never** lowered, even when a later low undercuts an old one. The
filter is what keeps the position, and the rationale is Kovner's, quoted by
Bassetti: put stops *"where they're hard to get to"*, because locals hunt the
obvious prior low.

Why this is not the shipped SWING stop
--------------------------------------
`stop_module`'s SWING stop sits at the nearest confirmed pivot — which is
*exactly* the obvious prior low E&M warn is hunted. The basing point differs
in two ways that matter: it requires **three full days clear** of the
candidate before trusting it at all, and it then sits a **filter** below it.

Rule 4 is behind a flag
-----------------------
E&M's own caveat, which the register carried forward: advancing the stop on
new highs as well can force a premature exit on a mid-trend blow-off. Bassetti
teaches a "simplified version" using only wave lows. So rule 4 is optional and
measured separately, per `EM-3`'s risk note.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

import pytest

from app.services.risk.basing_point import (
    DEFAULT_FILTER_PCT,
    DEFAULT_NEW_HIGH_PCT,
    DAYS_AWAY,
    BasingPointTracker,
)


@dataclass
class Bar:
    """Only the three fields the rules read."""
    high: float
    low: float
    close: float


def _bar(high: float, low: float, close: Optional[float] = None) -> Bar:
    return Bar(high=high, low=low, close=close if close is not None else (high + low) / 2)


def _feed(tracker: BasingPointTracker, bars: List[Bar]) -> List[Optional[float]]:
    """Push bars one at a time and collect the stop after each."""
    return [tracker.update(b.high, b.low, b.close) for b in bars]


# ---------------------------------------------------------------------------
# Rule 3 — the three-days-away confirmation
# ---------------------------------------------------------------------------

class TestThreeDaysAway:

    def test_a_candidate_low_is_not_trusted_until_three_days_are_clear(self):
        """The whole point of the rule: a low is not a basing point just
        because it is a low."""
        t = BasingPointTracker(direction="LONG")
        # candidate low day, then two clear days — not yet three
        _feed(t, [_bar(104, 100), _bar(106, 101), _bar(107, 102)])
        assert t.basing_point is None
        assert t.stop is None

    def test_three_clear_days_confirm_the_basing_point(self):
        t = BasingPointTracker(direction="LONG")
        _feed(t, [_bar(104, 100), _bar(106, 105), _bar(107, 106), _bar(108, 107)])
        assert t.basing_point == pytest.approx(100.0)

    def test_a_day_must_lie_COMPLETELY_outside_the_candidate_range(self):
        """Bassetti's wording, and it is the strict reading: the day's whole
        range must clear the candidate day's. A day that merely closes higher
        while still overlapping does not count."""
        t = BasingPointTracker(direction="LONG")
        # candidate 100-104; the next three overlap it, so none counts
        _feed(t, [_bar(104, 100), _bar(105, 103), _bar(106, 102), _bar(107, 101)])
        assert t.basing_point is None

    def test_the_count_resets_when_a_new_low_is_made(self):
        """'...before a new low is made.' A fresh low replaces the candidate
        and the three days start again."""
        t = BasingPointTracker(direction="LONG")
        _feed(t, [_bar(104, 100), _bar(106, 105), _bar(103, 98)])  # new low
        assert t.basing_point is None
        assert t.candidate_low == pytest.approx(98.0)

    def test_the_number_of_days_is_the_books_three(self):
        assert DAYS_AWAY == 3


# ---------------------------------------------------------------------------
# The filter — "where they're hard to get to"
# ---------------------------------------------------------------------------

class TestTheFilter:

    def test_the_stop_sits_below_the_basing_point_not_on_it(self):
        t = BasingPointTracker(direction="LONG", filter_pct=6.0)
        _feed(t, [_bar(104, 100), _bar(106, 105), _bar(107, 106), _bar(108, 107)])
        assert t.stop == pytest.approx(94.0)

    def test_the_filter_default_is_the_books_figure(self):
        assert DEFAULT_FILTER_PCT == pytest.approx(6.0)

    def test_a_short_puts_the_stop_above_the_basing_point(self):
        t = BasingPointTracker(direction="SHORT", filter_pct=6.0)
        _feed(t, [_bar(100, 96), _bar(95, 90), _bar(94, 89), _bar(93, 88)])
        assert t.basing_point == pytest.approx(100.0)
        assert t.stop == pytest.approx(106.0)


# ---------------------------------------------------------------------------
# The inviolable rule
# ---------------------------------------------------------------------------

class TestTheStopIsNeverLowered:

    def test_a_later_lower_basing_point_does_not_lower_the_stop(self):
        """E&M are explicit, and Bassetti calls it inviolable: the stop is
        never lowered even when a later low undercuts an old one. The filter
        is what keeps the position through the probe."""
        t = BasingPointTracker(direction="LONG", filter_pct=6.0)
        _feed(t, [_bar(104, 100), _bar(106, 105), _bar(107, 106), _bar(108, 107)])
        high_water = t.stop
        assert high_water == pytest.approx(94.0)

        # a deeper low, then three clear days above it
        _feed(t, [_bar(96, 90), _bar(99, 97), _bar(100, 98), _bar(101, 99)])
        assert t.stop == pytest.approx(high_water), "the stop moved down"

    def test_it_rises_when_a_higher_basing_point_forms(self):
        t = BasingPointTracker(direction="LONG", filter_pct=6.0)
        _feed(t, [_bar(104, 100), _bar(106, 105), _bar(107, 106), _bar(108, 107)])
        first = t.stop
        _feed(t, [_bar(120, 110), _bar(126, 122), _bar(127, 123), _bar(128, 124)])
        assert t.stop > first

    def test_a_short_stop_is_never_raised(self):
        t = BasingPointTracker(direction="SHORT", filter_pct=6.0)
        _feed(t, [_bar(100, 96), _bar(95, 90), _bar(94, 89), _bar(93, 88)])
        best = t.stop
        _feed(t, [_bar(112, 108), _bar(106, 102), _bar(105, 101), _bar(104, 100)])
        assert t.stop == pytest.approx(best)


# ---------------------------------------------------------------------------
# Rule 4 — the 3% new high, behind a flag
# ---------------------------------------------------------------------------

class TestTheNewHighRule:

    @staticmethod
    def _run(enabled: bool) -> BasingPointTracker:
        t = BasingPointTracker(direction="LONG", filter_pct=6.0, use_new_high_rule=enabled)
        # confirm a first basing point at 100
        _feed(t, [_bar(104, 100), _bar(106, 105), _bar(107, 106), _bar(108, 107)])
        # then a new high more than 3% above the previous high of 108
        _feed(t, [_bar(120, 112)])
        return t

    def test_a_new_high_beyond_the_threshold_sets_a_basing_point_at_that_days_low(self):
        t = self._run(enabled=True)
        assert t.basing_point == pytest.approx(112.0)
        assert t.stop == pytest.approx(112.0 * 0.94)

    def test_it_does_nothing_when_the_flag_is_off(self):
        """E&M's own caveat: advancing on new highs can force a premature exit
        on a mid-trend blow-off, so Bassetti teaches a simplified version
        using only wave lows. The flag exists so the two are measurable
        separately."""
        t = self._run(enabled=False)
        assert t.basing_point == pytest.approx(100.0)

    def test_a_new_high_inside_the_threshold_does_nothing(self):
        t = BasingPointTracker(direction="LONG", use_new_high_rule=True)
        _feed(t, [_bar(104, 100), _bar(106, 105), _bar(107, 106), _bar(108, 107)])
        before = t.basing_point
        _feed(t, [_bar(109, 108)])            # only ~0.9% above 108
        assert t.basing_point == pytest.approx(before)

    def test_the_threshold_is_the_books_figure(self):
        assert DEFAULT_NEW_HIGH_PCT == pytest.approx(3.0)


# ---------------------------------------------------------------------------
# Contract, causality, robustness
# ---------------------------------------------------------------------------

class TestContract:

    def test_update_returns_the_current_stop_or_none(self):
        t = BasingPointTracker(direction="LONG")
        assert t.update(104, 100, 102) is None
        _feed(t, [_bar(106, 105), _bar(107, 106), _bar(108, 107)])
        assert isinstance(t.stop, float)

    def test_it_only_ever_sees_one_bar_at_a_time(self):
        """Causality by construction: the tracker is fed bar by bar and holds
        no reference to the series, so it cannot read a future bar even by
        accident."""
        import inspect

        src = inspect.getsource(BasingPointTracker.update)
        for forbidden in ("bars", "[i +", "iloc", "shift(-"):
            assert forbidden not in src

    def test_feeding_the_same_bars_twice_gives_the_same_answer(self):
        bars = [_bar(104, 100), _bar(106, 105), _bar(107, 106), _bar(108, 107)]
        a = BasingPointTracker(direction="LONG")
        b = BasingPointTracker(direction="LONG")
        assert _feed(a, bars) == _feed(b, bars)

    def test_a_flat_series_never_confirms_a_basing_point(self):
        """No day can lie completely outside another identical day, so the
        rule correctly refuses to find a basing point."""
        t = BasingPointTracker(direction="LONG")
        _feed(t, [_bar(100, 100) for _ in range(20)])
        assert t.basing_point is None

    def test_an_unknown_direction_is_inert_rather_than_wrong(self):
        t = BasingPointTracker(direction="SIDEWAYS")
        _feed(t, [_bar(104, 100), _bar(106, 105), _bar(107, 106), _bar(108, 107)])
        assert t.stop is None
