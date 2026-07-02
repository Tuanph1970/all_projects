"""N12 — macro poller (FR-NEWS-MACRO, EC-N2/N7). Store + tag; no notify (Stream A)."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.ingest.macro_feeds import TaggedItem
from app.models.news_item import NewsItem
from app.services.macro_poller import MacroPoller


class FakeMacroSource:
    def __init__(self, tagged, raise_exc=None):
        self._tagged = tagged
        self._raise = raise_exc

    def fetch_all(self):
        if self._raise:
            raise self._raise
        return list(self._tagged)


def _tagged(guid, title, category) -> TaggedItem:
    item = NewsItem(
        source="fed_rss", stream="macro", symbol=None,
        ts_utc=datetime(2026, 7, 1, 9, 0, tzinfo=timezone.utc),
        title=title, body="b", url=f"https://x/{guid}", lang=None,
        raw_json="{}", guid=guid,
    )
    return TaggedItem(item, category)


@pytest.mark.asyncio
async def test_stores_and_tags_macro_items(news_repo):
    src = FakeMacroSource([
        _tagged("m1", "Fed raises rates", "monetary"),
        _tagged("m2", "New tariffs", "tariff"),
    ])
    stats = await MacroPoller(macro_source=src, repo=news_repo).tick()

    rows = news_repo.query(stream="macro")
    assert len(rows) == 2
    cats = {r.symbol: r for r in rows}  # noqa - just to touch
    by_id = {r.news_id: r for r in rows}
    # category persisted, sentiment stays None, classified_at set (so it is not re-processed)
    for r in rows:
        assert r.category in ("monetary", "tariff")
        assert r.sentiment is None
        assert r.classified_at is not None
    assert stats["new"] == 2 and stats["tagged"] == 2


@pytest.mark.asyncio
async def test_macro_items_excluded_from_company_classification(news_repo):
    src = FakeMacroSource([_tagged("m1", "Fed raises rates", "monetary")])
    await MacroPoller(macro_source=src, repo=news_repo).tick()
    # Company Phase B pulls list_new(stream="company"); macro rows must never appear there.
    assert news_repo.list_new(stream="company") == []


@pytest.mark.asyncio
async def test_rerun_is_idempotent(news_repo):
    src = FakeMacroSource([_tagged("m1", "Fed raises rates", "monetary")])
    poller = MacroPoller(macro_source=src, repo=news_repo)
    s1 = await poller.tick()
    s2 = await poller.tick()
    assert s1["new"] == 1 and s2["new"] == 0
    assert len(news_repo.query(stream="macro")) == 1


@pytest.mark.asyncio
async def test_source_failure_does_not_crash(news_repo):
    src = FakeMacroSource([], raise_exc=RuntimeError("feeds down"))
    stats = await MacroPoller(macro_source=src, repo=news_repo).tick()
    assert stats["errors"] >= 1
    assert news_repo.query(stream="macro") == []
