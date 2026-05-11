"""
Prediction Service Tests
"""
import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    """Test health endpoint"""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "prediction-service"


@pytest.mark.asyncio
async def test_liveness(client: AsyncClient):
    """Test liveness probe"""
    response = await client.get("/health/live")
    assert response.status_code == 200
    assert response.json()["status"] == "alive"


@pytest.mark.asyncio
async def test_service_info(client: AsyncClient):
    """Test service info endpoint"""
    response = await client.get("/stock_helper/api/v2/predict/info")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "prediction-service"
    assert "version" in data
    assert "ml_config" in data
    assert "endpoints" in data


@pytest.mark.asyncio
async def test_get_supported_models(client: AsyncClient):
    """Test supported models endpoint"""
    response = await client.get("/stock_helper/api/v2/predict/supported-models")
    assert response.status_code == 200
    data = response.json()
    assert "models" in data
    assert len(data["models"]) > 0
    model_types = [m["type"] for m in data["models"]]
    assert "xgboost" in model_types


# Prediction Tests
@pytest.mark.asyncio
async def test_predict_price(client: AsyncClient, prediction_request_data, mock_prediction):
    """Test price prediction"""
    with patch("app.api.routes.PredictionService") as MockService:
        mock_service = MagicMock()
        mock_service.repo = MagicMock()
        mock_service.repo.log_prediction_request = AsyncMock()
        mock_service.predict = AsyncMock(return_value=mock_prediction)
        MockService.return_value = mock_service

        response = await client.post(
            "/stock_helper/api/v2/predict/predict",
            json=prediction_request_data
        )
        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "VNM"
        assert "predictions" in data
        assert len(data["predictions"]) > 0


@pytest.mark.asyncio
async def test_predict_price_get(client: AsyncClient, mock_prediction):
    """Test price prediction via GET endpoint"""
    with patch("app.api.routes.PredictionService") as MockService:
        mock_service = MagicMock()
        mock_service.predict = AsyncMock(return_value=mock_prediction)
        MockService.return_value = mock_service

        response = await client.get(
            "/stock_helper/api/v2/predict/predict/VNM?days=5"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "VNM"


@pytest.mark.asyncio
async def test_predict_price_not_found(client: AsyncClient, prediction_request_data):
    """Test prediction for unknown symbol"""
    with patch("app.api.routes.PredictionService") as MockService:
        mock_service = MagicMock()
        mock_service.repo = MagicMock()
        mock_service.repo.log_prediction_request = AsyncMock()
        mock_service.predict = AsyncMock(return_value=None)
        MockService.return_value = mock_service

        prediction_request_data["symbol"] = "UNKNOWN"
        response = await client.post(
            "/stock_helper/api/v2/predict/predict",
            json=prediction_request_data
        )
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_predict_bulk(client: AsyncClient, mock_prediction):
    """Test bulk predictions"""
    with patch("app.api.routes.PredictionService") as MockService:
        mock_service = MagicMock()
        mock_service.predict = AsyncMock(return_value=mock_prediction)
        MockService.return_value = mock_service

        response = await client.post(
            "/stock_helper/api/v2/predict/predict/bulk",
            json={
                "symbols": ["VNM", "FPT"],
                "days": 5,
                "model_type": "xgboost"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "predictions" in data
        assert "failed" in data


# Model Management Tests
@pytest.mark.asyncio
async def test_list_models(client: AsyncClient, mock_model):
    """Test listing models"""
    with patch("app.api.routes.PredictionService") as MockService:
        mock_service = MagicMock()
        mock_service.get_models = AsyncMock(return_value=[mock_model])
        MockService.return_value = mock_service

        response = await client.get("/stock_helper/api/v2/predict/models")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["model_type"] == "xgboost"


@pytest.mark.asyncio
async def test_get_model_by_id(client: AsyncClient, mock_model):
    """Test getting model by ID"""
    with patch("app.api.routes.PredictionService") as MockService:
        mock_service = MagicMock()
        mock_service.get_model = AsyncMock(return_value=mock_model)
        MockService.return_value = mock_service

        response = await client.get("/stock_helper/api/v2/predict/models/1")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 1


@pytest.mark.asyncio
async def test_get_model_not_found(client: AsyncClient):
    """Test getting non-existent model"""
    with patch("app.api.routes.PredictionService") as MockService:
        mock_service = MagicMock()
        mock_service.get_model = AsyncMock(return_value=None)
        MockService.return_value = mock_service

        response = await client.get("/stock_helper/api/v2/predict/models/999")
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_train_model(client: AsyncClient, train_request_data, mock_train_response):
    """Test model training"""
    with patch("app.api.routes.PredictionService") as MockService:
        mock_service = MagicMock()
        mock_service.train_model = AsyncMock(return_value=mock_train_response)
        MockService.return_value = mock_service

        response = await client.post(
            "/stock_helper/api/v2/predict/models/train",
            json=train_request_data
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "training"


@pytest.mark.asyncio
async def test_get_feature_importance(client: AsyncClient, mock_feature_importance):
    """Test feature importance endpoint"""
    with patch("app.api.routes.PredictionService") as MockService:
        mock_service = MagicMock()
        mock_service.get_feature_importance = AsyncMock(return_value=mock_feature_importance)
        MockService.return_value = mock_service

        response = await client.get("/stock_helper/api/v2/predict/models/1/features")
        assert response.status_code == 200
        data = response.json()
        assert "features" in data
        assert len(data["features"]) > 0


# Backtest Tests
@pytest.mark.asyncio
async def test_run_backtest(client: AsyncClient, backtest_request_data, mock_backtest_result):
    """Test backtesting"""
    with patch("app.api.routes.PredictionService") as MockService:
        mock_service = MagicMock()
        mock_service.backtest = AsyncMock(return_value=mock_backtest_result)
        MockService.return_value = mock_service

        response = await client.post(
            "/stock_helper/api/v2/predict/backtest",
            json=backtest_request_data
        )
        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "VNM"
        assert "direction_accuracy" in data


@pytest.mark.asyncio
async def test_backtest_no_data(client: AsyncClient, backtest_request_data):
    """Test backtest with no historical data"""
    with patch("app.api.routes.PredictionService") as MockService:
        mock_service = MagicMock()
        mock_service.backtest = AsyncMock(return_value=None)
        MockService.return_value = mock_service

        response = await client.post(
            "/stock_helper/api/v2/predict/backtest",
            json=backtest_request_data
        )
        assert response.status_code == 404


# Comparison Tests
@pytest.mark.asyncio
async def test_compare_models(client: AsyncClient, comparison_request_data, mock_comparison_result):
    """Test model comparison"""
    with patch("app.api.routes.PredictionService") as MockService:
        mock_service = MagicMock()
        mock_repo = MagicMock()

        # Mock active model
        mock_model = MagicMock()
        mock_model.id = 1
        mock_model.accuracy = 85.5
        mock_repo.get_active_model = AsyncMock(return_value=mock_model)
        mock_repo.get_model_accuracy_stats = AsyncMock(return_value={
            "direction_accuracy": 75.0,
            "average_error": 1.5,
            "total_predictions": 100
        })

        mock_service.repo = mock_repo
        MockService.return_value = mock_service

        response = await client.post(
            "/stock_helper/api/v2/predict/compare",
            json=comparison_request_data
        )
        assert response.status_code == 200
        data = response.json()
        assert "comparisons" in data
        assert "recommended_model" in data


# Health & Status Tests
@pytest.mark.asyncio
async def test_models_health(client: AsyncClient, mock_model):
    """Test models health endpoint"""
    with patch("app.api.routes.PredictionService") as MockService:
        mock_service = MagicMock()
        mock_repo = MagicMock()

        # Create mock model with all required attributes
        mock_model_obj = MagicMock()
        mock_model_obj.id = 1
        mock_model_obj.name = "XGBoost VNM"
        mock_model_obj.status = MagicMock()
        mock_model_obj.status.value = "ready"
        mock_model_obj.trained_at = datetime.utcnow()

        mock_repo.get_all_models = AsyncMock(return_value=[mock_model_obj])
        mock_repo.get_prediction_count_last_24h = AsyncMock(return_value=150)
        mock_repo.get_model_accuracy_stats = AsyncMock(return_value={
            "direction_accuracy": 85.5,
            "total_predictions": 100
        })

        mock_service.repo = mock_repo
        MockService.return_value = mock_service

        response = await client.get("/stock_helper/api/v2/predict/health/models")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


# Unauthenticated Tests
@pytest.mark.asyncio
async def test_predict_unauthenticated(unauthenticated_client: AsyncClient, mock_prediction):
    """Test that prediction works without authentication"""
    with patch("app.api.routes.PredictionService") as MockService:
        mock_service = MagicMock()
        mock_service.repo = MagicMock()
        mock_service.repo.log_prediction_request = AsyncMock()
        mock_service.predict = AsyncMock(return_value=mock_prediction)
        MockService.return_value = mock_service

        response = await unauthenticated_client.post(
            "/stock_helper/api/v2/predict/predict",
            json={"symbol": "VNM", "days": 5}
        )
        # Prediction should work without auth (optional auth)
        assert response.status_code == 200


# Validation Tests
@pytest.mark.asyncio
async def test_predict_invalid_days(client: AsyncClient):
    """Test prediction with invalid days parameter"""
    response = await client.post(
        "/stock_helper/api/v2/predict/predict",
        json={"symbol": "VNM", "days": 100}  # Max is 30
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_bulk_predict_too_many_symbols(client: AsyncClient):
    """Test bulk prediction with too many symbols"""
    response = await client.post(
        "/stock_helper/api/v2/predict/predict/bulk",
        json={
            "symbols": [f"SYM{i}" for i in range(25)],  # Max is 20
            "days": 5
        }
    )
    assert response.status_code == 422
