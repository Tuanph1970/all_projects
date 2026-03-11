"""
Model manager service responsible for initialising and managing ML model lifecycle.
"""
from loguru import logger

from ..config.settings import Settings
from ..infrastructure.ml.base import ModelRegistry
from ..models.ocr_model import OCRModel, MathematicalOCRModel
from ..models.solution_model import SolutionModel


class ModelManager:
    """
    Orchestrates startup loading and graceful shutdown of all ML models.

    Used exclusively by the FastAPI lifespan context manager in api/main.py.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._registry = ModelRegistry()

    async def initialize_default_models(self) -> None:
        """Register and load the default OCR and solution models."""
        ml = self._settings.ml

        # --- OCR models ---
        default_ocr = OCRModel(
            model_name=ml.ocr_model_name,
            device=ml.device,
            confidence_threshold=ml.ocr_confidence_threshold,
        )
        self._registry.register_model(
            "default_ocr",
            default_ocr,
            config={"model_name": ml.ocr_model_name, "type": "ocr"},
        )
        logger.info(f"Registered default_ocr model: {ml.ocr_model_name}")

        mathematical_ocr = MathematicalOCRModel(
            model_name=ml.ocr_model_name,
            device=ml.device,
            confidence_threshold=ml.ocr_confidence_threshold,
        )
        self._registry.register_model(
            "mathematical_ocr",
            mathematical_ocr,
            config={"model_name": ml.ocr_model_name, "type": "mathematical_ocr"},
        )
        logger.info(f"Registered mathematical_ocr model: {ml.ocr_model_name}")

        # --- Solution model ---
        solution_model = SolutionModel(
            model_name=ml.llm_model_name,
            device=ml.device,
        )
        self._registry.register_model(
            "default_solution",
            solution_model,
            config={"model_name": ml.llm_model_name, "type": "solution"},
        )
        logger.info(f"Registered default_solution model: {ml.llm_model_name}")

        logger.info(
            f"Model manager initialised — "
            f"{len(self._registry.list_models())} models registered "
            f"(models are loaded on first request)"
        )

    def get_registry(self):
        """Return the underlying model registry."""
        return self._registry
