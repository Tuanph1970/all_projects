"""Backlog #113 — the pre-#112 corpus re-score.

What these protect, in order of how badly each would hurt:
  * no notification and no change to notified_at — a naive re-score would
    send the owner a burst of alerts about September news;
  * a 'template' answer (no LLM reachable) is NOT written: it would take the
    row out of the retry set for good while still holding no judgement;
  * an upstream that predates #112 stops the run before spending calls;
  * only pre-#112 company rows are touched; already-sourced rows, unclassified
    rows and macro rows are left alone, so a re-run resumes rather than repeats;
  * the dry run makes no classifier calls at all.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.exceptions import ClassificationError
from app.ingest.classifier import Classification
from app.models.domain import NewsEvent
from app.models.news_item import NewsItem
from app.services import rescore as rescore_mod
from app.services.rescore import UpstreamTooOld, rescore


def _seed(repo, n, *, title="FPT báo lãi quý 3", stream="company", symbol="FPT",
          sentiment="neutral", score=0.5, score_source=None, notified=False, classified=True):
    """Insert rows as the pre-#112 pipeline left them; return their news_ids."""
    ids = []
    for i in range(n):
        item = NewsItem(
            source="vnstock", stream=stream, symbol=symbol,
            ts_utc=datetime(2026, 9, 10 + i, 2, 0, tzinfo=timezone.utc),
            title=f"{title} #{i}", body="body", url=f"https://x/{stream}/{title}/{i}",
            lang="vi", raw_json="{}", guid=None,
        )
        repo.upsert(item)
        nid = item.news_id()
        if classified:
            repo.mark_classified(nid, sentiment=sentiment, category="other",
                                 score=score, score_source=score_source)
        if notified:
            repo.mark_notified(nid)
        ids.append(nid)
    return ids


def _get(repo, nid) -> NewsEvent:
    with repo._Session() as s:
        return s.get(NewsEvent, nid)


class FakeClassifier:
    def __init__(self, answers):
        self._answers = list(answers)
        self.calls = 0

    def classify(self, row):
        self.calls += 1
        a = self._answers.pop(0) if len(self._answers) > 1 else self._answers[0]
        if isinstance(a, Exception):
            raise a
        return a


GOOD = Classification(sentiment="good", category="earnings", score=0.45, score_source="model")
NEUTRAL = Classification(sentiment="neutral", category="other", score=0.0, score_source="model")
TEMPLATE = Classification(sentiment="neutral", category="other", score=0.0, score_source="template")
UNKNOWN = Classification(sentiment="neutral", category="other", score=0.0, score_source="unknown")


def test_dry_run_counts_and_makes_no_calls(news_repo):
    _seed(news_repo, 3)
    clf = FakeClassifier([GOOD])
    stats = rescore(news_repo, clf)
    assert stats.candidates == 3
    assert clf.calls == 0
    assert news_repo.list_unsourced_scored() != []


def test_apply_rewrites_the_score_and_records_provenance(news_repo):
    [nid] = _seed(news_repo, 1)
    stats = rescore(news_repo, FakeClassifier([GOOD]), apply=True)
    row = _get(news_repo, nid)
    assert (row.sentiment, row.sentiment_score, row.score_source, row.category) == \
        ("good", 0.45, "model", "earnings")
    assert stats.rescored == 1 and stats.changed_label == 1
    assert stats.audit_rows[0]["old_score"] == 0.5
    assert stats.audit_rows[0]["new_score"] == 0.45


def test_never_notifies_and_never_touches_notified_at(news_repo):
    """The trap #113 calls out: a re-score must not re-emit alerts."""
    never, already = _seed(news_repo, 1, title="a")[0], _seed(news_repo, 1, title="b", notified=True)[0]
    before = _get(news_repo, already).notified_at
    rescore(news_repo, FakeClassifier([GOOD]), apply=True)  # 'good' is a notify sentiment
    assert _get(news_repo, never).notified_at is None
    assert _get(news_repo, already).notified_at == before


def test_template_answer_is_deferred_not_stored(news_repo):
    [nid] = _seed(news_repo, 1)
    stats = rescore(news_repo, FakeClassifier([TEMPLATE]), apply=True)
    row = _get(news_repo, nid)
    assert stats.deferred == 1 and stats.rescored == 0
    assert row.score_source is None and row.sentiment_score == 0.5
    assert [r.news_id for r in news_repo.list_unsourced_scored()] == [nid]  # still retryable


def test_classifier_failure_is_deferred_and_the_run_continues(news_repo):
    ids = _seed(news_repo, 2)
    stats = rescore(news_repo, FakeClassifier([ClassificationError("timeout"), GOOD]), apply=True)
    assert (stats.deferred, stats.rescored) == (1, 1)
    assert _get(news_repo, ids[0]).score_source is None
    assert _get(news_repo, ids[1]).score_source == "model"


def test_an_upstream_without_provenance_stops_before_writing(news_repo):
    ids = _seed(news_repo, 3)
    clf = FakeClassifier([UNKNOWN])
    with pytest.raises(UpstreamTooOld):
        rescore(news_repo, clf, apply=True)
    assert clf.calls == 1
    assert all(_get(news_repo, i).score_source is None for i in ids)


def test_only_pre_112_company_rows_are_candidates(news_repo):
    stale = _seed(news_repo, 1, title="stale")
    _seed(news_repo, 1, title="fresh", score_source="model", score=0.2)
    _seed(news_repo, 1, title="unclassified", classified=False)
    _seed(news_repo, 1, title="macro", stream="macro", symbol=None)
    assert [r.news_id for r in news_repo.list_unsourced_scored()] == stale


def test_rerun_resumes_and_skips_rows_already_done(news_repo):
    _seed(news_repo, 4)
    first = rescore(news_repo, FakeClassifier([NEUTRAL]), apply=True, limit=2)
    clf = FakeClassifier([NEUTRAL])
    second = rescore(news_repo, clf, apply=True)
    assert (first.rescored, second.candidates, clf.calls) == (2, 2, 2)
    assert news_repo.list_unsourced_scored() == []


def test_pauses_between_calls_not_before_the_first(news_repo):
    _seed(news_repo, 3)
    slept = []
    rescore(news_repo, FakeClassifier([NEUTRAL]), apply=True, pause_seconds=0.5, sleep=slept.append)
    assert slept == [0.5, 0.5]


def test_cli_dry_run_prints_the_count(news_repo, monkeypatch, capsys):
    _seed(news_repo, 2)
    monkeypatch.setattr("app.repositories.news_repository.NewsRepository", lambda engine: news_repo)
    clf = FakeClassifier([GOOD])
    monkeypatch.setattr("app.ingest.classifier.NewsClassifier", lambda *a, **k: clf)
    assert rescore_mod.main([]) == 0
    assert clf.calls == 0
    assert "2 rows scored before #112" in capsys.readouterr().out
