"""N2 — news_events store: dedup (news_id) + immutable raw corpus (offline sqlite).

Mandatory gates (SRS §5.1, EC-N2/EC-N3):
  - same source entry -> same news_id across runs (pure, NFR-N2)
  - a second upsert of an already-seen news_id is a no-op (no dup, no re-classify)
  - raw title/body/raw_json are byte-identical after mark_classified (immutability)
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.models.news_item import NewsItem


def _item(**over) -> NewsItem:
    base = dict(
        source="vnstock",
        stream="company",
        symbol="FPT",
        ts_utc=datetime(2026, 7, 2, 2, 15, tzinfo=timezone.utc),
        title="FPT launches new AI product",
        body="FPT announced a new AI platform today.",
        url="https://example.com/fpt-ai",
        lang="en",
        raw_json='{"k": "v"}',
        guid="fpt-guid-1",
    )
    base.update(over)
    return NewsItem(**base)


def test_news_id_is_deterministic_and_pure():
    # Same source fields -> same id, every time (no clock/random — NFR-N2).
    assert _item().news_id() == _item().news_id()
    # 64-hex, fits String(64).
    nid = _item().news_id()
    assert len(nid) == 64 and all(c in "0123456789abcdef" for c in nid)


def test_news_id_prefers_guid_then_url_then_composite():
    with_guid = _item(guid="g", url="u").news_id()
    without_guid = _item(guid=None, url="u").news_id()
    without_guid_url = _item(guid=None, url=None).news_id()
    assert with_guid != without_guid          # guid drives the id when present
    assert without_guid != without_guid_url    # url drives it next


def test_same_title_different_source_gives_different_ids():
    a = _item(source="vnstock", guid=None, url=None).news_id()
    b = _item(source="reuters_rss", guid=None, url=None).news_id()
    assert a != b


def test_upsert_new_returns_true_then_dedup_noop(news_repo):
    item = _item()
    assert news_repo.upsert(item) is True          # newly inserted
    assert news_repo.upsert(item) is False         # already seen -> no-op (EC-N2)
    assert news_repo.exists(item.news_id()) is True
    # exactly one row
    assert len(news_repo.query(symbol="FPT")) == 1


def test_reupsert_does_not_mutate_raw_or_classification(news_repo):
    item = _item()
    news_repo.upsert(item)
    news_repo.mark_classified(item.news_id(), sentiment="good", category="new_product", score=0.7)
    # A re-poll delivering a mutated payload must NOT overwrite the stored raw/class.
    mutated = _item(title="TAMPERED", body="TAMPERED", raw_json='{"x":1}')
    assert news_repo.upsert(mutated) is False
    row = news_repo.get(item.news_id())
    assert row.title == "FPT launches new AI product"
    assert row.body == "FPT announced a new AI platform today."
    assert row.raw_json == '{"k": "v"}'
    assert row.sentiment == "good"


def test_mark_classified_leaves_raw_immutable(news_repo):
    item = _item()
    news_repo.upsert(item)
    before = news_repo.get(item.news_id())
    raw_before = (before.title, before.body, before.raw_json)
    news_repo.mark_classified(item.news_id(), sentiment="bad", category="regulatory", score=-0.4)
    after = news_repo.get(item.news_id())
    assert (after.title, after.body, after.raw_json) == raw_before  # EC-N3
    assert after.sentiment == "bad"
    assert after.category == "regulatory"
    assert after.sentiment_score == -0.4
    assert after.classified_at is not None


def test_list_new_returns_only_unclassified(news_repo):
    a = _item(guid="a", symbol="ACB")
    b = _item(guid="b", symbol="FPT")
    news_repo.upsert(a)
    news_repo.upsert(b)
    news_repo.mark_classified(a.news_id(), sentiment="neutral", category="other", score=0.0)
    new_ids = {r.news_id for r in news_repo.list_new()}
    assert b.news_id() in new_ids
    assert a.news_id() not in new_ids


def test_mark_notified_and_bridged(news_repo):
    item = _item()
    news_repo.upsert(item)
    news_repo.mark_notified(item.news_id())
    news_repo.mark_bridged(item.news_id())
    row = news_repo.get(item.news_id())
    assert row.notified_at is not None
    assert row.bridged_at is not None


def test_ensure_database_is_noop_for_sqlite(news_repo):
    # No separate CREATE DATABASE step for sqlite; ensure_schema must stay a no-op there
    # (the MySQL auto-create path is exercised in the live deploy check, not unit tests).
    news_repo._ensure_database()   # must not raise
    news_repo.ensure_schema()      # idempotent re-run
    assert news_repo.query() == []


def test_ts_utc_roundtrips_tz_aware(news_repo):
    item = _item()
    news_repo.upsert(item)
    row = news_repo.get(item.news_id())
    assert row.ts_utc.utcoffset() is not None  # tz-aware (EC-N6)
