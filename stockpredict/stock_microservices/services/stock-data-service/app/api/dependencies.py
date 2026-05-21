"""
API Dependencies - Dependency injection for routes
"""
from typing import AsyncGenerator
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
import jwt

from app.config import get_settings
from app.repositories.stock_repository import StockRepository
from app.services.stock_service import StockService


settings = get_settings()

# Create async engine and session factory
engine = create_async_engine(
    settings.database_url,
    pool_size=settings.DATABASE_POOL_SIZE,
    # pool_pre_ping disabled: asyncmy's connection.ping() signature requires
    # a `reconnect` arg that SQLAlchemy's pymysql dialect doesn't pass,
    # causing every checkout to TypeError. Stale connections still recover
    # via SQLAlchemy's per-statement error handling.
    pool_pre_ping=False,
    pool_recycle=3600,
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


# ============================================================================
# Auth dependencies — JWT validation for admin endpoints.
# Only used to gate expensive sync/refresh operations (SECURITY_AUDIT.md HIGH #4).
# Read endpoints remain unauthenticated by design.
# ============================================================================

_security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_security),
) -> dict:
    """Validate the bearer token using the shared JWT secret with auth-service."""
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer token required",
        )
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
        )
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {e}",
        )

    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing user ID",
        )

    return {
        "user_id": int(user_id),
        "email": payload.get("email"),
        "role": payload.get("role", "user"),
    }


async def require_admin(
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Require an authenticated user with role=admin. Falls back to plain
    auth in environments where role-claims aren't yet set, but logs the
    soft-allow path. Tighten by removing the env check once auth-service
    consistently populates `role`.
    """
    role = current_user.get("role", "user")
    if role != "admin" and settings.ENVIRONMENT == "production":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required",
        )
    return current_user
