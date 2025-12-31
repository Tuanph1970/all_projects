"""
Integration tests for prediction-service.

Tests cover:
- Model management (list, create, delete)
- Training workflows
- Price predictions
- Backtesting
- Model comparison

NOTE: prediction-service uses 'expose' instead of 'ports' in docker-compose,
making it accessible only to other services within the Docker network.
Tests running from host will receive 404 errors.
"""

import pytest
import httpx
from datetime import datetime, timedelta

from tests.conftest import get_api_path


# Skip all tests in this module - prediction-service is internal only
pytestmark = [
    pytest.mark.integration,
    pytest.mark.auth,
    pytest.mark.skip(reason="prediction-service is internal only (uses expose, not ports)")
]


class TestHealthEndpoints:
    """Test prediction-service health endpoints."""

    async def test_health_live(self, prediction_client: httpx.AsyncClient):
        """Test liveness probe endpoint."""
        response = await prediction_client.get("/health/live")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    async def test_health_ready(self, prediction_client: httpx.AsyncClient):
        """Test readiness probe endpoint."""
        response = await prediction_client.get("/health/ready")
        assert response.status_code == 200

    async def test_models_health(self, prediction_client: httpx.AsyncClient):
        """Test model health status."""
        response = await prediction_client.get("/health/models")
        assert response.status_code in [200, 404]


class TestSupportedModels:
    """Test supported model types."""

    async def test_list_supported_models(self, prediction_client: httpx.AsyncClient):
        """Test listing supported model types."""
        response = await prediction_client.get(get_api_path("supported-models"))
        assert response.status_code == 200
        data = response.json()

        # Should list available model types
        items = data if isinstance(data, list) else data.get("models", data.get("items", []))
        assert len(items) > 0

        # Check for expected model types
        model_names = [m.get("name", m.get("type", m)) for m in items] if isinstance(items[0], dict) else items
        expected_models = ["xgboost", "lightgbm", "random_forest", "linear", "arima"]
        assert any(model.lower() in str(model_names).lower() for model in expected_models)


class TestModelManagement:
    """Test model CRUD operations."""

    async def test_list_models(
        self,
        authenticated_prediction_client: httpx.AsyncClient
    ):
        """Test listing trained models."""
        response = await authenticated_prediction_client.get(get_api_path("models"))
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, (list, dict))

    async def test_get_model_by_id(
        self,
        authenticated_prediction_client: httpx.AsyncClient
    ):
        """Test getting model details by ID."""
        # First list models
        list_response = await authenticated_prediction_client.get(get_api_path("models"))
        if list_response.status_code == 200:
            models = list_response.json()
            items = models if isinstance(models, list) else models.get("items", [])

            if items:
                model_id = items[0].get("id")
                if model_id:
                    response = await authenticated_prediction_client.get(
                        get_api_path(f"models/{model_id}")
                    )
                    assert response.status_code in [200, 404]

    async def test_get_nonexistent_model(
        self,
        authenticated_prediction_client: httpx.AsyncClient
    ):
        """Test getting non-existent model returns 404."""
        response = await authenticated_prediction_client.get(get_api_path("models/99999"))
        assert response.status_code == 404


class TestModelTraining:
    """Test model training workflows."""

    @pytest.mark.slow
    async def test_train_xgboost_model(
        self,
        authenticated_prediction_client: httpx.AsyncClient
    ):
        """Test training an XGBoost model."""
        response = await authenticated_prediction_client.post(
            get_api_path("models/train"),
            json={
                "symbol": "VNM",
                "model_type": "xgboost",
                "lookback_days": 30,
                "prediction_horizon": 5
            }
        )
        # Training may be async (202) or sync (200)
        assert response.status_code in [200, 202, 400, 404]

        if response.status_code in [200, 202]:
            data = response.json()
            assert "model_id" in data or "id" in data or "task_id" in data

    @pytest.mark.slow
    async def test_train_lightgbm_model(
        self,
        authenticated_prediction_client: httpx.AsyncClient
    ):
        """Test training a LightGBM model."""
        response = await authenticated_prediction_client.post(
            get_api_path("models/train"),
            json={
                "symbol": "FPT",
                "model_type": "lightgbm",
                "lookback_days": 60
            }
        )
        assert response.status_code in [200, 202, 400, 404]

    @pytest.mark.slow
    async def test_train_random_forest_model(
        self,
        authenticated_prediction_client: httpx.AsyncClient
    ):
        """Test training a Random Forest model."""
        response = await authenticated_prediction_client.post(
            get_api_path("models/train"),
            json={
                "symbol": "VIC",
                "model_type": "random_forest",
                "lookback_days": 30
            }
        )
        assert response.status_code in [200, 202, 400, 404]

    async def test_train_with_invalid_symbol(
        self,
        authenticated_prediction_client: httpx.AsyncClient
    ):
        """Test training with invalid stock symbol."""
        response = await authenticated_prediction_client.post(
            get_api_path("models/train"),
            json={
                "symbol": "INVALID999",
                "model_type": "xgboost",
                "lookback_days": 30
            }
        )
        assert response.status_code in [400, 404, 422]

    async def test_train_with_invalid_model_type(
        self,
        authenticated_prediction_client: httpx.AsyncClient
    ):
        """Test training with invalid model type."""
        response = await authenticated_prediction_client.post(
            get_api_path("models/train"),
            json={
                "symbol": "VNM",
                "model_type": "invalid_model",
                "lookback_days": 30
            }
        )
        assert response.status_code in [400, 422]


class TestPredictions:
    """Test prediction generation."""

    async def test_predict_stock_price(
        self,
        authenticated_prediction_client: httpx.AsyncClient
    ):
        """Test generating stock price prediction."""
        response = await authenticated_prediction_client.post(
            get_api_path("predict"),
            json={
                "symbol": "VNM",
                "days": 5
            }
        )
        # May need trained model first
        assert response.status_code in [200, 400, 404]

        if response.status_code == 200:
            data = response.json()
            assert "predictions" in data or "forecast" in data or "prices" in data

    async def test_predict_get_endpoint(
        self,
        authenticated_prediction_client: httpx.AsyncClient
    ):
        """Test GET endpoint for prediction."""
        response = await authenticated_prediction_client.get(
            get_api_path("predict/VNM"),
            params={"days": 7}
        )
        assert response.status_code in [200, 400, 404]

    async def test_bulk_predictions(
        self,
        authenticated_prediction_client: httpx.AsyncClient
    ):
        """Test bulk prediction for multiple stocks."""
        response = await authenticated_prediction_client.post(
            get_api_path("predict/bulk"),
            json={
                "symbols": ["VNM", "FPT", "VIC"],
                "days": 5
            }
        )
        assert response.status_code in [200, 400, 404]

        if response.status_code == 200:
            data = response.json()
            # Should have predictions for each symbol
            assert isinstance(data, (list, dict))

    async def test_predict_with_specific_model(
        self,
        authenticated_prediction_client: httpx.AsyncClient
    ):
        """Test prediction using specific model."""
        # First get available models
        models_response = await authenticated_prediction_client.get(get_api_path("models"))
        if models_response.status_code == 200:
            models = models_response.json()
            items = models if isinstance(models, list) else models.get("items", [])

            if items:
                model_id = items[0].get("id")
                if model_id:
                    response = await authenticated_prediction_client.post(
                        get_api_path("predict"),
                        json={
                            "symbol": "VNM",
                            "days": 5,
                            "model_id": model_id
                        }
                    )
                    assert response.status_code in [200, 400, 404]


class TestBacktesting:
    """Test backtesting functionality."""

    @pytest.mark.slow
    async def test_backtest_model(
        self,
        authenticated_prediction_client: httpx.AsyncClient
    ):
        """Test backtesting a prediction model."""
        end_date = datetime.now() - timedelta(days=30)
        start_date = end_date - timedelta(days=90)

        response = await authenticated_prediction_client.post(
            get_api_path("backtest"),
            json={
                "symbol": "VNM",
                "model_type": "xgboost",
                "start_date": start_date.strftime("%Y-%m-%d"), "end_date": end_date.strftime("%Y-%m-%d"), "prediction_horizon": 5
            }
        )
        assert response.status_code in [200, 202, 400, 404]

        if response.status_code == 200:
            data = response.json()
            # Should contain accuracy metrics
            assert any(key in data for key in [
                "accuracy", "mae", "mse", "rmse", "mape", "metrics", "results"
            ])

    async def test_backtest_with_invalid_dates(
        self,
        authenticated_prediction_client: httpx.AsyncClient
    ):
        """Test backtest with future dates."""
        future_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")

        response = await authenticated_prediction_client.post(
            get_api_path("backtest"),
            json={
                "symbol": "VNM",
                "model_type": "xgboost",
                "start_date": future_date,
                "end_date": future_date
            }
        )
        assert response.status_code in [400, 422]


class TestModelComparison:
    """Test model comparison functionality."""

    @pytest.mark.slow
    async def test_compare_models(
        self,
        authenticated_prediction_client: httpx.AsyncClient
    ):
        """Test comparing different model types."""
        response = await authenticated_prediction_client.post(
            get_api_path("compare"),
            json={
                "symbol": "VNM",
                "model_types": ["xgboost", "lightgbm", "random_forest"],
                "lookback_days": 30
            }
        )
        assert response.status_code in [200, 202, 400, 404]

        if response.status_code == 200:
            data = response.json()
            # Should contain comparison results
            assert isinstance(data, (list, dict))


class TestFeatureImportance:
    """Test feature importance retrieval."""

    async def test_get_feature_importance(
        self,
        authenticated_prediction_client: httpx.AsyncClient
    ):
        """Test getting feature importance for a model."""
        # First get a model
        models_response = await authenticated_prediction_client.get(get_api_path("models"))
        if models_response.status_code == 200:
            models = models_response.json()
            items = models if isinstance(models, list) else models.get("items", [])

            if items:
                model_id = items[0].get("id")
                if model_id:
                    response = await authenticated_prediction_client.get(
                        get_api_path(f"models/{model_id}/features")
                    )
                    assert response.status_code in [200, 404]

                    if response.status_code == 200:
                        data = response.json()
                        # Should list feature importances
                        assert isinstance(data, (list, dict))


class TestTrainingLogs:
    """Test training log retrieval."""

    async def test_get_training_logs(
        self,
        authenticated_prediction_client: httpx.AsyncClient
    ):
        """Test getting training history for a model."""
        # First get a model
        models_response = await authenticated_prediction_client.get(get_api_path("models"))
        if models_response.status_code == 200:
            models = models_response.json()
            items = models if isinstance(models, list) else models.get("items", [])

            if items:
                model_id = items[0].get("id")
                if model_id:
                    response = await authenticated_prediction_client.get(
                        get_api_path(f"models/{model_id}/training-logs")
                    )
                    assert response.status_code in [200, 404]


class TestModelDeletion:
    """Test model deletion."""

    async def test_delete_model(
        self,
        authenticated_prediction_client: httpx.AsyncClient
    ):
        """Test deleting/deactivating a model."""
        # First train a model to delete
        train_response = await authenticated_prediction_client.post(
            get_api_path("models/train"),
            json={
                "symbol": "HPG",
                "model_type": "linear",
                "lookback_days": 14
            }
        )

        if train_response.status_code in [200, 202]:
            data = train_response.json()
            model_id = data.get("model_id", data.get("id"))

            if model_id:
                response = await authenticated_prediction_client.delete(
                    get_api_path(f"models/{model_id}")
                )
                assert response.status_code in [200, 204, 404]


class TestInputValidation:
    """Test input validation for prediction endpoints."""

    async def test_predict_negative_days(
        self,
        authenticated_prediction_client: httpx.AsyncClient
    ):
        """Test prediction with negative days."""
        response = await authenticated_prediction_client.post(
            get_api_path("predict"),
            json={
                "symbol": "VNM",
                "days": -5
            }
        )
        assert response.status_code == 422

    async def test_predict_too_many_days(
        self,
        authenticated_prediction_client: httpx.AsyncClient
    ):
        """Test prediction with too many days."""
        response = await authenticated_prediction_client.post(
            get_api_path("predict"),
            json={
                "symbol": "VNM",
                "days": 365  # Likely too far
            }
        )
        # May succeed or fail depending on limits
        assert response.status_code in [200, 400, 422]

    async def test_train_insufficient_lookback(
        self,
        authenticated_prediction_client: httpx.AsyncClient
    ):
        """Test training with insufficient lookback period."""
        response = await authenticated_prediction_client.post(
            get_api_path("models/train"),
            json={
                "symbol": "VNM",
                "model_type": "xgboost",
                "lookback_days": 1  # Too short
            }
        )
        assert response.status_code in [400, 422]
