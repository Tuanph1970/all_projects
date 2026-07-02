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
