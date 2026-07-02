"""N6 — company poller + notifier + scheduler (FR-NEWS-COMPANY / FR-NEWS-NOTIFY / FR-NEWS-SCHED).

Mandatory gates (SRS §5.2, EC-N2/N7/N8):
  - good/bad emits exactly one news.company event; neutral emits none (EC-N8)
  - re-running the tick over identical news emits zero new events (EC-N2 idempotency)
  - a classifier/source failure on one symbol does not crash the tick (EC-N7)
Fakes stand in for all I/O — no HTTP, no RabbitMQ.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import pytest

from app.exceptions import ClassificationError, SourceUnavailableError
from app.ingest.classifier import Classification
from app.models.news_item import NewsItem
from app.services.company_poller import CompanyPoller
from app.services.scheduler import PollerScheduler


# ---------------- fakes ----------------
class FakeWatch:
    def __init__(self, symbols):
        self._symbols = symbols

    def resolve(self):
        return list(self._symbols)


class FakeCompanySource:
    """Maps symbol -> list[NewsItem]; a symbol in `fail` raises SourceUnavailableError."""

    def __init__(self, by_symbol, fail=()):
        self._by = by_symbol
        self._fail = set(fail)

    def fetch(self, symbol):
        if symbol in self._fail:
            raise SourceUnavailableError(f"{symbol} down")
        return list(self._by.get(symbol, []))


class FakeClassifier:
    """Returns a preset Classification per symbol; a symbol in `fail` raises."""

    def __init__(self, by_symbol, fail=()):
        self._by = by_symbol
        self._fail = set(fail)

    def classify(self, item):
        if item.symbol in self._fail:
            raise ClassificationError(f"{item.symbol} classify failed")
        return self._by[item.symbol]


class FakeNotifier:
    def __init__(self):
        self.emitted = []

    async def emit_news_company(self, **payload):
        self.emitted.append(payload)


def _item(symbol, title, guid) -> NewsItem:
    return NewsItem(
        source="vnstock", stream="company", symbol=symbol,
        ts_utc=datetime(2026, 7, 1, 9, 0, tzinfo=timezone.utc),
        title=title, body="body", url=f"https://x/{guid}", lang="vi",
        raw_json="{}", guid=guid,
    )


def _poller(news_repo, watch, source, classifier, notifier):
    return CompanyPoller(
        watch_source=watch, company_source=source, classifier=classifier,
        repo=news_repo, notifier=notifier, notify_sentiments=("good", "bad"),
    )


# ---------------- tests ----------------
@pytest.mark.asyncio
async def test_good_emits_one_neutral_emits_none(news_repo):
    watch = FakeWatch(["ACB", "FPT"])
    source = FakeCompanySource({
        "ACB": [_item("ACB", "ACB great news", "acb1")],
        "FPT": [_item("FPT", "FPT so-so", "fpt1")],
    })
    classifier = FakeClassifier({
        "ACB": Classification("good", "new_product", 0.8),
        "FPT": Classification("neutral", "other", 0.0),
    })
    notifier = FakeNotifier()
    stats = await _poller(news_repo, watch, source, classifier, notifier).tick()

    # both stored + classified
    assert len(news_repo.query()) == 2
    assert news_repo.list_new() == []           # all classified
    # exactly one emit, for the good ACB item (EC-N8)
    assert len(notifier.emitted) == 1
    assert notifier.emitted[0]["symbol"] == "ACB"
    assert notifier.emitted[0]["sentiment"] == "good"
    assert stats["new"] == 2 and stats["notified"] == 1


@pytest.mark.asyncio
async def test_rerun_tick_is_idempotent(news_repo):
    watch = FakeWatch(["ACB"])
    source = FakeCompanySource({"ACB": [_item("ACB", "ACB great news", "acb1")]})
    classifier = FakeClassifier({"ACB": Classification("good", "new_product", 0.9)})
    notifier = FakeNotifier()
    poller = _poller(news_repo, watch, source, classifier, notifier)

    s1 = await poller.tick()
    s2 = await poller.tick()

    assert len(news_repo.query()) == 1          # no duplicate row (EC-N2)
    assert len(notifier.emitted) == 1           # no re-emit
    assert s1["new"] == 1 and s2["new"] == 0
    assert s2["notified"] == 0


@pytest.mark.asyncio
async def test_notify_payload_shape_has_no_user(news_repo):
    watch = FakeWatch(["FPT"])
    source = FakeCompanySource({"FPT": [_item("FPT", "FPT launches product", "fpt1")]})
    classifier = FakeClassifier({"FPT": Classification("bad", "regulatory", -0.6)})
    notifier = FakeNotifier()
    await _poller(news_repo, watch, source, classifier, notifier).tick()

    p = notifier.emitted[0]
    assert set(p) == {"news_id", "symbol", "sentiment", "category", "title", "url",
                      "ts_utc", "sentiment_score"}
    assert "user" not in p and "user_id" not in p          # EC-N10
    assert p["sentiment"] == "bad" and p["category"] == "regulatory"
    assert p["sentiment_score"] == -0.6


@pytest.mark.asyncio
async def test_classifier_failure_on_one_symbol_does_not_crash(news_repo):
    watch = FakeWatch(["ACB", "FPT"])
    source = FakeCompanySource({
        "ACB": [_item("ACB", "ACB good", "acb1")],
        "FPT": [_item("FPT", "FPT news", "fpt1")],
    })
    classifier = FakeClassifier({"ACB": Classification("good", "other", 0.5)}, fail=["FPT"])
    notifier = FakeNotifier()
    stats = await _poller(news_repo, watch, source, classifier, notifier).tick()

    # both raw rows stored (Phase A runs regardless of classifier)
    assert len(news_repo.query()) == 2
    # ACB classified + notified; FPT left unclassified for retry
    assert len(notifier.emitted) == 1 and notifier.emitted[0]["symbol"] == "ACB"
    unclassified = {r.symbol for r in news_repo.list_new()}
    assert unclassified == {"FPT"}
    assert stats["errors"] >= 1


@pytest.mark.asyncio
async def test_unclassified_item_is_retried_next_tick(news_repo):
    watch = FakeWatch(["FPT"])
    source = FakeCompanySource({"FPT": [_item("FPT", "FPT news", "fpt1")]})
    notifier = FakeNotifier()

    # Tick 1: classifier down -> stored unclassified, no emit.
    failing = FakeClassifier({}, fail=["FPT"])
    await _poller(news_repo, watch, source, failing, notifier).tick()
    assert len(news_repo.list_new()) == 1 and notifier.emitted == []

    # Tick 2: classifier recovers -> classified + notified, no re-fetch dup.
    ok = FakeClassifier({"FPT": Classification("good", "new_tech", 0.7)})
    await _poller(news_repo, watch, source, ok, notifier).tick()
    assert news_repo.list_new() == []
    assert len(notifier.emitted) == 1
    assert len(news_repo.query()) == 1


@pytest.mark.asyncio
async def test_source_failure_on_one_symbol_does_not_crash(news_repo):
    watch = FakeWatch(["ACB", "FPT"])
    source = FakeCompanySource({"FPT": [_item("FPT", "FPT news", "fpt1")]}, fail=["ACB"])
    classifier = FakeClassifier({"FPT": Classification("good", "other", 0.3)})
    notifier = FakeNotifier()
    stats = await _poller(news_repo, watch, source, classifier, notifier).tick()

    assert len(news_repo.query()) == 1          # only FPT stored
    assert stats["errors"] >= 1
    assert len(notifier.emitted) == 1


@pytest.mark.asyncio
async def test_scheduler_runs_tick_then_stops():
    class CountingPoller:
        def __init__(self):
            self.ticks = 0

        async def tick(self):
            self.ticks += 1

    poller = CountingPoller()
    sched = PollerScheduler(poller, interval_seconds=0.01, name="test")
    sched.start()
    await asyncio.sleep(0.05)
    await sched.stop()
    assert poller.ticks >= 1
