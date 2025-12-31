"""
Centralized configuration management for microservices.

Uses pydantic-settings for environment variable binding and validation.
"""

from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseConfig(BaseSettings):
    """Database configuration."""

    model_config = SettingsConfigDict(env_prefix="DB_")

    host: str = Field(default="localhost", description="Database host")
    port: int = Field(default=3306, description="Database port")
    user: str = Field(default="root", description="Database user")
    password: str = Field(default="", description="Database password")
    name: str = Field(default="stockdb", description="Database name")
    pool_size: int = Field(default=5, description="Connection pool size")
    pool_timeout: int = Field(default=30, description="Pool timeout in seconds")
    echo: bool = Field(default=False, description="Echo SQL queries")

    @property
    def url(self) -> str:
        """Get async database URL."""
        return f"mysql+asyncmy://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"

    @property
    def sync_url(self) -> str:
        """Get sync database URL."""
        return f"mysql+pymysql://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"


class RabbitMQConfig(BaseSettings):
    """RabbitMQ configuration."""

    model_config = SettingsConfigDict(env_prefix="RABBITMQ_")

    host: str = Field(default="localhost", description="RabbitMQ host")
    port: int = Field(default=5672, description="RabbitMQ AMQP port")
    user: str = Field(default="guest", description="RabbitMQ user")
    password: str = Field(default="guest", description="RabbitMQ password")
    vhost: str = Field(default="/", description="RabbitMQ virtual host")
    exchange: str = Field(default="stock_events", description="Default exchange name")
    prefetch_count: int = Field(default=10, description="Prefetch count for consumers")

    @property
    def url(self) -> str:
        """Get RabbitMQ connection URL."""
        return f"amqp://{self.user}:{self.password}@{self.host}:{self.port}/{self.vhost}"


class RedisConfig(BaseSettings):
    """Redis configuration."""

    model_config = SettingsConfigDict(env_prefix="REDIS_")

    host: str = Field(default="localhost", description="Redis host")
    port: int = Field(default=6379, description="Redis port")
    password: Optional[str] = Field(default=None, description="Redis password")
    db: int = Field(default=0, description="Redis database number")
    ssl: bool = Field(default=False, description="Use SSL connection")

    @property
    def url(self) -> str:
        """Get Redis connection URL."""
        scheme = "rediss" if self.ssl else "redis"
        auth = f":{self.password}@" if self.password else ""
        return f"{scheme}://{auth}{self.host}:{self.port}/{self.db}"


class JWTConfig(BaseSettings):
    """JWT authentication configuration."""

    model_config = SettingsConfigDict(env_prefix="JWT_")

    secret_key: str = Field(default="change-me-in-production", description="JWT secret key")
    algorithm: str = Field(default="HS256", description="JWT algorithm")
    access_token_expire_minutes: int = Field(default=30, description="Access token expiry")
    refresh_token_expire_days: int = Field(default=7, description="Refresh token expiry")


class TracingConfig(BaseSettings):
    """Distributed tracing configuration."""

    model_config = SettingsConfigDict(env_prefix="TRACING_")

    enabled: bool = Field(default=True, description="Enable tracing")
    jaeger_host: str = Field(default="localhost", description="Jaeger host")
    jaeger_port: int = Field(default=6831, description="Jaeger UDP port")
    sample_rate: float = Field(default=1.0, description="Trace sample rate (0.0-1.0)")


class ResilienceConfig(BaseSettings):
    """Resilience patterns configuration."""

    model_config = SettingsConfigDict(env_prefix="RESILIENCE_")

    circuit_breaker_failure_threshold: int = Field(
        default=5, description="Failures before circuit opens"
    )
    circuit_breaker_recovery_timeout: int = Field(
        default=30, description="Seconds before circuit half-opens"
    )
    retry_max_attempts: int = Field(default=3, description="Maximum retry attempts")
    retry_min_wait: float = Field(default=1.0, description="Minimum wait between retries (seconds)")
    retry_max_wait: float = Field(default=10.0, description="Maximum wait between retries (seconds)")
    timeout_default: float = Field(default=30.0, description="Default request timeout (seconds)")
    bulkhead_max_concurrent: int = Field(default=10, description="Max concurrent requests per bulkhead")


class ServiceConfig(BaseSettings):
    """Main service configuration aggregating all configs."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Service identity
    service_name: str = Field(default="unknown-service", description="Service name")
    service_version: str = Field(default="0.1.0", description="Service version")
    environment: str = Field(default="development", description="Environment (development/staging/production)")
    debug: bool = Field(default=False, description="Debug mode")

    # Server settings
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, description="Server port")
    workers: int = Field(default=1, description="Number of workers")

    # Sub-configurations
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    rabbitmq: RabbitMQConfig = Field(default_factory=RabbitMQConfig)
    redis: RedisConfig = Field(default_factory=RedisConfig)
    jwt: JWTConfig = Field(default_factory=JWTConfig)
    tracing: TracingConfig = Field(default_factory=TracingConfig)
    resilience: ResilienceConfig = Field(default_factory=ResilienceConfig)

    # Service discovery URLs (for inter-service communication)
    auth_service_url: str = Field(default="http://auth-service:8007", description="Auth service URL")
    stock_data_service_url: str = Field(default="http://stock-data-service:8001", description="Stock data service URL")
    portfolio_service_url: str = Field(default="http://portfolio-service:8003", description="Portfolio service URL")
    analysis_service_url: str = Field(default="http://analysis-service:8004", description="Analysis service URL")
    prediction_service_url: str = Field(default="http://prediction-service:8002", description="Prediction service URL")
    ai_insights_service_url: str = Field(default="http://ai-insights-service:8005", description="AI insights service URL")
    chatbot_service_url: str = Field(default="http://chatbot-service:8006", description="Chatbot service URL")


@lru_cache()
def get_config() -> ServiceConfig:
    """Get cached service configuration."""
    return ServiceConfig()
