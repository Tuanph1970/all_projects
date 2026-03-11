"""
Backward-compatibility shim.

All types have moved to their canonical locations:
  - Domain value objects  → src/domain/shared/value_objects.py
  - BaseMLModel / ModelRegistry → src/infrastructure/ml/base.py

This module re-exports everything so existing imports continue to work
during the migration period.  New code should import from the canonical
locations directly.
"""
# Domain value objects
from ..domain.shared.value_objects import (  # noqa: F401
    LLMResult,
    MLTask,
    ModelType,
    OCRResult,
    ProcessingResult,
    SolutionResult,
    SolutionStep,
    TaskStatus,
)

# Infrastructure base classes
from ..infrastructure.ml.base import BaseMLModel, ModelRegistry  # noqa: F401


# ---------------------------------------------------------------------------
# Deprecated helpers — kept only for backward compatibility.
# Use FastAPI DI (src/api/dependencies.py) in new code instead.
# ---------------------------------------------------------------------------
_REGISTRY_SINGLETON: ModelRegistry = ModelRegistry()


def get_model_registry() -> ModelRegistry:
    """
    DEPRECATED: returns the module-level singleton.

    New code should use the FastAPI dependency get_model_registry()
    from src/api/dependencies.py, which returns the registry stored
    in app.state (created by ModelManager at startup).
    """
    return _REGISTRY_SINGLETON
