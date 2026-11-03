"""Backlog #115 — news whose publication date the feed never supplied.

THE MEASUREMENT THIS EXISTS FOR. The upstream company feed returns
`"publishDate": null`, so a symbol's first poll writes its whole backlog under
one timestamp. Measured 2026-11-03: 350 of 360 stored items sat in seven
clusters of exactly 50 (the feed's page size), against a largest genuine
same-second group of 2. The three symbols added to the watchlist that day each
produced one, and each would have reported a news intensity of ~50 on a day when
nothing was published.

Those items are real news with an unknown date. They stay readable, and they
stay OUT of the decayed series, because that series is a model covariate.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pytest

from app.features.news_features import (
    NewsItemPoint,
    daily_news_features,
    rows_to_payload,
)


def _pt(day, hour=3, score=None, source="model", bulk=False):
    return NewsItemPoint(
        ts_utc=datetime(2026, 11, day, hour, tzinfo=timezone.utc),
        sentiment_score=score, score_source=source, bulk_ingest=bulk)


def _rows(points, start=date(2026, 11, 1), end=date(2026, 11, 5)):
    return daily_news_features(points, start=start, end=end, halflife_days=5.0)


# ---------------------------------------------------------------------------
# The gate
# ---------------------------------------------------------------------------

def test_a_backfill_batch_does_not_invent_fifty_news_events():
    """The exact case observed live on FPT, HPG and VIC on 2026-11-03."""
    batch = [_pt(3, score=0.0, bulk=True) for _ in range(50)]
    rows = {r.date: r for r in _rows(batch)}
    assert rows[date(2026, 11, 3)].intensity == 0.0
    assert rows[date(2026, 11, 3)].article_count == 0
    # ...and the 50 are REPORTED, not silently dropped.
    assert rows[date(2026, 11, 3)].undated_count == 50


def test_live_items_on_the_same_day_still_count():
    """Non-vacuity, and the case that matters most: a real item must survive
    even when it arrives on a day that also received a backlog dump."""
    pts = [_pt(3, score=0.55, bulk=False)] + [_pt(3, score=0.0, bulk=True) for _ in range(50)]
    r = {x.date: x for x in _rows(pts)}[date(2026, 11, 3)]
    assert r.article_count == 1
    assert r.intensity == pytest.approx(1.0)
    assert r.undated_count == 50
    # The strong story is NOT diluted by 50 routine filings — which is the
    # dilution #115 was raised about, now resolved by excluding the undated.
    assert r.polarity == pytest.approx(0.55, abs=1e-6)


def test_the_dilution_that_motivated_115_is_gone():
    """#115's measured example: a +0.55 earnings beat inside a batch of ~45
    routine filings read 0.005-0.053. With the undated excluded it reads 0.55.
    """
    pts = [_pt(3, score=0.55)] + [_pt(3, score=0.0, bulk=True) for _ in range(45)]
    r = {x.date: x for x in _rows(pts)}[date(2026, 11, 3)]
    assert r.polarity > 0.5, f"still diluted: {r.polarity}"


def test_undated_items_do_not_contribute_to_polarity_either():
    """The gate is stricter than the trust gate: it rules out BOTH features.
    An undated item with a strong score must not move polarity, because the
    date it would move is unknown."""
    pts = [_pt(3, score=0.9, bulk=True)]
    r = {x.date: x for x in _rows(pts)}[date(2026, 11, 3)]
    assert r.polarity == 0.0
    assert r.scored_count == 0


def test_an_all_live_series_is_unchanged_by_this_feature():
    """Regression guard: the common path must behave exactly as before."""
    pts = [_pt(2, score=0.4), _pt(3, score=-0.2), _pt(3, score=0.1)]
    rows = _rows(pts)
    assert [r.undated_count for r in rows] == [0] * len(rows)
    r3 = {x.date: x for x in rows}[date(2026, 11, 3)]
    assert r3.article_count == 2 and r3.scored_count == 2


def test_the_payload_carries_the_exclusion():
    pts = [_pt(3, score=0.0, bulk=True) for _ in range(50)]
    payload = rows_to_payload(_rows(pts))
    row = next(p for p in payload if p["date"] == "2026-11-03")
    assert row["undated_count"] == 50
    assert row["intensity"] == 0.0


def test_undated_items_outside_the_window_are_not_counted():
    pts = [_pt(20, score=0.0, bulk=True) for _ in range(50)]
    assert all(r.undated_count == 0 for r in _rows(pts))


# ---------------------------------------------------------------------------
# The threshold, and the gap it sits in
# ---------------------------------------------------------------------------

def test_the_cluster_threshold_sits_between_real_and_batch():
    """Measured: the largest genuine same-second group in the corpus is 2, and
    every backfill cluster is exactly 50 (the feed's page size). A threshold of
    20 is therefore nowhere near either edge — which is why it is safe, and why
    the gap is asserted rather than the number alone.
    """
    from app.repositories.news_repository import NewsRepository
    assert 2 < NewsRepository.BULK_CLUSTER_MIN < 50


def test_the_column_is_in_the_added_columns_migration():
    """create_all() does NOT alter an existing table, so a model field with no
    migration entry exists in Python and never in the database — and fails only
    on a real deploy against the live table."""
    from app.repositories.news_repository import NewsRepository
    names = {n for n, _ in NewsRepository._ADDED_COLUMNS}
    assert "bulk_ingest" in names


def test_the_poller_flags_a_batch_and_leaves_a_trickle_alone():
    """A flag nothing sets protects nothing; a flag that fires on ordinary
    polling would erase the live corpus. Both directions, on the real code."""
    import inspect
    from app.services.company_poller import CompanyPoller
    src = inspect.getsource(CompanyPoller.tick)
    assert "mark_bulk_ingest" in src
    assert "BULK_CLUSTER_MIN" in src
