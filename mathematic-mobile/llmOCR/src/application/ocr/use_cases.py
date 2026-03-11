"""
OCR application use cases.

These classes orchestrate domain objects and infrastructure repositories.
They contain the business rules that belong between the HTTP layer and
the ML model adapters — rules such as model selection fallback and
metadata assembly.
"""
import io
from typing import Any, Dict, List, Optional

from PIL import Image
from loguru import logger

from ...infrastructure.ml.base import ModelRegistry
from ...domain.shared.value_objects import OCRResult
from ...api.exceptions import ModelNotLoadedException, OCRException


class ExtractTextUseCase:
    """
    Extract text from a single PIL image using the configured OCR model.

    Encapsulates:
    - Model selection with mathematical→default fallback
    - Lazy model loading on first request
    - Confidence threshold configuration
    """

    def __init__(self, registry: ModelRegistry) -> None:
        self._registry = registry

    def execute(
        self,
        image: Image.Image,
        confidence_threshold: float = 0.8,
        use_mathematical_model: bool = True,
        source_metadata: Optional[Dict[str, Any]] = None,
    ) -> OCRResult:
        model = self._resolve_ocr_model(use_mathematical_model)
        self._ensure_loaded(model)

        if hasattr(model, "set_confidence_threshold"):
            model.set_confidence_threshold(confidence_threshold)

        result: OCRResult = model.predict(image)

        if source_metadata:
            result.metadata.update(source_metadata)

        return result

    def _resolve_ocr_model(self, use_mathematical: bool):
        preferred = "mathematical_ocr" if use_mathematical else "default_ocr"
        fallback = "default_ocr"

        if preferred in self._registry.list_models():
            return self._registry.get_model(preferred)
        if fallback in self._registry.list_models():
            logger.warning(f"OCR model '{preferred}' not found, falling back to '{fallback}'")
            return self._registry.get_model(fallback)

        raise ModelNotLoadedException("No OCR model registered")

    @staticmethod
    def _ensure_loaded(model) -> None:
        if not model.is_model_loaded():
            logger.info(f"Lazy-loading OCR model: {model.model_name}")
            model.load_model()


class BatchExtractTextUseCase:
    """Extract text from multiple images, collecting per-image results."""

    def __init__(self, registry: ModelRegistry) -> None:
        self._single = ExtractTextUseCase(registry)

    def execute(
        self,
        images: List[Image.Image],
        confidence_threshold: float = 0.8,
        use_mathematical_model: bool = True,
    ) -> List[OCRResult]:
        results = []
        for idx, image in enumerate(images):
            try:
                result = self._single.execute(
                    image,
                    confidence_threshold=confidence_threshold,
                    use_mathematical_model=use_mathematical_model,
                    source_metadata={"batch_index": idx},
                )
            except Exception as exc:
                logger.error(f"Batch OCR failed for image {idx}: {exc}")
                result = OCRResult(
                    success=False,
                    extracted_text="",
                    confidence=0.0,
                    processing_time=0.0,
                    metadata={"error": str(exc), "batch_index": idx},
                )
            results.append(result)
        return results
