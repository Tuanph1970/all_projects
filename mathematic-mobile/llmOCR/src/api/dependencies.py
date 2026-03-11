"""
FastAPI dependency providers.

All dependencies are resolved from app.state (set during lifespan startup)
so there are no module-level singletons anywhere in the application.

Usage in routers:
    from ..dependencies import get_extract_text_use_case
    ...
    async def my_endpoint(use_case = Depends(get_extract_text_use_case)):
        ...
"""
from fastapi import Depends, Request

from ..infrastructure.ml.base import ModelRegistry
from ..application.ocr.use_cases import BatchExtractTextUseCase, ExtractTextUseCase
from ..application.solution.use_cases import OCRAndSolveUseCase, SolveProblemUseCase


def get_model_registry(request: Request) -> ModelRegistry:
    """Return the ModelRegistry stored in app.state by ModelManager."""
    return request.app.state.model_manager.get_registry()


def get_extract_text_use_case(
    registry: ModelRegistry = Depends(get_model_registry),
) -> ExtractTextUseCase:
    return ExtractTextUseCase(registry=registry)


def get_batch_extract_text_use_case(
    registry: ModelRegistry = Depends(get_model_registry),
) -> BatchExtractTextUseCase:
    return BatchExtractTextUseCase(registry=registry)


def get_solve_problem_use_case(
    registry: ModelRegistry = Depends(get_model_registry),
) -> SolveProblemUseCase:
    return SolveProblemUseCase(registry=registry)


def get_ocr_and_solve_use_case(
    registry: ModelRegistry = Depends(get_model_registry),
) -> OCRAndSolveUseCase:
    return OCRAndSolveUseCase(registry=registry)
