"""
Debug endpoints — only mounted when ENABLE_DEBUG_ENDPOINTS=true.

These routes expose internal service state and must NEVER be enabled in production.
"""
import sys
import platform
from fastapi import APIRouter, Request
from loguru import logger

from ...config.settings import get_settings

router = APIRouter()


@router.get("/", summary="Debug overview")
async def debug_overview(request: Request):
    """Return a summary of runtime and service state for debugging."""
    settings = get_settings()
    registry = request.app.state.model_manager.get_registry()

    return {
        "warning": "Debug endpoints are enabled — disable in production (ENABLE_DEBUG_ENDPOINTS=false)",
        "python": {
            "version": sys.version,
            "platform": platform.platform(),
        },
        "settings": {
            "environment": settings.logging.environment,
            "log_level": settings.logging.level,
            "ml_device": settings.ml.device,
            "ocr_model": settings.ml.ocr_model_name,
            "llm_model": settings.ml.llm_model_name,
        },
        "registry": registry.get_registry_status(),
    }


@router.get("/registry", summary="Model registry raw status")
async def debug_registry(request: Request):
    """Return raw model registry status."""
    registry = request.app.state.model_manager.get_registry()
    return {"registry_status": registry.get_registry_status()}


@router.post("/reload-model/{model_name}", summary="Force-reload a registered model")
async def debug_reload_model(model_name: str, request: Request):
    """Unload and reload a specific model by name."""
    registry = request.app.state.model_manager.get_registry()
    model = registry.get_model(model_name)

    if model is None:
        return {"success": False, "detail": f"Model '{model_name}' not found in registry"}

    logger.warning(f"[DEBUG] Force-reloading model: {model_name}")
    registry.unload_model(model_name)
    model.load_model()

    return {"success": True, "model": model_name, "info": model.get_model_info()}
