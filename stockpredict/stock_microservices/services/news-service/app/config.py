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
    # Forward-return scoring of stored TCBS calls (FR-BM-SCORE). Cheap and local to
    # the calls already stored, so on by default; degrades to a no-op with no calls.
    ENABLE_SCORING: bool = True

    # Poll cadence (seconds).
    COMPANY_POLL_INTERVAL_SECONDS: int = 900   # 15 min
    MACRO_POLL_INTERVAL_SECONDS: int = 1800    # 30 min
    # Horizons fill as sessions elapse, so a few passes a day is ample.
    SCORING_INTERVAL_SECONDS: int = 21600      # 6 h
    # The index every call is measured against (EC-B7's benchmark).
    MARKET_INDEX_SYMBOL: str = "VNINDEX"
    # Below this many scored calls the track record is not reportable (FR-BM-RECORD).
    SCORING_MIN_CALLS: int = 30

    # --- Broker mail intake, phase E1 (FR-BM-INTAKE, EC-B1) ----------------
    # `ENABLE_EMAIL` above is the stream toggle. SRS Appendix C names the default
    # `BROKER_MAIL_ENABLED`, but ENABLE_EMAIL already exists here, is already plumbed
    # through both compose files, and was reserved for exactly this stream — two flags
    # meaning one thing is how a feature ends up half-on.
    #
    # Credentials address the DEDICATED ingestion mailbox and nothing else (EC-B1): the
    # service must never hold credentials to an inbox carrying personal mail. Env only —
    # there is no secret store yet (Backlog #24).
    BROKER_MAIL_HOST: str = ""
    BROKER_MAIL_PORT: int = 993
    BROKER_MAIL_USER: str = ""
    BROKER_MAIL_PASSWORD: str = ""
    BROKER_MAIL_FOLDER: str = "INBOX"
    # Appendix B's sender allow-list, as globs. The forwarding address is
    # deployment-specific — a Gmail filter rewrites `From` to the forwarder — so it is
    # appended here per deployment rather than hardcoded.
    BROKER_MAIL_ALLOW_FROM: str = "*@tcbs.com.vn"
    BROKER_MAIL_SOURCE_KEY: str = "tcbs.daily"
    BROKER_MAIL_POLL_INTERVAL_SECONDS: int = 1800   # SRS Appendix C
    # How far back each scheduled tick looks. Dedupe makes the overlap free, so this only
    # has to exceed the longest outage we expect to sleep through.
    BROKER_MAIL_LOOKBACK_DAYS: int = 7

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

    @property
    def broker_mail_allow_from(self) -> list[str]:
        return [p.strip() for p in self.BROKER_MAIL_ALLOW_FROM.split(",") if p.strip()]

    @property
    def broker_mail_configured(self) -> bool:
        """True once the mailbox is actually addressable. Kept separate from
        ENABLE_EMAIL so "switched on but not configured" is a distinguishable state
        rather than a confusing connection error on every tick."""
        return bool(self.BROKER_MAIL_HOST and self.BROKER_MAIL_USER
                    and self.BROKER_MAIL_PASSWORD)

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
