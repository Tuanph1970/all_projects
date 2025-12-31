"""
Base classes and interfaces for ML models.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field
import torch
from PIL import Image


class ModelType(str, Enum):
    """Types of ML models supported by the service."""
    OCR = "ocr"
    LLM = "llm"
    CHAT = "chat"
    SOLUTION = "solution"
    FINE_TUNE = "fine_tune"
    AGENT = "agent"


class TaskStatus(str, Enum):
    """Status of ML processing tasks."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ProcessingResult(BaseModel):
    """Base result class for all ML processing operations."""
    success: bool = Field(description="Whether the operation was successful")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score of the result")
    processing_time: float = Field(ge=0.0, description="Processing time in seconds")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class OCRResult(ProcessingResult):
    """Result from OCR processing."""
    extracted_text: str = Field(description="Extracted text from the image")
    bounding_boxes: Optional[List[Dict[str, Any]]] = Field(default=None)
    detected_language: Optional[str] = Field(default=None)


class LLMResult(ProcessingResult):
    """Result from LLM processing."""
    generated_text: str = Field(description="Generated response text")
    tokens_used: int = Field(ge=0, description="Number of tokens used")
    model_name: str = Field(description="Name of the model used")


class SolutionStep(BaseModel):
    """A single step in a mathematical solution."""
    step_number: int = Field(ge=1, description="Step number in sequence")
    description: str = Field(description="Description of what this step does")
    formula: Optional[str] = Field(default=None, description="Mathematical formula used")
    explanation: str = Field(description="Detailed explanation of the step")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in this step")


class SolutionResult(ProcessingResult):
    """Result from mathematical problem solving."""
    problem_type: str = Field(description="Type of mathematical problem")
    steps: List[SolutionStep] = Field(description="Step-by-step solution")
    final_answer: str = Field(description="Final answer to the problem")
    alternative_methods: Optional[List[str]] = Field(default=None)


class MLTask(BaseModel):
    """Represents an ML processing task."""
    id: str = Field(description="Unique task identifier")
    task_type: str = Field(description="Type of task being processed")
    status: TaskStatus = Field(default=TaskStatus.PENDING)
    input_data: Dict[str, Any] = Field(description="Input data for processing")
    result: Optional[ProcessingResult] = Field(default=None)
    error_message: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    user_id: Optional[str] = Field(default=None)

    def mark_processing(self) -> None:
        """Mark task as currently processing."""
        self.status = TaskStatus.PROCESSING
        self.updated_at = datetime.utcnow()

    def mark_completed(self, result: ProcessingResult) -> None:
        """Mark task as completed with result."""
        self.status = TaskStatus.COMPLETED
        self.result = result
        self.error_message = None
        self.updated_at = datetime.utcnow()

    def mark_failed(self, error_message: str) -> None:
        """Mark task as failed with error message."""
        self.status = TaskStatus.FAILED
        self.error_message = error_message
        self.result = None
        self.updated_at = datetime.utcnow()


class BaseMLModel(ABC):
    """Abstract base class for all ML models."""
    
    def __init__(self, model_name: str, device: str = "cpu"):
        self.model_name = model_name
        self.device = device
        self.model: Optional[Any] = None
        self.is_loaded = False
        self._load_time: Optional[float] = None

    @abstractmethod
    def load_model(self, model_path: str) -> None:
        """Load the ML model from the specified path."""
        pass

    @abstractmethod
    def predict(self, input_data: Any) -> ProcessingResult:
        """Make predictions on the input data."""
        pass

    @abstractmethod
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the model."""
        pass

    def is_model_loaded(self) -> bool:
        """Check if the model is loaded and ready for inference."""
        return self.is_loaded and self.model is not None

    def get_device_info(self) -> Dict[str, str]:
        """Get information about the device being used."""
        device_info = {"device": self.device}
        
        if self.device == "cuda" and torch.cuda.is_available():
            device_info.update({
                "cuda_version": torch.version.cuda,
                "gpu_name": torch.cuda.get_device_name(0),
                "gpu_memory": f"{torch.cuda.get_device_properties(0).total_memory / 1e9:.2f}GB"
            })
        elif self.device == "mps" and torch.backends.mps.is_available():
            device_info["mps_available"] = "true"
        
        return device_info

    def unload_model(self) -> None:
        """Unload the model from memory."""
        if self.model is not None:
            del self.model
            self.model = None
        self.is_loaded = False
        
        # Clear GPU cache if using CUDA
        if self.device == "cuda" and torch.cuda.is_available():
            torch.cuda.empty_cache()


class ModelRegistry:
    """Registry for managing multiple ML models."""
    
    def __init__(self):
        self._models: Dict[str, BaseMLModel] = {}
        self._model_configs: Dict[str, Dict[str, Any]] = {}

    def register_model(
        self, 
        model_id: str, 
        model: BaseMLModel, 
        config: Optional[Dict[str, Any]] = None
    ) -> None:
        """Register a model with the registry."""
        self._models[model_id] = model
        self._model_configs[model_id] = config or {}

    def get_model(self, model_id: str) -> Optional[BaseMLModel]:
        """Get a model from the registry."""
        return self._models.get(model_id)

    def get_model_config(self, model_id: str) -> Dict[str, Any]:
        """Get model configuration."""
        return self._model_configs.get(model_id, {})

    def list_models(self) -> List[str]:
        """List all registered model IDs."""
        return list(self._models.keys())

    def is_model_loaded(self, model_id: str) -> bool:
        """Check if a specific model is loaded."""
        model = self.get_model(model_id)
        return model.is_model_loaded() if model else False

    def unload_model(self, model_id: str) -> bool:
        """Unload a specific model."""
        model = self.get_model(model_id)
        if model:
            model.unload_model()
            return True
        return False

    def unload_all_models(self) -> None:
        """Unload all models from memory."""
        for model in self._models.values():
            model.unload_model()

    def get_registry_status(self) -> Dict[str, Any]:
        """Get status of all models in the registry."""
        status = {}
        for model_id, model in self._models.items():
            status[model_id] = {
                "loaded": model.is_model_loaded(),
                "model_name": model.model_name,
                "device": model.device,
                "load_time": getattr(model, "_load_time", None)
            }
        return status


# Global model registry instance
model_registry = ModelRegistry()


def get_model_registry() -> ModelRegistry:
    """Get the global model registry instance."""
    return model_registry