"""
Feature Flag Service Configuration
"""
import os
from typing import List, Dict, Any
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Service configuration"""

    # Service
    SERVICE_NAME: str = "feature-flags"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"

    # Server
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8010"))

    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://redis:6379/6")

    # CORS
    CORS_ORIGINS: List[str] = ["*"]

    # Auth (for admin endpoints)
    ADMIN_API_KEY: str = os.getenv("ADMIN_API_KEY", "change-me-in-production")

    class Config:
        env_file = ".env"


settings = Settings()


# Default feature flags configuration
DEFAULT_FLAGS: Dict[str, Dict[str, Any]] = {
    # Service-level flags
    "auth_microservice": {
        "enabled": True,
        "percentage": 0,  # Start at 0%
        "description": "Route auth traffic to microservice",
        "service": "auth-service",
        "django_path": "/api/v1/auth",
        "microservice_path": "/api/v2/auth",
    },
    "stock_data_microservice": {
        "enabled": True,
        "percentage": 0,
        "description": "Route stock data traffic to microservice",
        "service": "stock-data-service",
        "django_path": "/api/v1/stocks",
        "microservice_path": "/api/v2/stocks",
    },
    "portfolio_microservice": {
        "enabled": True,
        "percentage": 0,
        "description": "Route portfolio traffic to microservice",
        "service": "portfolio-service",
        "django_path": "/api/v1/portfolio",
        "microservice_path": "/api/v2/portfolio",
    },
    "prediction_microservice": {
        "enabled": True,
        "percentage": 0,
        "description": "Route prediction traffic to microservice",
        "service": "prediction-service",
        "django_path": "/api/v1/models",
        "microservice_path": "/api/v2/models",
    },
    "analysis_microservice": {
        "enabled": True,
        "percentage": 0,
        "description": "Route analysis traffic to microservice",
        "service": "analysis-service",
        "django_path": "/api/v1/analysis",
        "microservice_path": "/api/v2/analysis",
    },
    "ai_insights_microservice": {
        "enabled": True,
        "percentage": 0,
        "description": "Route AI insights traffic to microservice",
        "service": "ai-insights-service",
        "django_path": "/api/v1/ai",
        "microservice_path": "/api/v2/ai",
    },
    "chatbot_microservice": {
        "enabled": True,
        "percentage": 0,
        "description": "Route chatbot traffic to microservice",
        "service": "chatbot-service",
        "django_path": "/api/v1/chat",
        "microservice_path": "/api/v2/chat",
    },
}


# Cutover phases configuration
CUTOVER_PHASES = {
    "shadow": {
        "name": "Shadow Mode",
        "description": "100% Django, microservices receive mirrored traffic",
        "week": 1,
        "percentages": {
            "auth_microservice": 0,
            "stock_data_microservice": 0,
            "portfolio_microservice": 0,
            "prediction_microservice": 0,
            "analysis_microservice": 0,
            "ai_insights_microservice": 0,
            "chatbot_microservice": 0,
        }
    },
    "canary": {
        "name": "Canary Release",
        "description": "10% to microservices, 90% to Django",
        "week": 2,
        "percentages": {
            "auth_microservice": 10,
            "stock_data_microservice": 10,
            "portfolio_microservice": 10,
            "prediction_microservice": 5,
            "analysis_microservice": 5,
            "ai_insights_microservice": 5,
            "chatbot_microservice": 5,
        }
    },
    "early_adopter": {
        "name": "Early Adopter",
        "description": "30% to microservices",
        "week": 3,
        "percentages": {
            "auth_microservice": 30,
            "stock_data_microservice": 30,
            "portfolio_microservice": 30,
            "prediction_microservice": 20,
            "analysis_microservice": 20,
            "ai_insights_microservice": 20,
            "chatbot_microservice": 20,
        }
    },
    "half": {
        "name": "50/50 Split",
        "description": "50% to microservices",
        "week": 4,
        "percentages": {
            "auth_microservice": 50,
            "stock_data_microservice": 50,
            "portfolio_microservice": 50,
            "prediction_microservice": 30,
            "analysis_microservice": 30,
            "ai_insights_microservice": 30,
            "chatbot_microservice": 30,
        }
    },
    "majority": {
        "name": "Majority Migrated",
        "description": "80% to microservices",
        "week": 5,
        "percentages": {
            "auth_microservice": 80,
            "stock_data_microservice": 80,
            "portfolio_microservice": 80,
            "prediction_microservice": 50,
            "analysis_microservice": 50,
            "ai_insights_microservice": 50,
            "chatbot_microservice": 50,
        }
    },
    "final_validation": {
        "name": "Final Validation",
        "description": "95% to microservices",
        "week": 6,
        "percentages": {
            "auth_microservice": 95,
            "stock_data_microservice": 95,
            "portfolio_microservice": 95,
            "prediction_microservice": 80,
            "analysis_microservice": 80,
            "ai_insights_microservice": 80,
            "chatbot_microservice": 80,
        }
    },
    "complete": {
        "name": "Complete Cutover",
        "description": "100% to microservices",
        "week": 7,
        "percentages": {
            "auth_microservice": 100,
            "stock_data_microservice": 100,
            "portfolio_microservice": 100,
            "prediction_microservice": 100,
            "analysis_microservice": 100,
            "ai_insights_microservice": 100,
            "chatbot_microservice": 100,
        }
    },
    "rollback": {
        "name": "Emergency Rollback",
        "description": "100% to Django (emergency)",
        "week": 0,
        "percentages": {
            "auth_microservice": 0,
            "stock_data_microservice": 0,
            "portfolio_microservice": 0,
            "prediction_microservice": 0,
            "analysis_microservice": 0,
            "ai_insights_microservice": 0,
            "chatbot_microservice": 0,
        }
    },
}


# Alert thresholds for cutover monitoring
ALERT_THRESHOLDS = {
    "error_rate": {
        "warning": 1.0,   # 1% error rate
        "critical": 5.0,  # 5% error rate
    },
    "latency_p99": {
        "warning": 300,   # 300ms
        "critical": 500,  # 500ms
    },
    "success_rate": {
        "warning": 99.0,  # Below 99%
        "critical": 95.0, # Below 95%
    },
    "mismatch_rate": {
        "warning": 5.0,   # 5% mismatch
        "critical": 10.0, # 10% mismatch
    },
}
