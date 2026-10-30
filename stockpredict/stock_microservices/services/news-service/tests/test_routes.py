"""N8 — read API (FR-NEWS-API): GET /news, GET /news/{id}, POST /ingest, POST /poll/{stream}."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.deps import container, get_repo
from app.main import app
from app.models.news_item import NewsItem

_BASE = "/stock_helper/api/v2/news"


@pytest.fixture
def api_client(news_repo):
    # Share one StaticPool in-memory DB across requests (default sqlite:// would give
    # each thread a fresh DB and break ingest->list).
    app.dependency_overrides[get_repo] = lambda: news_repo
    with TestClient(app) as c:
        yield c, news_repo
    app.dependency_overrides.clear()


def _seed(repo, **over):
    base = dict(
        source="vnstock", stream="company", symbol="FPT",
        ts_utc=datetime(2026, 7, 1, 9, 0, tzinfo=timezone.utc),
        title="FPT news", body="body", url="https://x/1", lang="vi",
        raw_json='{"k":"v"}', guid=None,
    )
    base.update(over)
    item = NewsItem(**base)
    repo.upsert(item)
    return item


def test_list_filters_by_symbol_and_sentiment(api_client):
    client, repo = api_client
    a = _seed(repo, symbol="FPT", guid="a")
    b = _seed(repo, symbol="ACB", guid="b")
    repo.mark_classified(a.news_id(), sentiment="good", category="new_product", score=0.8)
    repo.mark_classified(b.news_id(), sentiment="bad", category="regulatory", score=-0.5)

    r = client.get(f"{_BASE}/news", params={"symbol": "FPT"})
    assert r.status_code == 200
    data = r.json()["data"]
    assert len(data) == 1 and data[0]["symbol"] == "FPT"
    # list view omits the heavy raw_json
    assert "raw_json" not in data[0]

    r2 = client.get(f"{_BASE}/news", params={"sentiment": "bad"})
    assert [d["symbol"] for d in r2.json()["data"]] == ["ACB"]


def test_list_filter_by_stream_and_category(api_client):
    client, repo = api_client
    _seed(repo, symbol="FPT", guid="c")
    r = client.get(f"{_BASE}/news", params={"stream": "company", "symbol": "FPT"})
    assert r.status_code == 200 and r.json()["count"] == 1


def test_get_by_id_includes_raw_json(api_client):
    client, repo = api_client
    item = _seed(repo, guid="d")
    r = client.get(f"{_BASE}/news/{item.news_id()}")
    assert r.status_code == 200
    body = r.json()
    assert body["news_id"] == item.news_id()
    assert body["raw_json"] == '{"k":"v"}'      # detail includes raw payload


def test_get_missing_id_404(api_client):
    client, _ = api_client
    assert client.get(f"{_BASE}/news/nope").status_code == 404


def test_ingest_stores_then_dedups(api_client):
    client, repo = api_client
    payload = {
        "source": "manual", "stream": "company", "symbol": "FPT",
        "ts_utc": "2026-07-01T09:00:00+00:00", "title": "Manual item",
        "body": "b", "url": "https://x/m", "lang": "en", "raw_json": "{}", "guid": "m1",
    }
    r1 = client.post(f"{_BASE}/ingest", json=payload)
    assert r1.status_code == 200
    assert r1.json()["stored"] is True
    news_id = r1.json()["news_id"]

    r2 = client.post(f"{_BASE}/ingest", json=payload)
    assert r2.json()["stored"] is False          # dedup (EC-N2)
    assert r2.json()["news_id"] == news_id
    assert len(repo.query()) == 1


def test_poll_company_runs_container_poller(api_client):
    client, _ = api_client

    class FakePoller:
        def __init__(self):
            self.ran = 0

        async def tick(self):
            self.ran += 1
            return {"fetched": 3, "new": 2, "classified": 2, "notified": 1, "errors": 0}

    fake = FakePoller()
    container.company_poller = fake
    try:
        r = client.post(f"{_BASE}/poll/company")
        assert r.status_code == 200
        assert r.json()["new"] == 2
        assert fake.ran == 1
    finally:
        container.company_poller = None


def test_poll_company_503_when_not_running(api_client):
    client, _ = api_client
    container.company_poller = None
    assert client.post(f"{_BASE}/poll/company").status_code == 503


def test_poll_unknown_stream_400(api_client):
    client, _ = api_client
    assert client.post(f"{_BASE}/poll/bogus").status_code == 400


def test_poll_macro_503_when_not_running(api_client):
    client, _ = api_client
    container.macro_poller = None
    assert client.post(f"{_BASE}/poll/macro").status_code == 503


def test_poll_macro_runs_container_poller(api_client):
    client, _ = api_client

    class FakeMacro:
        def __init__(self):
            self.ran = 0

        async def tick(self):
            self.ran += 1
            return {"fetched": 2, "new": 2, "tagged": 2, "bridged": 0, "errors": 0}

    fake = FakeMacro()
    container.macro_poller = fake
    try:
        r = client.post(f"{_BASE}/poll/macro")
        assert r.status_code == 200
        assert r.json()["tagged"] == 2
        assert fake.ran == 1
    finally:
        container.macro_poller = None


def test_health_live_still_ok(api_client):
    client, _ = api_client
    assert client.get("/health/live").status_code == 200


# ---------------------------------------------------------------------------
# Backlog #106 — GET /news/features/{symbol}
# ---------------------------------------------------------------------------

def test_news_features_returns_one_row_per_calendar_date(api_client):
    client, repo = api_client
    r = client.get(f"{_BASE}/news/features/FPT",
                   params={"start": "2026-09-01", "end": "2026-09-05"})
    assert r.status_code == 200
    body = r.json()
    assert body["count"] == 5
    assert [d["date"] for d in body["data"]] == [
        "2026-09-01", "2026-09-02", "2026-09-03", "2026-09-04", "2026-09-05"]
    # Weekends included on purpose: news ages over them, and the caller reindexes
    # onto its own trading calendar.
    assert body["covariate_type"] == "past"
    assert body["features"] == ["news_intensity", "news_polarity"]


def test_news_features_decays_a_real_stored_item(api_client):
    client, repo = api_client
    it = _seed(repo, guid="feat-1", symbol="ACB",
               ts_utc=datetime(2026, 9, 1, 2, 0, tzinfo=timezone.utc))
    repo.mark_classified(it.news_id(), sentiment="good", category="earnings",
                         score=0.6, score_source="model")
    body = client.get(f"{_BASE}/news/features/ACB",
                      params={"start": "2026-09-01", "end": "2026-09-06",
                              "halflife_days": 5}).json()
    rows = body["data"]
    assert rows[0]["intensity"] == 1.0
    assert rows[0]["polarity"] == 0.6
    assert rows[-1]["intensity"] == pytest.approx(0.5, abs=1e-6)   # one half-life
    assert body["articles_in_window"] == 1
    assert body["scored_in_window"] == 1
    assert body["polarity_available"] is True


def test_news_features_reports_when_no_tone_is_trustworthy(api_client):
    """The field that stops a flat polarity looking like 'the news was neutral'.
    A row scored before #112 carries score_source NULL and is excluded from
    polarity, while still counting as coverage."""
    client, repo = api_client
    it = _seed(repo, guid="legacy-1", symbol="POW",
               ts_utc=datetime(2026, 9, 1, 2, 0, tzinfo=timezone.utc))
    repo.mark_classified(it.news_id(), sentiment="neutral", category="other",
                         score=0.5, score_source=None)
    body = client.get(f"{_BASE}/news/features/POW",
                      params={"start": "2026-09-01", "end": "2026-09-02"}).json()
    assert body["articles_in_window"] == 1      # coverage counted
    assert body["scored_in_window"] == 0        # tone not counted
    assert body["polarity_available"] is False
    assert body["data"][0]["intensity"] == 1.0
    assert body["data"][0]["polarity"] == 0.0


def test_news_features_is_case_insensitive_on_the_symbol(api_client):
    client, repo = api_client
    it = _seed(repo, guid="case-1", symbol="VND",
               ts_utc=datetime(2026, 9, 1, 2, 0, tzinfo=timezone.utc))
    repo.mark_classified(it.news_id(), sentiment="bad", category="regulatory",
                         score=-0.3, score_source="model")
    body = client.get(f"{_BASE}/news/features/vnd",
                      params={"start": "2026-09-01", "end": "2026-09-01"}).json()
    assert body["symbol"] == "VND"
    assert body["data"][0]["intensity"] == 1.0


def test_news_features_rejects_an_inverted_range(api_client):
    client, _ = api_client
    r = client.get(f"{_BASE}/news/features/FPT",
                   params={"start": "2026-09-10", "end": "2026-09-01"})
    assert r.status_code == 422
    assert "precedes" in r.json()["detail"]


def test_news_features_rejects_a_non_positive_halflife(api_client):
    client, _ = api_client
    r = client.get(f"{_BASE}/news/features/FPT",
                   params={"start": "2026-09-01", "end": "2026-09-02",
                           "halflife_days": 0})
    assert r.status_code == 422


def test_news_features_route_is_not_shadowed_by_the_detail_route(api_client):
    """GET /news/{news_id} would happily match 'features/FPT' if it were declared
    first. Ordering is load-bearing here, so it gets a test."""
    client, _ = api_client
    r = client.get(f"{_BASE}/news/features/FPT",
                   params={"start": "2026-09-01", "end": "2026-09-01"})
    assert r.status_code == 200
    assert "data" in r.json()
