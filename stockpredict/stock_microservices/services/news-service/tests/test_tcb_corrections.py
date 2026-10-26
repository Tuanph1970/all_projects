"""Operator corrections to a parsed TCBS mail (Backlog #55).

Before this, the only remedy for a misparsed call was to untick it — which does not fix
the call, it loses it: the mail still stores the recommendation and the watchlist never
sees it.

The properties these hold down:

  * a correction edits the INTERPRETATION, never `raw_content` (EC-B2), so a parser fix
    is still replayable over the archive;
  * every overridden field is RECORDED, because extraction is a re-runnable pass and a
    reparse would otherwise silently revert a human's work;
  * a correction that cannot be matched to its call rejects the whole save (EC-B10) —
    one ticker landing on the wrong row would poison the ledger silently;
  * `label_verbatim` is never correctable (EC-B4), which is what keeps the correction
    auditable afterwards.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from app.deps import container, get_tcb_repo, get_watchlist_pusher
from app.ingest.tcb_corrections import CorrectionError, apply_corrections
from app.ingest.tcb_mail_parser import ParsedMail, ParsedReco, parse_tcb_mail
from app.main import app
from app.repositories.tcb_repository import TcbRepository
from app.services.watchlist_push import PushResult

FIXTURES = Path(__file__).parent / "fixtures"
PREFIX = "/stock_helper/api/v2/news"
CALL_DATE = date(2026, 9, 21)


def _load(n: int) -> str:
    return (FIXTURES / f"tcb_mail_{n}.txt").read_text(encoding="utf-8")


class Fix:
    """A correction payload, duck-typed like the pydantic model."""

    def __init__(self, index, from_symbol, symbol=None, action=None, target_price=None):
        self.index = index
        self.from_symbol = from_symbol
        self.symbol = symbol
        self.action = action
        self.target_price = target_price


def mail(*recos) -> ParsedMail:
    return ParsedMail(recos=list(recos))


def reco(symbol="NTP", action="WATCH", label="Chờ mua", **kw) -> ParsedReco:
    return ParsedReco(symbol=symbol, action=action, label_verbatim=label, **kw)


# ---------------------------------------------------------------------------
# Applying a correction
# ---------------------------------------------------------------------------

def test_no_corrections_leaves_the_parse_exactly_as_it_was():
    parsed = mail(reco(), reco(symbol="MSN", action="BUY", label="Mua"))
    assert apply_corrections(parsed, None) is parsed
    assert apply_corrections(parsed, []) is parsed


def test_a_corrected_ticker_replaces_the_parsed_one_and_is_recorded():
    parsed = apply_corrections(mail(reco(symbol="NTP")),
                               [Fix(0, "NTP", symbol="NTL")])
    assert parsed.recos[0].symbol == "NTL"
    assert parsed.recos[0].corrected_fields == ("symbol",)
    # EC-B4: the source phrase is untouched, which is what makes the fix auditable.
    assert parsed.recos[0].label_verbatim == "Chờ mua"


def test_a_corrected_action_replaces_the_normalisation_not_the_label():
    parsed = apply_corrections(mail(reco(action="WATCH", label="Chờ mua")),
                               [Fix(0, "NTP", action="BUY")])
    assert parsed.recos[0].action == "BUY"
    assert parsed.recos[0].label_verbatim == "Chờ mua"
    assert parsed.recos[0].corrected_fields == ("action",)


def test_an_unknown_action_can_be_resolved_to_a_real_one():
    """The case the hint on the preview screen is about: the parser could not normalise
    the label, so the call would never be pushed. Now it can be rescued."""
    parsed = apply_corrections(mail(reco(action=None, label="Mua gom dần")),
                               [Fix(0, "NTP", action="BUY")])
    assert parsed.recos[0].action == "BUY"


def test_an_action_can_be_cleared_back_to_unknown():
    parsed = apply_corrections(mail(reco(action="BUY")), [Fix(0, "NTP", action="")])
    assert parsed.recos[0].action is None
    assert parsed.recos[0].corrected_fields == ("action",)


def test_several_fields_on_one_call_are_all_recorded():
    parsed = apply_corrections(
        mail(reco(symbol="NTP", action="WATCH")),
        [Fix(0, "NTP", symbol="NTL", action="BUY", target_price=31.5)])
    r = parsed.recos[0]
    assert (r.symbol, r.action, r.target_price) == ("NTL", "BUY", 31.5)
    assert r.corrected_fields == ("action", "symbol", "target_price")


def test_corrections_to_different_calls_are_independent():
    parsed = apply_corrections(
        mail(reco(symbol="NTP"), reco(symbol="MSN", action="BUY", label="Mua")),
        [Fix(1, "MSN", symbol="MSR")])
    assert parsed.recos[0].symbol == "NTP" and parsed.recos[0].corrected_fields == ()
    assert parsed.recos[1].symbol == "MSR" and parsed.recos[1].corrected_fields == ("symbol",)


def test_a_ticker_is_normalised_to_upper_case():
    parsed = apply_corrections(mail(reco()), [Fix(0, "ntp", symbol=" ntl ")])
    assert parsed.recos[0].symbol == "NTL"


def test_echoing_a_value_back_unchanged_is_not_recorded_as_a_correction():
    """The UI sends whatever sits in its inputs. An unchanged value must not be logged
    as a human correction, or the audit trail stops meaning anything."""
    parsed = apply_corrections(
        mail(reco(symbol="NTP", action="WATCH")),
        [Fix(0, "NTP", symbol="NTP", action="WATCH")])
    assert parsed.recos[0].corrected_fields == ()


# ---------------------------------------------------------------------------
# Refusing a correction that cannot be matched (EC-B10)
# ---------------------------------------------------------------------------

def test_a_mismatched_cross_check_is_refused():
    """The guard that makes an index safe to trust: if the row at that position is not
    the ticker the operator was looking at, the edit is not applied anywhere."""
    with pytest.raises(CorrectionError, match="does not match"):
        apply_corrections(mail(reco(symbol="NTP")), [Fix(0, "MSN", symbol="MSR")])


def test_an_out_of_range_index_is_refused():
    with pytest.raises(CorrectionError, match="parsed 1"):
        apply_corrections(mail(reco()), [Fix(5, "NTP", symbol="NTL")])


def test_two_corrections_to_the_same_call_are_refused():
    """Taking the last would make the result depend on payload order."""
    with pytest.raises(CorrectionError, match="two corrections"):
        apply_corrections(mail(reco()),
                          [Fix(0, "NTP", symbol="NTL"), Fix(0, "NTP", symbol="MSN")])


@pytest.mark.parametrize("bad", ["", "N", "NT", "NOT A TICKER", "NTP!", "x" * 13])
def test_an_unusable_ticker_is_refused(bad):
    with pytest.raises(CorrectionError, match="not a usable ticker"):
        apply_corrections(mail(reco()), [Fix(0, "NTP", symbol=bad)])


def test_an_unrecognised_action_is_refused_rather_than_stored():
    with pytest.raises(CorrectionError, match="not a recognised action"):
        apply_corrections(mail(reco()), [Fix(0, "NTP", action="STRONG_BUY")])


def test_a_non_positive_target_price_is_refused():
    with pytest.raises(CorrectionError, match="must be positive"):
        apply_corrections(mail(reco()), [Fix(0, "NTP", target_price=-1)])


def test_a_refusal_leaves_the_parse_untouched():
    """EC-B10: no partial application. The first correction must not survive the second
    one being rejected."""
    parsed = mail(reco(symbol="NTP"), reco(symbol="MSN", action="BUY", label="Mua"))
    with pytest.raises(CorrectionError):
        apply_corrections(parsed, [Fix(0, "NTP", symbol="NTL"), Fix(1, "WRONG", symbol="X")])
    assert [r.symbol for r in parsed.recos] == ["NTP", "MSN"]
    assert all(r.corrected_fields == () for r in parsed.recos)


# ---------------------------------------------------------------------------
# End to end through the save endpoint
# ---------------------------------------------------------------------------

class StubPusher:
    def __init__(self):
        self.calls: list[dict] = []

    def push(self, **kwargs) -> PushResult:
        self.calls.append(kwargs)
        return PushResult(symbol=kwargs["symbol"], ok=True, error=None)


@pytest.fixture
def repo():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    r = TcbRepository(engine)
    r.ensure_schema()
    return r


@pytest.fixture
def pusher():
    return StubPusher()


@pytest.fixture
def client(repo, pusher):
    app.dependency_overrides[get_tcb_repo] = lambda: repo
    app.dependency_overrides[get_watchlist_pusher] = lambda: pusher
    container.tcb_repo = repo
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _first_symbol() -> str:
    """Whatever the fixture mail's first recommendation actually parses as — read from
    the parser rather than hardcoded, so this suite does not quietly encode a guess."""
    return parse_tcb_mail(_load(1), reference_date=CALL_DATE).recos[0].symbol


def test_a_correction_is_stored_and_the_raw_text_is_untouched(client, repo):
    original = _first_symbol()
    resp = client.post(f"{PREFIX}/tcb", json={
        "content": _load(1),
        "session_date": "2026-09-21",
        "corrections": [{"index": 0, "from_symbol": original, "symbol": "NTL"}],
        "push_symbols": [],
    })
    assert resp.status_code == 201
    stored = resp.json()["mail"]["recos"][0]
    assert stored["symbol"] == "NTL"
    assert stored["corrected_fields"] == "symbol"
    assert stored["corrected_at"] is not None

    # EC-B2: the archive is byte-identical, so a parser fix is still replayable over it.
    row = repo.get(resp.json()["mail"]["id"])
    assert row.raw_content == _load(1)
    assert parse_tcb_mail(row.raw_content, reference_date=CALL_DATE).recos[0].symbol == original


def test_an_uncorrected_call_records_no_provenance(client):
    resp = client.post(f"{PREFIX}/tcb", json={
        "content": _load(1), "session_date": "2026-09-21", "push_symbols": [],
    })
    for stored in resp.json()["mail"]["recos"]:
        assert stored["corrected_fields"] is None and stored["corrected_at"] is None


def test_the_corrected_ticker_is_what_reaches_the_watchlist(client, pusher):
    """The whole point of #55: the fixed call must actually arrive, not be dropped."""
    original = _first_symbol()
    resp = client.post(f"{PREFIX}/tcb", json={
        "content": _load(1),
        "session_date": "2026-09-21",
        "corrections": [{"index": 0, "from_symbol": original, "symbol": "NTL",
                         "action": "BUY"}],
        "push_symbols": ["NTL"],
    })
    assert resp.status_code == 201
    assert [c["symbol"] for c in pusher.calls] == ["NTL"]
    assert pusher.calls[0]["action"] == "BUY"
    assert [p["symbol"] for p in resp.json()["pushed"]] == ["NTL"]


def test_a_mismatched_correction_is_a_422_and_stores_nothing(client, repo):
    resp = client.post(f"{PREFIX}/tcb", json={
        "content": _load(1),
        "session_date": "2026-09-21",
        "corrections": [{"index": 0, "from_symbol": "WRONG", "symbol": "NTL"}],
    })
    assert resp.status_code == 422
    assert "does not match" in resp.json()["detail"]
    assert repo.list() == []          # EC-B10: nothing half-written


def test_an_unrecognised_action_is_a_422_and_stores_nothing(client, repo):
    original = _first_symbol()
    resp = client.post(f"{PREFIX}/tcb", json={
        "content": _load(1),
        "session_date": "2026-09-21",
        "corrections": [{"index": 0, "from_symbol": original, "action": "STRONG_BUY"}],
    })
    assert resp.status_code == 422
    assert repo.list() == []


def test_a_malformed_correction_is_rejected_by_the_schema(client):
    """A negative index never reaches the apply pass."""
    resp = client.post(f"{PREFIX}/tcb", json={
        "content": _load(1),
        "session_date": "2026-09-21",
        "corrections": [{"index": -1, "from_symbol": "NTP", "symbol": "NTL"}],
    })
    assert resp.status_code == 422


def test_the_ledger_surfaces_the_correction(client):
    original = _first_symbol()
    client.post(f"{PREFIX}/tcb", json={
        "content": _load(1),
        "session_date": "2026-09-21",
        "corrections": [{"index": 0, "from_symbol": original, "symbol": "NTL"}],
        "push_symbols": [],
    })
    rows = client.get(f"{PREFIX}/tcb/recos").json()
    corrected = [r for r in rows if r["symbol"] == "NTL"]
    assert len(corrected) == 1
    assert corrected[0]["corrected_fields"] == "symbol"
