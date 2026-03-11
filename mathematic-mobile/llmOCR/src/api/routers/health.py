"""
Health check router for the Mathematics LLM OCR Service.
"""
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from typing import Dict, Any
import time
import psutil
import os

from ...config.settings import get_settings, Settings

router = APIRouter()


class HealthResponse(BaseModel):
    status: str
    timestamp: float
    uptime_seconds: float
    service_info: Dict[str, Any]
    system_info: Dict[str, Any]
    models_info: Dict[str, Any]


class ReadinessResponse(BaseModel):
    ready: bool
    checks: Dict[str, Any]


_start_time = time.time()


@router.get("/", response_model=HealthResponse)
@router.get("/health", response_model=HealthResponse)
async def health_check(request: Request, settings: Settings = Depends(get_settings)):
    """Health check endpoint providing service status and metrics."""
    current_time = time.time()
    uptime = current_time - _start_time

    # Get model registry status
    model_registry = request.app.state.model_manager.get_registry()
    models_status = model_registry.get_registry_status()
    
    # Get system information
    process = psutil.Process(os.getpid())
    memory_info = process.memory_info()
    
    return HealthResponse(
        status="healthy",
        timestamp=current_time,
        uptime_seconds=uptime,
        service_info={
            "name": settings.app_name,
            "version": settings.version,
            "environment": settings.logging.environment,
            "debug_mode": settings.enable_debug_endpoints,
        },
        system_info={
            "cpu_usage_percent": psutil.cpu_percent(),
            "memory_usage_mb": memory_info.rss / 1024 / 1024,
            "memory_percent": process.memory_percent(),
            "disk_usage_percent": psutil.disk_usage('/').percent if os.path.exists('/') else None,
        },
        models_info={
            "registry_status": models_status,
            "total_models": len(model_registry.list_models()),
            "loaded_models": len([m for m in model_registry.list_models() if model_registry.get_model(m).is_model_loaded()]),
        }
    )


@router.get("/ready", response_model=ReadinessResponse)
async def readiness_check(request: Request):
    """Readiness check endpoint for Kubernetes-style health checks."""
    model_registry = request.app.state.model_manager.get_registry()
    checks = {}
    ready = True
    
    # Check if default OCR model is loaded
    try:
        ocr_models = [name for name in model_registry.list_models() 
                     if 'ocr' in name.lower()]
        if ocr_models:
            ocr_model = model_registry.get_model(ocr_models[0])
            checks["ocr_model"] = {
                "status": "ready" if ocr_model.is_model_loaded() else "not_ready",
                "model_name": ocr_model.model_name
            }
            if not ocr_model.is_model_loaded():
                ready = False
        else:
            checks["ocr_model"] = {"status": "not_found"}
            ready = False
    except Exception as e:
        checks["ocr_model"] = {"status": "error", "error": str(e)}
        ready = False
    
    # Check system resources
    memory_percent = psutil.virtual_memory().percent
    checks["memory"] = {
        "status": "ok" if memory_percent < 90 else "warning",
        "usage_percent": memory_percent
    }
    
    cpu_percent = psutil.cpu_percent()
    checks["cpu"] = {
        "status": "ok" if cpu_percent < 90 else "warning", 
        "usage_percent": cpu_percent
    }
    
    return ReadinessResponse(ready=ready, checks=checks)


@router.get("/live")
async def liveness_check():
    """Simple liveness check for Kubernetes-style health checks."""
    return {"status": "alive", "timestamp": time.time()}