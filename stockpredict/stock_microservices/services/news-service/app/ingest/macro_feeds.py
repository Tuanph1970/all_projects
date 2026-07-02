"""ingest/ MacroFeedSource — Stream A macro/global events from feeds/APIs (FR-NEWS-MACRO).

Registry-driven readers for RSS/Atom (feedparser) and JSON APIs. Feeds/APIs only — never
HTML scraping (EC-N1). Each source is a dict:
    {name, kind: "rss"|"json", url, category_hint?, bridge?, map?}
`map` (json only) overrides field names: {title, body, url, date, id}.

Produces (NewsItem, category) pairs — NewsItem stays category-free (company category comes
from the classifier), so macro tagging is carried alongside. Timestamps are tz-aware UTC
(EC-N6); the raw source payload is preserved (EC-N3). Per-source failures are logged and
skipped so one bad feed never aborts the sweep (EC-N7).
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import NamedTuple, Optional

import feedparser
import httpx

from app.exceptions import SourceUnavailableError
from app.ingest.company_source import _parse_ts  # shared tz-aware UTC coercion
from app.models.news_item import NewsItem

logger = logging.getLogger(__name__)


class TaggedItem(NamedTuple):
    item: NewsItem
    category: str


MACRO_CATEGORIES = ("monetary", "tariff", "tax", "trade", "geopolitical", "war", "other")

# First match wins. Lowercased substring scan over title+body.
_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("tariff", ("tariff",)),
    ("tax", ("tax",)),
    ("monetary", ("interest rate", "rate hike", "rate cut", "fomc", "central bank",
                  "monetary", "inflation", "cpi", "federal reserve", "the fed")),
    ("war", ("war", "invasion", "missile", "airstrike", "troops", "conflict")),
    ("geopolitical", ("sanction", "election", "coup", "diplomat", "geopolit", "border dispute")),
    ("trade", ("trade", "export", "import", "wto", "embargo")),
]

# Convenience defaults (structured, public feeds). Not polled unless ENABLE_MACRO is on.
DEFAULT_SOURCES: list[dict] = [
    {"name": "fed_press", "kind": "rss",
     "url": "https://www.federalreserve.gov/feeds/press_all.xml", "category_hint": "monetary"},
    {"name": "treasury_press", "kind": "rss",
     "url": "https://home.treasury.gov/rss/press.xml", "category_hint": "tax"},
]


def tag_category(text: str, hint: Optional[str] = None) -> str:
    low = (text or "").lower()
    for category, keywords in _RULES:
        if any(k in low for k in keywords):
            return category
    if hint in MACRO_CATEGORIES:
        return hint
    return "other"


class MacroFeedSource:
    def __init__(self, sources: list[dict], *, client: Optional[httpx.Client] = None,
                 timeout: float = 10.0):
        self._sources = sources
        self._client = client
        self._timeout = timeout

    def fetch_all(self) -> list[TaggedItem]:
        out: list[TaggedItem] = []
        for src in self._sources:
            try:
                out.extend(self._fetch_source(src))
            except Exception as exc:  # noqa: BLE001 — log-and-continue (EC-N7)
                logger.warning("macro source %s failed: %s", src.get("name"), exc)
        return out

    def _fetch_source(self, src: dict) -> list[TaggedItem]:
        text = self._get(src["url"])
        kind = src.get("kind", "rss")
        if kind == "rss":
            return self._parse_rss(src, text)
        if kind == "json":
            return self._parse_json(src, json.loads(text))
        logger.warning("unknown macro source kind %r for %s", kind, src.get("name"))
        return []

    def _get(self, url: str) -> str:
        client = self._client or httpx.Client(timeout=self._timeout)
        try:
            resp = client.get(url)
        finally:
            if self._client is None:
                client.close()
        if resp.status_code != 200:
            raise SourceUnavailableError(f"{url} returned {resp.status_code}")
        return resp.text

    def _parse_rss(self, src: dict, text: str) -> list[TaggedItem]:
        feed = feedparser.parse(text)
        out: list[TaggedItem] = []
        for e in feed.entries:
            title = (e.get("title") or "").strip()
            ts = _rss_ts(e)
            if not title or ts is None:
                continue
            body = e.get("summary") or e.get("description")
            url = e.get("link")
            out.append(self._make(src, title, body, url, ts,
                                   e.get("id") or e.get("guid") or url,
                                   json.dumps(dict(e), default=str, ensure_ascii=False)))
        return out

    def _parse_json(self, src: dict, data) -> list[TaggedItem]:
        m = src.get("map", {})
        tkey, bkey = m.get("title", "title"), m.get("body", "summary")
        ukey, dkey, ikey = m.get("url", "url"), m.get("date", "published"), m.get("id", "id")
        rows = data if isinstance(data, list) else (data.get("items") or data.get("data") or [])
        out: list[TaggedItem] = []
        for it in rows:
            if not isinstance(it, dict):
                continue
            title = (it.get(tkey) or "").strip()
            ts = _parse_ts(it.get(dkey))
            if not title or ts is None:
                continue
            body = it.get(bkey) or it.get("description")
            out.append(self._make(src, title, body, it.get(ukey), ts,
                                   it.get(ikey) or it.get(ukey),
                                   json.dumps(it, default=str, ensure_ascii=False)))
        return out

    def _make(self, src, title, body, url, ts, guid, raw_json) -> TaggedItem:
        item = NewsItem(
            source=src["name"], stream="macro", symbol=None, ts_utc=ts,
            title=title, body=body, url=url, lang=None, raw_json=raw_json, guid=guid,
        )
        return TaggedItem(item, tag_category(f"{title} {body or ''}", src.get("category_hint")))


def _rss_ts(entry) -> Optional[datetime]:
    pp = entry.get("published_parsed") or entry.get("updated_parsed")
    if pp:
        return datetime(*pp[:6], tzinfo=timezone.utc)  # feedparser *_parsed are UTC
    return _parse_ts(entry.get("published") or entry.get("updated"))
