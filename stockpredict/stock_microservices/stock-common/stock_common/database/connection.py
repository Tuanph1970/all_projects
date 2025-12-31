"""
Async database connection management.

Provides:
- SQLAlchemy async engine
- Session management
- Connection pooling
"""

import logging
from typing import AsyncGenerator, Optional

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import QueuePool

from stock_common.config import DatabaseConfig

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Async database connection manager.

    Handles:
    - Engine creation with connection pooling
    - Session factory
    - Health checks
    """

    def __init__(self, config: DatabaseConfig):
        self.config = config
        self._engine = None
        self._session_factory = None

    async def connect(self) -> None:
        """Initialize database connection."""
        if self._engine is not None:
            return

        self._engine = create_async_engine(
            self.config.url,
            pool_size=self.config.pool_size,
            max_overflow=self.config.pool_size * 2,
            pool_timeout=self.config.pool_timeout,
            pool_recycle=3600,  # Recycle connections after 1 hour
            pool_pre_ping=True,  # Check connection health before use
            echo=self.config.echo,
            poolclass=QueuePool,
        )

        self._session_factory = async_sessionmaker(
            bind=self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )

        logger.info(
            f"Database connected: {self.config.host}:{self.config.port}/{self.config.name}"
        )

    async def disconnect(self) -> None:
        """Close database connection."""
        if self._engine is not None:
            await self._engine.dispose()
            self._engine = None
            self._session_factory = None
            logger.info("Database disconnected")

    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get an async database session."""
        if self._session_factory is None:
            await self.connect()

        async with self._session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    async def health_check(self) -> tuple[bool, str]:
        """Check database health."""
        try:
            async with self._engine.connect() as conn:
                await conn.execute("SELECT 1")
            return True, "Connected"
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False, str(e)

    @property
    def is_connected(self) -> bool:
        """Check if connected to database."""
        return self._engine is not None


# Global database manager instance
_db_manager: Optional[DatabaseManager] = None


def get_db_manager(config: Optional[DatabaseConfig] = None) -> DatabaseManager:
    """Get or create the global database manager."""
    global _db_manager
    if _db_manager is None:
        if config is None:
            from stock_common.config import get_config
            config = get_config().database
        _db_manager = DatabaseManager(config)
    return _db_manager


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for getting a database session."""
    manager = get_db_manager()
    async for session in manager.get_session():
        yield session
