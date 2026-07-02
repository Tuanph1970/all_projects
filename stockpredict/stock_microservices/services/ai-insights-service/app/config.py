"""AI Insights Service Configuration"""
from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    SERVICE_NAME: str = "ai-insights-service"
    SERVICE_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    API_PREFIX: str = "stock_helper"
    HOST: str = "0.0.0.0"
    PORT: int = 8005

    # Redis
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: Optional[str] = None
    CACHE_TTL: int = 3600

    # JWT
    JWT_SECRET_KEY: str = "your-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"

    # Service URLs
    STOCK_DATA_SERVICE_URL: str = "http://stock-data-service:8001"
    ANALYSIS_SERVICE_URL: str = "http://analysis-service:8004"
    PREDICTION_SERVICE_URL: str = "http://prediction-service:8002"

    # LLM Configuration
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    # auto = anthropic > openai > template; or pin explicitly
    LLM_PROVIDER: str = "auto"  # auto | anthropic | openai | template
    ANTHROPIC_MODEL: str = "claude-opus-4-7"
    LLM_MODEL: str = "gpt-4o-mini"  # used when provider falls back to OpenAI
    # OpenAI-compatible base URL. Point at any drop-in API (e.g. DeepSeek:
    # https://api.deepseek.com/v1 with LLM_MODEL=deepseek-chat).
    LLM_BASE_URL: str = "https://api.openai.com/v1"
    LLM_TEMPERATURE: float = 0.7
    LLM_MAX_TOKENS: int = 2000

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 10


    # CORS — comma-separated list of allowed origins. Wildcard with credentials
    # is unsafe (CSRF risk); SECURITY_AUDIT.md HIGH #3.
    CORS_ORIGINS: str = "http://localhost:3004,http://localhost:3000"

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance, validated against placeholder secrets."""
    from stock_common.secrets_validation import assert_no_placeholder_secrets
    s = Settings()
    assert_no_placeholder_secrets(s, service_name="ai-insights-service")
    return s
