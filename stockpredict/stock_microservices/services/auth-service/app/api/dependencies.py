"""
API Dependencies - Dependency injection for routes
"""
from typing import AsyncGenerator, Optional
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.config import get_settings
from app.models.domain import User
from app.repositories.user_repository import UserRepository
from app.services.auth_service import AuthService


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
    pool_recycle=3600,  # recycle every hour as a coarse stale-conn guard
    echo=settings.DEBUG,
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Security scheme
security = HTTPBearer(auto_error=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get database session"""
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()


def get_repository(session: AsyncSession = Depends(get_db)) -> UserRepository:
    """Get user repository"""
    return UserRepository(session)


def get_auth_service(repository: UserRepository = Depends(get_repository)) -> AuthService:
    """Get auth service"""
    return AuthService(repository)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    repository: UserRepository = Depends(get_repository),
) -> User:
    """Get current authenticated user from JWT token"""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Decode token
    payload = AuthService.decode_token(credentials.credentials)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Get user from database
    user_id = int(payload.get("sub"))
    user = await repository.get_user_by_id(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated",
        )

    return user


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    repository: UserRepository = Depends(get_repository),
) -> Optional[User]:
    """Get current user if authenticated, None otherwise"""
    if not credentials:
        return None

    payload = AuthService.decode_token(credentials.credentials)
    if not payload:
        return None

    user_id = int(payload.get("sub"))
    return await repository.get_user_by_id(user_id)


def get_client_info(request: Request) -> dict:
    """Get client information from request"""
    return {
        "user_agent": request.headers.get("user-agent"),
        "ip_address": request.client.host if request.client else None,
    }
