"""
Shared module for Mercai Microservices
Contains common utilities, models, and configurations shared across all services
"""

from .database import Base, get_db, engine, SessionLocal
from .config import settings
from .security import (
    verify_password,
    get_password_hash,
    validate_password,
    create_access_token,
    create_refresh_token,
    create_email_verification_token,
    verify_token,
    generate_password_reset_token,
    get_current_user,
    get_optional_current_user,
    get_user_from_token,
    get_current_active_user,
    oauth2_scheme
)

__all__ = [
    # Database
    "Base",
    "get_db",
    "engine",
    "SessionLocal",
    # Config
    "settings",
    # Security
    "verify_password",
    "get_password_hash",
    "validate_password",
    "create_access_token",
    "create_refresh_token",
    "create_email_verification_token",
    "verify_token",
    "generate_password_reset_token",
    "get_current_user",
    "get_optional_current_user",
    "get_user_from_token",
    "get_current_active_user",
    "oauth2_scheme"
]
