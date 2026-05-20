"""Decision Helper Service Configuration"""
from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    SERVICE_NAME: str = "decision-helper-service"
    SERVICE_VERSION: str = "0.2.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    API_PREFIX: str = "stock_helper"
    HOST: str = "0.0.0.0"
    PORT: int = 8010

    # Database
    DATABASE_HOST: str = "host.docker.internal"
    DATABASE_PORT: int = 3306
    DATABASE_USER: str = "root"
    DATABASE_PASSWORD: str = "Mysql_2025"
    DATABASE_NAME: str = "stockpredict"
    DATABASE_POOL_SIZE: int = 10

    # Redis
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: Optional[str] = None
    CACHE_TTL: int = 300

    # RabbitMQ
    RABBITMQ_HOST: str = "rabbitmq"
    RABBITMQ_PORT: int = 5672
    RABBITMQ_USER: str = "stockuser"
    RABBITMQ_PASSWORD: str = "stockpass"
    RABBITMQ_VHOST: str = "/stock"

    # JWT
    JWT_SECRET_KEY: str = "your-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"

    # Upstream service URLs (gateway timeout budgets per ADR §2.7)
    STOCK_DATA_SERVICE_URL: str = "http://stock-data-service:8001"
    ANALYSIS_SERVICE_URL: str = "http://analysis-service:8004"
    AI_INSIGHTS_SERVICE_URL: str = "http://ai-insights-service:8005"
    JOURNAL_SERVICE_URL: str = "http://journal-service:8008"

    MARKET_GATEWAY_TIMEOUT_MS: int = 800
    INDICATOR_GATEWAY_TIMEOUT_MS: int = 500
    PATTERN_GATEWAY_TIMEOUT_MS: int = 500
    JOURNAL_SYNC_TIMEOUT_S: float = 3.0

    # Tracing
    TRACING_ENABLED: bool = True
    TRACING_JAEGER_HOST: str = "jaeger"
    TRACING_JAEGER_PORT: int = 6831

    # CORS
    CORS_ORIGINS: str = "http://localhost:3004,http://localhost:3000"

    @property
    def database_url(self) -> str:
        return (
            f"mysql+asyncmy://{self.DATABASE_USER}:{self.DATABASE_PASSWORD}"
            f"@{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME}"
        )

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    from stock_common.secrets_validation import assert_no_placeholder_secrets
    s = Settings()
    assert_no_placeholder_secrets(s, service_name="decision-helper-service")
    return s
