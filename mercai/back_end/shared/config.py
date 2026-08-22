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
    AI_SERVICE_URL: str = "http://ai-service:8006"

    # --- AI / LLM ---------------------------------------------------------
    # Ollama runs on the Docker host; services already use host.docker.internal
    # for host-side dependencies (see docker-compose extra_hosts).
    OLLAMA_BASE_URL: str = "http://host.docker.internal:11434"
    OLLAMA_MODEL: str = "qwen2.5:14b-instruct-q4_K_M"
    OLLAMA_TIMEOUT_SECONDS: int = 45
    # A single Ollama instance serialises work; shed load rather than queue.
    AI_MAX_CONCURRENT_GENERATIONS: int = 4

    # Feature flags (default off -- see docs/ai-features/02-listing-optimizer.md)
    AI_LISTING_OPTIMIZER_ENABLED: bool = False
    AI_CHAT_COPILOT_ENABLED: bool = False
    AI_REVIEW_INTELLIGENCE_ENABLED: bool = False

    # Per-seller quotas, enforced in Redis
    AI_QUOTA_PER_HOUR: int = 20
    AI_QUOTA_PER_DAY: int = 100

    # Cache TTL for generated suggestions
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
