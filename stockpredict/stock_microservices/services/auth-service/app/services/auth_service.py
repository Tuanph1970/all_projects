"""
Auth Service - Business logic for authentication
"""
from datetime import datetime, timedelta
from typing import Optional, Tuple
import logging
import secrets
import jwt
from passlib.context import CryptContext

from app.config import get_settings
from app.models.domain import User, UserRole
from app.models.schemas import (
    UserCreate,
    UserLogin,
    UserResponse,
    TokenResponse,
    TokenVerifyResponse,
)
from app.repositories.user_repository import UserRepository
from app.services.email_service import send_password_reset_email

logger = logging.getLogger(__name__)


settings = get_settings()

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    """Service for authentication operations"""

    def __init__(self, repository: UserRepository):
        self.repository = repository

    # ==================== Password Utilities ====================

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password"""
        return pwd_context.hash(password)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash"""
        return pwd_context.verify(plain_password, hashed_password)

    # ==================== Token Utilities ====================

    @staticmethod
    def create_access_token(
        user_id: int,
        email: str,
        role: str,
        expires_delta: Optional[timedelta] = None,
    ) -> str:
        """Create a JWT access token"""
        if expires_delta is None:
            expires_delta = timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)

        expire = datetime.utcnow() + expires_delta
        payload = {
            "sub": str(user_id),
            "email": email,
            "role": role,
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "access",
        }
        return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    @staticmethod
    def create_refresh_token() -> Tuple[str, datetime]:
        """Create a refresh token with expiration"""
        token = secrets.token_urlsafe(64)
        expires_at = datetime.utcnow() + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
        return token, expires_at

    @staticmethod
    def decode_token(token: str) -> Optional[dict]:
        """Decode and verify a JWT token"""
        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM],
            )
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None

    # ==================== User Operations ====================

    async def register(self, user_data: UserCreate) -> Tuple[User, str]:
        """Register a new user"""
        # Check if email already exists
        existing_user = await self.repository.get_user_by_email(user_data.email)
        if existing_user:
            raise ValueError("Email already registered")

        # Check if username already exists
        existing_username = await self.repository.get_user_by_username(user_data.username)
        if existing_username:
            raise ValueError("Username already taken")

        # Hash password and create user
        hashed_password = self.hash_password(user_data.password)
        user = await self.repository.create_user(
            email=user_data.email,
            username=user_data.username,
            hashed_password=hashed_password,
            full_name=user_data.full_name,
        )

        return user, "User registered successfully"

    async def login(
        self,
        login_data: UserLogin,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> TokenResponse:
        """Authenticate user and return tokens"""
        # Get user by email
        user = await self.repository.get_user_by_email(login_data.email)
        if not user:
            raise ValueError("Invalid email or password")

        # Verify password
        if not self.verify_password(login_data.password, user.hashed_password):
            raise ValueError("Invalid email or password")

        # Check if user is active
        if not user.is_active:
            raise ValueError("User account is deactivated")

        # Create access token
        access_token = self.create_access_token(
            user_id=user.id,
            email=user.email,
            role=user.role,
        )

        # Create refresh token
        refresh_token, expires_at = self.create_refresh_token()
        await self.repository.create_refresh_token(
            user_id=user.id,
            token=refresh_token,
            expires_at=expires_at,
            user_agent=user_agent,
            ip_address=ip_address,
        )

        # Update last login
        await self.repository.update_last_login(user.id)

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    async def refresh_tokens(
        self,
        refresh_token: str,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> TokenResponse:
        """Refresh access token using refresh token"""
        # Get refresh token from database
        token_record = await self.repository.get_refresh_token(refresh_token)
        if not token_record:
            raise ValueError("Invalid refresh token")

        # Check if token is valid
        if not token_record.is_valid:
            raise ValueError("Refresh token is expired or revoked")

        # Get user
        user = await self.repository.get_user_by_id(token_record.user_id)
        if not user or not user.is_active:
            raise ValueError("User not found or inactive")

        # Revoke old refresh token
        await self.repository.revoke_refresh_token(refresh_token)

        # Create new tokens
        access_token = self.create_access_token(
            user_id=user.id,
            email=user.email,
            role=user.role,
        )

        new_refresh_token, expires_at = self.create_refresh_token()
        await self.repository.create_refresh_token(
            user_id=user.id,
            token=new_refresh_token,
            expires_at=expires_at,
            user_agent=user_agent,
            ip_address=ip_address,
        )

        return TokenResponse(
            access_token=access_token,
            refresh_token=new_refresh_token,
            token_type="bearer",
            expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    async def logout(self, refresh_token: str) -> bool:
        """Logout user by revoking refresh token"""
        return await self.repository.revoke_refresh_token(refresh_token)

    async def logout_all(self, user_id: int) -> int:
        """Logout user from all devices"""
        return await self.repository.revoke_all_user_tokens(user_id)

    async def verify_token(self, token: str) -> TokenVerifyResponse:
        """Verify if a token is valid"""
        payload = self.decode_token(token)
        if not payload:
            return TokenVerifyResponse(valid=False)

        return TokenVerifyResponse(
            valid=True,
            user_id=int(payload.get("sub")),
            email=payload.get("email"),
            expires_at=datetime.fromtimestamp(payload.get("exp")),
        )

    async def change_password(
        self,
        user_id: int,
        current_password: str,
        new_password: str,
    ) -> bool:
        """Change user password"""
        # Get user
        user = await self.repository.get_user_by_id(user_id)
        if not user:
            raise ValueError("User not found")

        # Verify current password
        if not self.verify_password(current_password, user.hashed_password):
            raise ValueError("Current password is incorrect")

        # Update password
        hashed_password = self.hash_password(new_password)
        success = await self.repository.update_password(user_id, hashed_password)

        # Revoke all refresh tokens for security
        if success:
            await self.repository.revoke_all_user_tokens(user_id)

        return success

    async def get_current_user(self, user_id: int) -> Optional[User]:
        """Get current user by ID"""
        return await self.repository.get_user_by_id(user_id)

    @staticmethod
    def create_password_reset_token(user_id: int, email: str) -> str:
        """Issue a short-lived JWT scoped to password reset."""
        expires_minutes = settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES
        payload = {
            "sub": str(user_id),
            "email": email,
            "type": "password_reset",
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + timedelta(minutes=expires_minutes),
        }
        return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    async def request_password_reset(self, email: str) -> str:
        """Issue a reset token and email a reset link.

        The response is the same regardless of whether the email exists, so
        callers cannot enumerate accounts. If SMTP is not configured the link
        is logged (development) and the response stays generic.
        """
        generic_message = "If the email exists, a reset link will be sent"
        user = await self.repository.get_user_by_email(email)
        if not user or not user.is_active:
            return generic_message

        token = self.create_password_reset_token(user.id, user.email)
        reset_link = (
            f"{settings.FRONTEND_BASE_URL.rstrip('/')}"
            f"{settings.FRONTEND_RESET_PATH}?token={token}"
        )
        try:
            await send_password_reset_email(
                to_email=user.email,
                reset_link=reset_link,
                expires_minutes=settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES,
            )
        except Exception as e:
            # Log but still return the generic message to avoid leaking state.
            logger.error("Password reset email send raised: %s", e)

        return generic_message

    async def confirm_password_reset(self, token: str, new_password: str) -> bool:
        """Verify a password-reset JWT and set the new password."""
        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM],
            )
        except jwt.ExpiredSignatureError:
            raise ValueError("Reset token has expired")
        except jwt.InvalidTokenError:
            raise ValueError("Invalid reset token")

        if payload.get("type") != "password_reset":
            raise ValueError("Invalid reset token")

        try:
            user_id = int(payload.get("sub"))
        except (TypeError, ValueError):
            raise ValueError("Invalid reset token")

        user = await self.repository.get_user_by_id(user_id)
        if not user or not user.is_active:
            raise ValueError("Invalid reset token")

        hashed_password = self.hash_password(new_password)
        success = await self.repository.update_password(user_id, hashed_password)
        if success:
            # Invalidate any existing sessions on password change.
            await self.repository.revoke_all_user_tokens(user_id)
        return success
