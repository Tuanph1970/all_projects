"""News-service configuration.

Two ingestion streams share one service:
  - Stream B (company): per-ticker good/bad news for owned/watched symbols -> classify
    (ai-insights) -> notify (portfolio-service). On by default.
  - Stream A (macro): global economic/political events from feeds/APIs -> news_events
    corpus for ML + bridge to event-reaction. Off until sources are configured.

All secrets/keys come from env (EC-N9); feeds/APIs only, never scraping (EC-N1).
"""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    SERVICE_NAME: str = "news-service"
    SERVICE_VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    API_PREFIX: str = "stock_helper"
    HOST: str = "0.0.0.0"
    PORT: int = 8013

    # Upstream services (EC-N4 notify, EC-N5 classify, EC-N10 watch, bridge).
    STOCK_DATA_SERVICE_URL: str = "http://stock-data-service:8001"
    AI_INSIGHTS_SERVICE_URL: str = "http://ai-insights-service:8005"
    PORTFOLIO_SERVICE_URL: str = "http://portfolio-service:8003"
    DECISION_HELPER_SERVICE_URL: str = "http://decision-helper-service:8010"
    EVENT_REACTION_SERVICE_URL: str = "http://event-reaction-service:8012"
    HTTP_TIMEOUT_SECONDS: float = 10.0

    # News corpus (system of record for news). Compose supplies a MySQL URL; sqlite
    # is a local/test fallback.
    DATABASE_URL: str = "sqlite:///./news.db"

    # Event bus (news.company emission — wired in N6).
    RABBITMQ_URL: str = "amqp://stockuser:stockpass@rabbitmq:5672/stock"

    # Stream toggles (NFR-N5). Company on; macro/bridge/email deferred until configured.
    ENABLE_COMPANY: bool = True
    ENABLE_MACRO: bool = False
    ENABLE_BRIDGE: bool = False
    ENABLE_EMAIL: bool = False

    # Poll cadence (seconds).
    COMPANY_POLL_INTERVAL_SECONDS: int = 900   # 15 min
    MACRO_POLL_INTERVAL_SECONDS: int = 1800    # 30 min

    # Only these sentiments trigger a notification (good/bad only — EC-N8).
    NOTIFY_SENTIMENTS: str = "good,bad"

    # Path to the macro source registry (Stream A, N11). Empty until configured.
    FEED_REGISTRY_PATH: str = ""

    # JWT (shared secret; validation via stock_common in non-dev environments).
    JWT_SECRET_KEY: str = "your-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"

    CORS_ORIGINS: str = "http://localhost:3004,http://localhost:3000"

    TRACING_ENABLED: bool = True
    TRACING_JAEGER_HOST: str = "jaeger"
    TRACING_JAEGER_PORT: int = 6831

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def notify_sentiments(self) -> list[str]:
        return [s.strip() for s in self.NOTIFY_SENTIMENTS.split(",") if s.strip()]

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    s = Settings()
    # Same stock-common secrets touchpoint as sibling services, enforced only outside
    # dev/test so the service stays runnable/offline-testable by default.
    if s.ENVIRONMENT not in ("development", "test"):
        try:
            from stock_common.secrets_validation import assert_no_placeholder_secrets

            assert_no_placeholder_secrets(s, service_name=s.SERVICE_NAME)
        except ImportError:
            pass
    return s
