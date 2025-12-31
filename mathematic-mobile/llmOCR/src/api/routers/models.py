"""
Model management router for the Mathematics LLM OCR Service.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Any, Optional
from loguru import logger

from ...models.base import get_model_registry
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
async def list_models():
    """List all available models with their status."""
    model_registry = get_model_registry()
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
async def get_model_info(model_name: str):
    """Get detailed information about a specific model."""
    model_registry = get_model_registry()
    
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
async def load_model(model_name: str, request: LoadModelRequest):
    """Load a specific model."""
    model_registry = get_model_registry()
    
    if model_name not in model_registry.list_models():
        raise HTTPException(status_code=404, detail=f"Model '{model_name}' not found")
    
    try:
        model = model_registry.get_model(model_name)
        
        if model.is_model_loaded() and not request.force_reload:
            return {"message": f"Model '{model_name}' is already loaded", "status": "already_loaded"}
        
        if request.force_reload and model.is_model_loaded():
            logger.info(f"Reloading model: {model_name}")
            model.unload_model()
        
        logger.info(f"Loading model: {model_name}")
        model.load_model()
        
        return {"message": f"Model '{model_name}' loaded successfully", "status": "loaded"}
        
    except Exception as e:
        logger.error(f"Failed to load model {model_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to load model: {str(e)}")


@router.post("/{model_name}/unload")
async def unload_model(model_name: str):
    """Unload a specific model."""
    model_registry = get_model_registry()
    
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


@router.get("/registry/status")
async def get_registry_status():
    """Get overall model registry status."""
    model_registry = get_model_registry()
    
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