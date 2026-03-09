"""
Model configuration management for flexible model selection.

This module provides a factory pattern for managing ML model configurations,
allowing easy switching between different models without code changes.
"""
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from enum import Enum
import json
import os
from loguru import logger


class ModelProvider(str, Enum):
    """Supported ML model providers."""
    HUGGING_FACE = "huggingface"
    LOCAL = "local"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    CUSTOM = "custom"


class ModelType(str, Enum):
    """Types of ML models."""
    OCR = "ocr"
    SOLUTION = "solution"
    LLM = "llm"
    EMBEDDING = "embedding"


class ModelConfig(BaseModel):
    """Configuration for a single model."""
    
    name: str = Field(..., description="Unique identifier for the model")
    model_type: ModelType = Field(..., description="Type of model")
    provider: ModelProvider = Field(..., description="Model provider")
    
    # Model location
    model_path: Optional[str] = Field(None, description="Path to model (for local models)")
    model_id: Optional[str] = Field(None, description="Model ID (for Hugging Face, etc.)")
    
    # Model parameters
    revision: Optional[str] = Field("main", description="Model revision/branch")
    trust_remote_code: bool = Field(False, description="Whether to trust remote code")
    use_auth_token: bool = Field(False, description="Whether to use auth token")
    
    # Inference parameters
    max_length: int = Field(512, description="Maximum sequence length")
    temperature: float = Field(0.7, description="Sampling temperature")
    top_p: float = Field(0.9, description="Nucleus sampling parameter")
    confidence_threshold: float = Field(0.7, description="Minimum confidence threshold")
    
    # Device configuration
    device: str = Field("cpu", description="Device to run model on (cpu, cuda, mps)")
    device_map: Optional[str] = Field(None, description="Device mapping strategy")
    
    # Performance settings
    batch_size: int = Field(1, description="Batch size for inference")
    num_workers: int = Field(1, description="Number of worker processes")
    
    # Additional configuration
    extra_config: Dict[str, Any] = Field(default_factory=dict, description="Additional model-specific config")
    
    class Config:
        use_enum_values = True
    
    def get_hf_config(self) -> Dict[str, Any]:
        """Get Hugging Face specific configuration."""
        config = {
            "pretrained_model_name_or_path": self.model_id or self.model_path,
            "revision": self.revision,
            "trust_remote_code": self.trust_remote_code,
        }
        
        if self.device_map:
            config["device_map"] = self.device_map
        else:
            config["device_map"] = self.device
        
        if self.use_auth_token:
            # Token will be loaded from environment
            config["use_auth_token"] = os.getenv("HUGGINGFACE_API_TOKEN")
        
        return {**config, **self.extra_config}
    
    def get_inference_config(self) -> Dict[str, Any]:
        """Get inference-time configuration."""
        return {
            "max_length": self.max_length,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "batch_size": self.batch_size,
        }


class ModelRegistryConfig(BaseModel):
    """Configuration for the model registry."""

    default_ocr_model: str = Field("microsoft/trocr-base-handwritten", description="Default OCR model")
    default_solution_model: str = Field("google/flan-t5-base", description="Default solution model")

    # Available models
    ocr_models: List[str] = Field(
        default_factory=lambda: [
            "microsoft/trocr-base-handwritten",
            "microsoft/trocr-base-printed",
            "microsoft/trocr-large-handwritten",
        ],
        description="Available OCR models"
    )
    
    solution_models: List[str] = Field(
        default_factory=lambda: [
            "google/flan-t5-base",
            "google/flan-t5-large",
            "google/flan-ul2",
        ],
        description="Available solution models"
    )
    
    class Config:
        use_enum_values = True


# Predefined model configurations
DEFAULT_MODEL_CONFIGS: Dict[str, ModelConfig] = {
    # OCR Models
    "microsoft/trocr-base-handwritten": ModelConfig(
        name="microsoft/trocr-base-handwritten",
        model_type=ModelType.OCR,
        provider=ModelProvider.HUGGING_FACE,
        model_id="microsoft/trocr-base-handwritten",
        max_length=512,
        confidence_threshold=0.8,
        extra_config={
            "processor_class": "TrOCRProcessor",
            "model_class": "VisionEncoderDecoderModel",
        }
    ),

    "microsoft/trocr-base-printed": ModelConfig(
        name="microsoft/trocr-base-printed",
        model_type=ModelType.OCR,
        provider=ModelProvider.HUGGING_FACE,
        model_id="microsoft/trocr-base-printed",
        max_length=512,
        confidence_threshold=0.8,
        extra_config={
            "processor_class": "TrOCRProcessor",
            "model_class": "VisionEncoderDecoderModel",
        }
    ),

    "microsoft/trocr-large-handwritten": ModelConfig(
        name="microsoft/trocr-large-handwritten",
        model_type=ModelType.OCR,
        provider=ModelProvider.HUGGING_FACE,
        model_id="microsoft/trocr-large-handwritten",
        max_length=512,
        confidence_threshold=0.85,
        extra_config={
            "processor_class": "TrOCRProcessor",
            "model_class": "VisionEncoderDecoderModel",
        }
    ),
    
    # Solution Models
    "google/flan-t5-base": ModelConfig(
        name="google/flan-t5-base",
        model_type=ModelType.SOLUTION,
        provider=ModelProvider.HUGGING_FACE,
        model_id="google/flan-t5-base",
        max_length=512,
        temperature=0.7,
        confidence_threshold=0.7,
        extra_config={
            "model_class": "AutoModelForSeq2SeqLM",
            "tokenizer_class": "AutoTokenizer",
        }
    ),
    
    "google/flan-t5-large": ModelConfig(
        name="google/flan-t5-large",
        model_type=ModelType.SOLUTION,
        provider=ModelProvider.HUGGING_FACE,
        model_id="google/flan-t5-large",
        max_length=768,
        temperature=0.7,
        confidence_threshold=0.75,
        extra_config={
            "model_class": "AutoModelForSeq2SeqLM",
            "tokenizer_class": "AutoTokenizer",
        }
    ),
    
    "google/flan-t5-xl": ModelConfig(
        name="google/flan-t5-xl",
        model_type=ModelType.SOLUTION,
        provider=ModelProvider.HUGGING_FACE,
        model_id="google/flan-t5-xl",
        max_length=1024,
        temperature=0.7,
        confidence_threshold=0.8,
        extra_config={
            "model_class": "AutoModelForSeq2SeqLM",
            "tokenizer_class": "AutoTokenizer",
        }
    ),
    
    "google/flan-ul2": ModelConfig(
        name="google/flan-ul2",
        model_type=ModelType.SOLUTION,
        provider=ModelProvider.HUGGING_FACE,
        model_id="google/flan-ul2",
        max_length=1024,
        temperature=0.7,
        confidence_threshold=0.8,
        extra_config={
            "model_class": "AutoModelForSeq2SeqLM",
            "tokenizer_class": "AutoTokenizer",
        }
    ),
}


class ModelConfigFactory:
    """
    Factory class for creating and managing model configurations.
    
    Provides methods to:
    - Get predefined model configurations
    - Create custom model configurations
    - Load configurations from files
    - Save configurations to files
    """
    
    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize the factory.
        
        Args:
            config_file: Optional path to custom configuration file
        """
        self.configs = DEFAULT_MODEL_CONFIGS.copy()
        self.config_file = config_file
        
        # Load custom configurations if file exists
        if config_file and os.path.exists(config_file):
            self.load_from_file(config_file)
    
    def get_config(self, model_name: str) -> Optional[ModelConfig]:
        """
        Get configuration for a specific model.
        
        Args:
            model_name: Name/ID of the model
            
        Returns:
            ModelConfig if found, None otherwise
        """
        return self.configs.get(model_name)
    
    def get_ocr_config(self, model_name: Optional[str] = None) -> ModelConfig:
        """
        Get OCR model configuration.

        Args:
            model_name: Optional model name, uses default if not provided

        Returns:
            ModelConfig for OCR model
        """
        name = model_name or "microsoft/trocr-base-handwritten"
        config = self.get_config(name)

        if not config:
            logger.warning(f"OCR model '{name}' not found, using default")
            return self.create_default_ocr_config(name)

        return config
    
    def get_solution_config(self, model_name: Optional[str] = None) -> ModelConfig:
        """
        Get solution model configuration.
        
        Args:
            model_name: Optional model name, uses default if not provided
            
        Returns:
            ModelConfig for solution model
        """
        name = model_name or "google/flan-t5-base"
        config = self.get_config(name)
        
        if not config:
            logger.warning(f"Solution model '{name}' not found, using default")
            return self.create_default_solution_config(name)
        
        return config
    
    def create_default_ocr_config(self, model_name: str) -> ModelConfig:
        """Create a default OCR model configuration."""
        return ModelConfig(
            name=model_name,
            model_type=ModelType.OCR,
            provider=ModelProvider.HUGGING_FACE,
            model_id=model_name,
            max_length=512,
            confidence_threshold=0.8,
        )
    
    def create_default_solution_config(self, model_name: str) -> ModelConfig:
        """Create a default solution model configuration."""
        return ModelConfig(
            name=model_name,
            model_type=ModelType.SOLUTION,
            provider=ModelProvider.HUGGING_FACE,
            model_id=model_name,
            max_length=512,
            temperature=0.7,
            confidence_threshold=0.7,
        )
    
    def create_custom_config(
        self,
        name: str,
        model_type: ModelType,
        provider: ModelProvider,
        model_path: Optional[str] = None,
        model_id: Optional[str] = None,
        **kwargs
    ) -> ModelConfig:
        """
        Create a custom model configuration.
        
        Args:
            name: Unique name for the model
            model_type: Type of model
            provider: Model provider
            model_path: Path for local models
            model_id: Model ID for remote models
            **kwargs: Additional configuration parameters
            
        Returns:
            ModelConfig instance
        """
        config = ModelConfig(
            name=name,
            model_type=model_type,
            provider=provider,
            model_path=model_path,
            model_id=model_id,
            **kwargs
        )
        
        self.configs[name] = config
        return config
    
    def list_configs(self, model_type: Optional[ModelType] = None) -> List[str]:
        """
        List all available model configurations.
        
        Args:
            model_type: Optional filter by model type
            
        Returns:
            List of model names
        """
        if model_type:
            return [
                name for name, config in self.configs.items()
                if config.model_type == model_type
            ]
        return list(self.configs.keys())
    
    def save_to_file(self, filepath: str) -> None:
        """
        Save configurations to a JSON file.
        
        Args:
            filepath: Path to save configuration
        """
        configs_dict = {
            name: config.dict() for name, config in self.configs.items()
        }
        
        with open(filepath, 'w') as f:
            json.dump(configs_dict, f, indent=2)
        
        logger.info(f"Saved {len(self.configs)} model configurations to {filepath}")
    
    def load_from_file(self, filepath: str) -> None:
        """
        Load configurations from a JSON file.
        
        Args:
            filepath: Path to configuration file
        """
        try:
            with open(filepath, 'r') as f:
                configs_dict = json.load(f)
            
            for name, config_data in configs_dict.items():
                self.configs[name] = ModelConfig(**config_data)
            
            logger.info(f"Loaded {len(self.configs)} model configurations from {filepath}")
            
        except Exception as e:
            logger.error(f"Failed to load configurations from {filepath}: {e}")
            raise
    
    def get_registry_config(self) -> ModelRegistryConfig:
        """Get the model registry configuration."""
        return ModelRegistryConfig(
            default_ocr_model="microsoft/trocr-base-handwritten",
            default_solution_model="google/flan-t5-base",
            ocr_models=self.list_configs(ModelType.OCR),
            solution_models=self.list_configs(ModelType.SOLUTION),
        )


# Global factory instance
_model_config_factory: Optional[ModelConfigFactory] = None


def get_model_config_factory(config_file: Optional[str] = None) -> ModelConfigFactory:
    """
    Get the global model configuration factory.
    
    Args:
        config_file: Optional path to custom configuration file
        
    Returns:
        ModelConfigFactory instance
    """
    global _model_config_factory
    
    if _model_config_factory is None:
        _model_config_factory = ModelConfigFactory(config_file)
    
    return _model_config_factory


def get_model_config(model_name: str) -> Optional[ModelConfig]:
    """
    Convenience function to get a model configuration.
    
    Args:
        model_name: Name of the model
        
    Returns:
        ModelConfig if found, None otherwise
    """
    return get_model_config_factory().get_config(model_name)


def get_default_ocr_config() -> ModelConfig:
    """Get default OCR model configuration."""
    return get_model_config_factory().get_ocr_config()


def get_default_solution_config() -> ModelConfig:
    """Get default solution model configuration."""
    return get_model_config_factory().get_solution_config()
