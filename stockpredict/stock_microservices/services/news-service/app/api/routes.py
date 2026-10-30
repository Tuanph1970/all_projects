"""News-service API routes.

N1 mounts an empty versioned router so the gateway prefix + OpenAPI are in place.
The read endpoints (GET /news, GET /news/{id}, POST /ingest, POST /poll/{stream})
land in task N8.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.schemas import IngestRequest, IngestResponse
from app.deps import container, get_repo
from app.exceptions import ClassificationError, NewsIngestError, SourceUnavailableError
from app.models.domain import NewsEvent
from app.models.news_item import NewsItem
from app.repositories.news_repository import NewsRepository

logger = logging.getLogger(__name__)
router = APIRouter()


def _handle(exc: Exception) -> HTTPException:
    if isinstance(exc, (SourceUnavailableError, ClassificationError)):
        return HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))
    if isinstance(exc, (ValueError, NewsIngestError)):
        return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    logger.exception("Unexpected error in news endpoint")
    return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


def _row_to_dict(row: NewsEvent, *, include_raw: bool = False) -> dict:
    d = {
        "news_id": row.news_id,
        "source": row.source,
        "stream": row.stream,
        "symbol": row.symbol,
        "ts_utc": row.ts_utc,
        "title": row.title,
        "body": row.body,
        "url": row.url,
        "lang": row.lang,
        "category": row.category,
        "sentiment": row.sentiment,
        "sentiment_score": row.sentiment_score,
        # #112(d): a consumer must be able to weight the score, not just read it.
        "score_source": row.score_source,
        "ingested_at": row.ingested_at,
        "classified_at": row.classified_at,
        "notified_at": row.notified_at,
        "bridged_at": row.bridged_at,
    }
    if include_raw:
        d["raw_json"] = row.raw_json  # heavy full payload — detail view only
    return d


@router.get("/news", summary="List stored news items")
def list_news(
    stream: Optional[str] = None,
    symbol: Optional[str] = None,
    category: Optional[str] = None,
    sentiment: Optional[str] = None,
    since: Optional[datetime] = None,
    until: Optional[datetime] = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    repo: NewsRepository = Depends(get_repo),
):
    rows = repo.query(
        stream=stream, symbol=symbol, category=category, sentiment=sentiment,
        since=since, until=until, limit=limit, offset=offset,
    )
    return {"data": [_row_to_dict(r) for r in rows], "count": len(rows)}


@router.get("/news/{news_id}", summary="Get one news item (incl. raw_json)")
def get_news(news_id: str, repo: NewsRepository = Depends(get_repo)):
    row = repo.get(news_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="news item not found")
    return _row_to_dict(row, include_raw=True)


@router.post("/ingest", response_model=IngestResponse, summary="Manually ingest one item")
def ingest(req: IngestRequest, repo: NewsRepository = Depends(get_repo)):
    try:
        item = NewsItem(
            source=req.source, stream=req.stream, symbol=req.symbol, ts_utc=req.ts_utc,
            title=req.title, body=req.body, url=req.url, lang=req.lang,
            raw_json=req.raw_json or "{}", guid=req.guid,
        )
        stored = repo.upsert(item)
    except Exception as exc:  # noqa: BLE001
        raise _handle(exc)
    return IngestResponse(news_id=item.news_id(), stored=stored)


@router.post("/poll/{stream}", summary="Trigger a poll tick (ops/testing)")
async def poll(stream: str):
    if stream == "company":
        poller = container.company_poller
        if poller is None:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                                detail="company poller not running")
        return await poller.tick()
    if stream == "macro":
        poller = container.macro_poller
        if poller is None:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                                detail="macro poller not running (ENABLE_MACRO off?)")
        return await poller.tick()
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"unknown stream: {stream}")
