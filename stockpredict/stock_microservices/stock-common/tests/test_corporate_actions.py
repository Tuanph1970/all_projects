"""Backlog #119 — the seam detector, and the diagnosis it encodes.

The detector itself is small. What these tests mostly pin is the REASONING,
because the obvious diagnosis of a -33.8% overnight move is wrong and leads to
the wrong fix:

  vnstock/VCI returns a CONTINUOUS TCB series across 2026-10-27 (22.80, 22.53,
  22.37). The provider restates the whole prior history on a share-count event.
  The gap exists only in OUR database, because `_top_up_prices` appends bars
  after the last stored date and never restates what is already there.

So this module detects and never adjusts. A local back-adjustment would be a
second, divergent definition of "adjusted" sitting in the same database as the
provider's.
"""
from __future__ import annotations

import pytest

from stock_common.analytics.corporate_actions import (
    MAX_BELIEVABLE_DAILY_MOVE_PCT,
    PriceSeam,
    find_price_seams,
)


def test_the_real_tcb_seam_is_found():
    closes = [34.20, 33.80, 22.37, 22.33]
    dates = ["2026-10-23", "2026-10-26", "2026-10-27", "2026-10-28"]
    seams = find_price_seams(closes, dates)
    assert len(seams) == 1
    s = seams[0]
    assert s.date == "2026-10-27"
    assert s.move_pct == pytest.approx(-33.81, abs=0.02)
    # ~1.51 reads as roughly a 3-for-2 issue, which is the informative number.
    assert s.ratio == pytest.approx(1.511, abs=0.01)
    assert s.index == 2


def test_the_series_the_provider_actually_returns_has_no_seam():
    """The decisive measurement, kept as a regression.

    These are vnstock's own closes for TCB across the same dates, fetched
    2026-11-03. They are continuous. If a future change made the detector fire
    on THIS, the repair would re-pull every symbol for ever.
    """
    closes = [22.80, 22.53, 22.37, 22.33, 22.35, 21.60, 21.40]
    assert find_price_seams(closes) == []


def test_a_upcom_limit_day_is_not_a_seam():
    """UPCoM allows +/-15%. Firing on that would flag real trading as a data
    fault and get the detector ignored, which costs more than the misses."""
    assert find_price_seams([10.0, 11.5]) == []          # exactly +15.00%


def test_just_past_the_ceiling_is_a_seam():
    """Guards the guard above: the boundary must be a boundary, not a floor."""
    seams = find_price_seams([10.0, 11.6])
    assert len(seams) == 1 and seams[0].move_pct == pytest.approx(16.0, abs=0.01)


def test_the_default_is_the_loosest_vn_board_limit():
    assert MAX_BELIEVABLE_DAILY_MOVE_PCT == 15.0


def test_the_ceiling_is_read_rather_than_baked_in():
    assert find_price_seams([10.0, 11.2]) == []                      # +12%, under 15
    assert len(find_price_seams([10.0, 11.2], max_move_pct=10.0)) == 1


def test_every_known_seam_in_this_database_is_caught():
    """The four real ones, measured 2026-11-03 across ~43,000 rows."""
    cases = [
        ("TCB", 33.80, 22.37, -33.8),
        ("HDB", 10.90, 8.00, -26.6),
        ("TPB", 13.03, 10.72, -17.7),
        ("VPB", 21.71, 17.91, -17.5),
    ]
    for sym, prev, cur, expected in cases:
        seams = find_price_seams([prev, cur])
        assert len(seams) == 1, f"{sym} not detected"
        assert seams[0].move_pct == pytest.approx(expected, abs=0.1), sym


def test_an_ordinary_series_produces_nothing():
    """Non-vacuity. Only four seams exist in five years, so a detector that
    fired on normal bars would be useless."""
    import random
    rnd = random.Random(119)
    price, closes = 50.0, []
    for _ in range(600):
        price = max(1.0, price * (1 + rnd.gauss(0, 0.02)))   # 2% daily vol
        closes.append(price)
    assert find_price_seams(closes) == []


def test_several_seams_are_all_reported_oldest_first():
    seams = find_price_seams([20.0, 10.0, 10.5, 5.0], ["a", "b", "c", "d"])
    assert [s.index for s in seams] == [1, 3]
    assert [s.date for s in seams] == ["b", "d"]


@pytest.mark.parametrize("closes", [[], [10.0], [None, None]])
def test_degenerate_input_is_empty_not_an_exception(closes):
    assert find_price_seams(closes) == []


def test_a_zero_or_negative_prior_close_is_skipped_not_divided_by():
    assert find_price_seams([0.0, 10.0]) == []
    assert find_price_seams([-5.0, 10.0]) == []


def test_non_numeric_and_nan_cells_are_skipped():
    assert find_price_seams(["x", 10.0, None, 50.0, float("nan"), 1.0]) == []


def test_dates_are_optional_and_never_required():
    seams = find_price_seams([34.0, 22.0])
    assert len(seams) == 1 and seams[0].date is None


def test_a_short_date_list_does_not_index_out_of_range():
    seams = find_price_seams([34.0, 22.0, 22.1], ["only-one"])
    assert len(seams) == 1 and seams[0].date is None


def test_the_dict_form_keeps_the_key_the_narrator_already_reads():
    """#118 shipped reading `bar_index`; renaming it here would break the
    narrator silently, since params are passed straight through to i18n."""
    d = find_price_seams([34.0, 22.0], ["2026-10-27"])[0].as_dict()
    assert d["bar_index"] == d["index"] == 1
    assert set(d) >= {"date", "prev_close", "close", "move_pct", "ratio", "bar_index"}


def test_the_module_exposes_no_adjust_function():
    """The design decision, asserted so it is not quietly undone.

    The provider already back-adjusts. A local `adjust()` would put a second,
    divergent definition of "adjusted" in the same database and would be
    overwritten the next time the symbol were re-pulled.
    """
    import stock_common.analytics.corporate_actions as mod
    assert not [n for n in dir(mod) if "adjust" in n.lower() and not n.startswith("_")]


def test_a_seam_is_immutable():
    s = find_price_seams([34.0, 22.0])[0]
    assert isinstance(s, PriceSeam)
    with pytest.raises(Exception):
        s.move_pct = 0.0
