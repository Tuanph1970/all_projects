"""
Integration tests for the ML service.
Tests the full pipeline from API to model using mocked ML models.
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

def _make_image_bytes(text_color=(0, 0, 0)) -> bytes:
    img = Image.new("RGB", (300, 100), color=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.getvalue()


def _make_b64_image() -> str:
    return base64.b64encode(_make_image_bytes()).decode()


# ──────────────────────────────────────────────────────────────
# Full pipeline: file upload → OCR → response
# ──────────────────────────────────────────────────────────────

class TestOCRPipelineIntegration:
    def test_full_ocr_pipeline_returns_text(self, test_client, mock_ocr_result):
        image_bytes = _make_image_bytes()
        response = test_client.post(
            "/ocr/extract",
            files={"file": ("equation.png", image_bytes, "image/png")},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["extracted_text"] == "2x + 3 = 7"
        assert data["confidence"] == 0.92

    def test_full_ocr_pipeline_metadata_contains_model_info(self, test_client):
        image_bytes = _make_image_bytes()
        response = test_client.post(
            "/ocr/extract",
            files={"file": ("test.png", image_bytes, "image/png")},
        )
        data = response.json()
        assert "metadata" in data
        assert "model_used" in data["metadata"]

    def test_base64_pipeline_returns_same_result(self, test_client, mock_ocr_result):
        response = test_client.post(
            "/ocr/extract-base64",
            json={"image_base64": _make_b64_image()},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["extracted_text"] == mock_ocr_result.extracted_text

    def test_batch_pipeline_processes_all_images(self, test_client):
        images = [_make_b64_image() for _ in range(3)]
        response = test_client.post(
            "/ocr/extract-batch",
            json={"images_base64": images},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) == 3
        assert data["successful_count"] == 3
        assert data["failed_count"] == 0


# ──────────────────────────────────────────────────────────────
# Health + OCR integration
# ──────────────────────────────────────────────────────────────

class TestHealthAndOCRIntegration:
    def test_service_healthy_before_ocr(self, test_client):
        health_response = test_client.get("/health")
        assert health_response.status_code == 200
        assert health_response.json()["status"] == "healthy"

        ocr_response = test_client.post(
            "/ocr/extract",
            files={"file": ("test.png", _make_image_bytes(), "image/png")},
        )
        assert ocr_response.status_code == 200

    def test_liveness_always_returns_alive(self, test_client):
        response = test_client.get("/live")
        assert response.status_code == 200
        assert response.json()["status"] == "alive"


# ──────────────────────────────────────────────────────────────
# Math parser + OCR model integration
# ──────────────────────────────────────────────────────────────

class TestMathParserOCRIntegration:
    @pytest.fixture(autouse=True)
    def mock_transformers(self):
        mock_processor = MagicMock()
        mock_model = MagicMock()
        with (
            patch("src.models.ocr_model.TrOCRProcessor.from_pretrained", return_value=mock_processor),
            patch("src.models.ocr_model.VisionEncoderDecoderModel.from_pretrained", return_value=mock_model),
        ):
            yield

    def test_math_corrections_applied_in_mathematical_model(self):
        from src.models.ocr_model import MathematicalOCRModel
        model = MathematicalOCRModel(model_name="test/model", device="cpu")
        corrected = model._apply_math_corrections("3 × 4 ÷ 2 + π − 1")
        assert "×" not in corrected
        assert "÷" not in corrected
        assert "π" not in corrected
        assert "−" not in corrected

    def test_parser_evaluates_ocr_output(self):
        from src.utils.math_parser import MathExpressionParser
        parser = MathExpressionParser()
        # Simulate OCR extracting "3 + 4" and parser evaluating it
        result = parser.evaluate_expression("3 + 4")
        assert result == 7

    def test_parser_handles_corrected_ocr_output(self):
        from src.models.ocr_model import MathematicalOCRModel
        from src.utils.math_parser import MathExpressionParser

        model = MathematicalOCRModel(model_name="test/model", device="cpu")
        parser = MathExpressionParser()

        # OCR text with symbols → corrections → parse
        raw_text = "3 × 4"
        corrected = model._apply_math_corrections(raw_text)
        result = parser.evaluate_expression(corrected)
        assert result == 12


# ──────────────────────────────────────────────────────────────
# Image preprocessing + OCR integration
# ──────────────────────────────────────────────────────────────

class TestImagePreprocessingOCRIntegration:
    @pytest.fixture(autouse=True)
    def mock_transformers(self):
        mock_processor = MagicMock()
        mock_model = MagicMock()
        with (
            patch("src.models.ocr_model.TrOCRProcessor.from_pretrained", return_value=mock_processor),
            patch("src.models.ocr_model.VisionEncoderDecoderModel.from_pretrained", return_value=mock_model),
        ):
            yield

    def test_preprocessed_image_accepted_by_ocr_prepare(self):
        from src.utils.image_processing import ImagePreprocessor
        from src.models.ocr_model import OCRModel

        preprocessor = ImagePreprocessor()
        model = OCRModel(model_name="test/model", device="cpu")

        # Preprocess an image
        raw_image = Image.new("RGBA", (200, 100), (200, 200, 200, 255))
        gray_image = preprocessor._convert_to_grayscale(preprocessor._load_image(raw_image))

        # Convert back to RGB for OCR input
        rgb_image = gray_image.convert("RGB")

        # OCR prepare should accept it without error
        prepared = model._prepare_image(rgb_image)
        assert prepared.mode == "RGB"

    def test_statistics_consistent_with_image_content(self):
        from src.utils.image_processing import ImagePreprocessor

        preprocessor = ImagePreprocessor()

        white_img = Image.new("RGB", (100, 100), (255, 255, 255))
        black_img = Image.new("RGB", (100, 100), (0, 0, 0))

        white_stats = preprocessor.get_image_statistics(white_img)
        black_stats = preprocessor.get_image_statistics(black_img)

        assert white_stats["mean_brightness"] > black_stats["mean_brightness"]
        assert white_stats["mean_brightness"] > 200
        assert black_stats["mean_brightness"] < 50
