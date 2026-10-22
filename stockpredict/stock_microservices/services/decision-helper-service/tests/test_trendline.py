"""EM-5 L1 — the admissible-line enumerator (`FR-EM-L1`..`L3`).

E&M Ch 14 draws up trendlines across the minor-reaction **bottoms** and down
lines across the minor-rally **tops** — *never bottom-to-top, never through
the price track* — and is explicit about which price to use:

> Intraday breaks that don't close beyond the line are ignored — **"closing
> prices often make a better trendline than extreme lows, especially in thin
> erratic stocks."**

The method is also explicitly plural: *"draw every line the action permits,
lightly; erase the useless, heavy the survivors."* So the engine **enumerates**
rather than choosing, and the thing that keeps the set finite is the
**price-track constraint**, not a cap — because a cap doing the pruning would
make the line set a function of the cap rather than of the price action.
"""
from __future__ import annotations

import math
from datetime import date, timedelta
from typing import List, Sequence

import pytest

from app.services.market_context import trendline as tl
from app.services.market_context.trendline import (
    DEFAULT_LOOKBACK,
    DEFAULT_MIN_SPAN,
    DEFAULT_PIVOT_PCT,
    Trendline,
    admissible_lines,
    candidate_pair_count,
)
from app.services.signal.base import OHLCVBar


def _legs(points: Sequence[float], bars_per_leg: int = 8,
          pad: float = 0.4) -> List[OHLCVBar]:
    """A zigzag through `points`, linearly interpolated on the CLOSE.

    Highs and lows are a wide band around the close so that any rule reading
    them instead of the close shows up (`H-L5`).
    """
    closes = [float(points[0])]
    for a, b in zip(points, points[1:]):
        for j in range(1, bars_per_leg + 1):
            closes.append(a + (b - a) * j / bars_per_leg)
    day, out = date(2020, 1, 1), []
    for c in closes:
        out.append(OHLCVBar(date=day, open=c, high=c + pad, low=c - pad,
                            close=c, volume=1_000_000))
        day += timedelta(days=1)
    return out


#: Rising lows at 104 and 108 with a LOWER low (99) between them. The line
#: 104 -> 108 is cut by that dip, so it is inadmissible; the line 99 -> 108
#: is not. One fixture, both cases.
VIOLATED = [100, 112, 104, 110, 99, 115, 108, 122]

#: Two rising lows with nothing between them that dips under the line.
CLEAN_UP = [100, 110, 104, 116, 109, 120]


def _ups(bars) -> List[Trendline]:
    return [ln for ln in admissible_lines(bars) if ln.kind == "UP"]


# ---------------------------------------------------------------------------
# FR-EM-L1 — what counts as a line
# ---------------------------------------------------------------------------

class TestEnumeration:

    def test_up_lines_anchor_on_lows_and_down_lines_on_highs(self):
        """E&M: **never bottom-to-top.** Same-side anchors only.

        The first version asserted only that `kind` was one of two strings and
        that the indices were ordered, so it was strengthened to check the
        anchors against the pivot list itself.

        **It still does not catch a mutation that puts every pivot in both
        groups, and that is because the mutation is EQUIVALENT.** Measured on
        four fixtures including a long zigzag, allowing mixed anchors produces
        an identical line count every time: the price-track constraint rejects
        bottom-to-top lines on its own, because a line between two highs read
        as *support* is necessarily cut by the very closes that made them
        highs — and conversely.

        So "never bottom-to-top" is enforced **twice**: structurally by the
        grouping here, and independently by `FR-EM-L2`. The grouping is kept
        because it is correct, cheap and states the rule where a reader looks
        for it — but it is belt-and-braces, not load-bearing, and recording
        that is the `#89` habit rather than claiming a guard the tests cannot
        exercise.
        """
        from app.services.market_context.dow import confirmed_pivots

        for points in (CLEAN_UP, VIOLATED, [120, 108, 115, 100, 112, 95]):
            bars = _legs(points)
            pivots = confirmed_pivots(bars, pct=DEFAULT_PIVOT_PCT)
            want = {"UP": "LOW", "DOWN": "HIGH"}
            by_index = {(p.index, p.kind) for p in pivots}

            lines = admissible_lines(bars)
            assert lines, f"no lines for {points}"
            for ln in lines:
                assert ln.kind in want
                assert ln.a_index < ln.b_index
                for idx in (ln.a_index, ln.b_index):
                    assert (idx, want[ln.kind]) in by_index, (
                        f"a {ln.kind} line is anchored on bar {idx}, which is "
                        f"not a {want[ln.kind]} pivot — bottom-to-top"
                    )

    def test_a_clean_rising_support_line_is_found(self):
        bars = _legs(CLEAN_UP)
        ups = _ups(bars)
        assert ups, "no support line found in a clean rising zigzag"
        assert any(ln.slope > 0 for ln in ups)

    def test_a_line_evaluates_to_its_own_anchors(self):
        bars = _legs(CLEAN_UP)
        for ln in admissible_lines(bars):
            assert ln.value_at(ln.a_index) == pytest.approx(ln.a_price, abs=1e-6)
            assert ln.value_at(ln.b_index) == pytest.approx(ln.b_price, abs=1e-6)

    def test_an_empty_or_short_frame_yields_nothing(self):
        assert admissible_lines([]) == []
        assert admissible_lines(_legs([100, 101], bars_per_leg=3)) == []


# ---------------------------------------------------------------------------
# H-L4 — the price-track constraint must BITE
# ---------------------------------------------------------------------------

class TestPriceTrackConstraint:

    def test_a_line_cut_by_an_intervening_close_is_rejected(self):
        """`FR-EM-L2`, asserted on the specific pair the fixture was built to
        exclude.

        `VIOLATED` has rising lows near 104 and 108 with a LOWER low near 99
        between them. The 104 -> 108 pair clears the span filter and is
        geometrically fine; it is excluded **solely** because price dipped
        below the connecting line. So the test names that pair rather than
        checking a general property that would also pass if nothing were
        pruned.
        """
        bars = _legs(VIOLATED)
        ups = _ups(bars)
        assert ups, "the fixture produced no support lines at all"

        def anchored_near(lines, lo, hi):
            return [ln for ln in lines
                    if abs(ln.a_price - lo) < 1.5 and abs(ln.b_price - hi) < 1.5]

        assert anchored_near(ups, 99, 108), \
            "the 99 -> 108 line should survive; the fixture is wrong"
        assert not anchored_near(ups, 104, 108), \
            "the 104 -> 108 line is cut by the dip to 99 and must be excluded"

    def test_down_lines_are_not_cut_from_above(self):
        bars = _legs([120, 108, 115, 100, 112, 95])
        for ln in admissible_lines(bars):
            if ln.kind != "DOWN":
                continue
            seg = [b.close for b in bars[ln.a_index:ln.b_index + 1]]
            for k, c in enumerate(seg):
                assert c <= ln.value_at(ln.a_index + k) + 1e-9

    def test_the_constraint_is_what_prunes_not_the_cap(self):
        """`H-L9`. If the admissible count equalled the candidate-pair count,
        the constraint would be inert and the set size would be governed by
        the lookback instead of by the price action."""
        bars = _legs(VIOLATED)
        pairs = candidate_pair_count(bars)
        admissible = len(admissible_lines(bars))
        assert pairs > 0
        assert admissible < pairs, (
            "the price-track constraint pruned nothing — the line set is a "
            "function of the cap, not of the price action"
        )


# ---------------------------------------------------------------------------
# FR-EM-L3 — closes, not extremes
# ---------------------------------------------------------------------------

class TestClosesOnly:

    def test_perturbing_highs_and_lows_changes_nothing(self):
        bars = _legs(CLEAN_UP)
        mangled = [OHLCVBar(date=b.date, open=b.open, high=b.close * 10.0,
                            low=b.close / 10.0, close=b.close, volume=b.volume)
                   for b in bars]
        assert admissible_lines(mangled) == admissible_lines(bars)


# ---------------------------------------------------------------------------
# H-L2 causality, H-L1 determinism
# ---------------------------------------------------------------------------

class TestCausalityAndDeterminism:

    def test_no_anchor_is_confirmed_after_the_bar_being_asked_about(self):
        """The heart of `H-L2`. A pivot is not knowable until its reversal
        confirms it, so a line anchored on a pivot confirmed later than
        `at_index` would be look-ahead — the error EM-6 D1's first test
        contained by reading `Pivot.index` instead of `confirmed_index`."""
        bars = _legs(VIOLATED)
        for at in range(DEFAULT_MIN_SPAN, len(bars)):
            for ln in admissible_lines(bars, at_index=at):
                assert ln.anchors_confirmed_at <= at

    def test_appending_future_bars_changes_no_past_line(self):
        bars = _legs(CLEAN_UP)
        at = len(bars) - 1
        before = admissible_lines(bars, at_index=at)
        after = admissible_lines(bars + _legs([120, 90, 95], bars_per_leg=9),
                                 at_index=at)
        assert after == before

    @pytest.mark.parametrize("at", [30, 40, 47])
    def test_a_truncated_frame_matches_the_full_one_at_the_same_bar(self, at):
        bars = _legs(VIOLATED)
        if at >= len(bars):
            pytest.skip("fixture shorter than the probe")
        assert admissible_lines(bars[: at + 1], at_index=at) == \
            admissible_lines(bars, at_index=at)

    def test_repeated_runs_are_identical(self):
        bars = _legs(VIOLATED)
        assert admissible_lines(bars) == admissible_lines(bars)

    def test_admissibility_is_stable_and_a_later_break_does_not_revoke_it(self):
        """`EC-L5`, corrected — and the correction is the point.

        My first version asserted that a collapse after the second anchor
        makes the line inadmissible. It does not, and the code is right: the
        price-track constraint is about closes **between the anchors**, and
        that segment is fixed in the past. A close that crosses the line
        *afterwards* is a **penetration** — `L2`'s subject — not a reason the
        line never existed. E&M rely on exactly that distinction: the
        throwback goes back to the *projected* trendline, so a broken line
        remains a real object.

        So the SRS's `EC-L5` was ambiguous. The set does not evolve by
        retroactive invalidation; it evolves by **new pivots adding** lines
        and by the **lookback dropping** them. Both are asserted here.
        """
        rising = _legs(CLEAN_UP)
        bars = rising + _legs([120, 70], bars_per_leg=12)
        at_early, at_late = len(rising) - 1, len(bars) - 1

        early = {(ln.a_index, ln.b_index)
                 for ln in admissible_lines(bars, at_index=at_early)
                 if ln.kind == "UP"}
        late = {(ln.a_index, ln.b_index)
                for ln in admissible_lines(bars, at_index=at_late)
                if ln.kind == "UP"}
        assert early, "no support lines before the collapse; fixture is wrong"
        assert early <= late, (
            "a line was retroactively revoked — admissibility must depend "
            "only on the closes between its anchors"
        )

    def test_the_lookback_is_what_drops_an_old_line(self):
        """The other half of `EC-L5`: the set is bounded by the window, and a
        line whose anchors have slid out of it is gone."""
        rising = _legs(CLEAN_UP)
        bars = rising + _legs([120, 70], bars_per_leg=12)
        at = len(bars) - 1
        wide = admissible_lines(bars, at_index=at, lookback=500)
        narrow = admissible_lines(bars, at_index=at, lookback=20)
        assert len(narrow) < len(wide), (
            "narrowing the lookback dropped nothing, so old lines are not "
            "ageing out of the window"
        )


# ---------------------------------------------------------------------------
# edge cases and parameters
# ---------------------------------------------------------------------------

class TestEdgeCasesAndParameters:

    def test_anchors_closer_than_the_minimum_span_are_rejected(self):
        """`EC-L2` / `EC-L3`: a line through adjacent pivots is noise with a
        slope, and bounding the bar separation is also what rules out a
        near-vertical line."""
        bars = _legs(VIOLATED)
        for ln in admissible_lines(bars):
            assert ln.b_index - ln.a_index >= DEFAULT_MIN_SPAN

    def test_non_positive_prices_never_anchor_a_line(self):
        """`EC-L6`: 13 such bars exist in the vendor data (#93)."""
        bars = _legs(CLEAN_UP)
        bars[20] = OHLCVBar(date=bars[20].date, open=0.0, high=0.0, low=0.0,
                            close=0.0, volume=1)
        for ln in admissible_lines(bars):
            assert ln.a_price > 0 and ln.b_price > 0

    def test_the_lookback_is_read_at_call_time_not_frozen_at_import(self, monkeypatch):
        """`H-L8` — tenth instance of this trap in the project."""
        bars = _legs(VIOLATED)
        assert admissible_lines(bars) != []
        monkeypatch.setattr(tl, "DEFAULT_LOOKBACK", 12)
        assert admissible_lines(bars) == [], (
            "DEFAULT_LOOKBACK is not being read at call time"
        )

    def test_the_min_span_is_read_at_call_time(self, monkeypatch):
        bars = _legs(VIOLATED)
        monkeypatch.setattr(tl, "DEFAULT_MIN_SPAN", 10 ** 6)
        assert admissible_lines(bars) == []

    def test_the_shipped_defaults_are_the_planned_ones(self):
        assert DEFAULT_MIN_SPAN == 10
        assert DEFAULT_LOOKBACK == 250
        assert DEFAULT_PIVOT_PCT == 0.02

    def test_the_pivot_scale_is_finer_than_the_dow_one(self):
        """A fifth parameter the plan did not name, and it matters.

        `dow.py`'s 5% zigzag is calibrated for E&M's **secondary** reactions,
        because it reads the PRIMARY trend. Trendlines are drawn across
        **minor**-reaction bottoms, which are the smaller degree — tide, wave,
        **ripple**. Using dow's scale would draw lines across the wrong degree
        of reversal.
        """
        from app.services.market_context.dow import DEFAULT_SWING_PCT
        assert DEFAULT_PIVOT_PCT < DEFAULT_SWING_PCT
