"""N4 — company-news source adapter (FR-NEWS-COMPANY, EC-N1/N3/N6).

Calls stock-data-service GET /companies/{symbol}/news (which wraps vnstock — no vnstock
import here, EC-N1) and normalizes each record to a NewsItem: tz-aware UTC ts_utc (EC-N6),
raw_json preserved verbatim (EC-N3).
"""
from __future__ import annotations

import json

import httpx
import pytest

from app.exceptions import SourceUnavailableError
from app.ingest.company_source import CompanyNewsSource

_BASE = "http://stock-data-service:8001"


def _source(handler) -> CompanyNewsSource:
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return CompanyNewsSource(_BASE, client=client)


def _rec(**over) -> dict:
    base = {
        "symbol": "FPT",
        "title": "FPT ra mắt sản phẩm AI mới",
        "description": "Tóm tắt ngắn",
        "content": "Nội dung đầy đủ về sản phẩm AI.",
        "source": "https://cafef.vn/fpt-ai.html",  # vnstock 'source' == article link
        "publishDate": "2026-07-01T09:00:00",       # naive -> must be coerced to UTC
        "id": "fpt-news-42",
    }
    base.update(over)
    return base


def test_normalizes_record_to_news_item():
    def handler(req):
        assert req.url.path.endswith("/companies/FPT/news")
        return httpx.Response(200, json=[_rec()])

    items = _source(handler).fetch("fpt")
    assert len(items) == 1
    it = items[0]
    assert it.source == "vnstock"
    assert it.stream == "company"
    assert it.symbol == "FPT"                 # uppercased
    assert it.title == "FPT ra mắt sản phẩm AI mới"
    assert it.body == "Nội dung đầy đủ về sản phẩm AI."  # prefers full content
    assert it.url == "https://cafef.vn/fpt-ai.html"
    assert it.guid == "fpt-news-42"


def test_ts_is_tz_aware_utc_even_when_source_is_naive():
    def handler(req):
        return httpx.Response(200, json=[_rec()])

    it = _source(handler).fetch("FPT")[0]
    assert it.ts_utc.utcoffset() is not None      # tz-aware (EC-N6), not stored naive
    assert it.ts_utc.tzinfo is not None


def test_raw_json_preserved_verbatim():
    rec = _rec()

    def handler(req):
        return httpx.Response(200, json=[rec])

    it = _source(handler).fetch("FPT")[0]
    assert json.loads(it.raw_json) == rec         # EC-N3: full source payload kept


def test_body_falls_back_to_description_when_no_content():
    def handler(req):
        return httpx.Response(200, json=[_rec(content=None)])

    it = _source(handler).fetch("FPT")[0]
    assert it.body == "Tóm tắt ngắn"


def test_non_200_raises_source_unavailable():
    def handler(req):
        return httpx.Response(503)

    with pytest.raises(SourceUnavailableError):
        _source(handler).fetch("FPT")


def test_non_list_payload_raises_source_unavailable():
    def handler(req):
        return httpx.Response(200, json={"error": "boom"})

    with pytest.raises(SourceUnavailableError):
        _source(handler).fetch("FPT")


def test_network_error_raises_source_unavailable():
    def handler(req):
        raise httpx.ConnectError("down")

    with pytest.raises(SourceUnavailableError):
        _source(handler).fetch("FPT")


def test_empty_list_is_normal_no_news_returns_empty():
    def handler(req):
        return httpx.Response(200, json=[])

    assert _source(handler).fetch("FPT") == []   # no news != source failure


def test_records_missing_title_or_date_are_skipped_not_fatal():
    def handler(req):
        return httpx.Response(200, json=[
            _rec(),                       # good
            _rec(title=None, id="a"),     # no title -> skip
            _rec(publishDate=None, createdAt=None, id="b"),  # no date -> skip
        ])

    items = _source(handler).fetch("FPT")
    assert len(items) == 1
    assert items[0].guid == "fpt-news-42"
