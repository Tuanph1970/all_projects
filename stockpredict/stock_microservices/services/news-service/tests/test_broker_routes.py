"""API tests for broker-mail intake, phase E1 (FR-BM-INTAKE, FR-BM-BACKFILL, EC-B8).

Two endpoints, and the two things about them that matter:

  * a mailbox problem is reported as data, not as a 5xx — "the service is broken" and
    "the mailbox was unreachable this minute" lead the operator somewhere different;
  * no message content crosses the API (EC-B8): counts and timestamps only.
"""
from __future__ import annotations

from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from app.deps import container, get_broker_mail_repo, get_broker_mail_source
from app.ingest.broker_mail_source import BrokerMailSource
from app.main import app
from app.repositories.broker_mail_repository import BrokerMailRepository

PREFIX = "/stock_helper/api/v2/news"
ALLOW = ("*@tcbs.com.vn",)


def mail(message_id: str = "<a@tcbs.com.vn>", sender: str = "research@tcbs.com.vn") -> bytes:
    return (f"From: TCBS <{sender}>\r\nMessage-ID: {message_id}\r\n"
            f"Subject: Investment Opportunity\r\n"
            f"Date: Mon, 21 Sep 2026 17:05:00 +0700\r\n\r\nbody\r\n").encode()


class FakeMailbox:
    """The `Mailbox` port.

    Messages default to *today* rather than a fixed date: the route calls `tick()` with
    no argument, so the window is computed from the real clock, and a fixture pinned to a
    literal date silently falls out of the window as time passes — which is exactly how
    these tests first failed.
    """

    def __init__(self, messages, received=None):
        self._messages = messages
        self._received = received or {}
        self.searched = []
        self.closed = 0

    def search_since(self, since):
        self.searched.append(since)
        if since is None:
            return list(self._messages)
        return [u for u in self._messages
                if self._received.get(u, date.today()) >= since]

    def fetch(self, uid):
        return self._messages.get(uid)

    def close(self):
        self.closed += 1


@pytest.fixture
def broker_repo():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    repo = BrokerMailRepository(engine)
    repo.ensure_schema()
    return repo


@pytest.fixture
def mailbox():
    """One message far in the past and one from today — so a tick sees exactly one and
    a backfill sees both, whenever these tests happen to run."""
    return FakeMailbox({b"1": mail("<a@tcbs.com.vn>"), b"2": mail("<b@tcbs.com.vn>")},
                       received={b"1": date(2025, 3, 2), b"2": date.today()})


@pytest.fixture
def broker_client(broker_repo, mailbox):
    source = BrokerMailSource(broker_repo, lambda: mailbox, allow_from=ALLOW)
    app.dependency_overrides[get_broker_mail_repo] = lambda: broker_repo
    app.dependency_overrides[get_broker_mail_source] = lambda: source
    container.broker_mail_repo = broker_repo
    container.broker_mail_source = source
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# POST /news/broker/poll
# ---------------------------------------------------------------------------

def test_poll_captures_and_reports_counts(broker_client, broker_repo):
    body = broker_client.post(f"{PREFIX}/broker/poll").json()

    assert body["captured"] == 1          # only the message inside the 7-day window
    assert body["duplicates"] == 0 and body["failed"] is False
    assert broker_repo.stats()["stored"] == 1


def test_polling_twice_captures_nothing_the_second_time(broker_client):
    first = broker_client.post(f"{PREFIX}/broker/poll").json()
    second = broker_client.post(f"{PREFIX}/broker/poll").json()

    assert first["captured"] == 1
    assert second["captured"] == 0 and second["duplicates"] == 1


def test_since_turns_the_poll_into_the_backfill(broker_client, broker_repo, mailbox):
    body = broker_client.post(f"{PREFIX}/broker/poll", params={"since": "2025-01-01"}).json()

    assert body["captured"] == 2          # reaches back past the tick's window
    assert mailbox.searched == [date(2025, 1, 1)]
    assert broker_repo.stats()["stored"] == 2


def test_the_backfill_is_idempotent_over_the_api(broker_client, broker_repo):
    broker_client.post(f"{PREFIX}/broker/poll", params={"since": "2025-01-01"})
    again = broker_client.post(f"{PREFIX}/broker/poll", params={"since": "2025-01-01"}).json()

    assert again["captured"] == 0 and again["duplicates"] == 2
    assert broker_repo.stats()["stored"] == 2


def test_an_unreachable_mailbox_is_200_with_a_reason_not_a_5xx(broker_repo):
    def explode():
        raise OSError("connection refused")

    source = BrokerMailSource(broker_repo, explode, allow_from=ALLOW)
    app.dependency_overrides[get_broker_mail_repo] = lambda: broker_repo
    app.dependency_overrides[get_broker_mail_source] = lambda: source
    with TestClient(app) as c:
        resp = c.post(f"{PREFIX}/broker/poll")
    app.dependency_overrides.clear()

    assert resp.status_code == 200
    body = resp.json()
    assert body["failed"] is True and body["captured"] == 0
    assert "connection refused" in body["detail"]


def test_a_rejected_sender_is_named_but_no_content_is_returned(broker_repo):
    box = FakeMailbox({b"1": mail("<x@evil.com>", sender="attacker@evil.com")})
    source = BrokerMailSource(broker_repo, lambda: box, allow_from=ALLOW)
    app.dependency_overrides[get_broker_mail_repo] = lambda: broker_repo
    app.dependency_overrides[get_broker_mail_source] = lambda: source
    with TestClient(app) as c:
        body = c.post(f"{PREFIX}/broker/poll").json()
    app.dependency_overrides.clear()

    assert body["rejected"] == 1 and body["captured"] == 0
    assert body["senders_rejected"] == ["attacker@evil.com"]
    # EC-B8: a diagnosable sender, but never a subject or a body.
    assert "subject" not in body and "raw_mime" not in body


# ---------------------------------------------------------------------------
# GET /news/broker/intake — the E1 gate
# ---------------------------------------------------------------------------

def test_intake_stats_start_empty(broker_client):
    body = broker_client.get(f"{PREFIX}/broker/intake").json()

    assert body["stored"] == 0 and body["distinct_message_ids"] == 0
    assert body["earliest_received"] is None and body["unextracted"] == 0
    # Reflects config rather than guessing: the loop is off by default (Appendix C) and
    # no mailbox is configured in a test environment.
    assert body["enabled"] is False and body["configured"] is False


def test_intake_stats_report_the_gate_after_a_backfill(broker_client):
    broker_client.post(f"{PREFIX}/broker/poll", params={"since": "2025-01-01"})
    body = broker_client.get(f"{PREFIX}/broker/intake").json()

    assert body["stored"] == 2
    assert body["distinct_message_ids"] == 2       # == stored is the zero-dup assertion
    assert body["earliest_received"] is not None   # the history actually came back
    assert body["latest_received"] is not None
    assert body["unextracted"] == 2                # E1 parses nothing, by design


def test_the_stats_payload_carries_no_message_content(broker_client):
    broker_client.post(f"{PREFIX}/broker/poll", params={"since": "2025-01-01"})
    body = broker_client.get(f"{PREFIX}/broker/intake").json()

    assert set(body) == {
        "enabled", "configured", "stored", "distinct_message_ids",
        "earliest_received", "latest_received", "unextracted",
    }
