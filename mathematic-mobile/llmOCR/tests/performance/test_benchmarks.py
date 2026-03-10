"""
Performance benchmark tests for OCR service.
These tests measure execution time for key operations.
"""
import time
import pytest
import numpy as np
from PIL import Image
from unittest.mock import MagicMock, patch


# ──────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────

THRESHOLD_MS = 500   # 500 ms threshold for preprocessing operations
PARSER_THRESHOLD_MS = 50   # 50 ms for parser operations


@pytest.fixture(autouse=True)
def mock_transformers():
    mock_processor = MagicMock()
    mock_model = MagicMock()
    mock_model.generate.return_value = MagicMock()

    with (
        patch("src.models.ocr_model.TrOCRProcessor.from_pretrained", return_value=mock_processor),
        patch("src.models.ocr_model.VisionEncoderDecoderModel.from_pretrained", return_value=mock_model),
    ):
        yield


@pytest.fixture
def preprocessor():
    from src.utils.image_processing import ImagePreprocessor
    return ImagePreprocessor()


@pytest.fixture
def parser():
    from src.utils.math_parser import MathExpressionParser
    return MathExpressionParser()


@pytest.fixture
def test_image_small():
    return Image.new("RGB", (100, 100), color=(200, 200, 200))


@pytest.fixture
def test_image_medium():
    return Image.new("RGB", (800, 600), color=(200, 200, 200))


@pytest.fixture
def test_image_large():
    return Image.new("RGB", (2000, 1500), color=(200, 200, 200))


# ──────────────────────────────────────────────────────────────
# Image preprocessing benchmarks
# ──────────────────────────────────────────────────────────────

class TestImagePreprocessingBenchmarks:
    def test_load_image_performance(self, preprocessor, test_image_small):
        start = time.time()
        preprocessor._load_image(test_image_small)
        elapsed_ms = (time.time() - start) * 1000
        assert elapsed_ms < THRESHOLD_MS, f"_load_image took {elapsed_ms:.1f}ms (limit: {THRESHOLD_MS}ms)"

    def test_convert_to_grayscale_performance(self, preprocessor, test_image_medium):
        start = time.time()
        preprocessor._convert_to_grayscale(test_image_medium)
        elapsed_ms = (time.time() - start) * 1000
        assert elapsed_ms < THRESHOLD_MS

    def test_resize_large_image_performance(self, preprocessor, test_image_large):
        start = time.time()
        preprocessor._resize_if_needed(test_image_large)
        elapsed_ms = (time.time() - start) * 1000
        assert elapsed_ms < THRESHOLD_MS

    def test_sharpen_performance(self, preprocessor):
        gray = Image.new("L", (500, 500), 128)
        start = time.time()
        preprocessor._sharpen(gray)
        elapsed_ms = (time.time() - start) * 1000
        assert elapsed_ms < THRESHOLD_MS

    def test_binarize_performance(self, preprocessor):
        gray_arr = np.random.randint(0, 255, (500, 500), dtype=np.uint8)
        gray = Image.fromarray(gray_arr, "L")
        start = time.time()
        preprocessor._binarize(gray)
        elapsed_ms = (time.time() - start) * 1000
        assert elapsed_ms < THRESHOLD_MS

    def test_get_image_statistics_performance(self, preprocessor, test_image_medium):
        start = time.time()
        preprocessor.get_image_statistics(test_image_medium)
        elapsed_ms = (time.time() - start) * 1000
        assert elapsed_ms < THRESHOLD_MS

    def test_gamma_correction_performance(self, preprocessor):
        gray = Image.new("L", (500, 500), 128)
        start = time.time()
        preprocessor._apply_gamma_correction(gray, gamma=1.5)
        elapsed_ms = (time.time() - start) * 1000
        assert elapsed_ms < THRESHOLD_MS


# ──────────────────────────────────────────────────────────────
# Math parser benchmarks
# ──────────────────────────────────────────────────────────────

class TestMathParserBenchmarks:
    def test_simple_addition_performance(self, parser):
        start = time.time()
        for _ in range(100):
            parser.evaluate_expression("2 + 3")
        elapsed_ms = (time.time() - start) * 1000
        avg_ms = elapsed_ms / 100
        assert avg_ms < PARSER_THRESHOLD_MS

    def test_complex_expression_performance(self, parser):
        expr = "((2 + 3) * 4 - 1) / 2"
        start = time.time()
        for _ in range(100):
            parser.evaluate_expression(expr)
        elapsed_ms = (time.time() - start) * 1000
        avg_ms = elapsed_ms / 100
        assert avg_ms < PARSER_THRESHOLD_MS

    def test_validate_expression_performance(self, parser):
        start = time.time()
        for _ in range(100):
            parser.validate_expression("2 + 3 * 4")
        elapsed_ms = (time.time() - start) * 1000
        avg_ms = elapsed_ms / 100
        assert avg_ms < PARSER_THRESHOLD_MS

    def test_extract_numbers_performance(self, parser):
        text = "John has 3 apples, Mary has 5 oranges, and Bob has 12 bananas"
        start = time.time()
        for _ in range(100):
            parser._extract_numbers(text)
        elapsed_ms = (time.time() - start) * 1000
        avg_ms = elapsed_ms / 100
        assert avg_ms < PARSER_THRESHOLD_MS

    def test_parse_word_problem_performance(self, parser):
        problem = "If John has 15 apples and gives 7 to Mary, how many does he have left?"
        start = time.time()
        for _ in range(50):
            parser.parse_word_problem(problem)
        elapsed_ms = (time.time() - start) * 1000
        avg_ms = elapsed_ms / 50
        assert avg_ms < PARSER_THRESHOLD_MS * 2


# ──────────────────────────────────────────────────────────────
# OCR model benchmarks (mocked)
# ──────────────────────────────────────────────────────────────

class TestOCRModelBenchmarks:
    def test_model_initialization_performance(self):
        from src.models.ocr_model import OCRModel
        start = time.time()
        for _ in range(10):
            OCRModel(model_name="test/model", device="cpu")
        elapsed_ms = (time.time() - start) * 1000
        avg_ms = elapsed_ms / 10
        assert avg_ms < 100  # Should init in < 100ms

    def test_prepare_image_performance(self):
        from src.models.ocr_model import OCRModel
        model = OCRModel(model_name="test/model", device="cpu")
        img = Image.new("RGB", (100, 100), color=(255, 255, 255))

        start = time.time()
        for _ in range(100):
            model._prepare_image(img)
        elapsed_ms = (time.time() - start) * 1000
        avg_ms = elapsed_ms / 100
        assert avg_ms < 10  # Image prep should be < 10ms per call

    def test_confidence_calculation_performance(self):
        from src.models.ocr_model import OCRModel
        from unittest.mock import MagicMock
        model = OCRModel(model_name="test/model", device="cpu")
        mock_ids = MagicMock()
        texts = ["2x + 3 = 7", "hello world", "x^2 + y^2 = r^2"]

        start = time.time()
        for _ in range(100):
            for text in texts:
                model._calculate_confidence(mock_ids, text)
        elapsed_ms = (time.time() - start) * 1000
        avg_ms = elapsed_ms / (100 * len(texts))
        assert avg_ms < 10
