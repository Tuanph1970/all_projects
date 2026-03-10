"""
Unit tests for ImagePreprocessor.
CV2 operations are mocked to avoid requiring a display environment.
"""
import pytest
import numpy as np
from PIL import Image
from unittest.mock import MagicMock, patch


# ──────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────

@pytest.fixture
def preprocessor():
    from src.utils.image_processing import ImagePreprocessor
    return ImagePreprocessor(target_width=512, target_height=512, dpi=300)


@pytest.fixture
def rgb_image():
    return Image.new("RGB", (100, 100), color=(200, 200, 200))


@pytest.fixture
def grayscale_image():
    return Image.new("L", (100, 100), color=128)


@pytest.fixture
def rgba_image():
    return Image.new("RGBA", (100, 100), color=(200, 200, 200, 255))


@pytest.fixture
def large_rgb_image():
    return Image.new("RGB", (3000, 2000), color=(255, 255, 255))


# ──────────────────────────────────────────────────────────────
# _load_image
# ──────────────────────────────────────────────────────────────

class TestLoadImage:
    def test_load_pil_rgb_returns_same(self, preprocessor, rgb_image):
        result = preprocessor._load_image(rgb_image)
        assert isinstance(result, Image.Image)
        assert result.mode == "RGB"

    def test_load_pil_grayscale_returns_l_mode(self, preprocessor, grayscale_image):
        result = preprocessor._load_image(grayscale_image)
        assert isinstance(result, Image.Image)
        assert result.mode == "L"

    def test_load_rgba_converts_to_rgb(self, preprocessor, rgba_image):
        result = preprocessor._load_image(rgba_image)
        assert result.mode == "RGB"

    def test_load_numpy_rgb_converts_to_pil(self, preprocessor):
        arr = np.ones((50, 50, 3), dtype=np.uint8) * 128
        result = preprocessor._load_image(arr)
        assert isinstance(result, Image.Image)
        assert result.mode == "RGB"

    def test_load_numpy_grayscale_converts_to_pil(self, preprocessor):
        arr = np.ones((50, 50), dtype=np.uint8) * 64
        result = preprocessor._load_image(arr)
        assert isinstance(result, Image.Image)
        assert result.mode == "L"

    def test_load_invalid_type_raises_type_error(self, preprocessor):
        with pytest.raises(TypeError):
            preprocessor._load_image(12345)

    def test_load_invalid_numpy_shape_raises_value_error(self, preprocessor):
        arr = np.ones((10, 10, 4), dtype=np.uint8)
        with pytest.raises((ValueError, Exception)):
            preprocessor._load_image(arr)

    def test_load_from_path_returns_pil(self, preprocessor, tmp_path, rgb_image):
        img_path = str(tmp_path / "test.png")
        rgb_image.save(img_path)
        result = preprocessor._load_image(img_path)
        assert isinstance(result, Image.Image)

    def test_load_invalid_path_raises_error(self, preprocessor):
        with pytest.raises(Exception):
            preprocessor._load_image("/nonexistent/path/image.png")


# ──────────────────────────────────────────────────────────────
# _resize_if_needed
# ──────────────────────────────────────────────────────────────

class TestResizeIfNeeded:
    def test_small_image_not_resized(self, preprocessor, rgb_image):
        result = preprocessor._resize_if_needed(rgb_image)
        assert result.size == rgb_image.size

    def test_large_image_is_resized(self, preprocessor, large_rgb_image):
        result = preprocessor._resize_if_needed(large_rgb_image)
        assert result.size[0] <= preprocessor.target_width
        assert result.size[1] <= preprocessor.target_height

    def test_aspect_ratio_preserved_landscape(self, preprocessor):
        wide_image = Image.new("RGB", (2000, 1000))
        result = preprocessor._resize_if_needed(wide_image)
        original_ratio = 2000 / 1000
        result_ratio = result.size[0] / result.size[1]
        assert abs(original_ratio - result_ratio) < 0.01

    def test_aspect_ratio_preserved_portrait(self, preprocessor):
        tall_image = Image.new("RGB", (1000, 2000))
        result = preprocessor._resize_if_needed(tall_image)
        original_ratio = 1000 / 2000
        result_ratio = result.size[0] / result.size[1]
        assert abs(original_ratio - result_ratio) < 0.01


# ──────────────────────────────────────────────────────────────
# _convert_to_grayscale
# ──────────────────────────────────────────────────────────────

class TestConvertToGrayscale:
    def test_rgb_converts_to_l(self, preprocessor, rgb_image):
        result = preprocessor._convert_to_grayscale(rgb_image)
        assert result.mode == "L"

    def test_already_grayscale_unchanged(self, preprocessor, grayscale_image):
        result = preprocessor._convert_to_grayscale(grayscale_image)
        assert result.mode == "L"
        assert result is grayscale_image


# ──────────────────────────────────────────────────────────────
# _sharpen
# ──────────────────────────────────────────────────────────────

class TestSharpen:
    def test_sharpen_returns_pil_image(self, preprocessor, grayscale_image):
        result = preprocessor._sharpen(grayscale_image)
        assert isinstance(result, Image.Image)

    def test_sharpen_preserves_mode(self, preprocessor, grayscale_image):
        result = preprocessor._sharpen(grayscale_image)
        assert result.mode == "L"

    def test_sharpen_preserves_size(self, preprocessor, grayscale_image):
        result = preprocessor._sharpen(grayscale_image)
        assert result.size == grayscale_image.size


# ──────────────────────────────────────────────────────────────
# _apply_gamma_correction
# ──────────────────────────────────────────────────────────────

class TestApplyGammaCorrection:
    def test_gamma_1_preserves_image(self, preprocessor, grayscale_image):
        result = preprocessor._apply_gamma_correction(grayscale_image, gamma=1.0)
        assert isinstance(result, Image.Image)
        arr_orig = np.array(grayscale_image)
        arr_result = np.array(result)
        assert np.allclose(arr_orig, arr_result, atol=1)

    def test_gamma_returns_l_mode(self, preprocessor, grayscale_image):
        result = preprocessor._apply_gamma_correction(grayscale_image, gamma=1.5)
        assert result.mode == "L"

    def test_gamma_greater_than_1_brightens(self, preprocessor):
        mid_gray = Image.fromarray(np.full((10, 10), 128, dtype=np.uint8), "L")
        result = preprocessor._apply_gamma_correction(mid_gray, gamma=2.0)
        arr = np.array(result)
        assert arr.mean() > 128


# ──────────────────────────────────────────────────────────────
# _binarize
# ──────────────────────────────────────────────────────────────

class TestBinarize:
    @pytest.mark.parametrize("method", ["otsu", "adaptive", "simple"])
    def test_binarize_returns_l_mode(self, preprocessor, method):
        gray = Image.fromarray(np.random.randint(0, 255, (50, 50), dtype=np.uint8), "L")
        result = preprocessor._binarize(gray, method=method)
        assert result.mode == "L"

    @pytest.mark.parametrize("method", ["otsu", "adaptive", "simple"])
    def test_binarize_output_is_binary(self, preprocessor, method):
        gray = Image.fromarray(np.random.randint(0, 255, (50, 50), dtype=np.uint8), "L")
        result = preprocessor._binarize(gray, method=method)
        arr = np.array(result)
        unique_values = np.unique(arr)
        assert all(v in [0, 255] for v in unique_values)


# ──────────────────────────────────────────────────────────────
# crop_to_region
# ──────────────────────────────────────────────────────────────

class TestCropToRegion:
    def test_crop_returns_correct_size(self, preprocessor, rgb_image):
        region = (10, 10, 50, 50)
        result = preprocessor.crop_to_region(rgb_image, region)
        assert result.size == (50, 50)

    def test_crop_returns_pil_image(self, preprocessor, rgb_image):
        result = preprocessor.crop_to_region(rgb_image, (0, 0, 50, 50))
        assert isinstance(result, Image.Image)


# ──────────────────────────────────────────────────────────────
# get_image_statistics
# ──────────────────────────────────────────────────────────────

class TestGetImageStatistics:
    def test_stats_has_required_fields(self, preprocessor, rgb_image):
        stats = preprocessor.get_image_statistics(rgb_image)
        required = ["width", "height", "mode", "mean_brightness", "std_brightness",
                    "min_brightness", "max_brightness", "histogram"]
        for field in required:
            assert field in stats

    def test_stats_width_height_correct(self, preprocessor, rgb_image):
        stats = preprocessor.get_image_statistics(rgb_image)
        assert stats["width"] == 100
        assert stats["height"] == 100

    def test_stats_brightness_in_range(self, preprocessor, rgb_image):
        stats = preprocessor.get_image_statistics(rgb_image)
        assert 0 <= stats["min_brightness"] <= 255
        assert 0 <= stats["max_brightness"] <= 255
        assert stats["min_brightness"] <= stats["max_brightness"]

    def test_stats_histogram_has_256_bins(self, preprocessor, rgb_image):
        stats = preprocessor.get_image_statistics(rgb_image)
        assert len(stats["histogram"]) == 256


# ──────────────────────────────────────────────────────────────
# ImagePreprocessor initialization
# ──────────────────────────────────────────────────────────────

class TestImagePreprocessorInit:
    def test_default_values(self):
        from src.utils.image_processing import ImagePreprocessor
        pp = ImagePreprocessor()
        assert pp.target_width == 2048
        assert pp.target_height == 2048
        assert pp.dpi == 300

    def test_custom_values(self):
        from src.utils.image_processing import ImagePreprocessor
        pp = ImagePreprocessor(target_width=800, target_height=600, dpi=150)
        assert pp.target_width == 800
        assert pp.target_height == 600
        assert pp.dpi == 150
