"""Analysis Repository - Database Operations"""
from typing import Optional, List
from datetime import datetime, timedelta
from sqlalchemy import select, update, delete, and_
from sqlalchemy.ext.asyncio import AsyncSession
import hashlib
import json

from app.models.domain import AnalysisResult, ScreenerConfig, ScreenerResult, FundamentalData, AnalysisType


class AnalysisRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def save_analysis(self, symbol: str, analysis_type: AnalysisType, **kwargs) -> AnalysisResult:
        result = AnalysisResult(
            symbol=symbol.upper(),
            analysis_type=analysis_type,
            expires_at=datetime.utcnow() + timedelta(hours=1),
            **kwargs
        )
        self.session.add(result)
        await self.session.commit()
        await self.session.refresh(result)
        return result

    async def get_cached_analysis(self, symbol: str, analysis_type: AnalysisType) -> Optional[AnalysisResult]:
        result = await self.session.execute(
            select(AnalysisResult).where(
                and_(
                    AnalysisResult.symbol == symbol.upper(),
                    AnalysisResult.analysis_type == analysis_type,
                    AnalysisResult.expires_at > datetime.utcnow()
                )
            ).order_by(AnalysisResult.created_at.desc())
        )
        return result.scalar_one_or_none()

    async def save_screener_config(self, user_id: int, name: str, filters: list,
                                   description: Optional[str] = None, is_public: bool = False) -> ScreenerConfig:
        config = ScreenerConfig(
            user_id=user_id,
            name=name,
            description=description,
            filters=filters,
            is_public=is_public
        )
        self.session.add(config)
        await self.session.commit()
        await self.session.refresh(config)
        return config

    async def get_screener_configs(self, user_id: int) -> List[ScreenerConfig]:
        result = await self.session.execute(
            select(ScreenerConfig).where(
                and_(ScreenerConfig.user_id == user_id, ScreenerConfig.is_active == True)
            ).order_by(ScreenerConfig.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_screener_config(self, config_id: int, user_id: int) -> Optional[ScreenerConfig]:
        result = await self.session.execute(
            select(ScreenerConfig).where(
                and_(ScreenerConfig.id == config_id, ScreenerConfig.user_id == user_id)
            )
        )
        return result.scalar_one_or_none()

    async def delete_screener_config(self, config_id: int, user_id: int) -> bool:
        result = await self.session.execute(
            delete(ScreenerConfig).where(
                and_(ScreenerConfig.id == config_id, ScreenerConfig.user_id == user_id)
            )
        )
        await self.session.commit()
        return result.rowcount > 0

    def _hash_filters(self, filters: list) -> str:
        return hashlib.sha256(json.dumps(filters, sort_keys=True).encode()).hexdigest()

    async def cache_screener_results(self, filters: list, results: list, total: int) -> ScreenerResult:
        filter_hash = self._hash_filters(filters)
        result = ScreenerResult(
            filter_hash=filter_hash,
            results=results,
            total_matches=total,
            expires_at=datetime.utcnow() + timedelta(minutes=5)
        )
        self.session.add(result)
        await self.session.commit()
        return result

    async def get_cached_screener(self, filters: list) -> Optional[ScreenerResult]:
        filter_hash = self._hash_filters(filters)
        result = await self.session.execute(
            select(ScreenerResult).where(
                and_(
                    ScreenerResult.filter_hash == filter_hash,
                    ScreenerResult.expires_at > datetime.utcnow()
                )
            )
        )
        return result.scalar_one_or_none()

    async def save_fundamental_data(self, symbol: str, **kwargs) -> FundamentalData:
        existing = await self.session.execute(
            select(FundamentalData).where(FundamentalData.symbol == symbol.upper())
        )
        data = existing.scalar_one_or_none()

        if data:
            for key, value in kwargs.items():
                if hasattr(data, key):
                    setattr(data, key, value)
            data.updated_at = datetime.utcnow()
        else:
            data = FundamentalData(symbol=symbol.upper(), **kwargs)
            self.session.add(data)

        await self.session.commit()
        await self.session.refresh(data)
        return data

    async def get_fundamental_data(self, symbol: str) -> Optional[FundamentalData]:
        result = await self.session.execute(
            select(FundamentalData).where(FundamentalData.symbol == symbol.upper())
        )
        return result.scalar_one_or_none()
