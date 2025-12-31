"""
User model for Auth Service
Re-exports from shared models
"""
from shared.models.user import User, UserRole

__all__ = ["User", "UserRole"]
