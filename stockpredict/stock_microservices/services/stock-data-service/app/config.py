"""
Stock Data Service Configuration
"""
from pydantic import field_validator
from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    """Service configuration from environment variables"""

    # Service Identity
    SERVICE_NAME: str = "stock-data-service"
    SERVICE_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    API_PREFIX: str = "stock_helper"

    # Backlog #87 — how much history an ingest pulls.
    #
    # This was hardcoded at 5 years, inherited from the monolith's
    # DEFAULT_YEARS_HISTORY, and the vendor is not the constraint: VCI returns
    # FPT from 2009-03-27 (4,380 bars) and VNINDEX from 2008-02-18 (4,641).
    #
    # The depth matters beyond tidiness. EM-4's test of E&M's claim that
    # "all major stock market Bottoms have corresponded with extremely low MEI
    # readings" came back n=2 at the 60-session horizon, because 5.3 years of
    # VN data contains exactly ONE bear market where E&M spoke of 20 years.
    # The claim was untestable for want of history, not refuted.
    HISTORY_YEARS: int = 5

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8001

    # Database
    DATABASE_HOST: str = "mysql"
    DATABASE_PORT: int = 3306
    DATABASE_USER: str = "root"
    DATABASE_PASSWORD: str = "Mysql_2025"
    DATABASE_NAME: str = "stockdata_db"
    DATABASE_POOL_SIZE: int = 10
    DATABASE_POOL_TIMEOUT: int = 30

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
    CACHE_TTL: int = 300  # 5 minutes default cache

    # JWT — shared secret with auth-service for validating bearer tokens.
    # Currently only used to gate admin endpoints (/companies/sync,
    # /priceboards/refresh). SECURITY_AUDIT.md HIGH #4.
    JWT_SECRET_KEY: str = "your-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"

    # VNStock Configuration
    VNSTOCK_DATA_SOURCE: str = "VCI"
    # vnstock 4.x (via its `vnai` dependency) enforces a client-side quota:
    # Guest = 20 req/min, free Community key = 60 req/min. vnai reads the key
    # from the VNSTOCK_API_KEY env var itself; we only use it to pick a default
    # spacing between calls. Get a key at https://vnstocks.com/login
    VNSTOCK_API_KEY: Optional[str] = None
    # Minimum seconds between two vnstock calls. None = derive from the tier
    # (3.1s guest / 1.05s with key), i.e. just under the per-minute quota.
    VNSTOCK_MIN_INTERVAL_SECONDS: Optional[float] = None
    # On RateLimitExceeded, sleep for vnai's retry_after and try once more.
    VNSTOCK_RATE_LIMIT_RETRY: bool = True
    VNSTOCK_RATE_LIMIT_MAX_WAIT_SECONDS: float = 90.0

    @field_validator("VNSTOCK_API_KEY", "VNSTOCK_MIN_INTERVAL_SECONDS", mode="before")
    @classmethod
    def _blank_env_is_unset(cls, v):
        """docker-compose passes `${VAR:-}` through as "" — treat as None."""
        if isinstance(v, str) and v.strip() == "":
            return None
        return v

    @property
    def vnstock_min_interval(self) -> float:
        if self.VNSTOCK_MIN_INTERVAL_SECONDS is not None:
            return self.VNSTOCK_MIN_INTERVAL_SECONDS
        return 1.05 if self.VNSTOCK_API_KEY else 3.1

    # Company data sync
    COMPANY_SYNC_STALE_DAYS: int = 7

    # Backlog #48 — during trading hours a price board row older than this is
    # refetched on read (one Vietcap POST; not vnstock, so no quota cost).
    PRICE_BOARD_MAX_AGE_SECONDS: int = 60

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
        """Sync database URL"""
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


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance, validated against placeholder secrets."""
    from stock_common.secrets_validation import assert_no_placeholder_secrets
    s = Settings()
    assert_no_placeholder_secrets(s, service_name="stock-data-service")
    return s
