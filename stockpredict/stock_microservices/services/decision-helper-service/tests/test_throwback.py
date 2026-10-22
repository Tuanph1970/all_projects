"""EM-7 T3 — the throwback entry detector (`FR-EM-T2`..`T5`, `T8`).

E&M Ch 6: the pullback to a broken boundary is *"the short-seller's second
chance and his stop-placement reference."* Ch 13 says why it works — a broken
support **becomes** resistance — and Ch 33 gives the tactic as *"whichever
comes first"* of a pullback to the line or a 40% recovery.

`T2`/Gate 1 established the phenomenon is real on this data: price returns to
a broken level 82.3% of the time against a distance-matched null of 72.3%, and
overshoots it 0.23 ATR less. **A ten-point edge on a 72% base**, which is why
this detector ships `OFF` and `T4` decides whether it ever ships enabled.

The four modes are **mutually exclusive** by design, not by accident: combined,
`BAND` and `RETRACE_40` would make each other unobservable, which is the `#83`
bug class where capping severities made `#82`'s override unreachable.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import List, Optional, Sequence

import pytest

from app.services.backtest.harness import BacktestConfig, run_backtest_on_bars
from app.services.signal import trend as _trend_pkg  # noqa: F401
from app.services.signal.base import OHLCVBar
from app.services.signal.trend import throwback as tb
from app.services.signal.trend.throwback import (
    MODE_BAND,
    MODE_EITHER,
    MODE_OFF,
    MODE_RETRACE,
    THROWBACK_MODES,
    detect_throwback,
)


def _bars(closes: Sequence[float], pad: float = 0.3,
          start: date = date(2020, 1, 1)) -> List[OHLCVBar]:
    out, day = [], start
    for c in closes:
        out.append(OHLCVBar(date=day, open=c, high=c + pad, low=c - pad,
                            close=c, volume=1_000_000))
        day += timedelta(days=1)
    return out


def _resistance_broken_up_then_throwback() -> List[OHLCVBar]:
    """A resistance at ~105 forms, breaks upward, then price falls back to it.

    After the break the level acts as SUPPORT (Ch 13), so the throwback is a
    LONG — an entry in the direction of the break.
    """
    closes = [100.0] * 12 + [102.0, 104.0, 105.0, 104.0, 102.0] + [100.0] * 14   # pivot high ~105
    closes += [103.0, 106.0, 109.0, 111.0]                                        # breaks up
    closes += [110.0, 108.0, 106.0, 105.1]                                        # throws back
    closes += [105.0] * 6
    return _bars(closes)


def _support_broken_down_then_pullback() -> List[OHLCVBar]:
    closes = [110.0] * 12 + [108.0, 106.0, 105.0, 106.0, 108.0] + [110.0] * 14   # pivot low ~105
    closes += [107.0, 104.0, 101.0, 99.0]                                         # breaks down
    closes += [100.0, 102.0, 104.0, 104.9]                                        # pulls back
    closes += [105.0] * 6
    return _bars(closes)


def _break_with_no_return() -> List[OHLCVBar]:
    closes = [100.0] * 12 + [102.0, 104.0, 105.0, 104.0, 102.0] + [100.0] * 14
    closes += [103.0, 106.0, 109.0, 112.0, 115.0, 118.0, 121.0, 124.0]
    closes += [127.0 + i for i in range(10)]
    return _bars(closes)


def _fire(bars: List[OHLCVBar], idx: int, **kw) -> Optional[object]:
    return detect_throwback(bars, bars[idx].date, **kw)


# ---------------------------------------------------------------------------
# FR-EM-T8 — off by default
# ---------------------------------------------------------------------------

class TestOffByDefault:

    def test_the_default_mode_is_off(self):
        bars = _resistance_broken_up_then_throwback()
        assert all(_fire(bars, i) is None for i in range(len(bars)))

    def test_off_is_the_registered_default_and_the_modes_are_closed(self):
        assert MODE_OFF == "OFF"
        assert THROWBACK_MODES == frozenset({MODE_OFF, MODE_BAND, MODE_RETRACE, MODE_EITHER})

    def test_an_unknown_mode_is_refused_rather_than_ignored(self):
        bars = _resistance_broken_up_then_throwback()
        with pytest.raises(ValueError, match="mode"):
            _fire(bars, -1, mode="NONSENSE")


# ---------------------------------------------------------------------------
# H-T2 — the planted throwback
# ---------------------------------------------------------------------------

class TestPlantedThrowback:

    def test_a_broken_resistance_revisited_is_a_long(self):
        bars = _resistance_broken_up_then_throwback()
        hits = [i for i in range(len(bars)) if _fire(bars, i, mode=MODE_BAND)]
        assert hits, "the planted throwback did not fire at all"
        sig = _fire(bars, hits[0], mode=MODE_BAND)
        assert sig.direction == "LONG"
        assert sig.kind == "THROWBACK"

    def test_a_broken_support_revisited_is_a_short(self):
        bars = _support_broken_down_then_pullback()
        hits = [i for i in range(len(bars)) if _fire(bars, i, mode=MODE_BAND)]
        assert hits
        assert _fire(bars, hits[0], mode=MODE_BAND).direction == "SHORT"

    def test_the_entry_is_in_the_direction_of_the_break(self):
        """Ch 13: the broken level reverses role, so the throwback is a
        continuation of the break and never a bet against it."""
        up = _resistance_broken_up_then_throwback()
        dn = _support_broken_down_then_pullback()
        for bars, want in ((up, "LONG"), (dn, "SHORT")):
            for i in range(len(bars)):
                s = _fire(bars, i, mode=MODE_BAND)
                if s:
                    assert s.direction == want

    def test_the_evidence_carries_the_facts_a_reader_needs(self):
        bars = _resistance_broken_up_then_throwback()
        sig = next(_fire(bars, i, mode=MODE_BAND)
                   for i in range(len(bars)) if _fire(bars, i, mode=MODE_BAND))
        ev = sig.evidence
        for key in ("level_price", "break_bar", "break_direction",
                    "bars_since_break", "trigger"):
            assert key in ev, key
        assert ev["trigger"] in (MODE_BAND, MODE_RETRACE)


# ---------------------------------------------------------------------------
# H-T3 — the planted absence
# ---------------------------------------------------------------------------

class TestPlantedAbsence:

    def test_a_break_that_never_comes_back_fires_nothing(self):
        bars = _break_with_no_return()
        assert all(_fire(bars, i, mode=MODE_EITHER) is None
                   for i in range(len(bars)))

    def test_a_series_with_no_break_fires_nothing(self):
        bars = _bars([100.0 + 0.4 * (i % 7) for i in range(80)])
        assert all(_fire(bars, i, mode=MODE_EITHER) is None
                   for i in range(len(bars)))


# ---------------------------------------------------------------------------
# edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:

    def test_the_break_bar_itself_is_not_a_throwback(self):
        """`EC-T5` / `EC-T2`, and the guard is **structural, not enforced**.

        Mutation-checking exposed this: changing `age <= 0` to `age < 0` — so
        a break on the current bar WOULD be eligible — left all 25 tests
        passing. The reason is that age 0 is unreachable by construction, not
        that the test was watching:

        * a decisive break requires the close to be at least one band BEYOND
          the level, so `BAND` cannot also be true on that bar; and
        * at the break bar the post-break extreme IS that bar, so the amount
          given back is zero and `RETRACE_40` cannot be true either.

        So the `age <= 0` check is **defensive** — it costs nothing and would
        matter if a future trigger could fire at the break bar. Recording that
        honestly is the `#89` lesson: an unreachable branch is logged as
        unreachable rather than asserted as though it were exercised.
        """
        bars = _resistance_broken_up_then_throwback()
        for i in range(len(bars)):
            sig = _fire(bars, i, mode=MODE_EITHER)
            if sig:
                assert sig.evidence["break_bar"] < i

        # The two reasons age 0 cannot fire, asserted directly.
        atr = tb.atr_series(bars)
        for i in range(tb.MIN_BARS, len(bars)):
            for cand in tb._candidates(
                tb.compute_sr_levels(bars[: i + 1]), bars, i, 10 ** 6
            ):
                if cand["bars_since_break"] != 0:
                    continue
                a = atr[i]
                assert a is not None and a > 0
                assert abs(bars[i].close - cand["price"]) > a * tb.DEFAULT_BAND_ATR, (
                    "a break bar is inside its own band — EC-T5 is no longer "
                    "structural and the age guard has become load-bearing"
                )
                assert not tb._retraced(bars, i, cand, tb.DEFAULT_RETRACE_PCT)

    def test_a_stale_break_is_not_a_second_chance(self):
        """`FR-EM-T5`. A level broken 200 bars ago and revisited is a
        different event from one broken last week."""
        bars = _resistance_broken_up_then_throwback()
        hit = next(i for i in range(len(bars)) if _fire(bars, i, mode=MODE_BAND))
        assert _fire(bars, hit, mode=MODE_BAND, stale_bars=1) is None

    def test_only_one_signal_is_emitted_per_bar(self):
        """`EC-T4`: with two qualifying levels the nearer governs."""
        bars = _resistance_broken_up_then_throwback()
        for i in range(len(bars)):
            s = _fire(bars, i, mode=MODE_EITHER)
            assert s is None or isinstance(s.evidence["level_price"], float)

    def test_a_short_frame_is_inert(self):
        assert _fire(_bars([100.0] * 10), -1, mode=MODE_EITHER) is None
        assert detect_throwback([], date(2020, 1, 1), mode=MODE_EITHER) is None

    def test_a_bar_date_not_in_the_frame_is_inert(self):
        bars = _resistance_broken_up_then_throwback()
        assert detect_throwback(bars, date(1999, 1, 1), mode=MODE_EITHER) is None


# ---------------------------------------------------------------------------
# the modes do not stack
# ---------------------------------------------------------------------------

class TestTheModesAreExclusive:

    def test_band_mode_never_reports_a_retrace_trigger(self):
        bars = _resistance_broken_up_then_throwback()
        for i in range(len(bars)):
            s = _fire(bars, i, mode=MODE_BAND)
            if s:
                assert s.evidence["trigger"] == MODE_BAND

    def test_retrace_mode_never_reports_a_band_trigger(self):
        bars = _resistance_broken_up_then_throwback()
        for i in range(len(bars)):
            s = _fire(bars, i, mode=MODE_RETRACE)
            if s:
                assert s.evidence["trigger"] == MODE_RETRACE

    def test_either_fires_wherever_a_single_mode_fires(self):
        """E&M's "whichever comes first" is a union, so it cannot be stricter
        than either half."""
        bars = _resistance_broken_up_then_throwback()
        band = {i for i in range(len(bars)) if _fire(bars, i, mode=MODE_BAND)}
        retr = {i for i in range(len(bars)) if _fire(bars, i, mode=MODE_RETRACE)}
        either = {i for i in range(len(bars)) if _fire(bars, i, mode=MODE_EITHER)}
        assert band | retr <= either


# ---------------------------------------------------------------------------
# H-T1 causality, H-T7 bound defaults
# ---------------------------------------------------------------------------

class TestCausalityAndDefaults:

    def test_appending_future_bars_changes_no_past_signal(self):
        bars = _resistance_broken_up_then_throwback()
        before = [bool(_fire(bars, i, mode=MODE_BAND)) for i in range(len(bars))]
        longer = bars + _bars([104.0] * 20, start=bars[-1].date + timedelta(days=1))
        after = [bool(_fire(longer, i, mode=MODE_BAND)) for i in range(len(bars))]
        assert after == before

    def test_the_band_is_read_at_call_time_not_frozen_at_import(self, monkeypatch):
        bars = _resistance_broken_up_then_throwback()
        assert any(_fire(bars, i, mode=MODE_BAND) for i in range(len(bars)))
        monkeypatch.setattr(tb, "DEFAULT_BAND_ATR", 0.0001)
        assert not any(_fire(bars, i, mode=MODE_BAND) for i in range(len(bars))), (
            "DEFAULT_BAND_ATR is not being read at call time"
        )

    def test_the_staleness_bound_is_read_at_call_time(self, monkeypatch):
        bars = _resistance_broken_up_then_throwback()
        monkeypatch.setattr(tb, "DEFAULT_STALE_BARS", 1)
        assert not any(_fire(bars, i, mode=MODE_BAND) for i in range(len(bars)))

    def test_the_shipped_defaults_are_the_measured_ones(self):
        """Gate 1's primary setting, which is where the effect was measured."""
        assert tb.DEFAULT_BAND_ATR == 0.5
        assert tb.DEFAULT_STALE_BARS == 60
        assert tb.DEFAULT_RETRACE_PCT == 0.40


# ---------------------------------------------------------------------------
# the no-op proof — the harness carries the flag but does not use it yet
# ---------------------------------------------------------------------------

class TestHarnessNoOp:

    def _series(self, n: int = 700) -> List[OHLCVBar]:
        out, price, day = [], 100.0, date(2018, 1, 1)
        for i in range(n):
            price *= 1.0 + (0.012 if (i // 23) % 2 == 0 else -0.009)
            out.append(OHLCVBar(date=day, open=price, high=price * 1.02,
                                low=price * 0.98, close=price, volume=1_000_000))
            day += timedelta(days=1)
        return out

    def test_the_default_config_is_off(self):
        cfg = BacktestConfig(ticker="X", start_date=date(2020, 1, 1),
                             end_date=date(2021, 1, 1))
        assert cfg.throwback_mode == MODE_OFF

    def test_a_default_run_is_identical_to_one_with_the_mode_spelled_out(self):
        bars = self._series()
        a = run_backtest_on_bars(BacktestConfig(
            ticker="X", start_date=bars[300].date, end_date=bars[-1].date), bars)
        b = run_backtest_on_bars(BacktestConfig(
            ticker="X", start_date=bars[300].date, end_date=bars[-1].date,
            throwback_mode=MODE_OFF), bars)
        assert ([(t.entry_date, t.exit_date, t.net_pnl) for t in a.trade_ledger]
                == [(t.entry_date, t.exit_date, t.net_pnl) for t in b.trade_ledger])

    def test_enabling_it_changes_something(self):
        """The vacuity guard: a flag that changes nothing is a bug, not a
        conservative default (the EM-6 H-D3 lesson)."""
        bars = self._series()
        off = run_backtest_on_bars(BacktestConfig(
            ticker="X", start_date=bars[300].date, end_date=bars[-1].date), bars)
        on = run_backtest_on_bars(BacktestConfig(
            ticker="X", start_date=bars[300].date, end_date=bars[-1].date,
            throwback_mode=MODE_EITHER), bars)
        assert len(on.trade_ledger) != len(off.trade_ledger) or any(
            a.entry_date != b.entry_date
            for a, b in zip(on.trade_ledger, off.trade_ledger))

    def test_an_unknown_harness_mode_is_refused(self):
        bars = self._series()
        cfg = BacktestConfig(ticker="X", start_date=bars[300].date,
                             end_date=bars[-1].date, throwback_mode="NONSENSE")
        with pytest.raises(ValueError, match="throwback_mode"):
            run_backtest_on_bars(cfg, bars)
