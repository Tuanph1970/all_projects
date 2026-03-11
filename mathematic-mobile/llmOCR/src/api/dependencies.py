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
from ..domain.tasks.repositories import ITaskRepository
from ..application.ocr.use_cases import BatchExtractTextUseCase, ExtractTextUseCase
from ..application.solution.use_cases import (
    BatchSolveProblemUseCase,
    OCRAndSolveUseCase,
    SolveProblemUseCase,
)
from ..application.tasks.use_cases import GetTaskUseCase, ListTasksUseCase


# ── ML model registry ─────────────────────────────────────────────────────────

def get_model_registry(request: Request) -> ModelRegistry:
    """Return the ModelRegistry stored in app.state by ModelManager."""
    return request.app.state.model_manager.get_registry()


# ── OCR use cases ─────────────────────────────────────────────────────────────

def get_extract_text_use_case(
    registry: ModelRegistry = Depends(get_model_registry),
) -> ExtractTextUseCase:
    return ExtractTextUseCase(registry=registry)


def get_batch_extract_text_use_case(
    registry: ModelRegistry = Depends(get_model_registry),
) -> BatchExtractTextUseCase:
    return BatchExtractTextUseCase(registry=registry)


# ── Solution use cases ────────────────────────────────────────────────────────

def get_solve_problem_use_case(
    registry: ModelRegistry = Depends(get_model_registry),
) -> SolveProblemUseCase:
    return SolveProblemUseCase(registry=registry)


def get_batch_solve_problem_use_case(
    registry: ModelRegistry = Depends(get_model_registry),
) -> BatchSolveProblemUseCase:
    return BatchSolveProblemUseCase(registry=registry)


def get_ocr_and_solve_use_case(
    registry: ModelRegistry = Depends(get_model_registry),
) -> OCRAndSolveUseCase:
    return OCRAndSolveUseCase(registry=registry)


# ── Task repository ───────────────────────────────────────────────────────────

def get_task_repository(request: Request) -> ITaskRepository:
    """Return the task store stored in app.state."""
    return request.app.state.task_repository


def get_get_task_use_case(
    repo: ITaskRepository = Depends(get_task_repository),
) -> GetTaskUseCase:
    return GetTaskUseCase(task_repo=repo)


def get_list_tasks_use_case(
    repo: ITaskRepository = Depends(get_task_repository),
) -> ListTasksUseCase:
    return ListTasksUseCase(task_repo=repo)
