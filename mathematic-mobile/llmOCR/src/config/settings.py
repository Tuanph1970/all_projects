"""
Configuration settings for the Mathematics LLM OCR Service.
"""
import os
from typing import Any, Dict, List, Optional
from pydantic import Field, validator
from pydantic_settings import BaseSettings


class DatabaseSettings(BaseSettings):
    """Database connection settings."""
    redis_url: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    redis_max_connections: int = Field(default=20, env="REDIS_MAX_CONNECTIONS")
    
    class Config:
        env_prefix = "DB_"


class MLModelSettings(BaseSettings):
    """Machine Learning model settings."""
    models_path: str = Field(default="./models", env="MODELS_PATH")
    device: str = Field(default="cpu", env="ML_DEVICE")  # cpu, cuda, mps
    
    # OCR Model Settings
    ocr_model_name: str = Field(default="microsoft/trocr-base-math", env="OCR_MODEL_NAME")
    ocr_confidence_threshold: float = Field(default=0.8, env="OCR_CONFIDENCE_THRESHOLD")
    ocr_max_image_size: int = Field(default=2048, env="OCR_MAX_IMAGE_SIZE")
    
    # LLM Settings
    llm_model_name: str = Field(default="microsoft/DialoGPT-medium", env="LLM_MODEL_NAME")
    llm_max_length: int = Field(default=512, env="LLM_MAX_LENGTH")
    llm_temperature: float = Field(default=0.7, env="LLM_TEMPERATURE")
    llm_top_p: float = Field(default=0.9, env="LLM_TOP_P")
    
    # Processing Settings
    batch_size: int = Field(default=1, env="ML_BATCH_SIZE")
    max_concurrent_requests: int = Field(default=10, env="ML_MAX_CONCURRENT")
    request_timeout_seconds: int = Field(default=30, env="ML_REQUEST_TIMEOUT")
    
    @validator("device")
    def validate_device(cls, v):
        import torch
        if v == "cuda" and not torch.cuda.is_available():
            return "cpu"
        elif v == "mps" and not torch.backends.mps.is_available():
            return "cpu"
        return v
    
    class Config:
        env_prefix = "ML_"


class APISettings(BaseSettings):
    """API server settings."""
    host: str = Field(default="0.0.0.0", env="API_HOST")
    port: int = Field(default=8000, env="API_PORT")
    debug: bool = Field(default=False, env="API_DEBUG")
    reload: bool = Field(default=False, env="API_RELOAD")
    workers: int = Field(default=1, env="API_WORKERS")
    
    # CORS Settings
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8080"],
        env="CORS_ORIGINS"
    )
    cors_allow_credentials: bool = Field(default=True, env="CORS_ALLOW_CREDENTIALS")
    cors_allow_methods: List[str] = Field(
        default=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        env="CORS_ALLOW_METHODS"
    )
    cors_allow_headers: List[str] = Field(default=["*"], env="CORS_ALLOW_HEADERS")
    
    # Rate Limiting
    rate_limit_requests: int = Field(default=100, env="RATE_LIMIT_REQUESTS")
    rate_limit_window: int = Field(default=60, env="RATE_LIMIT_WINDOW")  # seconds
    
    # File Upload Settings
    max_file_size: int = Field(default=10 * 1024 * 1024, env="MAX_FILE_SIZE")  # 10MB
    allowed_file_types: List[str] = Field(
        default=[".jpg", ".jpeg", ".png", ".bmp", ".tiff"],
        env="ALLOWED_FILE_TYPES"
    )
    
    class Config:
        env_prefix = "API_"


class LoggingSettings(BaseSettings):
    """Logging configuration settings."""
    level: str = Field(default="INFO", env="LOG_LEVEL")
    format: str = Field(default="json", env="LOG_FORMAT")  # json, text
    file_path: Optional[str] = Field(default=None, env="LOG_FILE_PATH")
    max_file_size: str = Field(default="100MB", env="LOG_MAX_FILE_SIZE")
    backup_count: int = Field(default=5, env="LOG_BACKUP_COUNT")
    
    # Structured logging fields
    service_name: str = Field(default="math-llm-ocr", env="SERVICE_NAME")
    service_version: str = Field(default="0.1.0", env="SERVICE_VERSION")
    environment: str = Field(default="development", env="ENVIRONMENT")
    
    class Config:
        env_prefix = "LOG_"


class MonitoringSettings(BaseSettings):
    """Monitoring and observability settings."""
    enable_metrics: bool = Field(default=True, env="ENABLE_METRICS")
    metrics_port: int = Field(default=9090, env="METRICS_PORT")
    
    # Tracing
    enable_tracing: bool = Field(default=False, env="ENABLE_TRACING")
    jaeger_endpoint: Optional[str] = Field(default=None, env="JAEGER_ENDPOINT")
    
    # Health checks
    health_check_interval: int = Field(default=30, env="HEALTH_CHECK_INTERVAL")
    
    class Config:
        env_prefix = "MONITORING_"


class SecuritySettings(BaseSettings):
    """Security configuration settings."""
    secret_key: str = Field(env="SECRET_KEY")
    algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    
    # API Key settings (for external service authentication)
    api_key_header: str = Field(default="X-API-Key", env="API_KEY_HEADER")
    valid_api_keys: List[str] = Field(default=[], env="VALID_API_KEYS")
    
    class Config:
        env_prefix = "SECURITY_"


class ExternalServiceSettings(BaseSettings):
    """External service integration settings."""
    backend_api_url: str = Field(
        default="http://localhost:8001/api", 
        env="BACKEND_API_URL"
    )
    backend_timeout: int = Field(default=30, env="BACKEND_TIMEOUT")
    
    # Hugging Face API (for additional models)
    huggingface_api_token: Optional[str] = Field(default=None, env="HUGGINGFACE_API_TOKEN")
    
    class Config:
        env_prefix = "EXTERNAL_"


class Settings(BaseSettings):
    """Main application settings."""
    
    # Sub-configurations
    database: DatabaseSettings = DatabaseSettings()
    ml: MLModelSettings = MLModelSettings()
    api: APISettings = APISettings()
    logging: LoggingSettings = LoggingSettings()
    monitoring: MonitoringSettings = MonitoringSettings()
    security: SecuritySettings = SecuritySettings()
    external: ExternalServiceSettings = ExternalServiceSettings()
    
    # Global settings
    app_name: str = Field(default="Mathematics LLM OCR Service", env="APP_NAME")
    app_description: str = Field(
        default="AI-powered mathematical OCR and problem solving service",
        env="APP_DESCRIPTION"
    )
    version: str = Field(default="0.1.0", env="APP_VERSION")
    
    # Development settings
    enable_docs: bool = Field(default=True, env="ENABLE_DOCS")
    enable_debug_endpoints: bool = Field(default=False, env="ENABLE_DEBUG_ENDPOINTS")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings instance."""
    return settings


# Configuration validation
def validate_settings() -> None:
    """Validate critical settings on startup."""
    errors = []
    
    # Check required directories exist
    if not os.path.exists(settings.ml.models_path):
        errors.append(f"Models directory does not exist: {settings.ml.models_path}")
    
    # Validate device settings
    if settings.ml.device not in ["cpu", "cuda", "mps"]:
        errors.append(f"Invalid device: {settings.ml.device}")
    
    # Check security settings
    if not settings.security.secret_key:
        errors.append("SECRET_KEY environment variable is required")
    
    if errors:
        raise ValueError("Configuration validation failed:\n" + "\n".join(errors))


# Environment-specific configurations
def get_development_overrides() -> Dict[str, Any]:
    """Get development environment overrides."""
    return {
        "api.debug": True,
        "api.reload": True,
        "logging.level": "DEBUG",
        "enable_debug_endpoints": True,
    }


def get_production_overrides() -> Dict[str, Any]:
    """Get production environment overrides."""
    return {
        "api.debug": False,
        "api.reload": False,
        "logging.level": "INFO",
        "enable_debug_endpoints": False,
        "monitoring.enable_tracing": True,
    }


def apply_environment_overrides(environment: str) -> None:
    """Apply environment-specific overrides."""
    global settings
    
    if environment == "development":
        overrides = get_development_overrides()
    elif environment == "production":
        overrides = get_production_overrides()
    else:
        return
    
    # Apply overrides (this would need custom implementation for nested settings)
    # For now, this is a placeholder for the pattern