"""
API Dependencies - Dependency injection for routes
"""
from typing import AsyncGenerator
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.config import get_settings
from app.repositories.stock_repository import StockRepository
from app.services.stock_service import StockService


settings = get_settings()

# Create async engine and session factory
engine = create_async_engine(
    settings.database_url,
    pool_size=settings.DATABASE_POOL_SIZE,
    pool_pre_ping=True,
    echo=settings.DEBUG,
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get database session"""
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()


def get_repository(session: AsyncSession = Depends(get_db)) -> StockRepository:
    """Get stock repository"""
    return StockRepository(session)


def get_stock_service(repository: StockRepository = Depends(get_repository)) -> StockService:
    """Get stock service"""
    return StockService(repository)
