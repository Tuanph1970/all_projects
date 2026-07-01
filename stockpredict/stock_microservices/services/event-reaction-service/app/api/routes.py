"""Event-Reaction API routes — thin HTTP wrapper over the library (SRS §4.4)."""
from __future__ import annotations

import logging
import math

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.concurrency import run_in_threadpool

from event_reaction.exceptions import (
    AlignmentError,
    EventReactionError,
    InsufficientDataError,
    LeakageError,
)

from app.api.schemas import (
    CrossSectionRequest,
    CrossSectionResponse,
    IngestRequest,
    IngestResponse,
    MeasureRequest,
    MeasureResponse,
)
from app.deps import get_service
from app.services.event_reaction_service import EventReactionService

logger = logging.getLogger(__name__)
router = APIRouter()


def _handle(exc: Exception) -> HTTPException:
    if isinstance(exc, (InsufficientDataError, AlignmentError)):
        return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    if isinstance(exc, (LeakageError, ValueError, EventReactionError)):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    logger.exception("Unexpected error in event-reaction endpoint")
    return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.post("/events", response_model=IngestResponse, summary="Ingest events")
async def ingest_events(req: IngestRequest, svc: EventReactionService = Depends(get_service)):
    try:
        n = await run_in_threadpool(svc.ingest, [e.model_dump() for e in req.events])
        return IngestResponse(ingested=n)
    except Exception as exc:  # noqa: BLE001
        raise _handle(exc)


@router.get("/events", summary="List events")
async def list_events(kind: str | None = None, svc: EventReactionService = Depends(get_service)):
    try:
        df = await run_in_threadpool(svc.list_events, kind)
        return {"data": df.assign(ts_utc=df["ts_utc"].astype(str)).to_dict(orient="records")}
    except Exception as exc:  # noqa: BLE001
        raise _handle(exc)


@router.post("/measure", response_model=MeasureResponse, summary="Measure one event's reaction")
async def measure(req: MeasureRequest, svc: EventReactionService = Depends(get_service)):
    try:
        er = await run_in_threadpool(
            svc.measure, req.symbol, req.market_symbol, req.event.model_dump(),
            method=req.method, jump_n_null=req.jump_n_null,
        )
    except Exception as exc:  # noqa: BLE001
        raise _handle(exc)
    return MeasureResponse(
        t0_index=er.aligned.t0_index,
        coverage=er.aligned.coverage,
        surprise=er.surprise.__dict__,
        abnormal={
            "car": er.abnormal.car,
            "alpha": er.abnormal.alpha,
            "beta": er.abnormal.beta,
            "sigma_ar": er.abnormal.sigma_ar,
        },
        jump={
            "statistic": er.jump.statistic,
            "threshold": er.jump.threshold,
            "is_jump": er.jump.is_jump,
            "sigma_local": er.jump.sigma_local,
            "null_fpr": None if math.isnan(er.jump.null_fpr) else er.jump.null_fpr,
        },
    )


@router.post("/cross-section", response_model=CrossSectionResponse, summary="Exposure regression")
async def cross_section(req: CrossSectionRequest, svc: EventReactionService = Depends(get_service)):
    try:
        out = await run_in_threadpool(
            svc.cross_section, [r.model_dump() for r in req.rows], cluster=req.cluster
        )
    except Exception as exc:  # noqa: BLE001
        raise _handle(exc)
    return CrossSectionResponse(**out.__dict__)
