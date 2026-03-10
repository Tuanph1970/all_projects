"""
Pytest configuration and fixtures for llmOCR tests.
"""
import io
import pytest
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from unittest.mock import MagicMock, patch


# ──────────────────────────────────────────────────────────────
# Image fixtures
# ──────────────────────────────────────────────────────────────

@pytest.fixture
def sample_image():
    """100x100 white RGB image."""
    return Image.new("RGB", (100, 100), color=(255, 255, 255))


@pytest.fixture
def sample_image_bytes(sample_image):
    """100x100 white image as PNG bytes."""
    buf = io.BytesIO()
    sample_image.save(buf, format="PNG")
    buf.seek(0)
    return buf.getvalue()


@pytest.fixture
def math_equation_image():
    """Simple image with math text drawn on it."""
    img = Image.new("RGB", (400, 100), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.text((10, 30), "2x + 3 = 7", fill=(0, 0, 0))
    return img


@pytest.fixture
def small_image():
    """Very small 10x10 image for edge case testing."""
    return Image.new("RGB", (10, 10), color=(200, 200, 200))


@pytest.fixture
def grayscale_image():
    """100x100 grayscale image."""
    return Image.new("L", (100, 100), color=128)


@pytest.fixture
def rgba_image():
    """100x100 RGBA image."""
    return Image.new("RGBA", (100, 100), color=(255, 255, 255, 255))


@pytest.fixture
def numpy_rgb_array():
    """100x100x3 numpy array (RGB)."""
    return np.ones((100, 100, 3), dtype=np.uint8) * 200


@pytest.fixture
def numpy_grayscale_array():
    """100x100 numpy array (grayscale)."""
    return np.ones((100, 100), dtype=np.uint8) * 128


# ──────────────────────────────────────────────────────────────
# Mock OCR model
# ──────────────────────────────────────────────────────────────

@pytest.fixture
def mock_ocr_result():
    """Mock OCR result for testing."""
    from src.models.base import OCRResult
    return OCRResult(
        success=True,
        extracted_text="2x + 3 = 7",
        confidence=0.92,
        processing_time=0.25,
        metadata={"model_name": "mock_model", "device": "cpu"}
    )


@pytest.fixture
def mock_ocr_model(mock_ocr_result):
    """Mock OCR model that returns predictable results."""
    model = MagicMock()
    model.is_model_loaded.return_value = True
    model.predict.return_value = mock_ocr_result
    model.get_model_info.return_value = {
        "model_name": "mock_ocr",
        "model_type": "OCR",
        "is_loaded": True,
        "device": "cpu",
    }
    return model


# ──────────────────────────────────────────────────────────────
# FastAPI test client
# ──────────────────────────────────────────────────────────────

@pytest.fixture
def mock_model_registry(mock_ocr_model):
    """Mock model registry for FastAPI tests."""
    registry = MagicMock()
    registry.list_models.return_value = ["mathematical_ocr", "default_ocr"]
    registry.get_model.return_value = mock_ocr_model
    return registry


@pytest.fixture
def test_client(mock_model_registry):
    """FastAPI TestClient with mocked model registry."""
    with patch("src.models.base.get_model_registry", return_value=mock_model_registry):
        from fastapi.testclient import TestClient
        from src.api.main import app
        client = TestClient(app)
        yield client
