"""Trade Diary & Chart Upload API Routes — Phase 3"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db, get_current_user
from app.services.diary_service import DiaryService
from app.models.schemas import TradeDiaryCreate, TradeDiaryUpdate
from app.config import get_settings

settings = get_settings()
router = APIRouter()


# =============================================================================
# Trade Diary Endpoints
# =============================================================================

@router.post("/trades/{trade_id}/diary", status_code=status.HTTP_201_CREATED)
async def create_or_get_diary(
    trade_id: int,
    data: Optional[TradeDiaryCreate] = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Create or get diary for a trade (Schwager's 3 pillars)"""
    service = DiaryService(db)
    result = await service.get_or_create_diary(trade_id, current_user["user_id"], data)
    if result is None:
        raise HTTPException(status_code=404, detail="Trade not found or not owned by user")
    return result


@router.get("/trades/{trade_id}/diary")
async def get_diary(
    trade_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get diary for a trade"""
    service = DiaryService(db)
    result = await service.get_diary(trade_id, current_user["user_id"])
    if result is None:
        raise HTTPException(status_code=404, detail="Trade not found or not owned by user")
    if result.get("not_found"):
        raise HTTPException(status_code=404, detail="Diary not found for this trade")
    return result


@router.put("/trades/{trade_id}/diary")
async def update_diary(
    trade_id: int,
    data: TradeDiaryUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Update diary — Schwager's rule: outcome/lessons only after trade is closed"""
    service = DiaryService(db)
    result = await service.update_diary(trade_id, current_user["user_id"], data)
    if result is None:
        raise HTTPException(status_code=404, detail="Trade not found or not owned by user")
    if result.get("error"):
        raise HTTPException(status_code=400, detail=result["message"])
    return result


@router.delete("/trades/{trade_id}/diary", status_code=status.HTTP_204_NO_CONTENT)
async def delete_diary(
    trade_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Delete diary and all associated charts"""
    service = DiaryService(db)
    result = await service.delete_diary(trade_id, current_user["user_id"])
    if result is None:
        raise HTTPException(status_code=404, detail="Trade not found or not owned by user")
    if not result:
        raise HTTPException(status_code=404, detail="Diary not found")


# =============================================================================
# Diary Chart Endpoints
# =============================================================================

@router.post("/diary/{diary_id}/charts", status_code=status.HTTP_201_CREATED)
async def upload_chart(
    diary_id: int,
    file: UploadFile = File(...),
    caption: Optional[str] = Form(None),
    chart_type: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Upload a chart screenshot to diary"""
    # Validate file type
    allowed_types = {"image/png", "image/jpeg", "image/jpg", "image/webp", "image/gif"}
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"File type not allowed. Allowed: {', '.join(allowed_types)}"
        )

    # Validate file size
    content = await file.read()
    max_size = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if len(content) > max_size:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Max size: {settings.MAX_UPLOAD_SIZE_MB}MB"
        )

    # Convert chart_type string to enum if provided
    chart_type_enum = None
    if chart_type:
        from app.models.domain import ChartType
        try:
            chart_type_enum = ChartType(chart_type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid chart_type: {chart_type}")

    service = DiaryService(db)
    result = await service.upload_chart(
        diary_id, current_user["user_id"],
        file_content=content,
        filename=file.filename,
        caption=caption,
        chart_type=chart_type_enum
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Diary not found or not owned by user")
    return result


@router.get("/diary/{diary_id}/charts")
async def get_charts(
    diary_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get all charts for a diary"""
    service = DiaryService(db)
    result = await service.get_charts(diary_id, current_user["user_id"])
    if result is None:
        raise HTTPException(status_code=404, detail="Diary not found or not owned by user")
    return result


@router.delete("/diary/charts/{chart_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chart(
    chart_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Delete a chart"""
    service = DiaryService(db)
    result = await service.delete_chart(chart_id, current_user["user_id"])
    if result is None:
        raise HTTPException(status_code=404, detail="Chart not found or not owned by user")
    if not result:
        raise HTTPException(status_code=404, detail="Chart not found")
