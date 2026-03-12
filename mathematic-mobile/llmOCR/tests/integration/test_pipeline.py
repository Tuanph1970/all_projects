"""
Integration tests for the full OCR → Solution pipeline.
Tests the complete flow from image upload through text extraction to math solving,
using mocked ML models to avoid loading real weights.
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

def _make_b64_image(text: str = "2x + 3 = 7", width: int = 300, height: int = 100) -> str:
    img = Image.new("RGB", (width, height), color=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return base64.b64encode(buf.getvalue()).decode()


def _make_image_bytes(width: int = 300, height: int = 100) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (width, height), color=(255, 255, 255)).save(buf, format="PNG")
    buf.seek(0)
    return buf.getvalue()


# ──────────────────────────────────────────────────────────────
# Shared fixtures
# ──────────────────────────────────────────────────────────────

@pytest.fixture
def pipeline_ocr_result():
    return OCRResult(
        success=True,
        extracted_text="2x + 3 = 7",
        confidence=0.92,
        processing_time=0.25,
        metadata={"model_used": "mathematical_ocr", "model_type": "ocr"},
    )


@pytest.fixture
def pipeline_solution_result():
    return SolutionResult(
        success=True,
        problem_type="linear_equation",
        solution="x = 2",
        steps=["2x + 3 = 7", "2x = 4", "x = 2"],
        final_answer="x = 2",
        confidence=0.90,
        processing_time=0.35,
        metadata={"model_used": "default_solution"},
    )


@pytest.fixture
def pipeline_client(pipeline_ocr_result, pipeline_solution_result):
    """
    TestClient with full OCR and solution pipeline mocked.
    Covers: OCR extract → text → solve flow.
    """
    from src.api.main import app
    from src.api.dependencies import (
        get_extract_text_use_case,
        get_batch_extract_text_use_case,
        get_solve_problem_use_case,
        get_ocr_and_solve_use_case,
        get_batch_solve_problem_use_case,
    )

    # OCR use cases
    mock_ocr_uc = MagicMock()
    mock_ocr_uc.execute.return_value = pipeline_ocr_result

    mock_batch_ocr_uc = MagicMock()
    mock_batch_ocr_uc.execute.return_value = [pipeline_ocr_result, pipeline_ocr_result]

    # Solution use cases
    mock_solve_uc = MagicMock()
    mock_solve_uc.execute.return_value = pipeline_solution_result

    mock_pipeline_uc = MagicMock()
    mock_pipeline_uc.execute.return_value = {
        "ocr_result": pipeline_ocr_result,
        "solution_result": pipeline_solution_result,
    }

    mock_batch_solve_uc = MagicMock()
    mock_batch_solve_uc.execute.return_value = [pipeline_solution_result]

    # Registry mock for direct app.state access (health, models endpoints)
    mock_registry = MagicMock()
    mock_registry.list_models.return_value = ["mathematical_ocr", "default_solution"]
    mock_model = MagicMock()
    mock_model.is_model_loaded.return_value = True
    mock_model.get_model_info.return_value = {"model_type": "ocr", "device": "cpu"}
    mock_registry.get_model.return_value = mock_model
    mock_manager = MagicMock()
    mock_manager.get_registry.return_value = mock_registry
    mock_manager.initialize_default_models = AsyncMock(return_value=None)

    app.dependency_overrides[get_extract_text_use_case] = lambda: mock_ocr_uc
    app.dependency_overrides[get_batch_extract_text_use_case] = lambda: mock_batch_ocr_uc
    app.dependency_overrides[get_solve_problem_use_case] = lambda: mock_solve_uc
    app.dependency_overrides[get_ocr_and_solve_use_case] = lambda: mock_pipeline_uc
    app.dependency_overrides[get_batch_solve_problem_use_case] = lambda: mock_batch_solve_uc

    with patch("src.api.main.ModelManager", return_value=mock_manager):
        with TestClient(app) as client:
            yield client

    app.dependency_overrides.clear()


# ──────────────────────────────────────────────────────────────
# OCR → text extraction
# ──────────────────────────────────────────────────────────────

class TestOCRExtractionStep:
    def test_ocr_extract_returns_text(self, pipeline_client, pipeline_ocr_result):
        response = pipeline_client.post(
            "/ocr/extract",
            files={"file": ("equation.png", _make_image_bytes(), "image/png")},
        )
        assert response.status_code == 200
        assert response.json()["extracted_text"] == pipeline_ocr_result.extracted_text

    def test_ocr_extract_returns_high_confidence(self, pipeline_client):
        response = pipeline_client.post(
            "/ocr/extract",
            files={"file": ("equation.png", _make_image_bytes(), "image/png")},
        )
        assert response.json()["confidence"] >= 0.9

    def test_ocr_base64_produces_same_text_as_file_upload(
        self, pipeline_client, pipeline_ocr_result
    ):
        file_resp = pipeline_client.post(
            "/ocr/extract",
            files={"file": ("eq.png", _make_image_bytes(), "image/png")},
        )
        b64_resp = pipeline_client.post(
            "/ocr/extract-base64",
            json={"image_base64": _make_b64_image()},
        )
        assert file_resp.json()["extracted_text"] == b64_resp.json()["extracted_text"]


# ──────────────────────────────────────────────────────────────
# text → math solution
# ──────────────────────────────────────────────────────────────

class TestSolutionStep:
    def test_solve_returns_final_answer(self, pipeline_client, pipeline_solution_result):
        response = pipeline_client.post(
            "/solution/solve",
            json={"problem": "2x + 3 = 7"},
        )
        assert response.status_code == 200
        assert response.json()["final_answer"] == pipeline_solution_result.final_answer

    def test_solve_returns_steps(self, pipeline_client, pipeline_solution_result):
        response = pipeline_client.post(
            "/solution/solve",
            json={"problem": "2x + 3 = 7"},
        )
        assert len(response.json()["steps"]) == len(pipeline_solution_result.steps)

    def test_solve_confidence_above_threshold(self, pipeline_client):
        response = pipeline_client.post(
            "/solution/solve",
            json={"problem": "2x + 3 = 7", "confidence_threshold": 0.7},
        )
        assert response.json()["confidence"] >= 0.7


# ──────────────────────────────────────────────────────────────
# Full end-to-end: image → OCR text → math solution
# ──────────────────────────────────────────────────────────────

class TestEndToEndPipeline:
    def test_ocr_solve_returns_both_text_and_solution(
        self, pipeline_client, pipeline_ocr_result, pipeline_solution_result
    ):
        response = pipeline_client.post(
            "/solution/ocr-solve",
            json={"image_base64": _make_b64_image()},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["extracted_text"] == pipeline_ocr_result.extracted_text
        assert data["final_answer"] == pipeline_solution_result.final_answer

    def test_ocr_solve_success_flag_is_true(self, pipeline_client):
        response = pipeline_client.post(
            "/solution/ocr-solve",
            json={"image_base64": _make_b64_image()},
        )
        assert response.json()["success"] is True

    def test_ocr_solve_total_time_is_positive(self, pipeline_client):
        response = pipeline_client.post(
            "/solution/ocr-solve",
            json={"image_base64": _make_b64_image()},
        )
        assert response.json()["total_processing_time"] >= 0.0

    def test_pipeline_with_failed_ocr_returns_partial_result(self, pipeline_client):
        from src.api.main import app
        from src.api.dependencies import get_ocr_and_solve_use_case

        failed_ocr = OCRResult(
            success=False,
            extracted_text="",
            confidence=0.0,
            processing_time=0.05,
            metadata={"error": "no_text_detected"},
        )
        partial_uc = MagicMock()
        partial_uc.execute.return_value = {"ocr_result": failed_ocr, "solution_result": None}

        app.dependency_overrides[get_ocr_and_solve_use_case] = lambda: partial_uc
        try:
            response = pipeline_client.post(
                "/solution/ocr-solve",
                json={"image_base64": _make_b64_image()},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is False
            assert data["extracted_text"] == ""
        finally:
            from src.api.dependencies import get_ocr_and_solve_use_case as dep
            app.dependency_overrides.pop(dep, None)


# ──────────────────────────────────────────────────────────────
# Batch pipeline: multiple images or problems
# ──────────────────────────────────────────────────────────────

class TestBatchPipeline:
    def test_batch_ocr_and_batch_solve_chain(self, pipeline_client):
        """Simulates batch OCR followed by batch solve of extracted texts."""
        # Step 1: batch OCR
        ocr_resp = pipeline_client.post(
            "/ocr/extract-batch",
            json={"images_base64": [_make_b64_image(), _make_b64_image()]},
        )
        assert ocr_resp.status_code == 200
        ocr_data = ocr_resp.json()
        assert ocr_data["successful_count"] == 2

        # Step 2: use extracted texts for batch solve
        problems = [r["extracted_text"] for r in ocr_data["results"] if r["success"]]
        solve_resp = pipeline_client.post(
            "/solution/solve-batch",
            json={"problems": problems},
        )
        assert solve_resp.status_code == 200
        assert solve_resp.json()["successful_count"] == len(problems)

    def test_health_check_passes_throughout_pipeline(self, pipeline_client):
        """Service must stay healthy across the full pipeline execution."""
        assert pipeline_client.get("/health").json()["status"] == "healthy"

        pipeline_client.post(
            "/ocr/extract",
            files={"file": ("eq.png", _make_image_bytes(), "image/png")},
        )
        pipeline_client.post("/solution/solve", json={"problem": "x = 1"})

        assert pipeline_client.get("/health").json()["status"] == "healthy"


# ──────────────────────────────────────────────────────────────
# Error propagation across pipeline
# ──────────────────────────────────────────────────────────────

class TestPipelineErrorHandling:
    def test_ocr_model_unavailable_returns_503(self, pipeline_client):
        from src.api.main import app
        from src.api.dependencies import get_extract_text_use_case

        unavailable_uc = MagicMock()
        unavailable_uc.execute.side_effect = ModelUnavailableError("mathematical_ocr")

        app.dependency_overrides[get_extract_text_use_case] = lambda: unavailable_uc
        try:
            response = pipeline_client.post(
                "/ocr/extract",
                files={"file": ("eq.png", _make_image_bytes(), "image/png")},
            )
            assert response.status_code == 503
        finally:
            from src.api.dependencies import get_extract_text_use_case as dep
            app.dependency_overrides.pop(dep, None)

    def test_solution_model_unavailable_returns_503(self, pipeline_client):
        from src.api.main import app
        from src.api.dependencies import get_solve_problem_use_case

        unavailable_uc = MagicMock()
        unavailable_uc.execute.side_effect = ModelUnavailableError("default_solution")

        app.dependency_overrides[get_solve_problem_use_case] = lambda: unavailable_uc
        try:
            response = pipeline_client.post(
                "/solution/solve",
                json={"problem": "2x + 3 = 7"},
            )
            assert response.status_code == 503
        finally:
            from src.api.dependencies import get_solve_problem_use_case as dep
            app.dependency_overrides.pop(dep, None)

    def test_invalid_image_rejected_before_ocr(self, pipeline_client):
        """Non-image uploads are rejected with 400 before reaching the OCR model."""
        response = pipeline_client.post(
            "/ocr/extract",
            files={"file": ("doc.pdf", b"%PDF-1.4 fake content", "application/pdf")},
        )
        assert response.status_code == 400
