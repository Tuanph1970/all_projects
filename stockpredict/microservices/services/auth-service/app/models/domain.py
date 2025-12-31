"""
Domain Models - SQLAlchemy ORM models for auth service
Maps to existing database schema in defaultdb
"""
from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    ForeignKey,
    Text,
    Enum as SQLEnum,
)
from sqlalchemy.dialects.mysql import INTEGER
from sqlalchemy.orm import relationship, DeclarativeBase
import enum


class Base(DeclarativeBase):
    """Base class for all models"""
    pass


class UserRole(enum.Enum):
    """User role enumeration"""
    USER = "user"
    ADMIN = "admin"
    PREMIUM = "premium"


class User(Base):
    """User model - maps to existing users table in defaultdb"""
    __tablename__ = "users"
    __table_args__ = {'extend_existing': True}

    # Match existing schema: id is int unsigned
    id = Column(INTEGER(unsigned=True), primary_key=True, autoincrement=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    first_name = Column(String(50), nullable=True)
    last_name = Column(String(50), nullable=True)
    mobile = Column(String(20), nullable=True)
    registered_at = Column(DateTime, default=datetime.utcnow, nullable=True)
    last_login = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True, nullable=True)

    # Relationships
    refresh_tokens = relationship(
        "RefreshToken",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    # Property to access password_hash as hashed_password for backward compatibility
    # Using @property here is safe because it doesn't define a SQLAlchemy column
    @property
    def hashed_password(self) -> str:
        """Backward-compatible property for password hash access"""
        return self.password_hash

    @hashed_password.setter
    def hashed_password(self, value: str) -> None:
        """Backward-compatible property for password hash access"""
        self.password_hash = value

    @property
    def full_name(self) -> Optional[str]:
        """Compute full name from first_name and last_name"""
        parts = [self.first_name, self.last_name]
        return " ".join(p for p in parts if p) or None

    @property
    def role(self) -> str:
        """Get user role - defaults to user"""
        return "user"

    @property
    def is_verified(self) -> bool:
        """Get verified status - defaults to True"""
        return True

    @property
    def created_at(self) -> Optional[datetime]:
        """Get created_at as alias for registered_at"""
        return self.registered_at

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, username={self.username})>"


class RefreshToken(Base):
    """Refresh token model for token management"""
    __tablename__ = "refresh_tokens"
    __table_args__ = {'extend_existing': True}

    id = Column(INTEGER(unsigned=True), primary_key=True, autoincrement=True)
    user_id = Column(INTEGER(unsigned=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token = Column(String(500), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)
    is_revoked = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    revoked_at = Column(DateTime, nullable=True)
    user_agent = Column(String(500), nullable=True)
    ip_address = Column(String(45), nullable=True)

    # Relationships
    user = relationship("User", back_populates="refresh_tokens")

    def __repr__(self):
        return f"<RefreshToken(id={self.id}, user_id={self.user_id}, revoked={self.is_revoked})>"

    @property
    def is_expired(self) -> bool:
        """Check if token is expired"""
        return datetime.utcnow() > self.expires_at

    @property
    def is_valid(self) -> bool:
        """Check if token is valid (not expired and not revoked)"""
        return not self.is_expired and not self.is_revoked
