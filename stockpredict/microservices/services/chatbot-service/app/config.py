"""Chatbot Service Configuration"""
from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    SERVICE_NAME: str = "chatbot-service"
    SERVICE_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    API_PREFIX: str = "stock_helper"
    HOST: str = "0.0.0.0"
    PORT: int = 8006

    # Redis
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: Optional[str] = None

    # JWT
    JWT_SECRET_KEY: str = "your-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"

    # Service URLs
    STOCK_DATA_SERVICE_URL: str = "http://stock-data-service:8001"
    ANALYSIS_SERVICE_URL: str = "http://analysis-service:8004"
    PREDICTION_SERVICE_URL: str = "http://prediction-service:8002"
    AI_INSIGHTS_SERVICE_URL: str = "http://ai-insights-service:8005"

    # LLM Configuration
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    LLM_MODEL: str = "gpt-4"
    LLM_TEMPERATURE: float = 0.7

    # Conversation
    MAX_CONVERSATION_HISTORY: int = 20
    SESSION_TIMEOUT_MINUTES: int = 30

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
