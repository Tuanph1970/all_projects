"""
Training module for Vietnamese Grade 12 Math Tutor.

This module handles:
- Model loading with quantization
- LoRA configuration
- Training loop execution
"""

from .model_config import load_model, load_tokenizer, get_peft_config
from .trainer_utils import MathTutorTrainer, compute_metrics

__all__ = [
    "load_model",
    "load_tokenizer",
    "get_peft_config",
    "MathTutorTrainer",
    "compute_metrics",
]
