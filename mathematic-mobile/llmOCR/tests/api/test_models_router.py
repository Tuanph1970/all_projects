"""
Tests for models management router endpoints.
Uses mocked model registry — no real ML models are loaded.
"""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi.testclient import TestClient


# ──────────────────────────────────────────────────────────────
# Shared fixtures
# ──────────────────────────────────────────────────────────────

def _make_mock_model(name: str, loaded: bool = True, model_type: str = "ocr") -> MagicMock:
    m = MagicMock()
    m.is_model_loaded.return_value = loaded
    m.get_model_info.return_value = {
        "model_name": name,
        "model_type": model_type,
        "is_loaded": loaded,
        "device": "cpu",
        "load_time_seconds": 1.2 if loaded else None,
    }
    return m


@pytest.fixture
def models_client():
    """TestClient with mocked model registry for models router tests."""
    from src.api.main import app

    ocr_model = _make_mock_model("mathematical_ocr", loaded=True, model_type="ocr")
    sol_model = _make_mock_model("default_solution", loaded=False, model_type="solution")

    mock_registry = MagicMock()
    mock_registry.list_models.return_value = ["mathematical_ocr", "default_solution"]
    mock_registry.get_model.side_effect = lambda name: {
        "mathematical_ocr": ocr_model,
        "default_solution": sol_model,
    }.get(name)
    mock_registry.get_registry_status.return_value = "healthy"

    mock_manager = MagicMock()
    mock_manager.get_registry.return_value = mock_registry
    mock_manager.initialize_default_models = AsyncMock(return_value=None)

    with patch("src.api.main.ModelManager", return_value=mock_manager):
        with TestClient(app) as client:
            yield client


# ──────────────────────────────────────────────────────────────
# GET /models/
# ──────────────────────────────────────────────────────────────

class TestListModelsEndpoint:
    def test_list_models_returns_200(self, models_client):
        response = models_client.get("/models/")
        assert response.status_code == 200

    def test_list_models_response_has_models_key(self, models_client):
        response = models_client.get("/models/")
        assert "models" in response.json()

    def test_list_models_response_has_total_count(self, models_client):
        response = models_client.get("/models/")
        assert "total_count" in response.json()

    def test_list_models_response_has_loaded_count(self, models_client):
        response = models_client.get("/models/")
        assert "loaded_count" in response.json()

    def test_list_models_total_count_matches_registry(self, models_client):
        response = models_client.get("/models/")
        data = response.json()
        assert data["total_count"] == 2

    def test_list_models_loaded_count_reflects_state(self, models_client):
        # mathematical_ocr is loaded, default_solution is not
        response = models_client.get("/models/")
        assert response.json()["loaded_count"] == 1

    def test_list_models_each_item_has_name_field(self, models_client):
        response = models_client.get("/models/")
        for model in response.json()["models"]:
            assert "name" in model

    def test_list_models_each_item_has_is_loaded_field(self, models_client):
        response = models_client.get("/models/")
        for model in response.json()["models"]:
            assert "is_loaded" in model

    def test_list_models_degraded_model_included_with_error(self, models_client):
        """A model that raises during get_model_info should still appear in the list."""
        from src.api.main import app

        bad_model = MagicMock()
        bad_model.get_model_info.side_effect = RuntimeError("model corrupted")

        registry = app.state.model_manager.get_registry()
        original_list = registry.list_models.return_value
        registry.list_models.return_value = ["mathematical_ocr", "bad_model"]
        original_get = registry.get_model.side_effect

        good_model = _make_mock_model("mathematical_ocr", loaded=True)
        registry.get_model.side_effect = lambda name: (
            good_model if name == "mathematical_ocr" else bad_model
        )
        try:
            response = models_client.get("/models/")
            assert response.status_code == 200
            names = [m["name"] for m in response.json()["models"]]
            assert "bad_model" in names
        finally:
            registry.list_models.return_value = original_list
            registry.get_model.side_effect = original_get


# ──────────────────────────────────────────────────────────────
# GET /models/{model_name}
# ──────────────────────────────────────────────────────────────

class TestGetModelInfoEndpoint:
    def test_get_existing_model_returns_200(self, models_client):
        response = models_client.get("/models/mathematical_ocr")
        assert response.status_code == 200

    def test_get_model_response_has_name(self, models_client):
        response = models_client.get("/models/mathematical_ocr")
        assert "name" in response.json()

    def test_get_model_response_has_model_type(self, models_client):
        response = models_client.get("/models/mathematical_ocr")
        assert "model_type" in response.json()

    def test_get_model_response_has_is_loaded(self, models_client):
        response = models_client.get("/models/mathematical_ocr")
        assert "is_loaded" in response.json()

    def test_get_model_response_has_device(self, models_client):
        response = models_client.get("/models/mathematical_ocr")
        assert "device" in response.json()

    def test_get_loaded_model_is_loaded_true(self, models_client):
        response = models_client.get("/models/mathematical_ocr")
        assert response.json()["is_loaded"] is True

    def test_get_unloaded_model_is_loaded_false(self, models_client):
        response = models_client.get("/models/default_solution")
        assert response.json()["is_loaded"] is False

    def test_get_unknown_model_returns_404(self, models_client):
        response = models_client.get("/models/nonexistent_model")
        assert response.status_code == 404


# ──────────────────────────────────────────────────────────────
# POST /models/{model_name}/load
# ──────────────────────────────────────────────────────────────

class TestLoadModelEndpoint:
    def test_load_unloaded_model_returns_200(self, models_client):
        response = models_client.post(
            "/models/default_solution/load",
            json={"model_name": "default_solution", "force_reload": False},
        )
        assert response.status_code == 200

    def test_load_model_response_has_status(self, models_client):
        response = models_client.post(
            "/models/default_solution/load",
            json={"model_name": "default_solution", "force_reload": False},
        )
        assert "status" in response.json()

    def test_load_already_loaded_model_returns_already_loaded(self, models_client):
        response = models_client.post(
            "/models/mathematical_ocr/load",
            json={"model_name": "mathematical_ocr", "force_reload": False},
        )
        assert response.json()["status"] == "already_loaded"

    def test_load_unknown_model_returns_404(self, models_client):
        response = models_client.post(
            "/models/nonexistent/load",
            json={"model_name": "nonexistent", "force_reload": False},
        )
        assert response.status_code == 404

    def test_force_reload_calls_unload_then_load(self, models_client):
        from src.api.main import app
        registry = app.state.model_manager.get_registry()
        ocr_model = registry.get_model("mathematical_ocr")
        ocr_model.is_model_loaded.return_value = True

        response = models_client.post(
            "/models/mathematical_ocr/load",
            json={"model_name": "mathematical_ocr", "force_reload": True},
        )
        assert response.status_code == 200
        ocr_model.unload_model.assert_called_once()
        ocr_model.load_model.assert_called_once()


# ──────────────────────────────────────────────────────────────
# POST /models/{model_name}/unload
# ──────────────────────────────────────────────────────────────

class TestUnloadModelEndpoint:
    def test_unload_loaded_model_returns_200(self, models_client):
        response = models_client.post("/models/mathematical_ocr/unload")
        assert response.status_code == 200

    def test_unload_model_response_has_status(self, models_client):
        response = models_client.post("/models/mathematical_ocr/unload")
        assert "status" in response.json()

    def test_unload_not_loaded_model_returns_not_loaded_status(self, models_client):
        response = models_client.post("/models/default_solution/unload")
        assert response.json()["status"] == "not_loaded"

    def test_unload_unknown_model_returns_404(self, models_client):
        response = models_client.post("/models/nonexistent/unload")
        assert response.status_code == 404

    def test_unload_calls_model_unload_method(self, models_client):
        from src.api.main import app
        registry = app.state.model_manager.get_registry()
        ocr_model = registry.get_model("mathematical_ocr")
        ocr_model.unload_model.reset_mock()

        models_client.post("/models/mathematical_ocr/unload")
        ocr_model.unload_model.assert_called_once()


# ──────────────────────────────────────────────────────────────
# GET /models/registry/status
# ──────────────────────────────────────────────────────────────

class TestRegistryStatusEndpoint:
    def test_registry_status_returns_200(self, models_client):
        response = models_client.get("/models/registry/status")
        assert response.status_code == 200

    def test_registry_status_has_registry_status_key(self, models_client):
        response = models_client.get("/models/registry/status")
        assert "registry_status" in response.json()

    def test_registry_status_has_total_models(self, models_client):
        response = models_client.get("/models/registry/status")
        assert "total_models" in response.json()

    def test_registry_status_has_loaded_models(self, models_client):
        response = models_client.get("/models/registry/status")
        assert "loaded_models" in response.json()

    def test_registry_status_has_unloaded_models(self, models_client):
        response = models_client.get("/models/registry/status")
        assert "unloaded_models" in response.json()

    def test_registry_status_has_load_percentage(self, models_client):
        response = models_client.get("/models/registry/status")
        assert "load_percentage" in response.json()

    def test_registry_status_total_equals_loaded_plus_unloaded(self, models_client):
        response = models_client.get("/models/registry/status")
        data = response.json()
        assert data["total_models"] == data["loaded_models"] + data["unloaded_models"]

    def test_registry_status_load_percentage_range(self, models_client):
        response = models_client.get("/models/registry/status")
        assert 0.0 <= response.json()["load_percentage"] <= 100.0
