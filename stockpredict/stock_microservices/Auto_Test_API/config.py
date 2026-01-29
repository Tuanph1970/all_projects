"""
Configuration for Auto_Test_API
"""
import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """API Testing Configuration"""

    # Base URL Configuration
    # Via Traefik (default - port 8004)
    BASE_URL: str = "http://localhost:8004/stock_helper/api/v2"

    # Direct service URLs (for debugging)
    AUTH_SERVICE_URL: str = "http://localhost:8007/stock_helper/api/v2"
    STOCK_DATA_SERVICE_URL: str = "http://localhost:8001/stock_helper/api/v2"
    PORTFOLIO_SERVICE_URL: str = "http://localhost:8003/stock_helper/api/v2"
    PREDICTION_SERVICE_URL: str = "http://localhost:8002/stock_helper/api/v2"
    ANALYSIS_SERVICE_URL: str = "http://localhost:8004/stock_helper/api/v2"
    AI_INSIGHTS_SERVICE_URL: str = "http://localhost:8005/stock_helper/api/v2"
    CHATBOT_SERVICE_URL: str = "http://localhost:8006/stock_helper/api/v2"

    # Test User Credentials (will be created during testing)
    TEST_USER_EMAIL: str = "autotest@stockhelper.com"
    TEST_USER_USERNAME: str = "autotest_user"
    TEST_USER_PASSWORD: str = "AutoTest@123"
    TEST_USER_FULL_NAME: str = "Auto Test User"

    # Admin User (if needed)
    ADMIN_EMAIL: str = "admin@stockhelper.com"
    ADMIN_PASSWORD: str = "Admin@123"

    # Test Data
    TEST_STOCK_SYMBOL: str = "VNM"  # Vietnam Dairy Products
    TEST_STOCK_SYMBOLS: list = ["VNM", "FPT", "VIC", "HPG", "VCB"]

    # Timeouts
    REQUEST_TIMEOUT: int = 30
    LONG_REQUEST_TIMEOUT: int = 120

    # Test Settings
    VERBOSE: bool = True
    CLEANUP_AFTER_TEST: bool = True

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


def get_settings() -> Settings:
    """Get settings instance"""
    return Settings()


settings = get_settings()
