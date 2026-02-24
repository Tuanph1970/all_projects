"""Diary Repository — Database Operations for TradeDiary & DiaryChart"""
from typing import Optional, List
from datetime import datetime
from sqlalchemy import select, update, delete, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.domain import TradeDiary, DiaryChart


class DiaryRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    # =========================================================================
    # TradeDiary Operations
    # =========================================================================

    async def get_diary_by_trade_id(self, trade_id: int) -> Optional[TradeDiary]:
        result = await self.session.execute(
            select(TradeDiary)
            .options(selectinload(TradeDiary.charts))
            .where(TradeDiary.trade_id == trade_id)
        )
        return result.scalar_one_or_none()

    async def get_diary_by_id(self, diary_id: int) -> Optional[TradeDiary]:
        result = await self.session.execute(
            select(TradeDiary)
            .options(selectinload(TradeDiary.charts))
            .where(TradeDiary.id == diary_id)
        )
        return result.scalar_one_or_none()

    async def create_diary(self, trade_id: int,
                           reasons_for_trade: Optional[str] = None,
                           chart_pattern=None,
                           emotional_state_entry=None) -> TradeDiary:
        diary = TradeDiary(
            trade_id=trade_id,
            reasons_for_trade=reasons_for_trade,
            chart_pattern=chart_pattern,
            emotional_state_entry=emotional_state_entry
        )
        self.session.add(diary)
        await self.session.commit()
        await self.session.refresh(diary)
        # Re-fetch with charts loaded
        return await self.get_diary_by_trade_id(trade_id)

    async def update_diary(self, diary_id: int, **kwargs) -> Optional[TradeDiary]:
        kwargs["updated_at"] = datetime.utcnow()
        await self.session.execute(
            update(TradeDiary)
            .where(TradeDiary.id == diary_id)
            .values(**kwargs)
        )
        await self.session.commit()
        return await self.get_diary_by_id(diary_id)

    async def delete_diary(self, diary_id: int) -> bool:
        result = await self.session.execute(
            delete(TradeDiary).where(TradeDiary.id == diary_id)
        )
        await self.session.commit()
        return result.rowcount > 0

    # =========================================================================
    # DiaryChart Operations
    # =========================================================================

    async def get_charts_by_diary(self, diary_id: int) -> List[DiaryChart]:
        result = await self.session.execute(
            select(DiaryChart)
            .where(DiaryChart.diary_id == diary_id)
            .order_by(DiaryChart.uploaded_at.desc())
        )
        return list(result.scalars().all())

    async def create_chart(self, diary_id: int, image_path: str,
                           caption: Optional[str] = None,
                           chart_type=None) -> DiaryChart:
        chart = DiaryChart(
            diary_id=diary_id,
            image_path=image_path,
            caption=caption,
            chart_type=chart_type
        )
        self.session.add(chart)
        await self.session.commit()
        await self.session.refresh(chart)
        return chart

    async def get_chart_by_id(self, chart_id: int) -> Optional[DiaryChart]:
        result = await self.session.execute(
            select(DiaryChart).where(DiaryChart.id == chart_id)
        )
        return result.scalar_one_or_none()

    async def delete_chart(self, chart_id: int) -> Optional[str]:
        """Delete chart and return its image_path for file cleanup"""
        chart = await self.get_chart_by_id(chart_id)
        if not chart:
            return None
        image_path = chart.image_path
        await self.session.execute(
            delete(DiaryChart).where(DiaryChart.id == chart_id)
        )
        await self.session.commit()
        return image_path
