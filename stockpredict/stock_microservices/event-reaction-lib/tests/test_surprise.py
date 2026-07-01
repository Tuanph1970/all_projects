"""T3 — surprise/ stage: observed constructors (FR-SURP, EC1, EC2).

Mandatory gate: a standardized surprise has the right sign and scale.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from event_reaction.exceptions import InsufficientDataError
from event_reaction.surprise import make_surprise


def _prior_consensus(surprises: np.ndarray) -> pd.DataFrame:
    """Prior same-kind events whose (actual - consensus) equals `surprises`."""
    return pd.DataFrame({"actual": surprises, "consensus": np.zeros_like(surprises)})


class TestConsensusSignScale:
    """MANDATORY: standardized surprise has the right sign/scale."""

    def test_scale_and_positive_sign(self):
        sp = np.array([0.1, -0.2, 0.3, -0.1, 0.15])
        scale = float(np.std(sp, ddof=1))
        prior = _prior_consensus(sp)
        # actual - consensus = 2*scale  ->  standardized s must be exactly 2.0
        row = pd.Series({"actual": 2 * scale, "consensus": 0.0, "kind": "k"})
        out = make_surprise(row, prior, method="consensus")
        assert out.scale == pytest.approx(scale)
        assert out.s == pytest.approx(2.0)
        assert out.sign == 1
        assert out.expected == 0.0

    def test_negative_sign(self):
        sp = np.array([0.1, -0.2, 0.3, -0.1, 0.15])
        scale = float(np.std(sp, ddof=1))
        row = pd.Series({"actual": -1.0 * scale, "consensus": 0.0})
        out = make_surprise(row, _prior_consensus(sp), method="consensus")
        assert out.s == pytest.approx(-1.0)
        assert out.sign == -1

    def test_scale_excludes_current_event(self):
        """Scale uses only prior same-kind events, never the current one (EC1)."""
        sp = np.array([0.1, -0.2, 0.3, -0.1, 0.15])
        prior = _prior_consensus(sp)
        row = pd.Series({"actual": 99.0, "consensus": 0.0})  # wild current surprise
        out = make_surprise(row, prior, method="consensus")
        # If the current 99.0 surprise leaked into the scale, std would balloon.
        assert out.scale == pytest.approx(float(np.std(sp, ddof=1)))


class TestShortHistoryFallback:
    def test_empty_prior_scale_is_one(self):
        row = pd.Series({"actual": 0.7, "consensus": 0.2})
        out = make_surprise(row, None, method="consensus")
        assert out.scale == 1.0
        assert out.s == pytest.approx(0.5)  # unstandardised

    def test_single_prior_scale_is_one(self):
        row = pd.Series({"actual": 0.7, "consensus": 0.2})
        out = make_surprise(row, _prior_consensus(np.array([0.3])), method="consensus")
        assert out.scale == 1.0


class TestFutures:
    def test_recovers_actual_minus_futures(self):
        row = pd.Series({"actual": 0.50, "consensus": 0.30})
        out = make_surprise(row, None, method="futures", futures=0.40)
        assert out.expected == 0.40
        assert out.s_raw == pytest.approx(0.10)

    def test_missing_futures_raises(self):
        row = pd.Series({"actual": 0.50, "consensus": 0.30})
        with pytest.raises(InsufficientDataError):
            make_surprise(row, None, method="futures")


class TestOdds:
    def _odds(self):
        idx = pd.to_datetime(
            ["2022-05-31 12:00", "2022-06-01 09:00", "2022-06-01 18:00"], utc=True
        )
        return pd.Series([0.20, 0.30, 0.90], index=idx)

    def test_uses_last_odds_strictly_before_event(self):
        # Event at 18:00; the 18:00 odds (== t0) must NOT be used, the 09:00 one must.
        row = pd.Series({"actual": 1.0, "ts_utc": pd.Timestamp("2022-06-01 18:00", tz="UTC")})
        out = make_surprise(row, None, method="odds", odds=self._odds())
        assert out.expected == pytest.approx(0.30)
        assert out.s_raw == pytest.approx(0.70)

    def test_no_pre_event_odds_raises(self):
        row = pd.Series({"actual": 1.0, "ts_utc": pd.Timestamp("2022-05-01 00:00", tz="UTC")})
        with pytest.raises(InsufficientDataError):
            make_surprise(row, None, method="odds", odds=self._odds())


class TestDeferredAndValidation:
    def test_llm_not_implemented(self):
        row = pd.Series({"actual": 1.0, "consensus": 0.0})
        with pytest.raises(NotImplementedError):
            make_surprise(row, None, method="llm")

    def test_unknown_method(self):
        row = pd.Series({"actual": 1.0, "consensus": 0.0})
        with pytest.raises(ValueError):
            make_surprise(row, None, method="nope")

    def test_missing_actual(self):
        row = pd.Series({"consensus": 0.0})
        with pytest.raises(InsufficientDataError):
            make_surprise(row, None, method="consensus")
