"""Analysis Service Configuration"""
from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    SERVICE_NAME: str = "analysis-service"
    SERVICE_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    API_PREFIX: str = "stock_helper"
    HOST: str = "0.0.0.0"
    PORT: int = 8004

    # Database
    DATABASE_HOST: str = "mysql"
    DATABASE_PORT: int = 3306
    DATABASE_USER: str = "root"
    DATABASE_PASSWORD: str = "Mysql_2025"
    DATABASE_NAME: str = "analysis_db"
    DATABASE_POOL_SIZE: int = 10

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
    CACHE_TTL: int = 300  # 5 minutes

    # JWT
    JWT_SECRET_KEY: str = "your-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"

    # Service URLs
    STOCK_DATA_SERVICE_URL: str = "http://stock-data-service:8001"

    # Tracing
    TRACING_ENABLED: bool = True
    TRACING_JAEGER_HOST: str = "jaeger"
    TRACING_JAEGER_PORT: int = 6831

    @property
    def database_url(self) -> str:
        return f"mysql+asyncmy://{self.DATABASE_USER}:{self.DATABASE_PASSWORD}@{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME}"

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
