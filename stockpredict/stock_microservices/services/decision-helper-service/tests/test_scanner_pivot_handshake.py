"""Backlog #140 — the scanner's base pivot reaching the decision engine.

THE RULE THIS FILE EXISTS TO PIN: the scanner may make the engine's breakout
trigger STRICTER, never easier. A pivot above the N-bar high replaces it; a
pivot below it is ignored. Honouring a lower pivot would fire a breakout the
engine's own rule would not — the scanner overriding the engine's standard,
which EC-S6 forbids. It proposes; it does not decide.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import List, Sequence

import pytest

from app.services.signal.base import OHLCVBar
from app.services.signal.trend.n_day_breakout import detect_n_day_breakout

START = date(2024, 1, 2)


def bars_from(closes: Sequence[float]) -> List[OHLCVBar]:
    return [
        OHLCVBar(date=START + timedelta(days=i), open=c, high=c, low=c, close=c,
                 volume=1_000_000)
        for i, c in enumerate(closes)
    ]


#: 20 bars oscillating 90..100, then today. The engine's own LONG level is
#: therefore 100 and its SHORT level 90 — the window needs real width, because
#: a perfectly flat lookback has highest == lowest and every close below it
#: reads as a breakdown rather than as "inside the range".
def series(today_close: float) -> List[OHLCVBar]:
    return bars_from([90.0 if i % 2 else 100.0 for i in range(20)] + [today_close])


def last(bars: List[OHLCVBar]) -> date:
    return bars[-1].date


# ---------------------------------------------------------------------------
# Baseline — unchanged behaviour when no pivot is supplied
# ---------------------------------------------------------------------------

def test_without_a_pivot_the_engine_uses_its_own_n_day_high():
    sig = detect_n_day_breakout(series(101.0), last(series(101.0)), n=20)
    assert sig is not None and sig.direction == "LONG"
    assert sig.evidence["breakout_level"] == pytest.approx(100.0)
    assert sig.evidence["level_source"] == "n_day_high"
    assert sig.evidence["reference_level"] is None


def test_without_a_pivot_a_close_inside_the_range_is_still_no_signal():
    bars = series(95.0)
    assert detect_n_day_breakout(bars, last(bars), n=20) is None


# ---------------------------------------------------------------------------
# A pivot ABOVE the N-day high tightens the trigger
# ---------------------------------------------------------------------------

def test_a_higher_pivot_becomes_the_breakout_level():
    bars = series(106.0)
    sig = detect_n_day_breakout(bars, last(bars), n=20, reference_level=105.0,
                                reference_source="scanner_base_pivot")
    assert sig is not None
    assert sig.evidence["breakout_level"] == pytest.approx(105.0)
    assert sig.evidence["level_source"] == "scanner_base_pivot"
    assert sig.evidence["n_day_level"] == pytest.approx(100.0)


def test_a_higher_pivot_suppresses_a_signal_the_engine_alone_would_have_fired():
    """THE WHOLE POINT. 101 clears the 20-day high but not the base pivot at
    105 — the stock is above its recent range and still inside its base, which
    is exactly the case Qullamaggie's entry trigger exists to skip."""
    bars = series(101.0)
    assert detect_n_day_breakout(bars, last(bars), n=20) is not None
    assert detect_n_day_breakout(bars, last(bars), n=20, reference_level=105.0) is None


def test_penetration_is_measured_against_the_pivot_not_the_n_day_high():
    bars = series(106.0)
    sig = detect_n_day_breakout(bars, last(bars), n=20, reference_level=105.0)
    # 106 over 105 is ~0.95%, not the 6% it would be over 100.
    assert sig.evidence["penetration_pct"] == pytest.approx(0.952, abs=0.01)


# ---------------------------------------------------------------------------
# A pivot BELOW the N-day high is ignored — the scanner cannot loosen the engine
# ---------------------------------------------------------------------------

def test_a_lower_pivot_is_ignored_and_the_engine_keeps_its_own_level():
    bars = series(101.0)
    sig = detect_n_day_breakout(bars, last(bars), n=20, reference_level=95.0,
                                reference_source="scanner_base_pivot")
    assert sig is not None
    assert sig.evidence["breakout_level"] == pytest.approx(100.0)
    assert sig.evidence["level_source"] == "n_day_high", \
        "a pivot below the engine's level must not become the trigger"


def test_a_lower_pivot_cannot_manufacture_a_signal():
    """If a 95 pivot were honoured, a close of 96 would 'break out' while
    sitting four points UNDER the 20-day high. The scanner would have loosened
    the engine's standard, which EC-S6 forbids."""
    bars = series(96.0)
    assert detect_n_day_breakout(bars, last(bars), n=20) is None, \
        "fixture check: 96 is inside the 90-100 range on the engine's own rule"
    assert detect_n_day_breakout(bars, last(bars), n=20, reference_level=95.0) is None


def test_the_ignored_pivot_is_still_reported():
    """Silently discarding it would leave a user unable to see why the Scanner
    tab's level and the engine's differ."""
    bars = series(101.0)
    sig = detect_n_day_breakout(bars, last(bars), n=20, reference_level=95.0)
    assert sig.evidence["reference_level"] == pytest.approx(95.0)


def test_a_pivot_equal_to_the_n_day_high_is_adopted_and_changes_nothing():
    bars = series(101.0)
    sig = detect_n_day_breakout(bars, last(bars), n=20, reference_level=100.0,
                                reference_source="scanner_base_pivot")
    assert sig.evidence["breakout_level"] == pytest.approx(100.0)
    assert sig.evidence["level_source"] == "scanner_base_pivot"


# ---------------------------------------------------------------------------
# The SHORT side is untouched — the scanner is a long-side funnel
# ---------------------------------------------------------------------------

def test_a_pivot_does_not_affect_a_breakdown():
    bars = series(85.0)
    plain = detect_n_day_breakout(bars, last(bars), n=20)
    withp = detect_n_day_breakout(bars, last(bars), n=20, reference_level=105.0)
    assert plain.direction == withp.direction == "SHORT"
    assert plain.evidence["breakout_level"] == withp.evidence["breakout_level"] == pytest.approx(90.0)
    assert withp.evidence["level_source"] == "n_day_low"


# ---------------------------------------------------------------------------
# load_scanner_pivot — only a candidate has a pivot worth using
# ---------------------------------------------------------------------------

class _Scalars:
    def __init__(self, rows): self._rows = rows
    def all(self): return self._rows


class _FakeResult:
    def __init__(self, rows): self._rows = rows
    def scalars(self): return _Scalars(self._rows)


class _FakeDB:
    """Returns the rows it was given, and records the statement for inspection."""
    def __init__(self, rows=()): self.rows = list(rows); self.stmt = None
    async def execute(self, stmt):
        self.stmt = stmt
        return _FakeResult(self.rows)


class _Row:
    def __init__(self, detail, scan_date=date(2024, 3, 29), symbol="GVR"):
        self.detail = detail; self.scan_date = scan_date; self.symbol = symbol


def _pivot_row(level, scan_date=date(2024, 3, 29)):
    return _Row({"base": {"pivot": {"level": level, "distance_pct": 8.0}}}, scan_date)


async def test_a_candidate_row_yields_its_pivot():
    from app.services.scanner.runner import load_scanner_pivot
    got = await load_scanner_pivot(_FakeDB([_pivot_row(35.0)]), "gvr", date(2024, 3, 29))
    assert got is not None and got.level == 35.0 and got.scan_date == date(2024, 3, 29)


async def test_the_most_recent_drawn_pivot_wins():
    """THE FIX THAT MADE THIS HANDSHAKE REAL. A candidate stops being one on the
    very day it breaks out — measured 0 of 8 — so matching scan_date == bar_date
    guaranteed the pivot was gone exactly when the engine needed it. The query
    orders by scan_date desc; the loader must take the first usable row."""
    from app.services.scanner.runner import load_scanner_pivot
    rows = [_pivot_row(35.0, date(2024, 3, 29)), _pivot_row(30.0, date(2024, 3, 20))]
    got = await load_scanner_pivot(_FakeDB(rows), "GVR", date(2024, 4, 3))
    assert got.level == 35.0 and got.scan_date == date(2024, 3, 29)


async def test_a_stale_row_is_skipped_in_favour_of_a_usable_one():
    """A row whose base payload is unusable must not mask an older good one."""
    from app.services.scanner.runner import load_scanner_pivot
    rows = [_Row({"momentum": {}}, date(2024, 3, 29)), _pivot_row(31.0, date(2024, 3, 22))]
    got = await load_scanner_pivot(_FakeDB(rows), "GVR", date(2024, 4, 1))
    assert got.level == 31.0


async def test_the_lookback_window_is_applied():
    from app.services.scanner.runner import load_scanner_pivot, PIVOT_LOOKBACK_DAYS
    db = _FakeDB([])
    await load_scanner_pivot(db, "GVR", date(2024, 4, 30), lookback_days=10)
    sql = str(db.stmt)
    assert "scan_date" in sql and "ORDER BY" in sql.upper()
    assert PIVOT_LOOKBACK_DAYS > 0


async def test_no_scan_row_means_no_pivot_not_an_error():
    from app.services.scanner.runner import load_scanner_pivot
    assert await load_scanner_pivot(_FakeDB([]), "GVR", date(2024, 3, 31)) is None


async def test_a_row_without_base_geometry_yields_no_pivot():
    """S-1-shaped rows (require_base=False) carry no base at all."""
    from app.services.scanner.runner import load_scanner_pivot
    assert await load_scanner_pivot(_FakeDB([_Row({"momentum": {}})]), "X", date(2024, 1, 1)) is None


async def test_an_unparseable_level_yields_no_pivot_rather_than_crashing():
    from app.services.scanner.runner import load_scanner_pivot
    assert await load_scanner_pivot(_FakeDB([_pivot_row("not a number")]), "X", date(2024, 1, 1)) is None


async def test_a_non_positive_level_is_refused():
    from app.services.scanner.runner import load_scanner_pivot
    assert await load_scanner_pivot(_FakeDB([_pivot_row(0.0)]), "X", date(2024, 1, 1)) is None
