"""N1 — service scaffold: health, metrics, config defaults (offline)."""
from __future__ import annotations

from app.config import get_settings


def test_health_live(client):
    r = client.get("/health/live")
    assert r.status_code == 200
    assert r.json() == {"status": "alive"}


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "healthy"
    assert body["service"] == "news-service"


def test_health_ready(client):
    r = client.get("/health/ready")
    assert r.status_code == 200
    assert r.json() == {"status": "ready"}


def test_metrics_endpoint(client):
    r = client.get("/metrics")
    assert r.status_code == 200
    assert "news_requests_total" in r.text


def test_router_mounted_under_prefix(client):
    # The versioned router is mounted; OpenAPI is served under the news prefix.
    r = client.get("/stock_helper/api/v2/news/openapi.json")
    assert r.status_code == 200


def test_config_defaults():
    s = get_settings()
    assert s.SERVICE_NAME == "news-service"
    assert s.PORT == 8013
    assert s.API_PREFIX == "stock_helper"
    # Stream toggles: company on by default; macro/bridge/email off until configured.
    assert s.ENABLE_COMPANY is True
    assert s.ENABLE_MACRO is False
    assert s.ENABLE_BRIDGE is False
    assert s.ENABLE_EMAIL is False
    # Sentiments that trigger a notification (good/bad only — EC-N8).
    assert s.notify_sentiments == ["good", "bad"]
    # Upstream services this subsystem talks to (EC-N4/EC-N5/EC-N10/bridge).
    for url in (
        s.STOCK_DATA_SERVICE_URL,
        s.AI_INSIGHTS_SERVICE_URL,
        s.PORTFOLIO_SERVICE_URL,
        s.DECISION_HELPER_SERVICE_URL,
        s.EVENT_REACTION_SERVICE_URL,
    ):
        assert url.startswith("http")
