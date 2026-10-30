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


# ---------------------------------------------------------------------------
# Backlog #112(d) — provenance for sentiment_score.
#
# Before this, a row scored while no LLM was reachable was indistinguishable
# from a real neutral judgement: both stored +0.5 and nothing recorded which.
# A corpus mixing judgements with constants cannot be audited after the fact,
# which is exactly why #108 could not say how many of the 165 stored neutrals
# had ever been judged at all. See docs/backlog108_news_sentiment_validation.md.
# ---------------------------------------------------------------------------

def test_mark_classified_persists_the_score_provenance(news_repo):
    item = _item(guid="prov-1")
    news_repo.upsert(item)
    news_repo.mark_classified(
        item.news_id(), sentiment="bad", category="regulatory",
        score=-0.35, score_source="model",
    )
    after = news_repo.get(item.news_id())
    assert after.sentiment_score == -0.35
    assert after.score_source == "model"


def test_a_template_scored_row_is_distinguishable_from_a_real_neutral(news_repo):
    """The whole point of the field: these two rows carry the same score and
    must not look the same."""
    judged = _item(guid="judged")
    fallback = _item(guid="fallback")
    news_repo.upsert(judged)
    news_repo.upsert(fallback)
    news_repo.mark_classified(judged.news_id(), sentiment="neutral",
                              category="other", score=0.0, score_source="model")
    news_repo.mark_classified(fallback.news_id(), sentiment="neutral",
                              category="other", score=0.0, score_source="template")
    a = news_repo.get(judged.news_id())
    b = news_repo.get(fallback.news_id())
    assert a.sentiment_score == b.sentiment_score == 0.0
    assert a.score_source != b.score_source


def test_ensure_schema_adds_the_column_to_a_pre_existing_table(tmp_path):
    """The live table predates the column and holds rows, and create_all() does
    not ALTER. Without an explicit migration the field would exist in the model
    and never in the database — failing only at runtime, on the real deploy."""
    import sqlalchemy as sa
    from app.repositories.news_repository import NewsRepository

    db = tmp_path / "legacy.db"
    engine = sa.create_engine(f"sqlite:///{db}")
    # A table shaped like the deployed one: no score_source.
    with engine.begin() as conn:
        conn.execute(sa.text(
            "CREATE TABLE news_events ("
            " news_id VARCHAR(64) PRIMARY KEY, source VARCHAR(64) NOT NULL,"
            " stream VARCHAR(16) NOT NULL, symbol VARCHAR(20), ts_utc DATETIME NOT NULL,"
            " title TEXT NOT NULL, body TEXT, url VARCHAR(1024), lang VARCHAR(8),"
            " raw_json TEXT, category VARCHAR(32), sentiment VARCHAR(8),"
            " sentiment_score FLOAT, ingested_at DATETIME NOT NULL,"
            " classified_at DATETIME, notified_at DATETIME, bridged_at DATETIME)"
        ))
        conn.execute(sa.text(
            "INSERT INTO news_events (news_id, source, stream, ts_utc, title,"
            " sentiment, sentiment_score, ingested_at)"
            " VALUES ('old1','vnstock','company','2026-09-01','legacy row',"
            " 'neutral', 0.5, '2026-09-01')"
        ))

    cols = lambda: {r[1] for r in engine.connect().execute(sa.text("PRAGMA table_info(news_events)"))}
    assert "score_source" not in cols()

    NewsRepository(engine).ensure_schema()
    assert "score_source" in cols()

    # Idempotent: a second deploy must not fail on an already-added column.
    NewsRepository(engine).ensure_schema()
    assert "score_source" in cols()

    # And the legacy row survives, with the field null rather than invented —
    # we do not know how it was scored, and saying "model" would be a lie.
    with engine.connect() as conn:
        row = conn.execute(sa.text(
            "SELECT sentiment_score, score_source FROM news_events WHERE news_id='old1'"
        )).one()
    assert row[0] == 0.5
    assert row[1] is None


# ---------------------------------------------------------------------------
# Backlog #106 — feature_points
# ---------------------------------------------------------------------------

def test_feature_points_returns_oldest_first_within_the_window(news_repo):
    from datetime import datetime, timezone
    for day in (3, 1, 2):
        it = _item(guid=f"fp-{day}", ts_utc=datetime(2026, 9, day, 2, 0, tzinfo=timezone.utc))
        news_repo.upsert(it)
        news_repo.mark_classified(it.news_id(), sentiment="good", category="earnings",
                                  score=0.1 * day, score_source="model")
    pts = news_repo.feature_points(
        symbol="FPT",
        since=datetime(2026, 9, 1, tzinfo=timezone.utc),
        until=datetime(2026, 9, 30, tzinfo=timezone.utc),
    )
    assert [p[0].day for p in pts] == [1, 2, 3], "the decay needs oldest-first"
    assert [p[2] for p in pts] == ["model"] * 3


def test_feature_points_is_not_capped_like_the_read_api(news_repo):
    """query() caps at `limit` and orders newest-first, so building the series on
    it would drop the oldest part of the window — the half the decay needs."""
    from datetime import datetime, timedelta, timezone
    base = datetime(2026, 9, 1, 2, 0, tzinfo=timezone.utc)
    for n in range(150):
        it = _item(guid=f"many-{n}", ts_utc=base + timedelta(hours=n))
        news_repo.upsert(it)
    pts = news_repo.feature_points(symbol="FPT", since=base,
                                   until=base + timedelta(days=30))
    assert len(pts) == 150
    assert len(news_repo.query(symbol="FPT")) <= 100   # the read API's cap


def test_feature_points_excludes_other_symbols(news_repo):
    from datetime import datetime, timezone
    ts = datetime(2026, 9, 2, 2, 0, tzinfo=timezone.utc)
    news_repo.upsert(_item(guid="s-acb", symbol="ACB", ts_utc=ts))
    news_repo.upsert(_item(guid="s-fpt", symbol="FPT", ts_utc=ts))
    assert len(news_repo.feature_points(
        symbol="ACB", since=datetime(2026, 9, 1, tzinfo=timezone.utc),
        until=datetime(2026, 9, 30, tzinfo=timezone.utc))) == 1
