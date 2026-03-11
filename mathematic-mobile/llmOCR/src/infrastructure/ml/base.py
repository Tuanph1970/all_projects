"""
Infrastructure base classes for ML model adapters.

BaseMLModel is the abstract adapter base; ModelRegistry manages their lifecycle.
Both are infrastructure concerns — domain code depends only on the repository
interfaces defined in src/domain/*/repositories.py.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

import torch

from ...domain.shared.value_objects import ProcessingResult


class BaseMLModel(ABC):
    """Abstract adapter base for all ML models."""

    def __init__(self, model_name: str, device: str = "cpu") -> None:
        self.model_name = model_name
        self.device = device
        self.model: Optional[Any] = None
        self.is_loaded: bool = False
        self._load_time: Optional[float] = None

    @abstractmethod
    def load_model(self, model_path: Optional[str] = None) -> None:
        """Load model weights from disk or Hugging Face hub."""
        ...

    @abstractmethod
    def predict(self, input_data: Any) -> ProcessingResult:
        """Run inference and return a domain ProcessingResult."""
        ...

    @abstractmethod
    def get_model_info(self) -> Dict[str, Any]:
        """Return metadata dict describing this model."""
        ...

    def is_model_loaded(self) -> bool:
        return self.is_loaded and self.model is not None

    def get_device_info(self) -> Dict[str, str]:
        info: Dict[str, str] = {"device": self.device}
        if self.device == "cuda" and torch.cuda.is_available():
            info.update({
                "cuda_version": torch.version.cuda or "unknown",
                "gpu_name": torch.cuda.get_device_name(0),
                "gpu_memory": f"{torch.cuda.get_device_properties(0).total_memory / 1e9:.2f}GB",
            })
        elif self.device == "mps" and torch.backends.mps.is_available():
            info["mps_available"] = "true"
        return info

    def unload_model(self) -> None:
        if self.model is not None:
            del self.model
            self.model = None
        self.is_loaded = False
        if self.device == "cuda" and torch.cuda.is_available():
            torch.cuda.empty_cache()


class ModelRegistry:
    """
    Registry that owns the lifecycle of all ML model adapters.

    A single instance is created by ModelManager at startup and stored in
    app.state.  Routers receive it via FastAPI dependency injection
    (see src/api/dependencies.py) — never via a module-level global.
    """

    def __init__(self) -> None:
        self._models: Dict[str, BaseMLModel] = {}
        self._model_configs: Dict[str, Dict[str, Any]] = {}

    def register_model(
        self,
        model_id: str,
        model: BaseMLModel,
        config: Optional[Dict[str, Any]] = None,
    ) -> None:
        self._models[model_id] = model
        self._model_configs[model_id] = config or {}

    def get_model(self, model_id: str) -> Optional[BaseMLModel]:
        return self._models.get(model_id)

    def get_model_config(self, model_id: str) -> Dict[str, Any]:
        return self._model_configs.get(model_id, {})

    def list_models(self) -> List[str]:
        return list(self._models.keys())

    def is_model_loaded(self, model_id: str) -> bool:
        model = self.get_model(model_id)
        return model.is_model_loaded() if model else False

    def unload_model(self, model_id: str) -> bool:
        model = self.get_model(model_id)
        if model:
            model.unload_model()
            return True
        return False

    def unload_all_models(self) -> None:
        for model in self._models.values():
            model.unload_model()

    def get_registry_status(self) -> Dict[str, Any]:
        return {
            model_id: {
                "loaded": model.is_model_loaded(),
                "model_name": model.model_name,
                "device": model.device,
                "load_time": getattr(model, "_load_time", None),
            }
            for model_id, model in self._models.items()
        }
