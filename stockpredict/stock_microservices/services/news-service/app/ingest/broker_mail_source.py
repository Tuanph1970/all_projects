"""ingest/ BrokerMailSource — capture broker mail over IMAP (FR-BM-INTAKE, FR-BM-DEDUP,
FR-BM-BACKFILL; EC-B1, EC-B2).

Phase E1 of SRS_broker_mail, and it ships alone: **no parsing happens here.** Appendix E
is blunt about why — "every day spent designing the parser is a day of emails that may
become unrecoverable" — so this module's only job is to get messages into
`broker_mail_raw` intact, and its only real failure mode is declining to store something
it should have stored.

Four rules the implementation exists to enforce:

1. **Capture is permissive; filtering is not capture's job.** Only the *sender*
   allow-list (Appendix B, EC-B1) gates intake. The registry also records a subject
   pattern, and it is deliberately NOT applied here: Appendix D warns the format drifts,
   and a subject filter turns a drift into silently lost mail, which EC-B2 says is the
   one unrecoverable outcome. Subject matching belongs to E2, where a mismatch
   quarantines loudly instead of dropping quietly.

2. **`mail_id = sha256(Message-ID)`, and the primary key is the dedupe.** Insert if
   absent; re-seeing a message is a no-op, never an update (FR-BM-DEDUP). This is what
   makes one code path serve both the scheduled tick and the one-shot backfill, and what
   makes re-running a backfill free.

3. **Raw MIME is stored byte-exact.** The column is TEXT per SRS §4.1, so the bytes are
   decoded `latin-1` — which is byte-transparent, so `row.raw_mime.encode("latin-1")`
   returns the original message exactly. A UTF-8 decode with `errors="replace"` would be
   lossy, and a lossy archive cannot satisfy EC-B2's promise that a parser fix replays
   over the whole archive. `subject` is separately decoded per RFC 2047 so a human has
   something readable; `raw_mime` is for machines and is never prettied up.

4. **It never raises into the scheduler.** A network drop, a bad password, one unparseable
   message — all are logged and retried on the next tick. A mailbox outage must not stop
   the service, and one bad message must not abandon the rest of the batch.
"""
from __future__ import annotations

import email
import hashlib
import imaplib
import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from email.header import decode_header, make_header
from email.utils import parseaddr, parsedate_to_datetime
from fnmatch import fnmatch
from typing import Callable, Iterable, Optional, Protocol

logger = logging.getLogger(__name__)

# Appendix B, key `tcbs.daily`. The forwarding address is deployment-specific — a Gmail
# filter on from:tcbs.com.vn forwards into the ingestion mailbox and rewrites `From` to
# the forwarder — so it is configured, not hardcoded.
DEFAULT_SOURCE_KEY = "tcbs.daily"
DEFAULT_ALLOW_FROM: tuple[str, ...] = ("*@tcbs.com.vn",)

# IMAP wants DD-Mon-YYYY with English month names. strftime("%b") is locale-dependent and
# the container's locale is not ours to assume, so the table is explicit.
_IMAP_MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
                "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def imap_date(d: date) -> str:
    """`date` -> the IMAP SEARCH date literal, locale-independently."""
    return f"{d.day:02d}-{_IMAP_MONTHS[d.month - 1]}-{d.year}"


def mail_id_for(message_id: str) -> str:
    """`sha256(Message-ID)` (FR-BM-DEDUP) — stable across re-parse, by construction.

    The header is stripped but otherwise untouched: Message-ID is a case-sensitive
    opaque token, so normalising its case could merge two genuinely different messages.
    """
    return hashlib.sha256((message_id or "").strip().encode("utf-8")).hexdigest()


def synthetic_message_id(raw: bytes) -> str:
    """A stand-in Message-ID for mail that arrived without one.

    RFC 5322 says SHOULD, not MUST, so a message with no Message-ID is legal and rare.
    Dropping it would violate rule 1 (capture is permissive); giving it a random id would
    break rule 2, because the next poll would store it again. Hashing the message bytes
    is stable, so re-seeing the same message is still a no-op, and the `synthetic-`
    prefix means a human can always tell a surrogate from a real header.
    """
    return f"synthetic-{hashlib.sha256(raw).hexdigest()}@broker-mail.local"


def sender_allowed(sender: str, patterns: Iterable[str]) -> bool:
    """EC-B1's allow-list. Glob patterns, so `*@tcbs.com.vn` covers the whole domain.

    Matching is case-insensitive on the address only — a display name is attacker-chosen
    and must never widen the allow-list.
    """
    address = (sender or "").strip().lower()
    if not address:
        return False
    return any(fnmatch(address, (p or "").strip().lower()) for p in patterns if p)


def decode_subject(value: Optional[str]) -> Optional[str]:
    """RFC 2047 -> text. TCBS subjects are Vietnamese, so they arrive encoded."""
    if not value:
        return None
    try:
        return str(make_header(decode_header(value)))
    except Exception:  # noqa: BLE001 — a malformed header must not cost us the message
        return value


def received_utc_of(message, *, fallback: datetime) -> datetime:
    """The mail's Date header in UTC, or `fallback` when it is missing or malformed.

    Never None: a NULL would break both ordering and "backfill since <date>", and a
    message with a broken Date still has to be captured (rule 1).
    """
    raw = message.get("Date")
    if not raw:
        return fallback
    try:
        parsed = parsedate_to_datetime(raw)
    except Exception:  # noqa: BLE001
        return fallback
    if parsed is None:
        return fallback
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


# ---------------------------------------------------------------------------
# The mailbox port — the only thing that touches the network
# ---------------------------------------------------------------------------

class Mailbox(Protocol):
    """Narrow port so intake is testable without an IMAP server or a network."""

    def search_since(self, since: Optional[date]) -> list[bytes]: ...
    def fetch(self, uid: bytes) -> Optional[bytes]: ...
    def close(self) -> None: ...


class ImapMailbox:
    """`Mailbox` over imaplib. Constructed per tick: a long-lived IMAP connection is the
    thing that goes stale silently, and reconnecting costs far less than diagnosing one."""

    def __init__(self, host: str, user: str, password: str, *,
                 port: int = 993, folder: str = "INBOX", timeout: float = 30.0):
        self._conn = imaplib.IMAP4_SSL(host, port, timeout=timeout)
        self._conn.login(user, password)
        # readonly: intake must not touch \Seen. The flags belong to whoever reads the
        # mailbox, and mutating them would make our own "what is new" unreliable.
        self._conn.select(folder, readonly=True)

    def search_since(self, since: Optional[date]) -> list[bytes]:
        criteria = ("SINCE", imap_date(since)) if since else ("ALL",)
        status, data = self._conn.search(None, *criteria)
        if status != "OK" or not data or data[0] is None:
            return []
        return data[0].split()

    def fetch(self, uid: bytes) -> Optional[bytes]:
        status, data = self._conn.fetch(uid, "(RFC822)")
        if status != "OK" or not data:
            return None
        for part in data:
            # imaplib yields a tuple (header, payload) for the body and bare bytes for
            # the closing paren; the payload is the one we want.
            if isinstance(part, tuple) and len(part) > 1 and isinstance(part[1], bytes):
                return part[1]
        return None

    def close(self) -> None:
        for step in (self._conn.close, self._conn.logout):
            try:
                step()
            except Exception:  # noqa: BLE001 — teardown must not mask a real error
                pass


# ---------------------------------------------------------------------------
# Intake
# ---------------------------------------------------------------------------

@dataclass
class IntakeResult:
    """What one intake pass did — surfaced by POST /news/broker/poll and the metrics log."""

    considered: int = 0
    captured: int = 0
    duplicates: int = 0
    rejected: int = 0          # failed the sender allow-list (EC-B1) — not an error
    errors: int = 0            # one message we could not process; the batch continued
    failed: bool = False       # the pass itself could not run (network/auth)
    detail: str = ""
    senders_rejected: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "considered": self.considered,
            "captured": self.captured,
            "duplicates": self.duplicates,
            "rejected": self.rejected,
            "errors": self.errors,
            "failed": self.failed,
            "detail": self.detail,
            "senders_rejected": sorted(set(self.senders_rejected))[:20],
        }


class BrokerMailSource:
    """Scheduled job: capture every allow-listed message the mailbox will show us."""

    def __init__(
        self,
        repo,
        mailbox_factory: Callable[[], Mailbox],
        *,
        allow_from: Iterable[str] = DEFAULT_ALLOW_FROM,
        source_key: str = DEFAULT_SOURCE_KEY,
        lookback_days: int = 7,
    ):
        self._repo = repo
        self._mailbox_factory = mailbox_factory
        self._allow = [p for p in allow_from if p]
        self._source_key = source_key
        self._lookback_days = max(1, lookback_days)

    async def tick(self, *, today: Optional[date] = None) -> dict:
        """One scheduled pass: the recent window only. Never raises (rule 4).

        A window rather than UNSEEN, because we select the folder read-only and must not
        depend on flags another client can change. Dedupe makes the overlap free, so the
        window only has to be wider than the longest plausible outage.
        """
        today = today or datetime.now(timezone.utc).date()
        since = today - timedelta(days=self._lookback_days)
        return self.intake(since=since).as_dict()

    def backfill(self, *, since: Optional[date] = None) -> dict:
        """FR-BM-BACKFILL: the one-shot walk, from `since` or the whole mailbox.

        Deliberately the same code path as `tick` — idempotent by FR-BM-DEDUP, so it is
        safe to re-run, and there is no second implementation to drift.
        """
        return self.intake(since=since).as_dict()

    def intake(self, *, since: Optional[date]) -> IntakeResult:
        """Capture everything at or after `since` (or everything, if None)."""
        result = IntakeResult()
        try:
            mailbox = self._mailbox_factory()
        except Exception as exc:  # noqa: BLE001
            # Auth or network. Logged, not raised: the next tick retries, and a mailbox
            # outage must not take the service down with it.
            result.failed = True
            result.detail = f"mailbox unavailable: {exc}"
            logger.warning("broker mail intake could not open the mailbox: %s", exc)
            return result

        try:
            try:
                uids = mailbox.search_since(since)
            except Exception as exc:  # noqa: BLE001
                result.failed = True
                result.detail = f"search failed: {exc}"
                logger.warning("broker mail search failed: %s", exc)
                return result

            result.considered = len(uids)
            for uid in uids:
                try:
                    self._capture_one(uid, mailbox, result)
                except Exception as exc:  # noqa: BLE001
                    # One bad message must not abandon the rest of the batch.
                    result.errors += 1
                    logger.warning("broker mail: skipping uid %r: %s", uid, exc)
        finally:
            try:
                mailbox.close()
            except Exception:  # noqa: BLE001
                pass

        logger.info("broker mail intake: %s", result.as_dict())
        return result

    def _capture_one(self, uid: bytes, mailbox: Mailbox, result: IntakeResult) -> None:
        raw = mailbox.fetch(uid)
        if not raw:
            result.errors += 1
            logger.warning("broker mail: empty fetch for uid %r", uid)
            return

        message = email.message_from_bytes(raw)
        sender = (parseaddr(message.get("From") or "")[1] or "").strip()
        if not sender_allowed(sender, self._allow):
            # EC-B1: ignored without error. Not a failure — the ingestion mailbox may
            # legitimately receive mail we have no business storing.
            result.rejected += 1
            result.senders_rejected.append(sender or "<no From>")
            return

        header_id = (message.get("Message-ID") or "").strip()
        message_id = header_id or synthetic_message_id(raw)
        if not header_id:
            logger.info("broker mail: no Message-ID from %s; using %s", sender, message_id)

        inserted = self._repo.insert_if_absent(
            mail_id=mail_id_for(message_id),
            message_id=message_id,
            sender=sender,
            subject=decode_subject(message.get("Subject")),
            received_utc=received_utc_of(message, fallback=datetime.now(timezone.utc)),
            # latin-1 is byte-transparent, so this round-trips exactly (rule 3).
            raw_mime=raw.decode("latin-1"),
            source=self._source_key,
        )
        if inserted:
            result.captured += 1
        else:
            result.duplicates += 1
