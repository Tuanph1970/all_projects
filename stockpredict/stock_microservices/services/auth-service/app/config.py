"""
Auth Service Configuration
"""
from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    """Service configuration from environment variables"""

    # Service Identity
    SERVICE_NAME: str = "auth-service"
    SERVICE_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    API_PREFIX: str = "stock_helper"

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8007

    # Database
    DATABASE_HOST: str = "mysql"
    DATABASE_PORT: int = 3306
    DATABASE_USER: str = "root"
    DATABASE_PASSWORD: str = "Mysql_2025"
    DATABASE_NAME: str = "auth_db"
    DATABASE_POOL_SIZE: int = 5
    DATABASE_POOL_TIMEOUT: int = 30

    # JWT
    JWT_SECRET_KEY: str = "your-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # RabbitMQ
    RABBITMQ_HOST: str = "rabbitmq"
    RABBITMQ_PORT: int = 5672
    RABBITMQ_USER: str = "stockuser"
    RABBITMQ_PASSWORD: str = "stockpass"
    RABBITMQ_VHOST: str = "/stock"

    # Redis
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: Optional[str] = None

    # SMTP / Email (password reset)
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USERNAME: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_USE_TLS: bool = True
    SMTP_FROM_EMAIL: str = "no-reply@stockhelper.local"
    SMTP_FROM_NAME: str = "Stock Helper"
    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int = 30
    FRONTEND_BASE_URL: str = "http://localhost:3004"
    FRONTEND_RESET_PATH: str = "/stock-app/reset-password"

    # Tracing
    TRACING_ENABLED: bool = True
    TRACING_JAEGER_HOST: str = "jaeger"
    TRACING_JAEGER_PORT: int = 6831
    TRACING_SAMPLE_RATE: float = 1.0

    @property
    def database_url(self) -> str:
        """Async database URL"""
        return (
            f"mysql+asyncmy://{self.DATABASE_USER}:{self.DATABASE_PASSWORD}"
            f"@{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME}"
        )

    @property
    def sync_database_url(self) -> str:
        """Sync database URL for migrations"""
        return (
            f"mysql+pymysql://{self.DATABASE_USER}:{self.DATABASE_PASSWORD}"
            f"@{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME}"
        )

    @property
    def rabbitmq_url(self) -> str:
        """RabbitMQ connection URL"""
        return (
            f"amqp://{self.RABBITMQ_USER}:{self.RABBITMQ_PASSWORD}"
            f"@{self.RABBITMQ_HOST}:{self.RABBITMQ_PORT}{self.RABBITMQ_VHOST}"
        )

    @property
    def redis_url(self) -> str:
        """Redis connection URL"""
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/0"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/0"

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # Allow extra environment variables


_PLACEHOLDER_JWT_SECRET = "your-secret-key-change-in-production"
_PLACEHOLDER_DB_PASSWORD = "Mysql_2025"


def _validate_secrets(s: "Settings") -> None:
    """Refuse to start in non-development environments with placeholder secrets.
    Documented in SECURITY_AUDIT.md (HIGH #1, #2)."""
    if s.ENVIRONMENT == "development":
        return  # local dev convenience
    problems = []
    if s.JWT_SECRET_KEY == _PLACEHOLDER_JWT_SECRET:
        problems.append("JWT_SECRET_KEY is unset (still default placeholder)")
    if s.DATABASE_PASSWORD == _PLACEHOLDER_DB_PASSWORD:
        problems.append("DATABASE_PASSWORD is unset (still default placeholder)")
    if problems:
        raise RuntimeError(
            "auth-service refuses to start with default secrets in environment "
            f"'{s.ENVIRONMENT}'. Set the env vars: " + ", ".join(problems)
        )


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    s = Settings()
    _validate_secrets(s)
    return s
