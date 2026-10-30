"""N5 — classifier adapter (FR-NEWS-CLASSIFY, EC-N5/N7/N11).

Sentiment + score come from ai-insights NewsAnalysis (the LLM — EC-N5). ai-insights'
response carries NO category, so `category` is keyword-derived here over the closed
company vocab (SRS Appendix A). Errors/timeouts -> ClassificationError (the poller then
stores the item unclassified and retries — EC-N7).
"""
from __future__ import annotations

from datetime import datetime, timezone

import httpx
import pytest

from app.exceptions import ClassificationError
from app.ingest.classifier import NewsClassifier
from app.models.news_item import NewsItem

_BASE = "http://ai-insights-service:8005"


def _item(title="Company update", body="Some neutral text.") -> NewsItem:
    return NewsItem(
        source="vnstock", stream="company", symbol="FPT",
        ts_utc=datetime(2026, 7, 1, 9, 0, tzinfo=timezone.utc),
        title=title, body=body, url="https://x/y", lang="vi", raw_json="{}", guid="g1",
    )


def _clf(handler) -> NewsClassifier:
    return NewsClassifier(_BASE, client=httpx.Client(transport=httpx.MockTransport(handler)))


def _resp(sentiment, score):
    def handler(req):
        assert req.url.path.endswith("/ai/news-analysis")
        return httpx.Response(200, json={
            "symbol": "FPT", "overall_sentiment": sentiment, "sentiment_score": score,
            "key_events": [], "potential_impact": "", "summary": "",
            "generated_at": "2026-07-01T09:00:00+00:00",
        })
    return handler


@pytest.mark.parametrize("raw,expected", [
    ("bullish", "good"), ("positive", "good"),
    ("bearish", "bad"), ("negative", "bad"),
    ("neutral", "neutral"),
])
def test_sentiment_mapping(raw, expected):
    c = _clf(_resp(raw, 0.3)).classify(_item())
    assert c.sentiment == expected
    assert c.score == 0.3


def test_unknown_sentiment_and_no_keywords_maps_to_neutral_other():
    c = _clf(_resp("something-weird", 0.0)).classify(_item(title="Generic", body="text"))
    assert c.sentiment == "neutral"
    assert c.category == "other"


@pytest.mark.parametrize("title,expected_cat", [
    ("FPT launches new product line", "new_product"),
    ("FPT ra mắt sản phẩm mới", "new_product"),
    ("New AI technology platform unveiled", "new_tech"),
    ("Board appoints new CEO", "management"),
    ("Company fined by regulator over license", "regulatory"),
    ("Q2 earnings: revenue and profit up", "earnings"),
    ("FPT signs partnership agreement", "partnership"),
])
def test_category_keyword_derivation(title, expected_cat):
    c = _clf(_resp("neutral", 0.0)).classify(_item(title=title, body=""))
    assert c.category == expected_cat


def _resp_with_category(sentiment, score, category):
    def handler(req):
        return httpx.Response(200, json={
            "symbol": "FPT", "overall_sentiment": sentiment, "sentiment_score": score,
            "category": category, "key_events": [], "potential_impact": "",
            "summary": "", "generated_at": "2026-07-01T09:00:00+00:00",
        })
    return handler


def test_prefers_ai_insights_category_over_keywords():
    # Title keywords say "new_product", but ai-insights labels it "management":
    # the service-provided category wins.
    c = _clf(_resp_with_category("good", 0.4, "management")).classify(
        _item(title="FPT launches new product", body="")
    )
    assert c.category == "management"


def test_falls_back_to_keywords_when_category_invalid_or_missing():
    # Out-of-vocab category from upstream -> local keyword derivation kicks in.
    c = _clf(_resp_with_category("neutral", 0.0, "totally-bogus")).classify(
        _item(title="Board appoints new CEO", body="")
    )
    assert c.category == "management"


def test_score_is_clamped_to_unit_range():
    assert _clf(_resp("bullish", 2.5)).classify(_item()).score == 1.0
    assert _clf(_resp("bearish", -9.0)).classify(_item()).score == -1.0


def test_missing_or_nonnumeric_score_defaults_zero():
    def handler(req):
        return httpx.Response(200, json={"symbol": "FPT", "overall_sentiment": "neutral"})
    assert _clf(handler).classify(_item()).score == 0.0


def test_non_200_raises_classification_error():
    def handler(req):
        return httpx.Response(500)
    with pytest.raises(ClassificationError):
        _clf(handler).classify(_item())


def test_network_error_raises_classification_error():
    def handler(req):
        raise httpx.ConnectTimeout("slow")
    with pytest.raises(ClassificationError):
        _clf(handler).classify(_item())


def test_request_carries_symbol_and_title():
    seen = {}

    def handler(req):
        import json
        seen.update(json.loads(req.content))
        return httpx.Response(200, json={"symbol": "FPT", "overall_sentiment": "neutral", "sentiment_score": 0.0})

    _clf(handler).classify(_item(title="Hello world"))
    assert seen["symbol"] == "FPT"
    assert seen["news_items"][0]["title"] == "Hello world"


# ---------------------------------------------------------------------------
# Backlog #112(d) — the classifier carries the score's provenance through.
# ---------------------------------------------------------------------------

def test_classification_carries_the_score_source_from_ai_insights():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={
            "symbol": "FPT", "overall_sentiment": "bearish",
            "sentiment_score": -0.35, "category": "regulatory",
            "score_source": "model",
        })

    client = httpx.Client(transport=httpx.MockTransport(handler))
    c = NewsClassifier("http://ai", client=client).classify(_item())
    assert c.sentiment == "bad"
    assert c.score == -0.35
    assert c.score_source == "model"


def test_a_missing_score_source_is_unknown_not_assumed_to_be_a_model():
    """An older ai-insights omits the field. Defaulting it to 'model' would
    assert a provenance we have no evidence for — the exact over-claim the
    provenance field exists to prevent."""
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={
            "symbol": "FPT", "overall_sentiment": "neutral", "sentiment_score": 0.0,
        })

    client = httpx.Client(transport=httpx.MockTransport(handler))
    c = NewsClassifier("http://ai", client=client).classify(_item())
    assert c.score_source == "unknown"
