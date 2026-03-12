"""
Tests for solution router endpoints.
Uses mocked use cases — no real ML models are loaded.
"""
import io
import base64
import pytest
from PIL import Image
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi.testclient import TestClient

from src.domain.shared.value_objects import OCRResult, SolutionResult
from src.domain.shared.exceptions import ModelUnavailableError


# ──────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────

def _make_b64_image(width: int = 100, height: int = 100) -> str:
    buf = io.BytesIO()
    Image.new("RGB", (width, height), color=(255, 255, 255)).save(buf, format="PNG")
    buf.seek(0)
    return base64.b64encode(buf.getvalue()).decode()


# ──────────────────────────────────────────────────────────────
# Shared fixtures
# ──────────────────────────────────────────────────────────────

@pytest.fixture
def mock_solution_result():
    return SolutionResult(
        success=True,
        problem_type="linear_equation",
        solution="x = 2",
        steps=["2x + 3 = 7", "2x = 4", "x = 2"],
        final_answer="x = 2",
        confidence=0.85,
        processing_time=0.15,
        metadata={"model_used": "default_solution"},
    )


@pytest.fixture
def mock_ocr_result_for_pipeline():
    return OCRResult(
        success=True,
        extracted_text="2x + 3 = 7",
        confidence=0.92,
        processing_time=0.25,
        metadata={"model_used": "mathematical_ocr"},
    )


@pytest.fixture
def solution_client(mock_solution_result, mock_ocr_result_for_pipeline):
    """TestClient with all solution dependencies mocked."""
    from src.api.main import app
    from src.api.dependencies import (
        get_solve_problem_use_case,
        get_batch_solve_problem_use_case,
        get_ocr_and_solve_use_case,
    )

    mock_solve_uc = MagicMock()
    mock_solve_uc.execute.return_value = mock_solution_result

    mock_batch_uc = MagicMock()
    mock_batch_uc.execute.return_value = [mock_solution_result, mock_solution_result]

    mock_pipeline_uc = MagicMock()
    mock_pipeline_uc.execute.return_value = {
        "ocr_result": mock_ocr_result_for_pipeline,
        "solution_result": mock_solution_result,
    }

    # Registry mock for GET /solution/models (accesses app.state directly)
    mock_sol_model = MagicMock()
    mock_sol_model.get_model_info.return_value = {"model_type": "solution", "device": "cpu"}
    mock_registry = MagicMock()
    mock_registry.list_models.return_value = ["default_solution"]
    mock_registry.get_model.return_value = mock_sol_model
    mock_manager = MagicMock()
    mock_manager.get_registry.return_value = mock_registry
    mock_manager.initialize_default_models = AsyncMock(return_value=None)

    app.dependency_overrides[get_solve_problem_use_case] = lambda: mock_solve_uc
    app.dependency_overrides[get_batch_solve_problem_use_case] = lambda: mock_batch_uc
    app.dependency_overrides[get_ocr_and_solve_use_case] = lambda: mock_pipeline_uc

    with patch("src.api.main.ModelManager", return_value=mock_manager):
        with TestClient(app) as client:
            yield client

    app.dependency_overrides.clear()


# ──────────────────────────────────────────────────────────────
# POST /solution/solve
# ──────────────────────────────────────────────────────────────

class TestSolveProblemEndpoint:
    def test_solve_returns_200_on_success(self, solution_client):
        response = solution_client.post(
            "/solution/solve",
            json={"problem": "2x + 3 = 7"},
        )
        assert response.status_code == 200

    def test_solve_response_has_success_field(self, solution_client):
        response = solution_client.post(
            "/solution/solve",
            json={"problem": "2x + 3 = 7"},
        )
        assert "success" in response.json()

    def test_solve_response_success_is_true(self, solution_client, mock_solution_result):
        response = solution_client.post(
            "/solution/solve",
            json={"problem": "2x + 3 = 7"},
        )
        assert response.json()["success"] is True

    def test_solve_response_has_solution_field(self, solution_client):
        response = solution_client.post(
            "/solution/solve",
            json={"problem": "2x + 3 = 7"},
        )
        assert "solution" in response.json()

    def test_solve_response_has_steps_list(self, solution_client):
        response = solution_client.post(
            "/solution/solve",
            json={"problem": "2x + 3 = 7"},
        )
        data = response.json()
        assert "steps" in data
        assert isinstance(data["steps"], list)

    def test_solve_response_has_final_answer(self, solution_client):
        response = solution_client.post(
            "/solution/solve",
            json={"problem": "2x + 3 = 7"},
        )
        assert "final_answer" in response.json()

    def test_solve_response_confidence_in_range(self, solution_client):
        response = solution_client.post(
            "/solution/solve",
            json={"problem": "2x + 3 = 7"},
        )
        confidence = response.json()["confidence"]
        assert 0.0 <= confidence <= 1.0

    def test_solve_response_has_processing_time(self, solution_client):
        response = solution_client.post(
            "/solution/solve",
            json={"problem": "2x + 3 = 7"},
        )
        assert "processing_time" in response.json()

    def test_solve_response_has_metadata(self, solution_client):
        response = solution_client.post(
            "/solution/solve",
            json={"problem": "2x + 3 = 7"},
        )
        assert "metadata" in response.json()

    def test_solve_missing_problem_returns_422(self, solution_client):
        response = solution_client.post(
            "/solution/solve",
            json={"confidence_threshold": 0.7},
        )
        assert response.status_code == 422

    def test_solve_returns_mock_answer(self, solution_client, mock_solution_result):
        response = solution_client.post(
            "/solution/solve",
            json={"problem": "2x + 3 = 7"},
        )
        assert response.json()["final_answer"] == mock_solution_result.final_answer

    def test_solve_returns_503_when_model_unavailable(self, solution_client):
        from src.api.main import app
        from src.api.dependencies import get_solve_problem_use_case

        unavailable_uc = MagicMock()
        unavailable_uc.execute.side_effect = ModelUnavailableError("default_solution")

        app.dependency_overrides[get_solve_problem_use_case] = lambda: unavailable_uc
        try:
            response = solution_client.post(
                "/solution/solve",
                json={"problem": "2x + 3 = 7"},
            )
            assert response.status_code == 503
        finally:
            from src.api.dependencies import get_solve_problem_use_case as dep
            app.dependency_overrides.pop(dep, None)


# ──────────────────────────────────────────────────────────────
# POST /solution/ocr-solve
# ──────────────────────────────────────────────────────────────

class TestOCRAndSolveEndpoint:
    def test_ocr_solve_returns_200_on_success(self, solution_client):
        response = solution_client.post(
            "/solution/ocr-solve",
            json={"image_base64": _make_b64_image()},
        )
        assert response.status_code == 200

    def test_ocr_solve_response_has_extracted_text(self, solution_client):
        response = solution_client.post(
            "/solution/ocr-solve",
            json={"image_base64": _make_b64_image()},
        )
        assert "extracted_text" in response.json()

    def test_ocr_solve_response_has_ocr_confidence(self, solution_client):
        response = solution_client.post(
            "/solution/ocr-solve",
            json={"image_base64": _make_b64_image()},
        )
        data = response.json()
        assert "ocr_confidence" in data
        assert 0.0 <= data["ocr_confidence"] <= 1.0

    def test_ocr_solve_response_has_solution(self, solution_client):
        response = solution_client.post(
            "/solution/ocr-solve",
            json={"image_base64": _make_b64_image()},
        )
        assert "solution" in response.json()

    def test_ocr_solve_response_has_final_answer(self, solution_client):
        response = solution_client.post(
            "/solution/ocr-solve",
            json={"image_base64": _make_b64_image()},
        )
        assert "final_answer" in response.json()

    def test_ocr_solve_response_has_total_processing_time(self, solution_client):
        response = solution_client.post(
            "/solution/ocr-solve",
            json={"image_base64": _make_b64_image()},
        )
        assert "total_processing_time" in response.json()

    def test_ocr_solve_invalid_base64_returns_400(self, solution_client):
        response = solution_client.post(
            "/solution/ocr-solve",
            json={"image_base64": "not!!valid!!base64"},
        )
        assert response.status_code == 400

    def test_ocr_solve_missing_image_returns_422(self, solution_client):
        response = solution_client.post(
            "/solution/ocr-solve",
            json={"ocr_confidence_threshold": 0.8},
        )
        assert response.status_code == 422

    def test_ocr_solve_returns_503_when_model_unavailable(self, solution_client):
        from src.api.main import app
        from src.api.dependencies import get_ocr_and_solve_use_case

        unavailable_uc = MagicMock()
        unavailable_uc.execute.side_effect = ModelUnavailableError("default_solution")

        app.dependency_overrides[get_ocr_and_solve_use_case] = lambda: unavailable_uc
        try:
            response = solution_client.post(
                "/solution/ocr-solve",
                json={"image_base64": _make_b64_image()},
            )
            assert response.status_code == 503
        finally:
            from src.api.dependencies import get_ocr_and_solve_use_case as dep
            app.dependency_overrides.pop(dep, None)

    def test_ocr_solve_returns_failure_when_ocr_fails(self, solution_client):
        from src.api.main import app
        from src.api.dependencies import get_ocr_and_solve_use_case

        failed_ocr = OCRResult(
            success=False,
            extracted_text="",
            confidence=0.0,
            processing_time=0.1,
            metadata={"error": "ocr_failed"},
        )
        pipeline_uc = MagicMock()
        pipeline_uc.execute.return_value = {"ocr_result": failed_ocr, "solution_result": None}

        app.dependency_overrides[get_ocr_and_solve_use_case] = lambda: pipeline_uc
        try:
            response = solution_client.post(
                "/solution/ocr-solve",
                json={"image_base64": _make_b64_image()},
            )
            assert response.status_code == 200
            assert response.json()["success"] is False
        finally:
            from src.api.dependencies import get_ocr_and_solve_use_case as dep
            app.dependency_overrides.pop(dep, None)


# ──────────────────────────────────────────────────────────────
# POST /solution/solve-batch
# ──────────────────────────────────────────────────────────────

class TestBatchSolveProblemEndpoint:
    def test_batch_solve_returns_200(self, solution_client):
        response = solution_client.post(
            "/solution/solve-batch",
            json={"problems": ["2x + 3 = 7", "x^2 = 4"]},
        )
        assert response.status_code == 200

    def test_batch_solve_results_count_matches_input(self, solution_client):
        from src.api.main import app
        from src.api.dependencies import get_batch_solve_problem_use_case
        from src.domain.shared.value_objects import SolutionResult

        results = [
            SolutionResult(
                success=True, problem_type="linear", solution="x=1",
                steps=[], final_answer="x=1", confidence=0.9,
                processing_time=0.1, metadata={},
            )
            for _ in range(3)
        ]
        batch_uc = MagicMock()
        batch_uc.execute.return_value = results

        app.dependency_overrides[get_batch_solve_problem_use_case] = lambda: batch_uc
        try:
            response = solution_client.post(
                "/solution/solve-batch",
                json={"problems": ["p1", "p2", "p3"]},
            )
            assert len(response.json()["results"]) == 3
        finally:
            from src.api.dependencies import get_batch_solve_problem_use_case as dep
            app.dependency_overrides.pop(dep, None)

    def test_batch_solve_has_successful_count(self, solution_client):
        response = solution_client.post(
            "/solution/solve-batch",
            json={"problems": ["2x = 4"]},
        )
        assert "successful_count" in response.json()

    def test_batch_solve_has_failed_count(self, solution_client):
        response = solution_client.post(
            "/solution/solve-batch",
            json={"problems": ["2x = 4"]},
        )
        assert "failed_count" in response.json()

    def test_batch_solve_has_total_processing_time(self, solution_client):
        response = solution_client.post(
            "/solution/solve-batch",
            json={"problems": ["2x = 4"]},
        )
        assert "total_processing_time" in response.json()

    def test_batch_solve_counts_sum_to_results(self, solution_client):
        response = solution_client.post(
            "/solution/solve-batch",
            json={"problems": ["2x + 3 = 7", "x^2 = 4"]},
        )
        data = response.json()
        assert data["successful_count"] + data["failed_count"] == len(data["results"])

    def test_batch_solve_empty_problems_returns_422(self, solution_client):
        response = solution_client.post(
            "/solution/solve-batch",
            json={"problems": []},
        )
        assert response.status_code == 422

    def test_batch_solve_returns_503_when_model_unavailable(self, solution_client):
        from src.api.main import app
        from src.api.dependencies import get_batch_solve_problem_use_case

        unavailable_uc = MagicMock()
        unavailable_uc.execute.side_effect = ModelUnavailableError("default_solution")

        app.dependency_overrides[get_batch_solve_problem_use_case] = lambda: unavailable_uc
        try:
            response = solution_client.post(
                "/solution/solve-batch",
                json={"problems": ["2x = 4"]},
            )
            assert response.status_code == 503
        finally:
            from src.api.dependencies import get_batch_solve_problem_use_case as dep
            app.dependency_overrides.pop(dep, None)


# ──────────────────────────────────────────────────────────────
# GET /solution/models
# ──────────────────────────────────────────────────────────────

class TestListSolutionModelsEndpoint:
    def test_list_models_returns_200(self, solution_client):
        response = solution_client.get("/solution/models")
        assert response.status_code == 200

    def test_list_models_has_models_key(self, solution_client):
        response = solution_client.get("/solution/models")
        assert "models" in response.json()

    def test_list_models_is_list(self, solution_client):
        response = solution_client.get("/solution/models")
        assert isinstance(response.json()["models"], list)
