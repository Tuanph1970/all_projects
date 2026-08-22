"""
Search telemetry (PR 1) -- see docs/ai-features/01-instrumentation.md.

The behaviour that matters most here is not that rows get written, but that
`result_count` is the TOTAL match count and that a telemetry failure can never
break a buyer's search.
"""
import pytest

from shared.models.analytics import SearchLog


def logs(db):
    return db.query(SearchLog).order_by(SearchLog.id).all()


# --------------------------------------------------------------------------
# Basic search
# --------------------------------------------------------------------------

def test_search_with_hits_is_logged(client, db, products):
    response = client.get("/api/v1/products/", params={"search": "vase"})

    assert response.status_code == 200
    assert len(response.json()) == 1

    rows = logs(db)
    assert len(rows) == 1
    row = rows[0]
    assert row.query_text == "vase"
    assert row.query_norm == "vase"
    assert row.result_count == 1
    assert row.source == "basic"
    assert row.user_id is None


def test_zero_result_search_is_logged(client, db, products):
    """The assortment-gap signal: a buyer looked for something we don't sell."""
    client.get("/api/v1/products/", params={"search": "teapot"})

    rows = logs(db)
    assert len(rows) == 1
    assert rows[0].result_count == 0


def test_result_count_is_total_not_page_length(client, db, products):
    """
    A buyer paging past the end must not look like a zero-result search, or
    the gap signal fills with noise.
    """
    response = client.get(
        "/api/v1/products/", params={"search": "handmade", "skip": 50, "limit": 20}
    )

    assert response.status_code == 200
    assert response.json() == []          # the page is empty ...
    assert logs(db)[0].result_count == 2  # ... but both products matched


def test_query_is_normalised_and_raw_text_preserved(client, db, products):
    client.get("/api/v1/products/", params={"search": "  BLUE   Vase "})

    row = logs(db)[0]
    assert row.query_norm == "blue vase"
    assert row.query_text == "BLUE   Vase"


def test_only_applied_filters_are_stored(client, db, products):
    client.get("/api/v1/products/", params={"search": "vase", "min_price": 10})

    assert logs(db)[0].filters == {"min_price": 10.0}


def test_unfiltered_search_stores_sql_null(client, db, products):
    """`none_as_null` keeps `WHERE filters IS NULL` meaningful."""
    client.get("/api/v1/products/", params={"search": "vase"})

    assert logs(db)[0].filters is None
    assert db.query(SearchLog).filter(SearchLog.filters.is_(None)).count() == 1


def test_anon_id_header_is_captured(client, db, products):
    client.get(
        "/api/v1/products/",
        params={"search": "mug"},
        headers={"X-Anon-Id": "device-abc"},
    )

    assert logs(db)[0].anon_id == "device-abc"


# --------------------------------------------------------------------------
# Guards
# --------------------------------------------------------------------------

@pytest.mark.parametrize("term", ["v", "va"])
def test_short_queries_are_not_logged(client, db, products, term):
    """Per-keystroke clients would otherwise bury aggregates in prefixes."""
    client.get("/api/v1/products/", params={"search": term})

    assert logs(db) == []


def test_plain_listing_is_not_logged(client, db, products):
    """Browsing the catalogue is not a search."""
    response = client.get("/api/v1/products/")

    assert response.status_code == 200
    assert logs(db) == []


# --------------------------------------------------------------------------
# Advanced search
# --------------------------------------------------------------------------

def test_advanced_search_is_logged_with_filters(client, db, products):
    response = client.get(
        "/api/v1/products/search/advanced",
        params={"q": "vase", "material": "stoneware"},
    )

    assert response.status_code == 200
    row = logs(db)[0]
    assert row.source == "advanced"
    assert row.query_norm == "vase"
    assert row.filters["material"] == "stoneware"


def test_advanced_filter_only_search_is_logged(client, db, products):
    """A filter with no query text still expresses intent."""
    response = client.get(
        "/api/v1/products/search/advanced", params={"material": "porcelain"}
    )

    assert response.status_code == 200
    rows = logs(db)
    assert len(rows) == 1
    assert rows[0].query_norm is None
    assert rows[0].filters == {"material": "porcelain", "sort_by": "relevance"}


# --------------------------------------------------------------------------
# Reliability class: TELEMETRY
# --------------------------------------------------------------------------

def test_telemetry_failure_does_not_break_search(client, db, products, monkeypatch):
    """
    The whole point of the telemetry class: a broken logging path must degrade
    to lost rows, never to a failed buyer request.
    """
    import app.services.search_logging as search_logging

    def exploding_session():
        raise RuntimeError("database is down")

    monkeypatch.setattr(search_logging, "SessionLocal", exploding_session)

    response = client.get("/api/v1/products/", params={"search": "vase"})

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert logs(db) == []
