"""Diary Service — Business Logic for Trade Diary (Schwager's 3 Pillars)"""
import os
import uuid
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.diary_repository import DiaryRepository
from app.repositories.trade_repository import TradeRepository
from app.repositories.account_repository import AccountRepository
from app.models.domain import TradeStatus
from app.models.schemas import TradeDiaryCreate, TradeDiaryUpdate
from app.config import get_settings

settings = get_settings()


class DiaryService:
    def __init__(self, session: AsyncSession):
        self.diary_repo = DiaryRepository(session)
        self.trade_repo = TradeRepository(session)
        self.account_repo = AccountRepository(session)

    # =========================================================================
    # Helpers
    # =========================================================================

    @staticmethod
    def _diary_to_dict(diary) -> dict:
        """Convert diary ORM object to dict for API response"""
        return {
            "id": diary.id,
            "trade_id": diary.trade_id,
            "reasons_for_trade": diary.reasons_for_trade,
            "how_it_turned_out": diary.how_it_turned_out,
            "lessons_and_mistakes": diary.lessons_and_mistakes,
            "chart_pattern": diary.chart_pattern.value if diary.chart_pattern else None,
            "emotional_state_entry": diary.emotional_state_entry.value if diary.emotional_state_entry else None,
            "emotional_state_during": diary.emotional_state_during.value if diary.emotional_state_during else None,
            "emotional_state_exit": diary.emotional_state_exit.value if diary.emotional_state_exit else None,
            "diary_complete": diary.how_it_turned_out is not None and diary.lessons_and_mistakes is not None,
            "created_at": diary.created_at,
            "updated_at": diary.updated_at,
            "charts": [
                {
                    "id": c.id,
                    "diary_id": c.diary_id,
                    "image_path": c.image_path,
                    "caption": c.caption,
                    "chart_type": c.chart_type.value if c.chart_type else None,
                    "uploaded_at": c.uploaded_at
                }
                for c in (diary.charts or [])
            ]
        }

    async def _verify_trade_ownership(self, trade_id: int, user_id: int):
        """Verify user owns the trade via account ownership"""
        trade = await self.trade_repo.get_trade_by_id_no_account(trade_id)
        if not trade:
            return None, None
        account = await self.account_repo.get_account_by_id(trade.account_id, user_id)
        if not account:
            return None, None
        return trade, account

    # =========================================================================
    # Diary CRUD
    # =========================================================================

    async def get_or_create_diary(self, trade_id: int, user_id: int,
                                  data: Optional[TradeDiaryCreate] = None) -> Optional[dict]:
        """Get existing diary or create new one for a trade"""
        trade, account = await self._verify_trade_ownership(trade_id, user_id)
        if not trade:
            return None

        diary = await self.diary_repo.get_diary_by_trade_id(trade_id)
        if diary:
            return self._diary_to_dict(diary)

        # Create new diary
        diary = await self.diary_repo.create_diary(
            trade_id=trade_id,
            reasons_for_trade=data.reasons_for_trade if data else None,
            chart_pattern=data.chart_pattern if data else None,
            emotional_state_entry=data.emotional_state_entry if data else None
        )
        return self._diary_to_dict(diary)

    async def get_diary(self, trade_id: int, user_id: int) -> Optional[dict]:
        """Get diary for a trade"""
        trade, account = await self._verify_trade_ownership(trade_id, user_id)
        if not trade:
            return None

        diary = await self.diary_repo.get_diary_by_trade_id(trade_id)
        if not diary:
            return {"not_found": True, "trade_id": trade_id}
        return self._diary_to_dict(diary)

    async def update_diary(self, trade_id: int, user_id: int,
                           data: TradeDiaryUpdate) -> Optional[dict]:
        """Update diary — Schwager's rule: 'how_it_turned_out' and 'lessons'
        can only be filled after trade is closed"""
        trade, account = await self._verify_trade_ownership(trade_id, user_id)
        if not trade:
            return None

        diary = await self.diary_repo.get_diary_by_trade_id(trade_id)
        if not diary:
            return {"error": True, "message": "Chưa có nhật ký cho giao dịch này. Hãy tạo trước."}

        update_data = data.model_dump(exclude_unset=True)

        # Schwager's diary lock rule: outcome/lessons only after trade is closed
        locked_fields = ["how_it_turned_out", "lessons_and_mistakes",
                         "emotional_state_exit"]
        if trade.status != TradeStatus.CLOSED:
            for field in locked_fields:
                if field in update_data and update_data[field] is not None:
                    return {
                        "error": True,
                        "message": f"Chỉ có thể điền '{field}' sau khi đóng lệnh. Đây là quy tắc của Schwager: "
                                   f"ghi nhận kết quả và bài học chỉ sau khi giao dịch kết thúc."
                    }

        if not update_data:
            return self._diary_to_dict(diary)

        diary = await self.diary_repo.update_diary(diary.id, **update_data)
        return self._diary_to_dict(diary)

    async def delete_diary(self, trade_id: int, user_id: int) -> Optional[bool]:
        """Delete diary and all associated charts"""
        trade, account = await self._verify_trade_ownership(trade_id, user_id)
        if not trade:
            return None

        diary = await self.diary_repo.get_diary_by_trade_id(trade_id)
        if not diary:
            return False

        # Clean up chart files
        for chart in (diary.charts or []):
            try:
                if os.path.exists(chart.image_path):
                    os.remove(chart.image_path)
            except OSError:
                pass

        return await self.diary_repo.delete_diary(diary.id)

    # =========================================================================
    # Chart Operations
    # =========================================================================

    async def upload_chart(self, diary_id: int, user_id: int,
                           file_content: bytes, filename: str,
                           caption: Optional[str] = None,
                           chart_type=None) -> Optional[dict]:
        """Upload a chart image to diary"""
        diary = await self.diary_repo.get_diary_by_id(diary_id)
        if not diary:
            return None

        # Verify ownership
        trade, account = await self._verify_trade_ownership(diary.trade_id, user_id)
        if not trade:
            return None

        # Save file
        ext = os.path.splitext(filename)[1] or ".png"
        safe_name = f"{diary_id}_{uuid.uuid4().hex[:8]}{ext}"
        file_path = os.path.join(settings.UPLOAD_DIR, safe_name)

        with open(file_path, "wb") as f:
            f.write(file_content)

        chart = await self.diary_repo.create_chart(
            diary_id=diary_id,
            image_path=file_path,
            caption=caption,
            chart_type=chart_type
        )

        return {
            "id": chart.id,
            "diary_id": chart.diary_id,
            "image_path": chart.image_path,
            "caption": chart.caption,
            "chart_type": chart.chart_type.value if chart.chart_type else None,
            "uploaded_at": chart.uploaded_at
        }

    async def get_charts(self, diary_id: int, user_id: int) -> Optional[list]:
        """Get all charts for a diary"""
        diary = await self.diary_repo.get_diary_by_id(diary_id)
        if not diary:
            return None

        trade, account = await self._verify_trade_ownership(diary.trade_id, user_id)
        if not trade:
            return None

        charts = await self.diary_repo.get_charts_by_diary(diary_id)
        return [
            {
                "id": c.id,
                "diary_id": c.diary_id,
                "image_path": c.image_path,
                "caption": c.caption,
                "chart_type": c.chart_type.value if c.chart_type else None,
                "uploaded_at": c.uploaded_at
            }
            for c in charts
        ]

    async def delete_chart(self, chart_id: int, user_id: int) -> Optional[bool]:
        """Delete a chart and its file"""
        chart = await self.diary_repo.get_chart_by_id(chart_id)
        if not chart:
            return None

        diary = await self.diary_repo.get_diary_by_id(chart.diary_id)
        if not diary:
            return None

        trade, account = await self._verify_trade_ownership(diary.trade_id, user_id)
        if not trade:
            return None

        image_path = await self.diary_repo.delete_chart(chart_id)
        if image_path:
            try:
                if os.path.exists(image_path):
                    os.remove(image_path)
            except OSError:
                pass
            return True
        return False
