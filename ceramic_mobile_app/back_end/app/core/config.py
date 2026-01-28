from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Optional
import os
from urllib.parse import quote_plus

class Settings(BaseSettings):
    # Database individual components
    DB_USER: str = "ceramic_user"
    DB_PASSWORD: str = "Mysql_2025"
    DB_HOST: str = "db"
    DB_PORT: int = 3306
    DB_NAME: str = "ceramic_marketplace"

    # Constructed DATABASE_URL with proper URL encoding
    @property
    def DATABASE_URL(self) -> str:
        password_encoded = quote_plus(self.DB_PASSWORD)
        return f"mysql+pymysql://{self.DB_USER}:{password_encoded}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    # Security
    SECRET_KEY: str = "your-secret-key-here-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # Email verification
    EMAIL_VERIFICATION_EXPIRE_HOURS: int = 24

    # Password reset
    PASSWORD_RESET_EXPIRE_HOURS: int = 5

    # Password requirements
    MIN_PASSWORD_LENGTH: int = 8

    # Environment
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # CORS
    ALLOWED_HOSTS: List[str] = ["*"]

    # File Upload
    UPLOAD_DIR: str = "uploads"
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB

    # Email Configuration
    SMTP_SERVER: str = ""
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = ""
    SMTP_FROM_NAME: str = "Ceramic Marketplace"

    # Redis Configuration
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None

    # Cache TTL Settings (in seconds)
    CACHE_TTL_PRODUCTS: int = 300  # 5 minutes
    CACHE_TTL_CATEGORIES: int = 3600  # 1 hour
    CACHE_TTL_FEATURED: int = 180  # 3 minutes
    CACHE_TTL_HOME: int = 120  # 2 minutes

    @property
    def REDIS_URL(self) -> str:
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"  # Allow extra fields from .env without validation errors
    )

settings = Settings()