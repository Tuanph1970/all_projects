"""EM-5 L2 — contacts, penetration, the shakeout, and amendment.

`FR-EM-L4` (counting only), `L5`, `L6`, `L7`.

E&M Ch 14's three tests of a valid penetration:

1. **Extent** — a close beyond the line by about **3%** of price (2% in the
   averages). *"It need not happen in one day."*
2. **Volume** — not required for a downside break.
3. **The pullback test** — a borderline break followed by a feeble,
   volume-less rally that rounds over under the line. And its counterpart:
   **beware the shakeout** — a high-volume crack that **closes back above** the
   line is usually a false move.

And the amendment rules, which are where the confirmed/provisional
distinction comes from:

> If the original line rested on only **two** points and the third contact
> penetrates it indecisively, **redraw** across the first and third (or second
> and third) bottoms. If the line has already been **confirmed** by a third or
> fourth bottom, **disregard** the indecisive break.

L1's measurement is why contacts are here rather than behind Gate A: there are
**89 admissible lines per bar** (median), and most rest on exactly two
anchors. Without the confirmed/provisional split a "break" would mean
"something happened to one of 89 lines", which is close to meaning nothing.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import List, Sequence

import pytest

from app.services.backtest.market_features import atr_series
from app.services.market_context import trendline_breaks as tb
from app.services.market_context.trendline import Trendline, admissible_lines
from app.services.market_context.trendline_breaks import (
    CONTACT_TOL_ATR,
    MIN_CONTACTS_CONFIRMED,
    PENETRATION_PCT,
    amend_line,
    count_contacts,
    detect_penetration,
    is_confirmed,
)
from app.services.signal.base import OHLCVBar


def _bars_from(closes: Sequence[float], pad: float = 0.4,
               highs=None, lows=None) -> List[OHLCVBar]:
    day, out = date(2020, 1, 1), []
    for i, c in enumerate(closes):
        h = (highs[i] if highs else c + pad)
        l = (lows[i] if lows else c - pad)
        out.append(OHLCVBar(date=day, open=c, high=h, low=l, close=c,
                            volume=1_000_000))
        day += timedelta(days=1)
    return out


#: An UP line from (0, 100.0) to (20, 110.0): slope +0.5/bar.
LINE = Trendline(kind="UP", a_index=0, b_index=20, a_price=100.0,
                 b_price=110.0, slope=0.5, anchors_confirmed_at=20)


def _on_line_series(n: int = 60, touch_at: Sequence[int] = (),
                    lift: float = 6.0, near: float = 0.0) -> List[OHLCVBar]:
    """Closes sit `lift` above the line, except at `touch_at` where they come
    within `near` of it. Lets contact counting be tested without the
    enumerator.

    `near` exists because a close sitting EXACTLY on the line satisfies any
    tolerance — `|c - v| = 0 <= band` for every band — so an exact-touch
    fixture cannot exercise the tolerance at all. The first version of this
    helper had no `near`, and the bound-default guard duly passed against a
    tolerance of 1e-9. Same shape as L1's quiet fixture, which was not quiet
    relative to its level.
    """
    anchors = {LINE.a_index, LINE.b_index}
    closes = []
    for i in range(n):
        v = LINE.value_at(i)
        if i in anchors:
            closes.append(v)            # anchors ARE on the line, by construction
        elif i in set(touch_at):
            closes.append(v + near)
        else:
            closes.append(v + lift)
    return _bars_from(closes)


# ---------------------------------------------------------------------------
# H-L3 — contacts
# ---------------------------------------------------------------------------

class TestContacts:

    def test_three_closes_on_the_line_give_three_contacts(self):
        bars = _on_line_series(touch_at=(0, 20, 40))
        assert count_contacts(bars, LINE, at_index=59) == 3

    def test_a_fourth_touch_raises_it_to_four(self):
        bars = _on_line_series(touch_at=(0, 20, 40, 52))
        assert count_contacts(bars, LINE, at_index=59) == 4

    def test_contacts_are_counted_up_to_the_evaluation_bar_only(self):
        """Causal. A touch at bar 40 is not a contact at bar 30."""
        bars = _on_line_series(touch_at=(0, 20, 40))
        assert count_contacts(bars, LINE, at_index=30) == 2
        assert count_contacts(bars, LINE, at_index=45) == 3

    def test_contacts_are_counted_beyond_the_second_anchor(self):
        """E&M's amendment rule speaks of a line "confirmed by a third or
        fourth bottom" — and those arrive AFTER the original two. So contacts
        cannot be restricted to the anchor segment."""
        bars = _on_line_series(touch_at=(0, 20, 44))
        assert count_contacts(bars, LINE, at_index=59) == 3

    def test_a_close_outside_the_tolerance_is_not_a_contact(self):
        bars = _on_line_series(touch_at=(0, 20))
        atr = atr_series(bars)
        i = 40
        far = LINE.value_at(i) + 3.0 * (atr[i] or 1.0) * CONTACT_TOL_ATR
        closes = [b.close for b in bars]
        closes[i] = far
        assert count_contacts(_bars_from(closes), LINE, at_index=59) == 2

    def test_the_tolerance_is_read_at_call_time(self, monkeypatch):
        """`H-L8` — tenth instance of this trap.

        The touches sit 0.2 ATR-ish off the line, inside the 0.25 default and
        outside a tightened one, so the parameter can actually bite. The two
        anchors remain exactly on the line by construction and still count,
        which is why the tightened expectation is 2 rather than 0.
        """
        bars = _on_line_series(touch_at=(0, 20, 40), near=0.15)
        assert count_contacts(bars, LINE, at_index=59) == 3
        monkeypatch.setattr(tb, "CONTACT_TOL_ATR", 1e-9)
        assert count_contacts(bars, LINE, at_index=59) == 2, (
            "CONTACT_TOL_ATR is not being read at call time"
        )


class TestConfirmedVersusProvisional:

    def test_two_anchors_alone_are_provisional(self):
        bars = _on_line_series(touch_at=(0, 20))
        assert not is_confirmed(bars, LINE, at_index=59)

    def test_a_third_contact_confirms_the_line(self):
        bars = _on_line_series(touch_at=(0, 20, 40))
        assert is_confirmed(bars, LINE, at_index=59)

    def test_the_threshold_is_the_books_third_bottom(self):
        assert MIN_CONTACTS_CONFIRMED == 3


# ---------------------------------------------------------------------------
# FR-EM-L5 — penetration
# ---------------------------------------------------------------------------

class TestPenetration:

    def test_a_close_three_percent_below_an_up_line_is_a_break(self):
        bars = _on_line_series(touch_at=(0, 20))
        closes = [b.close for b in bars]
        i = 40
        closes[i] = LINE.value_at(i) * (1.0 - PENETRATION_PCT - 0.005)
        pen = detect_penetration(_bars_from(closes), LINE, at_index=59)
        assert pen is not None
        assert pen.bar_index == i and pen.direction == "down"

    def test_a_close_barely_beyond_is_not_decisive(self):
        """E&M's extent test is the whole point of the 3%: price dipping
        under the line is not a break."""
        bars = _on_line_series(touch_at=(0, 20))
        closes = [b.close for b in bars]
        closes[40] = LINE.value_at(40) * (1.0 - 0.005)
        assert detect_penetration(_bars_from(closes), LINE, at_index=59) is None

    def test_the_first_decisive_close_is_the_break(self):
        bars = _on_line_series(touch_at=(0, 20))
        closes = [b.close for b in bars]
        for i in (40, 45):
            closes[i] = LINE.value_at(i) * (1.0 - PENETRATION_PCT - 0.01)
        pen = detect_penetration(_bars_from(closes), LINE, at_index=59)
        assert pen.bar_index == 40

    def test_a_penetration_cannot_predate_the_second_anchor(self):
        """This falls out of `FR-EM-L2`: the price track never crosses the
        line between its anchors, so a break can only occur after `b_index`.
        Asserted on real enumerated lines rather than a constructed one."""
        bars = _legs_clean()
        at = len(bars) - 1
        for ln in admissible_lines(bars, at_index=at):
            pen = detect_penetration(bars, ln, at_index=at)
            if pen is not None:
                assert pen.bar_index > ln.b_index

    def test_a_down_line_breaks_upward(self):
        line = Trendline(kind="DOWN", a_index=0, b_index=20, a_price=110.0,
                         b_price=100.0, slope=-0.5, anchors_confirmed_at=20)
        closes = [line.value_at(i) - 6.0 for i in range(60)]
        closes[40] = line.value_at(40) * (1.0 + PENETRATION_PCT + 0.005)
        pen = detect_penetration(_bars_from(closes), line, at_index=59)
        assert pen is not None and pen.direction == "up"

    def test_the_threshold_is_read_at_call_time(self, monkeypatch):
        bars = _on_line_series(touch_at=(0, 20))
        closes = [b.close for b in bars]
        closes[40] = LINE.value_at(40) * (1.0 - 0.02)
        poked = _bars_from(closes)
        assert detect_penetration(poked, LINE, at_index=59) is None
        monkeypatch.setattr(tb, "PENETRATION_PCT", 0.01)
        assert detect_penetration(poked, LINE, at_index=59) is not None

    def test_the_default_is_the_books_figure(self):
        assert PENETRATION_PCT == 0.03


# ---------------------------------------------------------------------------
# FR-EM-L6 — the shakeout
# ---------------------------------------------------------------------------

class TestTheShakeout:

    def test_an_intraday_crack_that_closes_back_above_is_not_a_break(self):
        """E&M: *"a high-volume crack through the line that closes back above
        it is usually a false move for that moment."*

        Reading closes only (`FR-EM-L3`) makes this **structural** rather than
        a separate rule — but the fixture proves it, because "it follows from
        another requirement" is exactly the kind of claim that rots.
        """
        bars = _on_line_series(touch_at=(0, 20))
        closes = [b.close for b in bars]
        lows = [b.low for b in bars]
        i = 40
        lows[i] = LINE.value_at(i) * (1.0 - 0.10)      # a deep intraday crack
        assert detect_penetration(_bars_from(closes, lows=lows), LINE,
                                  at_index=59) is None

    def test_a_failed_break_is_still_recorded_as_a_break(self):
        """Causality, and it cuts against intuition.

        A penetration that price later recovers is a *failed* break — but
        whether it failed is only knowable afterwards, so it cannot be a
        condition on recording the break. Filtering those out would be
        look-ahead. The recovery is an OUTCOME, which is Gate A's subject.
        """
        bars = _on_line_series(touch_at=(0, 20))
        closes = [b.close for b in bars]
        closes[40] = LINE.value_at(40) * (1.0 - PENETRATION_PCT - 0.01)
        for i in range(41, 60):                        # full recovery above
            closes[i] = LINE.value_at(i) + 8.0
        pen = detect_penetration(_bars_from(closes), LINE, at_index=59)
        assert pen is not None and pen.bar_index == 40


# ---------------------------------------------------------------------------
# FR-EM-L7 — amendment
# ---------------------------------------------------------------------------

def _legs_clean(points=(100, 110, 104, 116, 109, 120), bars_per_leg=8):
    closes = [float(points[0])]
    for a, b in zip(points, points[1:]):
        for j in range(1, bars_per_leg + 1):
            closes.append(a + (b - a) * j / bars_per_leg)
    return _bars_from(closes)


class TestAmendment:

    def test_a_confirmed_line_is_never_amended(self):
        """E&M: *"if the line has already been confirmed by a third or fourth
        bottom, disregard the indecisive break."*"""
        bars = _on_line_series(touch_at=(0, 20, 40))
        closes = [b.close for b in bars]
        closes[45] = LINE.value_at(45) * (1.0 - 0.01)   # indecisive
        assert amend_line(_bars_from(closes), LINE, at_index=59) is None

    def test_a_provisional_line_indecisively_broken_is_redrawn(self):
        bars = _legs_clean()
        at = len(bars) - 1
        amended = [a for ln in admissible_lines(bars, at_index=at)
                   if (a := amend_line(bars, ln, at_index=at)) is not None]
        for a in amended:
            assert a.rule in ("first_and_third", "second_and_third")
            assert (a.line.a_index, a.line.b_index) != (a.original.a_index,
                                                        a.original.b_index)

    def test_the_rule_applied_is_recorded(self):
        """`H-L7`. An amended line must never be silently a different line."""
        bars = _legs_clean()
        at = len(bars) - 1
        for ln in admissible_lines(bars, at_index=at):
            a = amend_line(bars, ln, at_index=at)
            if a is not None:
                assert a.original == ln
                assert a.rule

    def test_amendment_is_deterministic(self):
        bars = _legs_clean()
        at = len(bars) - 1
        for ln in admissible_lines(bars, at_index=at):
            assert amend_line(bars, ln, at_index=at) == amend_line(bars, ln, at_index=at)


class TestThinData:

    def test_an_empty_frame_is_inert(self):
        assert count_contacts([], LINE, at_index=0) == 0
        assert detect_penetration([], LINE, at_index=0) is None
        assert amend_line([], LINE, at_index=0) is None

    def test_a_bar_index_past_the_frame_is_inert(self):
        bars = _on_line_series(touch_at=(0, 20))
        assert detect_penetration(bars, LINE, at_index=10_000) is None
