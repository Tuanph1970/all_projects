"""
Test Configuration and Fixtures for Prediction Service
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, date, timedelta

from app.main import app
from app.api.dependencies import get_db, get_current_user, get_current_user_optional
from app.models.schemas import (
    ModelType, ModelStatus,
    PredictionResponse, DailyPrediction,
    ModelResponse, ModelTrainResponse,
    BacktestResult, ModelComparisonResult,
    FeatureImportanceResponse, FeatureImportance,
    ModelHealthStatus
)


@pytest_asyncio.fixture
async def mock_db():
    """Mock database session"""
    mock_session = AsyncMock()
    yield mock_session


@pytest_asyncio.fixture
async def client(mock_db):
    """Create test client with mocked dependencies"""

    async def override_get_db():
        yield mock_db

    def override_get_current_user():
        return {"user_id": 1, "email": "test@example.com", "role": "user"}

    def override_get_current_user_optional():
        return {"user_id": 1, "email": "test@example.com", "role": "user"}

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_current_user_optional] = override_get_current_user_optional

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def unauthenticated_client(mock_db):
    """Create test client without authentication"""

    async def override_get_db():
        yield mock_db

    def override_get_current_user_optional():
        return None

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user_optional] = override_get_current_user_optional

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture
def mock_prediction():
    """Mock prediction response"""
    today = date.today()
    return PredictionResponse(
        symbol="VNM",
        current_price=75000.0,
        predictions=[
            DailyPrediction(
                date=today + timedelta(days=i),
                predicted_price=75000.0 + (i * 500),
                predicted_change=(i * 500) / 75000 * 100,
                direction="up",
                confidence=0.75 - (i * 0.05),
                price_low=74500.0 + (i * 400),
                price_high=75500.0 + (i * 600)
            )
            for i in range(1, 6)
        ],
        model_type="xgboost",
        model_accuracy=85.5,
        generated_at=datetime.utcnow()
    )


@pytest.fixture
def mock_model():
    """Mock model response"""
    return ModelResponse(
        id=1,
        name="XGBoost VNM",
        model_type=ModelType.XGBOOST,
        symbol="VNM",
        version="1.0.0",
        status=ModelStatus.READY,
        accuracy=85.5,
        mse=0.025,
        mae=0.012,
        rmse=0.158,
        r2_score=0.92,
        is_active=True,
        created_at=datetime.utcnow(),
        trained_at=datetime.utcnow()
    )


@pytest.fixture
def mock_train_response():
    """Mock model training response"""
    return ModelTrainResponse(
        model_id=1,
        status="training",
        message="Model training started",
        estimated_time_seconds=120
    )


@pytest.fixture
def mock_backtest_result():
    """Mock backtest result"""
    return BacktestResult(
        symbol="VNM",
        model_type="xgboost",
        period="2024-01-01 to 2024-06-30",
        total_predictions=100,
        correct_direction=75,
        direction_accuracy=75.0,
        mean_absolute_error=1.5,
        root_mean_squared_error=2.3,
        average_confidence=0.72
    )


@pytest.fixture
def mock_comparison_result():
    """Mock model comparison result"""
    return ModelComparisonResult(
        symbol="VNM",
        comparisons=[
            {
                "model_type": "xgboost",
                "model_id": 1,
                "accuracy": 85.5,
                "direction_accuracy": 75.0,
                "average_error": 1.5,
                "predictions_count": 100
            },
            {
                "model_type": "lightgbm",
                "model_id": 2,
                "accuracy": 82.0,
                "direction_accuracy": 72.0,
                "average_error": 1.8,
                "predictions_count": 100
            }
        ],
        recommended_model="xgboost",
        recommendation_reason="Highest accuracy at 85.50%"
    )


@pytest.fixture
def mock_feature_importance():
    """Mock feature importance response"""
    return FeatureImportanceResponse(
        model_id=1,
        model_type="xgboost",
        features=[
            FeatureImportance(feature="close_lag_1", importance=0.25, description="Previous day closing price"),
            FeatureImportance(feature="volume", importance=0.15, description="Trading volume"),
            FeatureImportance(feature="rsi_14", importance=0.12, description="14-day RSI"),
            FeatureImportance(feature="macd", importance=0.10, description="MACD indicator"),
        ]
    )


@pytest.fixture
def mock_model_health():
    """Mock model health status"""
    return ModelHealthStatus(
        model_id=1,
        name="XGBoost VNM",
        status="ready",
        last_trained=datetime.utcnow() - timedelta(days=2),
        predictions_last_24h=150,
        accuracy_last_30_days=85.5,
        needs_retraining=False
    )


@pytest.fixture
def prediction_request_data():
    """Test data for prediction request"""
    return {
        "symbol": "VNM",
        "days": 5,
        "model_type": "xgboost"
    }


@pytest.fixture
def train_request_data():
    """Test data for training request"""
    return {
        "symbol": "VNM",
        "model_type": "xgboost",
        "lookback_days": 365,
        "hyperparameters": {
            "n_estimators": 100,
            "max_depth": 6
        }
    }


@pytest.fixture
def backtest_request_data():
    """Test data for backtest request"""
    return {
        "symbol": "VNM",
        "model_type": "xgboost",
        "start_date": "2024-01-01",
        "end_date": "2024-06-30",
        "prediction_horizon": 5
    }


@pytest.fixture
def comparison_request_data():
    """Test data for model comparison"""
    return {
        "symbol": "VNM",
        "model_types": ["xgboost", "lightgbm"]
    }
