"""Broker-mail intake, phase E1 (FR-BM-INTAKE, FR-BM-DEDUP, FR-BM-BACKFILL).

The properties these exist to hold down, from SRS §5.1 and the EC constraints:

  * the sender allow-list accepts TCBS and rejects everything else (EC-B1);
  * `mail_id` is stable, and re-seeing a message inserts nothing (FR-BM-DEDUP);
  * raw MIME survives byte-for-byte, because a lossy archive cannot be replayed (EC-B2);
  * nothing raises into the scheduler — an outage defers, it does not fail;
  * capture is permissive: a drifted subject must not cost us the mail.

No IMAP server and no network: the `Mailbox` port is faked, which is the whole reason
intake was written against a port rather than against imaplib.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from app.ingest.broker_mail_source import (
    BrokerMailSource,
    decode_subject,
    imap_date,
    mail_id_for,
    received_utc_of,
    sender_allowed,
    synthetic_message_id,
)
from app.repositories.broker_mail_repository import BrokerMailRepository

ALLOW = ("*@tcbs.com.vn", "forwarder@gmail.com")


def mail(
    *,
    message_id: str = "<daily-2026-09-21@tcbs.com.vn>",
    sender: str = "research@tcbs.com.vn",
    subject: str = "=?utf-8?B?Q8ahIGjhu5lpIMSR4bqndSB0xrA=?=",   # "Cơ hội đầu tư"
    date_hdr: str = "Mon, 21 Sep 2026 17:05:00 +0700",
    body: str = "Thị trường chung: VN-Index 1,774.15\r\n",
) -> bytes:
    """A minimal but real RFC 822 message, as bytes — which is what IMAP returns."""
    headers = [f"From: TCBS Research <{sender}>", "To: ingest@example.com"]
    if message_id:
        headers.append(f"Message-ID: {message_id}")
    if subject:
        headers.append(f"Subject: {subject}")
    if date_hdr:
        headers.append(f"Date: {date_hdr}")
    headers += ["MIME-Version: 1.0", "Content-Type: text/plain; charset=utf-8"]
    return ("\r\n".join(headers) + "\r\n\r\n" + body).encode("utf-8")


class FakeMailbox:
    """The `Mailbox` port. `messages` maps uid -> raw bytes."""

    def __init__(self, messages: dict[bytes, bytes], *, received: dict[bytes, date] | None = None):
        self._messages = messages
        self._received = received or {}
        self.searched: list[date | None] = []
        self.closed = 0

    def search_since(self, since):
        self.searched.append(since)
        if since is None:
            return list(self._messages)
        return [uid for uid in self._messages
                if self._received.get(uid, date(2026, 9, 21)) >= since]

    def fetch(self, uid):
        return self._messages.get(uid)

    def close(self):
        self.closed += 1


def fresh_repo() -> BrokerMailRepository:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    repo = BrokerMailRepository(engine)
    repo.ensure_schema()
    return repo


def source_over(messages, *, repo=None, **kw):
    repo = repo or fresh_repo()
    box = FakeMailbox(messages) if isinstance(messages, dict) else messages
    src = BrokerMailSource(repo, lambda: box, allow_from=ALLOW, **kw)
    return src, repo, box


# ---------------------------------------------------------------------------
# EC-B1 — the sender allow-list
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("sender", [
    "research@tcbs.com.vn",
    "RESEARCH@TCBS.COM.VN",          # case-insensitive on the address
    "no-reply@tcbs.com.vn",
    "forwarder@gmail.com",           # the forwarding address, per Appendix B
])
def test_the_allow_list_accepts_tcbs_and_the_forwarder(sender):
    assert sender_allowed(sender, ALLOW) is True


@pytest.mark.parametrize("sender", [
    "attacker@evil.com",
    "",
    "research@tcbs.com.vn.evil.com",      # suffix, not the domain
    "research@nottcbs.com.vn",
    "someone@gmail.com",                  # a different Gmail is not the forwarder
])
def test_the_allow_list_rejects_everything_else(sender):
    assert sender_allowed(sender, ALLOW) is False


def test_a_display_name_cannot_widen_the_allow_list():
    """The display name is attacker-chosen; only the address may ever match."""
    raw = mail(sender="attacker@evil.com").replace(
        b"From: TCBS Research <attacker@evil.com>",
        b'From: "research@tcbs.com.vn" <attacker@evil.com>')
    src, repo, _ = source_over({b"1": raw})
    result = src.intake(since=None)

    assert result.captured == 0 and result.rejected == 1
    assert repo.stats()["stored"] == 0


@pytest.mark.asyncio
async def test_non_allow_listed_mail_is_ignored_without_error():
    """EC-B1 says ignored, not failed — the ingestion mailbox may receive other mail."""
    src, repo, _ = source_over({
        b"1": mail(),
        b"2": mail(message_id="<spam@evil.com>", sender="attacker@evil.com"),
    })
    result = await src.tick(today=date(2026, 9, 22))

    assert result["captured"] == 1 and result["rejected"] == 1
    assert result["errors"] == 0 and result["failed"] is False
    assert result["senders_rejected"] == ["attacker@evil.com"]


# ---------------------------------------------------------------------------
# FR-BM-DEDUP — mail_id and insert-if-absent
# ---------------------------------------------------------------------------

def test_mail_id_is_sha256_of_the_message_id_and_stable():
    import hashlib
    mid = "<daily-2026-09-21@tcbs.com.vn>"
    assert mail_id_for(mid) == hashlib.sha256(mid.encode()).hexdigest()
    assert mail_id_for(mid) == mail_id_for(f"  {mid}  ")   # surrounding space ignored
    assert mail_id_for(mid) != mail_id_for(mid.upper())    # but case is significant


@pytest.mark.asyncio
async def test_re_seeing_a_message_inserts_nothing():
    src, repo, _ = source_over({b"1": mail()})
    first = await src.tick(today=date(2026, 9, 22))
    second = await src.tick(today=date(2026, 9, 22))

    assert first["captured"] == 1 and first["duplicates"] == 0
    assert second["captured"] == 0 and second["duplicates"] == 1
    assert repo.stats()["stored"] == 1


@pytest.mark.asyncio
async def test_a_second_sighting_never_overwrites_the_stored_message():
    """EC-B2: raw is immutable, so even a changed body must not rewrite the row."""
    repo = fresh_repo()
    src, _, _ = source_over({b"1": mail(body="original\r\n")}, repo=repo)
    await src.tick(today=date(2026, 9, 22))
    stored = repo.list_recent()[0].raw_mime

    # The same Message-ID arriving with different content — a forwarded, re-wrapped copy.
    src2, _, _ = source_over({b"1": mail(body="tampered\r\n")}, repo=repo)
    result = await src2.tick(today=date(2026, 9, 22))

    assert result["duplicates"] == 1 and result["captured"] == 0
    assert repo.list_recent()[0].raw_mime == stored
    assert "original" in stored and "tampered" not in stored


def test_mail_with_no_message_id_is_still_captured_and_still_dedupes():
    """RFC 5322 says SHOULD, not MUST. Dropping it would break capture; randomising the
    id would break dedupe. The surrogate hashes the bytes, so both hold."""
    raw = mail(message_id="")
    src, repo, _ = source_over({b"1": raw})

    first = src.intake(since=None)
    second = src.intake(since=None)

    assert first.captured == 1 and second.duplicates == 1
    row = repo.list_recent()[0]
    assert row.message_id == synthetic_message_id(raw)
    assert row.message_id.startswith("synthetic-")   # traceable as a stand-in


def test_stats_report_zero_duplicates_as_an_equality():
    src, repo, _ = source_over({
        b"1": mail(message_id="<a@tcbs.com.vn>"),
        b"2": mail(message_id="<b@tcbs.com.vn>"),
    })
    src.intake(since=None)
    stats = repo.stats()

    assert stats["stored"] == 2 == stats["distinct_message_ids"]
    assert stats["unextracted"] == 2


# ---------------------------------------------------------------------------
# EC-B2 — raw MIME is byte-exact
# ---------------------------------------------------------------------------

def test_raw_mime_round_trips_byte_for_byte():
    """The archive's whole value is that a future parser can replay over it, so the
    bytes IMAP handed us must come back out of the database unchanged."""
    raw = mail(body="Ngành: Plants — ~1.234,5 tỷ ₫\r\n\x80\xff binary-ish\r\n".encode(
        "utf-8", "surrogateescape").decode("utf-8", "replace"))
    src, repo, _ = source_over({b"1": raw})
    src.intake(since=None)

    assert repo.list_recent()[0].raw_mime.encode("latin-1") == raw


def test_a_non_utf8_message_is_captured_without_corruption():
    """A latin-1 body is legal MIME and would be mangled by a utf-8 decode."""
    raw = (b"From: research@tcbs.com.vn\r\nMessage-ID: <x@tcbs.com.vn>\r\n"
           b"Subject: test\r\nDate: Mon, 21 Sep 2026 17:05:00 +0700\r\n"
           b"Content-Type: text/plain; charset=iso-8859-1\r\n\r\n"
           b"caf\xe9 \xff\xfe not utf-8\r\n")
    src, repo, _ = source_over({b"1": raw})
    src.intake(since=None)

    assert repo.list_recent()[0].raw_mime.encode("latin-1") == raw


def test_the_subject_is_decoded_for_humans_even_though_raw_is_not():
    src, repo, _ = source_over({b"1": mail()})
    src.intake(since=None)
    assert repo.list_recent()[0].subject == "Cơ hội đầu tư"


def test_decode_subject_survives_a_malformed_header():
    assert decode_subject(None) is None
    assert decode_subject("plain ascii") == "plain ascii"
    assert decode_subject("=?utf-8?B?!!!not-base64!!!?=") is not None


# ---------------------------------------------------------------------------
# Capture is permissive (rule 1) — filtering is E2's job
# ---------------------------------------------------------------------------

def test_a_drifted_subject_does_not_cost_us_the_mail():
    """Appendix D warns the format drifts. A subject filter would turn drift into
    silently lost mail, which EC-B2 calls the one unrecoverable outcome."""
    src, repo, _ = source_over({
        b"1": mail(message_id="<a@tcbs.com.vn>", subject="Daily Market Wrap"),
        b"2": mail(message_id="<b@tcbs.com.vn>", subject=""),      # no Subject at all
    })
    result = src.intake(since=None)

    assert result.captured == 2 and result.rejected == 0
    assert repo.stats()["stored"] == 2
    assert repo.list_recent()[0].subject in (None, "Daily Market Wrap")


def test_a_broken_date_header_still_lands_with_a_usable_timestamp():
    before = datetime.now(timezone.utc)
    src, repo, _ = source_over({
        b"1": mail(message_id="<a@tcbs.com.vn>", date_hdr=""),
        b"2": mail(message_id="<b@tcbs.com.vn>", date_hdr="not a date at all"),
    })
    result = src.intake(since=None)

    assert result.captured == 2
    for row in repo.list_recent():
        assert row.received_utc is not None       # never NULL — ordering depends on it
        # Neither sqlite nor MySQL DATETIME stores an offset, so the column reads back
        # NAIVE and is UTC purely by the write-side convention. Re-attaching UTC here is
        # the comparison the rest of the codebase has to make too — comparing this value
        # against an aware datetime raises, which is exactly how this assertion first
        # failed.
        assert row.received_utc.replace(tzinfo=timezone.utc) >= before - timedelta(seconds=5)


def test_received_utc_is_normalised_to_utc():
    """17:05 +0700 is 10:05 UTC — a session date derived from the wrong zone would be
    off by a day for a mail sent after 17:00 Hanoi time, which is every one of them."""
    import email as _email
    msg = _email.message_from_bytes(mail())
    got = received_utc_of(msg, fallback=datetime.now(timezone.utc))
    assert (got.year, got.month, got.day, got.hour, got.minute) == (2026, 9, 21, 10, 5)
    assert got.tzinfo is not None


# ---------------------------------------------------------------------------
# Rule 4 — never raises into the scheduler
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_an_unreachable_mailbox_defers_and_never_raises():
    def explode():
        raise OSError("connection refused")

    src = BrokerMailSource(fresh_repo(), explode, allow_from=ALLOW)
    result = await src.tick(today=date(2026, 9, 22))

    assert result["failed"] is True and result["captured"] == 0
    assert "connection refused" in result["detail"]


@pytest.mark.asyncio
async def test_a_bad_password_defers_and_never_raises():
    import imaplib

    def explode():
        raise imaplib.IMAP4.error("AUTHENTICATIONFAILED")

    src = BrokerMailSource(fresh_repo(), explode, allow_from=ALLOW)
    result = await src.tick(today=date(2026, 9, 22))
    assert result["failed"] is True and "AUTHENTICATIONFAILED" in result["detail"]


@pytest.mark.asyncio
async def test_a_failing_search_defers_without_losing_the_mailbox():
    class BadSearch(FakeMailbox):
        def search_since(self, since):
            raise RuntimeError("SEARCH timed out")

    box = BadSearch({b"1": mail()})
    src = BrokerMailSource(fresh_repo(), lambda: box, allow_from=ALLOW)
    result = await src.tick(today=date(2026, 9, 22))

    assert result["failed"] is True and "SEARCH timed out" in result["detail"]
    assert box.closed == 1                 # the connection is still released


def test_one_unreadable_message_does_not_abandon_the_batch():
    class HalfBroken(FakeMailbox):
        def fetch(self, uid):
            if uid == b"2":
                raise RuntimeError("FETCH failed")
            return super().fetch(uid)

    box = HalfBroken({b"1": mail(message_id="<a@tcbs.com.vn>"),
                      b"2": mail(message_id="<b@tcbs.com.vn>"),
                      b"3": mail(message_id="<c@tcbs.com.vn>")})
    src = BrokerMailSource(fresh_repo(), lambda: box, allow_from=ALLOW)
    result = src.intake(since=None)

    assert result.captured == 2 and result.errors == 1
    assert result.considered == 3


def test_an_empty_fetch_is_an_error_not_a_crash():
    box = FakeMailbox({b"1": b""})
    src = BrokerMailSource(fresh_repo(), lambda: box, allow_from=ALLOW)
    result = src.intake(since=None)
    assert result.errors == 1 and result.captured == 0


def test_the_connection_is_released_even_on_the_happy_path():
    src, _, box = source_over({b"1": mail()})
    src.intake(since=None)
    assert box.closed == 1


# ---------------------------------------------------------------------------
# FR-BM-BACKFILL — one code path, idempotent
# ---------------------------------------------------------------------------

def test_backfill_walks_the_whole_mailbox_when_no_date_is_given():
    src, repo, box = source_over({
        b"1": mail(message_id="<old@tcbs.com.vn>"),
        b"2": mail(message_id="<new@tcbs.com.vn>"),
    })
    result = src.backfill()

    assert result["captured"] == 2
    assert box.searched == [None]          # ALL, not a window


def test_backfill_from_a_date_searches_from_that_date():
    box = FakeMailbox(
        {b"1": mail(message_id="<old@tcbs.com.vn>"),
         b"2": mail(message_id="<new@tcbs.com.vn>")},
        received={b"1": date(2025, 1, 5), b"2": date(2026, 9, 21)},
    )
    src = BrokerMailSource(fresh_repo(), lambda: box, allow_from=ALLOW)
    result = src.backfill(since=date(2026, 1, 1))

    assert result["captured"] == 1 and result["considered"] == 1
    assert box.searched == [date(2026, 1, 1)]


def test_backfill_is_idempotent_so_re_running_is_free():
    src, repo, _ = source_over({
        b"1": mail(message_id="<a@tcbs.com.vn>"),
        b"2": mail(message_id="<b@tcbs.com.vn>"),
    })
    first = src.backfill()
    second = src.backfill()

    assert first["captured"] == 2 and first["duplicates"] == 0
    assert second["captured"] == 0 and second["duplicates"] == 2
    assert repo.stats()["stored"] == 2


@pytest.mark.asyncio
async def test_a_scheduled_tick_looks_back_a_window_not_at_unseen_flags():
    """The folder is opened read-only, so intake must not depend on \\Seen — a window
    plus dedupe is both cheaper to reason about and immune to another client's reads."""
    box = FakeMailbox({b"1": mail()}, received={b"1": date(2026, 9, 21)})
    src = BrokerMailSource(fresh_repo(), lambda: box, allow_from=ALLOW, lookback_days=7)
    await src.tick(today=date(2026, 9, 22))

    assert box.searched == [date(2026, 9, 15)]


def test_imap_date_is_locale_independent():
    """strftime('%b') follows the container's locale; the search literal must not."""
    assert imap_date(date(2026, 9, 21)) == "21-Sep-2026"
    assert imap_date(date(2026, 1, 5)) == "05-Jan-2026"
    assert imap_date(date(2026, 12, 31)) == "31-Dec-2026"


# ---------------------------------------------------------------------------
# The repository contract
# ---------------------------------------------------------------------------

def test_mark_extracted_is_the_only_mutation_the_table_allows():
    src, repo, _ = source_over({b"1": mail()})
    src.intake(since=None)
    row = repo.list_recent()[0]

    assert row.extracted_at is None
    assert repo.list_unextracted()[0].mail_id == row.mail_id
    assert repo.mark_extracted(row.mail_id) is True
    assert repo.get(row.mail_id).extracted_at is not None
    assert repo.list_unextracted() == []
    assert repo.stats()["unextracted"] == 0
    assert repo.mark_extracted("not-a-real-mail-id") is False


def test_an_oversized_header_is_truncated_to_fit_rather_than_losing_the_mail():
    """The column widths come from RFC ceilings, but a non-conforming sender must still
    be captured — raw_mime keeps the untruncated truth either way."""
    long_subject = "x" * 2000
    raw = mail(message_id="<" + "y" * 600 + "@tcbs.com.vn>", subject=long_subject)
    src, repo, _ = source_over({b"1": raw})
    result = src.intake(since=None)

    assert result.captured == 1
    row = repo.list_recent()[0]
    assert len(row.message_id) == 512 and len(row.subject) == 998
    assert row.raw_mime.encode("latin-1") == raw   # nothing lost where it matters
