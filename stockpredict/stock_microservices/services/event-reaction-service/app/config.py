"""Event-Reaction Service configuration."""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    SERVICE_NAME: str = "event-reaction-service"
    SERVICE_VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    API_PREFIX: str = "stock_helper"
    HOST: str = "0.0.0.0"
    PORT: int = 8012

    # Upstream price data
    STOCK_DATA_SERVICE_URL: str = "http://stock-data-service:8001"

    # Event store (system of record). Compose supplies a MySQL URL; sqlite is a
    # local/test fallback.
    DATABASE_URL: str = "sqlite:///./event_reaction.db"

    # JWT (shared secret; validation via stock_common in non-dev environments)
    JWT_SECRET_KEY: str = "your-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"

    CORS_ORIGINS: str = "http://localhost:3004,http://localhost:3000"

    TRACING_ENABLED: bool = True
    TRACING_JAEGER_HOST: str = "jaeger"
    TRACING_JAEGER_PORT: int = 6831

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    s = Settings()
    # Same stock-common secrets touchpoint as sibling services, but only enforced
    # outside dev/test so the service stays runnable/offline-testable by default.
    if s.ENVIRONMENT not in ("development", "test"):
        try:
            from stock_common.secrets_validation import assert_no_placeholder_secrets

            assert_no_placeholder_secrets(s, service_name=s.SERVICE_NAME)
        except ImportError:
            pass
    return s
