"""EM-6 D1 — Dow's primary trend from successive swing highs and lows.

E&M Ch 3, the tenets this module is accountable to:

* **tenet 8** — the primary trend is read from successively higher tops *and*
  bottoms (or lower ones). Both, never one.
* **tenet 11** — *"Only Closing Prices Used"*; intraday extremes are ignored
  and any penetration, even 0.01, counts.
* **tenet 12** — *"A Trend Is Assumed to Continue Until Reversal Is Definitely
  Signaled"*. So an incomplete turn — a higher high without a higher low —
  leaves the previous trend standing. It does not clear it, and it does not
  flip it.

These tests pin the *construction*. Whether the construction carries any
information about forward returns is `D3`'s question, and `D3` is a gate that
can close EM-6 (`docs/implementation_plan_em6_dow_gate.md` §4).
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import List, Sequence

import pytest

from app.services.market_context import dow
from app.services.market_context.dow import (
    DEFAULT_SWING_PCT,
    TREND_DOWN,
    TREND_UP,
    UNDEFINED,
    confirmed_pivots,
    swing_trend_series,
)
from app.services.signal.base import OHLCVBar


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------

def _legs(points: Sequence[float], bars_per_leg: int = 10) -> List[OHLCVBar]:
    """A zigzag through `points`, linearly interpolated.

    The high/low of each bar is deliberately set *wrong* — a wide band around
    the close — so that any rule reading them instead of the close shows up.
    """
    closes = [float(points[0])]
    for a, b in zip(points, points[1:]):
        for j in range(1, bars_per_leg + 1):
            closes.append(a + (b - a) * j / bars_per_leg)

    day = date(2020, 1, 1)
    bars = []
    for c in closes:
        bars.append(OHLCVBar(date=day, open=c, high=c * 1.20, low=c * 0.80,
                             close=c, volume=1_000_000))
        day += timedelta(days=1)
    return bars


#: higher highs (120 -> 130) AND higher lows (105 -> 112): a Dow uptrend.
UP_POINTS = [100, 120, 105, 130, 112, 140]

#: lower highs (100 -> 88) AND lower lows (80 -> 70): a Dow downtrend.
DOWN_POINTS = [100, 80, 88, 70, 76]


# ---------------------------------------------------------------------------
# H-D6 — planted construction
# ---------------------------------------------------------------------------

class TestThePlantedTrends:

    def test_higher_highs_and_higher_lows_is_an_uptrend(self):
        out = swing_trend_series(_legs(UP_POINTS))
        assert out[-1] == TREND_UP

    def test_lower_highs_and_lower_lows_is_a_downtrend(self):
        out = swing_trend_series(_legs(DOWN_POINTS))
        assert out[-1] == TREND_DOWN

    def test_a_monotone_rise_never_declares_a_trend(self):
        """No reaction, so no confirmed pivot, so nothing to compare.

        This is the honest consequence of Dow's definition rather than a
        shortcoming: a trend is read from *successive* tops and bottoms, and a
        straight line has none.
        """
        bars = _legs([100, 200], bars_per_leg=200)
        assert set(swing_trend_series(bars)) == {UNDEFINED}

    def test_the_trend_is_declared_only_once_four_pivots_exist(self):
        """Not before: two highs and two lows are needed to compare both.

        And not at the bar the fourth pivot *formed* on — at the later bar
        that *confirmed* it. Reading `Pivot.index` here instead of
        `confirmed_index` is precisely the look-ahead the two fields exist to
        keep apart, and this test was written that way first.
        """
        bars = _legs(UP_POINTS)
        out = swing_trend_series(bars)
        pivots = confirmed_pivots(bars)

        formed, confirmed = pivots[3].index, pivots[3].confirmed_index
        assert formed < confirmed, "the fixture must confirm after the fact"

        assert all(s == UNDEFINED for s in out[:confirmed])
        assert out[confirmed] == TREND_UP
        assert out[formed] == UNDEFINED, (
            "declaring the trend at the forming bar would be look-ahead"
        )

    def test_every_bar_gets_exactly_one_reading(self):
        bars = _legs(UP_POINTS)
        assert len(swing_trend_series(bars)) == len(bars)


# ---------------------------------------------------------------------------
# tenet 12 — a trend stands until reversal is *definitely* signalled
# ---------------------------------------------------------------------------

class TestTenet12:

    def test_a_higher_high_with_a_lower_low_leaves_the_uptrend_standing(self):
        """The rule E&M stress most, and the easiest to get wrong.

        Appended to the uptrend: a higher high (140) followed by a *lower* low
        (105 < 112). One condition of two. E&M are explicit that this is not a
        reversal signal, so the trend must neither flip nor clear.
        """
        bars = _legs(UP_POINTS + [105, 116])
        out = swing_trend_series(bars)

        pivots = confirmed_pivots(bars)
        highs = [p.price for p in pivots if p.kind == "HIGH"]
        lows = [p.price for p in pivots if p.kind == "LOW"]
        assert highs[-1] > highs[-2], "fixture must make a higher high"
        assert lows[-1] < lows[-2], "fixture must make a lower low"

        assert out[-1] == TREND_UP

    def test_a_declared_trend_is_never_reset_to_undefined(self):
        bars = _legs(UP_POINTS + [105, 116, 108, 118])
        out = swing_trend_series(bars)
        first = next(i for i, s in enumerate(out) if s != UNDEFINED)
        assert all(s != UNDEFINED for s in out[first:])


# ---------------------------------------------------------------------------
# tenet 11 — closing prices only
# ---------------------------------------------------------------------------

class TestTenet11:

    def test_intraday_extremes_do_not_participate(self):
        """Closes held fixed, highs and lows made absurd: nothing may move."""
        bars = _legs(UP_POINTS)
        mangled = [
            OHLCVBar(date=b.date, open=b.open, high=b.close * 10.0,
                     low=b.close / 10.0, close=b.close, volume=b.volume)
            for b in bars
        ]
        assert swing_trend_series(mangled) == swing_trend_series(bars)

    def test_any_penetration_counts_however_small(self):
        """E&M reject a minimum-move filter: the authors' own words.

        Two series whose confirmed highs differ by a hair must still be
        ordered by it — there is no dead band.
        """
        a = swing_trend_series(_legs([100, 120, 105, 120.001, 112, 140]))
        assert a[-1] == TREND_UP


# ---------------------------------------------------------------------------
# H-D1 causality, H-D4 determinism
# ---------------------------------------------------------------------------

class TestCausalityAndDeterminism:

    def test_appending_future_bars_changes_no_past_reading(self):
        bars = _legs(UP_POINTS)
        before = swing_trend_series(bars)
        extended = bars + _legs([140, 90, 95], bars_per_leg=12)
        after = swing_trend_series(extended)
        assert after[:len(before)] == before

    @pytest.mark.parametrize("cut", [30, 55, 80])
    def test_a_truncated_series_matches_the_prefix_of_the_full_one(self, cut):
        bars = _legs(UP_POINTS)
        assert swing_trend_series(bars[:cut]) == swing_trend_series(bars)[:cut]

    def test_repeated_runs_are_identical(self):
        bars = _legs(UP_POINTS)
        assert swing_trend_series(bars) == swing_trend_series(bars)


# ---------------------------------------------------------------------------
# the threshold, and H-D5 the bound-default guard
# ---------------------------------------------------------------------------

class TestTheThreshold:

    def test_a_larger_threshold_confirms_fewer_pivots(self):
        bars = _legs(UP_POINTS)
        assert len(confirmed_pivots(bars, pct=0.02)) >= len(confirmed_pivots(bars, pct=0.15))

    def test_a_threshold_too_large_for_the_reactions_declares_nothing(self):
        bars = _legs(UP_POINTS)
        assert set(swing_trend_series(bars, pct=0.50)) == {UNDEFINED}

    def test_the_threshold_is_read_at_call_time_not_frozen_at_import(self, monkeypatch):
        """H-D5. The trap this project has paid for five times.

        A parameter whose default is a module constant read in the signature
        is bound once at def time, so patching the constant is a silent no-op
        and a sweep over it reads as "flat, the parameter does not matter"
        (EM-1 S2, #78, W1, #84, and #87's HISTORY_YEARS).

        `_legs(UP_POINTS)`'s reactions are 12-16%, so 5% confirms them and 50%
        cannot. If the default were frozen, both calls below would return the
        same thing.
        """
        bars = _legs(UP_POINTS)
        assert swing_trend_series(bars)[-1] == TREND_UP

        monkeypatch.setattr(dow, "DEFAULT_SWING_PCT", 0.50)
        assert swing_trend_series(bars)[-1] == UNDEFINED, (
            "DEFAULT_SWING_PCT is not being read at call time"
        )

    def test_the_shipped_default_is_the_one_the_srs_registered(self):
        assert DEFAULT_SWING_PCT == 0.05


# ---------------------------------------------------------------------------
# thin data
# ---------------------------------------------------------------------------

class TestThinData:

    def test_an_empty_series_is_inert(self):
        assert swing_trend_series([]) == []
        assert confirmed_pivots([]) == []

    def test_a_single_bar_is_undefined(self):
        bars = _legs([100, 100], bars_per_leg=1)[:1]
        assert swing_trend_series(bars) == [UNDEFINED]
