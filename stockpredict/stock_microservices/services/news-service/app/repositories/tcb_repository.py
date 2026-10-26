"""TcbRepository — the only writer of the pasted-TCBS-mail tables.

Insert-if-absent on `content_hash`, mirroring NewsRepository's contract (EC-N2): pasting
the same email twice returns the row that already exists rather than creating a second
session. Parent and children are written in one transaction — a half-saved mail, with
market internals but no recommendations, would be worse than no row at all (EC-B10).
"""
from __future__ import annotations

import hashlib
import logging
import re
from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import select, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from app.ingest.tcb_mail_parser import ParsedMail
from app.models.domain import Base
from app.models.tcb_news import TcbNews, TcbNewsCompany, TcbNewsReco  # noqa: F401 (mapper registration)

logger = logging.getLogger(__name__)

PARSER_VERSION = "1"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def content_hash(raw: str) -> str:
    """Stable dedupe key over the *meaning* of the paste.

    Whitespace is collapsed first so that re-pasting the same mail from a different
    client — which reflows line breaks and trailing spaces — is still recognised as the
    same email rather than landing as a second session.
    """
    normalised = re.sub(r"\s+", " ", (raw or "")).strip()
    return hashlib.sha256(normalised.encode("utf-8")).hexdigest()


# Parent columns that come straight off the parse result, name for name.
_PARSED_FIELDS = (
    "vnindex_close", "vnindex_change_pct", "vnindex_change_pts",
    "matched_value_bn", "matched_volume_m", "putthrough_bn", "total_value_bn",
    "foreign_net_bn", "foreign_buy_bn", "foreign_sell_bn",
    "foreign_top_buy", "foreign_top_sell", "foreign_ytd_net_bn",
    "ma5", "ma10", "ma20", "ma50", "support_txt", "resistance_txt",
    "reports_txt", "market_txt", "liquidity_txt", "foreign_txt", "technical_txt",
    "macro_domestic_txt", "macro_intl_txt",
)


class TcbRepository:
    def __init__(self, engine: Engine):
        self._engine = engine
        self._Session = sessionmaker(bind=engine, expire_on_commit=False)

    def ensure_schema(self) -> None:
        """Create the three tables if absent. Shares `Base` with news_events, so the
        news repository's `_ensure_database()` has already created the database."""
        Base.metadata.create_all(self._engine)
        self._ensure_reco_columns()

    def _ensure_reco_columns(self) -> None:
        """Add columns that outgrew the original `tcb_news_reco` — the FR-BM-SCORE marks
        and the Backlog #55 correction provenance.

        `create_all` creates missing tables but never alters an existing one, so a
        database that already stored calls would otherwise be missing every return
        column. Each add is guarded by information_schema, so a reboot is a no-op.
        MySQL only — a fresh sqlite (tests) always comes from `create_all`.
        """
        if not self._engine.dialect.name.startswith("mysql"):
            return
        columns = {
            "ref_date": "DATE NULL",
            "ref_close": "DOUBLE NULL",
            "ret_1d": "DOUBLE NULL",
            "ret_5d": "DOUBLE NULL",
            "ret_20d": "DOUBLE NULL",
            "ret_60d": "DOUBLE NULL",
            "ret_1d_vs_index": "DOUBLE NULL",
            "ret_5d_vs_index": "DOUBLE NULL",
            "ret_20d_vs_index": "DOUBLE NULL",
            "ret_60d_vs_index": "DOUBLE NULL",
            "ret_adjusted": "TINYINT(1) NOT NULL DEFAULT 0",
            "scored_at": "DATETIME NULL",
            "scoring_done": "TINYINT(1) NOT NULL DEFAULT 0",
            # Operator corrections (Backlog #55).
            "corrected_fields": "VARCHAR(128) NULL",
            "corrected_at": "DATETIME NULL",
        }
        with self._engine.begin() as conn:
            for column, ddl in columns.items():
                try:
                    present = conn.execute(text(
                        "SELECT COUNT(*) FROM information_schema.COLUMNS "
                        "WHERE TABLE_SCHEMA = DATABASE() "
                        "AND TABLE_NAME = 'tcb_news_reco' AND COLUMN_NAME = :col"
                    ), {"col": column}).scalar()
                    if present:
                        continue
                    conn.execute(text(f"ALTER TABLE tcb_news_reco ADD COLUMN {column} {ddl}"))
                    logger.info("Added tcb_news_reco.%s", column)
                except Exception as exc:  # noqa: BLE001
                    logger.warning("tcb_news_reco.%s migration skipped: %s", column, exc)

    # -- reads ---------------------------------------------------------------

    def get_by_hash(self, digest: str) -> Optional[TcbNews]:
        with self._Session() as s:
            return s.execute(
                select(TcbNews).where(TcbNews.content_hash == digest)
            ).scalar_one_or_none()

    def get(self, mail_id: int) -> Optional[TcbNews]:
        with self._Session() as s:
            return s.get(TcbNews, mail_id)

    def list(
        self,
        *,
        since: Optional[date] = None,
        until: Optional[date] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[TcbNews]:
        """Newest session first — the operator reads today's mail, not the archive's."""
        with self._Session() as s:
            q = select(TcbNews)
            if since is not None:
                q = q.where(TcbNews.session_date >= since)
            if until is not None:
                q = q.where(TcbNews.session_date <= until)
            q = q.order_by(TcbNews.session_date.desc(), TcbNews.id.desc())
            return list(s.execute(q.limit(limit).offset(offset)).scalars().all())

    def list_recos(
        self,
        *,
        symbol: Optional[str] = None,
        action: Optional[str] = None,
        limit: int = 100,
    ) -> list[tuple[TcbNewsReco, date]]:
        """The call ledger, newest first, each paired with its session date."""
        with self._Session() as s:
            q = select(TcbNewsReco, TcbNews.session_date).join(
                TcbNews, TcbNewsReco.tcb_news_id == TcbNews.id)
            if symbol:
                q = q.where(TcbNewsReco.symbol == symbol.upper())
            if action:
                q = q.where(TcbNewsReco.action == action.upper())
            q = q.order_by(TcbNews.session_date.desc(), TcbNewsReco.id.desc()).limit(limit)
            return [(row[0], row[1]) for row in s.execute(q).all()]

    # -- writes --------------------------------------------------------------

    def save(
        self,
        parsed: ParsedMail,
        *,
        raw: str,
        session_date: date,
        subject: Optional[str] = None,
        created_by: Optional[int] = None,
    ) -> tuple[TcbNews, bool]:
        """Persist one parsed mail. Returns (row, created).

        `created` is False when this exact content was already stored — the caller gets
        the existing row back instead of a duplicate session (FR-BM-DEDUP).
        """
        digest = content_hash(raw)
        existing = self.get_by_hash(digest)
        if existing is not None:
            return existing, False

        row = TcbNews(
            session_date=session_date,
            source="tcbs.daily",
            lang=parsed.lang,
            subject=subject,
            raw_content=raw,
            content_hash=digest,
            parser_version=PARSER_VERSION,
            created_by=created_by,
            created_at=_utcnow(),
        )
        for name in _PARSED_FIELDS:
            setattr(row, name, getattr(parsed, name))
        row.companies = [
            TcbNewsCompany(symbol=c.symbol.upper(), item_text=c.item_text)
            for c in parsed.companies
        ]
        row.recos = [
            TcbNewsReco(
                symbol=r.symbol.upper(),
                action=r.action,
                label_verbatim=r.label_verbatim,
                rationale=r.rationale,
                target_price=r.target_price,
                pushed_to_watchlist=False,
                # Provenance for anything a human overrode in the preview (#55). NULL
                # when the parser's reading stands, so a reparse can tell the two apart.
                corrected_fields=(",".join(r.corrected_fields) or None),
                corrected_at=(_utcnow() if r.corrected_fields else None),
            )
            for r in parsed.recos
        ]

        with self._Session() as s:
            s.add(row)
            s.commit()
            s.refresh(row)
            _ = row.companies, row.recos  # force the selectin load before detaching
        logger.info("stored TCB mail session=%s recos=%d companies=%d",
                    session_date, len(row.recos), len(row.companies))
        return row, True

    def mark_pushed(self, reco_ids: list[int]) -> int:
        """Stamp the recommendations that reached the watchlist (FR-BM-CALLS)."""
        if not reco_ids:
            return 0
        with self._Session() as s:
            rows = s.execute(
                select(TcbNewsReco).where(TcbNewsReco.id.in_(reco_ids))
            ).scalars().all()
            for r in rows:
                r.pushed_to_watchlist = True
                r.pushed_at = _utcnow()
            s.commit()
            return len(rows)

    # -- scoring (FR-BM-SCORE) -----------------------------------------------

    def list_unscored(self, *, limit: int = 500) -> list[tuple[TcbNewsReco, date]]:
        """Calls with a horizon still to fill, oldest session first.

        `scoring_done` is the stop flag — without it a delisted symbol would be
        re-fetched on every tick forever. Oldest-first so the calls closest to
        completing a horizon are handled before any per-tick limit bites.
        """
        with self._Session() as s:
            q = (
                select(TcbNewsReco, TcbNews.session_date)
                .join(TcbNews, TcbNewsReco.tcb_news_id == TcbNews.id)
                .where(TcbNewsReco.scoring_done.is_(False))
                .order_by(TcbNews.session_date.asc(), TcbNewsReco.id.asc())
                .limit(limit)
            )
            return [(row[0], row[1]) for row in s.execute(q).all()]

    def save_score(self, reco_id: int, score, *, scoring_done: bool = False) -> None:
        """Write one call's marks. Only non-None horizons are written, so a later tick
        filling ret_60d never blanks the ret_1d an earlier tick already established."""
        with self._Session() as s:
            row = s.get(TcbNewsReco, reco_id)
            if row is None:
                return
            if score.ref_date is not None:
                row.ref_date = score.ref_date
                row.ref_close = score.ref_close
            for horizon, value in score.returns.items():
                if value is not None:
                    setattr(row, f"ret_{horizon}d", value)
            for horizon, value in score.excess.items():
                if value is not None:
                    setattr(row, f"ret_{horizon}d_vs_index", value)
            row.ret_adjusted = bool(score.adjusted)
            row.scored_at = _utcnow()
            row.scoring_done = bool(scoring_done)
            s.commit()

    def mark_scoring_done(self, reco_id: int) -> None:
        """Retire a call we can no longer price (delisted / never tracked)."""
        with self._Session() as s:
            row = s.get(TcbNewsReco, reco_id)
            if row is None:
                return
            row.scoring_done = True
            row.scored_at = _utcnow()
            s.commit()

    def all_scored_calls(self) -> list[tuple[str | None, dict, dict, bool]]:
        """(action, {horizon: return}, {horizon: excess}, adjusted) for every stored
        call — the input to the track record (FR-BM-RECORD).

        `ret_adjusted` travels with the marks rather than being left in the table for
        someone to remember to check (Backlog #60): it is what tells `build_record` that
        a call was priced off a raw series and so carries a share-count event as a
        return. Reading it here is the only reason the flag is load-bearing instead of
        decorative.
        """
        with self._Session() as s:
            rows = s.execute(select(TcbNewsReco)).scalars().all()
            return [
                (
                    r.action,
                    {h: getattr(r, f"ret_{h}d") for h in (1, 5, 20, 60)},
                    {h: getattr(r, f"ret_{h}d_vs_index") for h in (1, 5, 20, 60)},
                    bool(r.ret_adjusted),
                )
                for r in rows
            ]

    def delete(self, mail_id: int) -> bool:
        """Remove one stored mail together with its companies and recommendations.

        The children go via the ORM's delete-orphan cascade rather than the database's,
        because sqlite (used in tests) does not enforce ON DELETE CASCADE unless foreign
        keys are explicitly switched on — this way both backends behave identically.
        """
        with self._Session() as s:
            row = s.get(TcbNews, mail_id)
            if row is None:
                return False
            s.delete(row)
            s.commit()
            return True
