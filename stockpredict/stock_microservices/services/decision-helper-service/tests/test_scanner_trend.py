"""FR-SCAN-TREND — the four-clause trend template."""
from __future__ import annotations

from datetime import date, timedelta
from typing import List, Sequence

import pytest

from app.services.scanner.trend import (
    DEFAULT_ADVANCE_LOOKBACK,
    SMA_SLOW,
    assess_trend,
    required_bars,
    sma_at,
)
from app.services.signal.base import OHLCVBar


def bars_from(closes: Sequence[float]) -> List[OHLCVBar]:
    start = date(2023, 1, 2)
    return [
        OHLCVBar(date=start + timedelta(days=i), open=c, high=c, low=c, close=c, volume=1_000)
        for i, c in enumerate(closes)
    ]


def rising(n: int = 300, start: float = 50.0, step: float = 0.5) -> List[OHLCVBar]:
    return bars_from([start + step * i for i in range(n)])


def falling(n: int = 300, start: float = 200.0, step: float = 0.5) -> List[OHLCVBar]:
    return bars_from([start - step * i for i in range(n)])


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def test_sma_is_none_during_warmup_and_a_plain_mean_after():
    b = bars_from([1, 2, 3, 4])
    assert sma_at(b, 5) is None
    assert sma_at(b, 4) == pytest.approx(2.5)
    assert sma_at(b, 2) == pytest.approx(3.5)


def test_required_bars_is_bound_by_sma200_not_by_the_configured_floor():
    """The SRS default MIN_BARS = 150 is BELOW what SMA200 needs. A universe
    admitted at 150 would fail close_above_sma200 for want of history rather
    than for want of trend, and the exclusion would be invisible."""
    assert required_bars() >= SMA_SLOW
    assert required_bars(advance_lookback=400) == 401


# ---------------------------------------------------------------------------
# the template
# ---------------------------------------------------------------------------

def test_a_steady_uptrend_passes_every_clause():
    t = assess_trend("UP", rising())
    assert t.passed, t.failed_clauses()
    assert t.failed_clauses() == ()
    assert t.close > t.sma_fast > t.sma_slow


def test_a_downtrend_fails_and_names_which_clauses():
    t = assess_trend("DOWN", falling())
    assert not t.passed
    assert set(t.failed_clauses()) == {
        "close_above_sma50", "close_above_sma200", "sma50_above_sma200", "prior_advance",
    }


def test_short_history_fails_on_history_not_on_trend():
    """A near-miss and a no-data case must not look the same to a reader."""
    t = assess_trend("NEW", rising(n=100))
    assert not t.passed
    assert t.failed_clauses() == ("sufficient_history",)
    assert t.close is None and t.sma_slow is None


def test_every_clause_is_reported_pass_or_fail():
    t = assess_trend("UP", rising())
    assert len(t.clauses) == 4
    assert all(c.passed for c in t.clauses)
    assert all(c.detail for c in t.clauses), "a clause with no detail cannot be acted on"


def test_prior_advance_is_measured_off_the_window_low_and_can_be_the_only_failure():
    """Flat-then-up by 10%: above both averages with the fast above the slow,
    but the advance is under the 30% floor. Exactly one clause may fail."""
    flat = [100.0] * 260
    up = [100.0 + i * (10.0 / 40) for i in range(1, 41)]   # +10% over 40 bars
    t = assess_trend("WEAK", bars_from(flat + up))
    assert t.prior_advance_pct == pytest.approx(10.0, abs=0.2)
    assert t.failed_clauses() == ("prior_advance",)


def test_lowering_the_advance_floor_admits_the_same_series():
    flat = [100.0] * 260
    up = [100.0 + i * (10.0 / 40) for i in range(1, 41)]
    b = bars_from(flat + up)
    assert not assess_trend("WEAK", b).passed
    assert assess_trend("WEAK", b, min_prior_advance_pct=5.0).passed


def test_the_advance_window_is_the_configured_lookback():
    """A 40-bar rally inside a 260-bar flat base reads as +10% over 126 bars but
    as +0% over 20, because the 20-bar window never sees the base."""
    b = bars_from([100.0] * 260 + [100.0 + i * (10.0 / 40) for i in range(1, 41)])
    wide = assess_trend("X", b, advance_lookback=DEFAULT_ADVANCE_LOOKBACK)
    narrow = assess_trend("X", b, advance_lookback=20)
    assert wide.prior_advance_pct > narrow.prior_advance_pct


def test_assessment_reads_only_the_bars_handed_in():
    """Causality in miniature (EC-S1): truncating the series changes the answer
    only through the bars removed, never through bars that were never there."""
    b = rising(n=400)
    a = assess_trend("X", b[:300])
    c = assess_trend("X", list(b[:300]))
    assert a == c
