"""Backlog #106 — joining news covariates onto a solution's feature frame."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from app.services.news_covariates import (
    NEWS_FEATURE_COLUMNS,
    NewsCovariateError,
    attach_news_features,
    fetch_news_features,
    news_coverage,
)


def _frame(dates) -> pd.DataFrame:
    idx = pd.DatetimeIndex(dates)
    return pd.DataFrame({"close": np.arange(len(idx), dtype=float)}, index=idx)


def _rows(*pairs):
    return [{"date": d, "intensity": i, "polarity": p} for d, i, p in pairs]


# ---------------------------------------------------------------------------
# the join
# ---------------------------------------------------------------------------

def test_values_land_on_their_matching_bar():
    df = _frame(["2026-09-01", "2026-09-02", "2026-09-03"])
    out = attach_news_features(df, _rows(
        ("2026-09-01", 2.0, 0.4), ("2026-09-02", 1.5, 0.3), ("2026-09-03", 1.1, 0.2)))
    assert list(out["news_intensity"]) == [2.0, 1.5, 1.1]
    assert list(out["news_polarity"]) == [0.4, 0.3, 0.2]


def test_a_bar_with_no_news_row_is_zero_not_nan():
    """dropna() later governs the usable window, so a NaN here would delete
    every bar outside the news window — on this corpus, almost all of them."""
    df = _frame(["2026-09-01", "2026-09-02"])
    out = attach_news_features(df, _rows(("2026-09-02", 1.0, 0.5)))
    assert out["news_intensity"].isna().sum() == 0
    assert out["news_polarity"].isna().sum() == 0
    assert out.loc["2026-09-01", "news_intensity"] == 0.0
    assert len(out.dropna()) == len(out), "news columns must not shrink the window"


def test_weekend_rows_are_dropped_and_do_not_shift_the_alignment():
    """The series is calendar-daily; the frame is the trading calendar. The
    weekend's decay is already inside Monday's value upstream."""
    df = _frame(["2026-09-04", "2026-09-07"])        # Friday, Monday
    out = attach_news_features(df, _rows(
        ("2026-09-04", 1.0, 0.6), ("2026-09-05", 0.9, 0.6),
        ("2026-09-06", 0.8, 0.6), ("2026-09-07", 0.7, 0.6)))
    assert list(out["news_intensity"]) == [1.0, 0.7]


def test_extra_news_dates_outside_the_frame_are_ignored():
    df = _frame(["2026-09-02"])
    out = attach_news_features(df, _rows(
        ("2026-08-01", 9.0, 0.9), ("2026-09-02", 1.0, 0.1), ("2026-12-01", 9.0, 0.9)))
    assert list(out["news_intensity"]) == [1.0]


def test_an_intraday_timestamped_index_still_matches_by_date():
    df = _frame(["2026-09-01 09:30", "2026-09-02 09:30"])
    out = attach_news_features(df, _rows(("2026-09-01", 3.0, 0.2)))
    assert list(out["news_intensity"]) == [3.0, 0.0]


def test_no_rows_at_all_yields_zero_columns_not_a_crash():
    df = _frame(["2026-09-01", "2026-09-02"])
    out = attach_news_features(df, [])
    assert list(out["news_intensity"]) == [0.0, 0.0]
    assert all(c in out.columns for c in NEWS_FEATURE_COLUMNS)


def test_a_malformed_date_is_skipped_rather_than_poisoning_the_join():
    df = _frame(["2026-09-01"])
    out = attach_news_features(df, [
        {"date": "not-a-date", "intensity": 5.0, "polarity": 1.0},
        {"date": "2026-09-01", "intensity": 1.0, "polarity": 0.1},
    ])
    assert list(out["news_intensity"]) == [1.0]


def test_the_original_frame_is_not_mutated():
    df = _frame(["2026-09-01"])
    attach_news_features(df, _rows(("2026-09-01", 1.0, 0.1)))
    assert "news_intensity" not in df.columns


def test_existing_columns_survive_the_join():
    df = _frame(["2026-09-01", "2026-09-02"])
    df["rsi_14"] = [55.0, 60.0]
    out = attach_news_features(df, _rows(("2026-09-01", 1.0, 0.1)))
    assert list(out["rsi_14"]) == [55.0, 60.0]
    assert list(out["close"]) == [0.0, 1.0]


def test_an_empty_frame_gets_the_columns_with_no_rows():
    out = attach_news_features(_frame([]), _rows(("2026-09-01", 1.0, 0.1)))
    assert all(c in out.columns for c in NEWS_FEATURE_COLUMNS)
    assert len(out) == 0


# ---------------------------------------------------------------------------
# causality — these columns must not leak (CLAUDE.md C1)
# ---------------------------------------------------------------------------

def test_news_after_the_last_bar_cannot_change_any_attached_value():
    """The no-leakage check at the join boundary: rows dated beyond the frame
    must not alter a single bar. A forward-fill or an interpolate would fail."""
    df = _frame(["2026-09-01", "2026-09-02", "2026-09-03"])
    base = _rows(("2026-09-01", 1.0, 0.2), ("2026-09-02", 0.8, 0.2), ("2026-09-03", 0.6, 0.2))
    plain = attach_news_features(df, base)
    with_future = attach_news_features(df, base + _rows(("2026-09-10", 50.0, -1.0)))
    pd.testing.assert_frame_equal(plain, with_future)


def test_a_gap_is_not_forward_filled_from_an_earlier_bar():
    """Carrying yesterday's intensity into a day news-service reported nothing
    for would invent coverage. The decay belongs upstream, not here."""
    df = _frame(["2026-09-01", "2026-09-02"])
    out = attach_news_features(df, _rows(("2026-09-01", 4.0, 0.9)))
    assert out.loc["2026-09-02", "news_intensity"] == 0.0
    assert out.loc["2026-09-02", "news_polarity"] == 0.0


# ---------------------------------------------------------------------------
# coverage reporting
# ---------------------------------------------------------------------------

def test_coverage_reports_how_little_the_feature_actually_covers():
    df = _frame(["2026-09-01", "2026-09-02", "2026-09-03", "2026-09-04"])
    out = attach_news_features(df, _rows(("2026-09-02", 1.0, 0.5)))
    cov = news_coverage(out)
    assert cov["attached"] is True
    assert cov["rows"] == 4
    assert cov["rows_with_coverage"] == 1
    assert cov["coverage_fraction"] == 0.25
    assert cov["intensity_max"] == 1.0
    assert cov["polarity_nonzero_rows"] == 1
    assert "not neutral news" in cov["note"]


def test_coverage_says_so_when_the_columns_were_never_attached():
    assert news_coverage(_frame(["2026-09-01"]))["attached"] is False


def test_coverage_distinguishes_untrusted_tone_from_calm_news():
    """Intensity present with polarity flat is the #113 signature, and the
    report has to make it legible rather than look like calm news."""
    df = _frame(["2026-09-01", "2026-09-02"])
    out = attach_news_features(df, _rows(("2026-09-01", 3.0, 0.0), ("2026-09-02", 2.1, 0.0)))
    cov = news_coverage(out)
    assert cov["rows_with_coverage"] == 2
    assert cov["polarity_nonzero_rows"] == 0


# ---------------------------------------------------------------------------
# the fetch
# ---------------------------------------------------------------------------

class _Resp:
    def __init__(self, status_code, payload=None):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload


class _Client:
    def __init__(self, resp=None, exc=None):
        self._resp, self._exc = resp, exc
        self.seen = {}

    async def get(self, url, params=None):
        if self._exc:
            raise self._exc
        self.seen = {"url": url, "params": params}
        return self._resp


@pytest.mark.asyncio
async def test_fetch_returns_the_data_rows_and_builds_the_right_url():
    rows = _rows(("2026-09-01", 1.0, 0.2))
    c = _Client(_Resp(200, {"data": rows}))
    out = await fetch_news_features(
        c, base_url="http://news-service:8013", api_prefix="stock_helper",
        symbol="acb", start="2026-09-01", end="2026-09-30", halflife_days=5)
    assert out == rows
    assert c.seen["url"] == (
        "http://news-service:8013/stock_helper/api/v2/news/news/features/ACB")
    assert c.seen["params"]["halflife_days"] == 5


@pytest.mark.asyncio
async def test_fetch_raises_rather_than_training_without_the_feature():
    """Returning [] on failure would train a model on all-zero news columns and
    report it as a news-aware model — the #109 mislabelling defect again."""
    with pytest.raises(NewsCovariateError, match="HTTP 503"):
        await fetch_news_features(
            _Client(_Resp(503)), base_url="http://n", api_prefix="stock_helper",
            symbol="ACB", start="2026-09-01", end="2026-09-30", halflife_days=5)


@pytest.mark.asyncio
async def test_fetch_raises_on_a_transport_failure():
    with pytest.raises(NewsCovariateError, match="unreachable"):
        await fetch_news_features(
            _Client(exc=OSError("connection refused")), base_url="http://n",
            api_prefix="stock_helper", symbol="ACB", start="2026-09-01",
            end="2026-09-30", halflife_days=5)


@pytest.mark.asyncio
async def test_fetch_raises_when_the_payload_has_no_data_list():
    with pytest.raises(NewsCovariateError, match="no 'data' list"):
        await fetch_news_features(
            _Client(_Resp(200, {"oops": 1})), base_url="http://n",
            api_prefix="stock_helper", symbol="ACB", start="2026-09-01",
            end="2026-09-30", halflife_days=5)


# ---------------------------------------------------------------------------
# Backlog #116 — coverage has to be reported PER SPLIT.
#
# "36 of 703 bars covered (5.1%)" reads as sparse-but-usable and hides the only
# thing that mattered on the real corpus: all 36 were in the validation span, so
# the model trained on an identically-zero column. Measured on POW: rmse 0.4323
# -> 0.9601 and r2 +0.605 -> -0.948 from adding the two columns.
# ---------------------------------------------------------------------------

def _dated(n, start="2026-01-01"):
    idx = pd.bdate_range(start, periods=n)
    return pd.DataFrame({"close": np.arange(len(idx), dtype=float)}, index=idx)


def test_coverage_splits_train_and_validation():
    df = _dated(10)
    rows = [{"date": d.strftime("%Y-%m-%d"), "intensity": 1.0, "polarity": 0.2}
            for d in df.index[:4]]
    cov = news_coverage(attach_news_features(df, rows), train_ratio=0.8)
    assert cov["train_rows"] == 8
    assert cov["validation_rows"] == 2
    assert cov["train_rows_with_coverage"] == 4
    assert cov["validation_rows_with_coverage"] == 0


def test_coverage_flags_a_feature_the_model_cannot_learn_from():
    """The POW case: every covered bar falls in validation, so training sees a
    constant. This is the field that had to exist."""
    df = _dated(10)
    rows = [{"date": d.strftime("%Y-%m-%d"), "intensity": 50.0, "polarity": 0.1}
            for d in df.index[8:]]
    cov = news_coverage(attach_news_features(df, rows), train_ratio=0.8)
    assert cov["train_rows_with_coverage"] == 0
    assert cov["trainable"] is False
    assert "training" in cov["warning"].lower()


def test_coverage_is_trainable_when_the_training_span_sees_news():
    df = _dated(10)
    rows = [{"date": d.strftime("%Y-%m-%d"), "intensity": 2.0, "polarity": 0.3}
            for d in df.index[:6]]
    cov = news_coverage(attach_news_features(df, rows), train_ratio=0.8)
    assert cov["train_rows_with_coverage"] == 6
    assert cov["trainable"] is True
    assert cov.get("warning") in (None, "")


def test_a_corpus_with_no_coverage_at_all_is_not_flagged_as_harmful():
    """Zero everywhere is dead weight, not a trap: the scaler leaves a column
    that is constant on BOTH sides alone, so it degrades nothing. Only a
    train-constant/validation-varying column saturates the network."""
    cov = news_coverage(attach_news_features(_dated(10), []), train_ratio=0.8)
    assert cov["train_rows_with_coverage"] == 0
    assert cov["validation_rows_with_coverage"] == 0
    assert cov["trainable"] is False
    assert "no coverage" in cov["warning"].lower()


def test_coverage_without_a_train_ratio_keeps_the_old_shape():
    """Callers that do not know the split still get the overall numbers."""
    cov = news_coverage(attach_news_features(_dated(10), []))
    assert cov["attached"] is True
    assert "train_rows" not in cov
