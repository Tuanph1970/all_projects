"""
Configuration module for handling environment variables and settings
"""
import os
from typing import List, Optional
from pydantic import BaseSettings, validator
from functools import lru_cache


class Settings(BaseSettings):
    # Application
    app_name: str = "Mercai API"
    app_version: str = "1.0.0"
    environment: str = "production"
    debug: bool = False
    
    # Database
    db_host: str = "localhost"
    db_port: int = 3306
    db_name: str = "mercai"
    db_user: str = "fastapi_user"
    db_password: str = "changeme"
    database_url: Optional[str] = None
    
    # Security
    secret_key: str = "your-secret-key-here"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    
    # Server
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    workers: int = 4
    
    # CORS
    cors_origins: List[str] = ["http://localhost:3000", "http://localhost:8080"]
    cors_allow_credentials: bool = True
    cors_allow_methods: List[str] = ["*"]
    cors_allow_headers: List[str] = ["*"]
    
    # File Upload
    upload_dir: str = "uploads"
    max_file_size: int = 10485760  # 10MB
    allowed_extensions: List[str] = ["jpg", "jpeg", "png", "gif", "pdf", "doc", "docx"]
    
    # Email (Optional)
    smtp_server: Optional[str] = None
    smtp_port: int = 587
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_tls: bool = True
    smtp_ssl: bool = False
    mail_from: str = "noreply@mercai.com"
    mail_from_name: str = "Mercai"
    
    # Redis (Optional)
    redis_host: str = "redis"
    redis_port: int = 6379
    redis_db: int = 0
    
    # Logging
    log_level: str = "INFO"
    log_format: str = "json"
    log_file: str = "logs/app.log"
    
    # Pagination
    default_page_size: int = 20
    max_page_size: int = 100
    
    # API Documentation
    enable_docs: bool = True
    enable_redoc: bool = True
    enable_openapi: bool = True
    
    # Rate Limiting
    rate_limit_enabled: bool = True
    rate_limit_per_minute: int = 60
    
    # Monitoring
    sentry_dsn: Optional[str] = None
    
    # AWS (Optional)
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    aws_region: str = "us-east-1"
    s3_bucket_name: Optional[str] = None
    
    @validator("database_url", pre=True)
    def construct_db_url(cls, v, values):
        if v:
            return v
        return f"mysql+pymysql://{values.get('db_user')}:{values.get('db_password')}@{values.get('db_host')}:{values.get('db_port')}/{values.get('db_name')}"
    
    @validator("cors_origins", pre=True)
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            import json
            try:
                return json.loads(v)
            except:
                return [v]
        return v
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings():
    """
    Create cached settings instance
    """
    return Settings()


# Create settings instance
settings = get_settings()

# Convenience functions for different environments
def is_production():
    return settings.environment.lower() == "production"

def is_development():
    return settings.environment.lower() == "development"

def is_testing():
    return settings.environment.lower() == "testing"