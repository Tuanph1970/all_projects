"""SQLAlchemy models for the pasted TCBS daily mail (FR-BM-MARKET, FR-BM-CALLS).

Three tables, one parent and two children, in the existing `stock_news` database:

  tcb_news          one row per email — the single market section, plus the raw text
  tcb_news_company  the "Tin doanh nghiệp" items, one row per company
  tcb_news_reco     the section-3 recommendations, one row per call

The children exist because an email carries *many* companies and may carry many
recommendations; flattening them onto the parent would cap how many a day can hold and
make "every TCB call on HPG" unanswerable.

Units are named on every column (EC-B5): `_bn` is VND billion exactly as the mail prints
it, `_m` is millions of shares, index levels are points. Nothing is converted on the way
in — conversion happens once, at the point of use.

`raw_content` is the pasted text, stored verbatim and never mutated (EC-B2), so a parser
fix can be replayed over the whole archive without asking the operator to paste again.

Portable across MySQL (prod) and sqlite (tests), matching `domain.py` in this package.
"""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.mysql import MEDIUMTEXT
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.domain import Base

# Large text on MySQL, plain TEXT elsewhere (sqlite in tests).
_LongText = Text().with_variant(MEDIUMTEXT, "mysql")


class TcbNews(Base):
    """One pasted TCBS daily email."""

    __tablename__ = "tcb_news"
    __table_args__ = (
        # Pasting the same mail twice is a no-op, not a duplicate session (FR-BM-DEDUP).
        UniqueConstraint("content_hash", name="uq_tcb_news_content_hash"),
        Index("ix_tcb_news_session_date", "session_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # The trading session the mail DESCRIBES, not the day it was pasted — they differ.
    # The parser proposes it; the operator confirms it in the preview before saving.
    session_date: Mapped[date] = mapped_column(Date, nullable=False)
    source: Mapped[str] = mapped_column(String(64), default="tcbs.daily", nullable=False)
    lang: Mapped[str | None] = mapped_column(String(8), nullable=True)      # "vi" | "en"
    subject: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # --- Thị trường chung / General Market ---------------------------------
    vnindex_close: Mapped[float | None] = mapped_column(Float, nullable=True)       # points
    vnindex_change_pct: Mapped[float | None] = mapped_column(Float, nullable=True)  # signed %
    vnindex_change_pts: Mapped[float | None] = mapped_column(Float, nullable=True)  # signed points

    # --- Thanh khoản / Liquidity -------------------------------------------
    matched_value_bn: Mapped[float | None] = mapped_column(Float, nullable=True)   # khớp lệnh
    matched_volume_m: Mapped[float | None] = mapped_column(Float, nullable=True)   # million shares
    putthrough_bn: Mapped[float | None] = mapped_column(Float, nullable=True)      # thỏa thuận
    total_value_bn: Mapped[float | None] = mapped_column(Float, nullable=True)

    # --- Khối ngoại / Foreign trading (negative = net sell) ----------------
    foreign_net_bn: Mapped[float | None] = mapped_column(Float, nullable=True)
    foreign_buy_bn: Mapped[float | None] = mapped_column(Float, nullable=True)
    foreign_sell_bn: Mapped[float | None] = mapped_column(Float, nullable=True)
    foreign_top_buy: Mapped[str | None] = mapped_column(String(255), nullable=True)   # "MCH, VPB, …"
    foreign_top_sell: Mapped[str | None] = mapped_column(String(255), nullable=True)
    foreign_ytd_net_bn: Mapped[float | None] = mapped_column(Float, nullable=True)

    # --- Kỹ thuật / Technicals ---------------------------------------------
    ma5: Mapped[float | None] = mapped_column(Float, nullable=True)
    ma10: Mapped[float | None] = mapped_column(Float, nullable=True)
    ma20: Mapped[float | None] = mapped_column(Float, nullable=True)
    ma50: Mapped[float | None] = mapped_column(Float, nullable=True)
    support_txt: Mapped[str | None] = mapped_column(Text, nullable=True)
    resistance_txt: Mapped[str | None] = mapped_column(Text, nullable=True)

    # --- Section text kept verbatim (what the regexes did not reduce) ------
    reports_txt: Mapped[str | None] = mapped_column(Text, nullable=True)        # section 1
    market_txt: Mapped[str | None] = mapped_column(Text, nullable=True)
    liquidity_txt: Mapped[str | None] = mapped_column(Text, nullable=True)
    foreign_txt: Mapped[str | None] = mapped_column(Text, nullable=True)
    technical_txt: Mapped[str | None] = mapped_column(Text, nullable=True)
    macro_domestic_txt: Mapped[str | None] = mapped_column(Text, nullable=True)
    macro_intl_txt: Mapped[str | None] = mapped_column(Text, nullable=True)

    # --- Provenance ---------------------------------------------------------
    raw_content: Mapped[str] = mapped_column(_LongText, nullable=False)   # immutable, EC-B2
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)  # sha256 of normalised raw
    parser_version: Mapped[str | None] = mapped_column(String(16), nullable=True)
    created_by: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)  # user_id
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    companies: Mapped[list["TcbNewsCompany"]] = relationship(
        back_populates="mail", cascade="all, delete-orphan", lazy="selectin",
    )
    recos: Mapped[list["TcbNewsReco"]] = relationship(
        back_populates="mail", cascade="all, delete-orphan", lazy="selectin",
    )


class TcbNewsCompany(Base):
    """One "MSN: …" item from the corporate-news section."""

    __tablename__ = "tcb_news_company"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tcb_news_id: Mapped[int] = mapped_column(
        ForeignKey("tcb_news.id", ondelete="CASCADE"), nullable=False, index=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    item_text: Mapped[str] = mapped_column(Text, nullable=False)

    mail: Mapped[TcbNews] = relationship(back_populates="companies")


class TcbNewsReco(Base):
    """One section-3 recommendation — the row that feeds the watch screen."""

    __tablename__ = "tcb_news_reco"
    __table_args__ = (
        Index("ix_tcb_news_reco_symbol_action", "symbol", "action"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tcb_news_id: Mapped[int] = mapped_column(
        ForeignKey("tcb_news.id", ondelete="CASCADE"), nullable=False, index=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, index=True)

    # Normalised: BUY | SELL | HOLD | WATCH, or NULL when TCBS used wording we do not
    # yet map. `label_verbatim` always carries the original phrase (EC-B4) — a NULL
    # action is a prompt to extend the map, never a reason to discard the row.
    action: Mapped[str | None] = mapped_column(String(8), nullable=True)
    label_verbatim: Mapped[str] = mapped_column(String(128), nullable=False)
    rationale: Mapped[str | None] = mapped_column(_LongText, nullable=True)
    target_price: Mapped[float | None] = mapped_column(Float, nullable=True)

    # True once this call has been written to the operator's watchlist (FR-BM-CALLS).
    pushed_to_watchlist: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    pushed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # --- Forward-return scoring (FR-BM-SCORE) ------------------------------
    # Returns are fractions (0.031 = +3.1%) over 1/5/20/60 *trading sessions* from the
    # call's session close. A horizon that has not yet elapsed stays NULL — there is no
    # partial fill, because a shortened horizon flatters the desk.
    #
    # `*_vs_index` is the excess over the index across the SAME two dates, which is the
    # benchmark EC-B7 requires a call to beat before it may influence anything.
    ref_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    ref_close: Mapped[float | None] = mapped_column(Float, nullable=True)
    ret_1d: Mapped[float | None] = mapped_column(Float, nullable=True)
    ret_5d: Mapped[float | None] = mapped_column(Float, nullable=True)
    ret_20d: Mapped[float | None] = mapped_column(Float, nullable=True)
    ret_60d: Mapped[float | None] = mapped_column(Float, nullable=True)
    ret_1d_vs_index: Mapped[float | None] = mapped_column(Float, nullable=True)
    ret_5d_vs_index: Mapped[float | None] = mapped_column(Float, nullable=True)
    ret_20d_vs_index: Mapped[float | None] = mapped_column(Float, nullable=True)
    ret_60d_vs_index: Mapped[float | None] = mapped_column(Float, nullable=True)

    # True when prices used were split/dividend adjusted. False means raw closes, so a
    # corporate action inside the window shows up as a return that never happened —
    # the caller is told rather than left to assume.
    ret_adjusted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    scored_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Set once every horizon is filled, or the call is too old to ever fill one.
    scoring_done: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    mail: Mapped[TcbNews] = relationship(back_populates="recos")
