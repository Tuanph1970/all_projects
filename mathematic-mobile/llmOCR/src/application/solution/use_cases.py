"""
Solution application use cases.

SolveProblemUseCase: text problem → SolutionResult
BatchSolveProblemUseCase: list of problems → List[SolutionResult]
OCRAndSolveUseCase: image → OCRResult + SolutionResult
"""
from typing import Any, Dict, List

from loguru import logger
from PIL import Image

from ...infrastructure.ml.base import ModelRegistry
from ...domain.shared.value_objects import OCRResult, SolutionResult
from ...domain.shared.exceptions import ModelUnavailableError
from ..ocr.use_cases import ExtractTextUseCase


class SolveProblemUseCase:
    """Solve a text mathematical problem using the solution model."""

    def __init__(self, registry: ModelRegistry) -> None:
        self._registry = registry

    def execute(
        self,
        problem: str,
        context: Dict[str, Any] = None,
        confidence_threshold: float = 0.7,
    ) -> SolutionResult:
        model = self._resolve_solution_model()
        self._ensure_loaded(model)

        if hasattr(model, "set_confidence_threshold"):
            model.set_confidence_threshold(confidence_threshold)

        input_data = {"problem": problem, "context": context or {}}
        result: SolutionResult = model.predict(input_data)
        result.metadata.update({"input_type": "text_problem"})
        return result

    def _resolve_solution_model(self):
        name = "default_solution"
        model = self._registry.get_model(name)
        if model is None:
            raise ModelUnavailableError(name)
        return model

    @staticmethod
    def _ensure_loaded(model) -> None:
        if not model.is_model_loaded():
            logger.info(f"Lazy-loading solution model: {model.model_name}")
            model.load_model()


class OCRAndSolveUseCase:
    """Full pipeline: image → OCR text → mathematical solution."""

    def __init__(self, registry: ModelRegistry) -> None:
        self._registry = registry
        self._ocr_use_case = ExtractTextUseCase(registry)
        self._solve_use_case = SolveProblemUseCase(registry)

    def execute(
        self,
        image: Image.Image,
        ocr_confidence_threshold: float = 0.8,
        solution_confidence_threshold: float = 0.7,
        use_mathematical_ocr: bool = True,
    ) -> Dict[str, Any]:
        """
        Returns a dict with both 'ocr_result' and 'solution_result' keys
        so the caller can access both.
        """
        ocr_result: OCRResult = self._ocr_use_case.execute(
            image,
            confidence_threshold=ocr_confidence_threshold,
            use_mathematical_model=use_mathematical_ocr,
            source_metadata={"pipeline": "ocr_and_solve"},
        )

        if not ocr_result.success or not ocr_result.extracted_text.strip():
            return {"ocr_result": ocr_result, "solution_result": None}

        solution_result: SolutionResult = self._solve_use_case.execute(
            problem=ocr_result.extracted_text,
            context={
                "source": "ocr",
                "ocr_confidence": ocr_result.confidence,
                "ocr_metadata": ocr_result.metadata,
            },
            confidence_threshold=solution_confidence_threshold,
        )

        return {"ocr_result": ocr_result, "solution_result": solution_result}


class BatchSolveProblemUseCase:
    """Solve a list of text problems, collecting per-problem results."""

    def __init__(self, registry: ModelRegistry) -> None:
        self._single = SolveProblemUseCase(registry)

    def execute(
        self,
        problems: List[str],
        confidence_threshold: float = 0.7,
    ) -> List[SolutionResult]:
        results: List[SolutionResult] = []
        for idx, problem in enumerate(problems):
            try:
                result = self._single.execute(
                    problem=problem,
                    context={"batch_index": idx},
                    confidence_threshold=confidence_threshold,
                )
            except Exception as exc:
                logger.error(f"Batch solve failed for problem {idx}: {exc}")
                result = SolutionResult(
                    success=False,
                    problem_type="unknown",
                    solution="",
                    steps=[],
                    final_answer="",
                    confidence=0.0,
                    processing_time=0.0,
                    metadata={"error": str(exc), "batch_index": idx},
                )
            results.append(result)
        return results
