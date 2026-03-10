"""
Tests for health check endpoints.
"""
import pytest
from unittest.mock import MagicMock, patch


@pytest.fixture
def health_client(mock_model_registry):
    with patch("src.models.base.get_model_registry", return_value=mock_model_registry):
        from fastapi.testclient import TestClient
        from src.api.main import app
        client = TestClient(app)
        yield client


class TestHealthEndpoint:
    def test_health_returns_200(self, health_client):
        response = health_client.get("/health")
        assert response.status_code == 200

    def test_health_status_is_healthy(self, health_client):
        response = health_client.get("/health")
        data = response.json()
        assert data["status"] == "healthy"

    def test_health_has_timestamp(self, health_client):
        response = health_client.get("/health")
        data = response.json()
        assert "timestamp" in data
        assert data["timestamp"] > 0

    def test_health_has_uptime(self, health_client):
        response = health_client.get("/health")
        data = response.json()
        assert "uptime_seconds" in data
        assert data["uptime_seconds"] >= 0

    def test_health_has_service_info(self, health_client):
        response = health_client.get("/health")
        data = response.json()
        assert "service_info" in data

    def test_health_has_system_info(self, health_client):
        response = health_client.get("/health")
        data = response.json()
        assert "system_info" in data

    def test_health_has_models_info(self, health_client):
        response = health_client.get("/health")
        data = response.json()
        assert "models_info" in data

    def test_health_via_root_path(self, health_client):
        # The router is mounted, so we check the /health path
        response = health_client.get("/health")
        assert response.status_code == 200


class TestLivenessEndpoint:
    def test_liveness_returns_200(self, health_client):
        response = health_client.get("/live")
        assert response.status_code == 200

    def test_liveness_status_is_alive(self, health_client):
        response = health_client.get("/live")
        data = response.json()
        assert data["status"] == "alive"

    def test_liveness_has_timestamp(self, health_client):
        response = health_client.get("/live")
        data = response.json()
        assert "timestamp" in data


class TestReadinessEndpoint:
    def test_readiness_returns_200(self, health_client):
        response = health_client.get("/ready")
        assert response.status_code == 200

    def test_readiness_has_ready_field(self, health_client):
        response = health_client.get("/ready")
        data = response.json()
        assert "ready" in data
        assert isinstance(data["ready"], bool)

    def test_readiness_has_checks(self, health_client):
        response = health_client.get("/ready")
        data = response.json()
        assert "checks" in data
        assert isinstance(data["checks"], dict)

    def test_readiness_ready_when_model_loaded(self, mock_model_registry):
        mock_model_registry.list_models.return_value = ["mathematical_ocr"]
        mock_model = MagicMock()
        mock_model.is_model_loaded.return_value = True
        mock_model.model_name = "mathematical_ocr"
        mock_model_registry.get_model.return_value = mock_model

        with patch("src.models.base.get_model_registry", return_value=mock_model_registry):
            from fastapi.testclient import TestClient
            from src.api.main import app
            client = TestClient(app)
            response = client.get("/ready")
            data = response.json()
            assert data["ready"] is True

    def test_readiness_not_ready_when_model_not_loaded(self, mock_model_registry):
        mock_model_registry.list_models.return_value = ["mathematical_ocr"]
        mock_model = MagicMock()
        mock_model.is_model_loaded.return_value = False
        mock_model.model_name = "mathematical_ocr"
        mock_model_registry.get_model.return_value = mock_model

        with patch("src.models.base.get_model_registry", return_value=mock_model_registry):
            from fastapi.testclient import TestClient
            from src.api.main import app
            client = TestClient(app)
            response = client.get("/ready")
            data = response.json()
            assert data["ready"] is False

    def test_readiness_not_ready_when_no_models(self, mock_model_registry):
        mock_model_registry.list_models.return_value = []

        with patch("src.models.base.get_model_registry", return_value=mock_model_registry):
            from fastapi.testclient import TestClient
            from src.api.main import app
            client = TestClient(app)
            response = client.get("/ready")
            data = response.json()
            assert data["ready"] is False
