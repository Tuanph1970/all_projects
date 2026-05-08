"""Application configuration via pydantic-settings."""
from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Service configuration from environment variables."""

    # Service info
    SERVICE_NAME: str = "knowledge-qa-service"
    SERVICE_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    HOST: str = "0.0.0.0"
    PORT: int = 8009
    API_PREFIX: str = "stock_helper"

    # Neo4j
    NEO4J_URI: str = "bolt://host.docker.internal:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "neo4jabc"

    # Ollama
    OLLAMA_BASE_URL: str = "http://ollama:11434"
    OLLAMA_MODEL: str = "llama3.1"
    OLLAMA_TIMEOUT: float = 120.0

    # CORS — comma-separated list of allowed origins. Wildcard with credentials
    # is unsafe (CSRF risk); SECURITY_AUDIT.md HIGH #3.
    CORS_ORIGINS: str = "http://localhost:3004,http://localhost:3000"

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    # Tracing
    TRACING_ENABLED: bool = True
    TRACING_JAEGER_HOST: str = "jaeger"
    TRACING_JAEGER_PORT: int = 6831

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance, validated against placeholder secrets."""
    from stock_common.secrets_validation import assert_no_placeholder_secrets
    s = Settings()
    assert_no_placeholder_secrets(s, service_name="knowledge-qa-service")
    return s
