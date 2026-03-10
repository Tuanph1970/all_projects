"""
Tests for OCR router endpoints.
Uses mocked model registry so no real ML models are loaded.
"""
import io
import base64
import pytest
from PIL import Image
from unittest.mock import MagicMock, patch

from src.models.base import OCRResult


# ──────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────

def _make_image_bytes(width=100, height=100) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (width, height), color=(255, 255, 255)).save(buf, format="PNG")
    buf.seek(0)
    return buf.getvalue()


def _make_b64_image(width=100, height=100) -> str:
    return base64.b64encode(_make_image_bytes(width, height)).decode()


# ──────────────────────────────────────────────────────────────
# POST /ocr/extract (file upload)
# ──────────────────────────────────────────────────────────────

class TestExtractEndpoint:
    def test_extract_returns_200_on_success(self, test_client, sample_image_bytes):
        response = test_client.post(
            "/ocr/extract",
            files={"file": ("test.png", sample_image_bytes, "image/png")},
        )
        assert response.status_code == 200

    def test_extract_response_has_success_field(self, test_client, sample_image_bytes):
        response = test_client.post(
            "/ocr/extract",
            files={"file": ("test.png", sample_image_bytes, "image/png")},
        )
        data = response.json()
        assert "success" in data

    def test_extract_response_has_extracted_text(self, test_client, sample_image_bytes):
        response = test_client.post(
            "/ocr/extract",
            files={"file": ("test.png", sample_image_bytes, "image/png")},
        )
        data = response.json()
        assert "extracted_text" in data

    def test_extract_response_has_confidence(self, test_client, sample_image_bytes):
        response = test_client.post(
            "/ocr/extract",
            files={"file": ("test.png", sample_image_bytes, "image/png")},
        )
        data = response.json()
        assert "confidence" in data
        assert 0.0 <= data["confidence"] <= 1.0

    def test_extract_response_has_processing_time(self, test_client, sample_image_bytes):
        response = test_client.post(
            "/ocr/extract",
            files={"file": ("test.png", sample_image_bytes, "image/png")},
        )
        data = response.json()
        assert "processing_time" in data

    def test_extract_response_has_metadata(self, test_client, sample_image_bytes):
        response = test_client.post(
            "/ocr/extract",
            files={"file": ("test.png", sample_image_bytes, "image/png")},
        )
        data = response.json()
        assert "metadata" in data

    def test_extract_rejects_non_image_content_type(self, test_client):
        response = test_client.post(
            "/ocr/extract",
            files={"file": ("test.txt", b"hello world", "text/plain")},
        )
        assert response.status_code == 400

    def test_extract_math_extracted_text(self, test_client, sample_image_bytes, mock_ocr_result):
        response = test_client.post(
            "/ocr/extract",
            files={"file": ("test.png", sample_image_bytes, "image/png")},
        )
        data = response.json()
        # mock_ocr_result returns "2x + 3 = 7"
        assert data["extracted_text"] == mock_ocr_result.extracted_text


# ──────────────────────────────────────────────────────────────
# POST /ocr/extract-base64
# ──────────────────────────────────────────────────────────────

class TestExtractBase64Endpoint:
    def test_extract_base64_returns_200(self, test_client):
        response = test_client.post(
            "/ocr/extract-base64",
            json={"image_base64": _make_b64_image(), "use_mathematical_model": True},
        )
        assert response.status_code == 200

    def test_extract_base64_missing_image_returns_400(self, test_client):
        response = test_client.post(
            "/ocr/extract-base64",
            json={"use_mathematical_model": True},
        )
        assert response.status_code == 400

    def test_extract_base64_invalid_base64_returns_error(self, test_client):
        response = test_client.post(
            "/ocr/extract-base64",
            json={"image_base64": "not-valid-base64!!!"},
        )
        # Error is caught and returned as failed OCR result (not HTTP error)
        data = response.json()
        assert data["success"] is False

    def test_extract_base64_success_field_true(self, test_client):
        response = test_client.post(
            "/ocr/extract-base64",
            json={"image_base64": _make_b64_image()},
        )
        data = response.json()
        assert data["success"] is True

    def test_extract_base64_confidence_in_range(self, test_client):
        response = test_client.post(
            "/ocr/extract-base64",
            json={"image_base64": _make_b64_image()},
        )
        data = response.json()
        assert 0.0 <= data["confidence"] <= 1.0


# ──────────────────────────────────────────────────────────────
# POST /ocr/extract-batch
# ──────────────────────────────────────────────────────────────

class TestExtractBatchEndpoint:
    def test_batch_returns_200(self, test_client):
        response = test_client.post(
            "/ocr/extract-batch",
            json={"images_base64": [_make_b64_image(), _make_b64_image()]},
        )
        assert response.status_code == 200

    def test_batch_results_count_matches_input(self, test_client):
        images = [_make_b64_image() for _ in range(3)]
        response = test_client.post(
            "/ocr/extract-batch",
            json={"images_base64": images},
        )
        data = response.json()
        assert len(data["results"]) == 3

    def test_batch_has_successful_count(self, test_client):
        response = test_client.post(
            "/ocr/extract-batch",
            json={"images_base64": [_make_b64_image()]},
        )
        data = response.json()
        assert "successful_count" in data

    def test_batch_has_failed_count(self, test_client):
        response = test_client.post(
            "/ocr/extract-batch",
            json={"images_base64": [_make_b64_image()]},
        )
        data = response.json()
        assert "failed_count" in data

    def test_batch_has_total_processing_time(self, test_client):
        response = test_client.post(
            "/ocr/extract-batch",
            json={"images_base64": [_make_b64_image()]},
        )
        data = response.json()
        assert "total_processing_time" in data

    def test_batch_successful_count_matches_successful_results(self, test_client):
        response = test_client.post(
            "/ocr/extract-batch",
            json={"images_base64": [_make_b64_image(), _make_b64_image()]},
        )
        data = response.json()
        actual_success = sum(1 for r in data["results"] if r["success"])
        assert data["successful_count"] == actual_success

    def test_batch_invalid_images_counted_as_failed(self, test_client):
        response = test_client.post(
            "/ocr/extract-batch",
            json={"images_base64": [_make_b64_image(), "invalid-base64!!!"]},
        )
        data = response.json()
        assert data["failed_count"] >= 1


# ──────────────────────────────────────────────────────────────
# GET /ocr/models
# ──────────────────────────────────────────────────────────────

class TestListModelsEndpoint:
    def test_list_models_returns_200(self, test_client):
        response = test_client.get("/ocr/models")
        assert response.status_code == 200

    def test_list_models_has_models_key(self, test_client):
        response = test_client.get("/ocr/models")
        data = response.json()
        assert "models" in data

    def test_list_models_is_list(self, test_client):
        response = test_client.get("/ocr/models")
        data = response.json()
        assert isinstance(data["models"], list)
