"""API + repository tests for the pasted-TCBS-mail endpoints (FR-BM-API, FR-BM-DEDUP).

The watchlist push is exercised against a stubbed pusher — these tests must not need
portfolio-service running, and a push failure must never cost us the stored email.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from app.deps import container, get_tcb_repo, get_watchlist_pusher
from app.main import app
from app.repositories.tcb_repository import TcbRepository, content_hash
from app.services.watchlist_push import PushResult

FIXTURES = Path(__file__).parent / "fixtures"
PREFIX = "/stock_helper/api/v2/news"


def _load(n: int) -> str:
    return (FIXTURES / f"tcb_mail_{n}.txt").read_text(encoding="utf-8")


class StubPusher:
    """Records what would have been sent to portfolio-service."""

    def __init__(self, ok: bool = True):
        self.ok = ok
        self.calls: list[dict] = []

    def push(self, **kwargs) -> PushResult:
        self.calls.append(kwargs)
        return PushResult(symbol=kwargs["symbol"], ok=self.ok,
                          error=None if self.ok else "stub failure")


@pytest.fixture
def tcb_repo():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    repo = TcbRepository(engine)
    repo.ensure_schema()
    return repo


@pytest.fixture
def pusher():
    return StubPusher()


@pytest.fixture
def tcb_client(tcb_repo, pusher):
    app.dependency_overrides[get_tcb_repo] = lambda: tcb_repo
    app.dependency_overrides[get_watchlist_pusher] = lambda: pusher
    container.tcb_repo = tcb_repo
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Preview — parse, store nothing
# ---------------------------------------------------------------------------

def test_preview_returns_fields_without_storing(tcb_client, tcb_repo):
    resp = tcb_client.post(f"{PREFIX}/tcb/preview", json={
        "content": _load(1), "reference_date": "2026-09-22"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] is None
    assert body["session_date_hint"] == "2026-09-21"
    assert body["vnindex_close"] == pytest.approx(1799.67)
    assert body["foreign_net_bn"] == pytest.approx(-664.2)
    assert [c["symbol"] for c in body["companies"]] == ["MSN", "SSB", "MWG", "TLG"]
    assert [(r["symbol"], r["action"], r["label_verbatim"]) for r in body["recos"]] == [
        ("NTP", "WATCH", "Chờ mua")]
    assert tcb_repo.list() == []          # preview writes nothing


def test_preview_rejects_empty_content(tcb_client):
    assert tcb_client.post(f"{PREFIX}/tcb/preview", json={"content": "   "}).status_code == 422


# ---------------------------------------------------------------------------
# Save
# ---------------------------------------------------------------------------

def test_save_stores_parent_and_children(tcb_client, tcb_repo):
    resp = tcb_client.post(f"{PREFIX}/tcb", json={
        "content": _load(1), "session_date": "2026-09-21"})
    assert resp.status_code == 201
    body = resp.json()
    assert body["created"] is True
    mail = body["mail"]
    assert mail["id"] is not None
    assert mail["session_date"] == "2026-09-21"
    assert mail["lang"] == "vi"
    assert mail["ma50"] == pytest.approx(1776.0)
    assert len(mail["companies"]) == 4
    assert len(mail["recos"]) == 1


def test_save_keeps_raw_content_verbatim(tcb_repo):
    """EC-B2: the paste is the record; a parser fix must be replayable against it."""
    from app.ingest.tcb_mail_parser import parse_tcb_mail
    raw = _load(2)
    row, _ = tcb_repo.save(parse_tcb_mail(raw, reference_date=date(2026, 9, 22)),
                           raw=raw, session_date=date(2026, 9, 22))
    assert tcb_repo.get(row.id).raw_content == raw


def test_repasting_the_same_mail_is_a_noop(tcb_client, tcb_repo):
    first = tcb_client.post(f"{PREFIX}/tcb", json={
        "content": _load(1), "session_date": "2026-09-21"}).json()
    second = tcb_client.post(f"{PREFIX}/tcb", json={
        "content": _load(1), "session_date": "2026-09-21"}).json()
    assert first["created"] is True and second["created"] is False
    assert second["mail"]["id"] == first["mail"]["id"]
    assert len(tcb_repo.list()) == 1


def test_dedupe_ignores_reflowed_whitespace(tcb_client, tcb_repo):
    """A mail re-pasted from a different client reflows line breaks — still one session."""
    reflowed = _load(1).replace("\n\n", "\n \n ") + "   \n"
    tcb_client.post(f"{PREFIX}/tcb", json={"content": _load(1), "session_date": "2026-09-21"})
    resp = tcb_client.post(f"{PREFIX}/tcb", json={"content": reflowed, "session_date": "2026-09-21"})
    assert resp.json()["created"] is False
    assert len(tcb_repo.list()) == 1


def test_content_hash_is_whitespace_insensitive_but_content_sensitive():
    assert content_hash("a  b\n\nc") == content_hash(" a b c ")
    assert content_hash("NTP - Chờ mua") != content_hash("NTP - Mua")


def test_three_different_mails_are_three_sessions(tcb_client, tcb_repo):
    for n, d in ((1, "2026-09-21"), (2, "2026-09-22"), (3, "2026-09-23")):
        assert tcb_client.post(f"{PREFIX}/tcb", json={
            "content": _load(n), "session_date": d}).json()["created"] is True
    assert len(tcb_repo.list()) == 3


# ---------------------------------------------------------------------------
# Watchlist push
# ---------------------------------------------------------------------------

def test_save_pushes_every_recognised_call_by_default(tcb_client, pusher):
    body = tcb_client.post(f"{PREFIX}/tcb", json={
        "content": _load(1), "session_date": "2026-09-21"}).json()
    assert [p["symbol"] for p in body["pushed"]] == ["NTP"]
    assert pusher.calls[0]["symbol"] == "NTP"
    assert pusher.calls[0]["action"] == "WATCH"
    assert pusher.calls[0]["label_verbatim"] == "Chờ mua"
    assert pusher.calls[0]["session_date"] == date(2026, 9, 21)
    assert pusher.calls[0]["proposal_by"] == "TCB"
    assert body["mail"]["recos"][0]["pushed_to_watchlist"] is True


def test_empty_push_list_stores_without_touching_the_watchlist(tcb_client, pusher):
    body = tcb_client.post(f"{PREFIX}/tcb", json={
        "content": _load(1), "session_date": "2026-09-21", "push_symbols": []}).json()
    assert body["created"] is True
    assert body["pushed"] == []
    assert pusher.calls == []
    assert body["mail"]["recos"][0]["pushed_to_watchlist"] is False


def test_push_list_selects_which_calls_go_to_the_watchlist(tcb_client, pusher):
    """The operator unticked NTP in the preview, so nothing is pushed."""
    body = tcb_client.post(f"{PREFIX}/tcb", json={
        "content": _load(1), "session_date": "2026-09-21", "push_symbols": ["XYZ"]}).json()
    assert body["pushed"] == []
    assert pusher.calls == []


def test_bearer_token_is_forwarded_so_the_row_lands_on_the_callers_watchlist(tcb_client, pusher):
    tcb_client.post(f"{PREFIX}/tcb",
                    json={"content": _load(2), "session_date": "2026-09-22"},
                    headers={"Authorization": "Bearer tok-123"})
    assert pusher.calls[0]["authorization"] == "Bearer tok-123"


def test_proposal_by_is_overridable(tcb_client, pusher):
    tcb_client.post(f"{PREFIX}/tcb", json={
        "content": _load(2), "session_date": "2026-09-22", "proposal_by": "SSI"})
    assert pusher.calls[0]["proposal_by"] == "SSI"


def test_a_failed_push_never_costs_us_the_stored_mail(tcb_repo):
    """EC-N7: portfolio-service being down is reported, not fatal. The email is the
    record; the watchlist row can be retried."""
    failing = StubPusher(ok=False)
    app.dependency_overrides[get_tcb_repo] = lambda: tcb_repo
    app.dependency_overrides[get_watchlist_pusher] = lambda: failing
    container.tcb_repo = tcb_repo
    try:
        with TestClient(app) as c:
            body = c.post(f"{PREFIX}/tcb", json={
                "content": _load(1), "session_date": "2026-09-21"}).json()
        assert body["created"] is True
        assert body["pushed"] == [{"symbol": "NTP", "ok": False, "error": "stub failure"}]
        assert body["mail"]["recos"][0]["pushed_to_watchlist"] is False
        assert len(tcb_repo.list()) == 1
    finally:
        app.dependency_overrides.clear()


def test_unrecognised_label_is_stored_but_never_pushed_silently(tcb_client, pusher):
    """An action we cannot normalise must not reach the watchlist without review."""
    body = tcb_client.post(f"{PREFIX}/tcb", json={
        "content": "3. Khuyến nghị cổ phiếu\n\nHPG - Xin chào - Không rõ.\n",
        "session_date": "2026-09-21"}).json()
    reco = body["mail"]["recos"][0]
    assert reco["symbol"] == "HPG" and reco["action"] is None
    assert reco["label_verbatim"] == "Xin chào"     # kept verbatim (EC-B4)
    assert body["pushed"] == [] and pusher.calls == []


# ---------------------------------------------------------------------------
# Reads
# ---------------------------------------------------------------------------

def test_list_is_newest_session_first(tcb_client):
    for n, d in ((1, "2026-09-21"), (3, "2026-09-23"), (2, "2026-09-22")):
        tcb_client.post(f"{PREFIX}/tcb", json={"content": _load(n), "session_date": d})
    rows = tcb_client.get(f"{PREFIX}/tcb").json()
    assert [r["session_date"] for r in rows] == ["2026-09-23", "2026-09-22", "2026-09-21"]


def test_list_filters_by_session_date_range(tcb_client):
    for n, d in ((1, "2026-09-21"), (2, "2026-09-22"), (3, "2026-09-23")):
        tcb_client.post(f"{PREFIX}/tcb", json={"content": _load(n), "session_date": d})
    rows = tcb_client.get(f"{PREFIX}/tcb", params={"since": "2026-09-22"}).json()
    assert [r["session_date"] for r in rows] == ["2026-09-23", "2026-09-22"]


def test_reco_ledger_across_mails(tcb_client):
    for n, d in ((1, "2026-09-21"), (2, "2026-09-22"), (3, "2026-09-23")):
        tcb_client.post(f"{PREFIX}/tcb", json={"content": _load(n), "session_date": d})
    ledger = tcb_client.get(f"{PREFIX}/tcb/recos").json()
    assert [(r["symbol"], r["action"], r["session_date"]) for r in ledger] == [
        ("OIL", "WATCH", "2026-09-23"),
        ("MSN", "HOLD", "2026-09-22"),
        ("NTP", "WATCH", "2026-09-21"),
    ]


def test_reco_ledger_filters_by_symbol_and_action(tcb_client):
    for n, d in ((1, "2026-09-21"), (2, "2026-09-22"), (3, "2026-09-23")):
        tcb_client.post(f"{PREFIX}/tcb", json={"content": _load(n), "session_date": d})
    assert [r["symbol"] for r in
            tcb_client.get(f"{PREFIX}/tcb/recos", params={"action": "HOLD"}).json()] == ["MSN"]
    assert [r["symbol"] for r in
            tcb_client.get(f"{PREFIX}/tcb/recos", params={"symbol": "oil"}).json()] == ["OIL"]


def test_recos_route_is_not_shadowed_by_the_id_route(tcb_client):
    """/tcb/recos must resolve before /tcb/{mail_id}, or it 422s on "recos"."""
    assert tcb_client.get(f"{PREFIX}/tcb/recos").status_code == 200


def test_get_and_delete_one_mail(tcb_client, tcb_repo):
    mail_id = tcb_client.post(f"{PREFIX}/tcb", json={
        "content": _load(1), "session_date": "2026-09-21"}).json()["mail"]["id"]
    assert tcb_client.get(f"{PREFIX}/tcb/{mail_id}").json()["id"] == mail_id
    assert tcb_client.delete(f"{PREFIX}/tcb/{mail_id}").status_code == 204
    assert tcb_client.get(f"{PREFIX}/tcb/{mail_id}").status_code == 404
    assert tcb_repo.list() == []


def test_delete_removes_children_too(tcb_client, tcb_repo):
    from app.models.tcb_news import TcbNewsCompany, TcbNewsReco
    from sqlalchemy import func, select
    mail_id = tcb_client.post(f"{PREFIX}/tcb", json={
        "content": _load(1), "session_date": "2026-09-21"}).json()["mail"]["id"]
    tcb_client.delete(f"{PREFIX}/tcb/{mail_id}")
    with tcb_repo._Session() as s:
        assert s.execute(select(func.count()).select_from(TcbNewsCompany)).scalar() == 0
        assert s.execute(select(func.count()).select_from(TcbNewsReco)).scalar() == 0


def test_missing_mail_is_404(tcb_client):
    assert tcb_client.get(f"{PREFIX}/tcb/9999").status_code == 404
    assert tcb_client.delete(f"{PREFIX}/tcb/9999").status_code == 404


# ---------------------------------------------------------------------------
# Scoring endpoints (FR-BM-SCORE, FR-BM-RECORD)
# ---------------------------------------------------------------------------

def test_a_freshly_saved_call_is_unscored_and_queued(tcb_client, tcb_repo):
    tcb_client.post(f"{PREFIX}/tcb", json={"content": _load(1), "session_date": "2026-09-21"})
    pending = tcb_repo.list_unscored()
    assert [(r.symbol, d.isoformat()) for r, d in pending] == [("NTP", "2026-09-21")]
    assert pending[0][0].ret_20d is None and pending[0][0].scoring_done is False


def test_saved_scores_come_back_on_the_ledger(tcb_client, tcb_repo):
    """The individual marks are always readable, even while the aggregate is withheld."""
    from datetime import date as _date
    from app.services.call_scorer import CallScore

    tcb_client.post(f"{PREFIX}/tcb", json={"content": _load(1), "session_date": "2026-09-21"})
    reco_id = tcb_repo.list_unscored()[0][0].id
    tcb_repo.save_score(reco_id, CallScore(
        ref_date=_date(2026, 9, 21), ref_close=100.0,
        returns={1: 0.01, 5: 0.05, 20: 0.20, 60: None},
        excess={1: 0.005, 5: None, 20: 0.10, 60: None},
        adjusted=False,
    ), scoring_done=False)

    row = tcb_client.get(f"{PREFIX}/tcb/recos").json()[0]
    assert row["ref_close"] == pytest.approx(100.0)
    assert row["ret_20d"] == pytest.approx(0.20)
    assert row["ret_20d_vs_index"] == pytest.approx(0.10)
    assert row["ret_60d"] is None            # horizon not elapsed — reported as unknown
    assert row["ret_adjusted"] is False      # raw closes; caller can qualify it
    assert row["scored_at"] is not None


def test_a_partial_score_is_not_blanked_by_a_later_pass(tcb_client, tcb_repo):
    """The 60d pass must not wipe the 1d mark an earlier tick already established."""
    from app.services.call_scorer import CallScore
    tcb_client.post(f"{PREFIX}/tcb", json={"content": _load(1), "session_date": "2026-09-21"})
    reco_id = tcb_repo.list_unscored()[0][0].id

    tcb_repo.save_score(reco_id, CallScore(returns={1: 0.01, 5: None, 20: None, 60: None},
                                           excess={}), scoring_done=False)
    tcb_repo.save_score(reco_id, CallScore(returns={1: None, 5: None, 20: None, 60: 0.60},
                                           excess={}), scoring_done=True)

    row = tcb_client.get(f"{PREFIX}/tcb/recos").json()[0]
    assert row["ret_1d"] == pytest.approx(0.01)   # preserved
    assert row["ret_60d"] == pytest.approx(0.60)


def test_a_completed_call_leaves_the_scoring_queue(tcb_client, tcb_repo):
    from app.services.call_scorer import CallScore
    tcb_client.post(f"{PREFIX}/tcb", json={"content": _load(1), "session_date": "2026-09-21"})
    reco_id = tcb_repo.list_unscored()[0][0].id
    tcb_repo.save_score(reco_id, CallScore(
        returns={1: 0.01, 5: 0.05, 20: 0.20, 60: 0.60}, excess={}), scoring_done=True)
    assert tcb_repo.list_unscored() == []


def test_mark_scoring_done_retires_an_unpriceable_call(tcb_client, tcb_repo):
    tcb_client.post(f"{PREFIX}/tcb", json={"content": _load(1), "session_date": "2026-09-21"})
    reco_id = tcb_repo.list_unscored()[0][0].id
    tcb_repo.mark_scoring_done(reco_id)
    assert tcb_repo.list_unscored() == []


def test_record_is_withheld_below_the_minimum(tcb_client):
    """FR-BM-RECORD: three real emails are nowhere near 30 calls, so the aggregate must
    refuse — and say how far off it is rather than returning a meaningless number."""
    for n, d in ((1, "2026-09-21"), (2, "2026-09-22"), (3, "2026-09-23")):
        tcb_client.post(f"{PREFIX}/tcb", json={"content": _load(n), "session_date": d})
    resp = tcb_client.get(f"{PREFIX}/tcb/calls/record")
    assert resp.status_code == 409
    assert "30 required" in resp.json()["detail"]


def test_record_reports_once_enough_calls_are_scored(tcb_client, tcb_repo):
    from app.services.call_scorer import CallScore
    from app.models.tcb_news import TcbNews, TcbNewsReco
    from datetime import date as _date, datetime as _dt, timezone as _tz

    # 30 scored BUY calls that each beat a flat index.
    with tcb_repo._Session() as s:
        mail = TcbNews(session_date=_date(2026, 9, 21), source="tcbs.daily",
                       raw_content="x", content_hash="seed", created_at=_dt.now(_tz.utc))
        mail.recos = [TcbNewsReco(symbol=f"S{i:02d}", action="BUY", label_verbatim="Mua")
                      for i in range(30)]
        s.add(mail)
        s.commit()
        ids = [r.id for r in mail.recos]
    for rid in ids:
        tcb_repo.save_score(rid, CallScore(
            returns={1: 0.01, 5: 0.02, 20: 0.05, 60: 0.08},
            excess={1: 0.01, 5: 0.02, 20: 0.05, 60: 0.08}), scoring_done=True)

    body = tcb_client.get(f"{PREFIX}/tcb/calls/record").json()
    assert body["reportable"] is True
    assert body["scored_calls"] == 30
    h20 = body["horizons"]["20d"]
    assert h20["hit_rate"] == pytest.approx(1.0)
    assert h20["mean_return"] == pytest.approx(0.05)
    assert h20["mean_excess_return"] == pytest.approx(0.05)
    # Excess == return means the index went nowhere, so the benchmark bet lost.
    assert h20["benchmark_hit_rate"] == pytest.approx(0.0)
    assert body["by_action"]["BUY"]["n"] == 30


def test_score_endpoint_runs_a_pass(tcb_client, tcb_repo):
    from app.deps import get_call_scorer

    class StubScorer:
        async def tick(self):
            return {"considered": 2, "scored": 1, "completed": 0,
                    "gave_up": 0, "unavailable": ["GONE"]}

    app.dependency_overrides[get_call_scorer] = lambda: StubScorer()
    try:
        body = tcb_client.post(f"{PREFIX}/tcb/score").json()
    finally:
        app.dependency_overrides.pop(get_call_scorer, None)
    assert body == {"considered": 2, "scored": 1, "completed": 0,
                    "gave_up": 0, "unavailable": ["GONE"]}


def test_scoring_routes_are_not_shadowed_by_the_id_route(tcb_client):
    """/tcb/calls/record and /tcb/score must resolve before /tcb/{mail_id}."""
    assert tcb_client.get(f"{PREFIX}/tcb/calls/record").status_code == 409  # not 422
