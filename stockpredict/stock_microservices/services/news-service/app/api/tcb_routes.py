"""Routes for the pasted TCBS daily mail (FR-BM-API).

Two-step by design, matching the operator's confirm-before-save workflow:

    POST /news/tcb/preview   parse only — nothing is written
    POST /news/tcb           store the mail and push the ticked calls to the watchlist

Splitting them is what makes a misread ticker correctable: the operator sees exactly
what the parser found, fixes the session date if the guess is off, corrects a wrong
ticker or action outright (Backlog #55), and unticks anything wrong before a single row
exists. Correcting rather than only excluding matters because an excluded call is a
*lost* call — the mail still stores it, but the watchlist never sees it.
"""
from __future__ import annotations

import logging
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status

from app.api.tcb_schemas import (
    CallRecordResponse,
    CompanyOut,
    PushOut,
    RecoOut,
    TcbMailOut,
    TcbPreviewRequest,
    TcbRecoLedgerItem,
    ScoringRunResponse,
    TcbSaveRequest,
    TcbSaveResponse,
)
from app.config import get_settings
from app.deps import get_call_scorer, get_tcb_repo, get_watchlist_pusher
from app.ingest.tcb_corrections import CorrectionError, apply_corrections
from app.ingest.tcb_mail_parser import ParsedMail, parse_tcb_mail
from app.models.tcb_news import TcbNews, TcbNewsReco
from app.services.call_scorer import build_record
from app.repositories.tcb_repository import TcbRepository
from app.services.watchlist_push import WatchlistPusher

logger = logging.getLogger(__name__)
router = APIRouter()
settings = get_settings()

_PARSED_FIELDS = (
    "lang", "vnindex_close", "vnindex_change_pct", "vnindex_change_pts",
    "matched_value_bn", "matched_volume_m", "putthrough_bn", "total_value_bn",
    "foreign_net_bn", "foreign_buy_bn", "foreign_sell_bn",
    "foreign_top_buy", "foreign_top_sell", "foreign_ytd_net_bn",
    "ma5", "ma10", "ma20", "ma50", "support_txt", "resistance_txt",
    "reports_txt", "market_txt", "liquidity_txt", "foreign_txt", "technical_txt",
    "macro_domestic_txt", "macro_intl_txt",
)


def _parsed_to_out(parsed: ParsedMail) -> TcbMailOut:
    out = TcbMailOut(
        session_date=parsed.session_date_hint,
        session_date_hint=parsed.session_date_hint,
        **{f: getattr(parsed, f) for f in _PARSED_FIELDS},
    )
    out.companies = [CompanyOut(symbol=c.symbol, item_text=c.item_text) for c in parsed.companies]
    out.recos = [
        RecoOut(symbol=r.symbol, action=r.action, label_verbatim=r.label_verbatim,
                rationale=r.rationale, target_price=r.target_price)
        for r in parsed.recos
    ]
    return out


_SCORE_FIELDS = (
    "ref_date", "ref_close", "ret_adjusted", "scored_at",
    "ret_1d", "ret_5d", "ret_20d", "ret_60d",
    "ret_1d_vs_index", "ret_5d_vs_index", "ret_20d_vs_index", "ret_60d_vs_index",
)


def _reco_to_out(r: TcbNewsReco) -> RecoOut:
    return RecoOut(
        id=r.id, symbol=r.symbol, action=r.action, label_verbatim=r.label_verbatim,
        rationale=r.rationale, target_price=r.target_price,
        pushed_to_watchlist=r.pushed_to_watchlist,
        # Correction provenance travels with the call (#55): a reader of the ledger can
        # see that a human overrode the parser rather than having to take the row on
        # trust, and a reparse pass can tell which fields to leave alone.
        corrected_fields=r.corrected_fields, corrected_at=r.corrected_at,
        **{f: getattr(r, f) for f in _SCORE_FIELDS},
    )


def _row_to_out(row: TcbNews) -> TcbMailOut:
    out = TcbMailOut(
        id=row.id,
        session_date=row.session_date,
        source=row.source,
        subject=row.subject,
        created_at=row.created_at,
        **{f: getattr(row, f) for f in _PARSED_FIELDS},
    )
    out.companies = [CompanyOut(id=c.id, symbol=c.symbol, item_text=c.item_text)
                     for c in row.companies]
    out.recos = [_reco_to_out(r) for r in row.recos]
    return out


@router.post("/tcb/preview", response_model=TcbMailOut,
             summary="Parse a pasted TCBS mail without storing it")
def preview_tcb_mail(req: TcbPreviewRequest):
    try:
        parsed = parse_tcb_mail(req.content, reference_date=req.reference_date or date.today())
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    return _parsed_to_out(parsed)


@router.post("/tcb", response_model=TcbSaveResponse, status_code=status.HTTP_201_CREATED,
             summary="Store a pasted TCBS mail and push its calls to the watchlist")
def save_tcb_mail(
    req: TcbSaveRequest,
    authorization: Optional[str] = Header(default=None),
    repo: TcbRepository = Depends(get_tcb_repo),
    pusher: WatchlistPusher = Depends(get_watchlist_pusher),
):
    try:
        parsed = parse_tcb_mail(req.content, reference_date=req.session_date)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    # The operator's fixes land between parsing and storage (Backlog #55). They must be
    # applied HERE and not in the parser: `raw_content` stays byte-identical (EC-B2), so
    # a parser fix is still replayable over the archive, and each overridden field is
    # recorded on the stored call so a reparse does not quietly undo a human's work.
    # A correction that cannot be matched to its call rejects the whole save (EC-B10) —
    # one ticker on the wrong row would poison the ledger silently.
    try:
        parsed = apply_corrections(parsed, req.corrections)
    except CorrectionError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    row, created = repo.save(
        parsed, raw=req.content, session_date=req.session_date, subject=req.subject,
    )
    if not created:
        # Re-pasting the same mail is a no-op, not an error: hand back what is stored
        # so the screen shows the existing session rather than creating a second one.
        logger.info("TCB mail already stored as id=%s (session %s)", row.id, row.session_date)
        return TcbSaveResponse(mail=_row_to_out(row), created=False, pushed=[])

    # Default: push every call TCBS made that we could normalise. An unrecognised label
    # (action is None) is never pushed silently — it shows in the preview for review.
    if req.push_symbols is None:
        wanted = {r.symbol for r in row.recos if r.action}
    else:
        wanted = {s.strip().upper() for s in req.push_symbols if s and s.strip()}

    pushed: list[PushOut] = []
    ok_ids: list[int] = []
    for reco in row.recos:
        if reco.symbol not in wanted:
            continue
        result = pusher.push(
            symbol=reco.symbol,
            action=reco.action,
            label_verbatim=reco.label_verbatim,
            session_date=row.session_date,
            rationale=reco.rationale,
            authorization=authorization,
            proposal_by=req.proposal_by,
        )
        pushed.append(PushOut(symbol=result.symbol, ok=result.ok, error=result.error))
        if result.ok:
            ok_ids.append(reco.id)
    repo.mark_pushed(ok_ids)

    stored = repo.get(row.id) or row
    return TcbSaveResponse(mail=_row_to_out(stored), created=True, pushed=pushed)


@router.get("/tcb", response_model=list[TcbMailOut], summary="List stored TCBS mails")
def list_tcb_mails(
    since: Optional[date] = None,
    until: Optional[date] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    repo: TcbRepository = Depends(get_tcb_repo),
):
    return [_row_to_out(r) for r in repo.list(since=since, until=until, limit=limit, offset=offset)]


@router.get("/tcb/recos", response_model=list[TcbRecoLedgerItem],
            summary="The TCBS call ledger, newest first")
def list_tcb_recos(
    symbol: Optional[str] = None,
    action: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500),
    repo: TcbRepository = Depends(get_tcb_repo),
):
    return [
        TcbRecoLedgerItem(**_reco_to_out(r).model_dump(), session_date=session_date)
        for r, session_date in repo.list_recos(symbol=symbol, action=action, limit=limit)
    ]


@router.get("/tcb/calls/record", response_model=CallRecordResponse,
            summary="TCBS's track record — hit rate beside the index benchmark")
def tcb_call_record(repo: TcbRepository = Depends(get_tcb_repo)):
    """Refuses to report below SCORING_MIN_CALLS scored calls (FR-BM-RECORD).

    This is deliberate, not a limitation: a hit rate over a handful of calls is noise
    dressed as evidence, and the whole point of the ledger is to be the thing a decision
    can lean on. The individual marks are always readable via GET /news/tcb/recos.
    """
    record = build_record(repo.all_scored_calls(), min_calls=settings.SCORING_MIN_CALLS)
    if not record["reportable"]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(f"not reportable yet: {record['scored_calls']} scored call(s), "
                    f"{settings.SCORING_MIN_CALLS} required"),
        )
    return record


@router.post("/tcb/score", response_model=ScoringRunResponse,
             summary="Run a forward-return scoring pass now (ops/testing)")
async def run_tcb_scoring(scorer=Depends(get_call_scorer)):
    return await scorer.tick()


@router.get("/tcb/{mail_id}", response_model=TcbMailOut, summary="Get one stored TCBS mail")
def get_tcb_mail(mail_id: int, repo: TcbRepository = Depends(get_tcb_repo)):
    row = repo.get(mail_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="TCB mail not found")
    return _row_to_out(row)


@router.delete("/tcb/{mail_id}", status_code=status.HTTP_204_NO_CONTENT,
               summary="Delete one stored TCBS mail")
def delete_tcb_mail(mail_id: int, repo: TcbRepository = Depends(get_tcb_repo)):
    if not repo.delete(mail_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="TCB mail not found")
