"""
Unit tests for OCR model classes.
These tests mock transformers to avoid loading actual ML models.
"""
import pytest
import numpy as np
from PIL import Image
from unittest.mock import MagicMock, patch


# ──────────────────────────────────────────────────────────────
# Fixtures / Mock setup
# ──────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def mock_transformers():
    """Auto-mock heavy transformers to avoid loading real models."""
    mock_processor = MagicMock()
    mock_model_cls = MagicMock()
    mock_model_instance = MagicMock()
    mock_model_cls.from_pretrained.return_value = mock_model_instance

    with (
        patch("src.models.ocr_model.TrOCRProcessor.from_pretrained", return_value=mock_processor),
        patch("src.models.ocr_model.VisionEncoderDecoderModel.from_pretrained", return_value=mock_model_instance),
    ):
        yield {
            "processor": mock_processor,
            "model": mock_model_instance,
        }


@pytest.fixture
def ocr_model():
    from src.models.ocr_model import OCRModel
    return OCRModel(model_name="test/model", device="cpu", confidence_threshold=0.8)


@pytest.fixture
def math_ocr_model():
    from src.models.ocr_model import MathematicalOCRModel
    return MathematicalOCRModel(model_name="test/model", device="cpu")


@pytest.fixture
def loaded_ocr_model(ocr_model):
    """OCR model with mocked load."""
    ocr_model.load_model()
    return ocr_model


# ──────────────────────────────────────────────────────────────
# OCRModel tests
# ──────────────────────────────────────────────────────────────

class TestOCRModelInit:
    def test_init_default_values(self):
        from src.models.ocr_model import OCRModel
        model = OCRModel()
        assert model.confidence_threshold == 0.8
        assert model.device == "cpu"
        assert model.is_loaded is False

    def test_not_loaded_initially(self, ocr_model):
        assert ocr_model.is_model_loaded() is False

    def test_model_name_set_correctly(self, ocr_model):
        assert ocr_model.model_name == "test/model"


class TestOCRModelLoad:
    def test_load_model_sets_is_loaded(self, ocr_model):
        ocr_model.load_model()
        assert ocr_model.is_model_loaded() is True

    def test_load_model_loads_processor(self, ocr_model):
        ocr_model.load_model()
        assert ocr_model.processor is not None

    def test_load_model_sets_model(self, ocr_model):
        ocr_model.load_model()
        assert ocr_model.model is not None


class TestOCRModelPredict:
    def test_predict_without_loading_raises_runtime_error(self, ocr_model):
        img = Image.new("RGB", (100, 100), color=(255, 255, 255))
        with pytest.raises(RuntimeError, match="not loaded"):
            ocr_model.predict(img)


class TestPrepareImage:
    def test_prepare_pil_image_returns_pil_image(self, ocr_model):
        img = Image.new("RGB", (100, 100))
        result = ocr_model._prepare_image(img)
        assert isinstance(result, Image.Image)

    def test_prepare_numpy_rgb_array_converts_to_pil(self, ocr_model):
        arr = np.ones((100, 100, 3), dtype=np.uint8) * 200
        result = ocr_model._prepare_image(arr)
        assert isinstance(result, Image.Image)
        assert result.mode == "RGB"

    def test_prepare_numpy_grayscale_converts_to_pil(self, ocr_model):
        arr = np.ones((100, 100), dtype=np.uint8) * 128
        result = ocr_model._prepare_image(arr)
        assert isinstance(result, Image.Image)

    def test_prepare_rgba_image_converts_to_rgb(self, ocr_model):
        img = Image.new("RGBA", (100, 100), (255, 255, 255, 255))
        result = ocr_model._prepare_image(img)
        assert result.mode == "RGB"

    def test_prepare_grayscale_image_converts_to_rgb(self, ocr_model):
        img = Image.new("L", (100, 100), 128)
        result = ocr_model._prepare_image(img)
        assert result.mode == "RGB"

    def test_prepare_invalid_type_raises_type_error(self, ocr_model):
        with pytest.raises(TypeError):
            ocr_model._prepare_image(12345)

    def test_prepare_invalid_numpy_shape_raises_value_error(self, ocr_model):
        """4D array should raise ValueError."""
        arr = np.ones((10, 10, 10, 3), dtype=np.uint8)
        with pytest.raises((ValueError, Exception)):
            ocr_model._prepare_image(arr)


class TestCalculateConfidence:
    def test_empty_text_returns_zero(self, ocr_model):
        mock_ids = MagicMock()
        result = ocr_model._calculate_confidence(mock_ids, "")
        assert result == 0.0

    def test_whitespace_text_returns_zero(self, ocr_model):
        mock_ids = MagicMock()
        result = ocr_model._calculate_confidence(mock_ids, "   ")
        assert result == 0.0

    def test_short_text_returns_lower_confidence(self, ocr_model):
        mock_ids = MagicMock()
        result = ocr_model._calculate_confidence(mock_ids, "ab")
        assert result == 0.5

    def test_normal_text_returns_base_confidence(self, ocr_model):
        mock_ids = MagicMock()
        result = ocr_model._calculate_confidence(mock_ids, "hello world test")
        assert result >= 0.85

    def test_math_symbols_boost_confidence(self, ocr_model):
        mock_ids = MagicMock()
        base = ocr_model._calculate_confidence(mock_ids, "hello world test")
        math = ocr_model._calculate_confidence(mock_ids, "2x + 3 = 7")
        assert math >= base

    def test_confidence_never_exceeds_one(self, ocr_model):
        mock_ids = MagicMock()
        result = ocr_model._calculate_confidence(mock_ids, "x + y = z + a + b = c * d / e ^ f")
        assert result <= 1.0


class TestSetConfidenceThreshold:
    def test_set_valid_threshold(self, ocr_model):
        ocr_model.set_confidence_threshold(0.7)
        assert ocr_model.confidence_threshold == 0.7

    def test_set_zero_threshold(self, ocr_model):
        ocr_model.set_confidence_threshold(0.0)
        assert ocr_model.confidence_threshold == 0.0

    def test_set_one_threshold(self, ocr_model):
        ocr_model.set_confidence_threshold(1.0)
        assert ocr_model.confidence_threshold == 1.0

    def test_threshold_above_one_raises_value_error(self, ocr_model):
        with pytest.raises(ValueError):
            ocr_model.set_confidence_threshold(1.1)

    def test_threshold_below_zero_raises_value_error(self, ocr_model):
        with pytest.raises(ValueError):
            ocr_model.set_confidence_threshold(-0.1)


class TestValidateResult:
    def test_result_above_threshold_passes(self, ocr_model):
        from src.models.base import OCRResult
        result = OCRResult(True, "x=3", 0.9, 0.1, {})
        assert ocr_model.validate_result(result) is True

    def test_result_below_threshold_fails(self, ocr_model):
        from src.models.base import OCRResult
        result = OCRResult(True, "x=3", 0.5, 0.1, {})
        assert ocr_model.validate_result(result) is False

    def test_unsuccessful_result_fails(self, ocr_model):
        from src.models.base import OCRResult
        result = OCRResult(False, "", 0.95, 0.1, {})
        assert ocr_model.validate_result(result) is False


class TestGetModelInfo:
    def test_unloaded_model_info_has_is_loaded_false(self, ocr_model):
        info = ocr_model.get_model_info()
        assert info["is_loaded"] is False
        assert info["model_name"] == "test/model"

    def test_model_info_contains_required_fields(self, ocr_model):
        info = ocr_model.get_model_info()
        assert "model_name" in info
        assert "device" in info
        assert "is_loaded" in info
        assert "confidence_threshold" in info


# ──────────────────────────────────────────────────────────────
# MathematicalOCRModel tests
# ──────────────────────────────────────────────────────────────

class TestMathematicalOCRModel:
    def test_apply_math_corrections_times_symbol(self, math_ocr_model):
        result = math_ocr_model._apply_math_corrections("3 × 4")
        assert "×" not in result
        assert "*" in result

    def test_apply_math_corrections_division_symbol(self, math_ocr_model):
        result = math_ocr_model._apply_math_corrections("8 ÷ 2")
        assert "÷" not in result
        assert "/" in result

    def test_apply_math_corrections_pi(self, math_ocr_model):
        result = math_ocr_model._apply_math_corrections("π r²")
        assert "π" not in result
        assert "pi" in result

    def test_apply_math_corrections_sqrt(self, math_ocr_model):
        result = math_ocr_model._apply_math_corrections("√16 = 4")
        assert "√" not in result
        assert "sqrt" in result

    def test_apply_math_corrections_no_change_needed(self, math_ocr_model):
        text = "2x + 3 = 7"
        result = math_ocr_model._apply_math_corrections(text)
        assert result == text

    def test_apply_math_corrections_minus_sign(self, math_ocr_model):
        result = math_ocr_model._apply_math_corrections("5 − 3")
        assert "−" not in result
        assert "-" in result

    def test_math_symbol_corrections_dict_not_empty(self, math_ocr_model):
        assert len(math_ocr_model.math_symbol_corrections) > 0
