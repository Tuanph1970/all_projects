"""
Which sources sellers want that we cannot read yet.

The counterpart to comparables.py. That module records what happened to hosts
we DO support; this one records the hosts we turned away, because the refusal
path in `POST /comparables` is where the demand signal lives and it used to end
in an HTTPException with nothing written down.

Reading it back is `worklist()`, and the ranking it applies is the whole point:
distinct sellers first, attempts second. See RejectedHostRequest for why that
order and not the reverse.
"""
import ipaddress
import logging
from datetime import datetime, timezone

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from shared.models.intel import (
    ComparableObservation, RejectedHostRequest, TrackedComparable,
)

from app.services import adapters, comparables

logger = logging.getLogger(__name__)

MAX_SAMPLE_URL = 1000


def _is_candidate_source(host: str) -> bool:
    """
    Is this host something a human could plausibly write an adapter for?

    Needed because check_url runs the allowlist BEFORE the address check, so
    `http://169.254.169.254/latest/meta-data/` and `http://db:3306` both arrive
    here as HOST_NOT_ALLOWED -- the same status as `sendo.vn`. Recording them
    would fill the worklist with SSRF probe targets and internal service names,
    and the worklist's only purpose is to be a list a human works down. A
    prompt to allowlist `db` is the last thing it should contain.

    Two cheap rules, no network:
      - an IP literal is never a source; a marketplace has a name
      - a dotless host is an internal name (`db`, `traefik`, `localhost`)

    A registered domain whose DNS points somewhere private still gets counted.
    That is accepted: it is a name on a report someone reads, it cannot be
    allowlisted without a deliberate edit, and resolving here would put a DNS
    lookup on a telemetry path that must stay cheap and must never raise.
    """
    if not host or "." not in host:
        return False
    try:
        ipaddress.ip_address(host)
    except ValueError:
        return True  # not an IP literal, so a real name
    return False


def record_rejection(db: Session, *, seller_id: int, url: str) -> None:
    """
    Note that `seller_id` asked for an unsupported host.

    TELEMETRY class: this must never turn a clear "we don't support this site"
    message into a 500, so every failure path here is swallowed and logged. The
    caller is already on its way to raising a 422 and that 422 is the part the
    seller needs.

    The host is derived here rather than taken from the caller because
    check_url raises before it returns one -- and `host_of` normalises, which
    is what keeps `www.sendo.vn` and `sendo.vn` from becoming two entries in a
    list whose only job is to be counted.
    """
    try:
        host = comparables.host_of(url)
        if not _is_candidate_source(host):
            return

        now = datetime.now(timezone.utc)
        row = (
            db.query(RejectedHostRequest)
            .filter(
                RejectedHostRequest.host == host,
                RejectedHostRequest.seller_id == seller_id,
            )
            .first()
        )
        if row is not None:
            row.attempts = (row.attempts or 0) + 1
            row.last_seen_at = now
            row.sample_url = (url or "")[:MAX_SAMPLE_URL] or row.sample_url
            db.commit()
            return

        db.add(RejectedHostRequest(
            host=host,
            seller_id=seller_id,
            attempts=1,
            sample_url=(url or "")[:MAX_SAMPLE_URL] or None,
            first_seen_at=now,
            last_seen_at=now,
        ))
        db.commit()
    except IntegrityError:
        # Two tabs, same host, same second. The unique constraint is what makes
        # the grain (host, seller) true, so losing this race means the row now
        # exists and the retry below is the whole recovery.
        db.rollback()
        try:
            row = (
                db.query(RejectedHostRequest)
                .filter(
                    RejectedHostRequest.host == comparables.host_of(url),
                    RejectedHostRequest.seller_id == seller_id,
                )
                .first()
            )
            if row is not None:
                row.attempts = (row.attempts or 0) + 1
                row.last_seen_at = datetime.now(timezone.utc)
                db.commit()
        except Exception:
            logger.warning("Could not record rejected host after retry", exc_info=True)
            db.rollback()
    except Exception:
        logger.warning("Could not record rejected host", exc_info=True)
        db.rollback()


def unsupported_demand(db: Session):
    """
    Hosts we refuse, ranked by how many DIFFERENT sellers asked for them.

    Returns dicts rather than rows because the caller is a report, and because
    `sellers` and `attempts` are aggregates that belong to no single row.
    """
    rows = (
        db.query(
            RejectedHostRequest.host.label("host"),
            func.count(RejectedHostRequest.id).label("sellers"),
            func.sum(RejectedHostRequest.attempts).label("attempts"),
            func.min(RejectedHostRequest.first_seen_at).label("first_seen"),
            func.max(RejectedHostRequest.last_seen_at).label("last_seen"),
            func.max(RejectedHostRequest.sample_url).label("sample_url"),
        )
        .group_by(RejectedHostRequest.host)
        .order_by(
            func.count(RejectedHostRequest.id).desc(),
            func.sum(RejectedHostRequest.attempts).desc(),
        )
        .all()
    )
    return [
        {
            "host": r.host,
            "sellers": int(r.sellers or 0),
            "attempts": int(r.attempts or 0),
            "first_seen": r.first_seen,
            "last_seen": r.last_seen,
            "sample_url": r.sample_url,
        }
        for r in rows
    ]


def failing_supported_hosts(db: Session):
    """
    Allowlisted hosts whose latest observations are failing, by status.

    The other half of the worklist, and the one the design already called for:
    a host we support but cannot read is an adapter that needs writing or
    fixing, and `js_required` piling up on one host is the specific signal that
    the ladder has run out of rungs there.

    Counts every observation rather than only the latest per comparable: a host
    that failed a hundred times last month and works now should still show, with
    its dates, because "we fixed it" and "nobody has tried since" look identical
    from a snapshot.
    """
    rows = (
        db.query(
            TrackedComparable.source_host.label("host"),
            ComparableObservation.status.label("status"),
            func.count(ComparableObservation.id).label("n"),
            func.max(ComparableObservation.observed_at).label("last_seen"),
        )
        .join(TrackedComparable,
              TrackedComparable.id == ComparableObservation.comparable_id)
        .filter(ComparableObservation.status != "ok")
        .group_by(TrackedComparable.source_host, ComparableObservation.status)
        .order_by(func.count(ComparableObservation.id).desc())
        .all()
    )
    return [
        {
            "host": r.host,
            "status": r.status,
            "count": int(r.n or 0),
            "last_seen": r.last_seen,
        }
        for r in rows
    ]


def worklist(db: Session):
    """Both halves, plus what we already support, in one payload."""
    return {
        "supported_hosts": list(adapters.allowed_hosts()),
        "unsupported_demand": unsupported_demand(db),
        "failing_supported": failing_supported_hosts(db),
    }
