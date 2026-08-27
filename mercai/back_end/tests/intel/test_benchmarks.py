"""
Category benchmarks.

The behaviour that matters here is what the benchmark REFUSES to do: publish
quartiles over a thin sample, and leak into the seller's own position figures.
"""
from decimal import Decimal
from pathlib import Path

import pytest

from shared.models.intel import CategoryBenchmark

SERVICE = Path(__file__).resolve().parents[2] / "services" / "intel"


@pytest.fixture()
def bm(load_service):
    load_service(SERVICE)
    import app.services.benchmarks as module
    return module


def _fake_pages(pages):
    """A stand-in for the Tiki API returning `pages` lists of prices."""
    import json

    calls = {"n": 0}

    def sampler(url, respect_budget=True):
        from app.services import fetcher

        page = calls["n"]
        calls["n"] += 1
        rows = [{"price": p} for p in (pages[page] if page < len(pages) else [])]
        return fetcher.FetchResult(
            status=fetcher.OK, url=url, final_url=url, http_status=200,
            body=json.dumps({"data": rows, "paging": {"total": 767}}),
        )

    return sampler


def test_quantiles_are_interpolated(bm):
    assert bm._quantile([100, 200, 300, 400, 500], 0.5) == 300
    assert bm._quantile([100, 200, 300, 400], 0.5) == 250
    assert bm._quantile([], 0.5) is None


def test_a_healthy_sample_publishes_quartiles(bm, db, monkeypatch):
    monkeypatch.setattr(bm, "PAGE_DELAY_SECONDS", 0)
    monkeypatch.setattr(bm.fetcher, "fetch",
                        _fake_pages([list(range(100_000, 100_000 + 40 * 1000, 1000))] * 3))
    row = bm.refresh(db, {
        "source": "tiki", "external_category_id": "3178",
        "mercai_category": "Bát đĩa", "label": "Tableware",
    })
    assert row.status == "ok"
    assert row.sample_size == 120
    assert row.catalogue_total == 767
    assert row.median is not None and row.p25 < row.median < row.p75


def test_a_thin_sample_is_recorded_but_not_published(bm, db, monkeypatch):
    """
    Eleven items would give a median, and showing it would be the same mistake
    MIN_COMPARABLE_N exists to prevent, one market over.
    """
    monkeypatch.setattr(bm, "PAGE_DELAY_SECONDS", 0)
    monkeypatch.setattr(bm.fetcher, "fetch", _fake_pages([[100_000] * 11, [], []]))
    row = bm.refresh(db, {
        "source": "tiki", "external_category_id": "9999",
        "mercai_category": "Ấm chén", "label": "Thin",
    })
    assert row.status == "insufficient_sample"
    assert row.median is None
    assert bm.as_payload(row) is None, "a thin sample must not reach the client"


def test_a_failed_fetch_is_recorded_as_its_status(bm, db, monkeypatch):
    from app.services import fetcher

    monkeypatch.setattr(bm, "PAGE_DELAY_SECONDS", 0)

    def refuse(url, respect_budget=True):
        raise fetcher.FetchRefused(fetcher.HOST_NOT_ALLOWED, "nope")

    monkeypatch.setattr(bm.fetcher, "fetch", refuse)
    row = bm.refresh(db, {
        "source": "tiki", "external_category_id": "3178",
        "mercai_category": "Bát đĩa", "label": "Tableware",
    })
    assert row.status == fetcher.HOST_NOT_ALLOWED
    assert row.median is None


def test_refresh_samples_a_shared_category_once(bm, db, monkeypatch):
    """
    Two Mercai categories point at Tiki's single tableware leaf. Sampling it
    twice would double the requests for identical numbers.
    """
    monkeypatch.setattr(bm, "PAGE_DELAY_SECONDS", 0)
    seen = []

    def counting(entry_db, entry):
        seen.append(entry["external_category_id"])
        return None

    monkeypatch.setattr(bm, "refresh", counting)
    monkeypatch.setattr(bm, "config", lambda: [
        {"source": "tiki", "external_category_id": "3178", "mercai_category": "Bát đĩa"},
        {"source": "tiki", "external_category_id": "3178", "mercai_category": "Ấm chén"},
    ])
    bm.refresh_all(db)
    assert seen == ["3178"]


def test_staleness_is_time_based(bm, db):
    from datetime import datetime, timedelta, timezone

    fresh = CategoryBenchmark(
        source="tiki", external_category_id="1", mercai_category_name="x",
        computed_at=datetime.now(timezone.utc), status="ok",
    )
    old = CategoryBenchmark(
        source="tiki", external_category_id="2", mercai_category_name="x",
        computed_at=datetime.now(timezone.utc) - timedelta(hours=48), status="ok",
    )
    assert bm.is_stale(fresh) is False
    assert bm.is_stale(old) is True
    assert bm.is_stale(None) is True


def test_the_payload_ships_its_caveat_with_the_numbers(bm, db, monkeypatch):
    """
    Whoever reads the median needs to know what it is a median OF. Burying that
    in a doc and shipping the number bare is how a benchmark misleads.
    """
    monkeypatch.setattr(bm, "config", lambda: [{
        "source": "tiki", "external_category_id": "3178",
        "mercai_category": "Bát đĩa", "notes": "Dominated by sets.",
    }])
    row = CategoryBenchmark(
        source="tiki", external_category_id="3178", mercai_category_name="Bát đĩa",
        status="ok", sample_size=120, median=Decimal(200_000),
        p25=Decimal(120_000), p75=Decimal(300_000),
    )
    payload = bm.as_payload(row)
    assert payload["caveat"] == "Dominated by sets."
    assert payload["sample_size"] == 120
