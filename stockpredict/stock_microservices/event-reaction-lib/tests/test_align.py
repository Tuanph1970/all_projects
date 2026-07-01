"""T2 — align/ stage: log returns, event-day resolution, windows (FR-ALIGN, EC1, EC6)."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from event_reaction.align import log_returns, make_windows, resolve_event_day
from event_reaction.exceptions import AlignmentError, InsufficientDataError


class TestLogReturns:
    def test_matches_formula_and_length(self, price_series):
        p = price_series(n=50)
        r = log_returns(p)
        assert len(r) == len(p) - 1
        expected = np.log(p.to_numpy()[1:] / p.to_numpy()[:-1])
        np.testing.assert_allclose(r.to_numpy(), expected)

    def test_index_stays_tz_aware_utc(self, price_series):
        p = price_series(n=20)
        r = log_returns(p)
        assert str(r.index.tz) == "UTC"
        assert r.index.equals(p.index[1:])  # indexed by prices.index[1:]

    def test_naive_index_rejected(self):
        p = pd.Series([1.0, 2.0, 3.0], index=pd.date_range("2022-01-03", periods=3, freq="B"))
        with pytest.raises(AlignmentError):
            log_returns(p)

    def test_too_short(self, price_series):
        with pytest.raises(InsufficientDataError):
            log_returns(price_series(n=1))


class TestResolveEventDay:
    def test_naive_timestamp_rejected(self, price_series):
        idx = price_series(n=30).index
        with pytest.raises(AlignmentError):
            resolve_event_day(pd.Timestamp("2022-01-10 12:00"), idx)  # naive

    def test_weekend_resolves_to_next_trading_day(self, utc_index):
        # 2022-01-03 is a Monday; build a clean business-day index.
        idx = utc_index(20, start="2022-01-03")
        # 2022-01-08 is a Saturday -> next trading day is Monday 2022-01-10.
        pos = resolve_event_day(pd.Timestamp("2022-01-08 09:00", tz="UTC"), idx)
        assert idx[pos].date().isoformat() == "2022-01-10"

    def test_after_close_resolves_to_announcement_day(self, utc_index):
        idx = utc_index(20, start="2022-01-03")
        # An after-close instant on a trading day resolves to THAT day (announcement date).
        pos = resolve_event_day(pd.Timestamp("2022-01-05 22:30", tz="UTC"), idx)
        assert idx[pos].date().isoformat() == "2022-01-05"

    def test_event_after_last_bar_rejected(self, utc_index):
        idx = utc_index(10, start="2022-01-03")
        with pytest.raises(AlignmentError):
            resolve_event_day(pd.Timestamp("2030-01-01 00:00", tz="UTC"), idx)


class TestMakeWindows:
    def test_estimation_ends_strictly_before_t0_with_gap(self):
        aligned = make_windows(200, n=400, L=120, g=5, k1=1, k2=1)
        est_start, est_end = aligned.est_window
        assert est_end < aligned.t0_index                     # strictly before t0 (EC1)
        assert aligned.t0_index - est_end == 5                # gap g
        assert est_end - est_start == 120                     # L observations

    def test_event_window_half_open_includes_t0_plus_k2(self):
        aligned = make_windows(200, n=400, k1=1, k2=1)
        ev_start, ev_end = aligned.event_window
        assert ev_start == 199 and ev_end == 202             # [t0-1, t0+1+1)

    def test_window_past_left_boundary_raises(self):
        with pytest.raises(AlignmentError):
            make_windows(10, n=400, L=120, g=5)              # needs 125 bars before t0

    def test_window_past_right_boundary_raises(self):
        with pytest.raises(AlignmentError):
            make_windows(399, n=400, k1=1, k2=5)             # t0+k2 beyond data
