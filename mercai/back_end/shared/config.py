"""
Shared configuration for Mercai Microservices
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Optional
import os


class Settings(BaseSettings):
    # Service identification
    SERVICE_NAME: str = "mercai-service"
    SERVICE_PORT: int = 8000

    # Database configuration
    DB_USER: str = "mercai_user"
    DB_PASSWORD: str = "Mysql_2025"
    DB_HOST: str = "db"
    DB_PORT: int = 3306
    DB_NAME: str = "mercai"

    # Security
    SECRET_KEY: str = "your-secret-key-here-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # Email verification
    EMAIL_VERIFICATION_EXPIRE_HOURS: int = 24

    # Email Configuration (SMTP)
    SMTP_SERVER: str = ""
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = "noreply@mercai.com"
    SMTP_FROM_NAME: str = "Mercai"

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
    SMTP_FROM_NAME: str = "Mercai"

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

    # Inter-service communication
    AUTH_SERVICE_URL: str = "http://auth-service:8001"
    PRODUCT_SERVICE_URL: str = "http://product-service:8002"
    ORDER_SERVICE_URL: str = "http://order-service:8003"
    CHAT_SERVICE_URL: str = "http://chat-service:8004"
    SELLER_SERVICE_URL: str = "http://seller-service:8005"
    INTEL_SERVICE_URL: str = "http://intel-service:8006"

    # --- Intel (price & market intelligence) ------------------------------
    # No model settings live here any more. The Ollama client and the three LLM
    # features it served were removed on 2026-08-27 -- the deploy target cannot
    # run a model. See docs/ai-features/05-price-intelligence.md section 2.1.

    # Feature flag (default off -- staged per seller via the Redis allowlist)
    INTEL_PRICE_ENABLED: bool = False

    # Per-seller quotas, enforced in Redis. Kept generic: they bound expensive
    # operations, and outbound fetches are the expensive operation now.
    AI_QUOTA_PER_HOUR: int = 20
    AI_QUOTA_PER_DAY: int = 100

    # Market stats move whenever any seller edits a price, so the position
    # payload is cached briefly rather than not at all.
    CACHE_TTL_INTEL_POSITION: int = 300  # 5 minutes

    # Cache TTL for computed suggestions.
    # These three keep their AI_ / _AI_ names because they are tied to the
    # `ai_suggestions` table, which keeps its name -- it still holds the
    # listing optimizer's real rollout history and is feature-keyed, so price
    # intelligence writes to it rather than to a new table.
    CACHE_TTL_AI_SUGGESTION: int = 86400  # 24 hours

    @property
    def DATABASE_URL(self) -> str:
        from urllib.parse import quote_plus
        password_encoded = quote_plus(self.DB_PASSWORD)
        return f"mysql+pymysql://{self.DB_USER}:{password_encoded}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    @property
    def REDIS_URL(self) -> str:
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )


settings = Settings()
