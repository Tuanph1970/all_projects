"""
Models module for Auth Service
Re-exports shared models for compatibility
"""
from shared.models import User, UserRole

__all__ = ["User", "UserRole"]
