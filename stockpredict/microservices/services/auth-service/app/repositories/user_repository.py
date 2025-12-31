"""
User Repository - Data access layer for user operations
"""
from datetime import datetime, timedelta
from typing import Optional, List
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain import User, RefreshToken, UserRole


class UserRepository:
    """Repository for user-related database operations"""

    def __init__(self, session: AsyncSession):
        self.session = session

    # ==================== User Operations ====================

    async def create_user(
        self,
        email: str,
        username: str,
        hashed_password: str,
        full_name: Optional[str] = None,
        role: UserRole = UserRole.USER,
    ) -> User:
        """Create a new user"""
        # Parse full_name into first_name and last_name for existing schema
        first_name = None
        last_name = None
        if full_name:
            parts = full_name.split(" ", 1)
            first_name = parts[0] if parts else None
            last_name = parts[1] if len(parts) > 1 else None

        user = User(
            email=email,
            username=username,
            password_hash=hashed_password,  # Use password_hash for existing schema
            first_name=first_name,
            last_name=last_name,
            is_active=True,
        )
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID"""
        result = await self.session.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        result = await self.session.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username"""
        result = await self.session.execute(
            select(User).where(User.username == username)
        )
        return result.scalar_one_or_none()

    async def update_user(self, user_id: int, **kwargs) -> Optional[User]:
        """Update user fields"""
        await self.session.execute(
            update(User)
            .where(User.id == user_id)
            .values(**kwargs)  # Removed updated_at - not in existing schema
        )
        await self.session.commit()
        return await self.get_user_by_id(user_id)

    async def update_password(self, user_id: int, hashed_password: str) -> bool:
        """Update user password"""
        result = await self.session.execute(
            update(User)
            .where(User.id == user_id)
            .values(password_hash=hashed_password)  # Use password_hash for existing schema
        )
        await self.session.commit()
        return result.rowcount > 0

    async def update_last_login(self, user_id: int) -> None:
        """Update user's last login time"""
        await self.session.execute(
            update(User)
            .where(User.id == user_id)
            .values(last_login=datetime.utcnow())
        )
        await self.session.commit()

    async def verify_user(self, user_id: int) -> bool:
        """Mark user as verified - Note: is_verified not in existing schema, returns True for compatibility"""
        # Existing schema doesn't have is_verified column
        # Users are considered verified by default
        return True

    async def deactivate_user(self, user_id: int) -> bool:
        """Deactivate a user"""
        result = await self.session.execute(
            update(User)
            .where(User.id == user_id)
            .values(is_active=False)  # Removed updated_at - not in existing schema
        )
        await self.session.commit()
        return result.rowcount > 0

    async def get_all_users(self, skip: int = 0, limit: int = 100) -> List[User]:
        """Get all users with pagination"""
        result = await self.session.execute(
            select(User).offset(skip).limit(limit)
        )
        return list(result.scalars().all())

    # ==================== Refresh Token Operations ====================

    async def create_refresh_token(
        self,
        user_id: int,
        token: str,
        expires_at: datetime,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> RefreshToken:
        """Create a new refresh token"""
        refresh_token = RefreshToken(
            user_id=user_id,
            token=token,
            expires_at=expires_at,
            user_agent=user_agent,
            ip_address=ip_address,
        )
        self.session.add(refresh_token)
        await self.session.commit()
        await self.session.refresh(refresh_token)
        return refresh_token

    async def get_refresh_token(self, token: str) -> Optional[RefreshToken]:
        """Get refresh token by token string"""
        result = await self.session.execute(
            select(RefreshToken).where(RefreshToken.token == token)
        )
        return result.scalar_one_or_none()

    async def revoke_refresh_token(self, token: str) -> bool:
        """Revoke a refresh token"""
        result = await self.session.execute(
            update(RefreshToken)
            .where(RefreshToken.token == token)
            .values(is_revoked=True, revoked_at=datetime.utcnow())
        )
        await self.session.commit()
        return result.rowcount > 0

    async def revoke_all_user_tokens(self, user_id: int) -> int:
        """Revoke all refresh tokens for a user"""
        result = await self.session.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id)
            .where(RefreshToken.is_revoked == False)
            .values(is_revoked=True, revoked_at=datetime.utcnow())
        )
        await self.session.commit()
        return result.rowcount

    async def cleanup_expired_tokens(self) -> int:
        """Delete expired refresh tokens"""
        result = await self.session.execute(
            delete(RefreshToken).where(RefreshToken.expires_at < datetime.utcnow())
        )
        await self.session.commit()
        return result.rowcount

    async def get_user_active_tokens(self, user_id: int) -> List[RefreshToken]:
        """Get all active (non-revoked, non-expired) tokens for a user"""
        result = await self.session.execute(
            select(RefreshToken)
            .where(RefreshToken.user_id == user_id)
            .where(RefreshToken.is_revoked == False)
            .where(RefreshToken.expires_at > datetime.utcnow())
        )
        return list(result.scalars().all())
