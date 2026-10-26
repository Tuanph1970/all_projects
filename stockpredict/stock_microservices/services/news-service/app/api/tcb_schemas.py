"""Request/response models for the pasted-TCBS-mail API (FR-BM-API)."""
from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


class TcbPreviewRequest(BaseModel):
    """Parse a pasted mail without storing anything."""

    content: str = Field(..., min_length=1, description="The pasted email body")
    reference_date: Optional[date] = Field(
        default=None,
        description="Day the mail was received; bounds the session-date guess. Defaults to today.",
    )


class RecoOut(BaseModel):
    id: Optional[int] = None
    symbol: str
    action: Optional[str]          # BUY | SELL | HOLD | WATCH | null
    label_verbatim: str            # exactly as TCBS wrote it (EC-B4)
    rationale: Optional[str] = None
    target_price: Optional[float] = None
    pushed_to_watchlist: bool = False

    # Forward-return marks (FR-BM-SCORE). Fractions, 0.031 = +3.1%, over trading
    # sessions. A horizon that has not yet elapsed is null, never a partial fill.
    ref_date: Optional[date] = None
    ref_close: Optional[float] = None
    ret_1d: Optional[float] = None
    ret_5d: Optional[float] = None
    ret_20d: Optional[float] = None
    ret_60d: Optional[float] = None
    ret_1d_vs_index: Optional[float] = None
    ret_5d_vs_index: Optional[float] = None
    ret_20d_vs_index: Optional[float] = None
    ret_60d_vs_index: Optional[float] = None
    ret_adjusted: bool = False     # False => raw closes; corporate actions distort
    scored_at: Optional[datetime] = None


class CompanyOut(BaseModel):
    id: Optional[int] = None
    symbol: str
    item_text: str


class TcbMailOut(BaseModel):
    """One mail, parsed or stored. `id` is null on a preview."""

    id: Optional[int] = None
    session_date: Optional[date] = None
    session_date_hint: Optional[date] = None
    source: str = "tcbs.daily"
    lang: Optional[str] = None
    subject: Optional[str] = None

    vnindex_close: Optional[float] = None
    vnindex_change_pct: Optional[float] = None
    vnindex_change_pts: Optional[float] = None

    matched_value_bn: Optional[float] = None
    matched_volume_m: Optional[float] = None
    putthrough_bn: Optional[float] = None
    total_value_bn: Optional[float] = None

    foreign_net_bn: Optional[float] = None
    foreign_buy_bn: Optional[float] = None
    foreign_sell_bn: Optional[float] = None
    foreign_top_buy: Optional[str] = None
    foreign_top_sell: Optional[str] = None
    foreign_ytd_net_bn: Optional[float] = None

    ma5: Optional[float] = None
    ma10: Optional[float] = None
    ma20: Optional[float] = None
    ma50: Optional[float] = None
    support_txt: Optional[str] = None
    resistance_txt: Optional[str] = None

    reports_txt: Optional[str] = None
    market_txt: Optional[str] = None
    liquidity_txt: Optional[str] = None
    foreign_txt: Optional[str] = None
    technical_txt: Optional[str] = None
    macro_domestic_txt: Optional[str] = None
    macro_intl_txt: Optional[str] = None

    companies: list[CompanyOut] = Field(default_factory=list)
    recos: list[RecoOut] = Field(default_factory=list)

    created_at: Optional[datetime] = None


class TcbSaveRequest(BaseModel):
    """Store a previewed mail and optionally push its calls to the watchlist."""

    content: str = Field(..., min_length=1)
    session_date: date = Field(
        ..., description="The trading session the mail describes — confirmed by the operator"
    )
    subject: Optional[str] = Field(default=None, max_length=512)
    push_symbols: Optional[list[str]] = Field(
        default=None,
        description=(
            "Tickers whose recommendation should be written to the watchlist. "
            "Omit to push every recommendation that carries a recognised action; "
            "send [] to store the mail without touching the watchlist."
        ),
    )
    proposal_by: str = Field(default="TCB", max_length=32)


class PushOut(BaseModel):
    symbol: str
    ok: bool
    error: Optional[str] = None


class TcbSaveResponse(BaseModel):
    mail: TcbMailOut
    created: bool                  # False when this exact content was already stored
    pushed: list[PushOut] = Field(default_factory=list)


class TcbRecoLedgerItem(RecoOut):
    """A stored call with the session it came from — the head-to-head ledger row."""

    session_date: date


class HorizonRecord(BaseModel):
    """One horizon's aggregate, with the benchmark it has to beat beside it."""

    n: int
    mean_return: Optional[float] = None
    mean_excess_return: Optional[float] = None
    directional_n: int = 0
    hit_rate: Optional[float] = None
    # The same directional bet placed on the index instead (EC-B7 / CLAUDE.md C4).
    # A hit rate is only evidence of skill if it exceeds this.
    benchmark_hit_rate: Optional[float] = None


class ActionRecord(BaseModel):
    n: int
    horizons: dict[str, dict] = Field(default_factory=dict)


class CallRecordResponse(BaseModel):
    """The desk's track record (FR-BM-RECORD). Only served once enough calls exist."""

    total_calls: int
    scored_calls: int
    # Scored calls withheld because their prices were unadjusted (Backlog #60) — a raw
    # series spanning a share-count event carries that event as a return. Surfaced so a
    # reader can see the record is a subset, rather than the calls vanishing silently.
    excluded_unadjusted: int = 0
    min_calls: int
    reportable: bool
    horizons: dict[str, HorizonRecord] = Field(default_factory=dict)
    by_action: dict[str, ActionRecord] = Field(default_factory=dict)


class ScoringRunResponse(BaseModel):
    considered: int
    scored: int
    completed: int
    gave_up: int
    unavailable: list[str] = Field(default_factory=list)
