"""
Model management router for the Mathematics LLM OCR Service.
"""
import time as _time

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Dict, List, Any, Optional
from loguru import logger

from ...config.settings import get_settings, Settings

router = APIRouter()


class ModelInfo(BaseModel):
    name: str
    model_type: str
    is_loaded: bool
    load_time_seconds: Optional[float] = None
    device: str
    metadata: Dict[str, Any] = {}


class ModelsResponse(BaseModel):
    models: List[ModelInfo]
    total_count: int
    loaded_count: int


class LoadModelRequest(BaseModel):
    model_name: str
    force_reload: bool = False


@router.get("/", response_model=ModelsResponse)
async def list_models(request: Request):
    """List all available models with their status."""
    model_registry = request.app.state.model_manager.get_registry()
    models = []
    loaded_count = 0

    for model_name in model_registry.list_models():
        try:
            model = model_registry.get_model(model_name)
            model_info_dict = model.get_model_info()

            model_info = ModelInfo(
                name=model_name,
                model_type=model_info_dict.get('model_type', 'Unknown'),
                is_loaded=model.is_model_loaded(),
                load_time_seconds=model_info_dict.get('load_time_seconds'),
                device=model_info_dict.get('device', 'Unknown'),
                metadata=model_info_dict
            )

            models.append(model_info)
            if model.is_model_loaded():
                loaded_count += 1

        except Exception as e:
            logger.error(f"Failed to get info for model {model_name}: {e}")
            # Add basic info even if detailed info fails
            models.append(ModelInfo(
                name=model_name,
                model_type="Unknown",
                is_loaded=False,
                device="Unknown",
                metadata={"error": str(e)}
            ))

    return ModelsResponse(
        models=models,
        total_count=len(models),
        loaded_count=loaded_count
    )


@router.get("/{model_name}", response_model=ModelInfo)
async def get_model_info(model_name: str, request: Request):
    """Get detailed information about a specific model."""
    model_registry = request.app.state.model_manager.get_registry()

    if model_name not in model_registry.list_models():
        raise HTTPException(status_code=404, detail=f"Model '{model_name}' not found")

    try:
        model = model_registry.get_model(model_name)
        model_info_dict = model.get_model_info()

        return ModelInfo(
            name=model_name,
            model_type=model_info_dict.get('model_type', 'Unknown'),
            is_loaded=model.is_model_loaded(),
            load_time_seconds=model_info_dict.get('load_time_seconds'),
            device=model_info_dict.get('device', 'Unknown'),
            metadata=model_info_dict
        )
    except Exception as e:
        logger.error(f"Failed to get info for model {model_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get model info: {str(e)}")


@router.post("/{model_name}/load")
async def load_model(model_name: str, request: Request, load_request: LoadModelRequest):
    """Load a specific model."""
    model_registry = request.app.state.model_manager.get_registry()

    if model_name not in model_registry.list_models():
        raise HTTPException(status_code=404, detail=f"Model '{model_name}' not found")

    try:
        model = model_registry.get_model(model_name)

        if model.is_model_loaded() and not load_request.force_reload:
            return {"message": f"Model '{model_name}' is already loaded", "status": "already_loaded"}

        if load_request.force_reload and model.is_model_loaded():
            logger.info(f"Reloading model: {model_name}")
            model.unload_model()

        logger.info(f"Loading model: {model_name}")
        model.load_model()

        return {"message": f"Model '{model_name}' loaded successfully", "status": "loaded"}

    except Exception as e:
        logger.error(f"Failed to load model {model_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to load model: {str(e)}")


@router.post("/{model_name}/unload")
async def unload_model(model_name: str, request: Request):
    """Unload a specific model."""
    model_registry = request.app.state.model_manager.get_registry()

    if model_name not in model_registry.list_models():
        raise HTTPException(status_code=404, detail=f"Model '{model_name}' not found")

    try:
        model = model_registry.get_model(model_name)

        if not model.is_model_loaded():
            return {"message": f"Model '{model_name}' is not loaded", "status": "not_loaded"}

        logger.info(f"Unloading model: {model_name}")
        model.unload_model()

        return {"message": f"Model '{model_name}' unloaded successfully", "status": "unloaded"}

    except Exception as e:
        logger.error(f"Failed to unload model {model_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to unload model: {str(e)}")


@router.post("/{model_name}/warmup", summary="Warm up a model")
async def warmup_model(model_name: str, request: Request):
    """
    Load a model (if not already loaded) and run a lightweight dummy pass
    to eliminate cold-start latency on the first real inference request.

    Returns the time spent loading/warming up, and whether the model was
    already loaded before this call.
    """
    model_registry = request.app.state.model_manager.get_registry()

    if model_name not in model_registry.list_models():
        raise HTTPException(status_code=404, detail=f"Model '{model_name}' not found")

    try:
        model = model_registry.get_model(model_name)
        was_loaded = model.is_model_loaded()
        start = _time.time()

        if not was_loaded:
            logger.info(f"Warmup: loading model '{model_name}'")
            model.load_model()

        # If the model exposes a warmup() method, call it.
        # This allows models to run a dummy forward-pass internally.
        if hasattr(model, "warmup") and callable(model.warmup):
            logger.info(f"Warmup: running dummy inference for '{model_name}'")
            model.warmup()

        warmup_time = _time.time() - start
        logger.info(
            f"Model '{model_name}' warm-up complete in {warmup_time:.3f}s",
            model_name=model_name,
            was_loaded=was_loaded,
            warmup_time=warmup_time,
        )
        return {
            "model_name": model_name,
            "status": "warmed_up",
            "was_already_loaded": was_loaded,
            "warmup_time_seconds": round(warmup_time, 3),
        }

    except Exception as e:
        logger.error(
            f"Warmup failed for model '{model_name}': {e}",
            model_name=model_name,
        )
        raise HTTPException(status_code=500, detail=f"Model warm-up failed: {str(e)}")


@router.get("/registry/status")
async def get_registry_status(request: Request):
    """Get overall model registry status."""
    model_registry = request.app.state.model_manager.get_registry()

    try:
        status = model_registry.get_registry_status()
        total_models = len(model_registry.list_models())
        loaded_models = len([m for m in model_registry.list_models()
                           if model_registry.get_model(m).is_model_loaded()])

        return {
            "registry_status": status,
            "total_models": total_models,
            "loaded_models": loaded_models,
            "unloaded_models": total_models - loaded_models,
            "load_percentage": (loaded_models / total_models * 100) if total_models > 0 else 0
        }
    except Exception as e:
        logger.error(f"Failed to get registry status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get registry status: {str(e)}")
